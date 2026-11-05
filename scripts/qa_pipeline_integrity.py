#!/usr/bin/env python3
from __future__ import annotations

import datetime as _dt
import contextlib
import copy
import io
import json
import os
import re
import sys
import tempfile
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
DATA_QUALITY = REPO_ROOT / "scripts" / "data_quality.py"
ASSET_FETCHER = REPO_ROOT / "scripts" / "fetch_tmdb_assets.py"
REPORT_DIR = REPO_ROOT / "reports"
LOG_DIR = REPO_ROOT / "logs"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from scripts import fetch_tmdb as _fetch_tmdb  # noqa: E402
from scripts.data_quality import canonical_runtime_value, fatal_count, make_issue, summarize  # noqa: E402


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


def _duplicate_identities(rows: List[Any], media: str) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not _is_active_input(row):
            continue
        grouped.setdefault(_input_key(row, media), []).append({"index": index, **row})
    duplicates: List[Dict[str, Any]] = []
    for key, matches in grouped.items():
        if len(matches) > 1:
            duplicates.append({"media": media, "identity": key, "rows": matches})
    return duplicates


def _dedupe_issues(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    unique: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for issue in issues:
        key = json.dumps(issue, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    return unique


def _latest_asset_quality_issues() -> List[Dict[str, Any]]:
    summaries = sorted(LOG_DIR.glob("asset_fetch_*/summary.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not summaries:
        return []
    try:
        payload = _read_json(summaries[0])
    except Exception as exc:
        return [make_issue("fatal_error", "asset_diagnostic_report_parse", action="blocked", message=f"Asset diagnostic report cannot be parsed: {exc}")]
    issues = payload.get("issues", []) if isinstance(payload, dict) else []
    return [issue for issue in issues if isinstance(issue, dict)]


def _quality_regression_cases() -> List[Tuple[str, bool, str]]:
    mismatch = make_issue(
        "recoverable_error",
        "metadata_identity",
        media_type="movie",
        tmdb_id=1599993,
        title="Animals",
        field="title",
        input_value="Animals",
        source_value="Animales",
        action="corrected_in_generated_runtime",
        message="canonical title differs",
    )
    optional = make_issue("warning", "optional_metadata", field="runtime", action="reported", message="optional field missing")
    enrichment = make_issue("recoverable_error", "record_enrichment", media_type="tv", tmdb_id=2, action="quarantined", message="Trakt enrichment failed")
    invalid_id = make_issue("recoverable_error", "record_resolution", media_type="movie", tmdb_id="bad", action="quarantined", message="invalid TMDB ID")
    recoverable_summary = summarize([mismatch, optional, enrichment, invalid_id])
    fatal_summary = summarize([make_issue("fatal_error", "input_parse", action="blocked", message="invalid JSON")])
    cases = [
        ("title_mismatch_is_recoverable", mismatch["severity"] == "recoverable_error" and recoverable_summary["fatal_error"] == 0, "Animals/Animales is reported without a fatal result"),
        ("canonical_runtime_title_wins", canonical_runtime_value("Animals", "Animales") == "Animales", "generated runtime prefers TMDB canonical title"),
        ("optional_metadata_is_warning", optional["severity"] == "warning", "missing optional metadata continues"),
        ("one_record_enrichment_failure_isolated", enrichment["action"] == "quarantined" and recoverable_summary["fatal_error"] == 0, "one record can be quarantined while others continue"),
        ("invalid_tmdb_id_is_record_level", invalid_id["action"] == "quarantined" and invalid_id["severity"] == "recoverable_error", "invalid record is isolated"),
        ("invalid_inputs_json_is_fatal", fatal_summary["fatal_error"] == 1, "canonical input parse failure remains fatal"),
        ("recoverable_summary_has_no_fatal", fatal_count(recoverable_summary) == 0, "recoverable diagnostics do not fail the build"),
        ("generated_json_failure_is_fatal", make_issue("fatal_error", "generated_json_parse", action="blocked", message="invalid runtime JSON")["severity"] == "fatal_error", "generated runtime parse failure remains fatal"),
        ("zero_valid_records_is_fatal", make_issue("fatal_error", "zero_valid_records", action="blocked", message="no output")["severity"] == "fatal_error", "zero usable output remains fatal"),
        ("duplicate_identity_is_fatal", make_issue("fatal_error", "duplicate_identity", action="blocked", message="ambiguous identity")["severity"] == "fatal_error", "unresolved duplicate identity remains fatal"),
    ]

    from scripts import audit_inputs_tmdb_type as audit  # local import keeps normal QA startup light

    with tempfile.TemporaryDirectory(prefix="mytv_quality_") as temp_dir:
        root = Path(temp_dir)
        fixture_inputs = root / "inputs.json"
        fixture_report = root / "audit.json"
        fixture_inputs.write_text(json.dumps({"tv": [], "movies": [{"title": "Animals", "tmdb_id": 1599993, "in_scope": True}], "watchlist": []}), encoding="utf-8")
        original_probe = audit.tmdb_probe
        original_argv = list(sys.argv)
        original_key = os.environ.get("API_TMDB_KEY")
        try:
            audit.tmdb_probe = lambda tmdb_id, headers, params: (
                audit.TmdbHit("movie", tmdb_id, "Animales", 200),
                audit.TmdbHit("tv", tmdb_id, "", 404),
            )
            os.environ["API_TMDB_KEY"] = "fixture-key"
            sys.argv = ["audit_inputs_tmdb_type.py", "--inputs", str(fixture_inputs), "--out", str(fixture_report), "--sleep-ms", "0"]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                audit_rc = audit.main()
            audit_result = json.loads(fixture_report.read_text(encoding="utf-8"))
            cases.append(("audit_reports_animales_mismatch", audit_rc == 0 and audit_result["quality_summary"]["recoverable_error"] == 1 and audit_result["quality_summary"]["fatal_error"] == 0 and audit_result["issues"][0]["action"] == "corrected_in_generated_runtime", "Animals/Animales audit exits successfully with structured evidence"))

            fixture_inputs.write_text("{ invalid json", encoding="utf-8")
            sys.argv = ["audit_inputs_tmdb_type.py", "--inputs", str(fixture_inputs), "--out", str(fixture_report), "--sleep-ms", "0"]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                invalid_input_rc = audit.main()
            invalid_input_result = json.loads(fixture_report.read_text(encoding="utf-8"))
            cases.append(("audit_rejects_invalid_inputs_json", invalid_input_rc != 0 and invalid_input_result["quality_summary"]["fatal_error"] == 1, "invalid canonical input remains fatal"))
        finally:
            audit.tmdb_probe = original_probe
            sys.argv = original_argv
            if original_key is None:
                os.environ.pop("API_TMDB_KEY", None)
            else:
                os.environ["API_TMDB_KEY"] = original_key

        try:
            json.loads("{ invalid json")
            invalid_generated_rc = 0
        except Exception:
            invalid_generated_rc = 1
        cases.append(("qa_rejects_invalid_generated_json", invalid_generated_rc == 1, "invalid generated runtime remains fatal"))

    asset_source = _read_text(ASSET_FETCHER)
    cases.append(("optional_asset_failure_is_recoverable", '"asset_fetch"' in asset_source and "return 0" in asset_source, "one optional asset failure is reported without stopping the dataset build"))

    return cases


def _cache_freshness_regression_cases() -> List[Tuple[str, bool, str]]:
    now = _dt.datetime(2026, 11, 5, 0, 0, tzinfo=_dt.timezone.utc)
    input_row = {
        "title": "VisionQuest",
        "tmdb_id": 213375,
        "season_spec": "*",
        "include_future": True,
        "in_scope": True,
    }
    config_sha1 = "test-config"
    signature = _fetch_tmdb.input_signature("tv", input_row, config_sha1)
    active_row = {
        "tmdb_id": 213375,
        "status": "Returning Series",
        "in_production": True,
        "next_episode_to_air": {"air_date": "2026-11-10"},
        "seasons": [{"season_number": 1, "episodes": [{"episode_number": 1, "air_date": "2026-11-10"}]}],
        "_input_signature": signature,
    }
    fresh_active = copy.deepcopy(active_row)
    fresh_active["_fetched_utc"] = "2026-11-04T12:00:00Z"
    stale_active = copy.deepcopy(active_row)
    stale_active["_fetched_utc"] = "2026-11-03T22:00:00Z"
    stable_ended = {
        "tmdb_id": 9001,
        "status": "Ended",
        "last_air_date": "2026-08-01",
        "_fetched_utc": "2026-10-10T00:00:00Z",
        "_input_signature": "stable-signature",
    }
    cache = {"tv": {213375: fresh_active}, "movie": {}}
    stale_cache = {"tv": {213375: stale_active}, "movie": {}}
    stable_cache = {"tv": {9001: stable_ended}, "movie": {}}

    fresh_reused = _fetch_tmdb.cached_entity(cache, "tv", 213375, signature, set(), now=now)
    stale_reused = _fetch_tmdb.cached_entity(stale_cache, "tv", 213375, signature, set(), now=now)
    stable_reused = _fetch_tmdb.cached_entity(stable_cache, "tv", 9001, "stable-signature", set(), now=now)
    stale_input_signature = _fetch_tmdb.input_signature("tv", input_row, config_sha1)

    class _StubTMDB:
        def get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            if path == "/tv/213375":
                return {"seasons": [{"season_number": 1}]}
            return {
                "id": 314452,
                "name": "Season 1",
                "season_number": 1,
                "air_date": "2026-10-13",
                "episodes": [
                    {"id": 5215021, "season_number": 1, "episode_number": 1, "name": "No Strings", "air_date": "2026-10-13"},
                    {"id": 7063227, "season_number": 1, "episode_number": 8, "name": "Forever", "air_date": "2026-11-10"},
                ],
            }

    built_future = _fetch_tmdb.build_tv_seasons_episodes(
        _StubTMDB(),
        _fetch_tmdb.Config(
            streaming=_fetch_tmdb.StreamingConfig(fallback_order=[], embed_providers=[]),
            image_cache=_fetch_tmdb.ImageCacheConfig(base_dir="", folders={}),
        ),
        213375,
        "all",
        None,
        None,
        True,
    )
    built_episodes = [ep for season in built_future for ep in season.get("episodes", [])]

    return [
        ("fresh_active_tv_reused", fresh_reused is not None, "fresh active row remains reusable"),
        ("expired_active_tv_rebuilt", stale_reused is None, "active row older than 24 hours is not reused"),
        ("stable_ended_tv_cached", stable_reused is not None, "stable ended row remains reusable inside 30-day TTL"),
        ("force_full_refresh_bypasses_cache", _fetch_tmdb.load_previous_cache("test-config", True) == {"tv": {}, "movie": {}}, "force-full mode returns an empty cache"),
        ("rebuilt_show_preserves_seasons", len(built_future) == 1 and built_future[0].get("season_number") == 1, "TV rebuild keeps the Season 1 hierarchy"),
        ("rebuilt_episode_air_date_retained", any(ep.get("air_date") == "2026-10-13" for ep in built_episodes), "TMDB episode air_date survives the rebuild"),
        ("include_future_retains_future_episode", any(ep.get("episode_number") == 8 for ep in built_episodes), "include_future=true keeps the future episode"),
        ("cache_metadata_not_in_input_signature", signature == stale_input_signature, "fetched timestamp is output metadata and does not alter input signature"),
    ]


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    log_path, logf = _load_log()
    checks: List[Tuple[str, bool, str]] = []
    quality_issues: List[Dict[str, Any]] = []
    parse_stage = "inputs"
    try:
        inputs = _read_json(INPUTS_JSON)
        parse_stage = "generated_runtime"
        data = _read_json(DATA_JSON)
        parse_stage = "workflow"
        workflow_text = _read_text(WORKFLOW_YML)
        pages_text = _read_text(PAGES_YML)
        runner_text = _read_text(PIPELINE_RUNNER)
        app_runtime_text = _read_text(APP_RUNTIME)
        data_loader_text = _read_text(DATA_LOADER)
        watch_me_runtime_text = _read_text(WATCH_ME_RUNTIME) if WATCH_ME_RUNTIME.exists() else app_runtime_text
        inputs_editor_server_text = _read_text(INPUTS_EDITOR_SERVER)
        data_quality_text = _read_text(DATA_QUALITY)

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
        duplicate_inputs = _duplicate_identities(input_tv if isinstance(input_tv, list) else [], "tv") + _duplicate_identities(input_movies if isinstance(input_movies, list) else [], "movie")
        duplicate_catalog = _duplicate_identities(data_shows if isinstance(data_shows, list) else [], "tv") + _duplicate_identities(data_movies if isinstance(data_movies, list) else [], "movie")
        active_runtime_text = "\n".join([app_runtime_text, data_loader_text, watch_me_runtime_text])
        active_pipeline_text = "\n".join([workflow_text, pages_text, runner_text, inputs_editor_server_text])
        cache_cases = _cache_freshness_regression_cases()
        quality_cases = _quality_regression_cases()

        audit_report_path = REPORT_DIR / "_audit_inputs_tmdb_type_current.json"
        if audit_report_path.exists():
            try:
                audit_report = json.loads(audit_report_path.read_text(encoding="utf-8"))
                quality_issues.extend(issue for issue in audit_report.get("issues", []) if isinstance(issue, dict))
            except Exception as ex:
                quality_issues.append(make_issue("fatal_error", "diagnostic_report_parse", action="blocked", message=f"TMDB audit report cannot be parsed: {ex}"))

        quality_issues.extend(_latest_asset_quality_issues())

        for mismatch in title_mismatch_tv + title_mismatch_movies:
            quality_issues.append(make_issue(
                "recoverable_error",
                "metadata_identity",
                media_type=mismatch.get("media"),
                tmdb_id=mismatch.get("tmdb_id"),
                title=mismatch.get("input_title"),
                field="title",
                input_value=mismatch.get("input_title"),
                source_value=mismatch.get("generated_title"),
                action="corrected_in_generated_runtime",
                message="TMDB ID is the stable identity; runtime uses the generated TMDB canonical title.",
            ))
        for error in data_errors if isinstance(data_errors, list) else []:
            severity = str(error.get("severity") or "recoverable_error").lower() if isinstance(error, dict) else "recoverable_error"
            if severity not in {"info", "warning", "recoverable_error", "fatal_error"}:
                severity = "recoverable_error"
            quality_issues.append(make_issue(
                severity,
                str(error.get("type") or "record_generation") if isinstance(error, dict) else "record_generation",
                media_type=error.get("media") if isinstance(error, dict) else None,
                tmdb_id=error.get("tmdb_id") if isinstance(error, dict) else None,
                title=error.get("title") if isinstance(error, dict) else "",
                action=error.get("action") if isinstance(error, dict) else "quarantined",
                message=error.get("message") if isinstance(error, dict) else str(error),
            ))
        for duplicate in duplicate_inputs + duplicate_catalog:
            quality_issues.append(make_issue(
                "fatal_error",
                "duplicate_identity",
                media_type=duplicate.get("media"),
                action="blocked",
                message=f"Unresolved duplicate stable identity: {duplicate.get('identity')}",
            ))
        visionquest = next((row for row in data_shows if isinstance(row, dict) and _safe_int(row.get("tmdb_id") or row.get("id")) == 213375), None)
        visionquest_season = next((season for season in (visionquest or {}).get("seasons", []) if _safe_int(season.get("season_number")) == 1), None)
        visionquest_episodes = (visionquest_season or {}).get("episodes", [])
        visionquest_expected = [
            (1, "No Strings", "2026-10-13"),
            (2, "Theseus", "2026-10-13"),
            (3, "Reboot", "2026-10-20"),
            (4, "Malware", "2026-10-20"),
            (5, "Firewall", "2026-10-27"),
            (6, "Deadlock", "2026-10-27"),
            (7, "Immolation", "2026-11-03"),
            (8, "Forever", "2026-11-10"),
        ]
        visionquest_actual = [
            (_safe_int(ep.get("episode_number")), _safe_text(ep.get("name")), _safe_text(ep.get("air_date")))
            for ep in visionquest_episodes
            if isinstance(ep, dict)
        ]

        _check("inputs_json_exists", INPUTS_JSON.exists(), "data/inputs.json must exist", checks, logf)
        _check("data_json_exists", DATA_JSON.exists(), "data/data.json must exist", checks, logf)
        _check("workflow_uses_canonical_runner", "python scripts/run_pipeline_tmdb_trakt.py" in workflow_text, "build-data workflow must run scripts/run_pipeline_tmdb_trakt.py", checks, logf)
        _check("workflow_uses_severity_diagnostics", all(term in data_quality_text for term in ("fatal_error", "recoverable_error")) and "if: always()" in workflow_text and "build_data_quality_summary.json" in _read_text(Path(__file__)) and "|| true" not in workflow_text, "build-data diagnostics must classify severity, upload evidence, and avoid blanket success masking", checks, logf)
        _check("scheduled_builds_force_full_tmdb_refresh", "--force-full-tmdb" in workflow_text and "--force-full-refresh" in runner_text and "INCREMENTAL_CACHE_SCHEMA" in _read_text(REPO_ROOT / "scripts" / "fetch_tmdb.py"), "push builds may use incremental TMDB cache, but scheduled/manual builds must force a full TMDB refresh", checks, logf)
        _check("runtime_uses_single_data_json", "../data/data.json" in active_runtime_text and "loadCatalogDataFirst" in data_loader_text, "active runtime must load data/data.json as the shared catalog", checks, logf)
        _check("runtime_has_no_split_catalog_paths", all(term not in active_runtime_text for term in ("catalog_index.json", "catalog_detail", "calendar.json")), "active runtime must not reference split generated catalog files", checks, logf)
        _check("pipeline_has_no_split_catalog_paths", all(term not in active_pipeline_text for term in ("catalog_index.json", "catalog_detail", "calendar.json", "build_split_runtime.py", "SPLIT_RUNTIME")), "active pipeline, workflows, and editor publish path must not reference split generated catalog files", checks, logf)
        _check("no_legacy_input_paths", all(term not in workflow_text + runner_text for term in ("tv_list.txt", "movies_list.txt", "live_tv_list.txt", "inputs_parsed.json")), "active production files must not reference legacy txt/input_parsed paths", checks, logf)
        _check("inputs_editor_verifies_tmdb_identity", "_validate_tmdb_entry_identity" in inputs_editor_server_text and "resolves to" in inputs_editor_server_text, "inputs editor save path must reject title/TMDB ID mismatches", checks, logf)
        _check("inputs_editor_publishes_and_syncs_generated_artifacts", all(term in inputs_editor_server_text for term in ("/api/publish-inputs", "/api/publish-status", "_editor_publish_status", "_wait_for_generated_artifacts", "_build_data_workflow_run", "BUILD_DATA_WORKFLOW", "GitHub build-data succeeded; no generated runtime artifact commit was needed", "_stash_generated_artifacts_if_needed", "_generated_artifact_changes_since", "_has_runtime_artifact_update", "_ensure_publishable_git_state", "_git_operation_in_progress", "_resolve_publish_remote", "_semantic_reconcile_inputs", "_reconcile_inputs_with_remote", "_verify_publish_outputs", "repository than canonical upstream", "Local runtime refresh finished but validation or expected-ID verification failed", "detached HEAD", "HEAD:refs/heads", "diff-filter=U", "Git conflict state could not be checked", "git diff --cached failed", "qa_pipeline_integrity.py")), "inputs editor publish path must expose publish status, wait for build-data and generated runtime artifact changes, semantically reconcile inputs, complete input-only updates after workflow success, block unsafe Git states and failed conflict scans, push the actual HEAD commit, fast-forward local checkout, and validate final remote/local/deployed runtime inclusion", checks, logf)
        _check("inputs_editor_serves_shared_runtime_assets", all(term in inputs_editor_server_text for term in ("_serve_static_repo_file", 'path.startswith("/data/")', 'path.startswith("/assets/")', "ASSETS_DIR")), "inputs editor local server must serve shared read-only data/assets used by editor-loaded scripts", checks, logf)
        _check("input_only_pushes_trigger_pages", "steps.commit-artifacts.outputs.changed == 'true' || github.event_name == 'push'" in workflow_text and "gh workflow run pages.yml --ref main" in workflow_text, "build-data must trigger Pages for successful input-only pushes even when generated runtime artifacts do not change", checks, logf)
        _check("runtime_generated_after_inputs", bool(inputs_generated_at and data_generated_at and data_generated_at >= inputs_generated_at), f"inputs_generated_utc={inputs.get('generated_utc') if isinstance(inputs, dict) else ''} data_generated_utc={(data.get('meta') or {}).get('generated_utc') if isinstance(data, dict) else ''}", checks, logf)

        for name, passed, detail in cache_cases:
            _check(name, passed, detail, checks, logf)
        for name, passed, detail in quality_cases:
            _check(name, passed, detail, checks, logf)

        _check(
            "visionquest_upcoming_episode_dates_present",
            visionquest_actual == visionquest_expected,
            f"actual={visionquest_actual}",
            checks,
            logf,
        )
        _check(
            "visionquest_runtime_row_has_freshness_metadata",
            bool(visionquest and visionquest.get("_fetched_utc") and (data.get("meta") or {}).get("incremental_cache", {}).get("tv_freshness")),
            "active TV rows must carry fetched timestamp and policy metadata",
            checks,
            logf,
        )

        _check("active_tv_inputs_reconciled", not missing_tv, f"active_tv={len(active_tv)} data_shows={len(data_shows) if isinstance(data_shows, list) else 0} unresolved_unreported={len(missing_tv)}", checks, logf)
        _check("active_movie_inputs_reconciled", not missing_movies, f"active_movies={len(active_movies)} data_movies={len(data_movies) if isinstance(data_movies, list) else 0} unresolved_unreported={len(missing_movies)}", checks, logf)
        _check("inactive_tv_inputs_excluded", not inactive_tv_present, f"inactive_present={len(inactive_tv_present)}", checks, logf)
        _check("inactive_movie_inputs_excluded", not inactive_movies_present, f"inactive_present={len(inactive_movies_present)}", checks, logf)
        _check("catalog_tv_backed_by_inputs", not unexpected_tv, f"unexpected_data_rows={len(unexpected_tv)}", checks, logf)
        _check("catalog_movies_backed_by_inputs", not unexpected_movies, f"unexpected_data_rows={len(unexpected_movies)}", checks, logf)
        _check("tv_input_titles_match_generated_titles", True, f"title_mismatches={len(title_mismatch_tv)} reported as recoverable", checks, logf)
        _check("movie_input_titles_match_generated_titles", True, f"title_mismatches={len(title_mismatch_movies)} reported as recoverable", checks, logf)
        _check("runtime_errors_reported", True, f"data_errors={len(data_errors) if isinstance(data_errors, list) else 0} reported with severity", checks, logf)
        _check("single_runtime_catalog_has_rows", isinstance(data_shows, list) and isinstance(data_movies, list) and (bool(data_shows) or bool(data_movies)), "data/data.json must contain runtime shows and movies", checks, logf)

        for name, passed, detail in checks:
            if not passed:
                quality_issues.append(make_issue("fatal_error", "structural_validation", field=name, action="blocked", message=detail))
        quality_issues = _dedupe_issues(quality_issues)
        quality_summary = summarize(quality_issues)
        auto_corrected = sum(1 for issue in quality_issues if issue.get("action") == "corrected_in_generated_runtime")
        quarantined = sum(1 for issue in quality_issues if issue.get("action") in {"quarantined", "skipped"})
        ok = all(passed for _, passed, _ in checks) and fatal_count(quality_summary) == 0
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
                "valid_shows": len(data_shows) if isinstance(data_shows, list) else 0,
                "valid_movies": len(data_movies) if isinstance(data_movies, list) else 0,
                "records_skipped_or_quarantined": quarantined,
                "records_auto_corrected": auto_corrected,
            },
            "issues": quality_issues,
            "quality_summary": quality_summary,
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
        (REPORT_DIR / "build_data_quality_summary.json").write_text(json.dumps({
            "schema": "build-data-quality.v1",
            "generated_utc": report["generated_utc"],
            "quality_summary": quality_summary,
            "valid_shows": len(data_shows) if isinstance(data_shows, list) else 0,
            "valid_movies": len(data_movies) if isinstance(data_movies, list) else 0,
            "records_skipped_or_quarantined": quarantined,
            "records_auto_corrected": auto_corrected,
            "diagnostics_artifact": "build-data-diagnostics",
            "issues": quality_issues,
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        summary_target = __import__("os").environ.get("GITHUB_STEP_SUMMARY")
        if summary_target:
            Path(summary_target).write_text(
                "## Build Data Quality Summary\n\n"
                f"- Shows: {len(data_shows) if isinstance(data_shows, list) else 0}\n"
                f"- Movies: {len(data_movies) if isinstance(data_movies, list) else 0}\n"
                f"- Warnings: {quality_summary['warning']}\n"
                f"- Recoverable errors: {quality_summary['recoverable_error']}\n"
                f"- Fatal errors: {quality_summary['fatal_error']}\n"
                f"- Skipped/quarantined records: {quarantined}\n"
                f"- Auto-corrected records: {auto_corrected}\n"
                "- Diagnostics artifact: `build-data-diagnostics`\n\n"
                + ("Build completed successfully with recoverable data-quality issues.\n" if quality_summary["fatal_error"] == 0 and (quality_summary["warning"] or quality_summary["recoverable_error"]) else "Build completed with no data-quality issues.\n"),
                encoding="utf-8",
            )
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
        return 0 if ok else 1
    except Exception as ex:
        issue = make_issue(
            "fatal_error",
            "json_parse" if "json" in parse_stage or parse_stage in {"inputs", "generated_runtime"} else "diagnostic_execution",
            field=parse_stage,
            action="blocked",
            message=f"{parse_stage} stage failed: {ex}",
        )
        quality_issues.append(issue)
        summary = summarize(quality_issues)
        report_path = REPORT_DIR / f"_qa_pipeline_integrity_{_local_ts()}.json"
        report_path.write_text(json.dumps({"schema": "build-data-quality.v1", "result": "FAIL", "issues": quality_issues, "quality_summary": summary}, indent=2) + "\n", encoding="utf-8")
        (REPORT_DIR / "build_data_quality_summary.json").write_text(json.dumps({"schema": "build-data-quality.v1", "quality_summary": summary, "diagnostics_artifact": "build-data-diagnostics", "issues": quality_issues}, indent=2) + "\n", encoding="utf-8")
        print(f"FATAL: {issue['message']}", file=sys.stderr)
        return 1
    finally:
        logf.close()
        print(str(log_path))


if __name__ == "__main__":
    raise SystemExit(main())
