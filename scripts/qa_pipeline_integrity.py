#!/usr/bin/env python3
from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
INPUTS_JSON = DATA_DIR / "inputs.json"
DATA_JSON = DATA_DIR / "data.json"
INDEX_JSON = DATA_DIR / "catalog_index.json"
CALENDAR_JSON = DATA_DIR / "calendar.json"
DETAIL_DIR = DATA_DIR / "catalog_detail"
WORKFLOW_YML = REPO_ROOT / ".github" / "workflows" / "build-data.yml"
PIPELINE_RUNNER = REPO_ROOT / "scripts" / "run_pipeline_tmdb_trakt.py"
APP_RUNTIME = REPO_ROOT / "web" / "js" / "app_runtime.js"
WATCH_ME_RUNTIME = REPO_ROOT / "web" / "js" / "watch_me_runtime.js"
INPUTS_EDITOR_SERVER = REPO_ROOT / "tools" / "inputs_editor" / "inputs_editor_server.py"
REPORT_DIR = REPO_ROOT / "reports"
LOG_DIR = REPO_ROOT / "logs"


def _utc_ts() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _local_ts() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _load_log() -> Tuple[Path, Any]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"qa_pipeline_integrity_{_local_ts()}.log.txt"
    fh = path.open("w", encoding="utf-8")
    return path, fh


def _log(fh: Any, message: str) -> None:
    fh.write(f"{_utc_ts()} | {message}\n")
    fh.flush()


def _check(name: str, passed: bool, detail: str, checks: List[Tuple[str, bool, str]], fh: Any) -> None:
    checks.append((name, passed, detail))
    _log(fh, f"[qa_pipeline_integrity] CHECK {name} => {'OK' if passed else 'FAIL'} | {detail}")


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return 0


def _parse_utc(value: Any) -> Optional[_dt.datetime]:
    raw = _safe_text(value)
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        parsed = _dt.datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=_dt.timezone.utc)
        return parsed.astimezone(_dt.timezone.utc)
    except Exception:
        return None


def _title_tokens(value: Any) -> set[str]:
    stop = {"a", "an", "and", "in", "of", "part", "the", "to", "with"}
    return {token for token in re.findall(r"[a-z0-9]+", _safe_text(value).lower()) if token not in stop and not token.isdigit()}


def _is_active_input(row: Any) -> bool:
    if not isinstance(row, dict):
        return False
    return row.get("in_scope") is not False


def _input_key(row: Dict[str, Any], media: str) -> str:
    tmdb_id = _safe_int(row.get("tmdb_id") or row.get("id"))
    title = _safe_text(row.get("title") or row.get("name")).lower()
    if tmdb_id:
        return f"{media}:tmdb:{tmdb_id}"
    return f"{media}:title:{title}"


def _index_key(row: Dict[str, Any], media: str) -> str:
    tmdb_id = _safe_int(row.get("tmdb_id") or row.get("id"))
    title = _safe_text(row.get("title") or row.get("name")).lower()
    if tmdb_id:
        return f"{media}:tmdb:{tmdb_id}"
    return f"{media}:title:{title}"


def _error_keys(errors: Any) -> set[str]:
    keys: set[str] = set()
    if not isinstance(errors, list):
        return keys
    for err in errors:
        if not isinstance(err, dict):
            continue
        media_raw = _safe_text(err.get("media") or err.get("type_media") or err.get("kind")).lower()
        if media_raw in {"tv", "show", "shows"}:
            media = "tv"
        elif media_raw in {"movie", "movies"}:
            media = "movie"
        else:
            # If the error came from older code without media, do not let it hide a missing input.
            continue
        tmdb_id = _safe_int(err.get("tmdb_id") or err.get("id"))
        title = _safe_text(err.get("title") or err.get("name")).lower()
        if tmdb_id:
            keys.add(f"{media}:tmdb:{tmdb_id}")
        elif title:
            keys.add(f"{media}:title:{title}")
    return keys


def _missing_inputs(inputs: List[Any], index_rows: List[Any], errors: Any, media: str) -> List[Dict[str, Any]]:
    active_inputs = [row for row in inputs if _is_active_input(row)]
    index_keys = {_index_key(row, media) for row in index_rows if isinstance(row, dict)}
    errors_keys = _error_keys(errors)
    missing: List[Dict[str, Any]] = []
    for idx, row in enumerate(active_inputs):
        if not isinstance(row, dict):
            continue
        key = _input_key(row, media)
        if key in index_keys or key in errors_keys:
            continue
        missing.append(
            {
                "input_index": idx,
                "media": media,
                "tmdb_id": row.get("tmdb_id"),
                "title": row.get("title") or row.get("name"),
                "reason": "active input is absent from catalog_index and absent from data.errors",
            }
        )
    return missing


def _inactive_inputs_present(inputs: List[Any], index_rows: List[Any], media: str) -> List[Dict[str, Any]]:
    inactive_inputs = [row for row in inputs if isinstance(row, dict) and row.get("in_scope") is False]
    index_keys = {_index_key(row, media) for row in index_rows if isinstance(row, dict)}
    present: List[Dict[str, Any]] = []
    for idx, row in enumerate(inactive_inputs):
        key = _input_key(row, media)
        if key not in index_keys:
            continue
        present.append(
            {
                "input_index": idx,
                "media": media,
                "tmdb_id": row.get("tmdb_id"),
                "title": row.get("title") or row.get("name"),
                "reason": "inactive input is present in catalog_index",
            }
        )
    return present


def _unexpected_index_rows(inputs: List[Any], index_rows: List[Any], media: str) -> List[Dict[str, Any]]:
    active_keys = {
        _input_key(row, media)
        for row in inputs
        if isinstance(row, dict) and _is_active_input(row)
    }
    unexpected: List[Dict[str, Any]] = []
    for idx, row in enumerate(index_rows):
        if not isinstance(row, dict):
            continue
        key = _index_key(row, media)
        if key in active_keys:
            continue
        unexpected.append(
            {
                "index": idx,
                "media": media,
                "tmdb_id": row.get("tmdb_id") or row.get("id"),
                "title": row.get("title") or row.get("name"),
                "reason": "catalog_index row is not backed by an active input",
            }
        )
    return unexpected


def _title_mismatches(inputs: List[Any], index_rows: List[Any], media: str) -> List[Dict[str, Any]]:
    titles_by_key: Dict[str, str] = {}
    raw_titles_by_key: Dict[str, str] = {}
    for row in inputs:
        if not isinstance(row, dict) or not _is_active_input(row):
            continue
        key = _input_key(row, media)
        title = _safe_text(row.get("title") or row.get("name"))
        if title:
            titles_by_key[key] = title.lower()
            raw_titles_by_key[key] = title

    mismatches: List[Dict[str, Any]] = []
    for idx, row in enumerate(index_rows):
        if not isinstance(row, dict):
            continue
        key = _index_key(row, media)
        input_title = titles_by_key.get(key)
        if not input_title:
            continue
        generated_title = _safe_text(row.get("title") or row.get("name"))
        if (
            generated_title
            and generated_title.lower() != input_title
            and not (_title_tokens(raw_titles_by_key.get(key)) & _title_tokens(generated_title))
        ):
            mismatches.append(
                {
                    "index": idx,
                    "media": media,
                    "tmdb_id": row.get("tmdb_id") or row.get("id"),
                    "input_title": raw_titles_by_key.get(key),
                    "generated_title": generated_title,
                    "reason": "active input title does not match generated TMDB title for the same key",
                }
            )
    return mismatches


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    log_path, logf = _load_log()
    checks: List[Tuple[str, bool, str]] = []
    try:
        inputs = _read_json(INPUTS_JSON)
        data = _read_json(DATA_JSON)
        index = _read_json(INDEX_JSON)
        calendar = _read_json(CALENDAR_JSON)
        workflow_text = _read_text(WORKFLOW_YML)
        runner_text = _read_text(PIPELINE_RUNNER)
        app_runtime_text = _read_text(APP_RUNTIME)
        watch_me_runtime_text = _read_text(WATCH_ME_RUNTIME) if WATCH_ME_RUNTIME.exists() else app_runtime_text
        inputs_editor_server_text = _read_text(INPUTS_EDITOR_SERVER)

        input_tv = inputs.get("tv") if isinstance(inputs, dict) else []
        input_movies = inputs.get("movies") if isinstance(inputs, dict) else []
        data_shows = data.get("shows") if isinstance(data, dict) else []
        data_movies = data.get("movies") if isinstance(data, dict) else []
        data_errors = data.get("errors") if isinstance(data, dict) else []
        inputs_generated_at = _parse_utc(inputs.get("generated_utc") if isinstance(inputs, dict) else None)
        data_generated_at = _parse_utc((data.get("meta") or {}).get("generated_utc") if isinstance(data, dict) else None)
        index_shows = index.get("shows") if isinstance(index, dict) else []
        index_movies = index.get("movies") if isinstance(index, dict) else []
        detail_files = list(DETAIL_DIR.glob("*.json"))
        calendar_days = calendar.get("days") if isinstance(calendar, dict) else {}

        active_tv = [row for row in input_tv if _is_active_input(row)] if isinstance(input_tv, list) else []
        active_movies = [row for row in input_movies if _is_active_input(row)] if isinstance(input_movies, list) else []
        missing_tv = _missing_inputs(input_tv if isinstance(input_tv, list) else [], index_shows if isinstance(index_shows, list) else [], data_errors, "tv")
        missing_movies = _missing_inputs(input_movies if isinstance(input_movies, list) else [], index_movies if isinstance(index_movies, list) else [], data_errors, "movie")
        inactive_tv_present = _inactive_inputs_present(input_tv if isinstance(input_tv, list) else [], index_shows if isinstance(index_shows, list) else [], "tv")
        inactive_movies_present = _inactive_inputs_present(input_movies if isinstance(input_movies, list) else [], index_movies if isinstance(index_movies, list) else [], "movie")
        unexpected_tv = _unexpected_index_rows(input_tv if isinstance(input_tv, list) else [], index_shows if isinstance(index_shows, list) else [], "tv")
        unexpected_movies = _unexpected_index_rows(input_movies if isinstance(input_movies, list) else [], index_movies if isinstance(index_movies, list) else [], "movie")
        title_mismatch_tv = _title_mismatches(input_tv if isinstance(input_tv, list) else [], index_shows if isinstance(index_shows, list) else [], "tv")
        title_mismatch_movies = _title_mismatches(input_movies if isinstance(input_movies, list) else [], index_movies if isinstance(index_movies, list) else [], "movie")

        _check("inputs_json_exists", INPUTS_JSON.exists(), "data/inputs.json must exist", checks, logf)
        _check("catalog_index_exists", INDEX_JSON.exists(), "data/catalog_index.json must exist", checks, logf)
        _check("calendar_json_exists", CALENDAR_JSON.exists(), "data/calendar.json must exist", checks, logf)
        _check("catalog_detail_exists", DETAIL_DIR.exists(), "data/catalog_detail must exist", checks, logf)
        _check("workflow_uses_canonical_runner", "python scripts/run_pipeline_tmdb_trakt.py" in workflow_text, "build-data workflow must run scripts/run_pipeline_tmdb_trakt.py", checks, logf)
        _check("runner_builds_split_runtime", "SPLIT_RUNTIME_BUILD" in runner_text and "build_split_runtime.py" in runner_text, "pipeline runner must build split runtime artifacts", checks, logf)
        _check("runtime_no_first_load_data_json", "../data/data.json" not in app_runtime_text and "data/data.json" not in watch_me_runtime_text, "runtime first-load paths must not use data/data.json", checks, logf)
        _check("runtime_uses_split_index", "catalog_index.json" in app_runtime_text and "catalog_index.json" in watch_me_runtime_text, "app runtime and watch_me must use catalog_index.json", checks, logf)
        _check("runtime_uses_calendar_feed", "calendar.json" in app_runtime_text and "calendar.json" in watch_me_runtime_text, "app runtime and watch_me must use calendar.json", checks, logf)
        _check("no_legacy_input_paths", all(term not in workflow_text + runner_text for term in ("tv_list.txt", "movies_list.txt", "live_tv_list.txt", "inputs_parsed.json")), "active production files must not reference legacy txt/input_parsed paths", checks, logf)
        _check("inputs_editor_verifies_tmdb_identity", "_validate_tmdb_entry_identity" in inputs_editor_server_text and "resolves to" in inputs_editor_server_text, "inputs editor save path must reject title/TMDB ID mismatches", checks, logf)
        _check("inputs_editor_publishes_and_syncs_generated_artifacts", all(term in inputs_editor_server_text for term in ("/api/publish-inputs", "_wait_for_generated_artifacts", "_stash_generated_artifacts_if_needed", "_generated_artifact_changes_since", "_has_runtime_artifact_update", "qa_pipeline_integrity.py")), "inputs editor publish path must wait for generated runtime artifact changes, fast-forward local checkout, and validate reconciliation", checks, logf)
        _check("runtime_generated_after_inputs", bool(inputs_generated_at and data_generated_at and data_generated_at >= inputs_generated_at), f"inputs_generated_utc={inputs.get('generated_utc') if isinstance(inputs, dict) else ''} data_generated_utc={(data.get('meta') or {}).get('generated_utc') if isinstance(data, dict) else ''}", checks, logf)

        _check("active_tv_inputs_reconciled", not missing_tv, f"active_tv={len(active_tv)} catalog_index_shows={len(index_shows) if isinstance(index_shows, list) else 0} unresolved_unreported={len(missing_tv)}", checks, logf)
        _check("active_movie_inputs_reconciled", not missing_movies, f"active_movies={len(active_movies)} catalog_index_movies={len(index_movies) if isinstance(index_movies, list) else 0} unresolved_unreported={len(missing_movies)}", checks, logf)
        _check("inactive_tv_inputs_excluded", not inactive_tv_present, f"inactive_present={len(inactive_tv_present)}", checks, logf)
        _check("inactive_movie_inputs_excluded", not inactive_movies_present, f"inactive_present={len(inactive_movies_present)}", checks, logf)
        _check("catalog_tv_backed_by_inputs", not unexpected_tv, f"unexpected_index_rows={len(unexpected_tv)}", checks, logf)
        _check("catalog_movies_backed_by_inputs", not unexpected_movies, f"unexpected_index_rows={len(unexpected_movies)}", checks, logf)
        _check("tv_input_titles_match_generated_titles", not title_mismatch_tv, f"title_mismatches={len(title_mismatch_tv)}", checks, logf)
        _check("movie_input_titles_match_generated_titles", not title_mismatch_movies, f"title_mismatches={len(title_mismatch_movies)}", checks, logf)
        _check("runtime_errors_absent", not data_errors, f"data_errors={len(data_errors) if isinstance(data_errors, list) else 0}", checks, logf)
        _check("detail_file_count_matches_index", len(detail_files) >= (len(index_shows) if isinstance(index_shows, list) else 0) + (len(index_movies) if isinstance(index_movies, list) else 0), f"detail_files={len(detail_files)} index_total={(len(index_shows) if isinstance(index_shows, list) else 0) + (len(index_movies) if isinstance(index_movies, list) else 0)}", checks, logf)
        _check("calendar_has_days", isinstance(calendar_days, dict) and bool(calendar_days), f"calendar day buckets={len(calendar_days) if isinstance(calendar_days, dict) else 0}", checks, logf)
        _check("monolith_reference_still_builds", isinstance(data_shows, list) and isinstance(data_movies, list), "data/data.json remains available as a non-runtime reference artifact", checks, logf)

        ok = all(passed for _, passed, _ in checks)
        report = {
            "generated_utc": _utc_ts(),
            "repo_root": str(REPO_ROOT),
            "inputs_json": str(INPUTS_JSON),
            "data_json": str(DATA_JSON),
            "catalog_index_json": str(INDEX_JSON),
            "calendar_json": str(CALENDAR_JSON),
            "catalog_detail_dir": str(DETAIL_DIR),
            "counts": {
                "inputs_tv_total": len(input_tv) if isinstance(input_tv, list) else 0,
                "inputs_tv_active": len(active_tv),
                "inputs_movies_total": len(input_movies) if isinstance(input_movies, list) else 0,
                "inputs_movies_active": len(active_movies),
                "data_shows": len(data_shows) if isinstance(data_shows, list) else 0,
                "data_movies": len(data_movies) if isinstance(data_movies, list) else 0,
                "data_errors": len(data_errors) if isinstance(data_errors, list) else 0,
                "index_shows": len(index_shows) if isinstance(index_shows, list) else 0,
                "index_movies": len(index_movies) if isinstance(index_movies, list) else 0,
                "detail_files": len(detail_files),
                "calendar_days": len(calendar_days) if isinstance(calendar_days, dict) else 0,
                "inputs_generated_utc": inputs.get("generated_utc") if isinstance(inputs, dict) else "",
                "data_generated_utc": (data.get("meta") or {}).get("generated_utc") if isinstance(data, dict) else "",
            },
            "unresolved_unreported_inputs": {
                "tv": missing_tv,
                "movies": missing_movies,
            },
            "inactive_inputs_present": {
                "tv": inactive_tv_present,
                "movies": inactive_movies_present,
            },
            "unexpected_index_rows": {
                "tv": unexpected_tv,
                "movies": unexpected_movies,
            },
            "title_mismatches": {
                "tv": title_mismatch_tv,
                "movies": title_mismatch_movies,
            },
            "runtime_errors": data_errors if isinstance(data_errors, list) else [],
            "checks": [{"name": name, "passed": passed, "detail": detail} for name, passed, detail in checks],
            "result": "OK" if ok else "FAIL",
        }
        report_path = REPORT_DIR / f"_qa_pipeline_integrity_{_local_ts()}.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        _log(logf, f"[qa_pipeline_integrity] report={report_path}")
        if missing_tv or missing_movies:
            _log(logf, "[qa_pipeline_integrity] unresolved_unreported_inputs follow in report JSON")
        if inactive_tv_present or inactive_movies_present:
            _log(logf, "[qa_pipeline_integrity] inactive_inputs_present follow in report JSON")
        if unexpected_tv or unexpected_movies:
            _log(logf, "[qa_pipeline_integrity] unexpected_index_rows follow in report JSON")
        if title_mismatch_tv or title_mismatch_movies:
            _log(logf, "[qa_pipeline_integrity] title_mismatches follow in report JSON")
        if data_errors:
            _log(logf, "[qa_pipeline_integrity] runtime_errors follow in report JSON")
        return 0 if ok else 3
    finally:
        logf.close()
        print(str(log_path))


if __name__ == "__main__":
    raise SystemExit(main())
