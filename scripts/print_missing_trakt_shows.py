\
#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/print_missing_trakt_shows.py
# [PROJECT] my_TV_Movie
# [ROLE]    Print shows missing trakt_id (safe console output)
# [VERSION] v1.0.0
# [UPDATED] 2025-12-30_00-00-00
# [BUILD]   14.01.07
# ==============================================================================

import json
from pathlib import Path

def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    p = repo / "data" / "data.json"
    d = json.load(p.open("r", encoding="utf-8", errors="replace"))
    misses = [x for x in d.get("shows", []) if not x.get("trakt_id")]
    print(f"missing_shows: {len(misses)}")
    for x in misses:
        title = x.get("title")
        tmdb_id = x.get("tmdb_id")
        first_air_date = x.get("first_air_date")
        print(f"- title={title}  tmdb_id={tmdb_id}  first_air_date={first_air_date}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
