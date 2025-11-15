#!/usr/bin/env python
# File: scripts/fetch_tmdb.py
# Project: my_TV_Movie
# Version: v2.4.0 (2025-11-14 23:10 EST)
#
# Purpose:
#   - Read tv_list.txt and movies_list.txt
#   - Fetch core metadata from TMDB (shows, seasons, episodes, movies)
#   - Build data/data.json with:
#       shows[ { seasons[ { episodes[ { links: tmdb/vidsrc/videasy } ] } ] } ]
#       movies[ { links: tmdb/vidsrc/videasy } ]
#       meta: { shows, movies, livetv, built_at }
#
# Notes:
#   - Requires env: API_TMDB_KEY
#   - Optional: API_TMDB_TOKEN (v4 bearer) – unused here but left for future
#   - VidSrc/Videasy URL patterns are centralized here so the UI only reads links.*

import os
import sys
import json
import time
import pathlib
import logging
from typing import Dict, Any, List, Optional

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ROOT = pathlib.Path(__file__).resolve().parents[1]
TV_LIST_PATH = ROOT / "tv_list.txt"
MOVIES_LIST_PATH = ROOT / "movies_list.txt"
DATA_DIR = ROOT / "data"
DATA_JSON_PATH = DATA_DIR / "data.json"

TMDB_API_KEY = os.environ.get("API_TMDB_KEY")
if not TMDB_API_KEY:
    print("[fetch_tmdb] ERROR: API_TMDB_KEY is required in env.", file=sys.stderr)
    sys.exit(1)

TMDB_BASE = "https://api.themoviedb.org/3"

# --- WATCH URL BASES (edit these if your hosting changes) -------------------
TMDB_TV_URL = "https://www.themoviedb.org/tv/{tmdb_id}"
TMDB_EP_URL = "https://www.themoviedb.org/tv/{tmdb_id}/season/{season_number}/episode/{episode_number}"
TMDB_MOVIE_URL = "https://www.themoviedb.org/movie/{tmdb_id}"

VIDSRC_TV_EP_BASE = "https://vidsrc.to/embed/tv/{tmdb_id}/{season_number}/{episode_number}"
VIDSRC_MOVIE_BASE = "https://vidsrc.to/embed/movie/{tmdb_id}"

VIDEASY_TV_EP_BASE = "https://videasy.org/embed/tv/{tmdb_id}/{season_number}/{episode_number}"
VIDEASY_MOVIE_BASE = "https://videasy.org/embed/movie/{tmdb_id}"
# ---------------------------------------------------------------------------


logging.basicConfig(
    level=logging.INFO,
    format="[fetch_tmdb] %(levelname)s: %(message)s",
    stream=sys.stdout,
)

session = requests.Session()


def tmdb_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Thin wrapper around TMDB GET with simple retry."""
    url = f"{TMDB_BASE}{path}"
    if params is None:
        params = {}
    params.setdefault("api_key", TMDB_API_KEY)

    for attempt in range(3):
        try:
            r = session.get(url, params=params, timeout=15)
            if r.status_code == 404:
                logging.warning("TMDB 404: %s", url)
                return {}
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logging.warning("TMDB GET failed (%s) attempt %s/3", e, attempt + 1)
            time.sleep(1 + attempt)
    logging.error("TMDB GET hard-failed: %s", url)
    return {}


# ---------------------------------------------------------------------------
# Helpers: parsing tv_list.txt / movies_list.txt
# ---------------------------------------------------------------------------

def parse_tv_list(path: pathlib.Path) -> List[Dict[str, Any]]:
    """
    tv_list.txt format:
      # name | tmdb_show_id | season_spec | tvmaze_id(optional)

      Abbott Elementary|125935|5
      Abbott Elementary|125935|5|43354
      Only Murders in the Building|107113|5
      Stranger Things|66732|*
    """
    shows: List[Dict[str, Any]] = []
    if not path.exists():
        logging.warning("tv_list.txt missing at %s", path)
        return shows

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            logging.warning("Skipping tv_list line (too few parts): %r", line)
            continue
        name, tmdb_show_id, season_spec = parts[:3]
        tvmaze_id = parts[3] if len(parts) >= 4 and parts[3] else None
        try:
            tmdb_show_id_int = int(tmdb_show_id)
        except ValueError:
            logging.warning("Skipping tv_list line (non-numeric TMDB id): %r", line)
            continue

        shows.append(
            {
                "ref_name": name,
                "tmdb_id": tmdb_show_id_int,
                "season_spec": season_spec,
                "tvmaze_id": tvmaze_id,
            }
        )
    logging.info("Parsed %s TV lines from tv_list.txt", len(shows))
    return shows


def parse_movies_list(path: pathlib.Path) -> List[Dict[str, Any]]:
    """
    movies_list.txt format:
      # name | tmdb_movie_id

      28 Years Later|1100988
      Argylle|848538
    """
    movies: List[Dict[str, Any]] = []
    if not path.exists():
        logging.warning("movies_list.txt missing at %s", path)
        return movies

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            logging.warning("Skipping movies_list line (too few parts): %r", line)
            continue
        title, tmdb_movie_id = parts[:2]
        try:
            tmdb_movie_id_int = int(tmdb_movie_id)
        except ValueError:
            logging.warning("Skipping movies_list line (non-numeric TMDB id): %r", line)
            continue
        movies.append(
            {
                "ref_name": title,
                "tmdb_id": tmdb_movie_id_int,
            }
        )
    logging.info("Parsed %s movie lines from movies_list.txt", len(movies))
    return movies


def expand_season_spec(spec: str, show_json: Dict[str, Any]) -> List[int]:
    """
    season_spec:
      "5"       → [5]
      "1,2,5"   → [1, 2, 5]
      "*"       → all non-zero seasons from TMDB.
    """
    if spec.strip() == "*":
        seasons = []
        for s in show_json.get("seasons", []):
            num = s.get("season_number")
            if isinstance(num, int) and num != 0:
                seasons.append(num)
        return sorted(set(seasons))

    result: List[int] = []
    for part in spec.split(","):
        p = part.strip()
        if not p:
            continue
        try:
            result.append(int(p))
        except ValueError:
            logging.warning("Bad season spec piece: %r in %r", p, spec)
    return sorted(set(result))


# ---------------------------------------------------------------------------
# Link builders
# ---------------------------------------------------------------------------

def build_tv_show_links(tmdb_id: int) -> Dict[str, str]:
    return {
        "tmdb": TMDB_TV_URL.format(tmdb_id=tmdb_id),
        # Optional: add series-level VidSrc/Videasy if you ever want them.
    }


def build_tv_episode_links(tmdb_id: int, season_number: int, episode_number: int) -> Dict[str, str]:
    return {
        "tmdb": TMDB_EP_URL.format(
            tmdb_id=tmdb_id,
            season_number=season_number,
            episode_number=episode_number,
        ),
        "vidsrc": VIDSRC_TV_EP_BASE.format(
            tmdb_id=tmdb_id,
            season_number=season_number,
            episode_number=episode_number,
        ),
        "videasy": VIDEASY_TV_EP_BASE.format(
            tmdb_id=tmdb_id,
            season_number=season_number,
            episode_number=episode_number,
        ),
    }


def build_movie_links(tmdb_id: int) -> Dict[str, str]:
    return {
        "tmdb": TMDB_MOVIE_URL.format(tmdb_id=tmdb_id),
        "vidsrc": VIDSRC_MOVIE_BASE.format(tmdb_id=tmdb_id),
        "videasy": VIDEASY_MOVIE_BASE.format(tmdb_id=tmdb_id),
    }


# ---------------------------------------------------------------------------
# Builders: Shows / Movies
# ---------------------------------------------------------------------------

def build_show_entry(source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tmdb_id = source["tmdb_id"]
    ref_name = source["ref_name"]
    logging.info("Show: %s [%s]", ref_name, tmdb_id)

    show_json = tmdb_get(f"/tv/{tmdb_id}")
    if not show_json:
        return None

    # Determine which seasons to include
    seasons_numbers = expand_season_spec(source["season_spec"], show_json)

    seasons_out: List[Dict[str, Any]] = []
    for sn in seasons_numbers:
        logging.info("  Season %s", sn)
        season_json = tmdb_get(f"/tv/{tmdb_id}/season/{sn}")
        if not season_json:
            continue

        episodes_out: List[Dict[str, Any]] = []
        for ep in season_json.get("episodes", []):
            ep_num = ep.get("episode_number")
            if not isinstance(ep_num, int):
                continue
            ep_entry = {
                "episode_number": ep_num,
                "name": ep.get("name") or "",
                "air_date": ep.get("air_date"),
                "overview": ep.get("overview") or "",
                "runtime": ep.get("runtime"),  # may be None
                "links": build_tv_episode_links(tmdb_id, sn, ep_num),
            }
            episodes_out.append(ep_entry)

        seasons_out.append(
            {
                "season_number": sn,
                "name": season_json.get("name") or f"Season {sn}",
                "air_date": season_json.get("air_date"),
                "episode_count": len(episodes_out),
                "overview": season_json.get("overview") or "",
                "episodes": episodes_out,
            }
        )

    genres = [g.get("name") for g in show_json.get("genres", []) if g.get("name")]
    networks = [n.get("name") for n in show_json.get("networks", []) if n.get("name")]

    return {
        "ref_name": ref_name,
        "show_id": show_json.get("id"),
        "tmdb_id": tmdb_id,
        "name": show_json.get("name") or ref_name,
        "poster_path": show_json.get("poster_path"),
        "status": show_json.get("status"),
        "first_air_date": show_json.get("first_air_date"),
        "genres": genres,
        "overview": show_json.get("overview") or "",
        "networks": networks,
        "links": build_tv_show_links(tmdb_id),
        "seasons": seasons_out,
    }


def build_movie_entry(source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tmdb_id = source["tmdb_id"]
    ref_name = source["ref_name"]
    logging.info("Movie: %s [%s]", ref_name, tmdb_id)

    movie_json = tmdb_get(f"/movie/{tmdb_id}")
    if not movie_json:
        return None

    genres = [g.get("name") for g in movie_json.get("genres", []) if g.get("name")]
    coll = movie_json.get("belongs_to_collection") or {}
    belongs = None
    if isinstance(coll, dict) and coll.get("id"):
        belongs = {
            "id": coll.get("id"),
            "name": coll.get("name"),
            "poster_path": coll.get("poster_path"),
            "backdrop_path": coll.get("backdrop_path"),
        }

    return {
        "ref_name": ref_name,
        "movie_id": movie_json.get("id"),
        "tmdb_id": tmdb_id,
        "title": movie_json.get("title") or ref_name,
        "poster_path": movie_json.get("poster_path"),
        "release_date": movie_json.get("release_date"),
        "status": movie_json.get("status"),
        "runtime": movie_json.get("runtime"),
        "overview": movie_json.get("overview") or "",
        "genres": genres,
        "belongs_to_collection": belongs,
        "links": build_movie_links(tmdb_id),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    raw_tv = parse_tv_list(TV_LIST_PATH)
    raw_movies = parse_movies_list(MOVIES_LIST_PATH)

    shows_out: List[Dict[str, Any]] = []
    for s in raw_tv:
        entry = build_show_entry(s)
        if entry:
            shows_out.append(entry)

    movies_out: List[Dict[str, Any]] = []
    for m in raw_movies:
        entry = build_movie_entry(m)
        if entry:
            movies_out.append(entry)

    data: Dict[str, Any] = {
        "shows": shows_out,
        "movies": movies_out,
        "meta": {
            "shows": len(shows_out),
            "movies": len(movies_out),
            "livetv": 0,
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }

    DATA_JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logging.info("Wrote %s (shows=%s movies=%s)", DATA_JSON_PATH, len(shows_out), len(movies_out))


if __name__ == "__main__":
    main()
