#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/validate_runtime_catalog_integrity.py
# [PROJECT] my_TV_Movie
# [ROLE]    Validate JSON integrity and required availability/runtime fields
#           after the active pipeline has generated/enriched data/data.json.
# [VERSION] v1.0.0
# [UPDATED] 2026-03-21
# [BUILD]   21.03.02
# ==============================================================================

from __future__ import annotations

import argparse
import datetime as _dt
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from availability_status_lib import ALLOWED_AVAILABILITY, DATA_JSON, SOURCE_JSON, is_valid_primary_url, load_json, write_json_atomic

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "reports" / "availability_status"


def _stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _check_entity(entity_type: str, entity: Dict[str, Any], issues: List[str], counts: Counter) -> None:
    status = str(entity.get("availability_status") or "").strip()
    counts[f"{entity_type}:count"] += 1
    counts[f"{entity_type}:status:{status or 'missing'}"] += 1
    if status not in ALLOWED_AVAILABILITY:
        issues.append(f"{entity_type} invalid availability_status={status!r}")
    for key in ("availability_checked_at", "availability_source", "availability_reason"):
        if not str(entity.get(key) or "").strip():
            issues.append(f"{entity_type} missing {key}")
    tested = str(entity.get("primary_watch_url_tested") or "").strip()
    if tested and not is_valid_primary_url(tested):
        issues.append(f"{entity_type} invalid primary_watch_url_tested={tested!r}")
    watch_sources = entity.get("watch_sources")
    if watch_sources not in (None, ""):
        if not isinstance(watch_sources, list):
            issues.append(f"{entity_type} watch_sources must be a list")
        else:
            seen = set()
            for idx, row in enumerate(watch_sources):
                if not isinstance(row, dict):
                    issues.append(f"{entity_type} watch_sources[{idx}] must be an object")
                    continue
                for field in ("key", "label", "href", "type"):
                    if not str(row.get(field) or "").strip():
                        issues.append(f"{entity_type} watch_sources[{idx}] missing {field}")
                href = str(row.get("href") or "").strip()
                if href and not is_valid_primary_url(href):
                    issues.append(f"{entity_type} watch_sources[{idx}] invalid href")
                key = str(row.get("key") or "").strip()
                if key:
                    if key in seen:
                        issues.append(f"{entity_type} duplicate watch_sources key={key}")
                    seen.add(key)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-json", default=str(DATA_JSON))
    parser.add_argument("--source-json", default=str(SOURCE_JSON))
    parser.add_argument("--report-json", default="")
    args = parser.parse_args()

    data = load_json(Path(args.data_json))
    source = load_json(Path(args.source_json))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    issues: List[str] = []
    counts = Counter()

    if not isinstance(data, dict):
        issues.append("data/data.json root must be an object")
    if not isinstance(source, dict):
        issues.append("data/watch_source_availability.json root must be an object")
    if not isinstance(data.get("movies"), list):
        issues.append("data.json movies must be a list")
    if not isinstance(data.get("shows"), list):
        issues.append("data.json shows must be a list")
    if not isinstance(source.get("records"), list):
        issues.append("watch_source_availability.json records must be a list")

    for movie in data.get("movies", []) or []:
        if isinstance(movie, dict):
            _check_entity("movie", movie, issues, counts)
    for show in data.get("shows", []) or []:
        if not isinstance(show, dict):
            continue
        _check_entity("show", show, issues, counts)
        if not isinstance(show.get("seasons", []), list):
            issues.append(f"show {show.get('tmdb_id')} seasons must be a list")
            continue
        for season in show.get("seasons", []) or []:
            if not isinstance(season, dict):
                continue
            _check_entity("season", season, issues, counts)
            if not isinstance(season.get("episodes", []), list):
                issues.append(f"season {show.get('tmdb_id')}:{season.get('season_number')} episodes must be a list")
                continue
            for episode in season.get("episodes", []) or []:
                if isinstance(episode, dict):
                    _check_entity("episode", episode, issues, counts)

    report = {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "result": "OK" if not issues else "FAIL",
        "issue_count": len(issues),
        "counts": dict(counts),
        "issues_sample": issues[:100],
    }
    report_path = Path(args.report_json) if args.report_json else (REPORT_DIR / f"runtime_catalog_integrity_{_stamp()}.json")
    write_json_atomic(report_path, report)
    print(json.dumps({"report": str(report_path), **report}, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
