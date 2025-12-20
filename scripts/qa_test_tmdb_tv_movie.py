#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/qa_test_tmdb_tv_movie.py
# [PROJECT] my_TV_Movie (My TV Hub)
# [ROLE]    QA / debug TMDB calls + validate list parsing for tv/movies/watchlist
# [VERSION] v1.0.2
# [UPDATED] 2025-12-20
#
# CHANGELOG v1.0.2
# - Parser now matches actual input schemas:
#     tv_list.txt     => title|tmdb_id|season_spec|tvmaze_id
#     watchlist.txt   => title|tmdb_id|season_spec
#     movies_list.txt => title|tmdb_id
# - Removed "4-digit=year" heuristic (INVALID for these schemas)
# - Added tolerance for extra spacing around delimiters
# - Added fix for malformed "Title12345|12345|*" (strip trailing digits from title)
# - Writes a deterministic parse report to logs/ (always)
# - TMDB calls keep: session reuse, retries, timeouts, redacted api_key
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
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry  # type: ignore
except Exception:
    Retry = None  # type: ignore

try:
    from tqdm import tqdm  # type: ignore
except Exception:
    tqdm = None  # type: ignore


# -------------------------
# Repo paths
# -------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = REPO_ROOT / "logs"

TV_LIST_PATH = REPO_ROOT / "tv_list.txt"
WATCHLIST_PATH = REPO_ROOT / "watchlist.txt"
MOVIES_LIST_PATH = REPO_ROOT / "movies_list.txt"

TMDB_API_BASE = "https://api.themoviedb.org/3"

# Timeouts: (connect_timeout, read_timeout)
TIMEOUT = (10, 25)

# Retries (only for transient network/proxy/TLS hiccups)
RETRY_TOTAL = 4
RETRY_BACKOFF = 0.6

# Split on pipes with any surrounding whitespace
RE_PIPE_SPLIT = re.compile(r"\s*\|\s*")
RE_COMMENT_LINE = re.compile(r"^\s*#")
RE_APIKEY_IN_URL = re.compile(r"(api_key=)[^&]+")

# Malformed: Title12345|12345|*  -> strip trailing digits from title token
RE_TITLE_TRAILING_DIGITS = re.compile(r"^(?P<title>.*?)(?P<digits>\d{3,10})$")

# Digits-only token
RE_DIGITS = re.compile(r"^\d{3,10}$")


@dataclass(frozen=True)
class TmdbAuth:
    mode: str  # "v3" or "bearer"
    value: str


@dataclass(frozen=True)
class ParsedTvLine:
    title: str
    tmdb_id: int
    season_spec: str
    tvmaze_id: Optional[int]
    raw_line: str
    tokens: List[str]


@dataclass(frozen=True)
class ParsedWatchLine:
    title: str
    tmdb_id: int
    season_spec: str
    raw_line: str
    tokens: List[str]


@dataclass(frozen=True)
class ParsedMovieLine:
    title: str
    tmdb_id: int
    raw_line: str
    tokens: List[str]


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
    # Prefer TOKEN if present; otherwise KEY
    v_tok = (os.getenv("API_TMDB_TOKEN") or "").strip()
    v_key = (os.getenv("API_TMDB_KEY") or "").strip()
    candidate = v_tok or v_key
    if not candidate:
        raise RuntimeError("Missing API_TMDB_TOKEN or API_TMDB_KEY.")

    if _looks_like_bearer(candidate) and v_tok:
        return TmdbAuth(mode="bearer", value=candidate)
    return TmdbAuth(mode="v3", value=candidate)


def _make_session() -> requests.Session:
    s = requests.Session()

    if Retry is not None:
        retry = Retry(
            total=RETRY_TOTAL,
            connect=RETRY_TOTAL,
            read=RETRY_TOTAL,
            status=RETRY_TOTAL,
            backoff_factor=RETRY_BACKOFF,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    else:
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10)

    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def _redact_url(u: str) -> str:
    return RE_APIKEY_IN_URL.sub(r"\1***REDACTED***", u)


def tmdb_get(session: requests.Session, auth: TmdbAuth, path: str, params: Optional[Dict[str, Any]] = None) -> Tuple[int, str, Dict[str, Any]]:
    params = dict(params or {})
    url = f"{TMDB_API_BASE}{path}"
    headers = {"User-Agent": "my_TV_Movie qa_test_tmdb_tv_movie.py", "Accept": "application/json"}

    if auth.mode == "v3":
        params["api_key"] = auth.value
    else:
        headers["Authorization"] = f"Bearer {auth.value}"

    try:
        r = session.get(url, headers=headers, params=params, timeout=TIMEOUT)
        redacted_url = _redact_url(r.url if r.url else url)
        try:
            j = r.json() if r.text else {}
        except Exception:
            j = {"_non_json_head": (r.text or "")[:600]}
        return r.status_code, redacted_url, j

    except requests.RequestException as e:
        return 0, _redact_url(url), {"_request_exception": str(e)}


def _read_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    out: List[str] = []
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = ln.strip()
        if not s:
            continue
        if RE_COMMENT_LINE.match(s):
            continue
        out.append(s)
    return out


def _split_tokens(line: str) -> List[str]:
    toks = [t.strip() for t in RE_PIPE_SPLIT.split(line) if t.strip() != ""]
    return toks


def _normalize_title(title: str) -> str:
    # collapse internal whitespace; preserve casing/punctuation
    return " ".join(title.strip().split())


def _strip_trailing_digits_if_malformed(title: str, tmdb_id: int) -> Tuple[str, bool]:
    """
    Fix malformed: 'Criminal Record204490|204490|*'
    Title token ends with the same digits as tmdb_id.
    """
    m = RE_TITLE_TRAILING_DIGITS.match(title.strip())
    if not m:
        return title, False
    try:
        tail = int(m.group("digits"))
    except Exception:
        return title, False
    if tail == tmdb_id:
        cleaned = m.group("title").rstrip()
        return cleaned, True
    return title, False


def parse_tv_line(line: str) -> Optional[ParsedTvLine]:
    """
    Schema (binding): title | tmdb_show_id | season_spec | tvmaze_id
    - season_spec may be '*' or '1' or '1,2' etc.
    - tvmaze_id may be missing
    """
    toks = _split_tokens(line)
    if len(toks) < 3:
        return None

    title = _normalize_title(toks[0])

    if not RE_DIGITS.match(toks[1]):
        return None
    tmdb_id = int(toks[1])

    season_spec = _normalize_title(toks[2])

    tvmaze_id: Optional[int] = None
    if len(toks) >= 4 and RE_DIGITS.match(toks[3]):
        tvmaze_id = int(toks[3])

    title2, fixed = _strip_trailing_digits_if_malformed(title, tmdb_id)
    if fixed:
        title = _normalize_title(title2)

    return ParsedTvLine(
        title=title,
        tmdb_id=tmdb_id,
        season_spec=season_spec,
        tvmaze_id=tvmaze_id,
        raw_line=line,
        tokens=toks,
    )


def parse_watch_line(line: str) -> Optional[ParsedWatchLine]:
    """
    Schema (binding): title | tmdb_show_id | season_spec
    """
    toks = _split_tokens(line)
    if len(toks) < 3:
        return None

    title = _normalize_title(toks[0])

    if not RE_DIGITS.match(toks[1]):
        return None
    tmdb_id = int(toks[1])

    season_spec = _normalize_title(toks[2])

    title2, fixed = _strip_trailing_digits_if_malformed(title, tmdb_id)
    if fixed:
        title = _normalize_title(title2)

    return ParsedWatchLine(
        title=title,
        tmdb_id=tmdb_id,
        season_spec=season_spec,
        raw_line=line,
        tokens=toks,
    )


def parse_movie_line(line: str) -> Optional[ParsedMovieLine]:
    """
    Schema (binding): title | tmdb_movie_id
    """
    toks = _split_tokens(line)
    if len(toks) < 2:
        return None

    title = _normalize_title(toks[0])

    if not RE_DIGITS.match(toks[1]):
        return None
    tmdb_id = int(toks[1])

    title2, fixed = _strip_trailing_digits_if_malformed(title, tmdb_id)
    if fixed:
        title = _normalize_title(title2)

    return ParsedMovieLine(
        title=title,
        tmdb_id=tmdb_id,
        raw_line=line,
        tokens=toks,
    )


def _snippet(j: Dict[str, Any]) -> str:
    keep: Dict[str, Any] = {}
    for k in ["status_code", "status_message", "id", "name", "title", "release_date", "first_air_date", "results", "success", "_request_exception"]:
        if k in j:
            keep[k] = j[k]
    if isinstance(keep.get("results"), list):
        keep["results"] = keep["results"][:1]
    return json.dumps(keep, ensure_ascii=False)[:700]


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
        watch_lines = _read_lines(WATCHLIST_PATH)
        mov_lines = _read_lines(MOVIES_LIST_PATH)

        _write(log_fp, f"tv_list_lines={len(tv_lines)} watchlist_lines={len(watch_lines)} movies_list_lines={len(mov_lines)}")

        # Parse + report errors (parser validation)
        parsed_tv: List[ParsedTvLine] = []
        parsed_watch: List[ParsedWatchLine] = []
        parsed_mov: List[ParsedMovieLine] = []

        bad_tv: List[str] = []
        bad_watch: List[str] = []
        bad_mov: List[str] = []

        for ln in tv_lines:
            rec = parse_tv_line(ln)
            if rec is None:
                bad_tv.append(ln)
            else:
                parsed_tv.append(rec)

        for ln in watch_lines:
            rec = parse_watch_line(ln)
            if rec is None:
                bad_watch.append(ln)
            else:
                parsed_watch.append(rec)

        for ln in mov_lines:
            rec = parse_movie_line(ln)
            if rec is None:
                bad_mov.append(ln)
            else:
                parsed_mov.append(rec)

        _write(log_fp, f"PARSE tv_ok={len(parsed_tv)}/{len(tv_lines)} watch_ok={len(parsed_watch)}/{len(watch_lines)} mov_ok={len(parsed_mov)}/{len(mov_lines)}")

        if bad_tv:
            _write(log_fp, f"PARSE tv_bad_count={len(bad_tv)} (showing first 10)")
            for b in bad_tv[:10]:
                _write(log_fp, f"TV BAD   | {b!r}")

        if bad_watch:
            _write(log_fp, f"PARSE watch_bad_count={len(bad_watch)} (showing first 10)")
            for b in bad_watch[:10]:
                _write(log_fp, f"WATCH BAD| {b!r}")

        if bad_mov:
            _write(log_fp, f"PARSE mov_bad_count={len(bad_mov)} (showing first 10)")
            for b in bad_mov[:10]:
                _write(log_fp, f"MOV BAD  | {b!r}")

        # Show a few parsed examples
        for rec in parsed_tv[:5]:
            _write(log_fp, f"TV OK    | title={rec.title!r} id={rec.tmdb_id} seasons={rec.season_spec!r} tvmaze={rec.tvmaze_id} tokens={rec.tokens}")

        for rec in parsed_watch[:5]:
            _write(log_fp, f"WATCH OK | title={rec.title!r} id={rec.tmdb_id} seasons={rec.season_spec!r} tokens={rec.tokens}")

        for rec in parsed_mov[:5]:
            _write(log_fp, f"MOV OK   | title={rec.title!r} id={rec.tmdb_id} tokens={rec.tokens}")

        # TMDB preflight
        session = _make_session()
        st, url, j = tmdb_get(session, auth, "/configuration", params={})
        _write(log_fp, f"PRECHECK | status={st} url={url}")
        _write(log_fp, f"PRECHECK | resp={_snippet(j)}")
        if st != 200:
            _write(log_fp, "FAIL precheck: TMDB not reachable or auth invalid.")
            try:
                input("Press Enter to close...")
            except Exception:
                pass
            return 3

        # Minimal TMDB checks (by ID, deterministic subset)
        tv_subset = parsed_tv[:15]
        mov_subset = parsed_mov[:15]

        it_tv = tv_subset if tqdm is None else tqdm(tv_subset, desc="QA TV (ID)", unit="show")  # type: ignore
        for rec in it_tv:
            st2, url2, j2 = tmdb_get(session, auth, f"/tv/{rec.tmdb_id}", params={"language": "en-US"})
            _write(log_fp, f"TV ID    | title={rec.title!r} id={rec.tmdb_id} -> status={st2} url={url2}")
            _write(log_fp, f"TV ID    | resp={_snippet(j2)}")
            time.sleep(0.05)

        it_mov = mov_subset if tqdm is None else tqdm(mov_subset, desc="QA Movies (ID)", unit="movie")  # type: ignore
        for rec in it_mov:
            st2, url2, j2 = tmdb_get(session, auth, f"/movie/{rec.tmdb_id}", params={"language": "en-US"})
            _write(log_fp, f"MOV ID   | title={rec.title!r} id={rec.tmdb_id} -> status={st2} url={url2}")
            _write(log_fp, f"MOV ID   | resp={_snippet(j2)}")
            time.sleep(0.05)

        _write(log_fp, f"[qa_test_tmdb] END log={lp.as_posix()}")

    try:
        input("Press Enter to close...")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
