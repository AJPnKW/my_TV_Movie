#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/run_pipeline_full.py
# [PROJECT] my_TV_Movie
# [ROLE]    Orchestrate: TXT->inputs_parsed -> TMDB -> Trakt -> QA
# [VERSION] v1.2.0
# [UPDATED] 2026-01-03_00-00-00
# [BUILD]   14.01.07
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


def _write_line(fp: str, msg: str) -> None:
    with open(fp, "a", encoding="utf-8", errors="replace", newline="\n") as f:
        f.write(msg + "\n")


def _run(label: str, args: list[str], logfp: str) -> int:
    _write_line(logfp, f"\n[{label}] RUN {' '.join(args)}")
    p = subprocess.run(args, cwd=REPO_ROOT)
    _write_line(logfp, f"[{label}] exit_code={p.returncode}")
    return int(p.returncode)


def main() -> int:
    os.makedirs(LOG_DIR, exist_ok=True)
    logfp = os.path.join(LOG_DIR, f"run_pipeline_full_{_ts()}.log.txt")

    py = sys.executable
    started = _dt.datetime.now()

    _write_line(logfp, "--- SUMMARY ---")
    _write_line(logfp, f"repo_root : {REPO_ROOT}")
    _write_line(logfp, f"python    : {py}")
    _write_line(logfp, f"log       : {logfp}")

    # 1) Parse TXT inputs
    rc_parse = _run("PARSE", [py, os.path.join("scripts", "parse_txt_to_json.py")], logfp)
    if rc_parse != 0:
        _write_line(logfp, f"RESULT    : FAIL (parse exit_code={rc_parse})")
        return rc_parse

    # 2) TMDB fetch
    rc_tmdb = _run("TMDB", [py, os.path.join("scripts", "fetch_tmdb.py")], logfp)
    if rc_tmdb != 0:
        _write_line(logfp, f"RESULT    : FAIL (tmdb exit_code={rc_tmdb})")
        return rc_tmdb

    # 3) Trakt enrichment (public)
    rc_trakt = _run("TRAKT", [py, os.path.join("scripts", "fetch_trakt.py")], logfp)
    if rc_trakt != 0:
        _write_line(logfp, f"RESULT    : FAIL (trakt exit_code={rc_trakt})")
        return rc_trakt

    # 4) QA missing trakt ids
    rc_qa1 = _run("QA_MISSING_TRAKT", [py, os.path.join("scripts", "qa_missing_trakt_ids.py")], logfp)
    if rc_qa1 != 0:
        _write_line(logfp, f"RESULT    : FAIL (qa_missing_trakt_ids exit_code={rc_qa1})")
        return rc_qa1

    # 5) QA integrity / consistency
    rc_qa2 = _run("QA_INTEGRITY", [py, os.path.join("scripts", "qa_pipeline_integrity.py")], logfp)
    if rc_qa2 != 0:
        _write_line(logfp, f"RESULT    : FAIL (qa_pipeline_integrity exit_code={rc_qa2})")
        return rc_qa2

    finished = _dt.datetime.now()
    _write_line(logfp, "")
    _write_line(logfp, f"started   : {started.strftime('%Y-%m-%d %H:%M:%S')}")
    _write_line(logfp, f"finished  : {finished.strftime('%Y-%m-%d %H:%M:%S')}")
    _write_line(logfp, "RESULT    : OK (exit_code=0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
