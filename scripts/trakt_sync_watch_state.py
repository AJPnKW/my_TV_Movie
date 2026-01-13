#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/trakt_sync_watch_state.py
# [PROJECT] my_TV_Movie
# [ROLE]    Pull Trakt user watch-state (movies + shows/season/episodes) and embed
#           into data/data.json under watch_state.trakt
# [VERSION] v1.0.0
# [UPDATED] 2026-01-12
# [BUILD]   14.01.12
#
# Requires OAuth tokens:
#   API_TRAKT_ID, API_TRAKT_KEY (secret), API_TRAKT_ACCESS_TOKEN
# Optional:
#   API_TRAKT_REFRESH_TOKEN (refresh attempt; cannot persist to GH secrets)
#
# Behavior:
# - If access token missing: exit(0) (no-op).
# - If 401:
#     - If refresh token available: refresh once, proceed in-memory, and write
#       data/trakt_tokens_latest.json for manual secret updates.
#     - Else: record error in data.json and exit(0).
# - Writes watch_state.trakt = {generated_utc, user, movies{}, shows{}}
# - Keys are TMDB IDs (int) so UI can join with TMDB metadata.
# ==============================================================================
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "data" / "data.json"
TOK_OUT = REPO_ROOT / "data" / "trakt_tokens_latest.json"

TRAKT_API_BASE = "https://api.trakt.tv"
TRAKT_TOKEN_URL = "https://trakt.tv/oauth/token"
TRAKT_API_VERSION = "2"


def _utc() -> str:
    return _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def blank(s: str | None) -> bool:
    return s is None or str(s).strip() == ""


def http_json(url: str, headers: dict, method: str = "GET", body_obj=None, timeout: int = 45):
    data = None
    if body_obj is not None:
        data = json.dumps(body_obj).encode("utf-8")
        headers = dict(headers)
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw.strip() else {}


def trakt_headers(client_id: str, access_token: str | None = None) -> dict:
    h = {"trakt-api-version": TRAKT_API_VERSION, "trakt-api-key": client_id}
    if access_token and not blank(access_token):
        h["Authorization"] = f"Bearer {access_token}"
    return h


def refresh_tokens(client_id: str, client_secret: str, refresh_token: str) -> dict:
    payload = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    }
    return http_json(TRAKT_TOKEN_URL, headers={}, method="POST", body_obj=payload)


def load_data() -> Dict[str, Any]:
    if not DATA_PATH.is_file():
        return {"meta": {"generated_utc": _utc()}, "shows": [], "movies": [], "errors": []}
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {"meta": {"generated_utc": _utc()}, "shows": [], "movies": [], "errors": []}


def save_data(data: Dict[str, Any]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    client_id = os.getenv("API_TRAKT_ID")
    client_secret = os.getenv("API_TRAKT_KEY")
    access_token = os.getenv("API_TRAKT_ACCESS_TOKEN")
    refresh_token = os.getenv("API_TRAKT_REFRESH_TOKEN")

    if blank(access_token) or blank(client_id):
        # no-op (local-only feature)
        return 0

    data = load_data()
    data.setdefault("errors", [])

    def record_err(msg: str) -> None:
        data["errors"].append({"type": "trakt_watch_state", "message": msg, "utc": _utc()})

    # Identify user (optional)
    me_url = f"{TRAKT_API_BASE}/users/me"

    def call_me(tok: str) -> dict:
        return http_json(me_url, trakt_headers(client_id, tok))

    def pull_all(tok: str) -> dict:
        watched_movies = http_json(f"{TRAKT_API_BASE}/sync/watched/movies", trakt_headers(client_id, tok))
        watched_shows = http_json(f"{TRAKT_API_BASE}/sync/watched/shows", trakt_headers(client_id, tok))
        return {"watched_movies": watched_movies, "watched_shows": watched_shows}

    try:
        me = call_me(access_token)
        pulled = pull_all(access_token)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if getattr(e, "fp", None) else ""
        if e.code != 401:
            record_err(f"HTTP {e.code} calling Trakt: {body[:500]}")
            save_data(data)
            return 0

        # 401: try refresh once (cannot persist to secrets; writes a file for manual update)
        if blank(client_secret) or blank(refresh_token):
            record_err("401 Unauthorized and no refresh token/secret available; skipped watch-state pull.")
            save_data(data)
            return 0

        try:
            tok = refresh_tokens(client_id, client_secret, refresh_token)
            new_access = tok.get("access_token")
            new_refresh = tok.get("refresh_token")
            if blank(new_access) or blank(new_refresh):
                record_err("401 Unauthorized; refresh attempt did not return new tokens; skipped.")
                save_data(data)
                return 0

            # write tokens for manual update
            TOK_OUT.write_text(json.dumps({"generated_utc": _utc(), "access_token": new_access, "refresh_token": new_refresh}, indent=2), encoding="utf-8")

            me = call_me(new_access)
            pulled = pull_all(new_access)
        except Exception as ex2:
            record_err(f"401 Unauthorized; refresh attempt failed: {str(ex2)[:300]}")
            save_data(data)
            return 0
    except Exception as ex:
        record_err(f"Trakt watch-state pull failed: {str(ex)[:300]}")
        save_data(data)
        return 0

    username = (me or {}).get("username")

    # Normalize into tmdb-keyed maps
    movies_map: Dict[str, Any] = {}
    for it in pulled.get("watched_movies") or []:
        ids = ((it.get("movie") or {}).get("ids") or {})
        tmdb = ids.get("tmdb")
        if tmdb is None:
            continue
        movies_map[str(int(tmdb))] = {
            "last_watched_at": it.get("last_watched_at"),
            "plays": it.get("plays"),
            "trakt_id": ids.get("trakt"),
            "imdb": ids.get("imdb"),
        }

    shows_map: Dict[str, Any] = {}
    for it in pulled.get("watched_shows") or []:
        show = it.get("show") or {}
        ids = (show.get("ids") or {})
        tmdb = ids.get("tmdb")
        if tmdb is None:
            continue
        seasons_obj: Dict[str, Any] = {}
        for s in it.get("seasons") or []:
            sn = s.get("number")
            if sn is None:
                continue
            seasons_obj[str(int(sn))] = {
                "completed": s.get("completed"),
                "episodes": [int(e.get("number")) for e in (s.get("episodes") or []) if isinstance(e.get("number"), int) or str(e.get("number")).isdigit()],
            }
        shows_map[str(int(tmdb))] = {
            "last_watched_at": it.get("last_watched_at"),
            "last_updated_at": it.get("last_updated_at"),
            "plays": it.get("plays"),
            "completed": it.get("completed"),
            "trakt_id": ids.get("trakt"),
            "imdb": ids.get("imdb"),
            "tvdb": ids.get("tvdb"),
            "seasons": seasons_obj,
        }

    data.setdefault("watch_state", {})
    data["watch_state"]["trakt"] = {
        "generated_utc": _utc(),
        "user": username,
        "movies": movies_map,
        "shows": shows_map,
    }

    save_data(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
