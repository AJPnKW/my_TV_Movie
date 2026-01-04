#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/qa_missing_trakt_ids.py
# [PROJECT] my_TV_Movie
# [ROLE]    QA: list items missing trakt_id in data/data.json
# [VERSION] v1.0.0
# [UPDATED] 2026-01-01
# ==============================================================================

import json
from pathlib import Path

def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    data_path = repo_root / "data" / "data.json"

    if not data_path.exists():
        print(f"ERROR: missing {data_path}")
        return 2

    with data_path.open("r", encoding="utf-8", errors="replace") as f:
        d = json.load(f)

    shows = d.get("shows", []) or []
    movies = d.get("movies", []) or []

    missing_shows = [x for x in shows if not x.get("trakt_id")]
    missing_movies = [x for x in movies if not x.get("trakt_id")]

    print(f"shows_total={len(shows)} missing_trakt_id={len(missing_shows)}")
    for x in missing_shows:
        print(
            f"- SHOW  title={x.get('title')} | "
            f"tmdb_id={x.get('tmdb_id')} | "
            f"first_air_date={x.get('first_air_date')}"
        )

    print(f"movies_total={len(movies)} missing_trakt_id={len(missing_movies)}")
    for x in missing_movies:
        print(
            f"- MOVIE title={x.get('title')} | "
            f"tmdb_id={x.get('tmdb_id')} | "
            f"release_date={x.get('release_date')}"
        )

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
