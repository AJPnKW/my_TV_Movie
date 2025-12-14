#!/usr/bin/env python3
# ======================================================================================
# [FILE]        scripts/fetch_tmdb.py
# [PROJECT]     my_TV_Movie (My TV Hub)
# [ROLE]        Build data/data.json from TMDB using config-driven streaming bases,
#               and optionally cache missing images locally (never overwrite).
# [VERSION]     v2.6.0
# [UPDATED]     2025-12-14
# [OWNER]       Andrew & Brant (internal)
#
# [INPUTS]
#   - web/config.json            (authoritative streaming bases + image sizes)
#   - tv_list.txt                (show ids / names)
#   - movies_list.txt            (movie ids / names)
#   - live_tv_list.txt           (optional)
#
# [OUTPUTS]
#   - data/data.json             (links resolved, local_*_path fields added)
#   - image/**                   (download missing images only)
#
# [RULES]
#   - NO hard-coded streaming domains in UI
#   - ALL streaming URLs are generated here using web/config.json
#   - Image caching: download ONLY if file does not already exist
#   - Schema is additive; existing keys are preserved
# ======================================================================================

import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime

# -----------------------------
# [CFG-1.0] Paths
# -----------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "web" / "config.json"
DATA_DIR = REPO_ROOT / "data"
DATA_JSON_PATH = DATA_DIR / "data.json"

IMAGE_ROOT = REPO_ROOT / "image"
IMAGE_SHOWS = IMAGE_ROOT / "shows"
IMAGE_MOVIES = IMAGE_ROOT / "movies"

IMAGE_SHOWS_POSTER = IMAGE_SHOWS / "poster"
IMAGE_SHOWS_BACKDROP = IMAGE_SHOWS / "backdrop"
IMAGE_SEASONS_POSTER = IMAGE_SHOWS / "seasons" / "poster"
IMAGE_EP_STILLS = IMAGE_SHOWS / "episodes" / "stills"

IMAGE_MOVIES_POSTER = IMAGE_MOVIES / "poster"
IMAGE_MOVIES_BACKDROP = IMAGE_MOVIES / "backdrop"

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"

# -----------------------------
# [CFG-2.0] Environment
# -----------------------------
API_TMDB_KEY = os.environ.get("API_TMDB_KEY")
if not API_TMDB_KEY:
    print("[fetch_tmdb] ERROR: API_TMDB_KEY is required in env.", file=sys.stderr)
    sys.exit(1)

# -----------------------------
# [UTIL-1.0] Helpers
# -----------------------------
def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def download_if_missing(url: str, dest: Path):
    if not url or dest.exists():
        return
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with dest.open("wb") as f:
            f.write(r.content)
        print(f"[img] downloaded {dest.relative_to(REPO_ROOT)}")
    except Exception as e:
        print(f"[img] WARN: failed to download {url} -> {e}", file=sys.stderr)

def tmdb_image_url(path: str, width: int) -> str:
    if not path:
        return ""
    return f"{TMDB_IMAGE_BASE}/w{width}{path}"

# -----------------------------
# [CFG-3.0] Load config
# -----------------------------
config = load_json(CONFIG_PATH)

streaming = config.get("streaming_services", {})
img_sizes = config.get("image_sizes", {})

VIDSRC_TV = streaming.get("vidsrc_tv", "")
VIDSRC_MOVIE = streaming.get("vidsrc_movie", "")
VIDEASY_TV = streaming.get("videasy_tv", "")
VIDEASY_MOVIE = streaming.get("videasy_movie", "")

SHOW_W = int(img_sizes.get("show_width", 185))
MOVIE_W = int(img_sizes.get("movie_width", 185))
SEASON_W = int(img_sizes.get("season_width", SHOW_W))
EP_W = int(img_sizes.get("episode_still_w", 300))
BACKDROP_W = int(img_sizes.get("backdrop_w", 780))

# -----------------------------
# [CFG-4.0] TMDB session
# -----------------------------
SESSION = requests.Session()
SESSION.params = {"api_key": API_TMDB_KEY}

def tmdb_get(path: str, params=None):
    url = f"https://api.themoviedb.org/3{path}"
    r = SESSION.get(url, params=params or {}, timeout=30)
    r.raise_for_status()
    return r.json()

# -----------------------------
# [DATA-1.0] Load lists
# -----------------------------
def load_list(filename):
    p = REPO_ROOT / filename
    if not p.exists():
        return []
    items = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            items.append(line)
    return items

tv_list = load_list("tv_list.txt")
movie_list = load_list("movies_list.txt")

# -----------------------------
# [IMG-1.0] Ensure dirs
# -----------------------------
for d in [
    DATA_DIR,
    IMAGE_SHOWS_POSTER,
    IMAGE_SHOWS_BACKDROP,
    IMAGE_SEASONS_POSTER,
    IMAGE_EP_STILLS,
    IMAGE_MOVIES_POSTER,
    IMAGE_MOVIES_BACKDROP,
]:
    ensure_dir(d)

# -----------------------------
# [BUILD-1.0] Build data
# -----------------------------
output = {
    "meta": {
        "built_at": datetime.utcnow().isoformat() + "Z",
        "config_used": config.get("_meta", {}).get("version", "unknown"),
        "source": "TMDB",
    },
    "shows": [],
    "movies": [],
}

# -----------------------------
# [BUILD-2.0] TV shows
# -----------------------------
for ref in tv_list:
    try:
        show_id = int(ref.split()[0])
        show = tmdb_get(f"/tv/{show_id}")

        poster_path = show.get("poster_path")
        backdrop_path = show.get("backdrop_path")

        # Local image paths
        local_show_poster = f"/image/shows/poster/{poster_path.lstrip('/')}" if poster_path else ""
        local_show_backdrop = f"/image/shows/backdrop/{backdrop_path.lstrip('/')}" if backdrop_path else ""

        # Cache images (missing only)
        if poster_path:
            download_if_missing(
                tmdb_image_url(poster_path, SHOW_W),
                IMAGE_SHOWS_POSTER / poster_path.lstrip("/"),
            )
        if backdrop_path:
            download_if_missing(
                tmdb_image_url(backdrop_path, BACKDROP_W),
                IMAGE_SHOWS_BACKDROP / backdrop_path.lstrip("/"),
            )

        seasons_out = []
        for s in show.get("seasons", []):
            if not s.get("season_number", 0) >= 0:
                continue

            season_id = s.get("season_number")
            season_poster = s.get("poster_path")

            local_season_poster = (
                f"/image/shows/seasons/poster/{season_poster.lstrip('/')}"
                if season_poster else ""
            )

            if season_poster:
                download_if_missing(
                    tmdb_image_url(season_poster, SEASON_W),
                    IMAGE_SEASONS_POSTER / season_poster.lstrip("/"),
                )

            season_detail = tmdb_get(f"/tv/{show_id}/season/{season_id}")
            episodes_out = []

            for ep in season_detail.get("episodes", []):
                still_path = ep.get("still_path")
                local_ep_still = (
                    f"/image/shows/episodes/stills/{still_path.lstrip('/')}"
                    if still_path else ""
                )

                if still_path:
                    download_if_missing(
                        tmdb_image_url(still_path, EP_W),
                        IMAGE_EP_STILLS / still_path.lstrip("/"),
                    )

                episodes_out.append({
                    "season_number": season_id,
                    "episode_number": ep.get("episode_number"),
                    "name": ep.get("name"),
                    "air_date": ep.get("air_date"),
                    "overview": ep.get("overview"),
                    "runtime": ep.get("runtime"),
                    "still_path": still_path,
                    "local_still_path": local_ep_still,
                    "links": {
                        "vidsrc": f"{VIDSRC_TV}{show_id}/{season_id}/{ep.get('episode_number')}",
                        "videasy": f"{VIDEASY_TV}{show_id}/{season_id}/{ep.get('episode_number')}",
                    },
                })

            seasons_out.append({
                "season_number": season_id,
                "name": s.get("name"),
                "poster_path": season_poster,
                "local_poster_path": local_season_poster,
                "episodes": episodes_out,
            })

        output["shows"].append({
            "id": show_id,
            "name": show.get("name"),
            "status": show.get("status"),
            "poster_path": poster_path,
            "backdrop_path": backdrop_path,
            "local_poster_path": local_show_poster,
            "local_backdrop_path": local_show_backdrop,
            "seasons": seasons_out,
        })

    except Exception as e:
        print(f"[show] ERROR {ref}: {e}", file=sys.stderr)

# -----------------------------
# [BUILD-3.0] Movies
# -----------------------------
for ref in movie_list:
    try:
        movie_id = int(ref.split()[0])
        movie = tmdb_get(f"/movie/{movie_id}")

        poster_path = movie.get("poster_path")
        backdrop_path = movie.get("backdrop_path")

        local_movie_poster = f"/image/movies/poster/{poster_path.lstrip('/')}" if poster_path else ""
        local_movie_backdrop = f"/image/movies/backdrop/{backdrop_path.lstrip('/')}" if backdrop_path else ""

        if poster_path:
            download_if_missing(
                tmdb_image_url(poster_path, MOVIE_W),
                IMAGE_MOVIES_POSTER / poster_path.lstrip("/"),
            )
        if backdrop_path:
            download_if_missing(
                tmdb_image_url(backdrop_path, BACKDROP_W),
                IMAGE_MOVIES_BACKDROP / backdrop_path.lstrip("/"),
            )

        output["movies"].append({
            "id": movie_id,
            "name": movie.get("title"),
            "release_date": movie.get("release_date"),
            "poster_path": poster_path,
            "backdrop_path": backdrop_path,
            "local_poster_path": local_movie_poster,
            "local_backdrop_path": local_movie_backdrop,
            "links": {
                "vidsrc": f"{VIDSRC_MOVIE}{movie_id}",
                "videasy": f"{VIDEASY_MOVIE}{movie_id}",
            },
        })

    except Exception as e:
        print(f"[movie] ERROR {ref}: {e}", file=sys.stderr)

# -----------------------------
# [WRITE-1.0] Save output
# -----------------------------
ensure_dir(DATA_DIR)
with DATA_JSON_PATH.open("w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("[fetch_tmdb] OK: data/data.json written")
print("[fetch_tmdb] OK: image cache updated (missing only)")
            
