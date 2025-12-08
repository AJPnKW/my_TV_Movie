#!/usr/bin/env python
# =============================================================================
# File: scripts/fetch_trakt.py
# Project: my_TV_Movie
# Version: v1.0.0 (2025-11-09)
#
# Purpose:
#   Fetch watched shows/movies from Trakt per profile and normalize into:
#     data/trakt_raw.json
#
#   This script:
#     - Does NOT modify data.json directly.
#     - Is consumed by sync_trakt.py.
#
#   Expected env:
#     API_TRAKT_CLIENT_ID        - Trakt API client id (public)
#     TRAKT_PROFILES             - "Label:trakt_user;Other:trakt_user2"
#     TRAKT_TOKEN_<LABEL>        - OAuth access token for that profile label
#
#   Notes:
#     - If tokens are missing, script logs and writes an empty structure.
#     - This keeps behavior deterministic and safe.
# =============================================================================

import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "trakt_raw.json"

TRAKT_API = "https://api.trakt.tv"


def log(msg: str) -> None:
    print(f"[fetch_trakt] {msg}", flush=True)


def parse_profiles():
    raw = os.getenv("TRAKT_PROFILES", "").strip()
    if not raw:
        log("TRAKT_PROFILES not set; no Trakt profiles configured.")
        return {}
    profiles = {}
    for part in raw.split(";"):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            continue
        label, user = part.split(":", 1)
        label = label.strip()
        user = user.strip()
        if label and user:
            profiles[label] = user
    if not profiles:
        log("TRAKT_PROFILES parsed empty.")
    else:
        log(f"Configured Trakt profiles: {', '.join(profiles.keys())}")
    return profiles


def get_headers(label: str) -> dict | None:
    client_id = os.getenv("API_TRAKT_CLIENT_ID") or os.getenv("API_TRAKT_KEY")
    if not client_id:
        log("API_TRAKT_CLIENT_ID / API_TRAKT_KEY missing; cannot call Trakt.")
        return None
    token = os.getenv(f"TRAKT_TOKEN_{label.upper()}")
    if not token:
        log(f"TRAKT_TOKEN_{label.upper()} missing; {label} will be skipped.")
        return None
    return {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": client_id,
        "Authorization": f"Bearer {token}",
    }


def fetch_watched_shows(headers: dict) -> list:
    url = f"{TRAKT_API}/sync/watched/shows"
    r = requests.get(url, headers=headers, timeout=30)
    if not r.ok:
        log(f"watched shows failed: HTTP {r.status_code}")
        return []
    return r.json() or []


def fetch_watched_movies(headers: dict) -> list:
    url = f"{TRAKT_API}/sync/watched/movies"
    r = requests.get(url, headers=headers, timeout=30)
    if not r.ok:
        log(f"watched movies failed: HTTP {r.status_code}")
        return []
    return r.json() or []


def normalize(profiles: dict) -> dict:
    data = {
        "profiles": [],
        "episodes_watched": {},  # profile -> show_id -> season -> set(eps)
        "movies_watched": {},    # profile -> movie_id -> True
    }

    for label, _user in profiles.items():
        headers = get_headers(label)
        if not headers:
            continue

        data["profiles"].append(label)
        eps_map = {}
        mov_map = {}

        shows = fetch_watched_shows(headers)
        for item in shows:
            ids = (item.get("show") or {}).get("ids") or {}
            tmdb_id = ids.get("tmdb")
            if not tmdb_id:
                continue
            sid = str(tmdb_id)
            for s in item.get("seasons") or []:
                sn = s.get("number")
                if sn is None:
                    continue
                sn = int(sn)
                for e in s.get("episodes") or []:
                    en = e.get("number")
                    if en is None:
                        continue
                    en = int(en)
                    eps_map.setdefault(sid, {}).setdefault(sn, set()).add(en)

        movies = fetch_watched_movies(headers)
        for item in movies:
            ids = (item.get("movie") or {}).get("ids") or {}
            tmdb_id = ids.get("tmdb")
            if not tmdb_id:
                continue
            mid = str(tmdb_id)
            mov_map[mid] = True

        data["episodes_watched"][label] = {
            sid: {str(sn): sorted(list(eps)) for sn, eps in seas.items()}
            for sid, seas in eps_map.items()
        }
        data["movies_watched"][label] = mov_map

        log(f"{label}: {len(eps_map)} shows with watched episodes, {len(mov_map)} watched movies.")

    return data


def main():
    profiles = parse_profiles()
    if not profiles:
        # Still write predictable empty structure.
        empty = {
            "profiles": [],
            "episodes_watched": {},
            "movies_watched": {},
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(empty, indent=2), encoding="utf-8")
        log("No profiles; wrote empty trakt_raw.json.")
        return

    try:
        data = normalize(profiles)
    except Exception as e:  # noqa: BLE001
        log(f"Exception while talking to Trakt: {e}")
        # Write empty fallback to avoid breaking pipeline.
        data = {
            "profiles": [],
            "episodes_watched": {},
            "movies_watched": {},
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2), encoding="utf-8")
    log(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
