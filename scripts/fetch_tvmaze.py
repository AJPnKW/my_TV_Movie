# =============================================================================
# File: scripts/fetch_tvmaze.py
# Project: my_TV_Movie
# Version: v1.0.0 (2025-11-07)
#
# Purpose:
#   Optional helper to dump raw TVMaze episode data for shows
#   that specify a tvmaze_id in tv_list.txt.
#
#   Output:
#     data/tvmaze_raw.json
#
# Notes:
#   - Not required by the UI. Main integration is in fetch_tmdb.py.
#   - Useful for debugging and verifying TVMaze vs TMDB.
# =============================================================================

import os
import json
import re
import pathlib
import sys
from datetime import datetime

import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
TV_LIST = ROOT / "tv_list.txt"
DATA_DIR = ROOT / "data"
OUT = DATA_DIR / "tvmaze_raw.json"

TVMAZE_KEY = os.environ.get("API_TVMAZE_KEY", "")

BASE_TVMAZE = "https://api.tvmaze.com"
LINE_RE = re.compile(
    r"^\s*([^#|]+?)\s*\|\s*(\d+)\s*\|\s*([\d,\*]+)(?:\s*\|\s*(\d+))?\s*$"
)


def tvmaze_get(path: str, params=None):
    if not TVMAZE_KEY:
        raise RuntimeError("API_TVMAZE_KEY not set.")
    url = f"{BASE_TVMAZE}{path}"
    headers = {"X-API-Key": TVMAZE_KEY}
    r = requests.get(url, headers=headers, params=params or {}, timeout=20)
    r.raise_for_status()
    return r.json()


def parse_tv_list():
    if not TV_LIST.exists():
        return []
    items = []
    with TV_LIST.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = LINE_RE.match(line)
            if not m:
                continue
            name, _tmdb, _seasons, tvmaze_id = m.groups()
            if tvmaze_id:
                items.append({"name": name, "tvmaze_id": int(tvmaze_id)})
    return items


def main():
    if not TVMAZE_KEY:
        print("No API_TVMAZE_KEY; nothing to do.")
        sys.exit(0)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    shows = parse_tv_list()

    out = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "shows": [],
    }

    for item in shows:
        try:
            eps = tvmaze_get(f"/shows/{item['tvmaze_id']}/episodes")
            out["shows"].append(
                {
                    "name": item["name"],
                    "tvmaze_id": item["tvmaze_id"],
                    "episodes": eps,
                }
            )
        } catch Exception as e:
            print(f"ERROR TVMaze {item['name']}: {e}")

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: wrote {OUT}")


if __name__ == "__main__":
    main()
