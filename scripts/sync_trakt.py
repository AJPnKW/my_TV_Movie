#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/sync_trakt.py
# [PROJECT] my_TV_Movie
# [ROLE]    Deterministic orchestration wrapper for Trakt sync (invokes fetch_trakt.py)
# [VERSION] v1.4.0
# [UPDATED] 2025-12-19_00-00-00
# [BUILD]   14.01.05
#
# [INPUTS]
#   - scripts/fetch_trakt.py (authoritative Trakt sync implementation)
#   - web/config.json        (read by fetch_trakt.py)
#   - data/data.json         (read + updated by fetch_trakt.py)
#
# [OUTPUTS]
#   - data/data.json (via fetch_trakt.py)
#   - data/last_refresh_trakt.txt (via fetch_trakt.py)
#   - logs/sync_trakt_YYYY-MM-DD_HHMMSS.log.txt (this wrapper)
#   - logs/fetch_trakt_YYYY-MM-DD_HHMMSS.log.txt (via fetch_trakt.py)
#
# [ENV REQUIRED]
#   - TRAKT_CLIENT_ID
#   - TRAKT_USERNAME
#
# [ENV OPTIONAL]
#   - TRAKT_ACCESS_TOKEN
#
# [BINDING RULES APPLIED]
#   - No invented files/folders/modules.
#   - Errors must be surfaced (visible via console + log; no silent failures).
#   - data.json is not edited manually; script-driven updates only.
#   - Canonical assets: no deprecated "image/" references introduced here.
#
# [WHY THIS EXISTS]
#   - Provides a stable, single command entry for “Trakt sync” while keeping all
#     actual Trakt logic inside scripts/fetch_trakt.py.
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
FETCH_TRAKT = SCRIPTS_DIR / "fetch_trakt.py"

DATA_JSON = REPO_ROOT / "data" / "data.json"
LOGS_DIR = REPO_ROOT / "logs"


def _now_stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")


def _log_path() -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR / f"sync_trakt_{_now_stamp()}.log.txt"


def _write_line(fp, s: str) -> None:
    fp.write(s + "\n")
    fp.flush()


def _required_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing required env var: {name}")
    return v.strip()


def _check_prereqs() -> None:
    if not FETCH_TRAKT.exists():
        raise FileNotFoundError(f"Missing required script: {FETCH_TRAKT}")
    if not DATA_JSON.exists():
        raise FileNotFoundError(f"Missing required data file: {DATA_JSON} (run fetch_tmdb.py first)")
    _required_env("TRAKT_CLIENT_ID")
    _required_env("TRAKT_USERNAME")


def _run_fetch_trakt(log_fp) -> int:
    cmd = [sys.executable, str(FETCH_TRAKT)]
    _write_line(log_fp, f"[sync_trakt] CMD: {' '.join(cmd)}")

    # Stream stdout/stderr to console AND log (no silent failures)
    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip("\n")
        print(line)
        _write_line(log_fp, line)

    return proc.wait()


def main() -> int:
    lp = _log_path()
    with lp.open("w", encoding="utf-8") as log_fp:
        _write_line(log_fp, f"[sync_trakt] START { _dt.datetime.now().isoformat(timespec='seconds') }")
        _write_line(log_fp, f"[sync_trakt] repo_root={REPO_ROOT}")
        _write_line(log_fp, f"[sync_trakt] python={sys.executable}")
        _write_line(log_fp, f"[sync_trakt] log={lp}")

        try:
            _check_prereqs()
        except Exception as e:
            msg = f"[sync_trakt] ERROR prereq: {e}"
            print(msg, file=sys.stderr)
            _write_line(log_fp, msg)
            _write_line(log_fp, "[sync_trakt] END (failed prereq)")
            try:
                input("Press Enter to close...")
            except Exception:
                pass
            return 2

        try:
            rc = _run_fetch_trakt(log_fp)
        except Exception as e:
            msg = f"[sync_trakt] ERROR run: {e}"
            print(msg, file=sys.stderr)
            _write_line(log_fp, msg)
            _write_line(log_fp, "[sync_trakt] END (run error)")
            try:
                input("Press Enter to close...")
            except Exception:
                pass
            return 3

        _write_line(log_fp, f"[sync_trakt] fetch_trakt_exit_code={rc}")
        _write_line(log_fp, "[sync_trakt] END")

    try:
        input("Press Enter to close...")
    except Exception:
        pass

    return int(rc)


if __name__ == "__main__":
    raise SystemExit(main())
