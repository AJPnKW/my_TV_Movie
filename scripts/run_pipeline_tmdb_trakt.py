#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/run_pipeline_tmdb_trakt.py
# [PROJECT] my_TV_Movie
# [ROLE]    One-command local runner: TMDB build -> Trakt enrich
# [VERSION] v1.5.0
# [UPDATED] 2026-03-29_00-00-00
# [BUILD]   15.00.00
# ==============================================================================
from __future__ import annotations

import datetime as _dt
import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
LOGS_DIR = REPO_ROOT / "logs"

FETCH_TMDB = SCRIPTS_DIR / "fetch_tmdb.py"
FETCH_TRAKT = SCRIPTS_DIR / "fetch_trakt.py"
FETCH_TMDB_ASSETS = SCRIPTS_DIR / "fetch_tmdb_assets.py"
SELF_HEAL_ASSET_METADATA = SCRIPTS_DIR / "self_heal_asset_metadata.py"
OPTIMIZE_RUNTIME_ASSETS = SCRIPTS_DIR / "optimize_runtime_assets.py"
VALIDATE_AVAILABILITY = SCRIPTS_DIR / "validate_availability_overlay.py"
ENRICH_AVAILABILITY = SCRIPTS_DIR / "enrich_data_with_availability.py"
BUILD_SPLIT_RUNTIME = SCRIPTS_DIR / "build_split_runtime.py"
QA_AVAILABILITY = SCRIPTS_DIR / "qa_availability_status.py"
QA_AVAILABILITY_PHASE2 = SCRIPTS_DIR / "qa_availability_phase2.py"
VALIDATE_SECRET_DRIFT = SCRIPTS_DIR / "validate_secret_name_drift.py"
VALIDATE_RUNTIME_ASSETS = SCRIPTS_DIR / "validate_runtime_assets.py"
VALIDATE_RUNTIME_CATALOG = SCRIPTS_DIR / "validate_runtime_catalog_integrity.py"
QA_PIPELINE_INTEGRITY = SCRIPTS_DIR / "qa_pipeline_integrity.py"


def _ts() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _tail(path: Path, n: int = 40) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except Exception:
        return ""


def _latest_log(glob_pat: str) -> Path | None:
    try:
        hits = sorted(LOGS_DIR.glob(glob_pat), key=lambda p: p.stat().st_mtime, reverse=True)
        return hits[0] if hits else None
    except Exception:
        return None


def _run_one(label: str, script_path: Path, *extra_args: str) -> int:
    py = Path(sys.executable)
    print(f"\n[{label}] RUN {script_path}")
    if not script_path.exists():
        print(f"[{label}] ERROR missing: {script_path}")
        return 2
    p = subprocess.run([str(py), str(script_path), *extra_args], cwd=str(REPO_ROOT))
    print(f"[{label}] exit_code={p.returncode}")
    return int(p.returncode)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh-existing-trakt",
        action="store_true",
        default=os.environ.get("PIPELINE_REFRESH_EXISTING_TRAKT", "").strip().lower() in {"1", "true", "yes"},
        help="Recheck existing Trakt IDs instead of resolving only missing IDs.",
    )
    parser.add_argument(
        "--force-full-tmdb",
        action="store_true",
        default=os.environ.get("PIPELINE_FORCE_FULL_TMDB", "").strip().lower() in {"1", "true", "yes"},
        help="Force a full TMDB rebuild instead of reusing unchanged generated rows.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Required scope file (canonical)
    inputs_json = REPO_ROOT / 'data' / 'inputs.json'
    if not inputs_json.exists():
        print(f"[INIT] ERROR missing scope file: {inputs_json}")
        return 2

    started = _ts()
    tmdb_args = ("--force-full-refresh",) if args.force_full_tmdb else ()
    rc = _run_one("TMDB", FETCH_TMDB, *tmdb_args)
    if rc != 0:
        print("\n--- SUMMARY ---")
        print(f"started : {started}")
        print(f"finished: {_ts()}")
        return rc

    trakt_args = ("--refresh-existing",) if args.refresh_existing_trakt else ()
    rc = _run_one("TRAKT", FETCH_TRAKT, *trakt_args)
    if rc != 0:
        print("\n--- SUMMARY ---")
        print(f"started : {started}")
        print(f"finished: {_ts()}")
        return rc

    rc = _run_one("TMDB_ASSETS", FETCH_TMDB_ASSETS)
    if rc != 0:
        print("\n--- SUMMARY ---")
        print(f"started : {started}")
        print(f"finished: {_ts()}")
        return rc

    rc = _run_one("SECRET_DRIFT_VALIDATE", VALIDATE_SECRET_DRIFT)
    if rc != 0:
        print("\n--- SUMMARY ---")
        print(f"started : {started}")
        print(f"finished: {_ts()}")
        return rc

    rc = _run_one("ASSET_METADATA_SELF_HEAL", SELF_HEAL_ASSET_METADATA, "--fetch-missing")
    if rc != 0:
        print("\n--- SUMMARY ---")
        print(f"started : {started}")
        print(f"finished: {_ts()}")
        return rc

    rc = _run_one("RUNTIME_ASSET_OPTIMIZE", OPTIMIZE_RUNTIME_ASSETS)
    if rc != 0:
        print("\n--- SUMMARY ---")
        print(f"started : {started}")
        print(f"finished: {_ts()}")
        return rc

    rc = _run_one("AVAILABILITY_VALIDATE", VALIDATE_AVAILABILITY)
    if rc != 0:
        print("\n--- SUMMARY ---")
        print(f"started : {started}")
        print(f"finished: {_ts()}")
        return rc

    rc = _run_one("AVAILABILITY_ENRICH", ENRICH_AVAILABILITY)
    if rc != 0:
        print("\n--- SUMMARY ---")
        print(f"started : {started}")
        print(f"finished: {_ts()}")
        return rc

    rc = _run_one("SPLIT_RUNTIME_BUILD", BUILD_SPLIT_RUNTIME)
    if rc != 0:
        print("\n--- SUMMARY ---")
        print(f"started : {started}")
        print(f"finished: {_ts()}")
        return rc

    rc = _run_one("AVAILABILITY_QA", QA_AVAILABILITY)
    if rc != 0:
        finished = _ts()
        print("\n--- SUMMARY ---")
        print(f"started : {started}")
        print(f"finished: {finished}")
        return rc

    rc = _run_one("AVAILABILITY_PHASE2_QA", QA_AVAILABILITY_PHASE2)
    if rc != 0:
        finished = _ts()
        print("\n--- SUMMARY ---")
        print(f"started : {started}")
        print(f"finished: {finished}")
        return rc

    rc = _run_one("RUNTIME_ASSETS_VALIDATE", VALIDATE_RUNTIME_ASSETS)
    if rc != 0:
        finished = _ts()
        print("\n--- SUMMARY ---")
        print(f"started : {started}")
        print(f"finished: {finished}")
        return rc

    rc = _run_one("RUNTIME_CATALOG_VALIDATE", VALIDATE_RUNTIME_CATALOG)
    if rc != 0:
        finished = _ts()
        print("\n--- SUMMARY ---")
        print(f"started : {started}")
        print(f"finished: {finished}")
        return rc

    rc = _run_one("PIPELINE_INTEGRITY_QA", QA_PIPELINE_INTEGRITY)
    finished = _ts()

    tmdb_log = _latest_log("fetch_tmdb.*.log.txt")
    trakt_log = _latest_log("fetch_trakt_*.log.txt")

    print("\n--- SUMMARY ---")
    print(f"started : {started}")
    print(f"finished: {finished}")
    print(f"tmdb_log : {tmdb_log}" if tmdb_log else "tmdb_log : (not found)")
    print(f"trakt_log: {trakt_log}" if trakt_log else "trakt_log: (not found)")

    if tmdb_log:
        print("\n--- TMDB LOG (tail) ---")
        print(_tail(tmdb_log, 15))
    if trakt_log:
        print("\n--- TRAKT LOG (tail) ---")
        print(_tail(trakt_log, 15))

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
