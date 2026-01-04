#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/fetch_trakt.py
# [PROJECT] my_TV_Movie
# [ROLE]    Enrich data/data.json with Trakt IDs + lightweight Trakt metadata
# [VERSION] v1.3.0
# [UPDATED] 2025-12-29_00-00-00
# [BUILD]   14.01.08
#
# Purpose:
#   Public Trakt enrichment using ONLY API_TRAKT_ID + API_TRAKT_KEY.
#   - NO user context
#   - NO auth flows
#   - NO login, redirect, PIN, token, or user endpoints
#
# Behavior:
#   - Loads existing data/data.json (produced earlier in pipeline)
#   - For each show/movie that has tmdb_id, attempts to resolve Trakt IDs via
#     Trakt public search endpoint (tmdb lookup).
#   - Writes back into data/data.json atomically ONLY if changes occurred:
#       * missing/changed trakt_id on any item
#       * new/changed metadata.trakt_public_enrichment block
#       * new error appended
#   - Preserves all existing keys/structure (non-destructive).
#
# Required env (ONLY):
#   - API_TRAKT_ID
#   - API_TRAKT_KEY
#
# Notes:
#   - API_TRAKT_KEY is required to exist (per requirements) but is not transmitted
#     to Trakt for public lookups. Only API_TRAKT_ID is used for the public API.
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import requests  # type: ignore
except Exception:
    print("ERROR: Missing dependency 'requests'. Install via requirements.txt.", file=sys.stderr)
    raise

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
DATA_JSON_PATH = DATA_DIR / "data.json"
LOGS_DIR = REPO_ROOT / "logs"

TRAKT_API_BASE = "https://api.trakt.tv"
TRAKT_API_VERSION = "2"
DEFAULT_TIMEOUT = 30

USER_AGENT = "my_TV_Movie fetch_trakt.py (public enrichment)"


def _now_stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")


def _utc_iso() -> str:
    # keep existing style; avoid introducing new time semantics
    return _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


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
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    _ = json.loads(tmp.read_text(encoding="utf-8"))
    tmp.replace(path)


def _env_required(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing required env var: {name}")
    return v.strip()


def load_trakt_env() -> Tuple[str, str]:
    trakt_id = _env_required("API_TRAKT_ID")
    trakt_key = _env_required("API_TRAKT_KEY")
    return trakt_id, trakt_key


def trakt_headers(trakt_id: str) -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "trakt-api-version": TRAKT_API_VERSION,
        "trakt-api-key": trakt_id,
        "User-Agent": USER_AGENT,
    }


def trakt_get(trakt_id: str, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{TRAKT_API_BASE}{path}"
    r = requests.get(url, headers=trakt_headers(trakt_id), params=params or {}, timeout=DEFAULT_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"TRAKT GET {path} failed: {r.status_code} {r.text[:300]}")
    return r.json()


def append_error(existing: Dict[str, Any], message: str) -> bool:
    errs = existing.get("errors")
    if not isinstance(errs, list):
        existing["errors"] = []
        errs = existing["errors"]
    errs.append({"source": "fetch_trakt.py", "timestamp_utc": _utc_iso(), "message": str(message)})
    return True


def _resolve_trakt_by_tmdb(trakt_id: str, media_type: str, tmdb_id: int) -> Optional[Dict[str, Any]]:
    if tmdb_id <= 0:
        return None
    data = trakt_get(trakt_id, f"/search/tmdb/{tmdb_id}", params={"type": media_type})
    if not isinstance(data, list) or not data:
        return None
    first = data[0]
    return first if isinstance(first, dict) else None


def _extract_ids(search_hit: Dict[str, Any], media_type: str) -> Optional[Tuple[int, int]]:
    obj = search_hit.get(media_type)
    if not isinstance(obj, dict):
        return None
    ids = obj.get("ids")
    if not isinstance(ids, dict):
        return None
    trakt_val = ids.get("trakt")
    tmdb_val = ids.get("tmdb")
    if not isinstance(trakt_val, int) or trakt_val <= 0:
        return None
    if not isinstance(tmdb_val, int) or tmdb_val <= 0:
        return None
    return trakt_val, tmdb_val


def enrich_data_json(existing: Dict[str, Any], trakt_id: str) -> Tuple[Dict[str, int], bool]:
    shows = existing.get("shows")
    movies = existing.get("movies")
    if not isinstance(shows, list):
        shows = []
    if not isinstance(movies, list):
        movies = []

    updated_shows = updated_movies = 0
    already_shows = already_movies = 0
    looked_up = not_found = 0
    changed = False

    for s in shows:
        if not isinstance(s, dict):
            continue
        tmdb = s.get("tmdb_id")
        if not isinstance(tmdb, int) or tmdb <= 0:
            continue
        looked_up += 1
        try:
            hit = _resolve_trakt_by_tmdb(trakt_id, "show", tmdb)
            ids = _extract_ids(hit, "show") if hit else None
            if not ids:
                not_found += 1
                continue
            trakt_val, tmdb_val = ids
            if tmdb_val != tmdb:
                not_found += 1
                continue
            if s.get("trakt_id") != trakt_val:
                s["trakt_id"] = trakt_val
                updated_shows += 1
                changed = True
            else:
                already_shows += 1
        except Exception as e:
            changed = append_error(existing, f"Trakt lookup failed for show tmdb_id={tmdb}: {e}") or changed

    for m in movies:
        if not isinstance(m, dict):
            continue
        tmdb = m.get("tmdb_id")
        if not isinstance(tmdb, int) or tmdb <= 0:
            continue
        looked_up += 1
        try:
            hit = _resolve_trakt_by_tmdb(trakt_id, "movie", tmdb)
            ids = _extract_ids(hit, "movie") if hit else None
            if not ids:
                not_found += 1
                continue
            trakt_val, tmdb_val = ids
            if tmdb_val != tmdb:
                not_found += 1
                continue
            if m.get("trakt_id") != trakt_val:
                m["trakt_id"] = trakt_val
                updated_movies += 1
                changed = True
            else:
                already_movies += 1
        except Exception as e:
            changed = append_error(existing, f"Trakt lookup failed for movie tmdb_id={tmdb}: {e}") or changed

    counts = {
        "looked_up": looked_up,
        "not_found": not_found,
        "updated_shows": updated_shows,
        "updated_movies": updated_movies,
        "already_shows": already_shows,
        "already_movies": already_movies,
    }
    return counts, changed


def update_metadata(existing: Dict[str, Any], trakt_id: str, counts: Dict[str, int]) -> bool:
    meta = existing.get("metadata")
    if not isinstance(meta, dict):
        existing["metadata"] = {}
        meta = existing["metadata"]

    new_block = {
        "timestamp_utc": _utc_iso(),
        "script": "fetch_trakt.py",
        "mode": "public_lookup",
        "counts": counts,
        "client_id_sha256": _sha256_text(trakt_id),
    }
    prior = meta.get("trakt_public_enrichment")
    if prior != new_block:
        meta["trakt_public_enrichment"] = new_block
        return True
    return False


def main() -> int:
    setup_logging()

    try:
        trakt_id, trakt_key = load_trakt_env()
    except Exception as e:
        logging.error("[fetch_trakt] %s", e)
        return 2

    logging.info("[fetch_trakt] API_TRAKT_ID present (len=%d)", len(trakt_id))
    logging.info("[fetch_trakt] API_TRAKT_KEY present (len=%d) [not transmitted]", len(trakt_key))

    if not DATA_JSON_PATH.exists():
        logging.error("[fetch_trakt] Missing data/data.json. Run earlier pipeline steps first.")
        return 3

    try:
        existing = _load_json(DATA_JSON_PATH, "data/data.json")
    except Exception as e:
        logging.error("[fetch_trakt] %s", e)
        return 4

    before_hash = _sha256_text(_read_text(DATA_JSON_PATH))

    counts, changed_items = enrich_data_json(existing, trakt_id)
    changed_meta = update_metadata(existing, trakt_id, counts)
    changed = changed_items or changed_meta

    logging.info(
        "[fetch_trakt] DONE looked_up=%s not_found=%s updated_shows=%s updated_movies=%s already_shows=%s already_movies=%s changed=%s",
        counts.get("looked_up", 0),
        counts.get("not_found", 0),
        counts.get("updated_shows", 0),
        counts.get("updated_movies", 0),
        counts.get("already_shows", 0),
        counts.get("already_movies", 0),
        "YES" if changed else "NO",
    )

    if not changed:
        logging.info("[fetch_trakt] no changes detected; skipped write (data.json untouched).")
        return 0

    _safe_write_json_atomic(DATA_JSON_PATH, existing)
    after_hash = _sha256_text(_read_text(DATA_JSON_PATH))

    if before_hash == after_hash:
        logging.info("[fetch_trakt] write produced identical bytes; leaving file as-is.")
    else:
        logging.info("[fetch_trakt] wrote=%s", DATA_JSON_PATH)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
