\
#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/parse_txt_to_json.py
# [PROJECT] my_TV_Movie
# [ROLE]    Parse plain-text inputs/*.txt into data/inputs_parsed.json
# [VERSION] v1.2.0
# [UPDATED] 2026-01-03
# [BUILD]   14.01.07
#
# Fix: robustly locate tv + movies input files (filename drift tolerant) and
#      parse both "name|id" and "name | id | ..." formats.
# ==============================================================================

from __future__ import annotations

import json
import os
import sys
import re
import datetime as _dt
from typing import Any, Dict, List, Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INPUT_DIR = os.path.join(REPO_ROOT, "inputs")
OUT_PATH = os.path.join(REPO_ROOT, "data", "inputs_parsed.json")
LOG_DIR = os.path.join(REPO_ROOT, "logs")


def _ts_local() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ensure_dirs() -> None:
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)


def _log(msg: str) -> None:
    print(f"{_ts_local()} | [parse_txt_to_json] {msg}")


def _read_text(path: str) -> str:
    # tolerate odd encodings + BOM
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def _pick_existing(candidates: List[str]) -> str | None:
    for rel in candidates:
        p = os.path.join(INPUT_DIR, rel)
        if os.path.isfile(p):
            return p
    return None


_COMMENT_RE = re.compile(r"^\s*(#|;|//)")
_WS = re.compile(r"\s+")


def _split_pipe(line: str) -> List[str]:
    # Accept both "a|b" and "a | b | c" and trim whitespace.
    parts = [p.strip() for p in line.split("|")]
    # Drop empty trailing parts (common when line ends with '|')
    while parts and parts[-1] == "":
        parts.pop()
    return parts


def _norm_title(s: str) -> str:
    return _WS.sub(" ", (s or "").strip())


def _parse_tv_lines(text: str) -> Tuple[List[Dict[str, Any]], int]:
    out: List[Dict[str, Any]] = []
    errors = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or _COMMENT_RE.match(line):
            continue
        parts = _split_pipe(line)
        # Expected: name | tmdb_show_id | season_spec | tvmaze_id
        # But allow: name|tmdb_show_id (minimal)
        if len(parts) < 2:
            errors += 1
            continue
        title = _norm_title(parts[0])
        tmdb_id = (parts[1] or "").strip()
        if not title or not tmdb_id.isdigit():
            errors += 1
            continue
        season_spec = (parts[2] or "").strip() if len(parts) >= 3 else ""
        tvmaze_id = (parts[3] or "").strip() if len(parts) >= 4 else ""
        item: Dict[str, Any] = {
            "title": title,
            "tmdb_id": int(tmdb_id),
        }
        if season_spec:
            item["season_spec"] = season_spec
        if tvmaze_id.isdigit():
            item["tvmaze_id"] = int(tvmaze_id)
        out.append(item)
    return out, errors


def _parse_movie_lines(text: str) -> Tuple[List[Dict[str, Any]], int]:
    out: List[Dict[str, Any]] = []
    errors = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or _COMMENT_RE.match(line):
            continue
        parts = _split_pipe(line)
        # Expected: name|tmdb_movie_id
        if len(parts) < 2:
            errors += 1
            continue
        title = _norm_title(parts[0])
        tmdb_id = (parts[1] or "").strip()
        if not title or not tmdb_id.isdigit():
            errors += 1
            continue
        out.append({"title": title, "tmdb_id": int(tmdb_id)})
    return out, errors


def _parse_watchlist_lines(text: str) -> Tuple[List[Dict[str, Any]], int]:
    # Preserve existing behavior: accept flexible "type|id" or "name|id"
    out: List[Dict[str, Any]] = []
    errors = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or _COMMENT_RE.match(line):
            continue
        parts = _split_pipe(line)
        if len(parts) < 2:
            errors += 1
            continue
        a = (parts[0] or "").strip()
        b = (parts[1] or "").strip()
        if b.isdigit():
            out.append({"title": _norm_title(a), "tmdb_id": int(b)})
        else:
            errors += 1
    return out, errors


def main() -> int:
    _ensure_dirs()

    # Filename drift tolerant (covers older/newer naming).
    tv_path = _pick_existing(["tv_list.txt", "shows_list.txt", "tv.txt", "shows.txt"])
    mv_path = _pick_existing(["movies_list.txt", "movie_list.txt", "movies.txt"])
    wl_path = _pick_existing(["watchlist.txt"])

    if not tv_path:
        _log("WARNING tv input not found in inputs/. Expected one of: tv_list.txt, shows_list.txt, tv.txt, shows.txt")
    else:
        _log(f"tv_input={tv_path}")

    if not mv_path:
        _log("WARNING movies input not found in inputs/. Expected one of: movies_list.txt, movie_list.txt, movies.txt")
    else:
        _log(f"movies_input={mv_path}")

    if not wl_path:
        _log("WARNING watchlist input not found in inputs/. Expected: watchlist.txt")
    else:
        _log(f"watchlist_input={wl_path}")

    tv_items: List[Dict[str, Any]] = []
    mv_items: List[Dict[str, Any]] = []
    wl_items: List[Dict[str, Any]] = []
    err = 0

    if tv_path:
        tv_items, e = _parse_tv_lines(_read_text(tv_path))
        err += e

    if mv_path:
        mv_items, e = _parse_movie_lines(_read_text(mv_path))
        err += e

    if wl_path:
        wl_items, e = _parse_watchlist_lines(_read_text(wl_path))
        err += e

    payload: Dict[str, Any] = {
        "generated_local": _dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "generated_utc": _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tv": tv_items,
        "movies": mv_items,
        "watchlist": wl_items,
    }

    with open(OUT_PATH, "w", encoding="utf-8", errors="replace") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    _log(f"wrote {OUT_PATH.replace(os.sep, '/')}")
    _log(f"tv={len(tv_items)} movies={len(mv_items)} watchlist={len(wl_items)} errors={err}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
