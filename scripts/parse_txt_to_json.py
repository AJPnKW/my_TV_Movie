#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/parse_txt_to_json.py
# [PROJECT] my_TV_Movie
# [ROLE]    Parse inputs/*.txt into data/inputs_parsed.json
# [VERSION] v1.3.0
# [UPDATED] 2026-01-03_00-00-00
# [BUILD]   14.01.07
#
# NOTE:
# - Never blocks CI. Local "Press Enter" only if PARSE_TXT_PAUSE=1.
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import json
import os
import sys
from typing import Any, Dict, List

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INPUTS_DIR = os.path.join(REPO_ROOT, "inputs")
DATA_DIR = os.path.join(REPO_ROOT, "data")
OUT_JSON = os.path.join(DATA_DIR, "inputs_parsed.json")


def _ts() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _read_lines(path: str) -> List[str]:
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        # utf-8-sig strips BOM if present
        raw = f.read().splitlines()
    # drop blanks + comment lines (leading #)
    out: List[str] = []
    for line in raw:
        s = (line or "").strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        out.append(s)
    return out


def _parse_tmdb_id(line: str) -> str | None:
    # accepted formats:
    #   Title | tmdb_id=12345
    #   12345
    #   tmdb_id=12345
    if "tmdb_id=" in line:
        try:
            right = line.split("tmdb_id=", 1)[1].strip()
            # strip anything after separators
            for sep in ("|", ",", ";"):
                if sep in right:
                    right = right.split(sep, 1)[0].strip()
            return right if right.isdigit() else None
        except Exception:
            return None
    s = line.strip()
    return s if s.isdigit() else None


def _parse_title(line: str) -> str:
    # title is text before first |
    if "|" in line:
        return line.split("|", 1)[0].strip()
    return line.strip()


def _build_list(lines: List[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    errs = 0
    for line in lines:
        tid = _parse_tmdb_id(line)
        title = _parse_title(line)
        if not tid:
            errs += 1
            continue
        items.append({"title": title, "tmdb_id": tid, "first_air_date": None})
    return items


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)

    tv_lines = _read_lines(os.path.join(INPUTS_DIR, "tv_list.txt"))
    mv_lines = _read_lines(os.path.join(INPUTS_DIR, "movies_list.txt"))
    wl_lines = _read_lines(os.path.join(INPUTS_DIR, "watchlist.txt"))

    tv = _build_list(tv_lines)
    movies = _build_list(mv_lines)
    watchlist = [s for s in wl_lines]

    out = {
        "generated_local": _ts(),
        "tv": tv,
        "movies": movies,
        "watchlist": watchlist,
    }

    with open(OUT_JSON, "w", encoding="utf-8", errors="replace", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"{_ts()} | [parse_txt_to_json] wrote {OUT_JSON.replace(os.sep, '/')}")
    print(f"{_ts()} | tv={len(tv)} movies={len(movies)} watchlist={len(watchlist)} errors=0")

    if os.environ.get("PARSE_TXT_PAUSE", "").strip() == "1":
        try:
            input("Press Enter to close...")
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
