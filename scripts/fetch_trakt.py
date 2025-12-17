# =============================================================================
# File:        scripts/fetch_trakt.py
# Purpose:     Sync watch status from Trakt.tv into existing data.json
# Repo:        my_TV_Movie
#
# Version:     v1.3.0
# Date:        2025-12-17
# Build tag:   v14.01.04
#
# Notes:
# - Optional integration (never hard-fails)
# - Preserves all existing data.json content
# - Annotates shows/seasons/episodes with watch status
# - Designed to run AFTER fetch_tmdb.py
# - Safe to re-run multiple times
# =============================================================================

import os
import json
import time
import requests
from pathlib import Path
from typing import Dict, Any

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT_DIR / "data" / "data.json"
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# -----------------------------------------------------------------------------
# Trakt configuration (ENV)
# -----------------------------------------------------------------------------
TRAKT_CLIENT_ID = os.getenv("API_TRAKT_CLIENT_ID")
TRAKT_ACCESS_TOKEN = os.getenv("API_TRAKT_ACCESS_TOKEN")

TRAKT_API_BASE = "https://api.trakt.tv"

HEADERS = {
    "Content-Type": "application/json",
    "trakt-api-version": "2",
}

if TRAKT_CLIENT_ID:
    HEADERS["trakt-api-key"] = TRAKT_CLIENT_ID
if TRAKT_ACCESS_TOKEN:
    HEADERS["Authorization"] = f"Bearer {TRAKT_ACCESS_TOKEN}"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[fetch_trakt] {ts} | {msg}")

def load_data() -> Dict[str, Any]:
    if not DATA_FILE.exists():
        log("WARN: data.json not found — skipping Trakt sync.")
        return {}

    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data: Dict[str, Any]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def trakt_get(endpoint: str):
    url = f"{TRAKT_API_BASE}{endpoint}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        log(f"WARN: Trakt GET failed {r.status_code} {endpoint}")
        return None
    return r.json()

# -----------------------------------------------------------------------------
# Core Logic
# -----------------------------------------------------------------------------
def fetch_trakt_watch_history():
    if not TRAKT_CLIENT_ID or not TRAKT_ACCESS_TOKEN:
        log("INFO: Trakt credentials not set — skipping.")
        return None

    log("Fetching Trakt watched history...")
    return trakt_get("/sync/watched/shows")

def apply_watch_status(data: Dict[str, Any], watched_payload: Any) -> None:
    if not watched_payload:
        return

    shows_by_tmdb = {}

    for show in watched_payload:
        ids = show.get("show", {}).get("ids", {})
        tmdb_id = ids.get("tmdb")
        if tmdb_id:
            shows_by_tmdb[str(tmdb_id)] = show

    for show in data.get("shows", []):
        tmdb_id = str(show.get("tmdb_id"))
        watched = shows_by_tmdb.get(tmdb_id)

        if not watched:
            continue

        show["watch_status"] = "watched"
        show["last_watched_at"] = watched.get("last_watched_at")

        seasons_map = {
            s["number"]: s for s in watched.get("seasons", [])
        }

        for season in show.get("seasons", []):
            season_num = season.get("season_number")
            watched_season = seasons_map.get(season_num)

            if not watched_season:
                continue

            season["watch_status"] = "watched"

            eps_map = {
                e["number"]: e for e in watched_season.get("episodes", [])
            }

            for ep in season.get("episodes", []):
                ep_num = ep.get("episode_number")
                if ep_num in eps_map:
                    ep["watch_status"] = "watched"
                    ep["last_watched_at"] = eps_map[ep_num].get("last_watched_at")

# -----------------------------------------------------------------------------
# Entry
# -----------------------------------------------------------------------------
def main():
    log("Starting Trakt sync")

    data = load_data()
    if not data:
        return

    watched = fetch_trakt_watch_history()
    apply_watch_status(data, watched)

    save_data(data)
    log("Trakt sync complete")

if __name__ == "__main__":
    main()
