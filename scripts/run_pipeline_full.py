#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/run_pipeline_full.py
# [PROJECT] my_TV_Movie
# [ROLE]    Orchestrate: TXT->inputs_parsed -> TMDB -> Trakt -> QA
# [VERSION] v1.3.2
# [UPDATED] 2026-01-16_00-00-00
# [BUILD]   14.01.16
#
# Change:
# - QA GUARD (no new scripts):
#   * Detect merge markers in generated JSON (<<<<<<</=======/>>>>>>>)
#   * Validate JSON parse for inputs_parsed.json and data.json
#   * Fail fast with log evidence
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
import sys
from typing import Iterable


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_DIR = os.path.join(REPO_ROOT, "logs")

DATA_DIR = os.path.join(REPO_ROOT, "data")
DATA_JSON = os.path.join(DATA_DIR, "data.json")
INPUTS_PARSED_JSON = os.path.join(DATA_DIR, "inputs_parsed.json")

MERGE_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")


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


def _iter_head_lines(path: str, n: int = 80) -> Iterable[tuple[int, str]]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, start=1):
                yield i, line.rstrip("\n")
                if i >= n:
                    break
    except Exception:
        return


def _guard_no_merge_markers(paths: list[str], logfp: str) -> int:
    bad = []
    for p in paths:
        if not os.path.isfile(p):
            continue
        for ln, line in _iter_head_lines(p, 200):
            if line.startswith(MERGE_MARKERS):
                bad.append((p, ln, line))
                # capture a few more lines for context
                break

    if not bad:
        _write_line(logfp, "[GUARD] merge markers: OK")
        return 0

    _write_line(logfp, "[GUARD] merge markers: FAIL")
    for p, ln, line in bad[:10]:
        _write_line(logfp, f"[GUARD] marker found: {p} line={ln} text={line}")
        # dump small context
        for ln2, line2 in _iter_head_lines(p, 40):
            _write_line(logfp, f"[GUARD] {p}:{ln2}: {line2}")
            if ln2 >= 25:
                break
    return 90


def _guard_json_parse(paths: list[str], logfp: str) -> int:
    bad = []
    for p in paths:
        if not os.path.isfile(p):
            continue
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                json.load(f)
        except Exception as ex:
            bad.append((p, str(ex)))

    if not bad:
        _write_line(logfp, "[GUARD] json parse: OK")
        return 0

    _write_line(logfp, "[GUARD] json parse: FAIL")
    for p, err in bad[:10]:
        _write_line(logfp, f"[GUARD] json invalid: {p} err={err}")
        for ln, line in _iter_head_lines(p, 40):
            _write_line(logfp, f"[GUARD] {p}:{ln}: {line}")
            if ln >= 25:
                break
    return 91


def main() -> int:
    os.makedirs(LOG_DIR, exist_ok=True)
    logfp = os.path.join(LOG_DIR, f"run_pipeline_full_{_ts()}.log.txt")

    py = sys.executable
    started = _dt.datetime.now()

    _write_line(logfp, "--- SUMMARY ---")
    _write_line(logfp, f"repo_root : {REPO_ROOT}")
    _write_line(logfp, f"python    : {py}")
    _write_line(logfp, f"log       : {logfp}")

    # GUARD 0: fail fast if pre-existing generated JSON is corrupted (stash/merge markers)
    rc_guard0 = _guard_no_merge_markers([DATA_JSON, INPUTS_PARSED_JSON], logfp)
    if rc_guard0 != 0:
        _write_line(logfp, f"RESULT    : FAIL (guard merge markers exit_code={rc_guard0})")
        return rc_guard0

    rc_guard0b = _guard_json_parse([DATA_JSON, INPUTS_PARSED_JSON], logfp)
    if rc_guard0b != 0:
        # allow missing files pre-run; only fail if file exists and is invalid
        # (guard_json_parse already skips non-existent)
        _write_line(logfp, f"RESULT    : FAIL (guard json parse exit_code={rc_guard0b})")
        return rc_guard0b

    # 1) Parse TXT inputs
    rc_parse = _run("PARSE", [py, os.path.join("scripts", "parse_txt_to_json.py")], logfp)
    if rc_parse != 0:
        _write_line(logfp, f"RESULT    : FAIL (parse exit_code={rc_parse})")
        return rc_parse

    # GUARD 1: inputs_parsed.json must be marker-free + valid JSON
    rc_guard1 = _guard_no_merge_markers([INPUTS_PARSED_JSON], logfp)
    if rc_guard1 != 0:
        _write_line(logfp, f"RESULT    : FAIL (guard inputs_parsed merge markers exit_code={rc_guard1})")
        return rc_guard1
    rc_guard1b = _guard_json_parse([INPUTS_PARSED_JSON], logfp)
    if rc_guard1b != 0:
        _write_line(logfp, f"RESULT    : FAIL (guard inputs_parsed json parse exit_code={rc_guard1b})")
        return rc_guard1b

    # 2) TMDB fetch
    rc_tmdb = _run("TMDB", [py, os.path.join("scripts", "fetch_tmdb.py")], logfp)
    if rc_tmdb != 0:
        _write_line(logfp, f"RESULT    : FAIL (tmdb exit_code={rc_tmdb})")
        return rc_tmdb

    # GUARD 2: data.json must be marker-free + valid JSON
    rc_guard2 = _guard_no_merge_markers([DATA_JSON], logfp)
    if rc_guard2 != 0:
        _write_line(logfp, f"RESULT    : FAIL (guard data.json merge markers exit_code={rc_guard2})")
        return rc_guard2
    rc_guard2b = _guard_json_parse([DATA_JSON], logfp)
    if rc_guard2b != 0:
        _write_line(logfp, f"RESULT    : FAIL (guard data.json json parse exit_code={rc_guard2b})")
        return rc_guard2b

    # 3) Trakt enrichment (public)
    rc_trakt = _run("TRAKT", [py, os.path.join("scripts", "fetch_trakt.py")], logfp)
    if rc_trakt != 0:
        _write_line(logfp, f"RESULT    : FAIL (trakt exit_code={rc_trakt})")
        return rc_trakt

    # 3b) Trakt watch-state sync (OAuth; optional)
    rc_watch = _run("TRAKT_WATCH_STATE", [py, os.path.join("scripts", "trakt_sync_watch_state.py")], logfp)
    if rc_watch != 0:
        _write_line(logfp, f"RESULT    : FAIL (trakt_sync_watch_state exit_code={rc_watch})")
        return rc_watch

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
