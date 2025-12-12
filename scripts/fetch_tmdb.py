#!/usr/bin/env python
# File: scripts/fetch_tmdb.py
# Project: my_TV_Movie
# Version: v2.5.0 (2025-12-12 17:00 EST)
#
# Purpose:
#   - Read tv_list.txt and movies_list.txt
#   - Fetch core metadata from TMDB (shows, seasons, episodes, movies)
#   - Build data/data.json with:
#       shows[ { seasons[ { episodes[...] } ] } ]
#       movies[ ... ]
#
# Coding standards:
#   - Whole-file replacement (no snippets)
#   - Section numbering for “surgical replace” edits in the future
#   - Defensive handling (skip/continue on non-critical fetch failures)
#   - Deterministic outputs where possible
#
# NOTE:
#   This script runs on GitHub Actions (Linux). Your local Windows path is not used on Actions.
#   Repo-relative paths are the source of truth (ROOT = repo root).

from __future__ import annotations

import os
import sys
import json
import time
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# [PATH-1.0] Repo root + canonical file paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]  # .../my_TV_Movie/
TV_LIST_PATH = ROOT / "tv_list.txt"
MOVIES_LIST_PATH = ROOT / "movies_list.txt"

DATA_DIR = ROOT / "data"
DATA_JSON_PATH = DATA_DIR / "data.json"

# ---------------------------------------------------------------------------
# [ENV-1.1] Required environment variables
# ---------------------------------------------------------------------------

API_TMDB_KEY = os.getenv("API_TMDB_KEY", "").strip()

# ---------------------------------------------------------------------------
# [TMDB-1.2] TMDB endpoints + image bases
# ---------------------------------------------------------------------------

TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_ORIGINAL = "https://image.tmdb.org/t/p/original"
TMDB_IMAGE_BASE_W185 = "https://image.tmdb.org/t/p/w185"
TMDB_IMAGE_BASE_W300 = "https://image.tmdb.org/t/p/w300"

# ---------------------------------------------------------------------------
# [LINK-2.0] Streaming + info URL templates (DEFAULTS)
#
# IMPORTANT:
#   User-confirmed bases:
#     TV episode:
#       - VidSrc:  https://vidsrc.net/embed/tv/{tmdb_id}/{season_number}/{episode_number}
#       - VidEasy: https://player.videasy.net/tv/{tmdb_id}/{season_number}/{episode_number}
#     Movie:
#       - VidSrc:  https://vidsrc.net/embed/movie/{tmdb_id}
#       - VidEasy: https://player.videasy.net/movie/{tmdb_id}
# ---------------------------------------------------------------------------

TMDB_TV_EP_URL = "https://www.themoviedb.org/tv/{tmdb_id}/season/{season_number}/episode/{episode_number}"
TMDB_MOVIE_URL = "https://www.themoviedb.org/movie/{tmdb_id}"

VIDSRC_TV_EP_BASE = "https://vidsrc.net/embed/tv/{tmdb_id}/{season_number}/{episode_number}"
VIDSRC_MOVIE_BASE = "https://vidsrc.net/embed/movie/{tmdb_id}"

VIDEASY_TV_EP_BASE = "https://player.videasy.net/tv/{tmdb_id}/{season_number}/{episode_number}"
VIDEASY_MOVIE_BASE = "https://player.videasy.net/movie/{tmdb_id}"

# ---------------------------------------------------------------------------
# [CFG-2.1] Optional runtime config override (web/config.json)
#
# Goal:
#   - Allow base streaming URL patterns to be changed WITHOUT editing this script.
#   - If web/config.json exists and contains known keys, override the defaults above.
#
# Expected JSON shape (minimal):
# {
#   "streaming": {
#     "vidsrc":  {
#       "tv_episode_base": "https://vidsrc.net/embed/tv/{tmdb_id}/{season_number}/{episode_number}",
#       "movie_base":      "https://vidsrc.net/embed/movie/{tmdb_id}"
#     },
#     "videasy": {
#       "tv_episode_base": "https://player.videasy.net/tv/{tmdb_id}/{season_number}/{episode_number}",
#       "movie_base":      "https://player.videasy.net/movie/{tmdb_id}"
#     }
#   }
# }
#
# Notes:
#   - This is a STATIC GitHub Pages project; config.json is committed to the repo.
#   - The UI can also read the same config.json for runtime link building.
# ---------------------------------------------------------------------------

def try_load_repo_config() -> Dict[str, Any]:
    cfg_path = ROOT / "web" / "config.json"
    if not cfg_path.exists():
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception as e:
        logging.warning("config.json exists but could not be parsed: %s", e)
        return {}

def apply_config_overrides(cfg: Dict[str, Any]) -> None:
    global VIDSRC_TV_EP_BASE, VIDSRC_MOVIE_BASE, VIDEASY_TV_EP_BASE, VIDEASY_MOVIE_BASE

    streaming = (cfg or {}).get("streaming") or {}
    vidsrc = streaming.get("vidsrc") or {}
    videasy = streaming.get("videasy") or {}

    VIDSRC_TV_EP_BASE = vidsrc.get("tv_episode_base") or VIDSRC_TV_EP_BASE
    VIDSRC_MOVIE_BASE = vidsrc.get("movie_base") or VIDSRC_MOVIE_BASE

    VIDEASY_TV_EP_BASE = videasy.get("tv_episode_base") or VIDEASY_TV_EP_BASE
    VIDEASY_MOVIE_BASE = videasy.get("movie_base") or VIDEASY_MOVIE_BASE

# Apply overrides early (no-op if no config.json)
apply_config_overrides(try_load_repo_config())

# ---------------------------------------------------------------------------
# [LOG-3.0] Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

# ---------------------------------------------------------------------------
# [HTTP-3.1] Requests session + helpers
# ---------------------------------------------------------------------------

SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json"})

def tmdb_get(path: str, params: Optional[Dict[str, Any]] = None, retries: int = 3, sleep_s: float = 0.6) -> Dict[str, Any]:
    """
    [HTTP-3.1.1] TMDB GET wrapper with retry
    """
    if params is None:
        params = {}
    params = dict(params)
    params["api_key"] = API_TMDB_KEY

    url = f"{TMDB_API_BASE}{path}"

    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            r = SESSION.get(url, params=params, timeout=30)
            if r.status_code >= 400:
                raise RuntimeError(f"TMDB {r.status_code}: {r.text[:200]}")
            return r.json()
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(sleep_s)
            else:
                raise
    raise last_err or RuntimeError("tmdb_get failed with unknown error")

# ---------------------------------------------------------------------------
# [MODEL-4.0] Data structures
# ---------------------------------------------------------------------------

@dataclass
class TvListItem:
    ref_name: str
    tmdb_id: int

@dataclass
class MovieListItem:
    ref_name: str
    tmdb_id: int

# ---------------------------------------------------------------------------
# [PARSE-5.0] Input file parsing (tv_list.txt / movies_list.txt)
# ---------------------------------------------------------------------------

def parse_simple_list(path: Path) -> List[Tuple[str, int]]:
    """
    [PARSE-5.0.1] Parse lines like:
      Name | 12345
      Name\t12345
      12345 | Name
    Returns list of (ref_name, tmdb_id)
    """
    if not path.exists():
        logging.warning(f"[parse] Missing list file: {path}")
        return []

    out: List[Tuple[str, int]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        # Normalize separators
        parts = [p.strip() for p in line.replace("\t", "|").split("|") if p.strip()]
        if len(parts) < 2:
            continue

        # Try to find integer token
        tmdb_id: Optional[int] = None
        name_tokens: List[str] = []
        for p in parts:
            if tmdb_id is None:
                try:
                    tmdb_id = int(p)
                    continue
                except ValueError:
                    pass
            name_tokens.append(p)

        if tmdb_id is None:
            continue

        ref_name = " | ".join(name_tokens).strip() or f"tmdb:{tmdb_id}"
        out.append((ref_name, tmdb_id))

    # Deterministic order
    out.sort(key=lambda x: (x[0].lower(), x[1]))
    return out

def load_tv_list() -> List[TvListItem]:
    """
    [PARSE-5.1] Load TV list
    """
    items = parse_simple_list(TV_LIST_PATH)
    return [TvListItem(ref_name=n, tmdb_id=i) for (n, i) in items]

def load_movies_list() -> List[MovieListItem]:
    """
    [PARSE-5.2] Load Movies list
    """
    items = parse_simple_list(MOVIES_LIST_PATH)
    return [MovieListItem(ref_name=n, tmdb_id=i) for (n, i) in items]

# ---------------------------------------------------------------------------
# [LINK-6.0] Link builders (TMDB/VidSrc/VidEasy)
# ---------------------------------------------------------------------------

def build_tv_episode_links(tmdb_id: int, season_number: int, episode_number: int) -> Dict[str, str]:
    """
    [LINK-6.0.1] Build canonical episode links
    """
    return {
        "tmdb": TMDB_TV_EP_URL.format(tmdb_id=tmdb_id, season_number=season_number, episode_number=episode_number),
        "vidsrc": VIDSRC_TV_EP_BASE.format(tmdb_id=tmdb_id, season_number=season_number, episode_number=episode_number),
        "videasy": VIDEASY_TV_EP_BASE.format(tmdb_id=tmdb_id, season_number=season_number, episode_number=episode_number),
    }

def build_movie_links(tmdb_id: int) -> Dict[str, str]:
    """
    [LINK-6.0.2] Build canonical movie links
    """
    return {
        "tmdb": TMDB_MOVIE_URL.format(tmdb_id=tmdb_id),
        "vidsrc": VIDSRC_MOVIE_BASE.format(tmdb_id=tmdb_id),
        "videasy": VIDEASY_MOVIE_BASE.format(tmdb_id=tmdb_id),
    }

# ---------------------------------------------------------------------------
# [TMDB-7.0] Fetch show + seasons + episodes
# ---------------------------------------------------------------------------

def fetch_show_core(tmdb_id: int) -> Dict[str, Any]:
    """
    [TMDB-7.0.1] Fetch show core data
    """
    return tmdb_get(f"/tv/{tmdb_id}", params={"language": "en-US"})

def fetch_season(tmdb_id: int, season_number: int) -> Dict[str, Any]:
    """
    [TMDB-7.0.2] Fetch one season incl. episodes
    """
    return tmdb_get(f"/tv/{tmdb_id}/season/{season_number}", params={"language": "en-US"})

def build_show_object(item: TvListItem) -> Dict[str, Any]:
    """
    [TMDB-7.1] Build full show object for data.json
    """
    core = fetch_show_core(item.tmdb_id)

    seasons_out: List[Dict[str, Any]] = []

    for s in core.get("seasons", []) or []:
        season_number = s.get("season_number")
        if season_number is None:
            continue

        # Skip season 0 if you want specials excluded in calendar/UX
        # (keep it included in data for now; the UI can choose to hide it)
        season_data = fetch_season(item.tmdb_id, int(season_number))

        season_obj: Dict[str, Any] = {
            "season_number": int(season_number),
            "name": season_data.get("name") or s.get("name") or f"Season {season_number}",
            "overview": season_data.get("overview") or "",
            "air_date": season_data.get("air_date"),
            "episode_count": season_data.get("episodes") and len(season_data["episodes"]) or s.get("episode_count"),
            "poster_path": season_data.get("poster_path") or s.get("poster_path"),
            "episodes": [],
        }

        for ep in season_data.get("episodes", []) or []:
            ep_num = ep.get("episode_number")
            if ep_num is None:
                continue

            episode_obj = {
                "season_number": int(season_number),
                "episode_number": int(ep_num),
                "name": ep.get("name") or f"Episode {ep_num}",
                "air_date": ep.get("air_date"),
                "overview": ep.get("overview") or "",
                "runtime": ep.get("runtime"),
                "still_path": ep.get("still_path"),
                "links": build_tv_episode_links(item.tmdb_id, int(season_number), int(ep_num)),
            }

            season_obj["episodes"].append(episode_obj)

        seasons_out.append(season_obj)

    show_obj: Dict[str, Any] = {
        "ref_name": item.ref_name,
        "show_id": core.get("id"),
        "tmdb_id": core.get("id"),
        "name": core.get("name") or item.ref_name,
        "original_name": core.get("original_name"),
        "status": core.get("status"),
        "first_air_date": core.get("first_air_date"),
        "last_air_date": core.get("last_air_date"),
        "number_of_seasons": core.get("number_of_seasons"),
        "number_of_episodes": core.get("number_of_episodes"),
        "genres": [g.get("name") for g in (core.get("genres") or []) if g.get("name")],
        "networks": [n.get("name") for n in (core.get("networks") or []) if n.get("name")],
        "overview": core.get("overview") or "",
        "poster_path": core.get("poster_path"),
        "backdrop_path": core.get("backdrop_path"),
        "seasons": seasons_out,
    }

    return show_obj

# ---------------------------------------------------------------------------
# [TMDB-8.0] Fetch movies
# ---------------------------------------------------------------------------

def fetch_movie_core(tmdb_id: int) -> Dict[str, Any]:
    """
    [TMDB-8.0.1] Fetch movie core data
    """
    return tmdb_get(f"/movie/{tmdb_id}", params={"language": "en-US"})

def build_movie_object(item: MovieListItem) -> Dict[str, Any]:
    """
    [TMDB-8.1] Build movie object for data.json
    """
    core = fetch_movie_core(item.tmdb_id)

    movie_obj: Dict[str, Any] = {
        "ref_name": item.ref_name,
        "movie_id": core.get("id"),
        "tmdb_id": core.get("id"),
        "title": core.get("title") or item.ref_name,
        "original_title": core.get("original_title"),
        "release_date": core.get("release_date"),
        "runtime": core.get("runtime"),
        "status": core.get("status"),
        "genres": [g.get("name") for g in (core.get("genres") or []) if g.get("name")],
        "overview": core.get("overview") or "",
        "poster_path": core.get("poster_path"),
        "backdrop_path": core.get("backdrop_path"),
        "links": build_movie_links(item.tmdb_id),
    }

    return movie_obj

# ---------------------------------------------------------------------------
# [OUT-9.0] Write data/data.json
# ---------------------------------------------------------------------------

def utc_now_iso() -> str:
    """
    [OUT-9.0.1] Deterministic timestamp format for build metadata
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def write_data_json(payload: Dict[str, Any]) -> None:
    """
    [OUT-9.1] Write JSON with stable formatting
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

# ---------------------------------------------------------------------------
# [MAIN-10.0] Main pipeline
# ---------------------------------------------------------------------------

def main() -> int:
    """
    [MAIN-10.0.1] Entry point
    """
    if not API_TMDB_KEY:
        logging.error("[fetch_tmdb] ERROR: API_TMDB_KEY is required in env.")
        return 1

    logging.info("[fetch_tmdb] Starting build...")
    logging.info(f"[fetch_tmdb] ROOT={ROOT}")

    tv_items = load_tv_list()
    movie_items = load_movies_list()

    shows_out: List[Dict[str, Any]] = []
    movies_out: List[Dict[str, Any]] = []

    # [MAIN-10.1] TV shows
    for idx, item in enumerate(tv_items, start=1):
        try:
            logging.info(f"[fetch_tmdb] TV {idx}/{len(tv_items)}: {item.ref_name} ({item.tmdb_id})")
            shows_out.append(build_show_object(item))
        except Exception as e:
            logging.warning(f"[fetch_tmdb] WARN: failed show {item.tmdb_id}: {e}")

    # [MAIN-10.2] Movies
    for idx, item in enumerate(movie_items, start=1):
        try:
            logging.info(f"[fetch_tmdb] MOVIE {idx}/{len(movie_items)}: {item.ref_name} ({item.tmdb_id})")
            movies_out.append(build_movie_object(item))
        except Exception as e:
            logging.warning(f"[fetch_tmdb] WARN: failed movie {item.tmdb_id}: {e}")

    # [MAIN-10.3] Build payload
    payload: Dict[str, Any] = {
        "meta": {
            "version": "v2.5.0",
            "built_utc": utc_now_iso(),
            "counts": {
                "shows": len(shows_out),
                "movies": len(movies_out),
            },
            "streaming_templates": {
                "vidsrc_tv_episode": VIDSRC_TV_EP_BASE,
                "vidsrc_movie": VIDSRC_MOVIE_BASE,
                "videasy_tv_episode": VIDEASY_TV_EP_BASE,
                "videasy_movie": VIDEASY_MOVIE_BASE,
            },
        },
        "shows": shows_out,
        "movies": movies_out,
        "live_tv": [],
    }

    write_data_json(payload)

    logging.info("[fetch_tmdb] Build complete.")
    logging.info(f"[fetch_tmdb] Wrote: {DATA_JSON_PATH}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
