#!/usr/bin/env python3
# =====================================================================================
# [PY-HEADER]
# File:        scripts/fetch_trakt.py
# Project:     my_TV_Movie
# Purpose:     Enrich data/data.json with Trakt watched status (shows + movies)
# Version:     v14.01.03
# Date:        2025-12-16
# Author:      AJPnKW (maintained with ChatGPT)
#
# Key Behaviours / Non-Negotiables:
# - Does NOT hard-fail if Trakt credentials are missing (warn + exit 0).
# - Reads:  data/data.json
# - Writes: data/data.json (in-place update) + data/trakt_state.json (raw snapshot)
# - Adds watched fields:
#     - movies[].trakt.watched (bool)
#     - movies[].trakt.last_watched_at (iso str | null)
#     - shows[].trakt.watched_episodes (set count)
#     - shows[].trakt.last_watched_at
#     - shows[].seasons_full[].episodes[].trakt.watched (bool)
#
# Expected ENV:
# - TRAKT_CLIENT_ID      (required)
# - TRAKT_ACCESS_TOKEN   (required; "Bearer" token value)
#
# Notes:
# - This uses Trakt v2 API with OAuth bearer token:
#   Authorization: Bearer <token>
#   trakt-api-version: 2
#   trakt-api-key: <client_id>
# =====================================================================================

from __future__ import annotations

import datetime as _dt
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
LOGS_DIR = REPO_ROOT / "logs"

DATA_JSON = DATA_DIR / "data.json"
TRAKT_STATE_JSON = DATA_DIR / "trakt_state.json"

TRAKT_API_BASE = "https://api.trakt.tv"
SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json"})


def _now_iso_utc() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _log_path() -> Path:
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return LOGS_DIR / f"fetch_trakt_v14.01.03_{ts}.log.txt"


def _write_log_line(fp: Path, line: str) -> None:
    fp.parent.mkdir(parents=True, exist_ok=True)
    with fp.open("a", encoding="utf-8") as f:
        f.write(line.rstrip("\n") + "\n")


def _print_and_log(log_fp: Path, msg: str) -> None:
    print(msg)
    _write_log_line(log_fp, msg)


def _safe_write_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _trakt_headers(client_id: str, access_token: str) -> Dict[str, str]:
    return {
        "trakt-api-version": "2",
        "trakt-api-key": client_id,
        "Authorization": f"Bearer {access_token}",
    }


def _trakt_get(log_fp: Path, headers: Dict[str, str], path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{TRAKT_API_BASE}{path}"
    try:
        r = SESSION.get(url, headers=headers, params=params or {}, timeout=30)
        if r.status_code != 200:
            _print_and_log(log_fp, f"[fetch_trakt] WARN: GET {path} failed: {r.status_code} {r.text[:200]}")
            return None
        return r.json()
    except Exception as e:
        _print_and_log(log_fp, f"[fetch_trakt] WARN: GET {path} exception: {e}")
        return None


def _index_movie_history(history_items: List[Dict[str, Any]]) -> Dict[int, str]:
    """
    Returns {tmdb_id: last_watched_at_iso}
    """
    out: Dict[int, str] = {}
    for item in history_items or []:
        if item.get("type") != "movie":
            continue
        movie = item.get("movie") or {}
        ids = movie.get("ids") or {}
        tmdb = ids.get("tmdb")
        watched_at = item.get("watched_at")
        if isinstance(tmdb, int) and isinstance(watched_at, str):
            # history is newest-first; first seen is latest
            if tmdb not in out:
                out[tmdb] = watched_at
    return out


def _index_episode_history(history_items: List[Dict[str, Any]]) -> Tuple[Dict[Tuple[int, int, int], str], Dict[int, str]]:
    """
    Returns:
      - episode_key -> watched_at  where key = (show_tmdb, season, episode)
      - show_tmdb -> last_watched_at
    """
    ep_map: Dict[Tuple[int, int, int], str] = {}
    show_last: Dict[int, str] = {}

    for item in history_items or []:
        if item.get("type") != "episode":
            continue
        ep = item.get("episode") or {}
        show = item.get("show") or {}

        show_ids = (show.get("ids") or {})
        ep_ids = (ep.get("ids") or {})

        show_tmdb = show_ids.get("tmdb")
        season = ep.get("season")
        number = ep.get("number")
        watched_at = item.get("watched_at")

        if not (isinstance(show_tmdb, int) and isinstance(season, int) and isinstance(number, int) and isinstance(watched_at, str)):
            continue

        key = (show_tmdb, season, number)
        if key not in ep_map:
            ep_map[key] = watched_at

        if show_tmdb not in show_last:
            show_last[show_tmdb] = watched_at

    return ep_map, show_last


def main() -> int:
    log_fp = _log_path()
    start = time.time()

    if not DATA_JSON.exists():
        _print_and_log(log_fp, f"[fetch_trakt] WARN: Missing {DATA_JSON}. Nothing to enrich.")
        return 0

    client_id = os.environ.get("TRAKT_CLIENT_ID", "").strip()
    access_token = os.environ.get("TRAKT_ACCESS_TOKEN", "").strip()

    if not client_id or not access_token:
        _print_and_log(
            log_fp,
            "[fetch_trakt] WARN: TRAKT_CLIENT_ID and/or TRAKT_ACCESS_TOKEN not set. Skipping Trakt enrichment (non-fatal).",
        )
        return 0

    headers = _trakt_headers(client_id, access_token)

    data = json.loads(DATA_JSON.read_text(encoding="utf-8"))

    # Pull recent history; this is the most reliable way to mark watched without multiple endpoints.
    # Increase limit if needed later.
    history = _trakt_get(log_fp, headers, "/users/me/history", params={"limit": 500})
    if not isinstance(history, list):
        _print_and_log(log_fp, "[fetch_trakt] WARN: No usable history returned; leaving data.json unchanged.")
        return 0

    movie_last = _index_movie_history(history)
    ep_map, show_last = _index_episode_history(history)

    # Snapshot raw trakt-derived indexes (debuggable + auditable)
    trakt_state = {
        "meta": {"version": "v14.01.03", "built_utc": _now_iso_utc()},
        "movie_last_watched": movie_last,
        "episode_watched": {f"{k[0]}:{k[1]}:{k[2]}": v for k, v in ep_map.items()},
        "show_last_watched": show_last,
    }
    _safe_write_json(TRAKT_STATE_JSON, trakt_state)

    # Enrich movies
    for m in data.get("movies") or []:
        tmdb_id = m.get("tmdb_id") or m.get("id") or (m.get("ids") or {}).get("tmdb")
        watched_at = None
        if isinstance(tmdb_id, int):
            watched_at = movie_last.get(tmdb_id)

        m.setdefault("trakt", {})
        m["trakt"]["watched"] = bool(watched_at)
        m["trakt"]["last_watched_at"] = watched_at

    # Enrich shows + episodes
    for s in data.get("shows") or []:
        show_tmdb = s.get("tmdb_id") or s.get("id") or (s.get("ids") or {}).get("tmdb")
        if not isinstance(show_tmdb, int):
            continue

        watched_count = 0
        seasons_full = s.get("seasons_full") or []
        for season in seasons_full:
            season_number = season.get("season_number")
            eps = season.get("episodes") or []
            if not isinstance(season_number, int):
                continue
            for ep in eps:
                ep_num = ep.get("episode_number") or ep.get("number")
                if not isinstance(ep_num, int):
                    continue
                key = (show_tmdb, season_number, ep_num)
                w_at = ep_map.get(key)
                ep.setdefault("trakt", {})
                ep["trakt"]["watched"] = bool(w_at)
                ep["trakt"]["watched_at"] = w_at
                if w_at:
                    watched_count += 1

        s.setdefault("trakt", {})
        s["trakt"]["watched_episodes"] = watched_count
        s["trakt"]["last_watched_at"] = show_last.get(show_tmdb)

    # Stamp meta
    data.setdefault("meta", {})
    data["meta"]["trakt_enriched_utc"] = _now_iso_utc()
    data["meta"]["trakt_enriched_version"] = "v14.01.03"

    _safe_write_json(DATA_JSON, data)

    elapsed = time.time() - start
    _print_and_log(log_fp, f"[fetch_trakt] OK: wrote {TRAKT_STATE_JSON}")
    _print_and_log(log_fp, f"[fetch_trakt] OK: updated {DATA_JSON}")
    _print_and_log(log_fp, f"[fetch_trakt] DONE in {elapsed:.1f}s")
    _print_and_log(log_fp, f"[fetch_trakt] log={log_fp}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
