#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File: scripts/fetch_tmdb.py
Project: my_TV_Movie
Version: v2.3.1 (2025-11-11)

Purpose:
    Build data/data.json from:
      - tv_list.txt
      - movies_list.txt

Behavior:
    - Skips blank lines and lines starting with '#'.
    - Warns on malformed lines; continues.
    - Fetches from TMDB:
        * Shows + seasons + episodes (all, incl. TBA).
        * Movies (status, runtime, genres, collection).
    - Writes:
        data/data.json:
          {
            "generated_at": "...",
            "shows": [...],
            "movies": [...],
            "live_tv": [],
            "meta": { "shows": N, "movies": M, "live_tv": 0 }
          }
    - Fails (non-zero) if:
        * API_TMDB_KEY missing, OR
        * tv_list.txt has entries but 0 shows built, OR
        * movies_list.txt has entries but 0 movies built.

This prevents silent deploys with "Movies: 0" when input is non-empty.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import urllib.request
import urllib.parse
import urllib.error

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TV_LIST_PATH = BASE_DIR / "tv_list.txt"
MOVIES_LIST_PATH = BASE_DIR / "movies_list.txt"

TMDB_API_KEY = os.environ.get("API_TMDB_KEY")
TMDB_BASE = "https://api.themoviedb.org/3"


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def tmdb_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if not TMDB_API_KEY:
        print("FATAL: API_TMDB_KEY not set.", file=sys.stderr)
        sys.exit(1)

    q = {"api_key": TMDB_API_KEY}
    q.update(params or {})
    url = f"{TMDB_BASE}{path}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status != 200:
                raise RuntimeError(f"TMDB {path} status {resp.status}")
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"TMDB HTTPError {path}: {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"TMDB URLError {path}: {e.reason}") from e


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def load_tv_list() -> List[Dict[str, Any]]:
    shows = []
    if not TV_LIST_PATH.exists():
        print(f"INFO: {TV_LIST_PATH.name} not found, no shows requested.", file=sys.stderr)
        return shows

    with TV_LIST_PATH.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 2:
                print(f"WARNING: tv_list.txt line {lineno} malformed: {raw!r}", file=sys.stderr)
                continue

            name = parts[0]
            tmdb_id = parts[1]
            season_spec = parts[2] if len(parts) >= 3 and parts[2] else "*"
            tvmaze_id = parts[3] if len(parts) >= 4 and parts[3] else None

            if not tmdb_id.isdigit():
                print(f"WARNING: tv_list.txt line {lineno} non-numeric tmdb_id: {tmdb_id!r}", file=sys.stderr)
                continue

            shows.append({
                "name": name,
                "tmdb_id": int(tmdb_id),
                "season_spec": season_spec,
                "tvmaze_id": tvmaze_id
            })

    print(f"INFO: Loaded {len(shows)} TV entries from tv_list.txt", file=sys.stderr)
    return shows


def load_movies_list() -> List[Dict[str, Any]]:
    movies = []
    if not MOVIES_LIST_PATH.exists():
        print(f"INFO: {MOVIES_LIST_PATH.name} not found, no movies requested.", file=sys.stderr)
        return movies

    with MOVIES_LIST_PATH.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 2:
                print(f"WARNING: movies_list.txt line {lineno} malformed: {raw!r}", file=sys.stderr)
                continue

            name = parts[0]
            tmdb_id = parts[1]

            if not tmdb_id.isdigit():
                print(f"WARNING: movies_list.txt line {lineno} non-numeric tmdb_id: {tmdb_id!r}", file=sys.stderr)
                continue

            movies.append({
                "name": name,
                "tmdb_id": int(tmdb_id),
            })

    print(f"INFO: Loaded {len(movies)} movie entries from movies_list.txt", file=sys.stderr)
    return movies


def parse_season_spec(spec: str, all_seasons: List[int]) -> List[int]:
    spec = (spec or "*").strip()
    if spec in ("", "*"):
        return sorted(all_seasons)
    selected = set()
    for part in spec.split(","):
        p = part.strip()
        if not p:
            continue
        if p.isdigit():
            selected.add(int(p))
        else:
            print(f"WARNING: invalid season token in season_spec: {p!r}", file=sys.stderr)
    return sorted([s for s in all_seasons if s in selected]) if selected else sorted(all_seasons)


# ---------------------------------------------------------------------------
# Build shows
# ---------------------------------------------------------------------------

def build_show_entry(cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    show_id = cfg["tmdb_id"]

    try:
        info = tmdb_get(f"/tv/{show_id}", {"append_to_response": "networks"})
    except Exception as e:
        print(f"ERROR: Failed to fetch show {show_id}: {e}", file=sys.stderr)
        return None

    season_nums = [s["season_number"] for s in info.get("seasons", [])
                   if s.get("season_number") is not None]
    wanted = parse_season_spec(cfg.get("season_spec", "*"), season_nums)

    seasons_out: List[Dict[str, Any]] = []
    for sn in wanted:
        try:
          sdata = tmdb_get(f"/tv/{show_id}/season/{sn}", {})
        except Exception as e:
          print(f"ERROR: Failed to fetch S{sn} for show {show_id}: {e}", file=sys.stderr)
          continue

        episodes_out: List[Dict[str, Any]] = []
        for ep in sdata.get("episodes", []):
            episodes_out.append({
                "episode_number": ep.get("episode_number"),
                "name": ep.get("name") or "",
                "overview": ep.get("overview") or "",
                "air_date": ep.get("air_date") or None,
                "runtime": ep.get("runtime") or ep.get("episode_run_time") or None
            })

        seasons_out.append({
            "season_number": sn,
            "overview": sdata.get("overview") or "",
            "episodes": episodes_out
        })

    networks = [n.get("name") for n in (info.get("networks") or []) if n.get("name")]
    genres = [g.get("name") for g in (info.get("genres") or []) if g.get("name")]

    return {
        "show_id": show_id,
        "name": info.get("name") or cfg["name"],
        "overview": info.get("overview") or "",
        "poster_path": info.get("poster_path"),
        "status": info.get("status") or "",
        "genres": genres,
        "networks": networks,
        "tvmaze_id": cfg.get("tvmaze_id"),
        "seasons": seasons_out,
        "links": {
          "tmdb": f"https://www.themoviedb.org/tv/{show_id}"
        }
    }


def build_shows(tv_cfgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    shows_out: List[Dict[str, Any]] = []
    for cfg in tv_cfgs:
        entry = build_show_entry(cfg)
        if entry:
            shows_out.append(entry)
        time.sleep(0.2)
    print(f"INFO: Built {len(shows_out)} shows", file=sys.stderr)
    return shows_out


# ---------------------------------------------------------------------------
# Build movies
# ---------------------------------------------------------------------------

def build_movie_entry(cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    movie_id = cfg["tmdb_id"]

    try:
        info = tmdb_get(f"/movie/{movie_id}", {})
    except Exception as e:
        print(f"ERROR: Failed to fetch movie {movie_id}: {e}", file=sys.stderr)
        return None

    genres = [g.get("name") for g in (info.get("genres") or []) if g.get("name")]
    coll = info.get("belongs_to_collection") or None

    return {
        "movie_id": movie_id,
        "name": info.get("title") or cfg["name"],
        "overview": info.get("overview") or "",
        "poster_path": info.get("poster_path"),
        "release_date": info.get("release_date") or None,
        "runtime": info.get("runtime") or None,
        "status": info.get("status") or "",
        "genres": genres,
        "belongs_to_collection": (
            {"id": coll.get("id"), "name": coll.get("name")}
            if coll else None
        ),
    }


def build_movies(movies_cfgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    movies_out: List[Dict[str, Any]] = []
    for cfg in movies_cfgs:
        entry = build_movie_entry(cfg)
        if entry:
            movies_out.append(entry)
        time.sleep(0.2)
    print(f"INFO: Built {len(movies_out)} movies", file=sys.stderr)
    return movies_out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not TMDB_API_KEY:
        print("FATAL: API_TMDB_KEY is required.", file=sys.stderr)
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    tv_cfgs = load_tv_list()
    movies_cfgs = load_movies_list()

    shows = build_shows(tv_cfgs)
    movies = build_movies(movies_cfgs)

    # Hard guards: avoid silent "0" cases when lists are non-empty.
    if tv_cfgs and not shows:
        print("FATAL: tv_list.txt has entries but 0 shows were built.", file=sys.stderr)
        sys.exit(1)
    if movies_cfgs and not movies:
        print("FATAL: movies_list.txt has entries but 0 movies were built.", file=sys.stderr)
        sys.exit(1)

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "shows": shows,
        "movies": movies,
        "live_tv": [],
        "meta": {
            "shows": len(shows),
            "movies": len(movies),
            "live_tv": 0
        }
    }

    out_path = DATA_DIR / "data.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(
        f"INFO: Wrote {out_path} (shows={len(shows)}, movies={len(movies)})",
        file=sys.stderr
    )


if __name__ == "__main__":
    main()
