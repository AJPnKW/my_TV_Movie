>>> FILE: tools/library_manager/library_manager.py
# library_manager.py
# my_TV_Movie - TXT validator + JSON exporter (backend for future GUI)
# Version: v0.1.1 (2026-01-03)
# - Parses: movies_list.txt, tv_list.txt, watchlist.txt, livetv_list.txt (if present)
# - Supports commented entries (inactive) with leading '#'
# - Validates formatting + IDs + season specs
# - Exports: out/library_inputs.json and out/validation_report.json
#
# Env: API_TMDB_KEY (preferred) OR API_TMDB_TOKEN (Bearer token)
#
# Notes:
# - This is a non-interactive utility (CLI) used by the UI and for batch QA.
# - It does NOT modify your inputs unless explicitly asked to (it reads + reports).
#
# Usage:
#   python tools/library_manager/library_manager.py --repo-root "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
#   python tools/library_manager/library_manager.py --repo-root .. --out-dir tools/library_manager/out

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

UA = "my_TV_Movie-LibraryManagerBackend/0.1.1"

FILE_TV = "tv_list.txt"
FILE_MOVIES = "movies_list.txt"
FILE_WATCHLIST = "watchlist.txt"
FILE_LIVETV = "livetv_list.txt"

SEASON_SPEC_RE = re.compile(r"^\*$|^\d+(\s*[,]\s*\d+)*$")


def now_stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def safe_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="replace")


def json_dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_write_text(path, json.dumps(obj, indent=2, ensure_ascii=False))


def is_commented(line: str) -> bool:
    return line.lstrip().startswith("#")


def uncomment_line(line: str) -> str:
    m = re.match(r"^(\s*)#\s?(.*)$", line)
    if not m:
        return line
    return f"{m.group(1)}{m.group(2)}"


def split_pipe_line(line: str) -> List[str]:
    return [p.strip() for p in line.split("|")]


def parse_int(s: str) -> Optional[int]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return int(s)
    except Exception:
        return None


def validate_season_spec(spec: str) -> Tuple[bool, str]:
    spec = (spec or "").strip()
    if spec == "" or SEASON_SPEC_RE.match(spec):
        return True, "ok"
    return False, "Invalid season spec. Use '*' or comma-separated numbers (e.g., 1,2,3)."


class TMDBClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("API_TMDB_KEY", "") or ""
        self.api_token = os.getenv("API_TMDB_TOKEN", "") or ""

    def headers(self) -> Dict[str, str]:
        h = {"User-Agent": UA}
        if self.api_token:
            h["Authorization"] = f"Bearer {self.api_token}"
        return h

    def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        params = params or {}
        if self.api_key:
            params.setdefault("api_key", self.api_key)
        return requests.get(url, params=params, headers=self.headers(), timeout=20)

    def validate_tv_id(self, tmdb_id: int) -> Tuple[bool, str]:
        r = self.get(f"https://api.themoviedb.org/3/tv/{tmdb_id}", params={"language": "en-US"})
        if r.status_code == 200:
            return True, "ok"
        return False, f"TMDB TV ID not found/invalid (HTTP {r.status_code})"

    def validate_movie_id(self, tmdb_id: int) -> Tuple[bool, str]:
        r = self.get(f"https://api.themoviedb.org/3/movie/{tmdb_id}", params={"language": "en-US"})
        if r.status_code == 200:
            return True, "ok"
        return False, f"TMDB Movie ID not found/invalid (HTTP {r.status_code})"


@dataclass
class Issue:
    file: str
    line_index: int
    raw: str
    error: str


@dataclass
class Item:
    file: str
    active: bool
    name: str
    tmdb_id: Optional[int]
    season_spec: str = ""
    tvmaze_id: Optional[int] = None
    parse_ok: bool = True
    parse_error: str = ""


def parse_tv_line(line: str) -> Tuple[Optional[Item], Optional[Issue]]:
    raw = line.rstrip("\n")
    if not raw.strip() or raw.strip().startswith("# File:") or raw.strip().startswith("# Project:") or raw.strip().startswith("# Version:") or raw.strip().startswith("# format:"):
        return None, None

    active = not is_commented(raw)
    content = uncomment_line(raw).strip()
    parts = split_pipe_line(content)

    if len(parts) < 2:
        return None, Issue(FILE_TV, -1, raw, "Expected format: name|tmdb_show_id|season_spec|tvmaze_id")

    name = parts[0].strip()
    tmdb_id = parse_int(parts[1])
    season_spec = parts[2].strip() if len(parts) >= 3 else ""
    tvmaze_id = parse_int(parts[3]) if len(parts) >= 4 else None

    if not name:
        return None, Issue(FILE_TV, -1, raw, "Missing show name")
    if tmdb_id is None:
        return None, Issue(FILE_TV, -1, raw, "Invalid TMDB show ID")

    ok, msg = validate_season_spec(season_spec) if season_spec else (True, "ok")
    if not ok:
        return None, Issue(FILE_TV, -1, raw, msg)

    return Item(FILE_TV, active, name, tmdb_id, season_spec, tvmaze_id, True, ""), None


def parse_movies_line(line: str) -> Tuple[Optional[Item], Optional[Issue]]:
    raw = line.rstrip("\n")
    if not raw.strip() or raw.strip().startswith("# File:") or raw.strip().startswith("# Project:") or raw.strip().startswith("# Version:") or raw.strip().startswith("# format:"):
        return None, None

    active = not is_commented(raw)
    content = uncomment_line(raw).strip()
    parts = split_pipe_line(content)

    if len(parts) < 2:
        return None, Issue(FILE_MOVIES, -1, raw, "Expected format: name|tmdb_movie_id")

    name = parts[0].strip()
    tmdb_id = parse_int(parts[1])

    if not name:
        return None, Issue(FILE_MOVIES, -1, raw, "Missing movie name")
    if tmdb_id is None:
        return None, Issue(FILE_MOVIES, -1, raw, "Invalid TMDB movie ID")

    return Item(FILE_MOVIES, active, name, tmdb_id, "", None, True, ""), None


def parse_watchlist_line(line: str) -> Tuple[Optional[Item], Optional[Issue]]:
    raw = line.rstrip("\n")
    if not raw.strip() or raw.strip().startswith("# File:") or raw.strip().startswith("# Project:") or raw.strip().startswith("# Version:") or raw.strip().startswith("# format:"):
        return None, None

    active = not is_commented(raw)
    content = uncomment_line(raw).strip()
    parts = split_pipe_line(content)

    if len(parts) < 2:
        return None, Issue(FILE_WATCHLIST, -1, raw, "Expected format: title|tmdb_id|seasons")

    name = parts[0].strip()
    tmdb_id = parse_int(parts[1])
    season_spec = parts[2].strip() if len(parts) >= 3 else ""

    if not name:
        return None, Issue(FILE_WATCHLIST, -1, raw, "Missing title")
    if tmdb_id is None:
        return None, Issue(FILE_WATCHLIST, -1, raw, "Invalid TMDB ID")

    ok, msg = validate_season_spec(season_spec) if season_spec else (True, "ok")
    if not ok:
        return None, Issue(FILE_WATCHLIST, -1, raw, msg)

    return Item(FILE_WATCHLIST, active, name, tmdb_id, season_spec, None, True, ""), None


def load_items_and_issues(inputs_dir: Path) -> Tuple[List[Item], List[Issue]]:
    items: List[Item] = []
    issues: List[Issue] = []

    files = [
        (FILE_MOVIES, parse_movies_line),
        (FILE_TV, parse_tv_line),
        (FILE_WATCHLIST, parse_watchlist_line),
    ]

    for fname, parser in files:
        fp = inputs_dir / fname
        if not fp.exists():
            continue
        for i, line in enumerate(safe_read_text(fp).splitlines()):
            item, issue = parser(line)
            if issue:
                issue.line_index = i
                issues.append(issue)
            if item:
                items.append(item)

    # livetv_list is allowed to exist; currently treated as free-form (no hard validation)
    fp_live = inputs_dir / FILE_LIVETV
    if fp_live.exists():
        for i, line in enumerate(safe_read_text(fp_live).splitlines()):
            raw = line.rstrip("\n")
            if not raw.strip() or raw.strip().startswith("#"):
                continue
            active = not is_commented(raw)
            content = uncomment_line(raw).strip()
            name = split_pipe_line(content)[0].strip() if content else ""
            items.append(Item(FILE_LIVETV, active, name, None, "", None, True, ""))

    return items, issues


def validate_tmdb_ids(items: List[Item], issues: List[Issue]) -> None:
    tmdb = TMDBClient()
    if not (tmdb.api_key or tmdb.api_token):
        issues.append(Issue("ENV", -1, "", "Missing TMDB credentials: set API_TMDB_KEY or API_TMDB_TOKEN"))
        return

    for it in items:
        if it.tmdb_id is None:
            continue
        if it.file == FILE_MOVIES:
            ok, msg = tmdb.validate_movie_id(it.tmdb_id)
            if not ok:
                issues.append(Issue(it.file, it.line_index if hasattr(it, "line_index") else -1, "", f"{it.name}: {msg}"))
        elif it.file in (FILE_TV, FILE_WATCHLIST):
            ok, msg = tmdb.validate_tv_id(it.tmdb_id)
            if not ok:
                issues.append(Issue(it.file, it.line_index if hasattr(it, "line_index") else -1, "", f"{it.name}: {msg}"))


def main(argv: Optional[List[str]] = None) -> int:
    argv = argv or sys.argv[1:]
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", required=True)
    p.add_argument("--out-dir", default="")
    args = p.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    inputs_dir = repo_root / "inputs"
    out_dir = Path(args.out_dir).resolve() if args.out_dir else (repo_root / "tools" / "library_manager" / "out")
    out_dir.mkdir(parents=True, exist_ok=True)

    items, issues = load_items_and_issues(inputs_dir)

    # write snapshot
    library_inputs_path = out_dir / "library_inputs.json"
    validation_report_path = out_dir / "validation_report.json"

    json_dump(
        library_inputs_path,
        {
            "generated_at": now_stamp(),
            "repo_root": str(repo_root),
            "inputs_dir": str(inputs_dir),
            "items": [it.__dict__ for it in items],
        },
    )

    json_dump(
        validation_report_path,
        {
            "generated_at": now_stamp(),
            "repo_root": str(repo_root),
            "inputs_dir": str(inputs_dir),
            "issues": [iss.__dict__ for iss in issues],
        },
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
<<< END FILE
