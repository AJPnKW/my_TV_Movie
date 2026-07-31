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
WORKFLOW_YML = REPO_ROOT / ".github" / "workflows" / "build-data.yml"
PAGES_YML = REPO_ROOT / ".github" / "workflows" / "pages.yml"
PIPELINE_RUNNER = REPO_ROOT / "scripts" / "run_pipeline_tmdb_trakt.py"
APP_RUNTIME = REPO_ROOT / "web" / "js" / "app_runtime.js"
DATA_LOADER = REPO_ROOT / "web" / "js" / "data_loader.js"
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


def _catalog_key(row: Dict[str, Any], media: str) -> str:
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


def _missing_inputs(inputs: List[Any], catalog_rows: List[Any], errors: Any, media: str) -> List[Dict[str, Any]]:
    active_inputs = [row for row in inputs if _is_active_input(row)]
    catalog_keys = {_catalog_key(row, media) for row in catalog_rows if isinstance(row, dict)}
    errors_keys = _error_keys(errors)
    missing: List[Dict[str, Any]] = []
    for idx, row in enumerate(active_inputs):
        if not isinstance(row, dict):
            continue
        key = _input_key(row, media)
        if key in catalog_keys or key in errors_keys:
            continue
        missing.append(
            {
                "input_index": idx,
                "media": media,
                "tmdb_id": row.get("tmdb_id"),
                "title": row.get("title") or row.get("name"),
                "reason": "active input is absent from data/data.json and absent from data.errors",
            }
        )
    return missing


def _inactive_inputs_present(inputs: List[Any], catalog_rows: List[Any], media: str) -> List[Dict[str, Any]]:
    inactive_inputs = [row for row in inputs if isinstance(row, dict) and row.get("in_scope") is False]
    catalog_keys = {_catalog_key(row, media) for row in catalog_rows if isinstance(row, dict)}
    present: List[Dict[str, Any]] = []
    for idx, row in enumerate(inactive_inputs):
        key = _input_key(row, media)
        if key not in catalog_keys:
            continue
        present.append(
            {
                "input_index": idx,
                "media": media,
                "tmdb_id": row.get("tmdb_id"),
                "title": row.get("title") or row.get("name"),
                "reason": "inactive input is present in data/data.json",
            }
        )
    return present


def _unexpected_catalog_rows(inputs: List[Any], catalog_rows: List[Any], media: str) -> List[Dict[str, Any]]:
    active_keys = {
        _input_key(row, media)
        for row in inputs
        if isinstance(row, dict) and _is_active_input(row)
    }
    unexpected: List[Dict[str, Any]] = []
    for idx, row in enumerate(catalog_rows):
        if not isinstance(row, dict):
            continue
        key = _catalog_key(row, media)
        if key in active_keys:
            continue
        unexpected.append(
            {
                "index": idx,
                "media": media,
                "tmdb_id": row.get("tmdb_id") or row.get("id"),
                "title": row.get("title") or row.get("name"),
                "reason": "data/data.json row is not backed by an active input",
            }
        )
    return unexpected


def _title_mismatches(inputs: List[Any], catalog_rows: List[Any], media: str) -> List[Dict[str, Any]]:
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
    for idx, row in enumerate(catalog_rows):
        if not isinstance(row, dict):
            continue
        key = _catalog_key(row, media)
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
        workflow_text = _read_text(WORKFLOW_YML)
        pages_text = _read_text(PAGES_YML)
        runner_text = _read_text(PIPELINE_RUNNER)
        app_runtime_text = _read_text(APP_RUNTIME)
        data_loader_text = _read_text(DATA_LOADER)
        watch_me_runtime_text = _read_text(WATCH_ME_RUNTIME) if WATCH_ME_RUNTIME.exists() else app_runtime_text
        inputs_editor_server_text = _read_text(INPUTS_EDITOR_SERVER)

        input_tv = inputs.get("tv") if isinstance(inputs, dict) else []
        input_movies = inputs.get("movies") if isinstance(inputs, dict) else []
        data_shows = data.get("shows") if isinstance(data, dict) else []
        data_movies = data.get("movies") if isinstance(data, dict) else []
        data_errors = data.get("errors") if isinstance(data, dict) else []
        inputs_generated_at = _parse_utc(inputs.get("generated_utc") if isinstance(inputs, dict) else None)
        data_generated_at = _parse_utc((data.get("meta") or {}).get("generated_utc") if isinstance(data, dict) else None)

        active_tv = [row for row in input_tv if _is_active_input(row)] if isinstance(input_tv, list) else []
        active_movies = [row for row in input_movies if _is_active_input(row)] if isinstance(input_movies, list) else []
        missing_tv = _missing_inputs(input_tv if isinstance(input_tv, list) else [], data_shows if isinstance(data_shows, list) else [], data_errors, "tv")
        missing_movies = _missing_inputs(input_movies if isinstance(input_movies, list) else [], data_movies if isinstance(data_movies, list) else [], data_errors, "movie")
        inactive_tv_present = _inactive_inputs_present(input_tv if isinstance(input_tv, list) else [], data_shows if isinstance(data_shows, list) else [], "tv")
        inactive_movies_present = _inactive_inputs_present(input_movies if isinstance(input_movies, list) else [], data_movies if isinstance(data_movies, list) else [], "movie")
        unexpected_tv = _unexpected_catalog_rows(input_tv if isinstance(input_tv, list) else [], data_shows if isinstance(data_shows, list) else [], "tv")
        unexpected_movies = _unexpected_catalog_rows(input_movies if isinstance(input_movies, list) else [], data_movies if isinstance(data_movies, list) else [], "movie")
        title_mismatch_tv = _title_mismatches(input_tv if isinstance(input_tv, list) else [], data_shows if isinstance(data_shows, list) else [], "tv")
        title_mismatch_movies = _title_mismatches(input_movies if isinstance(input_movies, list) else [], data_movies if isinstance(data_movies, list) else [], "movie")
        active_runtime_text = "\n".join([app_runtime_text, data_loader_text, watch_me_runtime_text])
        active_pipeline_text = "\n".join([workflow_text, pages_text, runner_text, inputs_editor_server_text])

        _check("inputs_json_exists", INPUTS_JSON.exists(), "data/inputs.json must exist", checks, logf)
        _check("data_json_exists", DATA_JSON.exists(), "data/data.json must exist", checks, logf)
        _check("workflow_uses_canonical_runner", "python scripts/run_pipeline_tmdb_trakt.py" in workflow_text, "build-data workflow must run scripts/run_pipeline_tmdb_trakt.py", checks, logf)
        _check("scheduled_builds_force_full_tmdb_refresh", "--force-full-tmdb" in workflow_text and "--force-full-refresh" in runner_text and "INCREMENTAL_CACHE_SCHEMA" in _read_text(REPO_ROOT / "scripts" / "fetch_tmdb.py"), "push builds may use incremental TMDB cache, but scheduled/manual builds must force a full TMDB refresh", checks, logf)
        _check("runtime_uses_single_data_json", "../data/data.json" in active_runtime_text and "loadCatalogDataFirst" in data_loader_text, "active runtime must load data/data.json as the shared catalog", checks, logf)
        _check("runtime_has_no_split_catalog_paths", all(term not in active_runtime_text for term in ("catalog_index.json", "catalog_detail", "calendar.json")), "active runtime must not reference split generated catalog files", checks, logf)
        _check("pipeline_has_no_split_catalog_paths", all(term not in active_pipeline_text for term in ("catalog_index.json", "catalog_detail", "calendar.json", "build_split_runtime.py", "SPLIT_RUNTIME")), "active pipeline, workflows, and editor publish path must not reference split generated catalog files", checks, logf)
        _check("no_legacy_input_paths", all(term not in workflow_text + runner_text for term in ("tv_list.txt", "movies_list.txt", "live_tv_list.txt", "inputs_parsed.json")), "active production files must not reference legacy txt/input_parsed paths", checks, logf)
        _check("inputs_editor_verifies_tmdb_identity", "_validate_tmdb_entry_identity" in inputs_editor_server_text and "resolves to" in inputs_editor_server_text, "inputs editor save path must reject title/TMDB ID mismatches", checks, logf)
        _check("inputs_editor_publishes_and_syncs_generated_artifacts", all(term in inputs_editor_server_text for term in ("/api/publish-inputs", "/api/publish-status", "_editor_publish_status", "_wait_for_generated_artifacts", "_build_data_workflow_run", "BUILD_DATA_WORKFLOW", "GitHub build-data succeeded; no generated runtime artifact commit was needed", "_stash_generated_artifacts_if_needed", "_generated_artifact_changes_since", "_has_runtime_artifact_update", "_ensure_publishable_git_state", "_git_operation_in_progress", "_resolve_publish_remote", "detached HEAD", "HEAD:refs/heads", "diff-filter=U", "Git conflict state could not be checked", "git diff --cached failed", "qa_pipeline_integrity.py")), "inputs editor publish path must expose publish status, wait for build-data and generated runtime artifact changes, complete input-only updates after workflow success, block unsafe Git states and failed conflict scans, push the actual HEAD commit, fast-forward local checkout, and validate reconciliation", checks, logf)
        _check("inputs_editor_serves_shared_runtime_assets", all(term in inputs_editor_server_text for term in ("_serve_static_repo_file", 'path.startswith("/data/")', 'path.startswith("/assets/")', "ASSETS_DIR")), "inputs editor local server must serve shared read-only data/assets used by editor-loaded scripts", checks, logf)
        _check("input_only_pushes_trigger_pages", "steps.commit-artifacts.outputs.changed == 'true' || github.event_name == 'push'" in workflow_text and "gh workflow run pages.yml --ref main" in workflow_text, "build-data must trigger Pages for successful input-only pushes even when generated runtime artifacts do not change", checks, logf)
        _check("runtime_generated_after_inputs", bool(inputs_generated_at and data_generated_at and data_generated_at >= inputs_generated_at), f"inputs_generated_utc={inputs.get('generated_utc') if isinstance(inputs, dict) else ''} data_generated_utc={(data.get('meta') or {}).get('generated_utc') if isinstance(data, dict) else ''}", checks, logf)

        _check("active_tv_inputs_reconciled", not missing_tv, f"active_tv={len(active_tv)} data_shows={len(data_shows) if isinstance(data_shows, list) else 0} unresolved_unreported={len(missing_tv)}", checks, logf)
        _check("active_movie_inputs_reconciled", not missing_movies, f"active_movies={len(active_movies)} data_movies={len(data_movies) if isinstance(data_movies, list) else 0} unresolved_unreported={len(missing_movies)}", checks, logf)
        _check("inactive_tv_inputs_excluded", not inactive_tv_present, f"inactive_present={len(inactive_tv_present)}", checks, logf)
        _check("inactive_movie_inputs_excluded", not inactive_movies_present, f"inactive_present={len(inactive_movies_present)}", checks, logf)
        _check("catalog_tv_backed_by_inputs", not unexpected_tv, f"unexpected_data_rows={len(unexpected_tv)}", checks, logf)
        _check("catalog_movies_backed_by_inputs", not unexpected_movies, f"unexpected_data_rows={len(unexpected_movies)}", checks, logf)
        _check("tv_input_titles_match_generated_titles", not title_mismatch_tv, f"title_mismatches={len(title_mismatch_tv)}", checks, logf)
        _check("movie_input_titles_match_generated_titles", not title_mismatch_movies, f"title_mismatches={len(title_mismatch_movies)}", checks, logf)
        _check("runtime_errors_absent", not data_errors, f"data_errors={len(data_errors) if isinstance(data_errors, list) else 0}", checks, logf)
        _check("single_runtime_catalog_has_rows", isinstance(data_shows, list) and isinstance(data_movies, list) and (bool(data_shows) or bool(data_movies)), "data/data.json must contain runtime shows and movies", checks, logf)

        ok = all(passed for _, passed, _ in checks)
        report = {
            "generated_utc": _utc_ts(),
            "repo_root": str(REPO_ROOT),
            "inputs_json": str(INPUTS_JSON),
            "data_json": str(DATA_JSON),
            "counts": {
                "inputs_tv_total": len(input_tv) if isinstance(input_tv, list) else 0,
                "inputs_tv_active": len(active_tv),
                "inputs_movies_total": len(input_movies) if isinstance(input_movies, list) else 0,
                "inputs_movies_active": len(active_movies),
                "data_shows": len(data_shows) if isinstance(data_shows, list) else 0,
                "data_movies": len(data_movies) if isinstance(data_movies, list) else 0,
                "data_errors": len(data_errors) if isinstance(data_errors, list) else 0,
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
            "unexpected_data_rows": {
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
            _log(logf, "[qa_pipeline_integrity] unexpected_data_rows follow in report JSON")
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
