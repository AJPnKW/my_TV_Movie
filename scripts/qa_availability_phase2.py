#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/qa_availability_phase2.py
# [PROJECT] my_TV_Movie
# [ROLE]    Deterministic hardening checks for override precedence, future-date
#           behavior, unknown fallback, and provider-aware validation.
# [VERSION] v1.0.0
# [UPDATED] 2026-03-21
# [BUILD]   21.03.02
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any, Dict, List

from availability_status_lib import (
    DATA_JSON,
    SOURCE_JSON,
    canonical_source_document,
    load_json,
    load_streaming_config,
    resolve_availability,
    validate_primary_watch_url,
    write_json_atomic,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "reports" / "availability_status"


def _pick_live_samples(data: Dict[str, Any]) -> Dict[str, Any]:
    show = next((item for item in data.get("shows", []) if isinstance(item, dict) and item.get("seasons")), None)
    season = next((item for item in (show.get("seasons") if isinstance(show, dict) else []) or [] if isinstance(item, dict) and item.get("episodes")), None)
    episode = next((item for item in (season.get("episodes") if isinstance(season, dict) else []) or [] if isinstance(item, dict)), None)
    movie = next((item for item in data.get("movies", []) if isinstance(item, dict)), None)
    return {"movie": movie, "show": show, "season": season, "episode": episode}


def _assert(condition: bool, label: str, issues: List[str]) -> None:
    if not condition:
        issues.append(label)


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_json(DATA_JSON)
    source = canonical_source_document(load_json(SOURCE_JSON))
    streaming = load_streaming_config()
    samples = _pick_live_samples(data)
    issues: List[str] = []

    movie = samples["movie"]
    show = samples["show"]
    season = samples["season"]
    episode = samples["episode"]

    _assert(isinstance(movie, dict), "live movie sample missing", issues)
    _assert(isinstance(show, dict), "live show sample missing", issues)
    _assert(isinstance(season, dict), "live season sample missing", issues)
    _assert(isinstance(episode, dict), "live episode sample missing", issues)

    if issues:
        report = {"generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "result": "FAIL", "issues": issues}
        path = REPORT_DIR / f"availability_phase2_qa_{_dt.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
        write_json_atomic(path, report)
        print(json.dumps({"report": str(path), **report}, indent=2))
        return 1

    movie_result = resolve_availability(
        "movie",
        movie,
        {"show_tmdb_id": None, "season_number": None, "episode_number": None},
        source["defaults"],
        streaming,
        {"entity_type": "movie", "entity_key": f"movie:{movie.get('tmdb_id')}", "status_override": "unavailable", "reason": "qa override"},
    )
    _assert(movie_result["availability_status"] == "unavailable", "movie status_override must win", issues)

    show_result = resolve_availability(
        "show",
        show,
        {"show_tmdb_id": show.get("tmdb_id"), "season_number": None, "episode_number": None},
        source["defaults"],
        streaming,
        {"entity_type": "show", "entity_key": f"show:{show.get('tmdb_id')}", "release_date_override": "2099-01-01"},
    )
    _assert(show_result["availability_status"] == "not_yet_released", "show future release override must produce not_yet_released", issues)

    season_result = resolve_availability(
        "season",
        season,
        {"show_tmdb_id": show.get("tmdb_id"), "season_number": season.get("season_number"), "episode_number": None},
        source["defaults"],
        streaming,
        {"entity_type": "season", "entity_key": f"show:{show.get('tmdb_id')}:season:{season.get('season_number')}", "preferred_source": "vidsrc", "primary_watch_url": "https://example.invalid/season"},
    )
    _assert(season_result["availability_status"] == "unavailable", "season invalid provider URL must be unavailable", issues)

    episode_result = resolve_availability(
        "episode",
        episode,
        {"show_tmdb_id": show.get("tmdb_id"), "season_number": season.get("season_number"), "episode_number": episode.get("episode_number")},
        source["defaults"],
        streaming,
        {"entity_type": "episode", "entity_key": f"show:{show.get('tmdb_id')}:season:{season.get('season_number')}:episode:{episode.get('episode_number')}", "requires_url": False},
    )
    _assert(episode_result["availability_status"] in {"unknown", "not_yet_released", "available", "unavailable"}, "episode result must be normalized", issues)

    provider_validation = validate_primary_watch_url(
        "https://example.invalid/movie/123",
        "movie",
        movie,
        {"show_tmdb_id": None, "season_number": None, "episode_number": None},
        streaming,
        source["defaults"],
        source_key="videasy",
    )
    _assert(provider_validation["url_test_result"] == "fail", "provider-aware validation must fail mismatched bases", issues)

    report = {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "result": "OK" if not issues else "FAIL",
        "issue_count": len(issues),
        "issues": issues,
        "live_override_seed_count": len(source.get("records", [])),
        "override_seeded_in_catalog": bool(source.get("records")),
    }
    path = REPORT_DIR / f"availability_phase2_qa_{_dt.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
    write_json_atomic(path, report)
    print(json.dumps({"report": str(path), **report}, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
