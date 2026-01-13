#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/trakt_push_watch_queue.py
# [PROJECT] my_TV_Movie
# [ROLE]    Push local watch/rating actions to Trakt (OAuth) from data/watch_queue.json
# [VERSION] v1.0.0
# [UPDATED] 2026-01-13
# [BUILD]   14.01.13
#
# Queue contract (data/watch_queue.json):
# {
#   "generated_utc": "2026-01-13T00:00:00Z",
#   "items": [
#     {
#       "id": "uuid-or-client-id",
#       "action": "add" | "remove" | "rate",
#       "type": "movie" | "show" | "season" | "episode",
#       "tmdb_id": 123,                 # show/movie TMDB id (required)
#       "season": 7,                    # required for season/episode
#       "episode": 3,                   # required for episode
#       "watched_at": "2026-01-13T01:02:03Z",   # optional for add/remove
#       "rating": 8                      # 1-10, only for action=rate
#     }
#   ]
# }
#
# Behavior:
# - If OAuth access token missing => exit(0) (no-op)
# - If queue missing/empty => exit(0) (no-op)
# - POSTs:
#     /sync/history        (add)
#     /sync/history/remove (remove)
#     /sync/ratings        (rate)
# - Acks + clears queue:
#     data/watch_queue.acked.json
#     data/trakt_push_watch_queue_report.json
# ==============================================================================

from __future__ import annotations

import json
import os
import datetime as _dt
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
QUEUE_PATH = DATA_DIR / "watch_queue.json"
ACK_PATH = DATA_DIR / "watch_queue.acked.json"
REPORT_PATH = DATA_DIR / "trakt_push_watch_queue_report.json"
LOG_DIR = REPO_ROOT / "logs"

TRAKT_API_BASE = "https://api.trakt.tv"
TRAKT_TOKEN_URL = "https://trakt.tv/oauth/token"
TRAKT_API_VERSION = "2"
DEFAULT_TIMEOUT = 45


def utc() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def ts_file() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y%m%d_%H%M%S")


def blank(s: Any) -> bool:
    return s is None or str(s).strip() == ""


def log_path() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / f"trakt_push_watch_queue.{ts_file()}.log.txt"


def log_line(fh, msg: str) -> None:
    fh.write(f"{utc()} | {msg}\n")
    fh.flush()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def trakt_headers(client_id: str, access_token: str | None = None) -> dict:
    h = {"trakt-api-version": TRAKT_API_VERSION, "trakt-api-key": client_id, "Content-Type": "application/json"}
    if access_token and not blank(access_token):
        h["Authorization"] = f"Bearer {access_token}"
    return h


def http_json(url: str, headers: dict, method: str = "GET", body_obj=None, timeout: int = DEFAULT_TIMEOUT):
    data = None
    if body_obj is not None:
        data = json.dumps(body_obj).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw.strip() else {}


def refresh_tokens(client_id: str, client_secret: str, refresh_token: str) -> dict:
    payload = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    }
    return http_json(TRAKT_TOKEN_URL, headers={"Content-Type": "application/json"}, method="POST", body_obj=payload)


def build_bulk_payload(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"movies": [], "shows": [], "seasons": [], "episodes": []}
    for it in items:
        t = str(it.get("type") or "").lower().strip()
        tmdb_id = it.get("tmdb_id")
        watched_at = it.get("watched_at")

        if not isinstance(tmdb_id, int):
            continue

        if t == "movie":
            obj: Dict[str, Any] = {"ids": {"tmdb": int(tmdb_id)}}
            if watched_at and not blank(watched_at):
                obj["watched_at"] = watched_at
            payload["movies"].append(obj)

        elif t == "show":
            obj = {"ids": {"tmdb": int(tmdb_id)}}
            if watched_at and not blank(watched_at):
                obj["watched_at"] = watched_at
            payload["shows"].append(obj)

        elif t == "season":
            season = it.get("season")
            if isinstance(season, int):
                obj = {"ids": {"tmdb": int(tmdb_id)}, "season": int(season)}
                if watched_at and not blank(watched_at):
                    obj["watched_at"] = watched_at
                payload["seasons"].append(obj)

        elif t == "episode":
            season = it.get("season")
            ep = it.get("episode")
            if isinstance(season, int) and isinstance(ep, int):
                obj = {"ids": {"tmdb": int(tmdb_id)}, "season": int(season), "number": int(ep)}
                if watched_at and not blank(watched_at):
                    obj["watched_at"] = watched_at
                payload["episodes"].append(obj)

    return {k: v for k, v in payload.items() if v}


def build_ratings_payload(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"movies": [], "shows": [], "seasons": [], "episodes": []}
    for it in items:
        t = str(it.get("type") or "").lower().strip()
        tmdb_id = it.get("tmdb_id")
        rating = it.get("rating")
        rated_at = it.get("rated_at") or it.get("watched_at")

        if not isinstance(tmdb_id, int):
            continue
        if not isinstance(rating, int) or not (1 <= rating <= 10):
            continue

        base: Dict[str, Any] = {"ids": {"tmdb": int(tmdb_id)}, "rating": int(rating)}
        if rated_at and not blank(rated_at):
            base["rated_at"] = rated_at

        if t == "movie":
            payload["movies"].append(base)
        elif t == "show":
            payload["shows"].append(base)
        elif t == "season":
            season = it.get("season")
            if isinstance(season, int):
                payload["seasons"].append({**base, "season": int(season)})
        elif t == "episode":
            season = it.get("season")
            ep = it.get("episode")
            if isinstance(season, int) and isinstance(ep, int):
                payload["episodes"].append({**base, "season": int(season), "number": int(ep)})

    return {k: v for k, v in payload.items() if v}


def main() -> int:
    lp = log_path()
    with open(lp, "w", encoding="utf-8") as log_fh:
        log_line(log_fh, "START trakt_push_watch_queue")

        client_id = os.getenv("API_TRAKT_ID")
        client_secret = os.getenv("API_TRAKT_KEY")
        access_token = os.getenv("API_TRAKT_ACCESS_TOKEN")
        refresh_token = os.getenv("API_TRAKT_REFRESH_TOKEN")

        if blank(client_id) or blank(access_token):
            log_line(log_fh, "no-op (missing OAuth token/client id)")
            return 0

        q = load_json(QUEUE_PATH)
        items = q.get("items") if isinstance(q, dict) else None
        if not isinstance(items, list) or not items:
            log_line(log_fh, "no-op (queue missing or empty)")
            return 0

        valid: List[Dict[str, Any]] = []
        invalid: List[Dict[str, Any]] = []
        for it in items:
            if not isinstance(it, dict):
                invalid.append({"reason": "not_a_dict", "item": it})
                continue
            action = str(it.get("action") or "").lower().strip()
            typ = str(it.get("type") or "").lower().strip()
            tmdb_id = it.get("tmdb_id")
            ok = action in ("add", "remove", "rate") and typ in ("movie", "show", "season", "episode") and isinstance(tmdb_id, int)
            if typ in ("season", "episode") and not isinstance(it.get("season"), int):
                ok = False
            if typ == "episode" and not isinstance(it.get("episode"), int):
                ok = False
            if action == "rate" and not (isinstance(it.get("rating"), int) and 1 <= int(it.get("rating")) <= 10):
                ok = False
            if ok:
                valid.append(it)
            else:
                invalid.append({"reason": "failed_validation", "item": it})

        report: Dict[str, Any] = {
            "generated_utc": utc(),
            "script": "trakt_push_watch_queue.py",
            "log": str(lp),
            "counts": {"queued": len(items), "valid": len(valid), "invalid": len(invalid)},
            "results": {},
            "invalid": invalid,
        }

        def do_post(path: str, payload: Dict[str, Any], tok: str) -> Any:
            if not payload:
                return {"skipped": True, "reason": "empty_payload"}
            url = f"{TRAKT_API_BASE}{path}"
            try:
                return http_json(url, trakt_headers(client_id, tok), method="POST", body_obj=payload)
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace") if getattr(e, "fp", None) else ""
                return {"status": int(getattr(e, "code", 0) or 0), "body": body[:800]}
            except Exception as ex:
                return {"error": str(ex)[:300]}

        def post_with_refresh(path: str, payload: Dict[str, Any], tok: str) -> Any:
            resp = do_post(path, payload, tok)
            if isinstance(resp, dict) and resp.get("status") == 401 and not blank(client_secret) and not blank(refresh_token):
                log_line(log_fh, "401 on POST; attempting refresh once")
                try:
                    tok2 = refresh_tokens(client_id, client_secret, refresh_token)
                    new_access = tok2.get("access_token")
                    new_refresh = tok2.get("refresh_token")
                    if not blank(new_access) and not blank(new_refresh):
                        payload_tok = {"generated_utc": utc(), "access_token": new_access, "refresh_token": new_refresh}
                        (DATA_DIR / "trakt_tokens_latest.json").write_text(json.dumps(payload_tok, indent=2), encoding="utf-8")
                        (DATA_DIR / "trakt.json").write_text(json.dumps(payload_tok, indent=2), encoding="utf-8")
                        log_line(log_fh, "refreshed tokens written to data/trakt_tokens_latest.json and data/trakt.json")
                        return do_post(path, payload, new_access)
                except Exception as ex:
                    return {"status": 401, "refresh_error": str(ex)[:300], "original": resp}
            return resp

        adds = [it for it in valid if str(it.get("action")).lower() == "add"]
        removes = [it for it in valid if str(it.get("action")).lower() == "remove"]
        rates = [it for it in valid if str(it.get("action")).lower() == "rate"]

        report["results"]["add"] = post_with_refresh("/sync/history", build_bulk_payload(adds), access_token)
        report["results"]["remove"] = post_with_refresh("/sync/history/remove", build_bulk_payload(removes), access_token)
        report["results"]["rate"] = post_with_refresh("/sync/ratings", build_ratings_payload(rates), access_token)

        save_json(ACK_PATH, {"acked_utc": utc(), "original_queue": q, "report": report})
        save_json(REPORT_PATH, report)
        save_json(QUEUE_PATH, {"generated_utc": utc(), "items": []})

        log_line(log_fh, f"wrote report={REPORT_PATH}")
        log_line(log_fh, f"wrote ack={ACK_PATH}")
        log_line(log_fh, "cleared queue=data/watch_queue.json")
        log_line(log_fh, "DONE")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
