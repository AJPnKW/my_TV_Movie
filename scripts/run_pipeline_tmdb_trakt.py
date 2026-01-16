#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/run_pipeline_tmdb_trakt.py
# [PROJECT] my_TV_Movie
# [ROLE]    Orchestrate minimal pipeline: TXT->inputs_parsed -> TMDB -> Trakt
# [VERSION] v0.2.0
# [UPDATED] 2026-01-15
# [BUILD]   14.01.15
# ==============================================================================
from __future__ import annotations
import datetime as _dt
import os
import subprocess
import sys
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_DIR = os.path.join(REPO_ROOT, "logs")
def _ts() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
def _write(fp: str, msg: str) -> None:
    with open(fp, "a", encoding="utf-8", errors="replace", newline="\n") as f:
        f.write(msg + "\n")
def _run(label: str, args: list[str], logfp: str) -> int:
    _write(logfp, f"\n[{label}] RUN {' '.join(args)}")
    p = subprocess.run(args, cwd=REPO_ROOT)
    _write(logfp, f"[{label}] exit_code={p.returncode}")
    return int(p.returncode)
def main() -> int:
    os.makedirs(LOG_DIR, exist_ok=True)
    logfp = os.path.join(LOG_DIR, f"run_pipeline_tmdb_trakt_{_ts()}.log.txt")
    py = sys.executable
    rc = _run("PARSE", [py, os.path.join("scripts", "parse_txt_to_json.py")], logfp)
    if rc != 0:
        return rc
    rc = _run("TMDB", [py, os.path.join("scripts", "fetch_tmdb.py")], logfp)
    if rc != 0:
        return rc
    rc = _run("TRAKT", [py, os.path.join("scripts", "fetch_trakt.py")], logfp)
    return rc
if __name__ == "__main__":
    raise SystemExit(main())
