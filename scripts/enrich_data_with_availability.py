#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/enrich_data_with_availability.py
# [PROJECT] my_TV_Movie
# [ROLE]    Resolve normalized availability fields into data/data.json using
#           data/watch_source_availability.json as the external source of truth.
# [VERSION] v2.0.0
# [UPDATED] 2026-03-21
# [BUILD]   21.03.02
# ==============================================================================

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from availability_status_lib import (
    CONFIG_JSON,
    DATA_JSON,
    SOURCE_JSON,
    build_catalog_key_index,
    canonical_source_document,
    load_json,
    load_network_cache,
    load_streaming_config,
    resolve_availability,
    validate_source_document,
    write_json_atomic,
    write_network_cache,
)


def apply_availability_fields(entity: Dict[str, Any], resolved: Dict[str, Any]) -> None:
    entity["availability_status"] = resolved["availability_status"]
    entity["availability_checked_at"] = resolved["availability_checked_at"]
    entity["availability_source"] = resolved["availability_source"]
    entity["availability_reason"] = resolved["availability_reason"]
    if resolved.get("primary_watch_url_tested"):
        entity["primary_watch_url_tested"] = resolved["primary_watch_url_tested"]
    elif "primary_watch_url_tested" in entity:
        entity.pop("primary_watch_url_tested", None)


def _resolve_episode(show_id: Any, season_number: Any, episode: Dict[str, Any], source: Dict[str, Any], streaming: Dict[str, str], records: Dict[str, Dict[str, Any]], allow_network: bool, cache: Dict[str, Any]) -> Dict[str, Any]:
    episode_number = episode.get("episode_number") or episode.get("number")
    episode_key = f"show:{show_id}:season:{season_number}:episode:{episode_number}"
    resolved = resolve_availability(
        "episode",
        episode,
        {"show_tmdb_id": show_id, "season_number": season_number, "episode_number": episode_number},
        source["defaults"],
        streaming,
        records.get(episode_key),
        allow_network=allow_network,
        cache=cache,
    )
    apply_availability_fields(episode, resolved)
    return resolved


def _resolve_season(show_id: Any, season: Dict[str, Any], source: Dict[str, Any], streaming: Dict[str, str], records: Dict[str, Dict[str, Any]], allow_network: bool, cache: Dict[str, Any]) -> Dict[str, Any]:
    season_number = season.get("season_number") or season.get("number")
    child_statuses: List[str] = []
    for episode in season.get("episodes", []) or []:
        if not isinstance(episode, dict):
            continue
        resolved_episode = _resolve_episode(show_id, season_number, episode, source, streaming, records, allow_network, cache)
        child_statuses.append(resolved_episode["availability_status"])
    season_key = f"show:{show_id}:season:{season_number}"
    resolved = resolve_availability(
        "season",
        season,
        {"show_tmdb_id": show_id, "season_number": season_number, "episode_number": None},
        source["defaults"],
        streaming,
        records.get(season_key),
        child_statuses=child_statuses,
        allow_network=allow_network,
        cache=cache,
    )
    apply_availability_fields(season, resolved)
    return resolved


def _resolve_show(show: Dict[str, Any], source: Dict[str, Any], streaming: Dict[str, str], records: Dict[str, Dict[str, Any]], allow_network: bool, cache: Dict[str, Any]) -> Dict[str, Any]:
    show_id = show.get("tmdb_id") or show.get("id")
    child_statuses: List[str] = []
    for season in show.get("seasons", []) or []:
        if not isinstance(season, dict):
            continue
        resolved_season = _resolve_season(show_id, season, source, streaming, records, allow_network, cache)
        child_statuses.append(resolved_season["availability_status"])
    show_key = f"show:{show_id}"
    resolved = resolve_availability(
        "show",
        show,
        {"show_tmdb_id": show_id, "season_number": None, "episode_number": None},
        source["defaults"],
        streaming,
        records.get(show_key),
        child_statuses=child_statuses,
        allow_network=allow_network,
        cache=cache,
    )
    apply_availability_fields(show, resolved)
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-json", default=str(DATA_JSON))
    parser.add_argument("--source-json", default=str(SOURCE_JSON))
    parser.add_argument("--config-json", default=str(CONFIG_JSON))
    parser.add_argument("--report-json", default="")
    parser.add_argument("--network-check", action="store_true")
    args = parser.parse_args()

    data_path = Path(args.data_json)
    source_path = Path(args.source_json)
    config_path = Path(args.config_json)

    data = load_json(data_path)
    existing_source = load_json(source_path) if source_path.exists() else {}
    source = canonical_source_document(existing_source)
    known_keys = build_catalog_key_index(data).keys()
    errors = validate_source_document(source, known_keys)
    if errors:
        print(json.dumps({"result": "FAIL", "errors": errors}, indent=2))
        return 1

    streaming = load_streaming_config(config_path)
    cache = load_network_cache(source["defaults"])
    records = {record["entity_key"]: record for record in source.get("records", []) if isinstance(record, dict) and record.get("entity_key")}

    counts_by_entity = Counter()
    counts_by_status = Counter()

    for movie in data.get("movies", []) or []:
        if not isinstance(movie, dict):
            continue
        key = f"movie:{movie.get('tmdb_id') or movie.get('id')}"
        resolved = resolve_availability(
            "movie",
            movie,
            {"show_tmdb_id": None, "season_number": None, "episode_number": None},
            source["defaults"],
            streaming,
            records.get(key),
            allow_network=args.network_check,
            cache=cache,
        )
        apply_availability_fields(movie, resolved)
        counts_by_entity["movie"] += 1
        counts_by_status[f"movie:{resolved['availability_status']}"] += 1

    for show in data.get("shows", []) or []:
        if not isinstance(show, dict):
            continue
        resolved_show = _resolve_show(show, source, streaming, records, args.network_check, cache)
        counts_by_entity["show"] += 1
        counts_by_status[f"show:{resolved_show['availability_status']}"] += 1
        for season in show.get("seasons", []) or []:
            if not isinstance(season, dict):
                continue
            counts_by_entity["season"] += 1
            counts_by_status[f"season:{season.get('availability_status')}"] += 1
            for episode in season.get("episodes", []) or []:
                if not isinstance(episode, dict):
                    continue
                counts_by_entity["episode"] += 1
                counts_by_status[f"episode:{episode.get('availability_status')}"] += 1

    source["generated_at"] = source.get("generated_at") or ""
    write_json_atomic(source_path, source)
    write_network_cache(source["defaults"], cache)
    write_json_atomic(data_path, data)

    report = {
        "result": "OK",
        "data_json": str(data_path),
        "source_json": str(source_path),
        "network_cache": str(Path(source["defaults"]["network"]["cache_file"])),
        "network_check_enabled": bool(args.network_check),
        "counts_by_entity": dict(counts_by_entity),
        "counts_by_status": dict(counts_by_status),
    }
    if args.report_json:
        write_json_atomic(Path(args.report_json), report)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
