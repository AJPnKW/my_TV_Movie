#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
INDEX_JSON = DATA_DIR / "catalog_index.json"
CALENDAR_JSON = DATA_DIR / "calendar.json"
DETAIL_DIR = DATA_DIR / "catalog_detail"
REPORT_DIR = REPO_ROOT / "reports" / "availability_status"
REGIONS = ("CA", "US", "GB", "AU")
LEGACY_WATCH_KEYS = ("watch_sources", "source_options", "watch_providers", "watchProviders")
ALLOWED_AVAILABILITY = {"not_yet_released", "available", "unavailable", "unknown", ""}


def _stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    json.loads(tmp.read_text(encoding="utf-8"))
    tmp.replace(path)


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _validate_watch_block(path_label: str, watch: Any, issues: List[str]) -> None:
    if not isinstance(watch, dict):
        issues.append(f"{path_label} watch must be an object")
        return
    embed = watch.get("embed")
    providers = watch.get("providers")
    if not isinstance(embed, list):
        issues.append(f"{path_label} watch.embed must be a list")
    else:
        seen = set()
        for idx, row in enumerate(embed):
            if not isinstance(row, dict):
                issues.append(f"{path_label} watch.embed[{idx}] must be an object")
                continue
            for field in ("key", "label", "href", "type"):
                if not _safe_text(row.get(field)):
                    issues.append(f"{path_label} watch.embed[{idx}] missing {field}")
            href = _safe_text(row.get("href"))
            if href and not (href.startswith("http://") or href.startswith("https://") or href.startswith("/")):
                issues.append(f"{path_label} watch.embed[{idx}] invalid href")
            key = (_safe_text(row.get("key")), href)
            if key in seen:
                issues.append(f"{path_label} duplicate watch.embed entry {key[0]}")
            seen.add(key)
    if not isinstance(providers, dict):
        issues.append(f"{path_label} watch.providers must be an object")
    else:
        for region in REGIONS:
            rows = providers.get(region)
            if not isinstance(rows, list):
                issues.append(f"{path_label} watch.providers.{region} must be a list")
                continue
            for idx, row in enumerate(rows):
                if not isinstance(row, dict):
                    issues.append(f"{path_label} watch.providers.{region}[{idx}] must be an object")
                    continue
                if not _safe_text(row.get("provider_name")):
                    issues.append(f"{path_label} watch.providers.{region}[{idx}] missing provider_name")


def _assert_no_legacy_watch_keys(path_label: str, entity: Dict[str, Any], issues: List[str]) -> None:
    for key in LEGACY_WATCH_KEYS:
        if key in entity:
            issues.append(f"{path_label} contains legacy key {key}")


def _validate_detail(path: Path, payload: Dict[str, Any], issues: List[str], counts: Counter) -> None:
    entity_type = _safe_text(payload.get("type"))
    counts[f"{entity_type or 'unknown'}:count"] += 1
    _assert_no_legacy_watch_keys(str(path), payload, issues)
    _validate_watch_block(str(path), payload.get("watch"), issues)
    availability = _safe_text(payload.get("availability_status"))
    counts[f"{entity_type or 'unknown'}:availability:{availability or 'missing'}"] += 1
    if availability not in ALLOWED_AVAILABILITY:
        issues.append(f"{path} invalid availability_status={availability!r}")

    if entity_type == "tv":
        seasons = payload.get("seasons")
        if not isinstance(seasons, list):
            issues.append(f"{path} tv seasons must be a list")
            return
        for season_idx, season in enumerate(seasons):
            if not isinstance(season, dict):
                issues.append(f"{path} seasons[{season_idx}] must be an object")
                continue
            _assert_no_legacy_watch_keys(f"{path} seasons[{season_idx}]", season, issues)
            _validate_watch_block(f"{path} seasons[{season_idx}]", season.get("watch"), issues)
            episodes = season.get("episodes")
            if not isinstance(episodes, list):
                issues.append(f"{path} seasons[{season_idx}] episodes must be a list")
                continue
            for episode_idx, episode in enumerate(episodes):
                if not isinstance(episode, dict):
                    issues.append(f"{path} seasons[{season_idx}].episodes[{episode_idx}] must be an object")
                    continue
                _assert_no_legacy_watch_keys(f"{path} seasons[{season_idx}].episodes[{episode_idx}]", episode, issues)
                _validate_watch_block(f"{path} seasons[{season_idx}].episodes[{episode_idx}]", episode.get("watch"), issues)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-json", default=str(INDEX_JSON))
    parser.add_argument("--calendar-json", default=str(CALENDAR_JSON))
    parser.add_argument("--detail-dir", default=str(DETAIL_DIR))
    parser.add_argument("--report-json", default="")
    args = parser.parse_args()

    index_path = Path(args.index_json)
    calendar_path = Path(args.calendar_json)
    detail_dir = Path(args.detail_dir)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    issues: List[str] = []
    counts = Counter()

    if not index_path.exists():
      issues.append(f"missing {index_path}")
    if not calendar_path.exists():
      issues.append(f"missing {calendar_path}")
    if not detail_dir.exists():
      issues.append(f"missing {detail_dir}")

    index = _read_json(index_path) if index_path.exists() else {}
    calendar = _read_json(calendar_path) if calendar_path.exists() else {}

    shows = index.get("shows") if isinstance(index, dict) else None
    movies = index.get("movies") if isinstance(index, dict) else None
    if not isinstance(shows, list):
        issues.append("catalog_index.json shows must be a list")
        shows = []
    if not isinstance(movies, list):
        issues.append("catalog_index.json movies must be a list")
        movies = []

    detail_files = sorted(detail_dir.glob("*.json")) if detail_dir.exists() else []
    detail_ids = set()
    for path in detail_files:
        payload = _read_json(path)
        if not isinstance(payload, dict):
            issues.append(f"{path} root must be an object")
            continue
        detail_id = int(payload.get("id") or 0)
        if not detail_id:
            issues.append(f"{path} missing id")
            continue
        detail_ids.add(detail_id)
        _validate_detail(path, payload, issues, counts)

    for row in shows + movies:
        if not isinstance(row, dict):
            issues.append("catalog_index entry must be an object")
            continue
        for field in ("id", "type", "title", "detail_path"):
            if not _safe_text(row.get(field)):
                issues.append(f"catalog_index entry missing {field}")
        if int(row.get("id") or 0) not in detail_ids:
            issues.append(f"catalog_index entry {row.get('id')} missing detail file")
        if any(key in row for key in LEGACY_WATCH_KEYS):
            issues.append(f"catalog_index entry {row.get('id')} contains legacy watch keys")

    days = calendar.get("days") if isinstance(calendar, dict) else None
    if not isinstance(days, dict):
        issues.append("calendar.json days must be an object")
        days = {}
    for date_key, entries in days.items():
        if not isinstance(entries, list):
            issues.append(f"calendar.json days[{date_key}] must be a list")
            continue
        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                issues.append(f"calendar.json days[{date_key}][{idx}] must be an object")
                continue
            kind = _safe_text(entry.get("kind"))
            if kind not in {"movie", "episode"}:
                issues.append(f"calendar.json days[{date_key}][{idx}] invalid kind={kind!r}")
            if kind == "movie" and not int(entry.get("id") or entry.get("tmdb_id") or 0):
                issues.append(f"calendar.json days[{date_key}][{idx}] movie missing id")
            if kind == "episode":
                if not int(entry.get("show_id") or entry.get("show_tmdb_id") or 0):
                    issues.append(f"calendar.json days[{date_key}][{idx}] episode missing show_id")
                if entry.get("season_number") is None or _safe_text(entry.get("season_number")) == "":
                    issues.append(f"calendar.json days[{date_key}][{idx}] episode missing season_number")
                if entry.get("episode_number") is None or _safe_text(entry.get("episode_number")) == "":
                    issues.append(f"calendar.json days[{date_key}][{idx}] episode missing episode_number")
            if any(key in entry for key in LEGACY_WATCH_KEYS):
                issues.append(f"calendar.json days[{date_key}][{idx}] contains legacy watch keys")

    report = {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "result": "OK" if not issues else "FAIL",
        "issue_count": len(issues),
        "counts": dict(counts),
        "detail_file_count": len(detail_files),
        "issues_sample": issues[:100],
    }
    report_path = Path(args.report_json) if args.report_json else (REPORT_DIR / f"runtime_catalog_integrity_{_stamp()}.json")
    _write_json(report_path, report)
    print(json.dumps({"report": str(report_path), **report}, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
