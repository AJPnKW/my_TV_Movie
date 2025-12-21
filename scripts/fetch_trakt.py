#!/usr/bin/env python3
# ==============================================================================
# File: scripts/fetch_trakt.py
# Project: my_TV_Movie
# Purpose:
#   Public Trakt enrichment using ONLY API_TRAKT_ID + API_TRAKT_KEY.
#   - NO user context
#   - NO auth flows
#   - NO login, redirect, PIN, token, or user endpoints
#
# Behavior:
#   - Loads existing data/data.json (produced earlier in pipeline)
#   - For each show/movie that has tmdb_id, attempts to resolve Trakt IDs via
#     public Trakt search endpoint (tmdb lookup).
#   - Writes back into data/data.json atomically, preserving all existing keys.
#   - Surfaces errors visually (stdout + log file) and records failures into
#     data["errors"] without requiring any other env vars.
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
    # read-back validation
    _ = json.loads(tmp.read_text(encoding="utf-8"))
    tmp.replace(path)


def _env_required(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing required env var: {name}")
    return v.strip()


def load_trakt_env() -> Tuple[str, str]:
    # REQUIRED: both must exist (per requirements)
    trakt_id = _env_required("API_TRAKT_ID")
    trakt_key = _env_required("API_TRAKT_KEY")
    return trakt_id, trakt_key


def trakt_headers(trakt_id: str) -> Dict[str, str]:
    # Public Trakt API: client id in header
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


def append_error(existing: Dict[str, Any], message: str) -> None:
    errs = existing.get("errors")
    if not isinstance(errs, list):
        existing["errors"] = []
        errs = existing["errors"]
    errs.append(
        {
            "source": "fetch_trakt.py",
            "timestamp_utc": _utc_iso(),
            "message": str(message),
        }
    )


def _resolve_trakt_by_tmdb(trakt_id: str, media_type: str, tmdb_id: int) -> Optional[Dict[str, Any]]:
    """
    Public lookup: search by tmdb id.
    Endpoint: /search/tmdb/{tmdb_id}?type={movie|show}
    Returns first match record dict or None.
    """
    if tmdb_id <= 0:
        return None
    # Public search endpoint; no user context
    data = trakt_get(trakt_id, f"/search/tmdb/{tmdb_id}", params={"type": media_type})
    if not isinstance(data, list) or not data:
        return None
    first = data[0]
    if not isinstance(first, dict):
        return None
    return first


def _extract_ids(search_hit: Dict[str, Any], media_type: str) -> Optional[Tuple[int, int]]:
    """
    Returns (trakt_id, tmdb_id) from search result for the given media_type.
    """
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


def enrich_data_json(existing: Dict[str, Any], trakt_id: str) -> Dict[str, int]:
    """
    Non-destructive enrichment:
      - For each show/movie with tmdb_id, add/update trakt_id field if resolvable.
    Returns counts.
    """
    shows = existing.get("shows")
    movies = existing.get("movies")

    if not isinstance(shows, list):
        shows = []
    if not isinstance(movies, list):
        movies = []

    updated_shows = 0
    updated_movies = 0
    looked_up = 0
    not_found = 0

    # Shows
    for s in shows:
        if not isinstance(s, dict):
            continue
        tmdb = s.get("tmdb_id")
        if not isinstance(tmdb, int) or tmdb <= 0:
            continue

        looked_up += 1
        try:
            hit = _resolve_trakt_by_tmdb(trakt_id, "show", tmdb)
            if not hit:
                not_found += 1
                continue
            ids = _extract_ids(hit, "show")
            if not ids:
                not_found += 1
                continue
            trakt_val, tmdb_val = ids
            if tmdb_val != tmdb:
                # defensive: don't set mismatched ids
                not_found += 1
                continue
            if s.get("trakt_id") != trakt_val:
                s["trakt_id"] = trakt_val
                updated_shows += 1
        except Exception as e:
            append_error(existing, f"Trakt lookup failed for show tmdb_id={tmdb}: {e}")
            continue

    # Movies
    for m in movies:
        if not isinstance(m, dict):
            continue
        tmdb = m.get("tmdb_id")
        if not isinstance(tmdb, int) or tmdb <= 0:
            continue

        looked_up += 1
        try:
            hit = _resolve_trakt_by_tmdb(trakt_id, "movie", tmdb)
            if not hit:
                not_found += 1
                continue
            ids = _extract_ids(hit, "movie")
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
        except Exception as e:
            append_error(existing, f"Trakt lookup failed for movie tmdb_id={tmdb}: {e}")
            continue

    return {
        "looked_up": looked_up,
        "not_found": not_found,
        "updated_shows": updated_shows,
        "updated_movies": updated_movies,
    }


def update_metadata(existing: Dict[str, Any], trakt_id: str, counts: Dict[str, int]) -> None:
    meta = existing.get("metadata")
    if not isinstance(meta, dict):
        existing["metadata"] = {}
        meta = existing["metadata"]

    # Record only what this script did; no auth/user semantics
    meta["trakt_public_enrichment"] = {
        "timestamp_utc": _utc_iso(),
        "script": "fetch_trakt.py",
        "mode": "public_lookup",
        "counts": counts,
        "client_id_sha256": _sha256_text(trakt_id),
    }


def main() -> int:
    setup_logging()

    # Load required env vars (ONLY the two allowed names)
    try:
        trakt_id, trakt_key = load_trakt_env()
    except Exception as e:
        logging.error("[fetch_trakt] %s", e)
        return 2

    # Per requirements: API_TRAKT_KEY must exist. It is not used for public endpoints.
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

    # Enrich
    try:
        counts = enrich_data_json(existing, trakt_id)
    except Exception as e:
        logging.error("[fetch_trakt] enrichment failed: %s", e)
        append_error(existing, f"Trakt enrichment failed: {e}")
        _safe_write_json_atomic(DATA_JSON_PATH, existing)
        return 5

    update_metadata(existing, trakt_id, counts)

    # Write atomically
    try:
        _safe_write_json_atomic(DATA_JSON_PATH, existing)
    except Exception as e:
        logging.error("[fetch_trakt] write failed: %s", e)
        return 6

    logging.info(
        "[fetch_trakt] DONE looked_up=%s not_found=%s updated_shows=%s updated_movies=%s",
        counts.get("looked_up", 0),
        counts.get("not_found", 0),
        counts.get("updated_shows", 0),
        counts.get("updated_movies", 0),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
