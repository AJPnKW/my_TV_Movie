#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/qa_test_tmdb_tv_movie.py
# [PROJECT] my_TV_Movie
# [ROLE]    Deterministic TMDB QA: auth + parser + direct ID validation + search sanity
# [VERSION] v1.1.1
# [UPDATED] 2025-12-20_00-00-00
# [BUILD]   14.01.06
#
# [OUTPUT]
#   - logs/qa_test_tmdb_YYYY-MM-DD_HHMMSS.log.txt
#
# [WHAT IT DOES]
#   1) Loads env (API_TMDB_KEY / API_TMDB_TOKEN) and tests TMDB /configuration
#   2) Parses tv_list.txt + movies_list.txt using the binding pipe formats
#   3) Validates a sample of:
#      - direct ID lookups (/tv/{id}, /movie/{id})
#      - search lookups when tmdb_id missing (title/year)
#   4) Writes complete results to the log (no silent failures)
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

try:
    from tqdm import tqdm  # type: ignore
except Exception:
    tqdm = None  # noqa


REPO_ROOT = Path(__file__).resolve().parents[1]
TV_LIST_PATH = REPO_ROOT / "tv_list.txt"
MOVIES_LIST_PATH = REPO_ROOT / "movies_list.txt"
LOGS_DIR = REPO_ROOT / "logs"

TMDB_API_BASE = "https://api.themoviedb.org/3"
DEFAULT_TIMEOUT = 30

RE_INT = re.compile(r"^\s*(\d{1,10})\s*$")
RE_TRAILING_YEAR_PARENS = re.compile(r"\((\d{4})\)\s*$")
RE_TRAILING_YEAR_SEP = re.compile(r"[\|\-]\s*(\d{4})\s*$")

RE_SEASON_RANGE = re.compile(r"^\s*(\d{1,3})\s*-\s*(\d{1,3})\s*$")
RE_SEASON_LIST = re.compile(r"^\s*(\d{1,3})\s*(,\s*\d{1,3}\s*)+$")


def now_stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")


def log_path() -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR / f"qa_test_tmdb_{now_stamp()}.log.txt"


def w(log: Path, msg: str) -> None:
    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} | {msg}"
    print(line)
    log.write_text(log.read_text(encoding="utf-8") + line + "\n", encoding="utf-8")


def split_pipes(line: str) -> List[str]:
    parts = [p.strip() for p in line.split("|")]
    while len(parts) > 0 and parts[-1] == "" and len(parts) > 4:
        parts.pop()
    return parts


def parse_title_year(s: str) -> Tuple[str, Optional[int]]:
    s = (s or "").strip()
    if not s:
        return "", None
    m = RE_TRAILING_YEAR_PARENS.search(s)
    if m:
        return s[: m.start()].strip(), int(m.group(1))
    m = RE_TRAILING_YEAR_SEP.search(s)
    if m:
        return s[: m.start()].strip(), int(m.group(1))
    return s, None


def parse_season_spec(spec: str) -> Optional[Set[int]]:
    s = (spec or "").strip()
    if not s or s == "*":
        return None
    s = re.sub(r"(?i)\bseason\b", "", s).strip()
    s = re.sub(r"(?i)\bs\b", "", s).strip()
    m = RE_SEASON_RANGE.match(s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        lo, hi = (a, b) if a <= b else (b, a)
        return set(range(lo, hi + 1))
    if RE_SEASON_LIST.match(s):
        out: Set[int] = set()
        for part in s.split(","):
            part = part.strip()
            if part.isdigit():
                n = int(part)
                if n > 0:
                    out.add(n)
        return out if out else None
    if s.isdigit():
        n = int(s)
        return {n} if n > 0 else None
    return None


def parse_tv_list(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = split_pipes(line)
        if len(parts) > 4:
            parts = parts[:4]
        name = parts[0] if len(parts) >= 1 else ""
        c2 = parts[1] if len(parts) >= 2 else ""
        c3 = parts[2] if len(parts) >= 3 else ""
        c4 = parts[3] if len(parts) >= 4 else ""

        title, year = parse_title_year(name)

        tmdb_id: Optional[int] = None
        season_spec = ""
        tvmaze_id: Optional[int] = None

        if c2 and RE_INT.match(c2):
            tmdb_id = int(c2)
            season_spec = c3 or ""
        else:
            season_spec = c2 or ""
            if c3 and RE_INT.match(c3):
                tmdb_id = int(c3)

        if c4 and RE_INT.match(c4):
            tvmaze_id = int(c4)

        sf = parse_season_spec(season_spec)

        if not tmdb_id and not title:
            continue

        rows.append(
            {
                "title": title,
                "year": year,
                "tmdb_id": tmdb_id,
                "season_spec": season_spec.strip(),
                "season_filter": sorted(list(sf)) if isinstance(sf, set) else None,
                "tvmaze_id": tvmaze_id,
                "raw": line,
            }
        )
    return rows


def parse_movies_list(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = split_pipes(line)
        if len(parts) == 1:
            s = parts[0].strip()
            m = RE_INT.match(s)
            if m:
                rows.append({"title": "", "year": None, "tmdb_id": int(m.group(1)), "raw": line})
                continue
            title, year = parse_title_year(s)
            rows.append({"title": title, "year": year, "tmdb_id": None, "raw": line})
            continue

        title_raw = parts[0].strip()
        id_raw = parts[1].strip() if len(parts) >= 2 else ""
        title, year = parse_title_year(title_raw)
        tmdb_id = int(id_raw) if id_raw and RE_INT.match(id_raw) else None

        if not tmdb_id and not title:
            continue

        rows.append({"title": title, "year": year, "tmdb_id": tmdb_id, "raw": line})
    return rows


def looks_like_bearer(token: str) -> bool:
    t = (token or "").strip()
    if len(t) >= 60:
        return True
    if t.startswith("eyJ") and len(t) > 40:
        return True
    return False


def build_auth_candidates() -> List[Tuple[str, str]]:
    k = (os.getenv("API_TMDB_KEY") or "").strip()
    t = (os.getenv("API_TMDB_TOKEN") or "").strip()
    cands: List[Tuple[str, str]] = []

    if t:
        cands.append(("bearer" if looks_like_bearer(t) else "v3", t))
    if k:
        cands.append(("bearer" if looks_like_bearer(k) else "v3", k))

    # de-dupe
    out: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()
    for c in cands:
        if c not in seen:
            out.append(c)
            seen.add(c)

    return out


def tmdb_get(mode: str, cred: str, path: str, params: Optional[Dict[str, Any]] = None) -> Tuple[int, str, Dict[str, Any]]:
    url = f"{TMDB_API_BASE}{path}"
    headers = {"Accept": "application/json"}
    qp = dict(params or {})
    if mode == "v3":
        qp["api_key"] = cred
    else:
        headers["Authorization"] = f"Bearer {cred}"
    r = requests.get(url, headers=headers, params=qp, timeout=DEFAULT_TIMEOUT)
    txt = r.text
    try:
        j = r.json() if txt else {}
    except Exception:
        j = {}
    return r.status_code, url, j


def pick_working_auth(log: Path) -> Tuple[str, str]:
    cands = build_auth_candidates()
    if not cands:
        raise RuntimeError("Missing TMDB env: API_TMDB_KEY or API_TMDB_TOKEN")

    last = ""
    for mode, cred in cands:
        status, url, j = tmdb_get(mode, cred, "/configuration", params={})
        w(log, f"PRECHECK  | mode={mode} status={status} url={url}")
        w(log, f"PRECHECK  | resp={json.dumps(j)[:400]}")
        if status == 200:
            return mode, cred
        last = f"{status} {j}"

    raise RuntimeError(f"All auth candidates failed. last={last}")


def main() -> int:
    lp = log_path()
    lp.write_text("", encoding="utf-8")

    w(lp, f"[qa_test_tmdb] START repo_root={REPO_ROOT.as_posix()}")

    # 1) Auth precheck
    try:
        mode, cred = pick_working_auth(lp)
        w(lp, f"auth_mode={mode}")
    except Exception as e:
        w(lp, f"FAIL precheck: {e}")
        return 2

    # 2) Parse lists
    if not TV_LIST_PATH.exists():
        w(lp, f"FAIL missing {TV_LIST_PATH}")
        return 3
    if not MOVIES_LIST_PATH.exists():
        w(lp, f"FAIL missing {MOVIES_LIST_PATH}")
        return 3

    tv_rows = parse_tv_list(TV_LIST_PATH)
    mv_rows = parse_movies_list(MOVIES_LIST_PATH)

    w(lp, f"tv_list_parsed={len(tv_rows)} movies_list_parsed={len(mv_rows)}")
    w(lp, "TV SAMPLE (first 10 parsed):")
    for r in tv_rows[:10]:
        w(lp, f"  tv  tmdb_id={r.get('tmdb_id')} seasons={r.get('season_spec')!r} title={r.get('title')!r} raw={r.get('raw')!r}")
    w(lp, "MOVIE SAMPLE (first 10 parsed):")
    for r in mv_rows[:10]:
        w(lp, f"  mov tmdb_id={r.get('tmdb_id')} title={r.get('title')!r} raw={r.get('raw')!r}")

    # 3) Validate a deterministic sample of IDs and searches
    def check_tv(row: Dict[str, Any]) -> None:
        tmdb_id = row.get("tmdb_id")
        title = row.get("title") or ""
        year = row.get("year")

        if isinstance(tmdb_id, int) and tmdb_id > 0:
            status, url, j = tmdb_get(mode, cred, f"/tv/{tmdb_id}", params={"language": "en-US"})
            ok = status == 200 and isinstance(j, dict) and j.get("id") == tmdb_id
            w(lp, f"TV ID   | ok={ok} status={status} id={tmdb_id} name={j.get('name')!r} url={url}")
            if not ok:
                w(lp, f"TV ID   | resp={json.dumps(j)[:400]}")
            return

        # fallback search when id missing
        params: Dict[str, Any] = {"query": title}
        if isinstance(year, int):
            params["first_air_date_year"] = year
        status, url, j = tmdb_get(mode, cred, "/search/tv", params=params)
        top = (j.get("results") or [None])[0] if isinstance(j, dict) else None
        w(lp, f"TV SRCH | status={status} title={title!r} year={year!r} top_id={(top or {}).get('id') if isinstance(top, dict) else None} url={url}")

    def check_movie(row: Dict[str, Any]) -> None:
        tmdb_id = row.get("tmdb_id")
        title = row.get("title") or ""
        year = row.get("year")

        if isinstance(tmdb_id, int) and tmdb_id > 0:
            status, url, j = tmdb_get(mode, cred, f"/movie/{tmdb_id}", params={"language": "en-US"})
            ok = status == 200 and isinstance(j, dict) and j.get("id") == tmdb_id
            w(lp, f"MOV ID  | ok={ok} status={status} id={tmdb_id} title={j.get('title')!r} url={url}")
            if not ok:
                w(lp, f"MOV ID  | resp={json.dumps(j)[:400]}")
            return

        params2: Dict[str, Any] = {"query": title}
        if isinstance(year, int):
            params2["year"] = year
        status, url, j = tmdb_get(mode, cred, "/search/movie", params=params2)
        top = (j.get("results") or [None])[0] if isinstance(j, dict) else None
        w(lp, f"MOV SRCH| status={status} title={title!r} year={year!r} top_id={(top or {}).get('id') if isinstance(top, dict) else None} url={url}")

    # deterministic: first 15 of each list
    tv_sample = tv_rows[:15]
    mv_sample = mv_rows[:15]

    if tqdm is not None:
        for r in tqdm(tv_sample, desc="QA TV", unit="show"):
            check_tv(r)
            time.sleep(0.10)
        for r in tqdm(mv_sample, desc="QA Movies", unit="movie"):
            check_movie(r)
            time.sleep(0.10)
    else:
        for r in tv_sample:
            check_tv(r)
            time.sleep(0.10)
        for r in mv_sample:
            check_movie(r)
            time.sleep(0.10)

    w(lp, f"[qa_test_tmdb] DONE log={lp.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
