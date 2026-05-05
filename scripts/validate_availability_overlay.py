#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/validate_availability_overlay.py
# [PROJECT] my_TV_Movie
# [ROLE]    Validate and optionally normalize data/watch_source_availability.json.
# [VERSION] v1.0.0
# [UPDATED] 2026-05-05
# ==============================================================================
from __future__ import annotations

import argparse
import datetime as _dt
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Set

from availability_status_lib import (
    DATA_JSON,
    SOURCE_JSON,
    canonical_source_document,
    episode_key,
    load_json,
    movie_key,
    season_key,
    show_key,
    validate_source_document,
    write_json_atomic,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "reports" / "availability_status"


def _utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_load_json(path: Path) -> Any:
    try:
        return load_json(path)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        return {"__load_error__": f"{path}: invalid JSON: {exc}"}
    except Exception as exc:
        return {"__load_error__": f"{path}: {exc}"}


def _known_catalog_keys(data: Dict[str, Any]) -> Set[str]:
    keys: Set[str] = set()
    for movie in data.get("movies", []) if isinstance(data.get("movies"), list) else []:
        if isinstance(movie, dict):
            key = movie_key(movie)
            if key:
                keys.add(key)

    for show in data.get("shows", []) if isinstance(data.get("shows"), list) else []:
        if not isinstance(show, dict):
            continue
        show_id = show.get("tmdb_id") or show.get("id")
        key = show_key(show)
        if key:
            keys.add(key)
        seasons = show.get("seasons") if isinstance(show.get("seasons"), list) else []
        for season in seasons:
            if not isinstance(season, dict):
                continue
            season_number = season.get("season_number")
            key = season_key(show_id, season_number)
            if key:
                keys.add(key)
            episodes = season.get("episodes") if isinstance(season.get("episodes"), list) else []
            for episode in episodes:
                if not isinstance(episode, dict):
                    continue
                key = episode_key(show_id, season_number, episode.get("episode_number"))
                if key:
                    keys.add(key)
    return keys


def _report_path() -> Path:
    stamp = _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return REPORT_DIR / f"availability_overlay_validation_{stamp}.json"


def _validate_source(source: Dict[str, Any], known_keys: Iterable[str]) -> list[str]:
    issues = list(validate_source_document(source, known_keys))
    for idx, record in enumerate(source.get("records") or []):
        if not isinstance(record, dict):
            continue
        entity_type = str(record.get("entity_type") or "").strip().lower()
        entity_key = str(record.get("entity_key") or "").strip()
        if entity_type == "movie" and not entity_key.startswith("movie:"):
            issues.append(f"records[{idx}] movie entity_key must start with movie:")
        elif entity_type in {"show", "season", "episode"} and not entity_key.startswith("show:"):
            issues.append(f"records[{idx}] {entity_type} entity_key must start with show:")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-normalized", action="store_true", help="Rewrite watch_source_availability.json in canonical shape.")
    parser.add_argument("--report", default="", help="Optional report JSON path.")
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    raw_source = _safe_load_json(SOURCE_JSON)
    raw_data = _safe_load_json(DATA_JSON)

    issues: list[str] = []
    if isinstance(raw_source, dict) and raw_source.get("__load_error__"):
        issues.append(str(raw_source["__load_error__"]))
        source: Dict[str, Any] = canonical_source_document({})
    else:
        source = canonical_source_document(raw_source if isinstance(raw_source, dict) else {})

    if isinstance(raw_data, dict) and raw_data.get("__load_error__"):
        issues.append(str(raw_data["__load_error__"]))
        known_keys: Set[str] = set()
    elif isinstance(raw_data, dict):
        known_keys = _known_catalog_keys(raw_data)
    else:
        issues.append(f"{DATA_JSON}: root must be an object")
        known_keys = set()

    issues.extend(_validate_source(source, known_keys))

    if args.write_normalized and not issues:
        write_json_atomic(SOURCE_JSON, source)

    report = {
        "generated_at": _utc(),
        "result": "OK" if not issues else "FAIL",
        "source": str(SOURCE_JSON.relative_to(REPO_ROOT)).replace("\\", "/"),
        "write_normalized": bool(args.write_normalized),
        "record_count": len(source.get("records", [])),
        "known_catalog_key_count": len(known_keys),
        "issue_count": len(issues),
        "issues": issues,
    }
    path = Path(args.report) if args.report else _report_path()
    write_json_atomic(path, report)
    print(json.dumps({"report": str(path), **report}, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
