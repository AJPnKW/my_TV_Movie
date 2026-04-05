#!/usr/bin/env python3
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

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
        watch_me_runtime_text = _read_text(WATCH_ME_RUNTIME)

        input_tv = inputs.get("tv") if isinstance(inputs, dict) else []
        input_movies = inputs.get("movies") if isinstance(inputs, dict) else []
        data_shows = data.get("shows") if isinstance(data, dict) else []
        data_movies = data.get("movies") if isinstance(data, dict) else []
        index_shows = index.get("shows") if isinstance(index, dict) else []
        index_movies = index.get("movies") if isinstance(index, dict) else []
        detail_files = list(DETAIL_DIR.glob("*.json"))
        calendar_days = calendar.get("days") if isinstance(calendar, dict) else {}
        expected_missing = {
            int(err.get("tmdb_id") or 0)
            for err in (data.get("errors") or [])
            if isinstance(err, dict) and str(err.get("type") or "").strip() in {"tmdb_error", "tmdb_not_found"}
        }

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

        _check("shows_present_when_tv_inputs_present", isinstance(index_shows, list) and len(index_shows) >= max(0, len(input_tv) - len(expected_missing)), f"catalog_index shows={len(index_shows) if isinstance(index_shows, list) else 0} inputs_tv={len(input_tv) if isinstance(input_tv, list) else 0}", checks, logf)
        _check("movies_present_when_movie_inputs_present", isinstance(index_movies, list) and len(index_movies) >= max(0, len(input_movies) - len(expected_missing)), f"catalog_index movies={len(index_movies) if isinstance(index_movies, list) else 0} inputs_movies={len(input_movies) if isinstance(input_movies, list) else 0}", checks, logf)
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
                "inputs_tv": len(input_tv) if isinstance(input_tv, list) else 0,
                "inputs_movies": len(input_movies) if isinstance(input_movies, list) else 0,
                "data_shows": len(data_shows) if isinstance(data_shows, list) else 0,
                "data_movies": len(data_movies) if isinstance(data_movies, list) else 0,
                "index_shows": len(index_shows) if isinstance(index_shows, list) else 0,
                "index_movies": len(index_movies) if isinstance(index_movies, list) else 0,
                "detail_files": len(detail_files),
                "calendar_days": len(calendar_days) if isinstance(calendar_days, dict) else 0,
            },
            "checks": [{"name": name, "passed": passed, "detail": detail} for name, passed, detail in checks],
            "result": "OK" if ok else "FAIL",
        }
        report_path = REPORT_DIR / f"_qa_pipeline_integrity_{_local_ts()}.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        _log(logf, f"[qa_pipeline_integrity] report={report_path}")
        return 0 if ok else 3
    finally:
        logf.close()
        print(str(log_path))


if __name__ == "__main__":
    raise SystemExit(main())
