#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/qa_test_tmdb_tv_movie.py
# [PROJECT] my_TV_Movie (My TV Hub)
# [ROLE]    QA / debug TMDB calls (search vs direct ID) for TV + Movies
# [VERSION] v1.0.0
# [UPDATED] 2025-12-20_00-00-00
# [BUILD]   14.01.10
#
# PURPOSE
# - Determine why fetch_tmdb reports "[show]/[movie] not found" even for valid TMDB IDs.
# - Tests both:
#   (A) Search calls (query + optional year)
#   (B) Direct ID calls (/tv/{id}, /movie/{id})
# - Produces request-level debug: auth mode, URL, status, and a small JSON snippet.
#
# ENV
# - API_TMDB_KEY (required)  : v3 key OR v4 bearer (auto-detected)
# - API_TMDB_TOKEN (optional): v4 bearer (preferred if present)
#
# INPUT
# - Reads repo-root:
#     tv_list.txt
#     movies_list.txt
#
# OUTPUT
# - logs/qa_test_tmdb_YYYY-MM-DD_HHMMSS.log.txt
# - Console summary + per-item diagnostic lines
#
# RUN (PowerShell)
#   cd C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie
#   python scripts\qa_test_tmdb_tv_movie.py
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

try:
    from tqdm import tqdm  # type: ignore
except Exception:
    tqdm = None  # noqa


# -------------------------
# Repo paths
# -------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = REPO_ROOT / "logs"

TV_LIST_PATH = REPO_ROOT / "tv_list.txt"
MOVIES_LIST_PATH = REPO_ROOT / "movies_list.txt"

TMDB_API_BASE = "https://api.themoviedb.org/3"
TIMEOUT = 25

# IMPORTANT: Your current list format appears to be:
#   Title|TMDB_ID|optional
# The existing fetch parser is likely treating "|TMDB_ID" as a YEAR, causing invalid year params.
# This QA parser extracts ID tokens safely and also shows what would happen if treated as year.

RE_PIPE_SPLIT = re.compile(r"\s*\|\s*")
RE_TMDB_TOKEN = re.compile(r"(?i)\b(tmdb)\s*[:=]\s*(\d{3,10})\b")
RE_ID_ONLY = re.compile(r"^\d{3,10}$")
RE_YEAR_4 = re.compile(r"^\d{4}$")


@dataclass(frozen=True)
class TmdbAuth:
    mode: str  # "v3" or "bearer"
    value: str


def _now_stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")


def _log_path() -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR / f"qa_test_tmdb_{_now_stamp()}.log.txt"


def _write(log_fp, msg: str) -> None:
    line = f"{_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {msg}"
    print(line)
    log_fp.write(line + "\n")
    log_fp.flush()


def _looks_like_bearer(token: str) -> bool:
    t = token.strip()
    if len(t) >= 60:
        return True
    if t.startswith("eyJ") and len(t) > 40:
        return True
    return False


def load_auth() -> TmdbAuth:
    v_key = (os.getenv("API_TMDB_KEY") or "").strip()
    v_tok = (os.getenv("API_TMDB_TOKEN") or "").strip()
    candidate = v_tok or v_key
    if not candidate:
        raise RuntimeError("Missing API_TMDB_KEY (or API_TMDB_TOKEN).")

    if _looks_like_bearer(candidate):
        return TmdbAuth(mode="bearer", value=candidate)
    return TmdbAuth(mode="v3", value=candidate)


def tmdb_get(auth: TmdbAuth, path: str, params: Optional[Dict[str, Any]] = None) -> Tuple[int, str, Dict[str, Any]]:
    params = dict(params or {})
    url = f"{TMDB_API_BASE}{path}"
    headers = {"User-Agent": "my_TV_Movie qa_test_tmdb_tv_movie.py"}

    if auth.mode == "v3":
        params["api_key"] = auth.value
    else:
        headers["Authorization"] = f"Bearer {auth.value}"

    r = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
    text_head = (r.text or "")[:600]

    try:
        j = r.json() if r.text else {}
    except Exception:
        j = {"_non_json_head": text_head}

    return r.status_code, r.url, j


def _read_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return [ln.strip() for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip() and not ln.strip().startswith("#")]


def parse_line_guess_formats(line: str) -> Dict[str, Any]:
    """
    Returns:
      title
      id_from_tokens
      year_from_tokens (ONLY if exactly 4 digits)
      raw_tokens
      tmdb_token_id (tmdb:123)
    """
    tmdb_token_id: Optional[int] = None
    m = RE_TMDB_TOKEN.search(line)
    if m:
        tmdb_token_id = int(m.group(2))

    tokens = RE_PIPE_SPLIT.split(line)
    tokens = [t.strip() for t in tokens if t.strip()]

    title = tokens[0] if tokens else line.strip()

    # attempt to extract an ID from pipe tokens (common in your logs)
    id_from_tokens: Optional[int] = None
    year_from_tokens: Optional[int] = None

    for t in tokens[1:]:
        if RE_ID_ONLY.match(t):
            # if 4 digits, treat as year candidate; otherwise treat as id
            if RE_YEAR_4.match(t):
                # could still be an ID, but this QA test tracks it as "year" only if 4 digits
                year_from_tokens = int(t)
            else:
                id_from_tokens = int(t)
                break

    return {
        "title": title,
        "raw_tokens": tokens,
        "tmdb_token_id": tmdb_token_id,
        "id_from_tokens": id_from_tokens,
        "year_from_tokens": year_from_tokens,
    }


def pick_id(rec: Dict[str, Any]) -> Optional[int]:
    # Priority: explicit tmdb: token, then pipe id token
    if rec.get("tmdb_token_id"):
        return int(rec["tmdb_token_id"])
    if rec.get("id_from_tokens"):
        return int(rec["id_from_tokens"])
    return None


def snippet(j: Dict[str, Any]) -> str:
    # safe compact snippet for logs
    keep: Dict[str, Any] = {}
    for k in ["status_code", "status_message", "id", "name", "title", "release_date", "first_air_date", "results", "success"]:
        if k in j:
            keep[k] = j[k]
    # trim results if present
    if isinstance(keep.get("results"), list):
        keep["results"] = keep["results"][:1]
    return json.dumps(keep, ensure_ascii=False)[:600]


def test_one_tv(auth: TmdbAuth, title: str, year: Optional[int], tmdb_id: Optional[int], log_fp) -> None:
    # A) search/tv
    params: Dict[str, Any] = {"query": title}
    if year:
        params["first_air_date_year"] = year
    st, url, j = tmdb_get(auth, "/search/tv", params=params)
    _write(log_fp, f"TV SEARCH | title={title!r} year={year} -> status={st} url={url}")
    _write(log_fp, f"TV SEARCH | resp={snippet(j)}")

    # B) direct id
    if tmdb_id:
        st2, url2, j2 = tmdb_get(auth, f"/tv/{tmdb_id}", params={"language": "en-US"})
        _write(log_fp, f"TV ID     | id={tmdb_id} -> status={st2} url={url2}")
        _write(log_fp, f"TV ID     | resp={snippet(j2)}")


def test_one_movie(auth: TmdbAuth, title: str, year: Optional[int], tmdb_id: Optional[int], log_fp) -> None:
    # A) search/movie
    params: Dict[str, Any] = {"query": title}
    if year:
        params["year"] = year
    st, url, j = tmdb_get(auth, "/search/movie", params=params)
    _write(log_fp, f"MOV SEARCH | title={title!r} year={year} -> status={st} url={url}")
    _write(log_fp, f"MOV SEARCH | resp={snippet(j)}")

    # B) direct id
    if tmdb_id:
        st2, url2, j2 = tmdb_get(auth, f"/movie/{tmdb_id}", params={"language": "en-US"})
        _write(log_fp, f"MOV ID     | id={tmdb_id} -> status={st2} url={url2}")
        _write(log_fp, f"MOV ID     | resp={snippet(j2)}")


def main() -> int:
    lp = _log_path()
    with lp.open("w", encoding="utf-8") as log_fp:
        _write(log_fp, f"[qa_test_tmdb] START repo_root={REPO_ROOT.as_posix()}")
        try:
            auth = load_auth()
        except Exception as e:
            _write(log_fp, f"FAIL auth: {e}")
            try:
                input("Press Enter to close...")
            except Exception:
                pass
            return 2

        _write(log_fp, f"auth_mode={auth.mode}")

        tv_lines = _read_lines(TV_LIST_PATH)
        mov_lines = _read_lines(MOVIES_LIST_PATH)

        _write(log_fp, f"tv_list_lines={len(tv_lines)} movies_list_lines={len(mov_lines)}")

        # Preflight: /configuration
        st, url, j = tmdb_get(auth, "/configuration", params={})
        _write(log_fp, f"PRECHECK  | status={st} url={url}")
        _write(log_fp, f"PRECHECK  | resp={snippet(j)}")
        if st != 200:
            _write(log_fp, "FAIL precheck: TMDB not reachable or auth invalid.")
            try:
                input("Press Enter to close...")
            except Exception:
                pass
            return 3

        # Test subsets (first 15 each) to keep fast
        tv_subset = tv_lines[:15]
        mov_subset = mov_lines[:15]

        it_tv = tv_subset if tqdm is None else tqdm(tv_subset, desc="QA TV", unit="show")  # type: ignore
        for line in it_tv:
            rec = parse_line_guess_formats(line)
            title = rec["title"]
            tmdb_id = pick_id(rec)

            # IMPORTANT: this shows you the problematic behavior:
            # - if you treat the pipe-number as YEAR (e.g., 60585), searches will fail
            year = rec.get("year_from_tokens")

            _write(log_fp, "-----------------")
            _write(log_fp, f"TV LINE   | raw={line!r}")
            _write(log_fp, f"TV PARSE  | tokens={rec['raw_tokens']} id={tmdb_id} year4={year} tmdb_token={rec['tmdb_token_id']}")

            # Run tests:
            # 1) Search with NO year (baseline)
            test_one_tv(auth, title=title, year=None, tmdb_id=tmdb_id, log_fp=log_fp)

            # 2) If there is a 4-digit year, test search with year too
            if year:
                test_one_tv(auth, title=title, year=year, tmdb_id=None, log_fp=log_fp)

            time.sleep(0.10)

        it_mov = mov_subset if tqdm is None else tqdm(mov_subset, desc="QA Movies", unit="movie")  # type: ignore
        for line in it_mov:
            rec = parse_line_guess_formats(line)
            title = rec["title"]
            tmdb_id = pick_id(rec)

            year = rec.get("year_from_tokens")

            _write(log_fp, "-----------------")
            _write(log_fp, f"MOV LINE  | raw={line!r}")
            _write(log_fp, f"MOV PARSE | tokens={rec['raw_tokens']} id={tmdb_id} year4={year} tmdb_token={rec['tmdb_token_id']}")

            test_one_movie(auth, title=title, year=None, tmdb_id=tmdb_id, log_fp=log_fp)

            if year:
                test_one_movie(auth, title=title, year=year, tmdb_id=None, log_fp=log_fp)

            time.sleep(0.10)

        _write(log_fp, f"[qa_test_tmdb] END log={lp.as_posix()}")

    try:
        input("Press Enter to close...")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
