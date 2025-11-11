# =============================================================================
# File: scripts/fetch_tvmaze.py
# Project: my_TV_Movie
# Version: v1.0.1 (2025-11-10)
#
# Purpose:
#   Optional helper to dump raw TVMaze episode data for shows
#   that specify a tvmaze_id in tv_list.txt.
#
#   Output:
#     data/tvmaze_raw.json
#
# Behavior:
#   - If API_TVMAZE_KEY is missing -> log + exit(0) (does NOT break pipeline).
#   - If tv_list.txt has no tvmaze_id entries -> writes empty structure.
#
# Notes:
#   - Does NOT modify data.json.
#   - Main UI still driven by TMDB; this is for cross-checking & future merge.
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


def log(msg: str) -> None:
    print(f"[fetch_tvmaze] {msg}", flush=True)


def tvmaze_get(path: str, params=None):
    url = f"{BASE_TVMAZE}{path}"
    headers = {}
    if TVMAZE_KEY:
        headers["X-API-Key"] = TVMAZE_KEY
    r = requests.get(url, headers=headers, params=params or {}, timeout=20)
    r.raise_for_status()
    return r.json()


def parse_tv_list():
    if not TV_LIST.exists():
        log("tv_list.txt missing; nothing to do.")
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
    log(f"Found {len(items)} shows with tvmaze_id.")
    return items


def main():
    # Soft-fail if no key; we do NOT want to break the whole workflow.
    if not TVMAZE_KEY:
        log("API_TVMAZE_KEY not set; skipping TVMaze fetch.")
        # Still write a predictable empty file for debugging.
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        empty = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "shows": [],
            "note": "Skipped: missing API_TVMAZE_KEY",
        }
        OUT.write_text(json.dumps(empty, ensure_ascii=False, indent=2), encoding="utf-8")
        return

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
        except Exception as e:  # noqa: BLE001
            log(f"ERROR TVMaze {item['name']} ({item['tvmaze_id']}): {e}")

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"OK: wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
