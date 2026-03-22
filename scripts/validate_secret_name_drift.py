#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/validate_secret_name_drift.py
# [PROJECT] my_TV_Movie
# [ROLE]    Detect canonical-vs-typo Trakt redirect secret drift in repo files
#           and the current environment.
# [VERSION] v1.0.0
# [UPDATED] 2026-03-21
# [BUILD]   21.03.03
# ==============================================================================

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from availability_status_lib import REPO_ROOT, write_json_atomic

REPORT_DIR = REPO_ROOT / "reports" / "availability_status"
CANONICAL = "API_TRAKT_REDIRECT_URL"
TYPO = "API_TRAKT__REDIRECT_URL"
ALLOWED_TYPO_FILES = {
    "scripts/trakt_device_auth.py",
    "scripts/trakt_test_tokens.py",
    "scripts/validate_secret_name_drift.py",
}
SKIP_PARTS = {".git", ".my_notes", "logs", "node_modules", "__pycache__", ".venv", "dist", "build"}


def _is_text(path: Path) -> bool:
    return path.suffix.lower() in {".py", ".md", ".txt", ".yml", ".yaml", ".json", ".ps1", ".html", ".js", ".css"}


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    typo_hits: List[str] = []
    canonical_hits: List[str] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or not _is_text(path):
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if any(part in SKIP_PARTS for part in path.relative_to(REPO_ROOT).parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if CANONICAL in text:
            canonical_hits.append(rel)
        if TYPO in text and rel not in ALLOWED_TYPO_FILES:
            typo_hits.append(rel)

    canonical_env = os.getenv(CANONICAL)
    typo_env = os.getenv(TYPO)
    env_conflict = bool(canonical_env and typo_env and canonical_env.strip() != typo_env.strip())
    env_typo_only = bool(typo_env and not canonical_env)

    report = {
        "result": "OK" if not typo_hits and not env_conflict else "FAIL",
        "canonical_secret_name": CANONICAL,
        "canonical_refs": sorted(set(canonical_hits)),
        "unexpected_typo_refs": sorted(set(typo_hits)),
        "env": {
            "canonical_set": bool(canonical_env and canonical_env.strip()),
            "typo_set": bool(typo_env and typo_env.strip()),
            "conflict": env_conflict,
            "typo_only": env_typo_only,
        },
        "allowed_typo_guard_files": sorted(ALLOWED_TYPO_FILES),
    }
    report_path = REPORT_DIR / "secret_name_drift_validation.json"
    write_json_atomic(report_path, report)
    print(json.dumps({"report": str(report_path), **report}, indent=2))
    return 0 if report["result"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
