#!/usr/bin/env python3
# ======================================================================================
# File:        scripts/fetch_trakt.py
# Project:     my_TV_Movie
#
# Purpose:
#   - Pull watched state from Trakt (optional feature; do NOT break builds if not configured)
#   - Produce static watched maps that the UI can consume later:
#       - data/trakt_watched.json
#       - data/trakt_last_refresh.txt
#
# Version:
#   v1.2.0 (2025-12-16)
#
# Required env (one of the following modes):
#   Mode A (recommended):
#     - API_TRAKT_CLIENT_ID
#     - API_TRAKT_ACCESS_TOKEN
#
#   Mode B (fallback – if you manage refresh yourself):
#     - API_TRAKT_CLIENT_ID
#     - API_TRAKT_ACCESS_TOKEN
#
# Notes:
#   - If Trakt env is missing, script writes an EMPTY watched map and exits 0 (non-blocking).
#   - This script does NOT mutate data/data.json (keeps responsibilities clean).
# ======================================================================================

from __future__ import annotations

import datetime as _dt
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]

PATH_DATA_DIR = REPO_ROOT / "data"
PATH_WATCHED_JSON = PATH_DATA_DIR / "trakt_watched.json"
PATH_LAST_REFRESH = PATH_DATA_DIR / "trakt_last_refresh.txt"

PATH_LOG_DIR = REPO_ROOT / "logs"
PATH_LOG_FILE = PATH_LOG_DIR / "fetch_trakt.log.txt"

TRAKT_API_BASE = "https://api.trakt.tv"


def _now_utc_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def log(msg: str) -> None:
    PATH_LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"{_now_utc_iso()} {msg}"
    print(line)
    with PATH_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def empty_payload(reason: str) -> Dict[str, Any]:
    return {
        "meta": {
            "builder": "scripts/fetch_trakt.py",
            "version": "v1.2.0",
            "built_at": _now_utc_iso(),
            "configured": False,
            "reason": reason,
        },
        "watched": {
            "shows": {},   # tmdb_id -> { "episodes": { "SxEy": true, ... } }
            "movies": {},  # tmdb_id -> true
        },
    }


def main() -> int:
    t0 = time.time()
    log("[fetch_trakt] START")

    client_id = os.getenv("API_TRAKT_CLIENT_ID", "").strip()
    access_token = os.getenv("API_TRAKT_ACCESS_TOKEN", "").strip()

    if not client_id or not access_token:
        payload = empty_payload("Missing API_TRAKT_CLIENT_ID and/or API_TRAKT_ACCESS_TOKEN in env (non-blocking).")
        write_json(PATH_WATCHED_JSON, payload)
        PATH_DATA_DIR.mkdir(parents=True, exist_ok=True)
        PATH_LAST_REFRESH.write_text(payload["meta"]["built_at"] + "\n", encoding="utf-8")
        log("[fetch_trakt] SKIP (not configured) -> wrote empty watched map")
        return 0

    import requests  # local import to make missing dep obvious
    s = requests.Session()
    headers = {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": client_id,
        "Authorization": f"Bearer {access_token}",
    }

    def get_json(path: str):
        url = f"{TRAKT_API_BASE}{path}"
        r = s.get(url, headers=headers, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f"Trakt {r.status_code} for {url}: {r.text[:200]}")
        return r.json()

    watched_shows = get_json("/sync/watched/shows?extended=full")
    watched_movies = get_json("/sync/watched/movies?extended=full")

    shows_map: Dict[str, Any] = {}
    for item in watched_shows or []:
        show = (item or {}).get("show") or {}
        ids = show.get("ids") or {}
        tmdb_id = ids.get("tmdb")
        if not tmdb_id:
            continue

        episodes = {}
        for season in (item.get("seasons") or []):
            s_num = season.get("number")
            for ep in (season.get("episodes") or []):
                e_num = ep.get("number")
                if s_num is None or e_num is None:
                    continue
                key = f"S{s_num}E{e_num}"
                episodes[key] = True

        shows_map[str(tmdb_id)] = {"episodes": episodes}

    movies_map: Dict[str, Any] = {}
    for item in watched_movies or []:
        movie = (item or {}).get("movie") or {}
        ids = movie.get("ids") or {}
        tmdb_id = ids.get("tmdb")
        if not tmdb_id:
            continue
        movies_map[str(tmdb_id)] = True

    built_at = _now_utc_iso()
    payload = {
        "meta": {
            "builder": "scripts/fetch_trakt.py",
            "version": "v1.2.0",
            "built_at": built_at,
            "configured": True,
            "counts": {"shows": len(shows_map), "movies": len(movies_map)},
        },
        "watched": {"shows": shows_map, "movies": movies_map},
    }

    write_json(PATH_WATCHED_JSON, payload)
    PATH_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PATH_LAST_REFRESH.write_text(built_at + "\n", encoding="utf-8")

    dt = time.time() - t0
    log(f"[fetch_trakt] DONE in {dt:.1f}s -> data/trakt_watched.json ({PATH_WATCHED_JSON.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
