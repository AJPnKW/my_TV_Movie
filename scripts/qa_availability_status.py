#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/qa_availability_status.py
# [PROJECT] my_TV_Movie
# [ROLE]    QA summary for normalized availability fields in data/data.json.
# [VERSION] v1.0.0
# [UPDATED] 2026-03-21
# [BUILD]   21.03.01
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from availability_status_lib import ALLOWED_AVAILABILITY, DATA_JSON, load_json, write_json_atomic

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "reports" / "availability_status"


def _stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _check_entity(entity_type: str, entity: Dict[str, Any], issues: List[str], counts: Counter) -> None:
    status = str(entity.get("availability_status") or "").strip()
    counts[f"{entity_type}:{status or 'missing'}"] += 1
    if status not in ALLOWED_AVAILABILITY:
        issues.append(f"{entity_type} missing/invalid availability_status")
    if not str(entity.get("availability_checked_at") or "").strip():
        issues.append(f"{entity_type} missing availability_checked_at")
    if not str(entity.get("availability_source") or "").strip():
        issues.append(f"{entity_type} missing availability_source")
    if not str(entity.get("availability_reason") or "").strip():
        issues.append(f"{entity_type} missing availability_reason")


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_json(DATA_JSON)
    counts = Counter()
    issues: List[str] = []

    for movie in data.get("movies", []) or []:
        if isinstance(movie, dict):
            _check_entity("movie", movie, issues, counts)
    for show in data.get("shows", []) or []:
        if not isinstance(show, dict):
            continue
        _check_entity("show", show, issues, counts)
        for season in show.get("seasons", []) or []:
            if not isinstance(season, dict):
                continue
            _check_entity("season", season, issues, counts)
            for episode in season.get("episodes", []) or []:
                if isinstance(episode, dict):
                    _check_entity("episode", episode, issues, counts)

    report = {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "result": "OK" if not issues else "FAIL",
        "counts": dict(counts),
        "issue_count": len(issues),
        "issues_sample": issues[:100],
    }
    report_path = REPORT_DIR / f"availability_status_{_stamp()}.json"
    write_json_atomic(report_path, report)
    print(json.dumps({"report": str(report_path), **report}, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
