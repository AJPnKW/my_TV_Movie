#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/qa_pipeline_integrity.py
# [PROJECT] my_TV_Movie
# [ROLE]    Sanity + consistency checks across inputs.json and data/data.json
# [VERSION] v1.1.0
# [UPDATED] 2026-01-19_00-00-00
# [BUILD]   14.01.07
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import json
import os
import sys
from typing import Any, Dict, List, Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_JSON = os.path.join(REPO_ROOT, "data", "data.json")
INPUTS_JSON = os.path.join(REPO_ROOT, 'data', 'inputs.json')
AVAILABILITY_JSON = os.path.join(REPO_ROOT, "data", "watch_source_availability.json")
WEB_CONFIG = os.path.join(REPO_ROOT, "web", "config.json")
WORKFLOW_YML = os.path.join(REPO_ROOT, ".github", "workflows", "build-data.yml")
PIPELINE_RUNNER = os.path.join(REPO_ROOT, "scripts", "run_pipeline_tmdb_trakt.py")
FETCH_TMDB = os.path.join(REPO_ROOT, "scripts", "fetch_tmdb.py")
AVAILABILITY_LIB = os.path.join(REPO_ROOT, "scripts", "availability_status_lib.py")
LOG_DIR = os.path.join(REPO_ROOT, "logs")
REPORT_DIR = os.path.join(REPO_ROOT, "reports")
ALLOWED_AVAILABILITY = {"not_yet_released", "available", "unavailable", "unknown"}
REQUIRED_WATCH_SOURCE_FIELDS = ("key", "label", "href", "type")


def _utc_ts() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _local_ts_compact() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _ensure_dirs() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)


def _log_open() -> Tuple[str, Any]:
    _ensure_dirs()
    fp = os.path.join(LOG_DIR, f"qa_pipeline_integrity_{_local_ts_compact()}.log.txt")
    f = open(fp, "w", encoding="utf-8", errors="replace", newline="\n")
    return fp, f


def _log(f: Any, msg: str) -> None:
    f.write(f"{_utc_ts()} | {msg}\n")
    f.flush()


def _strip_jsonc(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.lstrip().startswith("//"):
            continue
        out = []
        in_str = False
        esc = False
        i = 0
        while i < len(line):
            ch = line[i]
            if in_str:
                out.append(ch)
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == "\"":
                    in_str = False
                i += 1
                continue
            if ch == "\"":
                in_str = True
                out.append(ch)
                i += 1
                continue
            if ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                break
            out.append(ch)
            i += 1
        lines.append("".join(out).rstrip())
    cleaned = "\n".join(lines)
    if not cleaned.lstrip().startswith("{"):
        brace = cleaned.find("{")
        if brace != -1:
            cleaned = cleaned[brace:]
    return cleaned


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        raw = fh.read()
    if path.endswith("config.json"):
        raw = _strip_jsonc(raw)
    return json.loads(raw)


def _count_missing_trakt(items: List[Dict[str, Any]]) -> int:
    return sum(1 for x in items if not x.get("trakt_id"))


def _as_int(v: Any) -> int:
    try:
        if v is None:
            return 0
        return int(str(v).strip() or "0")
    except Exception:
        return 0


def _index_by_tmdb(items: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    for x in items:
        tid = _as_int(x.get("tmdb_id"))
        if tid:
            out[tid] = x
    return out


def _is_local_asset(path: str) -> bool:
    p = (path or "").strip()
    return p.startswith("/assets/")


def _fs_path_from_site_path(path: str) -> str:
    return os.path.join(REPO_ROOT, path.lstrip("/").replace("/", os.sep))


def _load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _validate_watch_sources(entity: Dict[str, Any], label: str, issues: List[str]) -> None:
    watch_sources = entity.get("watch_sources")
    if watch_sources in (None, ""):
        return
    if not isinstance(watch_sources, list):
        issues.append(f"{label} watch_sources must be a list")
        return
    seen = set()
    for idx, row in enumerate(watch_sources):
        if not isinstance(row, dict):
            issues.append(f"{label} watch_sources[{idx}] must be an object")
            continue
        for field in REQUIRED_WATCH_SOURCE_FIELDS:
            if not str(row.get(field) or "").strip():
                issues.append(f"{label} watch_sources[{idx}] missing {field}")
        href = str(row.get("href") or "").strip()
        if href and not (href.startswith("http://") or href.startswith("https://") or href.startswith("/")):
            issues.append(f"{label} watch_sources[{idx}] invalid href")
        key = str(row.get("key") or "").strip()
        if key:
            if key in seen:
                issues.append(f"{label} duplicate watch_sources key={key}")
            seen.add(key)


def main() -> int:
    log_path, logf = _log_open()
    try:
        _log(logf, f"[qa_pipeline_integrity] START repo_root={REPO_ROOT}")
        _log(logf, f"[qa_pipeline_integrity] data_json={DATA_JSON}")
        _log(logf, f"[qa_pipeline_integrity] inputs_json={INPUTS_JSON}")
        _log(logf, f"[qa_pipeline_integrity] availability_json={AVAILABILITY_JSON}")
        _log(logf, f"[qa_pipeline_integrity] log={log_path}")

        if not os.path.isfile(DATA_JSON):
            _log(logf, f"[qa_pipeline_integrity] ERROR missing file: {DATA_JSON}")
            return 2
        if not os.path.isfile(INPUTS_JSON):
            _log(logf, f"[qa_pipeline_integrity] ERROR missing file: {INPUTS_JSON}")
            return 2

        data = _load_json(DATA_JSON)
        inp = _load_json(INPUTS_JSON)
        cfg = _load_json(WEB_CONFIG) if os.path.isfile(WEB_CONFIG) else {}
        workflow_text = _load_text(WORKFLOW_YML) if os.path.isfile(WORKFLOW_YML) else ""
        pipeline_runner_text = _load_text(PIPELINE_RUNNER) if os.path.isfile(PIPELINE_RUNNER) else ""
        fetch_tmdb_text = _load_text(FETCH_TMDB) if os.path.isfile(FETCH_TMDB) else ""
        availability_lib_text = _load_text(AVAILABILITY_LIB) if os.path.isfile(AVAILABILITY_LIB) else ""

        shows = data.get("shows", []) or []
        movies = data.get("movies", []) or []
        tv_inp = inp.get('tv', []) or inp.get('shows', []) or []
        mv_inp = inp.get("movies", []) or []
        data_errors = data.get("errors") if isinstance(data.get("errors"), list) else []
        expected_missing_movie_ids = {
            _as_int(err.get("tmdb_id"))
            for err in data_errors
            if isinstance(err, dict) and str(err.get("media") or "").strip() == "movie" and str(err.get("type") or "").strip() in {"tmdb_error", "tmdb_not_found"}
        }
        expected_missing_show_ids = {
            _as_int(err.get("tmdb_id"))
            for err in data_errors
            if isinstance(err, dict) and str(err.get("media") or "").strip() == "show" and str(err.get("type") or "").strip() in {"tmdb_error", "tmdb_not_found"}
        }
        trakt_meta = ((data.get("metadata") or {}).get("trakt_public_enrichment") or {}) if isinstance(data.get("metadata"), dict) else {}
        trakt_not_found = _as_int(((trakt_meta.get("counts") or {}) if isinstance(trakt_meta.get("counts"), dict) else {}).get("not_found"))

        # Core counts
        checks: List[Tuple[str, bool, str]] = []
        checks.append(("top_level_keys", isinstance(shows, list) and isinstance(movies, list), "data.json must contain shows[] and movies[] lists"))
        checks.append(("count_tv_matches_inputs", len(shows) + len(expected_missing_show_ids) == len(tv_inp), f"shows count mismatch after known upstream misses: data={len(shows)} inputs_json={len(tv_inp)} missing_expected={len(expected_missing_show_ids)}"))
        checks.append(("count_movies_matches_inputs", len(movies) + len(expected_missing_movie_ids) == len(mv_inp), f"movies count mismatch after known upstream misses: data={len(movies)} inputs_json={len(mv_inp)} missing_expected={len(expected_missing_movie_ids)}"))
        builder = (data.get("meta") or {}).get("builder") or {}
        checks.append(("builder_canonical_input", str(builder.get("canonical_input") or "") == "data/inputs.json", "data.meta.builder.canonical_input must be data/inputs.json"))
        checks.append(("builder_canonical_output", str(builder.get("canonical_output") or "") == "data/data.json", "data.meta.builder.canonical_output must be data/data.json"))
        checks.append(("workflow_uses_canonical_runner", "run_pipeline_tmdb_trakt.py" in workflow_text, "build-data workflow must run scripts/run_pipeline_tmdb_trakt.py"))
        checks.append(("pipeline_runs_integrity_qa", "qa_pipeline_integrity.py" in pipeline_runner_text, "run_pipeline_tmdb_trakt.py must run qa_pipeline_integrity.py"))
        legacy_markers = ["streaming_services", "inputs_parsed.json", "tv_list.txt", "movies_list.txt", "live_tv_list.txt"]
        legacy_hits = []
        for marker in legacy_markers:
            if marker in fetch_tmdb_text:
                legacy_hits.append(f"fetch_tmdb.py:{marker}")
            if marker in availability_lib_text:
                legacy_hits.append(f"availability_status_lib.py:{marker}")
        checks.append(("legacy_production_refs_removed", len(legacy_hits) == 0, f"legacy refs present in active production files: {', '.join(legacy_hits) if legacy_hits else 'none'}"))

        # Missing trakt ids (post-trakt run should usually be 0/0)
        ms = _count_missing_trakt(shows)
        mm = _count_missing_trakt(movies)
        checks.append(("missing_trakt_id_shows_bounded", ms <= trakt_not_found, f"shows missing trakt_id={ms} must not exceed trakt not_found={trakt_not_found}"))
        checks.append(("missing_trakt_id_movies_bounded", mm <= trakt_not_found, f"movies missing trakt_id={mm} must not exceed trakt not_found={trakt_not_found}"))

        # Ensure every item has a tmdb_id and title
        def _req_fields(items: List[Dict[str, Any]], label: str) -> List[str]:
            errs: List[str] = []
            for i, x in enumerate(items):
                if not _as_int(x.get("tmdb_id")):
                    errs.append(f"{label}[{i}] missing/invalid tmdb_id")
                t = (x.get("title") or "").strip()
                if not t:
                    errs.append(f"{label}[{i}] missing title")
            return errs

        field_errs = _req_fields(shows, "shows") + _req_fields(movies, "movies")
        checks.append(("required_fields_present", len(field_errs) == 0, f"{len(field_errs)} items missing required fields (tmdb_id/title)"))

        # Spot-check: inputs_json tmdb_id set should match output tmdb_id set
        out_tv_ids = set(_index_by_tmdb(shows).keys())
        inp_tv_ids = set(_index_by_tmdb(tv_inp).keys())
        out_mv_ids = set(_index_by_tmdb(movies).keys())
        inp_mv_ids = set(_index_by_tmdb(mv_inp).keys())

        tv_missing = sorted(list(inp_tv_ids - out_tv_ids))
        mv_missing = sorted(list(inp_mv_ids - out_mv_ids))
        checks.append(("tmdb_id_set_tv_matches", set(tv_missing).issubset(expected_missing_show_ids), f"unexpected missing tv tmdb_id(s): {sorted(set(tv_missing) - expected_missing_show_ids)[:50]}"))
        checks.append(("tmdb_id_set_movies_matches", set(mv_missing).issubset(expected_missing_movie_ids), f"unexpected missing movie tmdb_id(s): {sorted(set(mv_missing) - expected_missing_movie_ids)[:50]}"))

        # Asset drift checks (local files for poster/backdrop/still paths)
        image_cache = cfg.get("image_cache") if isinstance(cfg, dict) else {}
        cache_enabled = bool(image_cache.get("enabled", True)) if isinstance(image_cache, dict) else True
        missing_local_files: List[str] = []
        missing_local_fields: List[str] = []
        null_still_paths = 0

        def _track_local(path_val: Any, ctx: str) -> None:
            p = (path_val or "").strip()
            if not _is_local_asset(p):
                return
            fs = _fs_path_from_site_path(p)
            if not os.path.isfile(fs):
                missing_local_files.append(f"{ctx} -> {p}")

        def _track_expected_local(tmdb_path: Any, local_path: Any, ctx: str) -> None:
            tp = (tmdb_path or "").strip()
            lp = (local_path or "").strip()
            if tp and not lp:
                missing_local_fields.append(ctx)

        for s in shows:
            _track_expected_local(s.get("poster_path"), s.get("poster_local"), f"show {s.get('tmdb_id')} poster_local missing")
            _track_expected_local(s.get("backdrop_path"), s.get("backdrop_local"), f"show {s.get('tmdb_id')} backdrop_local missing")
            _track_local(s.get("poster_local"), f"show {s.get('tmdb_id')} poster_local missing file")
            _track_local(s.get("backdrop_local"), f"show {s.get('tmdb_id')} backdrop_local missing file")
            for se in s.get("seasons") or []:
                _track_expected_local(se.get("poster_path"), se.get("poster_local"), f"season {se.get('tmdb_season_id')} poster_local missing")
                _track_local(se.get("poster_local"), f"season {se.get('tmdb_season_id')} poster_local missing file")
                for ep in se.get("episodes") or []:
                    if not (ep.get("still_path") or "").strip():
                        null_still_paths += 1
                    _track_expected_local(ep.get("still_path"), ep.get("still_local"), f"episode {ep.get('tmdb_episode_id')} still_local missing")
                    _track_local(ep.get("still_local"), f"episode {ep.get('tmdb_episode_id')} still_local missing file")

        for m in movies:
            _track_expected_local(m.get("poster_path"), m.get("poster_local"), f"movie {m.get('tmdb_id')} poster_local missing")
            _track_expected_local(m.get("backdrop_path"), m.get("backdrop_local"), f"movie {m.get('tmdb_id')} backdrop_local missing")
            _track_local(m.get("poster_local"), f"movie {m.get('tmdb_id')} poster_local missing file")
            _track_local(m.get("backdrop_local"), f"movie {m.get('tmdb_id')} backdrop_local missing file")

        if cache_enabled:
            checks.append(("missing_local_asset_files_zero", len(missing_local_files) == 0, f"missing local asset files: {len(missing_local_files)}"))
            checks.append(("missing_local_asset_fields_zero", len(missing_local_fields) == 0, f"missing *_local fields when *_path present: {len(missing_local_fields)}"))

        availability_doc = _load_json(AVAILABILITY_JSON) if os.path.isfile(AVAILABILITY_JSON) else None
        checks.append(("availability_source_exists", isinstance(availability_doc, dict), "data/watch_source_availability.json must exist and parse"))

        availability_missing: List[str] = []
        availability_invalid: List[str] = []

        def _check_availability(entity: Dict[str, Any], label: str) -> None:
            status = str(entity.get("availability_status") or "").strip()
            if status not in ALLOWED_AVAILABILITY:
                availability_invalid.append(f"{label} invalid availability_status={status!r}")
            if not str(entity.get("availability_checked_at") or "").strip():
                availability_missing.append(f"{label} missing availability_checked_at")
            if not str(entity.get("availability_source") or "").strip():
                availability_missing.append(f"{label} missing availability_source")
            if not str(entity.get("availability_reason") or "").strip():
                availability_missing.append(f"{label} missing availability_reason")

        for s in shows:
            _check_availability(s, f"show {s.get('tmdb_id')}")
            _validate_watch_sources(s, f"show {s.get('tmdb_id')}", availability_missing)
            for se in s.get("seasons") or []:
                _check_availability(se, f"season {s.get('tmdb_id')}:{se.get('season_number')}")
                _validate_watch_sources(se, f"season {s.get('tmdb_id')}:{se.get('season_number')}", availability_missing)
                for ep in se.get("episodes") or []:
                    _check_availability(ep, f"episode {s.get('tmdb_id')}:{ep.get('season_number')}:{ep.get('episode_number')}")
                    _validate_watch_sources(ep, f"episode {s.get('tmdb_id')}:{ep.get('season_number')}:{ep.get('episode_number')}", availability_missing)

        for m in movies:
            _check_availability(m, f"movie {m.get('tmdb_id')}")
            _validate_watch_sources(m, f"movie {m.get('tmdb_id')}", availability_missing)

        checks.append(("availability_fields_present", len(availability_missing) == 0, f"entities missing availability fields: {len(availability_missing)}"))
        checks.append(("availability_status_enum_valid", len(availability_invalid) == 0, f"entities with invalid availability_status: {len(availability_invalid)}"))

        ok = True
        for name, passed, detail in checks:
            _log(logf, f"[qa_pipeline_integrity] CHECK {name} => {'OK' if passed else 'FAIL'} | {detail}")
            ok = ok and passed

        report = {
            "generated_utc": _utc_ts(),
            "repo_root": REPO_ROOT,
            "data_json": DATA_JSON,
            "inputs_json": INPUTS_JSON,
            "counts": {
                "shows": len(shows),
                "movies": len(movies),
                "inputs_tv": len(tv_inp),
                "inputs_movies": len(mv_inp),
                "missing_trakt_id_shows": ms,
                "missing_trakt_id_movies": mm,
                "trakt_not_found": trakt_not_found,
            },
            "tmdb_id_diffs": {
                "tv_missing_in_data_json": tv_missing[:50],
                "movies_missing_in_data_json": mv_missing[:50],
                "expected_missing_show_ids": sorted(expected_missing_show_ids)[:50],
                "expected_missing_movie_ids": sorted(expected_missing_movie_ids)[:50],
            },
            "field_errors_sample": field_errs[:50],
            "asset_drift": {
                "cache_enabled": cache_enabled,
                "missing_local_files": missing_local_files[:50],
                "missing_local_fields": missing_local_fields[:50],
                "null_episode_still_paths": null_still_paths,
            },
            "availability": {
                "availability_source_exists": isinstance(availability_doc, dict),
                "missing_fields_sample": availability_missing[:50],
                "invalid_status_sample": availability_invalid[:50],
            },
            "checks": [{"name": n, "passed": p, "detail": d} for (n, p, d) in checks],
            "result": "OK" if ok else "FAIL",
        }

        rep_path = os.path.join(REPORT_DIR, f"_qa_pipeline_integrity_{_local_ts_compact()}.json")
        with open(rep_path, "w", encoding="utf-8", errors="replace", newline="\n") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)

        _log(logf, f"[qa_pipeline_integrity] WROTE report={rep_path}")
        _log(logf, f"[qa_pipeline_integrity] END result={'OK' if ok else 'FAIL'}")

        return 0 if ok else 3

    finally:
        try:
            logf.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
