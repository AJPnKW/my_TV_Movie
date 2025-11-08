#!/usr/bin/env python
# =============================================================================
# File: scripts/sync_trakt.py
# Project: my_TV_Movie
# Version: v2.0.0 (2025-11-09)
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
#   Interpretation (UI side):
#     - Profile "Andrew"/"Brant": based on direct presence in watched_by.
#     - Profile "Both": treat an item as "watched_by Both" if both names present.
#
#   Notes:
#     - Safe if trakt_raw.json missing or empty.
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
    eps_map = trakt.get("episodes_watched") or {}
    mov_map = trakt.get("movies_watched") or {}

    data["profiles"] = profiles

    # Episodes
    shows = data.get("shows") or []
    ep_count = 0
    for show in shows:
      sid = str(show.get("show_id") or "")
      if not sid:
          continue
      per_show = eps_map.get(sid, {})
      # Normalize keys of per_show: season -> list
      for season in show.get("seasons") or []:
          sn = str(season.get("season_number"))
          if not sn or sn not in per_show:
              continue
          per_season = set()
          for p, by_show in eps_map.items():
              # we'll use the prebuilt per_show only
              pass
          eps_for_season = per_show.get(sn, {})
          # eps_for_season expected as {profile: [eps]} or earlier mapping.
          # But our fetch_trakt.py stored:
          # eps_map[profile][show_id][season][episodes...]
          # Re-read properly:
          break

    # Actually interpret based on fetch_trakt structure:
    #   episodes_watched[profile][show_id][season][episode] = true (via sets serialized)

    episodes_watched = trakt.get("episodes_watched") or {}

    for show in shows:
        sid = str(show.get("show_id") or "")
        if not sid:
            continue
        for season in show.get("seasons") or []:
            sn = str(season.get("season_number"))
            episodes = season.get("episodes") or []
            for ep in episodes:
                en = str(ep.get("episode_number"))
                if not en:
                    continue
                watched_by = []
                for profile in profiles:
                    by_profile = episodes_watched.get(profile, {})
                    by_show = by_profile.get(sid, {})
                    by_season = by_show.get(sn, [])
                    # by_season is a list of episode numbers (from fetch_trakt)
                    if isinstance(by_season, list):
                        if ep.get("episode_number") in by_season:
                            watched_by.append(profile)
                    elif isinstance(by_season, dict):
                        # fallback if structure differs
                        if en in by_season or ep.get("episode_number") in by_season:
                            watched_by.append(profile)
                if watched_by:
                    ep["watched_by"] = sorted(set(watched_by))
                    ep_count += 1

    # Movies
    movies = data.get("movies") or []
    mv_count = 0
    for mv in movies:
        mid = str(mv.get("movie_id") or mv.get("id") or "")
        if not mid:
            continue
        watched_by = []
        for profile in profiles:
            by_profile = mov_map.get(profile, {})
            if by_profile.get(mid):
                watched_by.append(profile)
        if watched_by:
            mv["watched_by"] = sorted(set(watched_by))
            mv_count += 1

    # Save
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    log(f"Applied Trakt data: {ep_count} episodes, {mv_count} movies, profiles={profiles}")


if __name__ == "__main__":
    main()
