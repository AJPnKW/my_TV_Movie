#!/usr/bin/env python3
# ======================================================================================
# sync_trakt.py
#
# Wrapper to run fetch_trakt.py with the same repository conventions:
# - Logs to repo_root/logs
# - Writes status to log
# - No schema changes here (pipeline scripts own data.json structure)
#
# NOTE:
#   This script currently "syncs" by executing fetch_trakt.py.
#   (i.e., it enriches/looks up trakt ids and related info already supported by fetch_trakt.py)
# ======================================================================================

from __future__ import annotations

import datetime as _dt
import os
import subprocess
import sys
from pathlib import Path

# ----------------------------
# Repo paths (derived)
# ----------------------------
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parent.parent  # .../my_TV_Movie
LOGS_DIR = REPO_ROOT / "logs"

FETCH_TRAKT = REPO_ROOT / "scripts" / "fetch_trakt.py"

DATA_DIR = REPO_ROOT / "data"
DATA_JSON = DATA_DIR / "data.json"


def _now_stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _log_path() -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR / f"sync_trakt_{_now_stamp()}.log.txt"


def _write_line(fp, s: str) -> None:
    fp.write(s + "\n")
    fp.flush()


def _check_prereqs() -> None:
    missing = []
    if not FETCH_TRAKT.exists():
        missing.append(str(FETCH_TRAKT))
    if not DATA_JSON.exists():
        # Not strictly required for fetch_trakt (depends on implementation),
        # but in this repo it is expected that pipeline produces/uses data.json.
        missing.append(str(DATA_JSON))

    if missing:
        raise FileNotFoundError("Missing required file(s): " + ", ".join(missing))


def _run_fetch_trakt(log_fp) -> int:
    cmd = [sys.executable, str(FETCH_TRAKT)]
    _write_line(log_fp, f"[sync_trakt] exec: {' '.join(cmd)}")

    # Inherit current environment (API_TRAKT_ID / API_TRAKT_KEY etc.)
    p = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    _write_line(log_fp, "[sync_trakt] --- fetch_trakt output begin ---")
    _write_line(log_fp, p.stdout.rstrip("\n"))
    _write_line(log_fp, "[sync_trakt] --- fetch_trakt output end ---")
    _write_line(log_fp, f"[sync_trakt] fetch_trakt exit_code={p.returncode}")
    return int(p.returncode)


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument(
        "--pause",
        action="store_true",
        help="Pause for Enter before exit (useful when double-clicking the script).",
    )
    args = ap.parse_args()

    lp = _log_path()
    with lp.open("w", encoding="utf-8") as log_fp:
        _write_line(log_fp, f"[sync_trakt] START {_dt.datetime.now().isoformat(timespec='seconds')}")
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
            if args.pause:
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
            _write_line(log_fp, "[sync_trakt] END (failed run)")
            if args.pause:
                try:
                    input("Press Enter to close...")
                except Exception:
                    pass
            return 3

        _write_line(log_fp, f"[sync_trakt] END exit_code={rc}")

    if args.pause:
        try:
            input("Press Enter to close...")
        except Exception:
            pass

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
