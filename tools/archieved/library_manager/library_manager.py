# -*- coding: utf-8 -*-
"""
File: library_manager.py
Project: my_TV_Movie
Tool: Library Manager (Backend Validator/Exporter)
Version: v0.1.2 (2026-01-04)
Path: tools/library_manager/library_manager.py

Reads inputs/*.txt and writes:
  tools/library_manager/out/library_inputs.json
  tools/library_manager/out/validation_report.json

This file stays non-interactive. The UI is library_manager_app.py.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

UA = "my_TV_Movie-LibraryManagerBackend/v0.1.2"

FILE_TV = "tv_list.txt"
FILE_MOVIES = "movies_list.txt"
FILE_WATCHLIST = "watchlist.txt"
FILE_LIVETV = "livetv_list.txt"

SEASON_SPEC_RE = re.compile(r"^\*$|^\d+(\s*,\s*\d+)*$")


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def safe_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="replace")


def json_dump(path: Path, obj: Any) -> None:
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
    if spec == "":
        return True, "ok"
    if not SEASON_SPEC_RE.match(spec):
        return False, "Invalid season spec. Use '*' or comma-separated numbers (e.g., 1,2,3)."
    return True, "ok"


class TMDBClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("API_TMDB_KEY", "") or ""
        self.api_token = os.getenv("API_TMDB_TOKEN", "") or ""
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA})
        if self.api_token:
            self.s.headers.update({"Authorization": f"Bearer {self.api_token}"})

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        params = params or {}
        if self.api_key:
            params.setdefault("api_key", self.api_key)
        return self.s.get(url, params=params, timeout=20)

    def validate_tv(self, tmdb_id: int) -> Tuple[bool, str]:
        r = self._get(f"https://api.themoviedb.org/3/tv/{tmdb_id}", params={"language": "en-US"})
        return (r.status_code == 200, f"HTTP {r.status_code}")

    def validate_movie(self, tmdb_id: int) -> Tuple[bool, str]:
        r = self._get(f"https://api.themoviedb.org/3/movie/{tmdb_id}", params={"language": "en-US"})
        return (r.status_code == 200, f"HTTP {r.status_code}")


@dataclass
class Issue:
    file: str
    line_index: int
    raw: str
    error: str


def load_lines(fp: Path) -> List[str]:
    if not fp.exists():
        return []
    return safe_read_text(fp).splitlines()


def validate_file_format(inputs_dir: Path) -> Tuple[List[Dict[str, Any]], List[Issue]]:
    items: List[Dict[str, Any]] = []
    issues: List[Issue] = []

    def add_issue(file: str, idx: int, raw: str, err: str) -> None:
        issues.append(Issue(file=file, line_index=idx, raw=raw, error=err))

    # movies_list.txt: name|tmdb_movie_id
    fp = inputs_dir / FILE_MOVIES
    for i, ln in enumerate(load_lines(fp)):
        raw = ln.rstrip("\n")
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        active = not is_commented(raw)
        content = uncomment_line(raw).strip()
        parts = split_pipe_line(content)
        if len(parts) < 2:
            add_issue(FILE_MOVIES, i, raw, "Expected: name|tmdb_movie_id")
            continue
        name = parts[0].strip()
        mid = parse_int(parts[1])
        if not name:
            add_issue(FILE_MOVIES, i, raw, "Missing movie name")
            continue
        if mid is None:
            add_issue(FILE_MOVIES, i, raw, "Invalid TMDB movie ID")
            continue
        items.append({"file": FILE_MOVIES, "line_index": i, "active": active, "name": name, "tmdb_id": mid})

    # tv_list.txt: name|tmdb_show_id|season_spec|tvmaze_id
    fp = inputs_dir / FILE_TV
    for i, ln in enumerate(load_lines(fp)):
        raw = ln.rstrip("\n")
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        active = not is_commented(raw)
        content = uncomment_line(raw).strip()
        parts = split_pipe_line(content)
        if len(parts) < 2:
            add_issue(FILE_TV, i, raw, "Expected: name|tmdb_show_id|season_spec|tvmaze_id")
            continue
        name = parts[0].strip()
        sid = parse_int(parts[1])
        season_spec = parts[2].strip() if len(parts) >= 3 else ""
        tvmaze_id = parse_int(parts[3]) if len(parts) >= 4 else None
        if not name:
            add_issue(FILE_TV, i, raw, "Missing show name")
            continue
        if sid is None:
            add_issue(FILE_TV, i, raw, "Invalid TMDB show ID")
            continue
        ok, msg = validate_season_spec(season_spec) if season_spec else (True, "ok")
        if not ok:
            add_issue(FILE_TV, i, raw, msg)
            continue
        items.append(
            {
                "file": FILE_TV,
                "line_index": i,
                "active": active,
                "name": name,
                "tmdb_id": sid,
                "season_spec": season_spec,
                "tvmaze_id": tvmaze_id,
            }
        )

    # watchlist.txt: title|tmdb_id|seasons
    fp = inputs_dir / FILE_WATCHLIST
    for i, ln in enumerate(load_lines(fp)):
        raw = ln.rstrip("\n")
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        active = not is_commented(raw)
        content = uncomment_line(raw).strip()
        parts = split_pipe_line(content)
        if len(parts) < 2:
            add_issue(FILE_WATCHLIST, i, raw, "Expected: title|tmdb_id|seasons")
            continue
        name = parts[0].strip()
        sid = parse_int(parts[1])
        season_spec = parts[2].strip() if len(parts) >= 3 else ""
        if not name:
            add_issue(FILE_WATCHLIST, i, raw, "Missing title")
            continue
        if sid is None:
            add_issue(FILE_WATCHLIST, i, raw, "Invalid TMDB ID")
            continue
        ok, msg = validate_season_spec(season_spec) if season_spec else (True, "ok")
        if not ok:
            add_issue(FILE_WATCHLIST, i, raw, msg)
            continue
        items.append({"file": FILE_WATCHLIST, "line_index": i, "active": active, "name": name, "tmdb_id": sid, "season_spec": season_spec})

    # livetv_list.txt: currently free-form (no strict validation)
    fp = inputs_dir / FILE_LIVETV
    for i, ln in enumerate(load_lines(fp)):
        raw = ln.rstrip("\n")
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        active = not is_commented(raw)
        content = uncomment_line(raw).strip()
        name = split_pipe_line(content)[0].strip() if content else ""
        items.append({"file": FILE_LIVETV, "line_index": i, "active": active, "name": name})

    return items, issues


def validate_tmdb_ids(items: List[Dict[str, Any]], issues: List[Issue]) -> None:
    tmdb = TMDBClient()
    if not (tmdb.api_key or tmdb.api_token):
        issues.append(Issue(file="ENV", line_index=-1, raw="", error="Missing TMDB credentials: set API_TMDB_KEY or API_TMDB_TOKEN"))
        return

    for it in items:
        tmdb_id = it.get("tmdb_id", None)
        if tmdb_id is None:
            continue
        if it["file"] == FILE_MOVIES:
            ok, msg = tmdb.validate_movie(int(tmdb_id))
            if not ok:
                issues.append(Issue(file=it["file"], line_index=int(it["line_index"]), raw="", error=f"{it.get('name','')}: invalid TMDB movie id ({msg})"))
        elif it["file"] in (FILE_TV, FILE_WATCHLIST):
            ok, msg = tmdb.validate_tv(int(tmdb_id))
            if not ok:
                issues.append(Issue(file=it["file"], line_index=int(it["line_index"]), raw="", error=f"{it.get('name','')}: invalid TMDB tv id ({msg})"))


def main(argv: Optional[List[str]] = None) -> int:
    argv = argv or sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--out-dir", default="")
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    inputs_dir = repo_root / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    out_dir = Path(args.out_dir).resolve() if args.out_dir else (repo_root / "tools" / "library_manager" / "out")
    out_dir.mkdir(parents=True, exist_ok=True)

    items, issues = validate_file_format(inputs_dir)
    validate_tmdb_ids(items, issues)

    json_dump(out_dir / "library_inputs.json", {"generated_at": now_stamp(), "repo_root": str(repo_root), "inputs_dir": str(inputs_dir), "items": items})
    json_dump(out_dir / "validation_report.json", {"generated_at": now_stamp(), "repo_root": str(repo_root), "inputs_dir": str(inputs_dir), "issues": [x.__dict__ for x in issues]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
