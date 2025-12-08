#!/usr/bin/env python
# =============================================================================
# File: scripts/sync_trakt.py
# Project: my_TV_Movie
# Version: v2.0.1 (2025-11-10)
#
# Purpose:
#   Merge Trakt-derived watch data (trakt_raw.json) into data.json.
#
#   - Adds `profiles` array at top level.
#   - For each episode in each show:
#       ep["watched_by"] = [profile, ...]
#   - For each movie:
#       movie["watched_by"] = [profile, ...]
#
#   Contract with fetch_trakt.py:
#     trakt_raw.json:
#       {
#         "profiles": ["Andrew", "Brant"],
#         "episodes_watched": {
#           "Andrew": {
#             "<tmdb_show_id>": {
#               "<season_number>": [<ep_numbers>]
#             }
#           },
#           ...
#         },
#         "movies_watched": {
#           "Andrew": {
#             "<tmdb_movie_id>": true,
#             ...
#           },
#           ...
#         }
#       }
#
#   Notes:
#     - Safe if trakt_raw.json missing or empty.
#     - If no Trakt data, data.json is left unchanged.
# =============================================================================

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "data.json"
TRAKT_FILE = ROOT / "data" / "trakt_raw.json"


def log(msg: str) -> None:
    print(f"[sync_trakt] {msg}", flush=True)


def load_json(path: Path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    data = load_json(DATA_FILE)
    if data is None:
        log("data.json missing; nothing to sync.")
        return

    trakt = load_json(TRAKT_FILE) or {}

    profiles = trakt.get("profiles") or []
    episodes_watched = trakt.get("episodes_watched") or {}
    movies_watched = trakt.get("movies_watched") or {}

    if not profiles:
        log("No Trakt profiles in trakt_raw.json; leaving data.json as-is.")
        return

    # Ensure top-level profiles exists for UI filters
    data["profiles"] = profiles

    shows = data.get("shows") or []
    movies = data.get("movies") or []

    ep_count = 0
    mv_count = 0

    # -------------------------------------------------------------------------
    # Episodes: annotate each ep with watched_by[]
    # -------------------------------------------------------------------------
    for show in shows:
        sid = str(show.get("show_id") or show.get("id") or "")
        if not sid:
           continue

        for season in show.get("seasons") or []:
            sn = str(season.get("season_number"))
            if not sn:
                continue

            for ep in season.get("episodes") or []:
                en = ep.get("episode_number")
                if en is None:
                    continue
                en_str = str(en)

                watched_by = []
                for profile in profiles:
                    p_map = episodes_watched.get(profile, {})
                    s_map = p_map.get(sid, {})
                    # By contract: s_map[sn] is either list[int] or dict[str, bool]
                    v = s_map.get(sn, [])
                    if isinstance(v, list):
                        if en in v or en_str in [str(x) for x in v]:
                            watched_by.append(profile)
                    elif isinstance(v, dict):
                        if en_str in v or str(en) in v:
                            watched_by.append(profile)

                if watched_by:
                    ep["watched_by"] = sorted(set(watched_by))
                    ep_count += 1

    # -------------------------------------------------------------------------
    # Movies: annotate each movie with watched_by[]
    # -------------------------------------------------------------------------
    for mv in movies:
        mid = str(mv.get("movie_id") or mv.get("id") or "")
        if not mid:
            continue

        watched_by = []
        for profile in profiles:
            p_map = movies_watched.get(profile, {})
            if p_map.get(mid):
                watched_by.append(profile)

        if watched_by:
            mv["watched_by"] = sorted(set(watched_by))
            mv_count += 1

    # -------------------------------------------------------------------------
    # Save
    # -------------------------------------------------------------------------
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    log(
        f"Applied Trakt data: {ep_count} episodes tagged, "
        f"{mv_count} movies tagged, profiles={profiles}"
    )


if __name__ == "__main__":
    main()
