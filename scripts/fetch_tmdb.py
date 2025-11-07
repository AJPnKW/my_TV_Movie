# =============================================================================
# File: scripts/fetch_tmdb.py
# Project: my_TV_Movie
# Version: v2.2.0 (2025-11-07)
#
# Purpose:
#   Build data/data.json for the static web UI.
#
# Inputs:
#   tv_list.txt
#       name | tmdb_show_id | season_spec | tvmaze_id (optional)
#         season_spec:
#           5       -> only season 5
#           1,2,5   -> seasons 1, 2, 5
#           *       -> all seasons
#
#   movies_list.txt OR movies.txt
#       name | tmdb_movie_id
#
# Behavior:
#   - Fetches show + season + episode data from TMDB.
#   - Optionally enriches with TVMaze if tvmaze_id + API_TVMAZE_KEY.
#   - Fetches movies from TMDB.
#   - Writes:
#       data/data.json
#       data/last_refresh.txt
#
# Output schema (simplified):
#   {
#     "generated_at": "...Z",
#     "shows": [ { show_id, name, status, genres, links, seasons[] } ],
#     "movies": [ { movie_id, name, status, genres, links } ],
#     "meta": { "shows": N, "movies": M }
#   }
#
# Env / GitHub Secrets:
#   API_TMDB_KEY     (required, unless API_TMDB_TOKEN used)
#   API_TMDB_TOKEN   (optional TMDB v4)
#   API_TVMAZE_KEY   (optional; improves episodes)
#
# Notes:
#   - Safe for local runs and GitHub Actions.
#   - Skips invalid / TBD movie IDs.
# =============================================================================

import os
import json
import time
import re
import pathlib
import sys
from datetime import datetime

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        pass

import requests

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
ROOT = pathlib.Path(__file__).resolve().parents[1]
TV_LIST = ROOT / "tv_list.txt"


def find_movies_list():
    """Find movies_list.txt or movies.txt if present."""
    for name in ("movies_list.txt", "movies.txt"):
        p = ROOT / name
        if p.exists():
            return p
    return None


MOVIES_LIST = find_movies_list()

DATA_DIR = ROOT / "data"
DATA_JSON = DATA_DIR / "data.json"
STAMP = DATA_DIR / "last_refresh.txt"

# -----------------------------------------------------------------------------
# Environment
# -----------------------------------------------------------------------------
load_dotenv(ROOT / ".env")

TMDB_V3 = os.environ.get("API_TMDB_KEY", "")
TMDB_V4 = os.environ.get("API_TMDB_TOKEN", "")
TVMAZE_KEY = os.environ.get("API_TVMAZE_KEY", "")

BASE_TMDB = "https://api.themoviedb.org/3"
BASE_TVMAZE = "https://api.tvmaze.com"

HEADERS_TMDB = (
    {"Authorization": f"Bearer {TMDB_V4}", "Accept": "application/json"}
    if TMDB_V4 else None
)
PARAMS_TMDB = {"api_key": TMDB_V3} if TMDB_V3 and not TMDB_V4 else {}

TV_LINE_RE = re.compile(
    r"^\s*([^#|]+?)\s*\|\s*(\d+)\s*\|\s*([\d,\*]+)(?:\s*\|\s*(\d+))?\s*$"
)
MOVIE_LINE_RE = re.compile(
    r"^\s*([^#|]+?)\s*\|\s*(\d+)\s*$"
)

# -----------------------------------------------------------------------------
# HTTP helpers
# -----------------------------------------------------------------------------
def tmdb_get(path: str, extra_params=None, max_tries=5, backoff=1.5):
    """GET from TMDB with retry + v3/v4 auth."""
    url = f"{BASE_TMDB}{path}"
    params = {}
    if not TMDB_V4:
        params.update(PARAMS_TMDB)
    if extra_params:
        params.update(extra_params or {})

    s = requests.Session()
    if HEADERS_TMDB:
        s.headers.update(HEADERS_TMDB)

    for attempt in range(max_tries):
        r = s.get(url, params=params, timeout=20)
        if r.status_code == 429:
            # rate limited; backoff
            time.sleep(backoff * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()

    raise RuntimeError(f"TMDB request failed after retries: {url}")


def tvmaze_get(path: str, params=None, max_tries=3, backoff=1.5):
    """GET from TVMaze if enabled."""
    if not TVMAZE_KEY:
        raise RuntimeError("TVMaze disabled (no API_TVMAZE_KEY).")
    url = f"{BASE_TVMAZE}{path}"
    headers = {"X-API-Key": TVMAZE_KEY}
    for attempt in range(max_tries):
        r = requests.get(url, headers=headers, params=params or {}, timeout=20)
        if r.status_code == 429:
            time.sleep(backoff * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"TVMaze request failed after retries: {url}")


def strip_html(text: str) -> str:
    return re.sub(r"<.*?>", "", text or "").strip()

# -----------------------------------------------------------------------------
# Parse tv_list.txt
# -----------------------------------------------------------------------------
def parse_tv_list(path: pathlib.Path):
    if not path.exists():
        return []
    out = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            m = TV_LINE_RE.match(line)
            if not m:
                print(f"WARN: skip malformed tv_list line: {line}")
                continue
            name, show_id, seasons, tvmaze_id = m.groups()
            if seasons == "*":
                season_spec = "*"
            else:
                season_spec = [
                    int(s.strip()) for s in seasons.split(",") if s.strip()
                ]
            item = {
                "ref_name": name.strip(),
                "show_id": int(show_id),
                "season_spec": season_spec,
                "profile": "default",
            }
            if tvmaze_id:
                item["tvmaze_id"] = int(tvmaze_id)
            out.append(item)
    return out

# -----------------------------------------------------------------------------
# Parse movies_list (simple + robust)
# -----------------------------------------------------------------------------
def parse_movies_list(path: pathlib.Path | None):
    if not path or not path.exists():
        return []
    movies = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            m = MOVIE_LINE_RE.match(line)
            if not m:
                # ignore malformed (e.g., TBD ids)
                continue
            name, movie_id = m.groups()
            movies.append(
                {
                    "ref_name": name.strip(),
                    "movie_id": int(movie_id),
                    "profile": "default",
                }
            )
    return movies

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def is_placeholder_title(name: str) -> bool:
    if not name:
        return True
    ln = name.strip().lower()
    if ln in {"tba", "n/a"}:
        return True
    if ln.startswith("episode "):
        return True
    return False


def ensure_title(ep: dict, season_no: int) -> str:
    name = ep.get("name") or ""
    ep_no = ep.get("episode_number") or 0
    if is_placeholder_title(name):
        return f"S{season_no:02d}E{ep_no:02d}"
    return name


def show_links(show_id: int) -> dict:
    return {
        "tmdb": f"https://www.themoviedb.org/tv/{show_id}",
    }


def movie_links(movie_id: int) -> dict:
    return {
        "tmdb": f"https://www.themoviedb.org/movie/{movie_id}",
    }

# -----------------------------------------------------------------------------
# TVMaze enrichment (optional)
# -----------------------------------------------------------------------------
def enrich_with_tvmaze(show_payload: dict, tvmaze_id: int):
    if not TVMAZE_KEY or not tvmaze_id:
        return
    try:
        eps = tvmaze_get(f"/shows/{tvmaze_id}/episodes")
    except Exception as e:
        print(f"WARN: TVMaze failed for {show_payload.get('name')}: {e}")
        return

    idx = {
        (e.get("season"), e.get("number")): e
        for e in eps
        if e.get("season") and e.get("number")
    }

    for s in show_payload.get("seasons", []):
        sn = s["season_number"]
        for ep in s.get("episodes", []):
            key = (sn, ep.get("episode_number"))
            src = idx.get(key)
            if not src:
                continue

            if not ep.get("air_date") and src.get("airdate"):
                ep["air_date"] = src["airdate"]
            if is_placeholder_title(ep.get("name") or "") and src.get("name"):
                ep["name"] = src["name"]
            if not ep.get("overview") and src.get("summary"):
                ep["overview"] = strip_html(src["summary"])

# -----------------------------------------------------------------------------
# Collectors
# -----------------------------------------------------------------------------
def collect_show(show_id: int, season_spec, tvmaze_id=None) -> dict:
    show = tmdb_get(f"/tv/{show_id}")
    genres = [g["name"] for g in show.get("genres", [])]

    all_meta = {
        s["season_number"]: s
        for s in show.get("seasons", [])
        if s.get("season_number", 0) > 0
    }

    if season_spec == "*":
        wanted = sorted(all_meta.keys())
    else:
        wanted = [s for s in season_spec if s in all_meta]

    seasons = []
    for sn in wanted:
        meta = all_meta.get(sn, {})
        info = tmdb_get(f"/tv/{show_id}/season/{sn}")
        eps = []
        for ep in info.get("episodes", []):
            eps.append(
                {
                    "episode_number": ep.get("episode_number"),
                    "name": ensure_title(ep, sn),
                    "air_date": ep.get("air_date"),
                    "overview": ep.get("overview") or "",
                    "still_path": ep.get("still_path"),
                }
            )
        seasons.append(
            {
                "season_number": sn,
                "name": meta.get("name") or f"Season {sn}",
                "air_date": meta.get("air_date") or info.get("air_date"),
                "episode_count": len(eps),
                "overview": info.get("overview") or meta.get("overview") or "",
                "episodes": eps,
            }
        )

    payload = {
        "show_id": show_id,
        "name": show.get("name"),
        "original_name": show.get("original_name"),
        "overview": show.get("overview") or "",
        "first_air_date": show.get("first_air_date"),
        "last_air_date": show.get("last_air_date"),
        "status": show.get("status"),
        "poster_path": show.get("poster_path"),
        "backdrop_path": show.get("backdrop_path"),
        "genres": genres,
        "links": show_links(show_id),
        "seasons": seasons,
    }

    if tvmaze_id:
        enrich_with_tvmaze(payload, tvmaze_id)

    return payload


def collect_movie(movie_id: int) -> dict:
    mv = tmdb_get(f"/movie/{movie_id}")
    genres = [g["name"] for g in mv.get("genres", [])]
    return {
        "movie_id": movie_id,
        "name": mv.get("title"),
        "original_name": mv.get("original_title"),
        "overview": mv.get("overview") or "",
        "release_date": mv.get("release_date"),
        "runtime": mv.get("runtime"),
        "status": mv.get("status"),
        "poster_path": mv.get("poster_path"),
        "backdrop_path": mv.get("backdrop_path"),
        "genres": genres,
        "links": movie_links(movie_id),
    }

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    if not TMDB_V3 and not TMDB_V4:
        print("ERROR: API_TMDB_KEY or API_TMDB_TOKEN required.")
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    tv_specs = parse_tv_list(TV_LIST)
    mv_specs = parse_movies_list(MOVIES_LIST)

    out = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "shows": [],
        "movies": [],
    }

    # TV shows
    for item in tv_specs:
        try:
            print(f"[TV] {item['ref_name']} ({item['show_id']}) {item['season_spec']}")
            sh = collect_show(
                item["show_id"],
                item["season_spec"],
                tvmaze_id=item.get("tvmaze_id"),
            )
            sh["ref_name"] = item["ref_name"]
            sh["profile"] = item.get("profile", "default")
            out["shows"].append(sh)
            time.sleep(0.2)
        except Exception as e:
            print(f"ERROR show {item['ref_name']} ({item['show_id']}): {e}")

    # Movies
    for item in mv_specs:
        try:
            print(f"[MV] {item['ref_name']} ({item['movie_id']})")
            mv = collect_movie(item["movie_id"])
            mv["ref_name"] = item["ref_name"]
            mv["profile"] = item.get("profile", "default")
            out["movies"].append(mv)
            time.sleep(0.2)
        except Exception as e:
            print(f"ERROR movie {item['ref_name']} ({item['movie_id']}): {e}")

    out["meta"] = {
        "shows": len(out["shows"]),
        "movies": len(out["movies"]),
    }

    DATA_JSON.write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    STAMP.write_text(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        encoding="utf-8",
    )

    print(
        f"OK: wrote {DATA_JSON} with "
        f"{out['meta']['shows']} shows, {out['meta']['movies']} movies"
    )


if __name__ == "__main__":
    main()
