#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/sync_trakt.py
# [PROJECT] my_TV_Movie
# [ROLE]    Wrapper runner for Trakt enrichment (exec fetch_trakt.py)
# [VERSION] v1.1.0
# [UPDATED] 2025-12-29_00-00-00
# [BUILD]   14.01.08
# ==============================================================================
from __future__ import annotations

import datetime as _dt
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = REPO_ROOT / "logs"
FETCH_TRAKT = REPO_ROOT / "scripts" / "fetch_trakt.py"


def _now() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def main() -> int:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"sync_trakt_{_stamp()}.log.txt"
    py = Path(sys.executable)

    with log_path.open("w", encoding="utf-8") as f:
        def w(line: str) -> None:
            f.write(line + "\n")
            f.flush()

        w(f"[sync_trakt] START {_now()}")
        w(f"[sync_trakt] repo_root={REPO_ROOT}")
        w(f"[sync_trakt] python={py}")
        w(f"[sync_trakt] log={log_path}")
        w(f"[sync_trakt] exec: {py} {FETCH_TRAKT}")

        if not FETCH_TRAKT.exists():
            w(f"[sync_trakt] ERROR missing script: {FETCH_TRAKT}")
            return 2

        try:
            p = subprocess.run(
                [str(py), str(FETCH_TRAKT)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except Exception as e:
            w(f"[sync_trakt] ERROR exec failed: {e}")
            return 3

        w("[sync_trakt] --- fetch_trakt output begin ---")
        if p.stdout:
            w(p.stdout.rstrip("\n"))
        if p.stderr:
            w(p.stderr.rstrip("\n"))
        w("[sync_trakt] --- fetch_trakt output end ---")
        w(f"[sync_trakt] fetch_trakt exit_code={p.returncode}")
        w(f"[sync_trakt] END exit_code={p.returncode}")

    return int(p.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
