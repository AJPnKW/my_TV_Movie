"""
FILE: tools/inputs_editor/inputs_editor_server.py
VERSION: 1.0.5
UPDATED: 2026-06-27T00:00:00Z
CHANGE NOTES:
- Restore live inputs editor server path used by web/inputs_editor.html.
- Serve the inputs editor UI and supporting /web assets from port 8787.
- Preserve frontend save/config/TMDB API contract for local testing.
- Block online publish from unresolved Git conflicts and report the exact recovery reason.
"""
from __future__ import annotations

import argparse
import copy
import json
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.error import HTTPError, URLError
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
INPUTS_JSON = DATA_DIR / "inputs.json"
CATALOG_INDEX_JSON = DATA_DIR / "catalog_index.json"
WATCH_STATE_QUEUE_JSON = DATA_DIR / "watch_state_queue.json"
WEB_DIR = REPO_ROOT / "web"
UI_FILE = WEB_DIR / "inputs_editor.html"
CONFIG_JSON = WEB_DIR / "config.json"
BACKUP_DIR = DATA_DIR / "backups"
MAX_JSON_BODY_BYTES = 5 * 1024 * 1024
PUBLISH_DEFAULT_WAIT_SECONDS = 15 * 60
PUBLISH_POLL_SECONDS = 15
GENERATED_SYNC_PATHS = [
    "data/data.json",
    "data/catalog_index.json",
    "data/calendar.json",
    "data/catalog_detail",
    "data/watch_state_queue.json",
    "assets",
]

TMDB_KEY_ENV = "API_TMDB_KEY"
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/"
SEASON_TOKEN_RE = re.compile(r"^S?\d+(?:\s*-\s*S?\d+)?$", re.IGNORECASE)
SEASON_MIN_RE = re.compile(r"^S?\d+\+$", re.IGNORECASE)
TITLE_STOPWORDS = {"a", "an", "and", "in", "of", "part", "the", "to", "with"}


def _now_utc_iso() -> str:
    import datetime as dt

    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _json(handler: BaseHTTPRequestHandler, code: int, obj: dict):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(data)


def _text(
    handler: BaseHTTPRequestHandler,
    code: int,
    text: str,
    ctype: str = "text/plain; charset=utf-8",
):
    data = text.encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(data)


def _read_request_json(handler: BaseHTTPRequestHandler) -> dict:
    raw_length = str(handler.headers.get("Content-Length") or "0").strip()
    try:
        content_length = int(raw_length)
    except ValueError as exc:
        raise ValueError("Invalid Content-Length") from exc
    if content_length < 0 or content_length > MAX_JSON_BODY_BYTES:
        raise ValueError(f"JSON payload is too large; limit is {MAX_JSON_BODY_BYTES} bytes")
    body = handler.rfile.read(content_length).decode("utf-8", errors="replace")
    try:
        obj = json.loads(body) if body.strip() else {}
    except Exception as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError("JSON payload must be an object")
    return obj


def _read_inputs() -> dict:
    if not INPUTS_JSON.exists():
        return {
            "tv": [],
            "movies": [],
            "watchlist": [],
            "generated_local": "",
            "generated_utc": "",
        }
    return json.loads(INPUTS_JSON.read_text(encoding="utf-8"))


def _atomic_write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(obj, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        tmp.replace(path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass


def _read_watch_state_queue() -> dict:
    if not WATCH_STATE_QUEUE_JSON.exists():
        return {
            "generated_utc": "",
            "schema": "watch_state_queue.v1",
            "items": [],
            "dry_run_payload": {},
        }
    try:
        obj = json.loads(WATCH_STATE_QUEUE_JSON.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        obj = {}
    if not isinstance(obj, dict):
        obj = {}
    obj.setdefault("schema", "watch_state_queue.v1")
    obj.setdefault("generated_utc", "")
    if not isinstance(obj.get("items"), list):
        obj["items"] = []
    if not isinstance(obj.get("dry_run_payload"), dict):
        obj["dry_run_payload"] = {}
    return obj


def _validate_queue_record(record: dict) -> dict:
    if not isinstance(record, dict):
        raise ValueError("queue record must be an object")
    normalized = copy.deepcopy(record)
    record_id = str(normalized.get("id") or "").strip()
    media_type = str(normalized.get("media_type") or "").strip().lower()
    state_type = str(normalized.get("state_type") or "").strip().lower()
    ids = normalized.get("ids") if isinstance(normalized.get("ids"), dict) else {}
    if not record_id:
        raise ValueError("queue record requires id")
    if media_type not in {"movie", "show", "episode"}:
        raise ValueError("queue record media_type must be movie, show, or episode")
    if state_type not in {"watched_status", "watch_list", "favourite"}:
        raise ValueError("queue record state_type is invalid")
    if not any(str(ids.get(key) or "").strip() for key in ("tmdb", "trakt", "imdb", "tvdb")):
        normalized["validation_status"] = "validation_issue"
        normalized["sync_status"] = "validation_issue"
        normalized["error"] = "missing IDs; title-only matching is forbidden"
    else:
        normalized.setdefault("validation_status", "ok")
        normalized.setdefault("sync_status", "queued")
        normalized.setdefault("error", "")
    normalized["id"] = record_id
    normalized["media_type"] = media_type
    normalized["state_type"] = state_type
    normalized["ids"] = ids
    normalized["show"] = normalized.get("show") if isinstance(normalized.get("show"), dict) else {"season": None, "episode": None}
    normalized.setdefault("changed_at", _now_utc_iso())
    return normalized


def _upsert_watch_state_queue_record(record: dict) -> dict:
    queue = _read_watch_state_queue()
    normalized = _validate_queue_record(record)
    items = [item for item in queue["items"] if str(item.get("id") or "") != normalized["id"]]
    items.append(normalized)
    queue["items"] = items
    queue["generated_utc"] = _now_utc_iso()
    _atomic_write(WATCH_STATE_QUEUE_JSON, queue)
    return queue


def _run_trakt_sync(dry_run: bool = True) -> dict:
    command = [sys.executable, str(REPO_ROOT / "scripts" / "trakt_two_way_sync.py")]
    if dry_run:
        command.append("--dry-run")
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    try:
        report = json.loads(completed.stdout)
    except Exception:
        report = {}
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "report": report,
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-8000:],
    }


def _backup_inputs() -> str | None:
    if not INPUTS_JSON.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"inputs_{_now_utc_iso().replace(':', '').replace('-', '')}.json"
    backup_path.write_text(INPUTS_JSON.read_text(encoding="utf-8"), encoding="utf-8")
    return str(backup_path)


def _coerce_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"false", "0", "no", "off", "out", "inactive"}:
            return False
        if text in {"true", "1", "yes", "on", "in", "active"}:
            return True
    return default


def _normalize_tags(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = value.split(",")
    elif isinstance(value, list):
        raw_items = value
    else:
        raise ValueError("tags must be a list or comma-separated string")
    tags: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        tag = str(item or "").strip()
        key = tag.casefold()
        if tag and key not in seen:
            seen.add(key)
            tags.append(tag)
    return tags


def _title_tokens(value: object) -> set[str]:
    text = str(value or "").casefold()
    return {
        token
        for token in re.findall(r"[^\W_]+", text, flags=re.UNICODE)
        if token not in TITLE_STOPWORDS and not token.isdigit()
    }


def _titles_match(local_title: str, remote_title: str) -> bool:
    local = str(local_title or "").strip().casefold()
    remote = str(remote_title or "").strip().casefold()
    if not local or not remote:
        return False
    if local == remote:
        return True
    return bool(_title_tokens(local) & _title_tokens(remote))


def _normalize_season_spec(value: object) -> str:
    spec = str(value or "*").strip()
    if not spec or spec == "*":
        return "*"
    compact = re.sub(r"\s+", "", spec)
    if SEASON_MIN_RE.match(compact):
        season_num = int(compact.rstrip("+").lstrip("Ss"))
        if season_num <= 0:
            raise ValueError("season_spec minimum must be greater than zero")
        return f"{season_num}+"

    seasons: set[int] = set()
    for token in compact.split(","):
        if not token:
            continue
        if not SEASON_TOKEN_RE.match(token):
            raise ValueError(f"invalid season_spec token '{token}'")
        token = re.sub(r"[Ss]", "", token)
        if "-" in token:
            start_raw, end_raw = token.split("-", 1)
            start, end = int(start_raw), int(end_raw)
            if start <= 0 or end <= 0:
                raise ValueError("season_spec seasons must be greater than zero")
            if start > end:
                start, end = end, start
            seasons.update(range(start, end + 1))
        else:
            season_num = int(token)
            if season_num <= 0:
                raise ValueError("season_spec seasons must be greater than zero")
            seasons.add(season_num)
    if not seasons:
        return "*"
    ordered = sorted(seasons)
    ranges: list[str] = []
    start = prev = ordered[0]
    for current in ordered[1:] + [None]:
        if current == prev + 1:
            prev = current
            continue
        ranges.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = current
    return ",".join(ranges)


def _normalize_media_entry(entry: dict, media_type: str) -> dict:
    if not isinstance(entry, dict):
        raise ValueError(f"{media_type} entries must be objects")
    normalized = copy.deepcopy(entry)
    normalized["title"] = str(normalized.get("title", "")).strip()
    if not normalized["title"]:
        raise ValueError(f"{media_type} entries require a title")
    tmdb_id = normalized.get("tmdb_id")
    if not isinstance(tmdb_id, int):
        if isinstance(tmdb_id, str) and tmdb_id.strip().isdigit():
            tmdb_id = int(tmdb_id.strip())
        else:
            raise ValueError(f"{media_type} '{normalized['title']}' requires an integer tmdb_id")
    normalized["tmdb_id"] = tmdb_id
    if normalized["tmdb_id"] <= 0:
        raise ValueError(f"{media_type} '{normalized['title']}' requires a positive tmdb_id")
    normalized["in_scope"] = _coerce_bool(normalized.get("in_scope"), True)
    if media_type == "tv":
        try:
            normalized["season_spec"] = _normalize_season_spec(normalized.get("season_spec", "*"))
        except ValueError as exc:
            raise ValueError(f"tv '{normalized['title']}' {exc}") from exc
        normalized["include_future"] = _coerce_bool(normalized.get("include_future"), True)
    normalized["tags"] = _normalize_tags(normalized.get("tags"))
    normalized["notes"] = str(normalized.get("notes", "") or "").strip()
    return normalized


def _dedupe_entries(entries: list[dict], media_type: str, warnings: list[str]) -> list[dict]:
    by_id: dict[int, dict] = {}
    order: list[int] = []
    for raw in entries:
        entry = _normalize_media_entry(raw, media_type)
        tmdb_id = int(entry["tmdb_id"])
        if tmdb_id not in by_id:
            by_id[tmdb_id] = entry
            order.append(tmdb_id)
            continue

        existing = by_id[tmdb_id]
        warnings.append(f"merged duplicate {media_type} tmdb_id={tmdb_id}")
        existing["in_scope"] = bool(existing.get("in_scope")) or bool(entry.get("in_scope"))
        if not existing.get("title") and entry.get("title"):
            existing["title"] = entry["title"]
        if media_type == "tv":
            if existing.get("season_spec") in {"", "*"} or entry.get("season_spec") == "*":
                existing["season_spec"] = "*"
            elif existing.get("season_spec") != entry.get("season_spec"):
                warnings.append(f"kept first season_spec for duplicate tv tmdb_id={tmdb_id}")
            existing["include_future"] = bool(existing.get("include_future")) or bool(entry.get("include_future"))
        merged_tags = _normalize_tags([*(existing.get("tags") or []), *(entry.get("tags") or [])])
        existing["tags"] = merged_tags
        if not existing.get("notes") and entry.get("notes"):
            existing["notes"] = entry["notes"]
    return [by_id[tmdb_id] for tmdb_id in order]


def _catalog_identity_map() -> dict[str, dict[int, str]]:
    identities: dict[str, dict[int, str]] = {"tv": {}, "movie": {}}
    if not CATALOG_INDEX_JSON.exists():
        return identities
    try:
        catalog = json.loads(CATALOG_INDEX_JSON.read_text(encoding="utf-8"))
    except Exception:
        return identities
    for media_type, key in (("tv", "shows"), ("movie", "movies")):
        rows = catalog.get(key) if isinstance(catalog, dict) else []
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                tmdb_id = int(row.get("tmdb_id") or row.get("id") or 0)
            except Exception:
                tmdb_id = 0
            title = str(row.get("title") or row.get("name") or "").strip()
            if tmdb_id > 0 and title:
                identities[media_type][tmdb_id] = title
    return identities


def _tmdb_entry_title(media_type: str, tmdb_id: int, cache: dict[tuple[str, int], str]) -> str:
    key = (media_type, int(tmdb_id))
    if key in cache:
        return cache[key]
    path = f"/tv/{int(tmdb_id)}" if media_type == "tv" else f"/movie/{int(tmdb_id)}"
    result = _tmdb_request_json(path)
    if not result.get("ok"):
        raise ValueError(f"{media_type} tmdb_id={tmdb_id} could not be verified: {result.get('error') or 'TMDB lookup failed'}")
    data = result.get("data") or {}
    remote_id = int(data.get("id") or 0)
    raw_title = data.get("name") if media_type == "tv" else data.get("title")
    remote_title = str(raw_title or "").strip()
    if remote_id != int(tmdb_id) or not remote_title:
        raise ValueError(f"{media_type} tmdb_id={tmdb_id} returned incomplete TMDB identity data")
    cache[key] = remote_title
    return remote_title


def _validate_tmdb_entry_identity(
    entry: dict,
    media_type: str,
    catalog_identities: dict[str, dict[int, str]],
    tmdb_cache: dict[tuple[str, int], str],
) -> None:
    if entry.get("in_scope") is False:
        return
    title = str(entry.get("title") or "").strip()
    tmdb_id = int(entry.get("tmdb_id") or 0)
    catalog_title = catalog_identities.get(media_type, {}).get(tmdb_id)
    if catalog_title:
        if _titles_match(title, catalog_title):
            return
        raise ValueError(
            f"{media_type} '{title}' tmdb_id={tmdb_id} resolves to '{catalog_title}' in the generated catalog; "
            "choose the correct TMDB search result before saving"
        )

    remote_title = _tmdb_entry_title(media_type, tmdb_id, tmdb_cache)
    if not _titles_match(title, remote_title):
        raise ValueError(
            f"{media_type} '{title}' tmdb_id={tmdb_id} resolves to '{remote_title}' in TMDB; "
            "choose the correct TMDB search result before saving"
        )


def _validate_tmdb_identities(validated: dict) -> None:
    catalog_identities = _catalog_identity_map()
    tmdb_cache: dict[tuple[str, int], str] = {}
    for entry in validated.get("tv") or []:
        _validate_tmdb_entry_identity(entry, "tv", catalog_identities, tmdb_cache)
    for entry in validated.get("movies") or []:
        _validate_tmdb_entry_identity(entry, "movie", catalog_identities, tmdb_cache)


def _validate_inputs_payload(obj: dict) -> tuple[dict, list[str]]:
    if not isinstance(obj, dict):
        raise ValueError("inputs payload must be an object")
    tv = obj.get("tv", [])
    movies = obj.get("movies", [])
    watchlist = obj.get("watchlist", [])
    if not isinstance(tv, list) or not isinstance(movies, list) or not isinstance(watchlist, list):
        raise ValueError("inputs must contain lists: tv, movies, watchlist")
    warnings: list[str] = []
    validated = copy.deepcopy(obj)
    validated["tv"] = _dedupe_entries(tv, "tv", warnings)
    validated["movies"] = _dedupe_entries(movies, "movie", warnings)
    _validate_tmdb_identities(validated)
    validated["watchlist"] = watchlist
    return validated, warnings


def _run_editor_refresh() -> dict:
    command = [sys.executable, str(REPO_ROOT / "scripts" / "run_pipeline_tmdb_trakt.py")]
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=1800,
        check=False,
    )
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-8000:],
    }


def _run_git_command(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


def _git_text(args: list[str]) -> str:
    result = _run_git_command(args)
    if result.returncode != 0:
        return ""
    return (result.stdout or "").strip()


def _git_failure(result: subprocess.CompletedProcess, fallback: str) -> str:
    return (result.stderr or result.stdout or fallback).strip()


def _git_unmerged_paths() -> list[str]:
    result = _run_git_command(["diff", "--name-only", "--diff-filter=U"])
    if result.returncode != 0:
        return []
    return [line.strip().replace("\\", "/") for line in (result.stdout or "").splitlines() if line.strip()]


def _ensure_publishable_git_state() -> dict:
    unmerged = _git_unmerged_paths()
    if unmerged:
        return {
            "ok": False,
            "error": (
                "Online update is blocked because this checkout has unresolved Git conflicts. "
                "Resolve the conflicted files, then run Save Online and Finish Update again."
            ),
            "unmerged_paths": unmerged,
        }
    return {"ok": True}


def _run_pipeline_integrity_validation() -> dict:
    completed = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "qa_pipeline_integrity.py")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def _generated_artifact_changes_since(base_ref: str, head_ref: str) -> list[str]:
    if not base_ref or not head_ref:
        return []
    diff = _run_git_command(["diff", "--name-only", f"{base_ref}..{head_ref}", "--", *GENERATED_SYNC_PATHS])
    if diff.returncode != 0:
        return []
    return [line.strip().replace("\\", "/") for line in (diff.stdout or "").splitlines() if line.strip()]


def _has_runtime_artifact_update(paths: list[str]) -> bool:
    required_exact = {
        "data/data.json",
        "data/catalog_index.json",
        "data/calendar.json",
    }
    for path in paths:
        if path in required_exact or path.startswith("data/catalog_detail/"):
            return True
    return False


def _stash_generated_artifacts_if_needed() -> dict:
    status = _run_git_command(["status", "--porcelain", "--", *GENERATED_SYNC_PATHS])
    if status.returncode != 0:
        return {"ok": False, "error": _git_failure(status, "git status failed")}
    if not (status.stdout or "").strip():
        return {"ok": True, "stashed": False}
    stash_message = f"inputs-editor generated artifacts before publish sync {_now_utc_iso()}"
    stash = _run_git_command(["stash", "push", "-u", "-m", stash_message, "--", *GENERATED_SYNC_PATHS])
    if stash.returncode != 0:
        return {"ok": False, "error": _git_failure(stash, "git stash failed")}
    return {"ok": True, "stashed": True, "message": stash_message}


def _generated_artifacts_are_dirty() -> bool:
    status = _run_git_command(["status", "--porcelain", "--", *GENERATED_SYNC_PATHS])
    return status.returncode == 0 and bool((status.stdout or "").strip())


def _fast_forward_remote(remote_name: str, branch_name: str) -> dict:
    remote_ref = f"{remote_name}/{branch_name}"
    stash = _stash_generated_artifacts_if_needed()
    if not stash.get("ok"):
        return stash
    merge = _run_git_command(["merge", "--ff-only", remote_ref])
    if merge.returncode != 0:
        return {
            "ok": False,
            "stashed": stash.get("stashed", False),
            "error": _git_failure(merge, f"git merge --ff-only {remote_ref} failed"),
        }
    return {
        "ok": True,
        "stashed": stash.get("stashed", False),
        "stash_message": stash.get("message", ""),
        "stdout": merge.stdout[-2000:],
    }


def _wait_for_generated_artifacts(remote_name: str, branch_name: str, input_commit: str, wait_seconds: int) -> dict:
    remote_ref = f"{remote_name}/{branch_name}"
    deadline = time.monotonic() + max(0, int(wait_seconds))
    attempts = 0
    last_remote_head = ""
    first_validation = _run_pipeline_integrity_validation()
    if first_validation.get("ok") and not _generated_artifacts_are_dirty():
        return {
            "ok": True,
            "synced": False,
            "validated": True,
            "reason": "local runtime artifacts already reconcile with inputs",
            "validation": first_validation,
        }
    if first_validation.get("ok") and _generated_artifacts_are_dirty():
        stash = _stash_generated_artifacts_if_needed()
        if not stash.get("ok"):
            return stash
        clean_validation = _run_pipeline_integrity_validation()
        if clean_validation.get("ok"):
            return {
                "ok": True,
                "synced": False,
                "validated": True,
                "stashed_generated_artifacts": stash.get("stashed", False),
                "stash_message": stash.get("message", ""),
                "reason": "stashed redundant local generated artifacts; committed runtime already reconciles with inputs",
                "validation": clean_validation,
            }

    while True:
        attempts += 1
        fetch = _run_git_command(["fetch", remote_name, branch_name])
        if fetch.returncode != 0:
            return {"ok": False, "error": _git_failure(fetch, "git fetch failed"), "attempts": attempts}

        remote_head = _git_text(["rev-parse", "--verify", remote_ref])
        last_remote_head = remote_head or last_remote_head
        if remote_head and remote_head != input_commit:
            ancestor = _run_git_command(["merge-base", "--is-ancestor", input_commit, remote_ref])
            if ancestor.returncode == 0:
                generated_changes = _generated_artifact_changes_since(input_commit, remote_head)
                if not _has_runtime_artifact_update(generated_changes):
                    if time.monotonic() >= deadline:
                        return {
                            "ok": False,
                            "synced": False,
                            "validated": False,
                            "attempts": attempts,
                            "remote_head": remote_head,
                            "error": "Remote branch advanced after the input commit, but no generated runtime artifact update was found.",
                            "generated_changes": generated_changes,
                            "validation": first_validation,
                        }
                    time.sleep(PUBLISH_POLL_SECONDS)
                    continue
                ff = _fast_forward_remote(remote_name, branch_name)
                if not ff.get("ok"):
                    ff["attempts"] = attempts
                    return ff
                validation = _run_pipeline_integrity_validation()
                if not validation.get("ok"):
                    return {
                        "ok": False,
                        "synced": True,
                        "attempts": attempts,
                        "remote_head": remote_head,
                        "error": "Generated artifact commit arrived, but local integrity validation failed.",
                        "validation": validation,
                    }
                return {
                    "ok": True,
                    "synced": True,
                    "validated": True,
                    "attempts": attempts,
                    "remote_head": remote_head,
                    "generated_changes": generated_changes,
                    "stashed_generated_artifacts": ff.get("stashed", False),
                    "stash_message": ff.get("stash_message", ""),
                    "validation": validation,
                }

        if time.monotonic() >= deadline:
            return {
                "ok": False,
                "synced": False,
                "validated": False,
                "attempts": attempts,
                "remote_head": last_remote_head,
                "error": "Timed out waiting for GitHub build-data to publish generated runtime artifacts.",
                "validation": first_validation,
            }
        time.sleep(PUBLISH_POLL_SECONDS)


def _push_inputs_to_remote(remote: str, branch: str) -> dict:
    git_state = _ensure_publishable_git_state()
    if not git_state.get("ok"):
        return git_state

    remote_name = (remote or "github").strip() or "github"
    branch_name = (branch or "main").strip() or "main"
    relative_inputs = str(INPUTS_JSON.relative_to(REPO_ROOT))

    add_result = _run_git_command(["add", "--", relative_inputs])
    if add_result.returncode != 0:
        return {"ok": False, "error": add_result.stderr.strip() or add_result.stdout.strip() or "git add failed"}

    diff_result = _run_git_command(["diff", "--cached", "--quiet", "--", relative_inputs])
    commit_id = ""
    committed = False
    if diff_result.returncode != 0:
        commit_message = f"Update inputs.json via inputs editor {_now_utc_iso()}"
        commit_result = _run_git_command(["commit", "-m", commit_message, "--", relative_inputs])
        if commit_result.returncode != 0:
            return {"ok": False, "error": commit_result.stderr.strip() or commit_result.stdout.strip() or "git commit failed"}
        committed = True
        head_result = _run_git_command(["rev-parse", "--short", "HEAD"])
        commit_id = (head_result.stdout or "").strip()

    fetch_result = _run_git_command(["fetch", remote_name, branch_name])
    if fetch_result.returncode != 0:
        return {"ok": False, "error": fetch_result.stderr.strip() or fetch_result.stdout.strip() or "git fetch failed"}

    rebase_result = _run_git_command(["rebase", "--autostash", f"{remote_name}/{branch_name}"])
    if rebase_result.returncode != 0:
        _run_git_command(["rebase", "--abort"])
        return {"ok": False, "error": rebase_result.stderr.strip() or rebase_result.stdout.strip() or "git rebase failed"}
    head_result = _run_git_command(["rev-parse", "--short", "HEAD"])
    commit_id = (head_result.stdout or "").strip()

    push_result = _run_git_command(["push", remote_name, branch_name])
    if push_result.returncode != 0:
        return {"ok": False, "error": push_result.stderr.strip() or push_result.stdout.strip() or "git push failed"}
    return {
        "ok": True,
        "pushed": committed,
        "rebased": True,
        "remote": remote_name,
        "branch": branch_name,
        "commit": commit_id,
    }


def _publish_inputs_to_remote(remote: str, branch: str, wait_seconds: int = PUBLISH_DEFAULT_WAIT_SECONDS) -> dict:
    push = _push_inputs_to_remote(remote, branch)
    if not push.get("ok"):
        return push
    remote_name = str(push.get("remote") or remote or "github")
    branch_name = str(push.get("branch") or branch or "main")
    input_commit = _git_text(["rev-parse", "--verify", "HEAD"])
    sync = _wait_for_generated_artifacts(remote_name, branch_name, input_commit, wait_seconds)
    return {
        **push,
        "publish_complete": bool(sync.get("ok")),
        "sync": sync,
        "ok": bool(sync.get("ok")),
    }


def _tmdb_search(query: str) -> dict:
    key = os.environ.get(TMDB_KEY_ENV, "").strip()
    if not key:
        return {"ok": False, "error": f"Missing env var {TMDB_KEY_ENV} (TMDB search disabled)"}

    qs = {
        "api_key": key,
        "query": query,
        "include_adult": "false",
        "language": "en-US",
        "region": "CA",
    }
    query_string = "&".join(
        [f"{name}={quote(str(value))}" for name, value in qs.items() if value is not None]
    )
    url = f"{TMDB_BASE}/search/multi?{query_string}"

    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=25) as response:
        raw = response.read().decode("utf-8", errors="replace")
    data = json.loads(raw)

    results = []
    for result in data.get("results", []):
        media_type = result.get("media_type")
        if media_type not in ("tv", "movie"):
            continue
        title = result.get("name") if media_type == "tv" else result.get("title")
        year = (result.get("first_air_date") or result.get("release_date") or "")[:4]
        results.append(
            {
                "type": media_type,
                "tmdb_id": result.get("id"),
                "title": title or "",
                "year": year,
                "poster_path": result.get("poster_path") or "",
            }
        )
    return {"ok": True, "results": results, "img_base": TMDB_IMG_BASE}


def _tmdb_request_json(path: str, qs: dict[str, object] | None = None) -> dict:
    key = os.environ.get(TMDB_KEY_ENV, "").strip()
    if not key:
        return {"ok": False, "error": f"Missing env var {TMDB_KEY_ENV} (TMDB disabled)"}

    query_items = {"api_key": key, "language": "en-US"}
    if qs:
        query_items.update(qs)
    query_string = "&".join(
        [f"{name}={quote(str(value))}" for name, value in query_items.items() if value is not None]
    )
    url = f"{TMDB_BASE}{path}?{query_string}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read().decode("utf-8", errors="replace")
        return {"ok": True, "data": json.loads(raw)}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "error": f"TMDB HTTP {exc.code}: {body[:400]}"}
    except URLError as exc:
        return {"ok": False, "error": f"TMDB request failed: {exc.reason}"}
    except Exception as exc:
        return {"ok": False, "error": f"TMDB request failed: {exc}"}


def _tmdb_tv_details(tmdb_id: int) -> dict:
    result = _tmdb_request_json(f"/tv/{int(tmdb_id)}")
    if not result.get("ok"):
        return result
    data = result.get("data") or {}
    seasons = [
        {
            "season_number": season.get("season_number"),
            "name": season.get("name") or "",
            "episode_count": season.get("episode_count") or 0,
            "air_date": season.get("air_date") or "",
        }
        for season in data.get("seasons", [])
        if isinstance(season.get("season_number"), int) and int(season.get("season_number")) > 0
    ]
    return {
        "ok": True,
        "show": {
            "tmdb_id": int(data.get("id") or tmdb_id),
            "title": data.get("name") or "",
            "total_seasons": len(seasons),
            "seasons": seasons,
        },
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stdout.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/web/inputs_editor.html"):
            if not UI_FILE.exists():
                _text(self, 404, "Missing: web/inputs_editor.html")
                return
            _text(self, 200, UI_FILE.read_text(encoding="utf-8", errors="replace"), "text/html; charset=utf-8")
            return

        if path == "/api/health":
            _json(self, 200, {"ok": True, "utc": _now_utc_iso(), "repo_root": str(REPO_ROOT)})
            return

        if path == "/api/inputs":
            _json(self, 200, {"ok": True, "inputs": _read_inputs()})
            return

        if path == "/api/watch-state-queue":
            _json(self, 200, {"ok": True, "queue": _read_watch_state_queue()})
            return

        if path == "/api/config":
            if not CONFIG_JSON.exists():
                _json(self, 200, {"ok": True, "config": {}})
                return
            try:
                config = json.loads(CONFIG_JSON.read_text(encoding="utf-8"))
            except Exception:
                config = {}
            _json(self, 200, {"ok": True, "config": config})
            return

        if path == "/api/tmdb/search":
            query = (parse_qs(parsed.query).get("q") or [""])[0].strip()
            if not query:
                _json(self, 400, {"ok": False, "error": "Missing q"})
                return
            result = _tmdb_search(query)
            _json(self, 200 if result.get("ok") else 400, result)
            return

        if path == "/api/tmdb/tv":
            raw_id = (parse_qs(parsed.query).get("id") or [""])[0].strip()
            if not raw_id.isdigit():
                _json(self, 400, {"ok": False, "error": "Missing numeric id"})
                return
            result = _tmdb_tv_details(int(raw_id))
            _json(self, 200 if result.get("ok") else 400, result)
            return

        if path == "/api/refresh-runtime":
            result = _run_editor_refresh()
            _json(self, 200 if result["ok"] else 500, result)
            return

        if path.startswith("/web/"):
            file_path = (REPO_ROOT / path.lstrip("/")).resolve()
            web_root = WEB_DIR.resolve()
            if web_root != file_path and web_root not in file_path.parents:
                _text(self, 403, "Forbidden")
                return
            if not file_path.exists() or not file_path.is_file():
                _text(self, 404, "Not found")
                return
            suffix = file_path.suffix.lower()
            if suffix in {".html", ".htm"}:
                _text(self, 200, file_path.read_text(encoding="utf-8", errors="replace"), "text/html; charset=utf-8")
                return
            if suffix == ".css":
                _text(self, 200, file_path.read_text(encoding="utf-8", errors="replace"), "text/css; charset=utf-8")
                return
            if suffix == ".js":
                _text(
                    self,
                    200,
                    file_path.read_text(encoding="utf-8", errors="replace"),
                    "application/javascript; charset=utf-8",
                )
                return
            if suffix == ".json":
                _text(self, 200, file_path.read_text(encoding="utf-8", errors="replace"), "application/json; charset=utf-8")
                return
            data = file_path.read_bytes()
            content_type, _ = mimetypes.guess_type(str(file_path))
            if not content_type:
                content_type = "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return

        _text(self, 404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/config":
            try:
                obj = _read_request_json(self)
            except ValueError as exc:
                _json(self, 400, {"ok": False, "error": str(exc)})
                return
            try:
                CONFIG_JSON.write_text(json.dumps(obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
            except Exception as exc:
                _json(self, 500, {"ok": False, "error": str(exc)})
                return
            _json(self, 200, {"ok": True})
            return

        if parsed.path == "/api/refresh-runtime":
            result = _run_editor_refresh()
            _json(self, 200 if result["ok"] else 500, result)
            return

        if parsed.path == "/api/push-inputs":
            try:
                obj = _read_request_json(self)
            except ValueError as exc:
                _json(self, 400, {"ok": False, "error": str(exc)})
                return
            result = _push_inputs_to_remote(
                str(obj.get("remote") or "github"),
                str(obj.get("branch") or "main"),
            )
            _json(self, 200 if result.get("ok") else 500, result)
            return

        if parsed.path == "/api/publish-inputs":
            try:
                obj = _read_request_json(self)
            except ValueError as exc:
                _json(self, 400, {"ok": False, "error": str(exc)})
                return
            try:
                wait_seconds = int(obj.get("wait_seconds") or PUBLISH_DEFAULT_WAIT_SECONDS)
            except Exception:
                wait_seconds = PUBLISH_DEFAULT_WAIT_SECONDS
            result = _publish_inputs_to_remote(
                str(obj.get("remote") or "github"),
                str(obj.get("branch") or "main"),
                wait_seconds=wait_seconds,
            )
            _json(self, 200 if result.get("ok") else 500, result)
            return

        if parsed.path == "/api/watch-state-queue":
            try:
                obj = _read_request_json(self)
            except ValueError as exc:
                _json(self, 400, {"ok": False, "error": str(exc)})
                return
            try:
                if isinstance(obj, dict) and isinstance(obj.get("record"), dict):
                    queue = _upsert_watch_state_queue_record(obj["record"])
                elif isinstance(obj, dict) and isinstance(obj.get("items"), list):
                    queue = _read_watch_state_queue()
                    for record in obj["items"]:
                        queue = _upsert_watch_state_queue_record(record)
                else:
                    raise ValueError("payload requires record or items")
            except Exception as exc:
                _json(self, 400, {"ok": False, "error": str(exc)})
                return
            _json(self, 200, {"ok": True, "queue": queue})
            return

        if parsed.path == "/api/trakt/sync":
            try:
                obj = _read_request_json(self)
            except ValueError as exc:
                _json(self, 400, {"ok": False, "error": str(exc)})
                return
            result = _run_trakt_sync(dry_run=obj.get("dry_run", True) is not False)
            _json(self, 200 if result.get("ok") else 500, result)
            return

        if parsed.path != "/api/inputs":
            _json(self, 404, {"ok": False, "error": "Not found"})
            return

        try:
            obj = _read_request_json(self)
        except ValueError as exc:
            _json(self, 400, {"ok": False, "error": str(exc)})
            return

        try:
            validated, warnings = _validate_inputs_payload(obj)
        except ValueError as exc:
            _json(self, 400, {"ok": False, "error": str(exc)})
            return

        validated["generated_utc"] = _now_utc_iso()
        backup_path = _backup_inputs()
        _atomic_write(INPUTS_JSON, validated)
        _json(
            self,
            200,
            {
                "ok": True,
                "saved": str(INPUTS_JSON),
                "backup": backup_path,
                "utc": validated["generated_utc"],
                "inputs": validated,
                "warnings": warnings,
                "counts": {
                    "tv": len(validated["tv"]),
                    "movies": len(validated["movies"]),
                    "active_tv": sum(1 for item in validated["tv"] if item.get("in_scope") is not False),
                    "active_movies": sum(1 for item in validated["movies"] if item.get("in_scope") is not False),
                },
            },
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    host = "127.0.0.1"
    server = HTTPServer((host, args.port), Handler)

    print("------------------------------------------------------------")
    print("my_TV_Movie • Inputs Editor Server")
    print(f"Repo:  {REPO_ROOT}")
    print(f"File:  {INPUTS_JSON}")
    print(f"URL:   http://{host}:{args.port}/web/inputs_editor.html")
    print(f"TMDB:  env {TMDB_KEY_ENV} {'present' if os.environ.get(TMDB_KEY_ENV) else 'missing'}")
    print("------------------------------------------------------------")
    server.serve_forever()


if __name__ == "__main__":
    main()
