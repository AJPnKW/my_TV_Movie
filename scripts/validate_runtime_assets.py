#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/validate_runtime_assets.py
# [PROJECT] my_TV_Movie
# [ROLE]    Validate runtime asset-path metadata and local-file coverage for the
#           active catalog in data/data.json.
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

from availability_status_lib import DATA_JSON, REPO_ROOT, load_json, safe_text, write_json_atomic

REPORT_DIR = REPO_ROOT / "reports" / "availability_status"

EXPECTED_FIELDS = {
    "movie": [
        {"name": "poster", "local_key": "poster_local", "remote_key": "poster_path", "prefix": "/assets/posters/movies/", "required_visual": True},
        {"name": "backdrop", "local_key": "backdrop_local", "remote_key": "backdrop_path", "prefix": "/assets/backdrops/movies/", "required_visual": False},
    ],
    "show": [
        {"name": "poster", "local_key": "poster_local", "remote_key": "poster_path", "prefix": "/assets/posters/shows/", "required_visual": True},
        {"name": "backdrop", "local_key": "backdrop_local", "remote_key": "backdrop_path", "prefix": "/assets/backdrops/shows/", "required_visual": False},
    ],
    "season": [
        {"name": "poster", "local_key": "poster_local", "remote_key": "poster_path", "prefix": "/assets/posters/seasons/", "required_visual": False},
    ],
    "episode": [
        {"name": "still", "local_key": "still_local", "remote_key": "still_path", "prefix": "/assets/stills/episodes/", "required_visual": False},
    ],
}


def _stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _abs_local(path_text: str) -> Path:
    normalized = safe_text(path_text).replace("\\", "/")
    if normalized.startswith("/"):
        normalized = normalized[1:]
    return REPO_ROOT / normalized


def _entity_label(entity_type: str, entity: Dict[str, Any], context: Dict[str, Any]) -> str:
    if entity_type == "movie":
        return f"movie:{entity.get('tmdb_id')}:{safe_text(entity.get('title'))}"
    if entity_type == "show":
        return f"show:{entity.get('tmdb_id')}:{safe_text(entity.get('title') or entity.get('name'))}"
    if entity_type == "season":
        return f"season:{context.get('show_tmdb_id')}:{context.get('season_number')}"
    return f"episode:{context.get('show_tmdb_id')}:{context.get('season_number')}:{context.get('episode_number')}"


def _check_field(entity_type: str, entity: Dict[str, Any], context: Dict[str, Any], field: Dict[str, Any], issues: List[str], warnings: List[str], counts: Counter, warning_groups: Counter) -> None:
    local_value = safe_text(entity.get(field["local_key"]))
    remote_value = safe_text(entity.get(field["remote_key"]))
    label = _entity_label(entity_type, entity, context)
    counts[f"{entity_type}:{field['name']}:checked"] += 1

    if local_value:
        if not (local_value.startswith("/assets/") or local_value.startswith("assets/")):
            issues.append(f"{label} {field['local_key']} must stay under /assets: {local_value}")
        if field["prefix"] and not local_value.startswith(field["prefix"]) and not local_value.startswith(field["prefix"][1:]):
            issues.append(f"{label} {field['local_key']} must use prefix {field['prefix']}")
        abs_path = _abs_local(local_value)
        if not abs_path.exists():
            issues.append(f"{label} local asset missing on disk: {local_value}")
        else:
            counts[f"{entity_type}:{field['name']}:local_exists"] += 1

    if remote_value and not local_value:
        issues.append(f"{label} missing {field['local_key']} for remote asset {field['remote_key']}")

    if field["required_visual"] and not local_value and not remote_value:
        warnings.append(f"{label} missing both {field['local_key']} and {field['remote_key']}")
        warning_groups[f"{entity_type}.{field['name']}:missing_metadata"] += 1

    if local_value and not remote_value:
        counts[f"{entity_type}:{field['name']}:local_only"] += 1
    if remote_value and local_value:
        counts[f"{entity_type}:{field['name']}:paired"] += 1
    if not local_value and not remote_value:
        counts[f"{entity_type}:{field['name']}:missing_metadata"] += 1


def _check_entity(entity_type: str, entity: Dict[str, Any], context: Dict[str, Any], issues: List[str], warnings: List[str], counts: Counter, warning_groups: Counter) -> None:
    for field in EXPECTED_FIELDS[entity_type]:
        _check_field(entity_type, entity, context, field, issues, warnings, counts, warning_groups)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-json", default=str(DATA_JSON))
    parser.add_argument("--report-json", default="")
    args = parser.parse_args()

    data = load_json(Path(args.data_json))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    issues: List[str] = []
    warnings: List[str] = []
    counts = Counter()
    warning_groups = Counter()

    for movie in data.get("movies", []) or []:
        if isinstance(movie, dict):
            _check_entity("movie", movie, {}, issues, warnings, counts, warning_groups)

    for show in data.get("shows", []) or []:
        if not isinstance(show, dict):
            continue
        show_context = {"show_tmdb_id": show.get("tmdb_id")}
        _check_entity("show", show, show_context, issues, warnings, counts, warning_groups)
        for season in show.get("seasons", []) or []:
            if not isinstance(season, dict):
                continue
            season_context = {"show_tmdb_id": show.get("tmdb_id"), "season_number": season.get("season_number") or season.get("number")}
            _check_entity("season", season, season_context, issues, warnings, counts, warning_groups)
            for episode in season.get("episodes", []) or []:
                if not isinstance(episode, dict):
                    continue
                episode_context = {
                    "show_tmdb_id": show.get("tmdb_id"),
                    "season_number": season_context["season_number"],
                    "episode_number": episode.get("episode_number") or episode.get("number"),
                }
                _check_entity("episode", episode, episode_context, issues, warnings, counts, warning_groups)

    report = {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "result": "OK" if not issues else "FAIL",
        "issue_count": len(issues),
        "warning_count": len(warnings),
        "counts": dict(counts),
        "warning_groups": dict(warning_groups),
        "issues_sample": issues[:100],
        "warnings_sample": warnings[:100],
    }
    report_path = Path(args.report_json) if args.report_json else (REPORT_DIR / f"runtime_asset_validation_{_stamp()}.json")
    write_json_atomic(report_path, report)
    print(json.dumps({"report": str(report_path), **report}, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
