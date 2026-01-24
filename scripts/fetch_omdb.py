# =============================================================================
# File: scripts/fetch_omdb.py
# Project: my_TV_Movie
# Version: v1.0.0 (2025-11-07)
#
# Purpose:
#   Optional helper to enrich movies via OMDb.
#   Reads data/data.json and writes:
#       data/omdb_movies.json
#
#   Uses:
#       API_OMDB_KEY
#
# Notes:
#   - This does NOT modify data.json (to keep pipeline simple).
#   - The UI currently does not consume this file directly.
#   - Use for debugging / future expansion (ratings, etc).
# =============================================================================

import os
import json
import pathlib
import sys
from urllib.parse import urlencode
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_JSON = ROOT / "data" / "data.json"
OUT = ROOT / "data" / "omdb_movies.json"

OMDB_KEY = os.environ.get("API_OMDB_KEY", "")


def fetch_omdb(title: str, year: str | None):
    params = {
        "apikey": OMDB_KEY,
        "t": title,
    }
    if year:
        params["y"] = year
    url = "https://www.omdbapi.com/?" + urlencode(params)
    r = requests.get(url, timeout=15)
    if not r.ok:
        return None
    data = r.json()
    if data.get("Response") != "True":
        return None
    return {
        "imdb_id": data.get("imdbID"),
        "rated": data.get("Rated"),
        "imdb_rating": data.get("imdbRating"),
        "imdb_votes": data.get("imdbVotes"),
        "metascore": data.get("Metascore"),
        "ratings": data.get("Ratings") or [],
        "tomato_meter": data.get("tomatoMeter", None),
        "tomato_rating": data.get("tomatoRating", None),
        "tomato_votes": data.get("tomatoReviews", None),
    }


def main():
    if not OMDB_KEY:
        print("No API_OMDB_KEY; skipping OMDb.")
        sys.exit(0)

    if not DATA_JSON.exists():
        print("Missing data/data.json; run fetch_tmdb.py first.")
        sys.exit(1)

    data = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    movies = data.get("movies", [])

    out = {"movies": []}
    for mv in movies:
        title = mv.get("title") or mv.get("name")
        year = mv.get("release_date", "")[:4] if mv.get("release_date") else None
        if not title:
            continue
        info = fetch_omdb(title, year)
        if info:
            out["movies"].append(
                {
                    "tmdb_id": mv.get("tmdb_id"),
                    "title": title,
                    "year": year,
                    "omdb": info,
                }
            )

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # Optionally merge into data.json (non-destructive, adds only omdb field)
    try:
        data = json.loads(DATA_JSON.read_text(encoding="utf-8"))
        by_tmdb = {str(x.get("tmdb_id")): x.get("omdb") for x in out.get("movies") or [] if x.get("tmdb_id")}
        if by_tmdb and isinstance(data.get("movies"), list):
            for mv in data["movies"]:
                key = str(mv.get("tmdb_id"))
                if key in by_tmdb:
                    mv["omdb"] = by_tmdb[key]
        DATA_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK: wrote {OUT} and merged OMDb into {DATA_JSON}")
    except Exception as ex:
        print(f"WARN: wrote {OUT} but could not merge into data.json: {ex}")


if __name__ == "__main__":
    main()
