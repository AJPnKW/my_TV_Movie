#!/usr/bin/env python3
# ==============================================================================
# File: scripts/qa_inputs_parsed_missing_trakt.py
# Project: my_TV_Movie
# Purpose:
#   Identify entries in data/inputs_parsed.json whose tmdb_id corresponds
#   to shows missing trakt_id in data/data.json.
# ==============================================================================

import json
import os
import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUTS_PARSED = os.path.join(REPO_ROOT, "data", "inputs_parsed.json")
REPORTS_DIR = os.path.join(REPO_ROOT, "reports")

MISSING_TMDB_IDS = {"203397", "203755"}

def main():
    with open(INPUTS_PARSED, "r", encoding="utf-8") as f:
        data = json.load(f)

    tv = data.get("tv", [])
    hits = [
        x for x in tv
        if str(x.get("tmdb_id", "")).strip() in MISSING_TMDB_IDS
    ]

    print(f"inputs_parsed tv hits: {len(hits)}")
    for x in hits:
        print(
            f"- title={x.get('title')}  "
            f"tmdb_id={x.get('tmdb_id')}  "
            f"first_air_date={x.get('first_air_date')}"
        )

    os.makedirs(REPORTS_DIR, exist_ok=True)
    out = os.path.join(
        REPORTS_DIR,
        f"_inputs_parsed_missing_trakt_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
    )

    with open(out, "w", encoding="utf-8") as f:
        json.dump({"hits": hits}, f, ensure_ascii=False, indent=2)

    print(f"WROTE {out}")

if __name__ == "__main__":
    main()
