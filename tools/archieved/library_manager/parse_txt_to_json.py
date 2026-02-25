#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/parse_txt_to_json.py
# [PROJECT] my_TV_Movie
# [ROLE]    Parse plain-text inputs into data/inputs_parsed.json
# [VERSION] v1.1.0
# [UPDATED] 2026-01-03
#
# Notes:
# - Robustly skips comment/header lines even if the file has a UTF-8 BOM (e.g., "\ufeff# ...")
# - Tolerates extra whitespace around "|" separators
# - Auto-corrects the common typo: "Criminal Record204490|204490|*" -> "Criminal Record|204490|*"
# - Keeps existing conventions: writes to data/inputs_parsed.json, logs a one-line summary, then waits for Enter
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import json as _json
import os as _os
import re as _re
import sys as _sys
from pathlib import Path as _Path


def _now_local() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _repo_root() -> _Path:
    # scripts/parse_txt_to_json.py -> repo root is parent of scripts/
    return _Path(__file__).resolve().parents[1]


def _read_lines(fp: _Path) -> list[str]:
    # Preserve non-ASCII titles; be resilient to odd bytes
    txt = fp.read_text(encoding="utf-8", errors="replace")
    return txt.splitlines()


def _is_comment_or_blank(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    # Handle BOM at start of file/line
    s = s.lstrip("\ufeff").lstrip()
    return s.startswith("#")


def _split_pipes(line: str) -> list[str]:
    # Split on | with optional whitespace around it
    parts = [p.strip() for p in _re.split(r"\s*\|\s*", line.strip())]
    # Drop empty tail parts (e.g., trailing "|")
    while parts and parts[-1] == "":
        parts.pop()
    return parts


def _fix_common_title_id_glue(parts: list[str]) -> list[str]:
    """
    Fix: "Criminal Record204490|204490|*" -> ["Criminal Record", "204490", "*"]
    Only when:
      - parts has 3 elements
      - parts[0] ends with digits
      - trailing digits == parts[1]
    """
    if len(parts) != 3:
        return parts
    title = parts[0]
    tmdb_id = parts[1]
    m = _re.match(r"^(.*?)(\d{4,10})$", title)
    if not m:
        return parts
    prefix, tail_digits = m.group(1), m.group(2)
    if tail_digits == tmdb_id and prefix.strip():
        return [prefix.strip(), tmdb_id.strip(), parts[2].strip()]
    return parts


def _parse_tv_list(fp: _Path) -> tuple[list[dict], int]:
    tv: list[dict] = []
    errors = 0

    for raw in _read_lines(fp):
        if _is_comment_or_blank(raw):
            continue

        # Remove BOM if it leaked into a non-comment line
        line = raw.lstrip("\ufeff").strip()
        parts = _split_pipes(line)
        parts = _fix_common_title_id_glue(parts)

        # Expected: title | tmdb_id | season_or_star (optional)
        if len(parts) < 2:
            errors += 1
            continue

        title = parts[0].strip()
        tmdb_id = parts[1].strip()

        if not title or not tmdb_id or not tmdb_id.isdigit():
            errors += 1
            continue

        season = None
        if len(parts) >= 3 and parts[2]:
            # keep raw value; caller can interpret "*" or specific season number
            season = parts[2].strip()

        tv.append(
            {
                "title": title,
                "tmdb_id": int(tmdb_id),
                "first_air_date": None,  # filled later by TMDB fetch
                "season": season,
            }
        )

    return tv, errors


def _parse_movies_list(fp: _Path) -> tuple[list[dict], int]:
    movies: list[dict] = []
    errors = 0

    for raw in _read_lines(fp):
        if _is_comment_or_blank(raw):
            continue

        line = raw.lstrip("\ufeff").strip()
        parts = _split_pipes(line)

        # Expected: title | tmdb_id
        if len(parts) < 2:
            errors += 1
            continue

        title = parts[0].strip()
        tmdb_id = parts[1].strip()

        if not title or not tmdb_id or not tmdb_id.isdigit():
            errors += 1
            continue

        movies.append(
            {
                "title": title,
                "tmdb_id": int(tmdb_id),
                "release_date": None,  # filled later by TMDB fetch
            }
        )

    return movies, errors


def _parse_watchlist(fp: _Path) -> tuple[list[dict], int]:
    wl: list[dict] = []
    errors = 0

    for raw in _read_lines(fp):
        if _is_comment_or_blank(raw):
            continue

        line = raw.lstrip("\ufeff").strip()
        parts = _split_pipes(line)

        # Tolerate:
        #   type | title | tmdb_id
        #   title | tmdb_id
        if len(parts) == 2:
            item_type = None
            title, tmdb_id = parts
        elif len(parts) >= 3:
            item_type = parts[0].lower() if parts[0] else None
            title, tmdb_id = parts[1], parts[2]
        else:
            errors += 1
            continue

        title = (title or "").strip()
        tmdb_id = (tmdb_id or "").strip()

        if not title or not tmdb_id or not tmdb_id.isdigit():
            errors += 1
            continue

        wl.append(
            {
                "type": item_type,
                "title": title,
                "tmdb_id": int(tmdb_id),
            }
        )

    return wl, errors


def main() -> int:
    root = _repo_root()

    inputs_dir = root / "inputs"
    tv_fp = inputs_dir / "tv_list.txt"
    movies_fp = inputs_dir / "movies_list.txt"
    watch_fp = inputs_dir / "watchlist.txt"

    out_dir = root / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_fp = out_dir / "inputs_parsed.json"

    tv, e1 = _parse_tv_list(tv_fp) if tv_fp.exists() else ([], 0)
    movies, e2 = _parse_movies_list(movies_fp) if movies_fp.exists() else ([], 0)
    watchlist, e3 = _parse_watchlist(watch_fp) if watch_fp.exists() else ([], 0)

    payload = {
        "generated_local": _now_local(),
        "tv": tv,
        "movies": movies,
        "watchlist": watchlist,
    }

    out_fp.write_text(_json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{_now_local()} | [parse_txt_to_json] wrote {out_fp.as_posix()}")
    print(f"{_now_local()} | tv={len(tv)} movies={len(movies)} watchlist={len(watchlist)} errors={e1+e2+e3}")

    try:
        input("Press Enter to close...")
    except EOFError:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
