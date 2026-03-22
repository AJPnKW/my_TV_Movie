#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/self_heal_asset_metadata.py
# [PROJECT] my_TV_Movie
# [ROLE]    Deterministically repair recoverable runtime asset metadata gaps and
#           optionally fetch missing assets before final validation.
# [VERSION] v1.0.0
# [UPDATED] 2026-03-21
# [BUILD]   21.03.03
# ==============================================================================

from __future__ import annotations

import argparse
import datetime as _dt
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from availability_status_lib import DATA_JSON, REPO_ROOT, load_json, strip_jsonc, write_json_atomic
from fetch_tmdb_assets import download_asset, iter_asset_refs
from validate_runtime_assets import EXPECTED_FIELDS

CONFIG_JSON = REPO_ROOT / "web" / "config.json"
REPORT_DIR = REPO_ROOT / "reports" / "availability_status"

FOLDER_MAP = {
    ("movie", "poster"): "movies_poster",
    ("movie", "backdrop"): "movies_backdrop",
    ("show", "poster"): "shows_poster",
    ("show", "backdrop"): "shows_backdrop",
    ("season", "poster"): "seasons_poster",
    ("episode", "still"): "episodes_stills",
}


def _stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _load_config() -> Dict[str, Any]:
    return json.loads(strip_jsonc(CONFIG_JSON.read_text(encoding="utf-8", errors="replace")))


def _asset_folders() -> Dict[str, str]:
    cfg = _load_config()
    folders = cfg.get("image_cache", {}).get("folders", {})
    return {str(key): str(value) for key, value in folders.items() if str(value).strip()}


def _basename(path_text: str) -> str:
    return Path(str(path_text or "").replace("\\", "/")).name


def _normalize_public_path(path_text: str) -> str:
    value = str(path_text or "").strip().replace("\\", "/")
    if not value:
        return ""
    if not value.startswith("/"):
        value = "/" + value.lstrip("./")
    return value


def _abs_local(path_text: str) -> Path:
    return REPO_ROOT / _normalize_public_path(path_text).lstrip("/")


def _path_exists(path_text: str) -> bool:
    value = _normalize_public_path(path_text)
    return bool(value) and _abs_local(value).exists()


def _derive_local_path(entity_type: str, asset_name: str, remote_path: str, folders: Dict[str, str]) -> str:
    folder_key = FOLDER_MAP.get((entity_type, asset_name))
    folder = _normalize_public_path(folders.get(folder_key))
    name = _basename(remote_path)
    if not folder or not name:
        return ""
    return f"{folder.rstrip('/')}/{name}"


def _derive_remote_path(local_path: str) -> str:
    name = _basename(local_path)
    return f"/{name}" if name else ""


def _entity_label(entity_type: str, entity: Dict[str, Any], context: Dict[str, Any]) -> str:
    if entity_type == "movie":
        return f"movie:{entity.get('tmdb_id')}:{entity.get('title')}"
    if entity_type == "show":
        return f"show:{entity.get('tmdb_id')}:{entity.get('title') or entity.get('name')}"
    if entity_type == "season":
        return f"season:{context.get('show_tmdb_id')}:{context.get('season_number')}"
    return f"episode:{context.get('show_tmdb_id')}:{context.get('season_number')}:{context.get('episode_number')}"


def _iter_entities(data: Dict[str, Any]) -> Iterable[Tuple[str, Dict[str, Any], Dict[str, Any]]]:
    for movie in data.get("movies", []) or []:
        if isinstance(movie, dict):
            yield "movie", movie, {}
    for show in data.get("shows", []) or []:
        if not isinstance(show, dict):
            continue
        show_ctx = {"show_tmdb_id": show.get("tmdb_id")}
        yield "show", show, show_ctx
        for season in show.get("seasons", []) or []:
            if not isinstance(season, dict):
                continue
            season_ctx = {"show_tmdb_id": show.get("tmdb_id"), "season_number": season.get("season_number") or season.get("number")}
            yield "season", season, season_ctx
            for episode in season.get("episodes", []) or []:
                if isinstance(episode, dict):
                    yield "episode", episode, {
                        "show_tmdb_id": show.get("tmdb_id"),
                        "season_number": season_ctx["season_number"],
                        "episode_number": episode.get("episode_number") or episode.get("number"),
                    }


def _warning_snapshot(data: Dict[str, Any]) -> Counter:
    counts = Counter()
    for entity_type, entity, _context in _iter_entities(data):
        for field in EXPECTED_FIELDS[entity_type]:
            if not str(entity.get(field["local_key"]) or "").strip() and not str(entity.get(field["remote_key"]) or "").strip():
                counts[f"{entity_type}.{field['name']}"] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-json", default=str(DATA_JSON))
    parser.add_argument("--fetch-missing", action="store_true")
    parser.add_argument("--max-workers", type=int, default=12)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--report-json", default="")
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    data_path = Path(args.data_json)
    data = load_json(data_path)
    folders = _asset_folders()
    before_counts = _warning_snapshot(data)

    repair_counts = Counter()
    grouped = Counter()
    samples: Dict[str, List[str]] = defaultdict(list)
    mutated = False

    for entity_type, entity, context in _iter_entities(data):
        for field in EXPECTED_FIELDS[entity_type]:
            asset_name = field["name"]
            local_key = field["local_key"]
            remote_key = field["remote_key"]
            local_value = _normalize_public_path(entity.get(local_key))
            remote_value = str(entity.get(remote_key) or "").strip()
            label = _entity_label(entity_type, entity, context)

            if remote_value and not local_value:
                derived_local = _derive_local_path(entity_type, asset_name, remote_value, folders)
                if derived_local:
                    entity[local_key] = derived_local
                    repair_counts["repaired_from_metadata"] += 1
                    grouped[f"{entity_type}.{asset_name}:path_backfill_from_metadata"] += 1
                    if len(samples["repaired_from_metadata"]) < 10:
                        samples["repaired_from_metadata"].append(f"{label} -> {local_key}={derived_local}")
                    local_value = derived_local
                    mutated = True
                else:
                    repair_counts["repair_failed"] += 1
                    grouped[f"{entity_type}.{asset_name}:repair_failed"] += 1

            if local_value and not remote_value and _path_exists(local_value):
                derived_remote = _derive_remote_path(local_value)
                if derived_remote:
                    entity[remote_key] = derived_remote
                    repair_counts["repaired_from_local_asset"] += 1
                    grouped[f"{entity_type}.{asset_name}:path_backfill_from_local_asset"] += 1
                    if len(samples["repaired_from_local_asset"]) < 10:
                        samples["repaired_from_local_asset"].append(f"{label} -> {remote_key}={derived_remote}")
                    mutated = True
                else:
                    repair_counts["repair_failed"] += 1
                    grouped[f"{entity_type}.{asset_name}:repair_failed"] += 1

            local_value = _normalize_public_path(entity.get(local_key))
            remote_value = str(entity.get(remote_key) or "").strip()
            if not local_value and not remote_value:
                repair_counts["unrecoverable_upstream_gap"] += 1
                grouped[f"{entity_type}.{asset_name}:upstream_metadata_unavailable"] += 1
                if len(samples["unrecoverable_upstream_gap"]) < 10:
                    samples["unrecoverable_upstream_gap"].append(label)

    if mutated:
        write_json_atomic(data_path, data)

    fetch_results: List[Dict[str, Any]] = []
    if args.fetch_missing:
        refs = iter_asset_refs(data)
        for ref in refs:
            if _abs_local(ref["local_path"]).exists():
                continue
            result = download_asset("https://image.tmdb.org/t/p/original", REPO_ROOT, ref, args.timeout, args.retries)
            fetch_results.append(result)
        for result in fetch_results:
            if result.get("status") == "downloaded":
                repair_counts["fetched_missing_asset"] += 1
                grouped[f"{result['entity']}.{result['asset_type']}:fetched_missing_asset"] += 1
                if len(samples["fetched_missing_asset"]) < 10:
                    samples["fetched_missing_asset"].append(f"{result['entity']}:{result.get('tmdb_id')}:{result['local_path']}")
            elif result.get("status") == "failed":
                repair_counts["repair_failed"] += 1
                grouped[f"{result['entity']}.{result['asset_type']}:repair_failed"] += 1
                if len(samples["repair_failed"]) < 10:
                    samples["repair_failed"].append(f"{result['entity']}:{result.get('tmdb_id')}:{result.get('error')}")

    after_data = load_json(data_path)
    after_counts = _warning_snapshot(after_data)
    report = {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "result": "OK" if repair_counts["repair_failed"] == 0 else "FAIL",
        "fetch_missing_enabled": bool(args.fetch_missing),
        "before_warning_counts": dict(before_counts),
        "after_warning_counts": dict(after_counts),
        "repair_counts": {
            "repaired_from_local_asset": repair_counts["repaired_from_local_asset"],
            "repaired_from_metadata": repair_counts["repaired_from_metadata"],
            "fetched_missing_asset": repair_counts["fetched_missing_asset"],
            "unrecoverable_upstream_gap": repair_counts["unrecoverable_upstream_gap"],
            "repair_failed": repair_counts["repair_failed"],
        },
        "grouped_counts": dict(grouped),
        "samples": dict(samples),
    }
    report_path = Path(args.report_json) if args.report_json else (REPORT_DIR / f"asset_metadata_self_heal_{_stamp()}.json")
    write_json_atomic(report_path, report)
    print(json.dumps({"report": str(report_path), **report}, indent=2))
    return 0 if repair_counts["repair_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
