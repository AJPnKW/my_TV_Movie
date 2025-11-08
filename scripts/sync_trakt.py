python scripts/sync_trakt.py#!/usr/bin/env python
# =============================================================================
# File: scripts/sync_trakt.py
# Project: my_TV_Movie
# Version: v1.0.0 (2025-11-09)
#
# Purpose:
#   Enrich data/data.json with Trakt-based watched flags for profiles.
#   - Reads existing data/data.json produced by fetch_tmdb.py.
#   - For each configured Trakt user, pulls watched episodes.
#   - Marks episodes with `watched_by: ["Andrew", "Brant"]` etc.
#
# Usage:
#   Export:
#     TRAKT_PROFILES='Andrew:trakt_username1;Brant:trakt_username2'
#     API_TRAKT_CLIENT_ID='...'
#   Then:
#     python scripts/sync_trakt.py
#
# Notes:
#   - Uses Trakt "sync/watched/shows" (public per-user with API key).
#   - This is OPTIONAL. If no env vars, script exits quietly.
#   - Do NOT expose these secrets in front-end JS.
# =============================================================================

import json
import os
import sys
import time
from pathlib import Path

import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "data.json"

TRAKT_CLIENT_ID = os.getenv("API_TRAKT_CLIENT_ID") or os.getenv("API_TRAKT_ID")
TRAKT_PROFILES = os.getenv("TRAKT_PROFILES", "").strip()
TRAKT_API_URL = "https://api.trakt.tv"

def log(msg: str) -> None:
    print(f"[sync_trakt] {msg}", flush=True)

def load_data():
    if not DATA_PATH.exists():
        log("data.json not found; skipping Trakt sync.")
        return None
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log("Updated data.json with Trakt watched flags.")

def parse_profiles():
    """
    TRAKT_PROFILES format:
      "Andrew:trakt_user1;Brant:trakt_user2"
    """
    profiles = {}
    if not TRAKT_PROFILES:
        return profiles
    for part in TRAKT_PROFILES.split(";"):
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
    return profiles

def trakt_get(path: str):
    if not TRAKT_CLIENT_ID:
        raise RuntimeError("Missing API_TRAKT_CLIENT_ID / API_TRAKT_ID")
    url = TRAKT_API_URL + path
    req = urllib.request.Request(url)
    req.add_header("Content-Type", "application/json")
    req.add_header("trakt-api-version", "2")
    req.add_header("trakt-api-key", TRAKT_CLIENT_ID)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        log(f"Trakt HTTP error {e.code} for {path}")
    except Exception as e:
        log(f"Trakt request failed for {path}: {e}")
    return None

def fetch_watched_map(trakt_user: str):
    """
    Returns {(tmdb_show_id, season, episode): True} for watched episodes.
    Uses sync/watched/shows which returns per-show seasons/episodes.
    """
    data = trakt_get(f"/users/{trakt_user}/watched/shows")
    watched = {}
    if not data:
        return watched
    for item in data:
        ids = item.get("show", {}).get("ids", {})
        tmdb_id = ids.get("tmdb")
        if not tmdb_id:
            continue
        for s in item.get("seasons", []):
            sn = s.get("number")
            for ep in s.get("episodes", []):
                en = ep.get("number")
                if sn is None or en is None:
                    continue
                watched[(int(tmdb_id), int(sn), int(en))] = True
    return watched

def apply_watched_flags(data, profiles_map):
    shows = data.get("shows", [])
    # Initialize profiles list for frontend
    data.setdefault("profiles", list(profiles_map.keys()))
    # Pre-build mapping per profile
    profile_watched = {
        label: fetch_watched_map(user)
        for label, user in profiles_map.items()
    }
    # Annotate episodes
    for sh in shows:
        sid = sh.get("show_id")
        for s in sh.get("seasons", []):
            sn = s.get("season_number")
            for ep in s.get("episodes", []):
                en = ep.get("episode_number")
                if not (sid and sn is not None and en is not None):
                    continue
                key = (int(sid), int(sn), int(en))
                wb = []
                for label, wmap in profile_watched.items():
                    if key in wmap:
                        wb.append(label)
                if wb:
                  ep["watched_by"] = sorted(wb)
    return data

def main():
    if not TRAKT_CLIENT_ID or not TRAKT_PROFILES:
        log("Trakt not configured (missing CLIENT_ID or TRAKT_PROFILES); nothing to do.")
        return
    data = load_data()
    if data is None:
        return
    profiles_map = parse_profiles()
    if not profiles_map:
        log("TRAKT_PROFILES not parseable; skipping.")
        return
    log(f"Syncing Trakt for profiles: {', '.join(profiles_map.keys())}")
    data = apply_watched_flags(data, profiles_map)
    save_data(data)

if __name__ == "__main__":
    main()
