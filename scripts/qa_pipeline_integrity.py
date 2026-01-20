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
LOG_DIR = os.path.join(REPO_ROOT, "logs")
REPORT_DIR = os.path.join(REPO_ROOT, "reports")


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


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return json.load(fh)


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


def main() -> int:
    log_path, logf = _log_open()
    try:
        _log(logf, f"[qa_pipeline_integrity] START repo_root={REPO_ROOT}")
        _log(logf, f"[qa_pipeline_integrity] data_json={DATA_JSON}")
        _log(logf, f"[qa_pipeline_integrity] inputs_json={INPUTS_JSON}")
        _log(logf, f"[qa_pipeline_integrity] log={log_path}")

        if not os.path.isfile(DATA_JSON):
            _log(logf, f"[qa_pipeline_integrity] ERROR missing file: {DATA_JSON}")
            return 2
        if not os.path.isfile(INPUTS_JSON):
            _log(logf, f"[qa_pipeline_integrity] ERROR missing file: {INPUTS_JSON}")
            return 2

        data = _load_json(DATA_JSON)
        inp = _load_json(INPUTS_JSON)

        shows = data.get("shows", []) or []
        movies = data.get("movies", []) or []
        tv_inp = inp.get('tv', []) or inp.get('shows', []) or []
        mv_inp = inp.get("movies", []) or []

        # Core counts
        checks: List[Tuple[str, bool, str]] = []
        checks.append(("top_level_keys", isinstance(shows, list) and isinstance(movies, list), "data.json must contain shows[] and movies[] lists"))
        checks.append(("count_tv_matches_inputs", len(shows) == len(tv_inp), f"shows count mismatch: data={len(shows)} inputs_json={len(tv_inp)}"))
        checks.append(("count_movies_matches_inputs", len(movies) == len(mv_inp), f"movies count mismatch: data={len(movies)} inputs_json={len(mv_inp)}"))

        # Missing trakt ids (post-trakt run should usually be 0/0)
        ms = _count_missing_trakt(shows)
        mm = _count_missing_trakt(movies)
        checks.append(("missing_trakt_id_shows_zero", ms == 0, f"shows missing trakt_id: {ms}"))
        checks.append(("missing_trakt_id_movies_zero", mm == 0, f"movies missing trakt_id: {mm}"))

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
        checks.append(("tmdb_id_set_tv_matches", len(tv_missing) == 0, f"data.json missing {len(tv_missing)} tv tmdb_id(s) present in inputs_json"))
        checks.append(("tmdb_id_set_movies_matches", len(mv_missing) == 0, f"data.json missing {len(mv_missing)} movie tmdb_id(s) present in inputs_json"))

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
            },
            "tmdb_id_diffs": {
                "tv_missing_in_data_json": tv_missing[:50],
                "movies_missing_in_data_json": mv_missing[:50],
            },
            "field_errors_sample": field_errs[:50],
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
