#!/usr/bin/env python
# =============================================================================
# File: scripts/fetch_live_tv.py
# Project: my_TV_Movie
# Version: v1.0.0 (2025-11-09)
#
# Purpose:
#   Read live_tv_list.txt and inject a `live_tv` array into data.json.
#   Used by the Live TV tab (guide-style skeleton, no EPG yet).
# =============================================================================

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE_FILE = ROOT / "live_tv_list.txt"
DATA_FILE = ROOT / "data" / "data.json"


def log(msg: str) -> None:
    print(f"[fetch_live_tv] {msg}", flush=True)


def load_data():
    if not DATA_FILE.exists():
        log("data.json missing; run fetch_tmdb.py first.")
        return None
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log("Updated data.json with live_tv entries.")


def parse_live_tv():
    if not LIVE_FILE.exists():
        log("live_tv_list.txt not found; skipping.")
        return []
    lines = LIVE_FILE.read_text(encoding="utf-8").splitlines()
    items = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or set(line) == {"-"}:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 1:
            continue
        name = parts[0]
        country = parts[1] if len(parts) > 1 else ""
        group = parts[2] if len(parts) > 2 else ""
        logo = parts[3] if len(parts) > 3 else ""
        epg_hint = parts[4] if len(parts) > 4 else ""
        items.append(
            {
                "name": name,
                "country": country,
                "group": group,
                "logo": logo,
                "epg_hint": epg_hint,
            }
        )
    log(f"Parsed {len(items)} live_tv entries.")
    return items


def main():
    data = load_data()
    if data is None:
        return
    data["live_tv"] = parse_live_tv()
    save_data(data)


if __name__ == "__main__":
    main()
