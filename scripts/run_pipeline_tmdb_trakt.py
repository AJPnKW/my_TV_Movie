#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/run_pipeline_tmdb_trakt.py
# [PROJECT] my_TV_Movie
# [ROLE]    One-command local runner: TMDB build -> Trakt enrich
# [VERSION] v1.2.0
# [UPDATED] 2025-12-29_00-00-00
# [BUILD]   14.01.08
# ==============================================================================
from __future__ import annotations

import datetime as _dt
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
LOGS_DIR = REPO_ROOT / "logs"

FETCH_TMDB = SCRIPTS_DIR / "fetch_tmdb.py"
FETCH_TRAKT = SCRIPTS_DIR / "fetch_trakt.py"


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


def _run_one(label: str, script_path: Path) -> int:
    py = Path(sys.executable)
    print(f"\n[{label}] RUN {script_path}")
    if not script_path.exists():
        print(f"[{label}] ERROR missing: {script_path}")
        return 2
    p = subprocess.run([str(py), str(script_path)], cwd=str(REPO_ROOT))
    print(f"[{label}] exit_code={p.returncode}")
    return int(p.returncode)


def main() -> int:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    started = _ts()
    rc = _run_one("TMDB", FETCH_TMDB)
    if rc != 0:
        print("\n--- SUMMARY ---")
        print(f"started : {started}")
        print(f"finished: {_ts()}")
        return rc

    rc = _run_one("TRAKT", FETCH_TRAKT)
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
