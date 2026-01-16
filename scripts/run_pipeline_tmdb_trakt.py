#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/run_pipeline_tmdb_trakt.py
# [PROJECT] my_TV_Movie
# [ROLE]    Local wrapper to run TMDB -> Trakt pipeline in correct order
# [VERSION] v1.0.0
# [UPDATED] 2025-12-29_22-30-00
# [BUILD]   14.01.07
#
# Usage:
#   cd C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie
#   .\.venv\Scripts\python.exe .\scripts\run_pipeline_tmdb_trakt.py
#
# Notes:
#   - Exits non-zero if any stage fails
#   - Prints paths to the newest TMDB/Trakt logs
# ==============================================================================
from __future__ import annotations

import sys
import subprocess
import datetime as _dt
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
LOGS = REPO_ROOT / "logs"

TMDB = SCRIPTS / "fetch_tmdb.py"
TRAKT = SCRIPTS / "fetch_trakt.py"

def _run(label: str, script: Path) -> int:
    print(f"\n[{label}] RUN {script}")
    cmd = [sys.executable, str(script)]
    p = subprocess.run(cmd, cwd=str(REPO_ROOT))
    print(f"[{label}] exit_code={p.returncode}")
    return p.returncode

def _newest_log(glob_pat: str) -> str:
    if not LOGS.exists():
        return ""
    hits = sorted([p for p in LOGS.glob(glob_pat)], key=lambda p: p.stat().st_mtime, reverse=True)
    return str(hits[0]) if hits else ""

def main() -> int:
    started = _dt.datetime.now()
    rc1 = _run("TMDB", TMDB)
    if rc1 != 0:
        return rc1

    rc2 = _run("TRAKT", TRAKT)
    if rc2 != 0:
        return rc2

    finished = _dt.datetime.now()

    print("\n--- SUMMARY ---")
    print("started : " + started.strftime("%Y-%m-%d %H:%M:%S"))
    print("finished: " + finished.strftime("%Y-%m-%d %H:%M:%S"))
    print("tmdb_log : " + _newest_log("fetch_tmdb.*.log.txt"))
    print("trakt_log: " + _newest_log("fetch_trakt_*.log.txt"))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
