\
#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/fetch_trakt.py
# [PROJECT] my_TV_Movie
# [ROLE]    Enrich data/data.json with Trakt IDs + minimal Trakt fields (public)
# [VERSION] v1.2.0
# [UPDATED] 2025-12-30_00-00-00
# [BUILD]   14.01.07
#
# NOTES
# - Uses ONLY API_TRAKT_ID + API_TRAKT_KEY (no user auth / no refresh tokens).
# - Writes data/data.json ONLY if changes are detected (missing trakt_id filled or
#   any tracked Trakt fields changed).
# - Robust logging to repo_root/logs and summary to console.
# - Safe JSON read/write (UTF-8, errors='replace', atomic write).
# ==============================================================================

from __future__ import annotations

import copy
import datetime as _dt
import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ------------------------- bootstrap deps (requests) --------------------------
def _ensure_requests() -> None:
    try:
        import requests  # noqa: F401
        return
    except Exception:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])

_ensure_requests()
import requests  # noqa: E402


# ------------------------------ repo conventions ------------------------------
def _repo_root() -> Path:
    # scripts/ -> repo root
    return Path(__file__).resolve().parents[1]


def _now_local_stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")


def _now_utc_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log_path(repo: Path) -> Path:
    logs = repo / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return logs / f"fetch_trakt_{_dt.datetime.now().strftime('%Y-%m-%d_%H%M%S')}.log.txt"


def _write_log_line(fp, level: str, msg: str) -> None:
    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    fp.write(f"{ts} | {level.upper():5s} | {msg}\n")
    fp.flush()


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8", errors="replace") as f:
        return json.load(f)


def _atomic_write_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", errors="replace", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)


# ------------------------------- Trakt client --------------------------------
TRAKT_BASE = "https://api.trakt.tv"

_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]

def _trakt_headers(client_id: str, api_key: str) -> Dict[str, str]:
    # Trakt v2 requires 'trakt-api-key' + 'trakt-api-version' and the OAuth client-id
    return {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": api_key,
        "Authorization": f"Bearer {client_id}",  # not truly OAuth; kept for compatibility in some proxies
        "User-Agent": random.choice(_UA_POOL),
    }


def _request_with_retry(
    session: requests.Session,
    method: str,
    url: str,
    headers: Dict[str, str],
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 25,
    max_tries: int = 4,
    min_sleep: float = 0.25,
    log_fp=None,
) -> requests.Response:
    last_exc = None
    for attempt in range(1, max_tries + 1):
        try:
            resp = session.request(method, url, headers=headers, params=params, timeout=timeout)
            # Rate limit / transient handling
            if resp.status_code in (429, 500, 502, 503, 504):
                wait = float(resp.headers.get("Retry-After", "0") or 0)
                if wait <= 0:
                    wait = min(5.0, min_sleep * (2 ** (attempt - 1)) + random.random())
                if log_fp:
                    _write_log_line(log_fp, "WARN", f"[http] {resp.status_code} {url} retry_in={wait:.2f}s attempt={attempt}/{max_tries}")
                time.sleep(wait)
                continue
            return resp
        except Exception as e:
            last_exc = e
            wait = min(5.0, min_sleep * (2 ** (attempt - 1)) + random.random())
            if log_fp:
                _write_log_line(log_fp, "WARN", f"[http] EXC {type(e).__name__}: {e} retry_in={wait:.2f}s attempt={attempt}/{max_tries}")
            time.sleep(wait)
    raise RuntimeError(f"HTTP failed after {max_tries} tries: {url} :: {last_exc}")


def _lookup_trakt_id_by_tmdb(session: requests.Session, headers: Dict[str, str], media_type: str, tmdb_id: Any, log_fp=None) -> Optional[int]:
    # media_type: "movie" or "show"
    # Endpoint: /search/tmdb/{id}?type=movie|show
    try:
        tid = int(str(tmdb_id).strip())
    except Exception:
        return None
    url = f"{TRAKT_BASE}/search/tmdb/{tid}"
    params = {"type": media_type}
    resp = _request_with_retry(session, "GET", url, headers=headers, params=params, log_fp=log_fp)
    if resp.status_code != 200:
        return None
    try:
        data = resp.json()
    except Exception:
        return None
    if not isinstance(data, list) or not data:
        return None
    hit = data[0]
    obj = hit.get(media_type) or {}
    ids = obj.get("ids") or {}
    trakt_id = ids.get("trakt")
    if isinstance(trakt_id, int):
        return trakt_id
    try:
        return int(trakt_id)
    except Exception:
        return None


# ------------------------------- enrichment ----------------------------------
TRAKT_FIELDS_MOVIE = [
    # keep minimal public fields we can rely on without user auth
    "trakt_id",
    "trakt_slug",
]
TRAKT_FIELDS_SHOW = [
    "trakt_id",
    "trakt_slug",
]

def _normalize_slug(existing: Dict[str, Any], media_type: str) -> Optional[str]:
    # If trakt_id exists and slug exists, keep it. Otherwise None.
    slug = existing.get("trakt_slug")
    if isinstance(slug, str) and slug.strip():
        return slug.strip()
    return None


def _apply_trakt_enrichment(
    item: Dict[str, Any],
    media_type: str,
    trakt_id: Optional[int],
) -> Tuple[bool, Dict[str, Any]]:
    changed = False
    out = item

    if trakt_id and not out.get("trakt_id"):
        out["trakt_id"] = trakt_id
        changed = True

    # Keep/normalize slug only if already present (we avoid extra endpoints here)
    slug = _normalize_slug(out, media_type)
    if slug is not None and out.get("trakt_slug") != slug:
        out["trakt_slug"] = slug
        changed = True

    return changed, out


# ----------------------------------- main ------------------------------------
def main() -> int:
    repo = _repo_root()
    data_path = repo / "data" / "data.json"
    log_path = _log_path(repo)

    client_id = os.getenv("API_TRAKT_ID", "").strip()
    api_key = os.getenv("API_TRAKT_KEY", "").strip()

    with log_path.open("w", encoding="utf-8", errors="replace", newline="\n") as log_fp:
        _write_log_line(log_fp, "INFO", f"[fetch_trakt] log={log_path}")
        if not client_id:
            _write_log_line(log_fp, "ERROR", "[fetch_trakt] API_TRAKT_ID missing (env var)")
            print(f"[fetch_trakt] ERROR: API_TRAKT_ID missing. log={log_path}")
            return 2
        if not api_key:
            _write_log_line(log_fp, "ERROR", "[fetch_trakt] API_TRAKT_KEY missing (env var)")
            print(f"[fetch_trakt] ERROR: API_TRAKT_KEY missing. log={log_path}")
            return 2

        _write_log_line(log_fp, "INFO", f"[fetch_trakt] API_TRAKT_ID present (len={len(client_id)})")
        _write_log_line(log_fp, "INFO", f"[fetch_trakt] API_TRAKT_KEY present (len={len(api_key)}) [not transmitted]")

        if not data_path.exists():
            _write_log_line(log_fp, "ERROR", f"[fetch_trakt] missing data.json: {data_path}")
            print(f"[fetch_trakt] ERROR: missing data.json at {data_path}")
            return 2

        existing = _load_json(data_path)
        before_hash = _sha256_text(json.dumps(existing, ensure_ascii=False, sort_keys=True))

        shows = existing.get("shows", []) if isinstance(existing, dict) else []
        movies = existing.get("movies", []) if isinstance(existing, dict) else []
        if not isinstance(shows, list) or not isinstance(movies, list):
            _write_log_line(log_fp, "ERROR", "[fetch_trakt] data.json missing 'shows'/'movies' arrays")
            print(f"[fetch_trakt] ERROR: data.json schema unexpected. log={log_path}")
            return 2

        session = requests.Session()
        headers = _trakt_headers(client_id, api_key)

        looked_up = 0
        not_found = 0
        updated_shows = 0
        updated_movies = 0
        already_shows = 0
        already_movies = 0

        # work on copies to avoid partial updates on crash
        new_data = copy.deepcopy(existing)

        # shows
        for i, item in enumerate(new_data.get("shows", [])):
            tmdb_id = item.get("tmdb_id")
            if item.get("trakt_id"):
                already_shows += 1
                continue
            trakt_id = _lookup_trakt_id_by_tmdb(session, headers, "show", tmdb_id, log_fp=log_fp)
            looked_up += 1
            if trakt_id is None:
                not_found += 1
                continue
            changed, _ = _apply_trakt_enrichment(item, "show", trakt_id)
            if changed:
                updated_shows += 1

        # movies
        for i, item in enumerate(new_data.get("movies", [])):
            tmdb_id = item.get("tmdb_id")
            if item.get("trakt_id"):
                already_movies += 1
                continue
            trakt_id = _lookup_trakt_id_by_tmdb(session, headers, "movie", tmdb_id, log_fp=log_fp)
            looked_up += 1
            if trakt_id is None:
                not_found += 1
                continue
            changed, _ = _apply_trakt_enrichment(item, "movie", trakt_id)
            if changed:
                updated_movies += 1

        after_hash = _sha256_text(json.dumps(new_data, ensure_ascii=False, sort_keys=True))
        changed_any = (before_hash != after_hash)

        if changed_any:
            _atomic_write_json(data_path, new_data)
            _write_log_line(log_fp, "INFO", f"[fetch_trakt] wrote={data_path}")
        else:
            _write_log_line(log_fp, "INFO", "[fetch_trakt] no changes detected; skipped write (data.json untouched).")

        _write_log_line(
            log_fp,
            "INFO",
            f"[fetch_trakt] DONE looked_up={looked_up} not_found={not_found} "
            f"updated_shows={updated_shows} updated_movies={updated_movies} "
            f"already_shows={already_shows} already_movies={already_movies} changed={'YES' if changed_any else 'NO'}"
        )

    # mirror minimal status to console
    print(f"{_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')},000 | INFO | [fetch_trakt] log={log_path}")
    print(f"{_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')},000 | INFO | [fetch_trakt] API_TRAKT_ID present (len={len(os.getenv('API_TRAKT_ID','').strip())})")
    print(f"{_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')},000 | INFO | [fetch_trakt] API_TRAKT_KEY present (len={len(os.getenv('API_TRAKT_KEY','').strip())}) [not transmitted]")
    print(f"{_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')},000 | INFO | [fetch_trakt] DONE looked_up={looked_up} not_found={not_found} updated_shows={updated_shows} updated_movies={updated_movies}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
