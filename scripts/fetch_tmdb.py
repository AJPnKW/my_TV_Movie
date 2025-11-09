#!/usr/bin/env python3
"""
File: scripts/fetch_tmdb.py
Project: my_TV_Movie
Version: v2.3.0 (2025-11-09)

Purpose
-------
Build the base data/data.json from TMDB for:

  - TV shows listed in tv_list.txt
  - Movies listed in movies_list.txt

Other enrichers:
  - fetch_tvmaze.py
  - fetch_omdb.py
  - fetch_live_tv.py
  - fetch_trakt.py / sync_trakt.py

are expected to load and update this JSON in later steps.

Conventions
-----------
tv_list.txt:
    # name | tmdb_show_id | season_spec | tvmaze_id (optional)
    Abbott Elementary|125935|5
    Only Murders in the Building|107113|5
    Stranger Things|66732|5
  season_spec:
    "5"       => only season 5
    "1,2,5"   => seasons 1,2,5
    "*"       => all seasons available on TMDB

movies_list.txt:
    # File: movies_list.txt
    # format: name|tmdb_movie_id
    40 Acres|1319951
    Argylle|848538
    ...

Output shape (subset)
---------------------
{
  "generated_at": "2025-11-09T23:59:59Z",
  "shows": [
    {
      "show_id": 125935,
      "name": "...",
      "poster_path": "...",
      "overview": "...",
      "status": "Returning Series",
      "genres": ["Comedy"],
      "networks": ["ABC", "Hulu"],
      "links": {
        "tmdb": "https://www.themoviedb.org/tv/125935"
      },
      "seasons": [
        {
          "season_number": 5,
          "overview": "...",
          "episodes": [
            {
              "episode_number": 1,
              "name": "...",
              "air_date": "2025-10-01",
              "overview": "",
              "watched_by": []
            },
            ...
          ]
        },
        ...
      ]
    },
    ...
  ],
  "movies": [
    {
      "movie_id": 848538,
      "name": "Argylle",
      "poster_path": "...",
      "overview": "...",
      "status": "Released",
      "release_date": "2024-02-02",
      "genres": ["Action","Thriller"],
      "links": {
        "tmdb": "https://www.themoviedb.org/movie/848538"
      },
      "watched_by": [],
      "belongs_to_collection": {
        "id": ...,
        "name": "Some Collection"
      }
    },
    ...
  ],
  "live_tv": [],
  "profiles": [],
  "meta": {
    "shows": N,
    "movies": M
  }
}
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# ---------------- TMDB client helpers ---------------- #

TMDB_API_KEY = os.getenv("API_TMDB_KEY", "").strip()
TMDB_BEARER = os.getenv("API_TMDB_TOKEN", "").strip()

TMDB_BASE = "https://api.themoviedb.org/3"


def _tmdb_headers() -> Dict[str, str]:
    headers = {"Accept": "application/json"}
    if TMDB_BEARER:
        headers["Authorization"] = f"Bearer {TMDB_BEARER}"
    return headers


def _tmdb_params() -> Dict[str, str]:
    params: Dict[str, str] = {}
    if TMDB_API_KEY and not TMDB_BEARER:
        params["api_key"] = TMDB_API_KEY
    return params


def tmdb_get(path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Safe wrapper for TMDB GET with minimal logging.
    Returns parsed JSON dict or None on error.
    """
    if not (TMDB_API_KEY or TMDB_BEARER):
        print("[tmdb] Missing API_TMDB_KEY or API_TMDB_TOKEN; skipping TMDB calls.", file=sys.stderr)
        return None

    url = f"{TMDB_BASE}{path}"
    q = _tmdb_params()
    if params:
        q.update(params)

    try:
        r = requests.get(url, headers=_tmdb_headers(), params=q, timeout=15)
    except Exception as e:  # pragma: no cover - network
        print(f"[tmdb] ERROR requesting {url}: {e}", file=sys.stderr)
        return None

    if r.status_code == 404:
        print(f"[tmdb] 404 for {url}", file=sys.stderr)
        return None

    if not r.ok:
        print(f"[tmdb] ERROR {r.status_code} for {url}: {r.text[:200]}", file=sys.stderr)
        return None

    try:
        return r.json()
    except Exception as e:  # pragma: no cover
        print(f"[tmdb] ERROR decoding JSON from {url}: {e}", file=sys.stderr)
        return None


# ---------------- Input parsers ---------------- #

ROOT = Path(__file__).resolve().parents[1]
TV_LIST = ROOT / "tv_list.txt"
MOVIES_LIST = ROOT / "movies_list.txt"
DATA_DIR = ROOT / "data"
DATA_FILE = DATA_DIR / "data.json"


def parse_season_spec(spec: str) -> Optional[List[int]]:
    spec = (spec or "").strip()
    if not spec:
        return None
    if spec == "*":
        return None  # "all seasons", handled at fetch time
    out: List[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if not part.isdigit():
            continue
        n = int(part)
        if n >= 0 and n not in out:
            out.append(n)
    return out or None


def load_tv_list() -> List[Dict[str, Any]]:
    shows: List[Dict[str, Any]] = []
    if not TV_LIST.exists():
        print(f"[tv] {TV_LIST} missing; no shows loaded.", file=sys.stderr)
        return shows

    with TV_LIST.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3:
                # name|tmdb_id|season_spec is required
                continue
            name, tmdb_id, season_spec = parts[:3]
            tvmaze_id = parts[3].strip() if len(parts) >= 4 and parts[3].strip() else None
            if not tmdb_id.isdigit():
                continue
            seasons = parse_season_spec(season_spec)
            shows.append(
                {
                    "name": name,
                    "show_id": int(tmdb_id),
                    "season_spec": seasons,
                    "tvmaze_id": tvmaze_id,
                }
            )
    print(f"[tv] Loaded {len(shows)} show entries from tv_list.txt")
    return shows


def load_movies_list() -> List[Dict[str, Any]]:
    movies: List[Dict[str, Any]] = []
    if not MOVIES_LIST.exists():
        print(f"[movie] {MOVIES_LIST} missing; no movies loaded.", file=sys.stderr)
        return movies

    with MOVIES_LIST.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 2:
                continue
            name, tmdb_id = parts[0], parts[1]
            if not tmdb_id.isdigit():
                # Ignore "TBD" / comments after id
                continue
            movies.append({"name": name, "movie_id": int(tmdb_id)})
    print(f"[movie] Loaded {len(movies)} movie entries from movies_list.txt")
    return movies


# ---------------- TV fetch ---------------- #

def build_show_entry(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    show_id = item["show_id"]
    base = tmdb_get(f"/tv/{show_id}")
    if not base:
        return None

    seasons_spec = item.get("season_spec")  # None means "all"
    networks = [n.get("name") for n in base.get("networks", []) if n.get("name")]
    genres = [g.get("name") for g in base.get("genres", []) if g.get("name")]

    show = {
        "show_id": show_id,
        "name": base.get("name") or item.get("name"),
        "poster_path": base.get("poster_path"),
        "overview": base.get("overview") or "",
        "status": base.get("status") or "",
        "genres": genres,
        "networks": networks,
        "links": {
            "tmdb": f"https://www.themoviedb.org/tv/{show_id}"
        },
        "seasons": [],
    }

    for s in base.get("seasons", []):
        sn = s.get("season_number")
        if sn is None or sn < 0:
            continue
        # Respect season_spec if provided
        if seasons_spec is not None and sn not in seasons_spec:
            continue

        season_detail = tmdb_get(f"/tv/{show_id}/season/{sn}")
        if not season_detail:
            continue

        season = {
            "season_number": sn,
            "overview": season_detail.get("overview") or "",
            "episodes": [],
        }

        for ep in season_detail.get("episodes", []):
            epn = ep.get("episode_number")
            if epn is None:
                continue
            season["episodes"].append(
                {
                    "episode_number": epn,
                    "name": ep.get("name") or "",
                    "air_date": ep.get("air_date") or "",
                    "overview": ep.get("overview") or "",
                    "watched_by": [],  # filled by sync_trakt later
                }
            )

        show["seasons"].append(season)
        time.sleep(0.15)  # gentle rate limiting

    return show


# ---------------- Movie fetch ---------------- #

def build_movie_entry(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    movie_id = item["movie_id"]
    base = tmdb_get(f"/movie/{movie_id}")
    if not base:
        return None

    genres = [g.get("name") for g in base.get("genres", []) if g.get("name")]

    movie: Dict[str, Any] = {
        "movie_id": movie_id,
        "name": base.get("title") or base.get("name") or item.get("name"),
        "poster_path": base.get("poster_path"),
        "overview": base.get("overview") or "",
        "status": base.get("status") or "",
        "release_date": base.get("release_date") or "",
        "genres": genres,
        "links": {
            "tmdb": f"https://www.themoviedb.org/movie/{movie_id}"
        },
        "watched_by": [],  # filled by sync_trakt later
    }

    coll = base.get("belongs_to_collection") or None
    if coll and isinstance(coll, dict):
        movie["belongs_to_collection"] = {
            "id": coll.get("id"),
            "name": coll.get("name"),
        }

    return movie


# ---------------- Main build ---------------- #

def main() -> None:
    tv_entries = load_tv_list()
    mv_entries = load_movies_list()

    shows: List[Dict[str, Any]] = []
    movies: List[Dict[str, Any]] = []

    # Build shows
    for item in tv_entries:
        sh = build_show_entry(item)
        if sh:
            shows.append(sh)
        time.sleep(0.15)

    # Build movies
    for item in mv_entries:
        mv = build_movie_entry(item)
        if mv:
            movies.append(mv)
        time.sleep(0.1)

    DATA_DIR.mkdir(exist_ok=True)

    data: Dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "shows": shows,
        "movies": movies,
        "live_tv": [],    # filled/extended by fetch_live_tv.py
        "profiles": [],   # filled by fetch_trakt/sync_trakt if configured
        "meta": {
            "shows": len(shows),
            "movies": len(movies),
        },
    }

    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=False)

    print(
        f"[done] Wrote {DATA_FILE} with {len(shows)} shows, {len(movies)} movies.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
