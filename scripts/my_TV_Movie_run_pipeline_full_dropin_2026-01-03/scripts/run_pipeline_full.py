\
#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/run_pipeline_full.py
# [PROJECT] my_TV_Movie
# [ROLE]    Local wrapper: parse inputs -> TMDB -> Trakt -> QA (missing trakt ids)
# [VERSION] v1.0.0
# [UPDATED] 2026-01-03
# [BUILD]   14.01.07
# ==============================================================================
# Runs (in order):
#   1) scripts/parse_txt_to_json.py     (auto-sends Enter to satisfy pause)
#   2) scripts/fetch_tmdb.py
#   3) scripts/fetch_trakt.py
#   4) scripts/qa_missing_trakt_ids.py
#
# Output:
#   - writes wrapper log to: logs/run_pipeline_full_YYYY-MM-DD_HH-MM-SS.log.txt
#   - prints a short SUMMARY block
#
# Notes:
#   - Uses the same venv python you launched this script with.
#   - Safe to run repeatedly.
# ==============================================================================

from __future__ import annotations

import os
import sys
import subprocess
import datetime as _dt
from pathlib import Path

def _utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _local_stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def _repo_root() -> Path:
    # Resolve repo root as parent of /scripts (this file lives in /scripts)
    here = Path(__file__).resolve()
    return here.parent.parent

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _write_line(fp: Path, msg: str) -> None:
    fp.parent.mkdir(parents=True, exist_ok=True)
    with fp.open("a", encoding="utf-8", errors="replace") as f:
        f.write(msg.rstrip() + "\n")

def _run_step(
    label: str,
    py: Path,
    script_path: Path,
    logfp: Path,
    stdin_text: str | None = None,
) -> int:
    cmd = [str(py), str(script_path)]
    _write_line(logfp, f"{_utc_stamp()} | [{label}] RUN {' '.join(cmd)}")
    try:
        p = subprocess.run(
            cmd,
            cwd=str(_repo_root()),
            input=(stdin_text.encode("utf-8") if stdin_text is not None else None),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        out = p.stdout.decode("utf-8", errors="replace")
        for line in out.splitlines():
            _write_line(logfp, f"{_utc_stamp()} | [{label}] {line}")
        _write_line(logfp, f"{_utc_stamp()} | [{label}] exit_code={p.returncode}")
        return int(p.returncode)
    except Exception as e:
        _write_line(logfp, f"{_utc_stamp()} | [{label}] ERROR {type(e).__name__}: {e}")
        return 2

def main() -> int:
    repo = _repo_root()
    logs = repo / "logs"
    _ensure_dir(logs)

    py = Path(sys.executable).resolve()
    logfp = logs / f"run_pipeline_full_{_local_stamp()}.log.txt"

    parse = repo / "scripts" / "parse_txt_to_json.py"
    tmdb  = repo / "scripts" / "fetch_tmdb.py"
    trakt = repo / "scripts" / "fetch_trakt.py"
    qa    = repo / "scripts" / "qa_missing_trakt_ids.py"

    _write_line(logfp, f"{_utc_stamp()} | [init] repo_root={repo}")
    _write_line(logfp, f"{_utc_stamp()} | [init] python={py}")
    _write_line(logfp, f"{_utc_stamp()} | [init] log={logfp}")

    # Step 1: parse (auto press Enter if it pauses)
    rc_parse = _run_step("parse", py, parse, logfp, stdin_text="\n")

    # Step 2: tmdb
    rc_tmdb = _run_step("tmdb", py, tmdb, logfp)

    # Step 3: trakt
    rc_trakt = _run_step("trakt", py, trakt, logfp)

    # Step 4: QA
    rc_qa = 0
    if qa.exists():
        rc_qa = _run_step("qa_missing_trakt_ids", py, qa, logfp)
    else:
        _write_line(logfp, f"{_utc_stamp()} | [qa_missing_trakt_ids] SKIP (missing file)")

    worst = max(rc_parse, rc_tmdb, rc_trakt, rc_qa)

    print()
    print("--- SUMMARY ---")
    print(f"repo_root : {repo}")
    print(f"python    : {py}")
    print(f"log       : {logfp}")
    print(f"exit_codes: parse={rc_parse} tmdb={rc_tmdb} trakt={rc_trakt} qa={rc_qa}")
    print(f"RESULT    : {'OK' if worst == 0 else 'ERROR'} (exit_code={worst})")

    return worst

if __name__ == "__main__":
    raise SystemExit(main())
