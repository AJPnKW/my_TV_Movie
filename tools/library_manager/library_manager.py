# >>> FILE: tools/library_manager/library_manager.py
# library_manager.py
# my_TV_Movie - TXT validator + JSON exporter (backend for future GUI)
# Version: v0.1.0 (2026-01-03)
#
# Note:
#   This file is optional if you are using library_manager_app.py.
#   It remains here as a standalone validator/exporter.

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

def _ensure_deps() -> None:
    try:
        import requests  # noqa: F401
    except Exception:
        import subprocess
        print("[deps] Installing requests ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])

_ensure_deps()
import requests  # noqa: E402


class Logger:
    def __init__(self, log_path: str) -> None:
        self.log_path = log_path

    def _write(self, level: str, msg: str) -> None:
        ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {level} {msg}"
        print(line)
        with open(self.log_path, "a", encoding="utf-8", errors="replace") as f:
            f.write(line + "\n")

    def info(self, msg: str) -> None:
        self._write("INFO ", msg)

    def warn(self, msg: str) -> None:
        self._write("WARN ", msg)

    def error(self, msg: str) -> None:
        self._write("ERROR", msg)


@dataclass
class InputRecord:
    kind: str
    active: bool
    name: str
    tmdb_id: Optional[int]
    season_spec: Optional[str] = None
    tvmaze_id: Optional[int] = None
    source_file: str = ""
    line_no: int = 0
    raw_line: str = ""


@dataclass
class ValidationIssue:
    severity: str
    code: str
    message: str
    source_file: str
    line_no: int
    raw_line: str


_SPLIT_RE = re.compile(r"\s*\|\s*")


def _is_header_or_comment_only(line: str) -> bool:
    s = line.strip()
    return (
        (not s)
        or s.startswith("# File:")
        or s.startswith("# Project:")
        or s.startswith("# Version:")
        or s.startswith("# format:")
        or s.startswith("#Title|")
        or s.startswith("# Title|")
        or s == "#"
    )


def _parse_int(value: str) -> Optional[int]:
    v = value.strip()
    if v == "":
        return None
    if not v.isdigit():
        return None
    try:
        return int(v)
    except Exception:
        return None


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip())


def _progress(cur: int, total: int, prefix: str = "") -> str:
    if total <= 0:
        return f"{prefix}0/0"
    width = 30
    filled = int((cur / total) * width)
    bar = "#" * filled + "-" * (width - filled)
    return f"{prefix}[{bar}] {cur}/{total}"


def _parse_season_spec(spec: str) -> Tuple[bool, List[int], Optional[str]]:
    s = spec.strip()
    if s == "":
        return True, [], None
    if s == "*":
        return True, [], "*"

    parts = [p.strip() for p in s.split(",") if p.strip()]
    seasons: List[int] = []

    for p in parts:
        if "-" in p:
            a, b = [x.strip() for x in p.split("-", 1)]
            if not (a.isdigit() and b.isdigit()):
                return False, [], None
            ia, ib = int(a), int(b)
            if ia <= 0 or ib <= 0 or ib < ia:
                return False, [], None
            seasons.extend(list(range(ia, ib + 1)))
        else:
            if not p.isdigit():
                return False, [], None
            i = int(p)
            if i <= 0:
                return False, [], None
            seasons.append(i)

    seasons = sorted(set(seasons))
    norm = ",".join(str(x) for x in seasons)
    return True, seasons, norm


class TMDBClient:
    def __init__(self, logger: Logger) -> None:
        self.logger = logger
        self.base = "https://api.themoviedb.org/3"
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

        key = os.getenv("API_TMDB_KEY", "").strip()
        token = os.getenv("API_TMDB_TOKEN", "").strip()

        self.api_key = key if key else None
        self.bearer = token if token else None

        if not self.api_key and not self.bearer:
            self.logger.warn("TMDB auth missing: set API_TMDB_KEY or API_TMDB_TOKEN. TMDB validation will be skipped.")

    def _auth_params(self) -> Dict[str, str]:
        if self.api_key:
            return {"api_key": self.api_key}
        return {}

    def _auth_headers(self) -> Dict[str, str]:
        if self.bearer:
            return {"Authorization": f"Bearer {self.bearer}"}
        return {}

    def _get(self, path: str) -> Tuple[int, Optional[Dict[str, Any]]]:
        url = f"{self.base}{path}"
        try:
            r = self.session.get(url, params=self._auth_params(), headers=self._auth_headers(), timeout=20)
            status = r.status_code
            if status == 200:
                return status, r.json()
            return status, None
        except Exception as e:
            self.logger.warn(f"TMDB request failed for {path}: {e}")
            return 0, None

    def movie_exists(self, tmdb_id: int) -> Tuple[bool, int]:
        if not (self.api_key or self.bearer):
            return True, 0
        status, _ = self._get(f"/movie/{tmdb_id}")
        if status == 200:
            return True, status
        if status == 404:
            return False, status
        return True, status

    def tv_exists_and_season_count(self, tmdb_id: int) -> Tuple[bool, int, int]:
        if not (self.api_key or self.bearer):
            return True, 0, 0
        status, data = self._get(f"/tv/{tmdb_id}")
        if status == 200 and data:
            n = int(data.get("number_of_seasons") or 0)
            return True, status, n
        if status == 404:
            return False, status, 0
        return True, status, 0


def parse_movies(file_path: str) -> Tuple[List[InputRecord], List[ValidationIssue]]:
    recs: List[InputRecord] = []
    issues: List[ValidationIssue] = []

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for idx, line in enumerate(f, start=1):
            raw = line.rstrip("\r\n")
            if _is_header_or_comment_only(raw):
                continue

            active = True
            s = raw.strip()
            if s.startswith("#"):
                active = False
                s = s[1:].strip()
            if not s:
                continue

            parts = _SPLIT_RE.split(s)
            if len(parts) != 2:
                issues.append(ValidationIssue("error", "MOVIES_FORMAT", "movies_list.txt line must be: name|tmdb_movie_id", os.path.basename(file_path), idx, raw))
                continue

            name = _normalize_name(parts[0])
            tmdb_id = _parse_int(parts[1])

            if not name:
                issues.append(ValidationIssue("error", "MOVIES_NAME_EMPTY", "Movie name is empty.", os.path.basename(file_path), idx, raw))
            if tmdb_id is None:
                issues.append(ValidationIssue("error", "MOVIES_TMDB_ID_INVALID", "tmdb_movie_id must be an integer.", os.path.basename(file_path), idx, raw))

            recs.append(InputRecord("movie", active, name, tmdb_id, None, None, os.path.basename(file_path), idx, raw))

    return recs, issues


def parse_watchlist(file_path: str) -> Tuple[List[InputRecord], List[ValidationIssue]]:
    recs: List[InputRecord] = []
    issues: List[ValidationIssue] = []

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for idx, line in enumerate(f, start=1):
            raw = line.rstrip("\r\n")
            if _is_header_or_comment_only(raw):
                continue

            active = True
            s = raw.strip()
            if s.startswith("#"):
                active = False
                s = s[1:].strip()
            if not s:
                continue

            parts = _SPLIT_RE.split(s)
            if len(parts) != 3:
                issues.append(ValidationIssue("error", "WATCHLIST_FORMAT", "watchlist.txt line must be: Title|TMDB_ID|seasons", os.path.basename(file_path), idx, raw))
                continue

            name = _normalize_name(parts[0])
            tmdb_id = _parse_int(parts[1])
            season_spec_raw = parts[2].strip()

            ok, _seasons, norm_spec = _parse_season_spec(season_spec_raw)
            if not ok:
                issues.append(ValidationIssue("error", "WATCHLIST_SEASON_SPEC_INVALID", "seasons must be '*' or like '1,2,3' or '1-3,5'.", os.path.basename(file_path), idx, raw))

            recs.append(InputRecord("watchlist", active, name, tmdb_id, (norm_spec if norm_spec is not None else (season_spec_raw or None)), None, os.path.basename(file_path), idx, raw))

    return recs, issues


def parse_tv(file_path: str) -> Tuple[List[InputRecord], List[ValidationIssue]]:
    recs: List[InputRecord] = []
    issues: List[ValidationIssue] = []

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for idx, line in enumerate(f, start=1):
            raw = line.rstrip("\r\n")
            if _is_header_or_comment_only(raw):
                continue

            active = True
            s = raw.strip()
            if s.startswith("#"):
                active = False
                s = s[1:].strip()
            if not s:
                continue

            parts = _SPLIT_RE.split(s)
            if len(parts) < 2 or len(parts) > 4:
                issues.append(ValidationIssue("error", "TV_FORMAT", "tv_list.txt line must be: name|tmdb_show_id|season_spec|tvmaze_id (season_spec/tvmaze_id optional)", os.path.basename(file_path), idx, raw))
                continue

            name = _normalize_name(parts[0])
            tmdb_id = _parse_int(parts[1])

            season_spec_raw = parts[2].strip() if len(parts) >= 3 else ""
            tvmaze_raw = parts[3].strip() if len(parts) == 4 else ""

            norm_spec: Optional[str] = None
            if season_spec_raw:
                ok, _seasons, norm_spec = _parse_season_spec(season_spec_raw)
                if not ok:
                    issues.append(ValidationIssue("error", "TV_SEASON_SPEC_INVALID", "season_spec must be '*' or like '1,2,3' or '1-3,5'.", os.path.basename(file_path), idx, raw))

            tvmaze_id = _parse_int(tvmaze_raw) if tvmaze_raw else None
            if tvmaze_raw and tvmaze_id is None:
                issues.append(ValidationIssue("warning", "TV_TVMAZE_ID_INVALID", "tvmaze_id should be an integer (or blank).", os.path.basename(file_path), idx, raw))

            recs.append(InputRecord("tv", active, name, tmdb_id, (norm_spec if norm_spec is not None else (season_spec_raw or None)), tvmaze_id, os.path.basename(file_path), idx, raw))

    return recs, issues


def validate_with_tmdb(logger: Logger, tmdb: TMDBClient, records: List[InputRecord]) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    targets = [r for r in records if r.tmdb_id is not None and r.kind in ("movie", "tv", "watchlist")]
    total = len(targets)
    logger.info(f"TMDB validation targets: {total}")

    for i, r in enumerate(targets, start=1):
        if i == 1 or i == total or (i % 10 == 0):
            logger.info(_progress(i, total, prefix="TMDB "))

        if r.kind == "movie":
            ok, status = tmdb.movie_exists(r.tmdb_id or 0)
            if not ok:
                issues.append(ValidationIssue("error", "TMDB_MOVIE_NOT_FOUND", f"TMDB movie id not found (HTTP {status}).", r.source_file, r.line_no, r.raw_line))
        else:
            ok, status, season_count = tmdb.tv_exists_and_season_count(r.tmdb_id or 0)
            if not ok:
                issues.append(ValidationIssue("error", "TMDB_TV_NOT_FOUND", f"TMDB TV id not found (HTTP {status}).", r.source_file, r.line_no, r.raw_line))
                continue
            if r.season_spec and r.season_spec != "*" and season_count > 0:
                ok_spec, seasons, _norm = _parse_season_spec(r.season_spec)
                if ok_spec:
                    bad = [s for s in seasons if s < 1 or s > season_count]
                    if bad:
                        issues.append(ValidationIssue("error", "SEASON_OUT_OF_RANGE", f"Season(s) out of range for TMDB show (max seasons={season_count}): {bad}", r.source_file, r.line_no, r.raw_line))

        time.sleep(0.05)

    return issues


def build_output_json(records: List[InputRecord]) -> Dict[str, Any]:
    now = dt.datetime.now().astimezone().isoformat()

    def pack(r: InputRecord) -> Dict[str, Any]:
        d = asdict(r)
        d["stable_key"] = f"{r.kind}:{(r.tmdb_id if r.tmdb_id is not None else 'na')}:{r.name.lower()}"
        if d.get("season_spec") == "":
            d["season_spec"] = None
        return d

    return {
        "schema_version": "inputs.v0.1",
        "generated_at": now,
        "records": [pack(r) for r in records],
        "by_kind": {
            "movies": [pack(r) for r in records if r.kind == "movie"],
            "tv": [pack(r) for r in records if r.kind == "tv"],
            "watchlist": [pack(r) for r in records if r.kind == "watchlist"],
        },
        "notes": {
            "inactive_rule": "Lines starting with '#' are treated as inactive but retained in JSON with active=false.",
            "season_spec_rule": "Use '*' for all seasons or '1,2,3' or '1-3,5'.",
        },
    }


def write_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", errors="replace") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--log_path", required=True)
    args = ap.parse_args()

    logger = Logger(args.log_path)
    logger.info("library_manager starting")

    files = {
        "movies": os.path.join(args.inputs_dir, "movies_list.txt"),
        "tv": os.path.join(args.inputs_dir, "tv_list.txt"),
        "watchlist": os.path.join(args.inputs_dir, "watchlist.txt"),
    }

    missing = [k for k, p in files.items() if not os.path.exists(p)]
    if missing:
        logger.error(f"Missing required input files: {missing}")
        return 2

    records: List[InputRecord] = []
    issues: List[ValidationIssue] = []

    logger.info("Parsing movies_list.txt")
    recs, iss = parse_movies(files["movies"]); records += recs; issues += iss

    logger.info("Parsing tv_list.txt")
    recs, iss = parse_tv(files["tv"]); records += recs; issues += iss

    logger.info("Parsing watchlist.txt")
    recs, iss = parse_watchlist(files["watchlist"]); records += recs; issues += iss

    logger.info("Running TMDB validation")
    tmdb = TMDBClient(logger)
    issues += validate_with_tmdb(logger, tmdb, records)

    out_inputs = os.path.join(args.out_dir, "library_inputs.json")
    out_report = os.path.join(args.out_dir, "validation_report.json")

    write_json(out_inputs, build_output_json(records))
    write_json(out_report, {
        "schema_version": "validation.v0.1",
        "generated_at": dt.datetime.now().astimezone().isoformat(),
        "counts": {
            "records_total": len(records),
            "issues_total": len(issues),
            "issues_error": sum(1 for x in issues if x.severity == "error"),
            "issues_warning": sum(1 for x in issues if x.severity == "warning"),
        },
        "issues": [asdict(x) for x in issues],
    })

    logger.info(f"Wrote: {out_inputs}")
    logger.info(f"Wrote: {out_report}")

    if any(x.severity == "error" for x in issues):
        logger.warn("Completed with ERRORS.")
        return 1

    logger.info("Completed OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# <<< END FILE
