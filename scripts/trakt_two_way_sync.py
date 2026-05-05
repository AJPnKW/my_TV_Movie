#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from trakt_http import USER_AGENT, build_headers, header_names  # noqa: E402

DATA_DIR = REPO_ROOT / "data"
QUEUE_PATH = DATA_DIR / "watch_state_queue.json"
REPORT_PATH = DATA_DIR / "trakt_two_way_sync_report.json"
TOK_OUT = DATA_DIR / "trakt.json"
TRAKT_API_BASE = "https://api.trakt.tv"
TRAKT_TOKEN_URL = "https://trakt.tv/oauth/token"

ENDPOINTS = {
    "pull_watchlist": "GET /sync/watchlist",
    "pull_history_movies": "GET /sync/history/movies",
    "pull_history_episodes": "GET /sync/history/episodes",
    "push_watchlist_add": "POST /sync/watchlist",
    "push_watchlist_remove": "POST /sync/watchlist/remove",
    "push_history_add": "POST /sync/history",
    "push_history_remove": "POST /sync/history/remove",
}

VALID_SYNC_STATUS = {
    "local_only",
    "queued",
    "synced",
    "mismatch",
    "missing_id",
    "validation_issue",
    "auth_required",
    "failed",
}


def utc() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return fallback


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = str(value or "").strip()
    return int(text) if text.isdigit() else None


def normalize_ids(ids: Any) -> dict[str, int | str]:
    src = ids if isinstance(ids, dict) else {}
    out: dict[str, int | str] = {}
    for key in ("trakt", "tmdb", "tvdb"):
        parsed = as_int(src.get(key))
        if parsed is not None:
            out[key] = parsed
    imdb = str(src.get("imdb") or "").strip()
    if imdb:
        out["imdb"] = imdb
    return out


def queue_doc(items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "generated_utc": utc(),
        "schema": "watch_state_queue.v1",
        "items": items or [],
        "dry_run_payload": empty_payloads(),
    }


def load_queue(path: Path) -> dict[str, Any]:
    raw = load_json(path, queue_doc())
    if isinstance(raw, list):
        return queue_doc([item for item in raw if isinstance(item, dict)])
    if not isinstance(raw, dict):
        return queue_doc()
    items = raw.get("items")
    raw["items"] = items if isinstance(items, list) else []
    raw.setdefault("schema", "watch_state_queue.v1")
    raw.setdefault("generated_utc", utc())
    raw.setdefault("dry_run_payload", empty_payloads())
    return raw


def sample_queue() -> dict[str, Any]:
    return queue_doc([
        {
            "id": "watched_status:episode:121:1:1",
            "media_type": "episode",
            "state_type": "watched_status",
            "previous_value": "unwatched",
            "new_value": "watched",
            "ids": {"tmdb": 111},
            "show": {"season": 1, "episode": 1},
            "changed_at": "2026-05-05T00:00:00Z",
            "sync_status": "queued",
            "validation_status": "ok",
            "error": "",
        },
        {
            "id": "watch_list:movie:123",
            "media_type": "movie",
            "state_type": "watch_list",
            "previous_value": "off",
            "new_value": "on",
            "ids": {"tmdb": 123},
            "show": {"season": None, "episode": None},
            "changed_at": "2026-05-05T00:00:00Z",
            "sync_status": "queued",
            "validation_status": "ok",
            "error": "",
        },
    ])


def empty_payloads() -> dict[str, Any]:
    return {
        ENDPOINTS["pull_watchlist"]: {},
        ENDPOINTS["pull_history_movies"]: {},
        ENDPOINTS["pull_history_episodes"]: {},
        ENDPOINTS["push_watchlist_add"]: {},
        ENDPOINTS["push_watchlist_remove"]: {},
        ENDPOINTS["push_history_add"]: {},
        ENDPOINTS["push_history_remove"]: {},
    }


def validate_record(record: dict[str, Any]) -> tuple[bool, str]:
    media_type = str(record.get("media_type") or "").strip().lower()
    state_type = str(record.get("state_type") or "").strip().lower()
    new_value = str(record.get("new_value") or "").strip().lower()
    ids = normalize_ids(record.get("ids"))
    show = record.get("show") if isinstance(record.get("show"), dict) else {}
    if media_type not in {"movie", "show", "episode"}:
        return False, "validation_issue: media_type must be movie, show, or episode"
    if state_type not in {"watched_status", "watch_list", "favourite"}:
        return False, "validation_issue: unsupported state_type"
    if state_type == "watched_status" and new_value not in {"unwatched", "partial", "watched"}:
        return False, "validation_issue: watched_status must be unwatched, partial, or watched"
    if state_type in {"watch_list", "favourite"} and new_value not in {"off", "on"}:
        return False, "validation_issue: binary state must be off or on"
    if state_type == "favourite":
        return True, "local_only"
    if state_type == "watched_status" and new_value == "partial":
        return True, "local_only"
    if as_int(ids.get("tmdb")) is None:
        return False, "missing_id: tmdb id is required; title-only matching is forbidden"
    if media_type == "episode":
        if as_int(show.get("season")) is None or as_int(show.get("episode")) is None:
            return False, "validation_issue: episode queue records require show.season and show.episode"
    if str(record.get("release_status") or "").strip().lower() in {"unreleased", "not_yet_released"} and state_type == "watched_status" and new_value == "watched":
        return False, "validation_issue: unreleased movie/episode cannot become watched"
    return True, "queued"


def media_obj(record: dict[str, Any], watched_at: bool = False) -> dict[str, Any]:
    ids = normalize_ids(record.get("ids"))
    obj: dict[str, Any] = {"ids": {k: v for k, v in ids.items() if k in {"trakt", "tmdb", "imdb", "tvdb"}}}
    if watched_at:
        obj["watched_at"] = str(record.get("changed_at") or utc())
    return obj


def append_payload(payload: dict[str, Any], key: str, media_type: str, obj: dict[str, Any]) -> None:
    if media_type == "movie":
        payload[key].setdefault("movies", []).append(obj)
    elif media_type == "show":
        payload[key].setdefault("shows", []).append(obj)
    elif media_type == "episode":
        payload[key].setdefault("episodes", []).append(obj)


def build_payloads(records: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    payloads = empty_payloads()
    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            invalid.append({"record": record, "error": "validation_issue: record must be an object"})
            continue
        ok, status = validate_record(record)
        next_record = {**record, "validation_status": "ok" if ok else "validation_issue", "sync_status": status.split(":", 1)[0], "error": "" if ok else status}
        if not ok:
            invalid.append(next_record)
            continue
        if status == "local_only":
            valid.append({**next_record, "sync_status": "local_only"})
            continue
        media_type = str(record.get("media_type") or "").strip().lower()
        state_type = str(record.get("state_type") or "").strip().lower()
        new_value = str(record.get("new_value") or "").strip().lower()
        if state_type == "watch_list":
            endpoint = ENDPOINTS["push_watchlist_add"] if new_value == "on" else ENDPOINTS["push_watchlist_remove"]
            append_payload(payloads, endpoint, media_type, media_obj(record, watched_at=False))
            valid.append(next_record)
        elif state_type == "watched_status":
            endpoint = ENDPOINTS["push_history_add"] if new_value == "watched" else ENDPOINTS["push_history_remove"]
            append_payload(payloads, endpoint, media_type, media_obj(record, watched_at=(new_value == "watched")))
            valid.append(next_record)
    return payloads, valid, invalid


def load_tokens_file() -> dict[str, Any]:
    return load_json(TOK_OUT, {})


def token_bundle() -> dict[str, str]:
    tok = load_tokens_file()
    return {
        "client_id": str(os.getenv("API_TRAKT_ID") or tok.get("client_id") or "").strip(),
        "client_secret": str(os.getenv("API_TRAKT_SECRET") or os.getenv("API_TRAKT_KEY") or tok.get("client_secret") or "").strip(),
        "access_token": str(tok.get("access_token") or os.getenv("API_TRAKT_ACCESS_TOKEN") or "").strip(),
        "refresh_token": str(tok.get("refresh_token") or os.getenv("API_TRAKT_REFRESH_TOKEN") or "").strip(),
    }


def http_json(method: str, path: str, client_id: str, token: str, body: Any | None = None) -> Any:
    headers = build_headers(client_id, token, include_auth=True)
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(f"{TRAKT_API_BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw.strip() else {}


def pull_remote(client_id: str, token: str) -> dict[str, Any]:
    return {
        ENDPOINTS["pull_watchlist"]: http_json("GET", "/sync/watchlist", client_id, token),
        ENDPOINTS["pull_history_movies"]: http_json("GET", "/sync/history/movies", client_id, token),
        ENDPOINTS["pull_history_episodes"]: http_json("GET", "/sync/history/episodes", client_id, token),
    }


def post_payloads(payloads: dict[str, Any], client_id: str, token: str) -> dict[str, Any]:
    path_for_endpoint = {
        ENDPOINTS["push_watchlist_add"]: "/sync/watchlist",
        ENDPOINTS["push_watchlist_remove"]: "/sync/watchlist/remove",
        ENDPOINTS["push_history_add"]: "/sync/history",
        ENDPOINTS["push_history_remove"]: "/sync/history/remove",
    }
    results: dict[str, Any] = {}
    for endpoint, path in path_for_endpoint.items():
        payload = payloads.get(endpoint) or {}
        if not payload:
            results[endpoint] = {"skipped": True, "reason": "empty_payload"}
            continue
        results[endpoint] = http_json("POST", path, client_id, token, payload)
    return results


def run_sync(queue: dict[str, Any], dry_run: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    records = [item for item in queue.get("items", []) if isinstance(item, dict)]
    payloads, valid, invalid = build_payloads(records)
    tokens = token_bundle()
    auth_ready = not blank(tokens["client_id"]) and not blank(tokens["access_token"])
    report: dict[str, Any] = {
        "generated_utc": utc(),
        "script": "trakt_two_way_sync.py",
        "base": TRAKT_API_BASE,
        "endpoints": ENDPOINTS,
        "dry_run": dry_run,
        "auth_ready": auth_ready,
        "header_names": header_names(build_headers(tokens["client_id"] or "CLIENT_ID", tokens["access_token"] or "TOKEN", include_auth=True)),
        "counts": {"queued": len(records), "valid": len(valid), "invalid": len(invalid)},
        "payloads": payloads,
        "valid": valid,
        "invalid": invalid,
        "remote_before": {},
        "push_results": {},
        "remote_after": {},
        "blocker": "" if auth_ready else "auth_required: API_TRAKT_ID and OAuth access token are required for live Trakt push/pull",
    }
    if dry_run or not auth_ready:
        next_queue = {**queue, "generated_utc": utc(), "dry_run_payload": payloads}
        return report, next_queue
    try:
        report["remote_before"] = pull_remote(tokens["client_id"], tokens["access_token"])
        report["push_results"] = post_payloads(payloads, tokens["client_id"], tokens["access_token"])
        report["remote_after"] = pull_remote(tokens["client_id"], tokens["access_token"])
        sent_ids = {str(record.get("id") or "") for record in valid if record.get("sync_status") == "queued"}
        next_items = []
        for record in records:
            if str(record.get("id") or "") in sent_ids:
                next_items.append({**record, "sync_status": "synced", "validation_status": "ok", "error": ""})
            else:
                next_items.append(record)
        next_queue = {**queue, "generated_utc": utc(), "items": next_items, "dry_run_payload": payloads}
        return report, next_queue
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if getattr(exc, "fp", None) else ""
        report["blocker"] = f"failed: Trakt HTTP {exc.code} {body[:300]}"
    except Exception as exc:
        report["blocker"] = f"failed: {str(exc)[:300]}"
    next_queue = {**queue, "generated_utc": utc(), "dry_run_payload": payloads}
    return report, next_queue


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Build payloads and report without network writes.")
    parser.add_argument("--sample", action="store_true", help="Use an in-memory sample queue for validation.")
    parser.add_argument("--queue", default=str(QUEUE_PATH))
    parser.add_argument("--report", default=str(REPORT_PATH))
    parser.add_argument("--no-write", action="store_true", help="Do not write queue/report files.")
    args = parser.parse_args()

    queue = sample_queue() if args.sample else load_queue(Path(args.queue))
    report, next_queue = run_sync(queue, dry_run=args.dry_run)
    if not args.no_write:
        save_json(Path(args.queue), next_queue)
        save_json(Path(args.report), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
