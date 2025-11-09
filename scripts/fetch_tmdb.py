#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: scripts/fetch_tmdb.py
Project: my_TV_Movie
Version: v2.3.0 (2025-11-10)

Purpose:
    Build data/data.json from:
      - tv_list.txt
      - movies_list.txt

    For each TV show:
      - Load core TMDB details.
      - Load requested seasons and episodes.
      - Attach per-episode runtime when available.
      - Fallback: use show's episode_run_time[0] if episode runtime missing.

    For each Movie:
      - Load TMDB details with runtime, genres, status, release_date.
      - Include belongs_to_collection if present.

Output JSON shape (consumed by web/index.html >= v2.8.06):

{
  "generated_at": "2025-11-10T03:12:45Z",
  "shows": [
    {
      "name": "...",
      "show_id": 125935,
      "overview": "...",
      "status": "Returning Series",
      "genres": ["Comedy"],
      "poster_path": "/path.jpg",
      "networks": ["ABC"],
      "links": {
        "tmdb": "https://www.themoviedb.org/tv/125935"
      },
      "seasons": [
        {
          "season_number": 5,
          "name": "Season 5",
          "overview": "...",
          "episodes": [
            {
              "episode_number": 1,
              "name": "...",
              "overview": "...",
              "air_date": "2025-10-01",
              "runtime": 22
            },
            ...
          ]
        }
      ]
    }
  ],
  "movies": [
    {
      "name": "Dune: Part Two",
      "movie_id": 693134,
      "overview": "...",
      "status": "Released",
      "genres": ["Science Fiction"],
      "poster_path": "/path.jpg",
      "release_date": "2024-02-28",
      "runtime": 166,
      "belongs_to_collection": {
        "id": 726871,
        "name": "Dune Collection"
      }
    }
  ],
  "live_tv": [],
  "meta": {
    "shows": 34,
    "movies": 47,
    "live_tv": 0
  }
}

Requirements:
    - API_TMDB_KEY in environment (GitHub Secret recommended)
    - requests (via requirements.txt)

Notes:
    - Gracefully skips bad IDs.
    - Logs minimal info to stdout for Actions debugging.
"""

import os
import sys
import json
import time
import pathlib
import traceback
from typing import Dict, Any, List, Optional

import requests


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ROOT = pathlib.Path(__file__).resolve().parents[1]
TV_LIST = ROOT / "tv_list.txt"
MOVIES_LIST = ROOT / "movies_list.txt"
DATA_DIR = ROOT / "data"
DATA_JSON = DATA_DIR / "data.json"

TMDB_API_KEY = os.getenv("API_TMDB_KEY")
TMDB_BASE = "https://api.themoviedb.org/3"

SESSION = requests.Session()
SESSION.params = {"api_key": TMDB_API_KEY}
SESSION.headers.update({"Accept": "application/json"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def tmdb_get(path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    url = f"{TMDB_BASE}{path}"
    try:
        resp = SESSION.get(url, params=params or {}, timeout=15)
        if resp.status_code == 404:
            log(f"[TMDB] 404 for {path}")
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log(f"[TMDB] ERROR {path}: {e}")
        return None


def safe_int(val: str) -> Optional[int]:
    try:
        return int(val.strip())
    except Exception:
        return None


def parse_tv_list(path: pathlib.Path) -> List[Dict[str, Any]]:
    """
    tv_list.txt format:
      name|tmdb_show_id|season_spec|tvmaze_id(optional)

    season_spec:
      *      -> all seasons from TMDB
      "5"    -> only season 5
      "1,2,5"-> seasons 1,2,5
    """
    shows = []
    if not path.exists():
        log(f"[TV] tv_list.txt not found at {path}")
        return shows

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue
        name, show_id_str = parts[0], parts[1]
        show_id = safe_int(show_id_str)
        if not show_id:
            log(f"[TV] skip invalid show id line: {line}")
            continue

        season_spec = parts[2].strip() if len(parts) >= 3 and parts[2].strip() else "*"
        tvmaze_id = parts[3].strip() if len(parts) >= 4 and parts[3].strip() else None

        shows.append({
            "name_hint": name,
            "show_id": show_id,
            "season_spec": season_spec,
            "tvmaze_id": tvmaze_id,
        })

    log(f"[TV] Parsed {len(shows)} tv_list entries")
    return shows


def parse_movies_list(path: pathlib.Path) -> List[Dict[str, Any]]:
    """
    movies_list.txt format:
      name|tmdb_movie_id
    """
    movies = []
    if not path.exists():
        log(f"[MOVIES] movies_list.txt not found at {path}")
        return movies

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue
        name, mid_str = parts[0], parts[1]
        mid = safe_int(mid_str)
        if not mid:
            log(f"[MOVIES] skip invalid movie id line: {line}")
            continue

        movies.append({
            "name_hint": name,
            "movie_id": mid,
        })

    log(f"[MOVIES] Parsed {len(movies)} movies_list entries")
    return movies


def expand_season_spec(spec: str, all_seasons: List[int]) -> List[int]:
    spec = spec.strip()
    if spec == "*" or not spec:
        return sorted(all_seasons)
    result = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        num = safe_int(part)
        if num:
            result.add(num)
    out = sorted(s for s in result if s in all_seasons)
    return out or sorted(all_seasons)


# ---------------------------------------------------------------------------
# TV Shows
# ---------------------------------------------------------------------------

def fetch_show_core(show_id: int) -> Optional[Dict[str, Any]]:
    # append_to_response used lightly to avoid huge payloads
    data = tmdb_get(f"/tv/{show_id}", params={"append_to_response": "content_ratings"})
    if not data:
        return None

    show = {
        "show_id": show_id,
        "name": data.get("name") or data.get("original_name"),
        "overview": data.get("overview") or "",
        "status": data.get("status") or "",
        "genres": [g["name"] for g in data.get("genres", []) if g.get("name")],
        "poster_path": data.get("poster_path"),
        "networks": [n["name"] for n in data.get("networks", []) if n.get("name")],
        "episode_run_time": data.get("episode_run_time") or [],
        "seasons_raw": data.get("seasons", []),
        "links": {
            "tmdb": f"https://www.themoviedb.org/tv/{show_id}"
        },
    }
    return show


def fetch_show_season(show_id: int, season_number: int) -> Optional[Dict[str, Any]]:
    data = tmdb_get(f"/tv/{show_id}/season/{season_number}")
    if not data:
        return None

    season = {
        "season_number": data.get("season_number", season_number),
        "name": data.get("name") or f"Season {season_number}",
        "overview": data.get("overview") or "",
        "episodes": []
    }

    for ep in data.get("episodes", []):
        ep_num = ep.get("episode_number")
        if ep_num is None:
            continue
        season["episodes"].append({
            "episode_number": ep_num,
            "name": ep.get("name") or "",
            "overview": ep.get("overview") or "",
            "air_date": ep.get("air_date") or None,
            # TMDB may have per-episode runtime (newer field) or not; keep as-is.
            # frontend will also fall back to show.episode_run_time[0] if missing.
            "runtime": ep.get("runtime") or ep.get("episode_runtime") or None,
        })

    return season


def build_shows(tv_specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    shows: List[Dict[str, Any]] = []

    for spec in tv_specs:
        show_id = spec["show_id"]
        season_spec = spec["season_spec"]
        log(f"[TV] Fetch show {show_id} (spec: {season_spec})")

        core = fetch_show_core(show_id)
        if not core:
          continue

        # Determine available seasons from core.seasons_raw
        all_season_nums = sorted(
            s["season_number"]
            for s in core.get("seasons_raw", [])
            if isinstance(s.get("season_number"), int) and s["season_number"] > 0
        )
        wanted = expand_season_spec(season_spec, all_season_nums)

        seasons: List[Dict[str, Any]] = []
        for snum in wanted:
            log(f"[TV]  Season {show_id}/{snum}")
            sdata = fetch_show_season(show_id, snum)
            if not sdata:
                continue

            # Backfill episode runtime from show-level value if missing
            show_level_rt = None
            if core.get("episode_run_time"):
                show_level_rt = core["episode_run_time"][0]

            if show_level_rt:
                for ep in sdata["episodes"]:
                    if not ep.get("runtime"):
                        ep["runtime"] = show_level_rt

            seasons.append(sdata)
            time.sleep(0.15)  # tiny delay to be polite

        out = {
            "show_id": core["show_id"],
            "name": core["name"],
            "overview": core["overview"],
            "status": core["status"],
            "genres": core["genres"],
            "poster_path": core["poster_path"],
            "networks": core["networks"],
            "links": core["links"],
            "seasons": seasons,
        }
        shows.append(out)
        time.sleep(0.15)

    log(f"[TV] Built {len(shows)} shows with seasons/episodes")
    return shows


# ---------------------------------------------------------------------------
# Movies
# ---------------------------------------------------------------------------

def fetch_movie(movie_id: int) -> Optional[Dict[str, Any]]:
    data = tmdb_get(f"/movie/{movie_id}", params={"append_to_response": "release_dates"})
    if not data:
        return None

    movie = {
        "movie_id": movie_id,
        "name": data.get("title") or data.get("original_title"),
        "overview": data.get("overview") or "",
        "status": data.get("status") or "",
        "genres": [g["name"] for g in data.get("genres", []) if g.get("name")],
        "poster_path": data.get("poster_path"),
        "release_date": data.get("release_date") or None,
        "runtime": data.get("runtime") or None,
        "links": {
            "tmdb": f"https://www.themoviedb.org/movie/{movie_id}"
        },
        "belongs_to_collection": None
    }

    coll = data.get("belongs_to_collection")
    if isinstance(coll, dict) and coll.get("id") and coll.get("name"):
        movie["belongs_to_collection"] = {
            "id": coll["id"],
            "name": coll["name"],
        }

    return movie


def build_movies(movie_specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    movies: List[Dict[str, Any]] = []

    for spec in movie_specs:
        mid = spec["movie_id"]
        log(f"[MOVIES] Fetch movie {mid}")
        mv = fetch_movie(mid)
        if not mv:
            continue
        movies.append(mv)
        time.sleep(0.15)

    log(f"[MOVIES] Built {len(movies)} movies")
    return movies


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if not TMDB_API_KEY:
        log("[ERROR] API_TMDB_KEY not set.")
        return 1

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        tv_specs = parse_tv_list(TV_LIST)
        movie_specs = parse_movies_list(MOVIES_LIST)

        shows = build_shows(tv_specs)
        movies = build_movies(movie_specs)

        # Keep live_tv if another script generates it; don't nuke it here.
        existing_live_tv = []
        if DATA_JSON.exists():
            try:
                old = json.loads(DATA_JSON.read_text(encoding="utf-8"))
                if isinstance(old, dict) and isinstance(old.get("live_tv"), list):
                    existing_live_tv = old["live_tv"]
            except Exception:
                existing_live_tv = []

        out = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "shows": shows,
            "movies": movies,
            "live_tv": existing_live_tv,
            "meta": {
                "shows": len(shows),
                "movies": len(movies),
                "live_tv": len(existing_live_tv),
            }
        }

        DATA_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"[OK] Wrote {DATA_JSON} (shows={len(shows)}, movies={len(movies)}, live_tv={len(existing_live_tv)})")
        return 0

    except Exception as e:
        log("[FATAL] Exception in fetch_tmdb.py")
        log(str(e))
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
