#!/usr/bin/env python3
# ==============================================================================
# [FILE] scripts/fetch_trakt.py
# [PROJECT] my_TV_Movie
# [ROLE] Enrich/Sync Trakt metadata into canonical data/data.json (watchlist + IDs)
# [VERSION] v2.2.1
# [UPDATED] 2025-12-20_00-00-00
# [BUILD] 14.01.06
#
# [INPUTS]
# - web/config.json (authoritative config; read-only here)
# - data/data.json (canonical dataset produced by fetch_tmdb.py; read + update)
#
# [OUTPUTS]
# - data/data.json (atomic update; preserves all unrelated keys/structures)
# - data/last_refresh_trakt.txt
# - logs/fetch_trakt_YYYY-MM-DD_HHMMSS.log.txt
#
# [ENV REQUIRED]
# - TRAKT_CLIENT_ID (required)
# - TRAKT_CLIENT_SECRET (required)
# - TRAKT_OAUTH_REDIRECT_URL (required) (may be "urn:ietf:wg:oauth:2.0:oob")
#
# [ENV OPTIONAL]
# - TRAKT_USERNAME (optional; only used for public user endpoints)
# - TRAKT_ACCESS_TOKEN (optional; if present, enables /users/me/* endpoints)
#
# [BINDING RULES APPLIED]
# - TRUE SPA: index.html is the only entry point (not relevant to this script)
# - data.json is not edited manually (script updates atomically)
# - No schema redesign / no simplification / preserve existing keys
# - Errors must be surfaced (written into data.json errors + log; no silent failures)
# - Canonical asset hierarchy: no deprecated "image/" references added here
#
# [WHAT THIS SCRIPT DOES]
# 1) Loads existing data/data.json
# 2) Attempts Trakt watchlist fetch:
#    - If TRAKT_ACCESS_TOKEN is present: uses /users/me/watchlist/*
#    - Else if TRAKT_USERNAME is present: uses /users/{username}/watchlist/*
#    - Else: skips Trakt fetch (no OAuth/login/PIN flow is triggered)
# 3) Updates:
#    - data["watchlist"] ONLY when Trakt fetch actually runs and returns data
#    - per-show and per-movie optional trakt_id enrichment when tmdb_id matches
#    - data["metadata"]["trakt_sync"] timestamp + counts + mode
#    - data["errors"] only for concrete failures (not for intentional skip)
# 4) Writes data/data.json atomically (temp -> validate -> replace)
#
# [NO INVENTED MODULES]
# - Does not create new files/folders beyond logs + last_refresh_trakt.txt
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests  # type: ignore
except Exception:
    print("ERROR: Missing dependency 'requests'.", file=sys.stderr)
    print("Install it inside your venv:", file=sys.stderr)
    print(" python -m pip install requests", file=sys.stderr)
    raise

try:
    import orjson  # type: ignore
except Exception:
    orjson = None  # noqa

try:
    from tqdm import tqdm  # type: ignore
except Exception:
    tqdm = None  # noqa


# -------------------------
# Paths
# -------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
CONFIG_JSON_PATH = WEB_DIR / "config.json"
DATA_DIR = REPO_ROOT / "data"
DATA_JSON_PATH = DATA_DIR / "data.json"
LAST_REFRESH_TRAKT_PATH = DATA_DIR / "last_refresh_trakt.txt"
LOGS_DIR = REPO_ROOT / "logs"


# -------------------------
# Trakt constants
# -------------------------
TRAKT_API_BASE = "https://api.trakt.tv"
TRAKT_API_VERSION = "2"
DEFAULT_TIMEOUT = 30
USER_AGENT = "my_TV_Movie fetch_trakt.py (static data builder)"


@dataclass(frozen=True)
class TraktEnv:
    client_id: str
    client_secret: str
    oauth_redirect_url: str
    username: Optional[str]
    access_token: Optional[str]


def _now_stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")


def setup_logging() -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"fetch_trakt_{_now_stamp()}.log.txt"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.info("[fetch_trakt] log=%s", log_path)
    return log_path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _load_json(path: Path, label: str) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}")
    raw = _read_text(path)
    try:
        return json.loads(raw)
    except Exception as e:
        raise ValueError(f"Invalid JSON in {label}: {e}") from e


def _safe_write_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")

    if orjson is not None:
        tmp.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS))
    else:
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    # Read-back validation (prevents partial/truncated writes)
    _ = json.loads(tmp.read_text(encoding="utf-8"))
    tmp.replace(path)


def _env_required(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing required env var: {name}")
    return v.strip()


def _env_optional(name: str) -> Optional[str]:
    v = os.getenv(name)
    if not v or not v.strip():
        return None
    return v.strip()


def load_trakt_env() -> TraktEnv:
    return TraktEnv(
        client_id=_env_required("TRAKT_CLIENT_ID"),
        client_secret=_env_required("TRAKT_CLIENT_SECRET"),
        oauth_redirect_url=_env_required("TRAKT_OAUTH_REDIRECT_URL"),
        username=_env_optional("TRAKT_USERNAME"),
        access_token=_env_optional("TRAKT_ACCESS_TOKEN"),
    )


def trakt_headers(env: TraktEnv) -> Dict[str, str]:
    h = {
        "Content-Type": "application/json",
        "trakt-api-version": TRAKT_API_VERSION,
        "trakt-api-key": env.client_id,
        "User-Agent": USER_AGENT,
    }
    if env.access_token:
        h["Authorization"] = f"Bearer {env.access_token}"
    return h


def trakt_get(env: TraktEnv, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{TRAKT_API_BASE}{path}"
    r = requests.get(url, headers=trakt_headers(env), params=params or {}, timeout=DEFAULT_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"TRAKT GET {path} failed: {r.status_code} {r.text[:300]}")
    return r.json()


# -------------------------
# Trakt watchlist fetch
# -------------------------
def _watchlist_base(env: TraktEnv) -> Optional[str]:
    # No OAuth/login/PIN flow is triggered here.
    # If access_token exists -> use /users/me; else if username exists -> use /users/{username}; else skip.
    if env.access_token:
        return "/users/me/watchlist"
    if env.username:
        return f"/users/{env.username}/watchlist"
    return None


def fetch_watchlist_movies(env: TraktEnv) -> List[Dict[str, Any]]:
    base = _watchlist_base(env)
    if not base:
        return []
    return trakt_get(env, f"{base}/movies", params={"extended": "full"})


def fetch_watchlist_shows(env: TraktEnv) -> List[Dict[str, Any]]:
    base = _watchlist_base(env)
    if not base:
        return []
    return trakt_get(env, f"{base}/shows", params={"extended": "full"})


# -------------------------
# Canonical watchlist shaping (minimal, id-focused)
# -------------------------
def _wl_movie_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    movie = item.get("movie") or {}
    ids = movie.get("ids") or {}
    tmdb = ids.get("tmdb")
    trakt = ids.get("trakt")
    if tmdb is None and trakt is None:
        return None
    return {
        "type": "movie",
        "tmdb_id": tmdb,
        "trakt_id": trakt,
        "title": movie.get("title") or "",
        "year": movie.get("year"),
        "listed_at": item.get("listed_at"),
    }


def _wl_show_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    show = item.get("show") or {}
    ids = show.get("ids") or {}
    tmdb = ids.get("tmdb")
    trakt = ids.get("trakt")
    if tmdb is None and trakt is None:
        return None
    return {
        "type": "show",
        "tmdb_id": tmdb,
        "trakt_id": trakt,
        "name": show.get("title") or "",
        "year": show.get("year"),
        "listed_at": item.get("listed_at"),
    }


def build_watchlist(env: TraktEnv) -> Tuple[List[Dict[str, Any]], Dict[str, int], str]:
    """
    Returns: (watchlist_items, counts, mode)
      mode:
        - "bearer_me"  (TRAKT_ACCESS_TOKEN present; /users/me)
        - "public_user" (TRAKT_USERNAME present; /users/{username})
        - "skipped"     (no token and no username; no network calls made)
    """
    base = _watchlist_base(env)
    if not base:
        counts = {"watchlist_movies": 0, "watchlist_shows": 0, "watchlist_total": 0}
        return [], counts, "skipped"

    mode = "bearer_me" if env.access_token else "public_user"

    movies_raw = fetch_watchlist_movies(env)
    shows_raw = fetch_watchlist_shows(env)

    out: List[Dict[str, Any]] = []

    it_m = movies_raw
    if tqdm is not None:
        it_m = tqdm(movies_raw, desc="Trakt watchlist movies", unit="movie")  # type: ignore
    for x in it_m:
        item = _wl_movie_item(x)
        if item:
            out.append(item)

    it_s = shows_raw
    if tqdm is not None:
        it_s = tqdm(shows_raw, desc="Trakt watchlist shows", unit="show")  # type: ignore
    for x in it_s:
        item = _wl_show_item(x)
        if item:
            out.append(item)

    counts = {
        "watchlist_movies": sum(1 for i in out if i.get("type") == "movie"),
        "watchlist_shows": sum(1 for i in out if i.get("type") == "show"),
        "watchlist_total": len(out),
    }
    return out, counts, mode


# -------------------------
# Enrichment into existing data.json (non-destructive)
# -------------------------
def index_by_tmdb_id(items: List[Dict[str, Any]], key: str = "tmdb_id") -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    for it in items:
        v = it.get(key)
        if isinstance(v, int) and v > 0:
            out[v] = it
    return out


def enrich_trakt_ids(existing: Dict[str, Any], watchlist: List[Dict[str, Any]]) -> Dict[str, int]:
    shows = existing.get("shows") or []
    movies = existing.get("movies") or []

    wl_shows = [i for i in watchlist if i.get("type") == "show"]
    wl_movies = [i for i in watchlist if i.get("type") == "movie"]

    wl_shows_idx = index_by_tmdb_id(wl_shows)
    wl_movies_idx = index_by_tmdb_id(wl_movies)

    updated_show = 0
    updated_movie = 0

    for s in shows:
        tmdb_id = s.get("tmdb_id")
        if isinstance(tmdb_id, int) and tmdb_id in wl_shows_idx:
            trakt_id = wl_shows_idx[tmdb_id].get("trakt_id")
            if trakt_id is not None and s.get("trakt_id") != trakt_id:
                s["trakt_id"] = trakt_id
                updated_show += 1

    for m in movies:
        tmdb_id = m.get("tmdb_id")
        if isinstance(tmdb_id, int) and tmdb_id in wl_movies_idx:
            trakt_id = wl_movies_idx[tmdb_id].get("trakt_id")
            if trakt_id is not None and m.get("trakt_id") != trakt_id:
                m["trakt_id"] = trakt_id
                updated_movie += 1

    return {"enriched_shows": updated_show, "enriched_movies": updated_movie}


def append_error(existing: Dict[str, Any], message: str) -> None:
    errs = existing.get("errors")
    if not isinstance(errs, list):
        existing["errors"] = []
        errs = existing["errors"]
    errs.append(
        {
            "source": "fetch_trakt.py",
            "timestamp_utc": _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "message": str(message),
        }
    )


def update_metadata(
    existing: Dict[str, Any],
    cfg_hash: str,
    trakt_counts: Dict[str, int],
    enrich_counts: Dict[str, int],
    mode: str,
    env: TraktEnv,
) -> None:
    meta = existing.get("metadata")
    if not isinstance(meta, dict):
        existing["metadata"] = {}
        meta = existing["metadata"]

    meta["trakt_sync"] = {
        "timestamp_utc": _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": "fetch_trakt.py",
        "script_version": "v2.2.1",
        "build": "14.01.06",
        "config_sha256": cfg_hash,
        "mode": mode,
        "redirect_url": env.oauth_redirect_url,
        "counts": trakt_counts,
        "enrichment": enrich_counts,
        "username_used": bool(env.username),
        "access_token_used": bool(env.access_token),
    }


def load_config_hash_only() -> str:
    raw = _read_text(CONFIG_JSON_PATH)
    _ = json.loads(raw)
    return _sha256_text(raw)


# -------------------------
# Main
# -------------------------
def main() -> int:
    setup_logging()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Load env (NO TRAKT_USERNAME required)
    try:
        env = load_trakt_env()
    except Exception as e:
        logging.error("[fetch_trakt] %s", e)
        return 2

    if not DATA_JSON_PATH.exists():
        logging.error("[fetch_trakt] Missing data/data.json. Run fetch_tmdb.py first.")
        return 3

    try:
        existing = _load_json(DATA_JSON_PATH, "data/data.json")
    except Exception as e:
        logging.error("[fetch_trakt] %s", e)
        return 4

    # Config hash (authoritative input)
    try:
        cfg_hash = load_config_hash_only()
    except Exception as e:
        logging.error("[fetch_trakt] config.json load failed: %s", e)
        append_error(existing, f"config.json load failed: {e}")
        _safe_write_json_atomic(DATA_JSON_PATH, existing)
        return 5

    # Fetch trakt data (or skip)
    try:
        watchlist, trakt_counts, mode = build_watchlist(env)

        if mode == "skipped":
            logging.info("[fetch_trakt] Trakt fetch skipped (no TRAKT_ACCESS_TOKEN and no TRAKT_USERNAME).")
            enrich_counts: Dict[str, int] = {"enriched_shows": 0, "enriched_movies": 0}
            update_metadata(existing, cfg_hash, trakt_counts, enrich_counts, mode, env)
            _safe_write_json_atomic(DATA_JSON_PATH, existing)
            LAST_REFRESH_TRAKT_PATH.write_text(_dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")
            return 0

        logging.info("[fetch_trakt] mode=%s", mode)
        logging.info("[fetch_trakt] watchlist_total=%s", trakt_counts.get("watchlist_total"))
    except Exception as e:
        logging.error("[fetch_trakt] Trakt fetch failed: %s", e)
        append_error(existing, f"Trakt fetch failed: {e}")
        _safe_write_json_atomic(DATA_JSON_PATH, existing)
        return 6

    # Refuse destructive wipe if Trakt returns empty but existing watchlist is non-empty
    existing_watchlist = existing.get("watchlist")
    if isinstance(existing_watchlist, list) and len(existing_watchlist) > 0 and len(watchlist) == 0:
        msg = "Refusing to overwrite watchlist with empty result (existing watchlist is non-empty)."
        logging.error("[fetch_trakt] %s", msg)
        append_error(existing, msg)
        _safe_write_json_atomic(DATA_JSON_PATH, existing)
        return 7

    # Apply updates (non-destructive; preserve existing keys)
    existing["watchlist"] = watchlist

    enrich_counts: Dict[str, int] = {}
    try:
        enrich_counts = enrich_trakt_ids(existing, watchlist)
    except Exception as e:
        logging.error("[fetch_trakt] Enrichment failed: %s", e)
        append_error(existing, f"Enrichment failed: {e}")
        enrich_counts = {"enriched_shows": 0, "enriched_movies": 0}

    update_metadata(existing, cfg_hash, trakt_counts, enrich_counts, mode, env)

    # Write atomically
    try:
        _safe_write_json_atomic(DATA_JSON_PATH, existing)
        LAST_REFRESH_TRAKT_PATH.write_text(_dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")
    except Exception as e:
        logging.error("[fetch_trakt] Write failed: %s", e)
        return 8

    logging.info(
        "[fetch_trakt] Updated data.json (watchlist=%s, enriched_shows=%s, enriched_movies=%s)",
        trakt_counts.get("watchlist_total"),
        enrich_counts.get("enriched_shows", 0),
        enrich_counts.get("enriched_movies", 0),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
