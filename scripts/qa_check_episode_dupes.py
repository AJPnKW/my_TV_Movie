# FILE: scripts\qa_check_episode_dupes.py
# PURPOSE: Verify whether data/data.json contains duplicate episode keys (show_tmdb_id, season_number, episode_number)
# RUN: py -3 scripts\qa_check_episode_dupes.py

import json
from collections import Counter
from pathlib import Path

def main() -> int:
    p = Path("data/data.json")
    data = json.loads(p.read_text(encoding="utf-8"))

    episodes = []
    for show in data.get("shows", []):
        sid = show.get("tmdb_id")
        for season in show.get("seasons", []):
            sn = season.get("season_number")
            for ep in season.get("episodes", []):
                key = (sid, sn, ep.get("episode_number"))
                episodes.append(key)

    counts = Counter(episodes)
    dupes = [k for k, v in counts.items() if v > 1]

    print(f"TOTAL_EPISODES={len(episodes)}")
    print(f"DUPLICATE_KEYS={len(dupes)}")
    if dupes:
        print("SAMPLE_DUPES=" + json.dumps(dupes[:25]))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
