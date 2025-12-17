#!/usr/bin/env python3
# =============================================================================
# File:        scripts/fetch_tmdb.py
# Purpose:     Build static TV/Movie release data + local image cache for the hub
# Repo:        my_TV_Movie
#
# Version:
#   v2.6.2 (2025-12-17)
# Build tag:   v14.01.04
#
# Key behaviours (do not remove):
#   - Reads hub config from: web/config.json (streaming bases + image sizes + UI tuning)
#   - Reads lists:
#       * tv_list.txt
#       * movies_list.txt
#       * livetv_list.txt  (OPTIONAL; do not hard-fail if missing)
#   - Writes outputs:
#       * data/data.json
#       * data/last_refresh.txt
#   - Generates streaming links using config bases (no hard-coded domains)
#   - Downloads ONLY missing images into local cache:
#       * image/shows/poster/
#       * image/shows/backdrop/
#       * image/shows/seasons/poster/
#       * image/shows/episodes/stills/
#       * image/movies/poster/
#       * image/movies/backdrop/
#   - Adds local_*_path fields in data.json for UI to reference local images.
#
# Environment:
#   - API_TMDB_KEY (required)  OR  API_TMDB_TOKEN (optional alternative)
# =============================================================================

from __future__ import annotations

import dataclasses
import datetime as _dt
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Third-party (must be installed in venv / workflow)
import requests  # noqa: F401

# -----------------------------------------------------------------------------
# [CFG-1.0] Repo paths (relative to repo root)
# -----------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
DATA_DIR = REPO_ROOT / "data"
IMAGE_DIR = REPO_ROOT / "image"

CONFIG_PATH = WEB_DIR / "config.json"

TV_LIST_PATH = REPO_ROOT / "tv_list.txt"
MOVIES_LIST_PATH = REPO_ROOT / "movies_list.txt"
LIVETV_LIST_PATH = REPO_ROOT / "livetv_list.txt"  # OPTIONAL; may be empty/missing

DATA_JSON_PATH = DATA_DIR / "data.json"
LAST_REFRESH_PATH = DATA_DIR / "last_refresh.txt"

# -----------------------------------------------------------------------------
# [CFG-1.1] TMDB constants
# -----------------------------------------------------------------------------
TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/"

DEFAULT_TIMEOUT = 30

# -----------------------------------------------------------------------------
# [CFG-1.2] Config defaults (used only if config.json missing keys)
# -----------------------------------------------------------------------------
DEFAULT_STREAMING_SERVICES = {
    "vidsrc_tv": "https://vidsrc.net/embed/tv/",
    "vidsrc_movie": "https://vidsrc.net/embed/movie/",
    "videasy_tv": "https://player.videasy.net/tv/",
    "videasy_movie": "https://player.videasy.net/movie/",
}

DEFAULT_IMAGE_SIZES = {
    "show_width": 185,
    "movie_width": 185,
    "season_width": 185,
    "episode_still_w": 300,
    "backdrop_w": 780,
}

DEFAULT_UI_TUNING = {
    "calendar_button_scale": 0.75,
    "calendar_card_density": 1.0,
}

# -----------------------------------------------------------------------------
# [LOG-1.0] Lightweight logging
# -----------------------------------------------------------------------------
def log(msg: str) -> None:
    ts = _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[fetch_tmdb] {ts} {msg}".rstrip())


def die(msg: str, code: int = 1) -> None:
    log(f"ERROR: {msg}")
    sys.exit(code)


# -----------------------------------------------------------------------------
# [UTIL-1.0] JSON helpers
# -----------------------------------------------------------------------------
def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        die(f"Failed to parse JSON: {path} ({e})")
        return {}  # unreachable


def write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


# -----------------------------------------------------------------------------
# [CFG-2.0] Config model + normalization
# -----------------------------------------------------------------------------
@dataclass
class StreamingConf:
    vidsrc_tv: str
    vidsrc_movie: str
    videasy_tv: str
    videasy_movie: str


@dataclass
class ImageSizeConf:
    show_width: int
    movie_width: int
    season_width: int
    episode_still_w: int
    backdrop_w: int


@dataclass
class UiTuningConf:
    calendar_button_scale: float
    calendar_card_density: float


@dataclass
class HubConfig:
    streaming: StreamingConf
    image_sizes: ImageSizeConf
    ui: UiTuningConf


def _to_int(v: Any, default: int) -> int:
    try:
        iv = int(v)
        return iv if iv > 0 else default
    except Exception:
        return default


def _to_float(v: Any, default: float) -> float:
    try:
        fv = float(v)
        return fv
    except Exception:
        return default


def _norm_base(u: str) -> str:
    """Normalize base URLs used for link building.
    - Trims whitespace
    - Ensures trailing slash
    - Self-heals known historical base variants so we don't silently mix domains/paths.
      * Videasy TV/Movie should be:
        https://player.videasy.net/tv/
        https://player.videasy.net/movie/
        (NOT /embed/...)
    """
    u = (u or "").strip()
    if not u:
        return ""

    # Self-heal legacy Videasy embed bases (these have caused breakage before)
    if "player.videasy.net/embed/" in u:
        u = u.replace("player.videasy.net/embed/", "player.videasy.net/")

    return u if u.endswith("/") else (u + "/")


def load_config() -> HubConfig:
    raw = read_json(CONFIG_PATH)

    ss = raw.get("streaming_services") or {}
    img = raw.get("image_sizes") or {}
    ui = raw.get("ui_tuning") or {}

    streaming = StreamingConf(
        vidsrc_tv=_norm_base(ss.get("vidsrc_tv", DEFAULT_STREAMING_SERVICES["vidsrc_tv"])),
        vidsrc_movie=_norm_base(ss.get("vidsrc_movie", DEFAULT_STREAMING_SERVICES["vidsrc_movie"])),
        videasy_tv=_norm_base(ss.get("videasy_tv", DEFAULT_STREAMING_SERVICES["videasy_tv"])),
        videasy_movie=_norm_base(ss.get("videasy_movie", DEFAULT_STREAMING_SERVICES["videasy_movie"])),
    )

    # Validate required bases exist (empty bases will break UI links)
    if not streaming.vidsrc_tv or not streaming.vidsrc_movie or not streaming.videasy_tv or not streaming.videasy_movie:
        die("config.json missing streaming base URLs under streaming_services.*")

    image_sizes = ImageSizeConf(
        show_width=_to_int(img.get("show_width"), DEFAULT_IMAGE_SIZES["show_width"]),
        movie_width=_to_int(img.get("movie_width"), DEFAULT_IMAGE_SIZES["movie_width"]),
        season_width=_to_int(img.get("season_width"), DEFAULT_IMAGE_SIZES["season_width"]),
        episode_still_w=_to_int(img.get("episode_still_w"), DEFAULT_IMAGE_SIZES["episode_still_w"]),
        backdrop_w=_to_int(img.get("backdrop_w"), DEFAULT_IMAGE_SIZES["backdrop_w"]),
    )

    ui_conf = UiTuningConf(
        calendar_button_scale=_to_float(ui.get("calendar_button_scale"), DEFAULT_UI_TUNING["calendar_button_scale"]),
        calendar_card_density=_to_float(ui.get("calendar_card_density"), DEFAULT_UI_TUNING["calendar_card_density"]),
    )

    return HubConfig(streaming=streaming, image_sizes=image_sizes, ui=ui_conf)


# -----------------------------------------------------------------------------
# [AUTH-1.0] TMDB auth handling
# -----------------------------------------------------------------------------
def get_tmdb_headers_and_params() -> Tuple[Dict[str, str], Dict[str, str]]:
    key = (os.getenv("API_TMDB_KEY") or "").strip()
    token = (os.getenv("API_TMDB_TOKEN") or "").strip()

    if key:
        # API key as query param
        return {}, {"api_key": key}

    if token:
        # Bearer token
        return {"Authorization": f"Bearer {token}"}, {}

    die("API_TMDB_KEY is required in env (or set API_TMDB_TOKEN).")
    return {}, {}  # unreachable


# -----------------------------------------------------------------------------
# [HTTP-1.0] Simple TMDB GET wrapper
# -----------------------------------------------------------------------------
def tmdb_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    headers, base_params = get_tmdb_headers_and_params()
    url = TMDB_API_BASE.rstrip("/") + "/" + path.lstrip("/")

    merged = {}
    merged.update(base_params)
    if params:
        merged.update(params)

    r = requests.get(url, headers=headers, params=merged, timeout=DEFAULT_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"TMDB {path} failed: {r.status_code} {r.text[:200]}")
    return r.json()


# -----------------------------------------------------------------------------
# [LIST-1.0] Input list parsing
# -----------------------------------------------------------------------------
_id_line_re = re.compile(r"^\s*#")
_tmdb_id_re = re.compile(r"(\d+)")


def read_list_ids(path: Path) -> List[int]:
    if not path.exists():
        die(f"Required list not found: {path.as_posix()}")
    ids: List[int] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or _id_line_re.match(line):
            continue
        m = _tmdb_id_re.search(line)
        if not m:
            continue
        ids.append(int(m.group(1)))
    # de-dupe preserve order
    seen = set()
    out = []
    for x in ids:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def read_list_ids_optional(path: Path) -> List[int]:
    if not path.exists():
        log(f"NOTE: Optional list missing (treated as empty): {path.name}")
        return []
    if path.stat().st_size == 0:
        return []
    return read_list_ids(path)


# -----------------------------------------------------------------------------
# [IMG-1.0] Local image caching (download missing only)
# -----------------------------------------------------------------------------
def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def tmdb_image_url(width: int, tmdb_path: Optional[str]) -> str:
    if not tmdb_path:
        return ""
    tmdb_path = tmdb_path.strip()
    if not tmdb_path:
        return ""
    if not tmdb_path.startswith("/"):
        tmdb_path = "/" + tmdb_path
    return f"{TMDB_IMAGE_BASE}w{width}{tmdb_path}"


def safe_filename_from_path(tmdb_path: str) -> str:
    # tmdb_path is like "/abc.jpg" -> "abc.jpg"
    return Path(tmdb_path).name


def download_missing(url: str, dest: Path) -> bool:
    """Return True if downloaded now, False if already existed."""
    if not url or not dest:
        return False
    if dest.exists() and dest.stat().st_size > 0:
        return False
    ensure_dir(dest.parent)
    r = requests.get(url, stream=True, timeout=DEFAULT_TIMEOUT)
    if r.status_code != 200:
        log(f"WARN: image download failed {r.status_code} {url}")
        return False
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    with tmp.open("wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 128):
            if chunk:
                f.write(chunk)
    if tmp.exists() and tmp.stat().st_size > 0:
        tmp.replace(dest)
        return True
    return False


def cache_image(category_rel: str, width: int, tmdb_path: Optional[str]) -> Tuple[str, str]:
    """
    Returns:
      (remote_url, local_rel_path)
    local_rel_path is repo-relative ("image/...") so UI can build correct URLs.
    """
    if not tmdb_path:
        return "", ""

    remote = tmdb_image_url(width, tmdb_path)
    if not remote:
        return "", ""

    filename = safe_filename_from_path(tmdb_path)
    local_rel = f"image/{category_rel}/{filename}"
    local_abs = REPO_ROOT / local_rel

    downloaded = download_missing(remote, local_abs)
    if downloaded:
        log(f"IMG: cached {local_rel}")

    return remote, local_rel


# -----------------------------------------------------------------------------
# [LINK-1.0] Streaming link builders (config-driven)
# -----------------------------------------------------------------------------
def join_base(base: str, *parts: Any) -> str:
    base = _norm_base(base)
    p = "/".join(str(x).strip("/") for x in parts if str(x).strip("/") != "")
    return base + p


def build_tv_links(cfg: HubConfig, tmdb_id: int, season: int, episode: int) -> Dict[str, str]:
    return {
        "vidsrc": join_base(cfg.streaming.vidsrc_tv, tmdb_id, season, episode),
        "videasy": join_base(cfg.streaming.videasy_tv, tmdb_id, season, episode),
    }


def build_movie_links(cfg: HubConfig, tmdb_id: int) -> Dict[str, str]:
    return {
        "vidsrc": join_base(cfg.streaming.vidsrc_movie, tmdb_id),
        "videasy": join_base(cfg.streaming.videasy_movie, tmdb_id),
    }


# -----------------------------------------------------------------------------
# [DATA-1.0] TMDB shape extraction
# -----------------------------------------------------------------------------
def fmt_air_date(d: Optional[str]) -> str:
    return (d or "").strip()


def parse_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def sort_key_date(s: str) -> Tuple[int, str]:
    # Empty goes last
    if not s:
        return (1, "")
    return (0, s)


# -----------------------------------------------------------------------------
# [DATA-2.0] Fetch TV show + seasons + episodes
# -----------------------------------------------------------------------------
def fetch_show_full(tmdb_id: int) -> Dict[str, Any]:
    # show details (append seasons)
    show = tmdb_get(f"/tv/{tmdb_id}", params={"language": "en-US"})
    return show


def fetch_season(tmdb_id: int, season_number: int) -> Dict[str, Any]:
    season = tmdb_get(f"/tv/{tmdb_id}/season/{season_number}", params={"language": "en-US"})
    return season


def build_show_record(cfg: HubConfig, show: Dict[str, Any]) -> Dict[str, Any]:
    show_id = parse_int(show.get("id"))
    name = show.get("name") or show.get("original_name") or ""
    status = show.get("status") or ""
    first_air_date = fmt_air_date(show.get("first_air_date"))
    last_air_date = fmt_air_date(show.get("last_air_date"))
    number_of_seasons = parse_int(show.get("number_of_seasons"))
    number_of_episodes = parse_int(show.get("number_of_episodes"))
    genres = [g.get("name") for g in (show.get("genres") or []) if g.get("name")]

    poster_path = show.get("poster_path")
    backdrop_path = show.get("backdrop_path")

    poster_url, local_poster = cache_image("shows/poster", cfg.image_sizes.show_width, poster_path)
    backdrop_url, local_backdrop = cache_image("shows/backdrop", cfg.image_sizes.backdrop_w, backdrop_path)

    rec = {
        "id": show_id,
        "name": name,
        "status": status,
        "first_air_date": first_air_date,
        "last_air_date": last_air_date,
        "number_of_seasons": number_of_seasons,
        "number_of_episodes": number_of_episodes,
        "genres": genres,
        "poster_path": poster_path,
        "backdrop_path": backdrop_path,
        "poster_url": poster_url,
        "backdrop_url": backdrop_url,
        "local_poster_path": local_poster,
        "local_backdrop_path": local_backdrop,
        "seasons": [],
    }

    return rec


def build_season_record(cfg: HubConfig, show_id: int, season: Dict[str, Any]) -> Dict[str, Any]:
    season_number = parse_int(season.get("season_number"))
    name = season.get("name") or ""
    air_date = fmt_air_date(season.get("air_date"))
    poster_path = season.get("poster_path")

    poster_url, local_poster = cache_image("shows/seasons/poster", cfg.image_sizes.season_width, poster_path)

    return {
        "show_id": show_id,
        "season_number": season_number,
        "name": name,
        "air_date": air_date,
        "poster_path": poster_path,
        "poster_url": poster_url,
        "local_poster_path": local_poster,
        "episodes": [],
    }


def build_episode_record(cfg: HubConfig, show_id: int, season_number: int, ep: Dict[str, Any]) -> Dict[str, Any]:
    ep_number = parse_int(ep.get("episode_number"))
    name = ep.get("name") or ""
    air_date = fmt_air_date(ep.get("air_date"))
    still_path = ep.get("still_path")

    still_url, local_still = cache_image("shows/episodes/stills", cfg.image_sizes.episode_still_w, still_path)

    links = build_tv_links(cfg, show_id, season_number, ep_number)

    return {
        "show_id": show_id,
        "season_number": season_number,
        "episode_number": ep_number,
        "name": name,
        "air_date": air_date,
        "still_path": still_path,
        "still_url": still_url,
        "local_still_path": local_still,
        "links": links,
    }


# -----------------------------------------------------------------------------
# [DATA-3.0] Fetch Movies
# -----------------------------------------------------------------------------
def fetch_movie(tmdb_id: int) -> Dict[str, Any]:
    movie = tmdb_get(f"/movie/{tmdb_id}", params={"language": "en-US"})
    return movie


def build_movie_record(cfg: HubConfig, movie: Dict[str, Any]) -> Dict[str, Any]:
    movie_id = parse_int(movie.get("id"))
    title = movie.get("title") or movie.get("original_title") or ""
    release_date = fmt_air_date(movie.get("release_date"))
    status = movie.get("status") or ""
    genres = [g.get("name") for g in (movie.get("genres") or []) if g.get("name")]

    poster_path = movie.get("poster_path")
    backdrop_path = movie.get("backdrop_path")

    poster_url, local_poster = cache_image("movies/poster", cfg.image_sizes.movie_width, poster_path)
    backdrop_url, local_backdrop = cache_image("movies/backdrop", cfg.image_sizes.backdrop_w, backdrop_path)

    links = build_movie_links(cfg, movie_id)

    return {
        "id": movie_id,
        "title": title,
        "release_date": release_date,
        "status": status,
        "genres": genres,
        "poster_path": poster_path,
        "backdrop_path": backdrop_path,
        "poster_url": poster_url,
        "backdrop_url": backdrop_url,
        "local_poster_path": local_poster,
        "local_backdrop_path": local_backdrop,
        "links": links,
    }


# -----------------------------------------------------------------------------
# [OUT-1.0] Flatten for calendar view (episodes + movie releases)
# -----------------------------------------------------------------------------
def build_calendar_items(shows: List[Dict[str, Any]], movies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    for s in shows:
        show_name = s.get("name") or ""
        show_id = s.get("id")
        for season in s.get("seasons") or []:
            for ep in season.get("episodes") or []:
                items.append(
                    {
                        "type": "episode",
                        "air_date": ep.get("air_date") or "",
                        "show_id": show_id,
                        "show_name": show_name,
                        "season_number": ep.get("season_number"),
                        "episode_number": ep.get("episode_number"),
                        "episode_name": ep.get("name") or "",
                        "still_path": ep.get("still_path"),
                        "still_url": ep.get("still_url"),
                        "local_still_path": ep.get("local_still_path"),
                        "links": ep.get("links") or {},
                    }
                )

    for m in movies:
        items.append(
            {
                "type": "movie",
                "release_date": m.get("release_date") or "",
                "id": m.get("id"),
                "title": m.get("title") or "",
                "poster_path": m.get("poster_path"),
                "poster_url": m.get("poster_url"),
                "local_poster_path": m.get("local_poster_path"),
                "links": m.get("links") or {},
            }
        )

    # Sort by date (episodes use air_date, movies use release_date)
    def _item_date(it: Dict[str, Any]) -> str:
        return (it.get("air_date") or it.get("release_date") or "").strip()

    items.sort(key=lambda x: sort_key_date(_item_date(x)))
    return items


# -----------------------------------------------------------------------------
# [MAIN-1.0] Execution
# -----------------------------------------------------------------------------
def main() -> int:
    t0 = time.time()

    cfg = load_config()

    # Ensure core folders
    ensure_dir(DATA_DIR)
    ensure_dir(IMAGE_DIR)

    # Read lists
    tv_ids = read_list_ids(TV_LIST_PATH)
    movie_ids = read_list_ids(MOVIES_LIST_PATH)
    livetv_ids = read_list_ids_optional(LIVETV_LIST_PATH)

    log(f"Lists: TV={len(tv_ids)} Movies={len(movie_ids)} LiveTV={len(livetv_ids)}")

    shows_out: List[Dict[str, Any]] = []
    movies_out: List[Dict[str, Any]] = []
    errors: List[str] = []

    # TV shows
    for i, sid in enumerate(tv_ids, 1):
        try:
            show = fetch_show_full(sid)
            srec = build_show_record(cfg, show)

            # Iterate seasons (exclude season 0 unless explicitly present in data)
            seasons = show.get("seasons") or []
            for s in seasons:
                sn = parse_int(s.get("season_number"))
                if sn < 0:
                    continue

                # Fetch season details + episodes
                sfull = fetch_season(sid, sn)
                srec_season = build_season_record(cfg, sid, sfull)

                for ep in (sfull.get("episodes") or []):
                    erec = build_episode_record(cfg, sid, sn, ep)
                    srec_season["episodes"].append(erec)

                # Keep season order
                srec_season["episodes"].sort(key=lambda e: (parse_int(e.get("season_number")), parse_int(e.get("episode_number"))))
                srec["seasons"].append(srec_season)

            # Keep season order
            srec["seasons"].sort(key=lambda x: parse_int(x.get("season_number")))
            shows_out.append(srec)

            if i % 5 == 0 or i == len(tv_ids):
                log(f"TV: {i}/{len(tv_ids)} ok")

        except Exception as e:
            msg = f"TV {sid} failed: {e}"
            log("WARN: " + msg)
            errors.append(msg)

    # Movies
    for i, mid in enumerate(movie_ids, 1):
        try:
            movie = fetch_movie(mid)
            mrec = build_movie_record(cfg, movie)
            movies_out.append(mrec)

            if i % 10 == 0 or i == len(movie_ids):
                log(f"Movies: {i}/{len(movie_ids)} ok")

        except Exception as e:
            msg = f"Movie {mid} failed: {e}"
            log("WARN: " + msg)
            errors.append(msg)

    # Build calendar items
    calendar_items = build_calendar_items(shows_out, movies_out)

    # Output payload
    built_at = _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "meta": {
            "built_at": built_at,
            "tv_count": len(shows_out),
            "movie_count": len(movies_out),
            "livetv_count": len(livetv_ids),
            "errors_count": len(errors),
            "fetch_tmdb_version": "v2.6.2",
            "build_tag": "v14.01.04",
        },
        "config_echo": {
            "streaming_services": dataclasses.asdict(cfg.streaming),
            "image_sizes": dataclasses.asdict(cfg.image_sizes),
            "ui_tuning": dataclasses.asdict(cfg.ui),
        },
        "tv": shows_out,
        "movies": movies_out,
        "calendar": calendar_items,
        "errors": errors,
    }

    # Write outputs (atomic; never leave blank/partial data.json)
    write_json_atomic(DATA_JSON_PATH, payload)
    LAST_REFRESH_PATH.write_text(built_at + "\n", encoding="utf-8")

    dt = time.time() - t0
    log(f"DONE: wrote {DATA_JSON_PATH.as_posix()} ({dt:.1f}s)")

    # Non-zero exit if EVERYTHING failed (protect against publishing an empty hub)
    if len(shows_out) == 0 and len(movies_out) == 0:
        die("No TV or Movies produced. Refusing to publish empty data.json.", 2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
