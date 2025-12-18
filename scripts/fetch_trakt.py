#!/usr/bin/env python3
# ==============================================================================
# [FILE]        scripts/fetch_trakt.py
# [PROJECT]     my_TV_Movie
# [ROLE]        Pull Trakt watch-state and export static trakt_state.json for UI
# [VERSION]     v1.5.0
# [UPDATED]     2025-12-17_16-30-00
# [BUILD]       14.01.06
#
# [DEPENDS ON]
#   - Environment variables:
#       API_TRAKT_CLIENT_ID          (required)
#       API_TRAKT_CLIENT_SECRET      (required for token refresh)
#       API_TRAKT_ACCESS_TOKEN       (optional; if missing, script tries refresh)
#       API_TRAKT_REFRESH_TOKEN      (optional; if missing, script cannot refresh)
#   - data/data.json                 (optional; used for quick integrity checks)
#
# [OUTPUTS]
#   - data/trakt_state.json
#   - logs/fetch_trakt_YYYY-MM-DD_HHMMSS.log.txt
#
# [NOTES]
#   - This script is READ-ONLY against Trakt (no scrobble, no sync writes).
#   - UI uses trakt_state.json to mark watched/unwatched.
#   - If tokens are missing/invalid, script fails gracefully without touching existing state file.
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests  # type: ignore
except Exception:
    print("ERROR: Missing dependency 'requests'. Install it inside your venv:", file=sys.stderr)
    print("  python -m pip install requests", file=sys.stderr)
    raise


# -------------------------
# Paths
# -------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = REPO_ROOT / "data"
DATA_JSON_PATH = DATA_DIR / "data.json"  # optional read
TRAKT_STATE_PATH = DATA_DIR / "trakt_state.json"

LOGS_DIR = REPO_ROOT / "logs"


# -------------------------
# Constants
# -------------------------
TRAKT_API = "https://api.trakt.tv"
TRAKT_OAUTH_TOKEN = "https://trakt.tv/oauth/token"
USER_AGENT = "my_TV_Movie fetch_trakt.py (static state builder)"
TIMEOUT = 30


def _now_stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")


def setup_logging() -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"fetch_trakt_{_now_stamp()}.log.txt"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
    )
    logging.info("[fetch_trakt] log=%s", log_path)
    return log_path


def env(name: str) -> Optional[str]:
    v = os.getenv(name)
    return v.strip() if v and v.strip() else None


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_json_if_exists(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None


def trakt_headers(client_id: str, access_token: str) -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "trakt-api-version": "2",
        "trakt-api-key": client_id,
        "Authorization": f"Bearer {access_token}",
    }


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> Optional[Dict[str, Any]]:
    payload = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "grant_type": "refresh_token",
    }
    r = requests.post(TRAKT_OAUTH_TOKEN, json=payload, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
    if r.status_code != 200:
        logging.error("[fetch_trakt] refresh failed: %s %s", r.status_code, r.text[:200])
        return None
    return r.json()


def trakt_get(path: str, client_id: str, access_token: str, params: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{TRAKT_API}{path}"
    r = requests.get(url, headers=trakt_headers(client_id, access_token), params=params, timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"Trakt GET {path} failed: {r.status_code} {r.text[:200]}")
    return r.json()


def safe_write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(obj, ensure_ascii=False, indent=2)

    if len(payload.strip()) < 10:
        raise RuntimeError("Refusing to write suspiciously small JSON payload")

    # parse-back validation
    _ = json.loads(payload)

    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def extract_watched_state(
    watched_shows: List[Dict[str, Any]],
    watched_movies: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Output structures optimized for O(1) checks in UI by TMDB id.
    """
    shows_by_tmdb: Dict[str, Any] = {}
    movies_by_tmdb: Dict[str, Any] = {}

    # watched shows: /sync/watched/shows returns seasons + episodes with numbers
    for s in watched_shows:
        ids = (s.get("show") or {}).get("ids") or {}
        tmdb = ids.get("tmdb")
        if not tmdb:
            continue
        tmdb_str = str(tmdb)

        seasons_state: Dict[str, Any] = {}
        for season in (s.get("seasons") or []):
            sn = season.get("number")
            if sn is None:
                continue
            sn_str = str(int(sn))
            eps = set()
            for ep in (season.get("episodes") or []):
                en = ep.get("number")
                if en is None:
                    continue
                eps.add(int(en))
            seasons_state[sn_str] = sorted(eps)

        shows_by_tmdb[tmdb_str] = {
            "type": "show",
            "tmdb_id": int(tmdb),
            "seasons": seasons_state,
        }

    # watched movies: /sync/watched/movies
    for m in watched_movies:
        ids = (m.get("movie") or {}).get("ids") or {}
        tmdb = ids.get("tmdb")
        if not tmdb:
            continue
        tmdb_str = str(tmdb)
        movies_by_tmdb[tmdb_str] = {
            "type": "movie",
            "tmdb_id": int(tmdb),
            "watched": True,
        }

    return shows_by_tmdb, movies_by_tmdb


def main() -> int:
    setup_logging()

    client_id = env("API_TRAKT_CLIENT_ID")
    client_secret = env("API_TRAKT_CLIENT_SECRET")
    access_token = env("API_TRAKT_ACCESS_TOKEN")
    refresh_token = env("API_TRAKT_REFRESH_TOKEN")

    if not client_id:
        logging.error("Missing API_TRAKT_CLIENT_ID")
        return 2
    if not client_secret:
        logging.error("Missing API_TRAKT_CLIENT_SECRET")
        return 2

    # Access token strategy:
    # 1) Use access token if present
    # 2) Else try refresh if refresh_token present
    token_meta: Dict[str, Any] = {"refreshed": False}

    if not access_token:
        if not refresh_token:
            logging.error("Missing API_TRAKT_ACCESS_TOKEN and API_TRAKT_REFRESH_TOKEN (cannot authenticate).")
            return 2
        logging.info("[fetch_trakt] No access token; attempting refresh...")
        tok = refresh_access_token(client_id, client_secret, refresh_token)
        if not tok:
            logging.error("[fetch_trakt] Token refresh failed.")
            return 3
        access_token = tok.get("access_token")
        refresh_token_new = tok.get("refresh_token")
        expires_in = tok.get("expires_in")
        token_meta = {
            "refreshed": True,
            "expires_in": expires_in,
            "received_at_utc": _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        if refresh_token_new:
            token_meta["refresh_token_rotated"] = True
        if not access_token:
            logging.error("[fetch_trakt] Refresh response did not contain access_token.")
            return 3

    # Pull watched state (minimal calls; deterministic)
    try:
        watched_shows = trakt_get("/sync/watched/shows", client_id, access_token, params={"extended": "full"})
        watched_movies = trakt_get("/sync/watched/movies", client_id, access_token, params={"extended": "full"})
    except Exception as e:
        logging.exception("[fetch_trakt] Fetch failed: %s", e)
        return 4

    shows_by_tmdb, movies_by_tmdb = extract_watched_state(watched_shows, watched_movies)

    # Optional integrity snapshot vs local data.json (helps catch mismatched TMDB ids)
    local_data = load_json_if_exists(DATA_JSON_PATH)
    local_meta: Dict[str, Any] = {}
    if local_data and isinstance(local_data, dict):
        try:
            local_meta = {
                "data_json_present": True,
                "data_json_generated_at": (local_data.get("meta") or {}).get("generated_at"),
                "data_json_config_sha256": (local_data.get("meta") or {}).get("config_sha256"),
                "shows_count": len(local_data.get("shows") or []),
                "movies_count": len(local_data.get("movies") or []),
            }
        except Exception:
            local_meta = {"data_json_present": True}
    else:
        local_meta = {"data_json_present": False}

    state = {
        "meta": {
            "generated_at": _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "script_version": "v1.5.0",
            "build": "14.01.06",
            "token_meta": token_meta,
            "local_data_snapshot": local_meta,
        },
        "shows_by_tmdb": shows_by_tmdb,
        "movies_by_tmdb": movies_by_tmdb,
    }

    # Guardrails: do not overwrite with empty if prior file exists (unless truly empty library)
    prior = load_json_if_exists(TRAKT_STATE_PATH)
    if prior and (len(shows_by_tmdb) == 0 and len(movies_by_tmdb) == 0):
        logging.error("[fetch_trakt] Refusing to overwrite existing trakt_state.json with empty state.")
        return 5

    safe_write_json(TRAKT_STATE_PATH, state)
    logging.info("[fetch_trakt] Wrote: %s (shows=%s movies=%s)", TRAKT_STATE_PATH, len(shows_by_tmdb), len(movies_by_tmdb))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
