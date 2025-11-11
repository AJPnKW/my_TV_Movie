"""
File: scripts/fetch_tmdb.py
Project: my_TV_Movie
Version: v2.3.1 (2025-11-11 22:15 EST)

Purpose:
  - Read:
      tv_list.txt    lines: name|tmdb_show_id|season_spec|[tvmaze_id]
      movies_list.txt lines: name|tmdb_movie_id
  - Pull metadata from TMDB.
  - Write data/data.json with:
      shows[] (with seasons & episodes),
      movies[],
      livetv[] (left as-is / filled by other scripts),
      meta{},
      generated_at.

Requirements:
  - Env: API_TMDB_KEY
Notes:
  - Ignores blank, comment (#), or invalid-ID lines.
  - Season spec:
        "*"      -> all seasons > 0
        "5"      -> only season 5
        "1,2,5"  -> seasons 1, 2, 5
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
TV_LIST = ROOT / "tv_list.txt"
MOVIE_LIST = ROOT / "movies_list.txt"
OUT_FILE = DATA_DIR / "data.json"

TMDB_API_KEY = os.getenv("API_TMDB_KEY")
TMDB_BASE = "https://api.themoviedb.org/3"


def log(msg: str) -> None:
    print(f"[fetch_tmdb] {msg}", flush=True)


def tmdb_get(path: str, params: dict | None = None) -> dict:
    if not TMDB_API_KEY:
        raise SystemExit("[fetch_tmdb] Missing API_TMDB_KEY")

    p = {"api_key": TMDB_API_KEY, "language": "en-US"}
    if params:
        p.update(params)

    url = f"{TMDB_BASE}{path}"
    r = requests.get(url, params=p, timeout=15)

    if r.status_code != 200:
        log(f"TMDB GET {path} failed: {r.status_code} {r.text[:120]}")
        return {}

    try:
        return r.json() or {}
    except Exception as e:
        log(f"TMDB JSON decode error for {path}: {e}")
        return {}


# ---------------------------------------------------------------------------
# Parsing input lists
# ---------------------------------------------------------------------------

def parse_tv_list() -> list[dict]:
    items: list[dict] = []

    if not TV_LIST.exists():
        log("tv_list.txt not found; no shows.")
        return items

    for raw in TV_LIST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue

        name, sid = parts[0], parts[1]
        if not sid.isdigit():
            continue

        season_spec = "*"
        if len(parts) >= 3 and parts[2].strip():
            season_spec = parts[2].strip()

        items.append(
            {
                "ref_name": name,
                "show_id": int(sid),
                "season_spec": season_spec,
            }
        )

    log(f"Parsed {len(items)} tv_list entries")
    return items


def parse_movies_list() -> list[dict]:
    items: list[dict] = []

    if not MOVIE_LIST.exists():
        log("movies_list.txt not found; no movies.")
        return items

    for raw in MOVIE_LIST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue

        name, mid = parts[0], parts[1]
        if not mid.isdigit():
            continue

        items.append(
            {
                "ref_name": name,
                "tmdb_id": int(mid),
            }
        )

    log(f"Parsed {len(items)} movies_list entries")
    return items


def expand_season_spec(spec: str, all_seasons: list[dict]) -> list[int]:
    if not spec or spec == "*":
        return sorted(
            {
                s.get("season_number")
                for s in all_seasons
                if s.get("season_number", 0) > 0
            }
        )

    wanted: set[int] = set()
    for chunk in spec.split(","):
        c = chunk.strip()
        if not c:
            continue
        if c.isdigit():
            wanted.add(int(c))

    if not wanted:
        return expand_season_spec("*", all_seasons)

    return sorted(wanted)


# ---------------------------------------------------------------------------
# Build shows / movies
# ---------------------------------------------------------------------------

def build_shows(tv_entries: list[dict]) -> list[dict]:
    shows: list[dict] = []

    for entry in tv_entries:
        sid = entry["show_id"]
        ref_name = entry["ref_name"]

        log(f"Show {ref_name} ({sid})")
        meta = tmdb_get(f"/tv/{sid}")
        if not meta or meta.get("status_code") == 34:
            log("  ! skipped (no TMDB data)")
            continue

        seasons_meta = meta.get("seasons") or []
        wanted_numbers = expand_season_spec(entry["season_spec"], seasons_meta)

        # Default episode runtime
        default_ep_rt = 0
        ep_rt_raw = meta.get("episode_run_time")
        if isinstance(ep_rt_raw, list) and ep_rt_raw:
            try:
                default_ep_rt = int(ep_rt_raw[0] or 0)
            except Exception:
                default_ep_rt = 0

        show_obj: dict = {
            "ref_name": ref_name,
            "show_id": sid,
            "tmdb_id": sid,
            "name": meta.get("name") or ref_name,
            "poster_path": meta.get("poster_path"),
            "status": meta.get("status") or "",
            "first_air_date": meta.get("first_air_date") or "",
            "genres": [g.get("name") for g in meta.get("genres") or []],
            "overview": meta.get("overview") or "",
            "networks": [n.get("name") for n in meta.get("networks") or []],
            "links": {
                "tmdb": f"https://www.themoviedb.org/tv/{sid}",
            },
            "seasons": [],
        }

        for s_meta in seasons_meta:
            snum = s_meta.get("season_number")
            if not snum or snum not in wanted_numbers:
                continue

            s_detail = tmdb_get(f"/tv/{sid}/season/{snum}")
            if not s_detail:
                continue

            episodes = []
            for ep in s_detail.get("episodes") or []:
                runtime = ep.get("runtime") or default_ep_rt or None
                episodes.append(
                    {
                        "episode_number": ep.get("episode_number"),
                        "name": ep.get("name") or "",
                        "air_date": ep.get("air_date") or "",
                        "overview": ep.get("overview") or "",
                        "runtime": runtime,
                        "links": {
                            "tmdb": f"https://www.themoviedb.org/tv/{sid}/season/{snum}/episode/{ep.get('episode_number')}"
                            if ep.get("episode_number")
                            else None
                        },
                    }
                )

            season_obj = {
                "season_number": snum,
                "name": s_detail.get("name") or f"Season {snum}",
                "air_date": s_detail.get("air_date") or "",
                "episode_count": len(episodes),
                "overview": s_detail.get("overview") or "",
                "episodes": episodes,
            }
            show_obj["seasons"].append(season_obj)

            time.sleep(0.15)

        shows.append(show_obj)
        time.sleep(0.15)

    log(f"Built {len(shows)} shows")
    return shows


def build_movies(movie_entries: list[dict]) -> list[dict]:
    movies: list[dict] = []

    for entry in movie_entries:
        mid = entry["tmdb_id"]
        ref_name = entry["ref_name"]

        log(f"Movie {ref_name} ({mid})")
        meta = tmdb_get(f"/movie/{mid}")
        if not meta or meta.get("status_code") == 34:
            log("  ! skipped (no TMDB data)")
            continue

        m = {
            "ref_name": ref_name,
            "tmdb_id": mid,
            "movie_id": mid,
            "title": meta.get("title") or ref_name,
            "poster_path": meta.get("poster_path"),
            "release_date": meta.get("release_date") or "",
            "status": meta.get("status") or "",
            "runtime": meta.get("runtime") or None,
            "overview": meta.get("overview") or "",
            "genres": [g.get("name") for g in meta.get("genres") or []],
            "belongs_to_collection": meta.get("belongs_to_collection") or None,
            "links": {
                "tmdb": f"https://www.themoviedb.org/movie/{mid}",
            },
        }

        movies.append(m)
        time.sleep(0.15)

    log(f"Built {len(movies)} movies")
    return movies


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    tv_entries = parse_tv_list()
    movie_entries = parse_movies_list()

    shows = build_shows(tv_entries)
    movies = build_movies(movie_entries)

    out = {
        "shows": shows,
        "movies": movies,
        "livetv": [],  # can be filled by fetch_live_tv.py
        "meta": {
            "shows": len(shows),
            "movies": len(movies),
            "livetv": 0,
        },
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }

    OUT_FILE.write_text(json.dumps(out, indent=2), encoding="utf-8")
    log(f"Wrote {OUT_FILE} ({len(shows)} shows, {len(movies)} movies)")


if __name__ == "__main__":
    main()
