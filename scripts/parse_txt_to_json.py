#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/parse_txt_to_json.py
# [PROJECT] my_TV_Movie
# [ROLE]    Parse TXT inputs → deterministic intermediate JSON for TMDB build
# [VERSION] v1.0.0
# [UPDATED] 2025-12-20_00-00-00
#
# [PIPELINE]
# TXT → parse_txt_to_json.py → JSON → fetch_tmdb.py → data/data.json → ...
#
# [INPUTS] (first-found wins; supports legacy locations)
# - inputs/tv_list.txt   OR tv_list.txt
# - inputs/movies_list.txt OR movies_list.txt
# - inputs/watchlist.txt OR watchlist.txt
#
# [OUTPUT]
# - data/inputs_parsed.json
#
# [RULES]
# - Handle extra spaces and inconsistent " | " formatting.
# - TV season rules:
#   - If season_spec missing/blank/"*" => all seasons (season_mode="all", seasons=null)
#   - If "1" / "S1" / "Season 1" => [1]
#   - If "1,2,3" => [1,2,3]
#   - If "1-5" => [1,2,3,4,5]
# - Never crash on a single bad line; capture to errors[] and continue.
# - Deterministic ordering: preserve file order.
# - No schema changes to data/data.json here; this is intermediate only.
# ==============================================================================

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None  # noqa

# -------------------------
# Constants / paths
# -------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
OUT_JSON = DATA_DIR / "inputs_parsed.json"

TV_CANDIDATES = [REPO_ROOT / "inputs" / "tv_list.txt", REPO_ROOT / "tv_list.txt"]
MOV_CANDIDATES = [REPO_ROOT / "inputs" / "movies_list.txt", REPO_ROOT / "movies_list.txt"]
WCH_CANDIDATES = [REPO_ROOT / "inputs" / "watchlist.txt", REPO_ROOT / "watchlist.txt"]

RE_COMMENT = re.compile(r"^\s*#")
RE_PIPE_SPLIT = re.compile(r"\s*\|\s*")
RE_YEAR_PAREN = re.compile(r"\((\d{4})\)\s*$", re.IGNORECASE)
RE_S_TOKEN = re.compile(r"^\s*(?:s|season)\s*(\d+)\s*$", re.IGNORECASE)
RE_RANGE = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")
RE_LIST = re.compile(r"^\s*(\d+)(\s*,\s*\d+)+\s*$")


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _first_existing(candidates: List[Path]) -> Optional[Path]:
    for p in candidates:
        if p.exists():
            return p
    return None


def _split_pipe(line: str) -> List[str]:
    # tolerate extra pipes, extra spaces
    parts = RE_PIPE_SPLIT.split(line.strip())
    # do NOT drop interior empties; trim only ends to support "title|"
    while parts and parts[-1] == "":
        parts.pop()
    return [p.strip() for p in parts]


def _parse_title_year(title_raw: str) -> Tuple[str, Optional[int]]:
    t = (title_raw or "").strip()
    if not t:
        return "", None
    m = RE_YEAR_PAREN.search(t)
    if m:
        year = int(m.group(1))
        t2 = t[: m.start()].strip()
        return t2, year
    return t, None


def _parse_int(s: str) -> Optional[int]:
    s2 = (s or "").strip()
    if not s2:
        return None
    if s2 == "*":
        return None
    try:
        return int(s2)
    except Exception:
        return None


def _parse_season_spec(spec_raw: str) -> Tuple[str, Optional[List[int]]]:
    s = (spec_raw or "").strip()
    if not s or s == "*":
        return "all", None

    m = RE_S_TOKEN.match(s)
    if m:
        n = int(m.group(1))
        return "list", [n]

    m = RE_RANGE.match(s)
    if m:
        a = int(m.group(1))
        b = int(m.group(2))
        if a <= 0 or b <= 0:
            return "all", None
        if a > b:
            a, b = b, a
        return "list", list(range(a, b + 1))

    if RE_LIST.match(s):
        nums = [int(x.strip()) for x in s.split(",") if x.strip().isdigit()]
        nums = [n for n in nums if n > 0]
        if not nums:
            return "all", None
        # dedupe but preserve order
        seen = set()
        out: List[int] = []
        for n in nums:
            if n not in seen:
                seen.add(n)
                out.append(n)
        return "list", out

    # single number
    if s.isdigit():
        n = int(s)
        if n > 0:
            return "list", [n]

    # unknown spec => treat as all, but record raw
    return "all", None


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{ts} | {msg}")


def main() -> int:
    if load_dotenv:
        # local support (no override)
        load_dotenv(dotenv_path=REPO_ROOT / ".env", override=False)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    tv_path = _first_existing(TV_CANDIDATES)
    mov_path = _first_existing(MOV_CANDIDATES)
    wch_path = _first_existing(WCH_CANDIDATES)

    errors: List[Dict[str, Any]] = []
    out: Dict[str, Any] = {
        "meta": {
            "generated_at_utc": _now_utc_iso(),
            "repo_root": str(REPO_ROOT).replace("\\", "/"),
            "inputs": {
                "tv_list": str(tv_path).replace("\\", "/") if tv_path else None,
                "movies_list": str(mov_path).replace("\\", "/") if mov_path else None,
                "watchlist": str(wch_path).replace("\\", "/") if wch_path else None,
            },
        },
        "tv": [],
        "movies": [],
        "watchlist": [],
        "errors": errors,
    }

    # -------------------------
    # TV
    # -------------------------
    if not tv_path:
        errors.append({"type": "missing_file", "file": "tv_list.txt", "message": "tv_list not found (inputs/ or repo root)"})
    else:
        lines = _read_text(tv_path).splitlines()
        for i, raw in enumerate(lines, start=1):
            if not raw.strip() or RE_COMMENT.match(raw):
                continue
            try:
                parts = _split_pipe(raw)
                # format: name | tmdb_show_id | season_spec | tvmaze_id
                name_raw = parts[0] if len(parts) >= 1 else ""
                tmdb_raw = parts[1] if len(parts) >= 2 else ""
                season_raw = parts[2] if len(parts) >= 3 else ""
                tvmaze_raw = parts[3] if len(parts) >= 4 else ""

                title, year = _parse_title_year(name_raw)
                tmdb_id = _parse_int(tmdb_raw)
                tvmaze_id = _parse_int(tvmaze_raw)

                season_mode, seasons = _parse_season_spec(season_raw)

                out["tv"].append(
                    {
                        "source_file": "tv_list",
                        "source_line": i,
                        "raw": raw.rstrip("\n"),
                        "title": title,
                        "year": year,
                        "tmdb_id": tmdb_id,
                        "season_spec_raw": (season_raw or "").strip() or None,
                        "season_mode": season_mode,   # "all" or "list"
                        "seasons": seasons,           # null if all
                        "tvmaze_id": tvmaze_id,
                    }
                )
            except Exception as ex:
                errors.append(
                    {
                        "type": "parse_error",
                        "file": "tv_list",
                        "line": i,
                        "raw": raw.rstrip("\n"),
                        "message": str(ex),
                    }
                )

    # -------------------------
    # Movies
    # -------------------------
    if not mov_path:
        errors.append({"type": "missing_file", "file": "movies_list.txt", "message": "movies_list not found (inputs/ or repo root)"})
    else:
        lines = _read_text(mov_path).splitlines()
        for i, raw in enumerate(lines, start=1):
            if not raw.strip() or RE_COMMENT.match(raw):
                continue
            try:
                parts = _split_pipe(raw)
                # format: name|tmdb_movie_id
                name_raw = parts[0] if len(parts) >= 1 else ""
                tmdb_raw = parts[1] if len(parts) >= 2 else ""

                title, year = _parse_title_year(name_raw)
                tmdb_id = _parse_int(tmdb_raw)

                out["movies"].append(
                    {
                        "source_file": "movies_list",
                        "source_line": i,
                        "raw": raw.rstrip("\n"),
                        "title": title,
                        "year": year,
                        "tmdb_id": tmdb_id,
                    }
                )
            except Exception as ex:
                errors.append(
                    {
                        "type": "parse_error",
                        "file": "movies_list",
                        "line": i,
                        "raw": raw.rstrip("\n"),
                        "message": str(ex),
                    }
                )

    # -------------------------
    # Watchlist (pass-through; used downstream)
    # -------------------------
    if wch_path and wch_path.exists():
        lines = _read_text(wch_path).splitlines()
        for i, raw in enumerate(lines, start=1):
            if not raw.strip() or RE_COMMENT.match(raw):
                continue
            out["watchlist"].append({"source_file": "watchlist", "source_line": i, "raw": raw.rstrip("\n")})

    # deterministic write
    tmp = OUT_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(OUT_JSON)

    _log(f"[parse_txt_to_json] wrote {OUT_JSON.as_posix()}")
    _log(f"tv={len(out['tv'])} movies={len(out['movies'])} watchlist={len(out['watchlist'])} errors={len(errors)}")

    # GH Actions must not wait; local interactive can
    if sys.stdin.isatty():
        try:
            input("Press Enter to close...")
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
