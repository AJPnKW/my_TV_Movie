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
DATA_JSON = DATA_DIR / "data.json"
REPORT_DIR = REPO_ROOT / "reports" / "availability_status"
REGIONS = ("CA", "US", "GB", "AU")
RETIRED_WATCH_KEYS = ("watch_sources", "source_options", "watchProviders")
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


def _validate_links(path_label: str, links: Any, issues: List[str]) -> None:
    if links in (None, ""):
        return
    if isinstance(links, dict):
        for key, href_value in links.items():
            label = _safe_text(key)
            href = _safe_text(href_value)
            if not label:
                issues.append(f"{path_label} links contains an empty key")
            if not href:
                issues.append(f"{path_label} links.{label or '<empty>'} missing href")
            elif not (href.startswith("http://") or href.startswith("https://") or href.startswith("/")):
                issues.append(f"{path_label} links.{label or '<empty>'} invalid href")
        return
    if not isinstance(links, list):
        issues.append(f"{path_label} links must be a list")
        return
    seen = set()
    for idx, row in enumerate(links):
        if not isinstance(row, dict):
            issues.append(f"{path_label} links[{idx}] must be an object")
            continue
        href = _safe_text(row.get("href"))
        label = _safe_text(row.get("label"))
        if not label:
            issues.append(f"{path_label} links[{idx}] missing label")
        if not href:
            issues.append(f"{path_label} links[{idx}] missing href")
        elif not (href.startswith("http://") or href.startswith("https://") or href.startswith("/")):
            issues.append(f"{path_label} links[{idx}] invalid href")
        key = (label, href)
        if key in seen:
            issues.append(f"{path_label} duplicate link {label}")
        seen.add(key)


def _validate_watch_providers(path_label: str, providers: Any, issues: List[str]) -> None:
    if providers in (None, ""):
        return
    if not isinstance(providers, dict):
        issues.append(f"{path_label} watch_providers must be an object")
        return
    for region in REGIONS:
        rows = providers.get(region)
        if rows in (None, ""):
            continue
        if not isinstance(rows, list):
            issues.append(f"{path_label} watch_providers.{region} must be a list")
            continue
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                issues.append(f"{path_label} watch_providers.{region}[{idx}] must be an object")
                continue
            if not _safe_text(row.get("provider_name")):
                issues.append(f"{path_label} watch_providers.{region}[{idx}] missing provider_name")


def _assert_no_retired_watch_keys(path_label: str, entity: Dict[str, Any], issues: List[str]) -> None:
    for key in RETIRED_WATCH_KEYS:
        if key in entity:
            issues.append(f"{path_label} contains retired key {key}")


def _validate_catalog_entity(path_label: str, payload: Dict[str, Any], media_kind: str, issues: List[str], counts: Counter) -> None:
    counts[f"{media_kind}:count"] += 1
    _assert_no_retired_watch_keys(path_label, payload, issues)
    _validate_links(path_label, payload.get("links"), issues)
    _validate_watch_providers(path_label, payload.get("watch_providers"), issues)
    availability = _safe_text(payload.get("availability_status"))
    counts[f"{media_kind}:availability:{availability or 'missing'}"] += 1
    if availability not in ALLOWED_AVAILABILITY:
        issues.append(f"{path_label} invalid availability_status={availability!r}")

    if media_kind == "tv":
        seasons = payload.get("seasons")
        if not isinstance(seasons, list):
            issues.append(f"{path_label} tv seasons must be a list")
            return
        for season_idx, season in enumerate(seasons):
            if not isinstance(season, dict):
                issues.append(f"{path_label} seasons[{season_idx}] must be an object")
                continue
            season_label = f"{path_label} seasons[{season_idx}]"
            _assert_no_retired_watch_keys(season_label, season, issues)
            _validate_links(season_label, season.get("links"), issues)
            episodes = season.get("episodes")
            if not isinstance(episodes, list):
                issues.append(f"{season_label} episodes must be a list")
                continue
            for episode_idx, episode in enumerate(episodes):
                if not isinstance(episode, dict):
                    issues.append(f"{season_label}.episodes[{episode_idx}] must be an object")
                    continue
                episode_label = f"{season_label}.episodes[{episode_idx}]"
                _assert_no_retired_watch_keys(episode_label, episode, issues)
                _validate_links(episode_label, episode.get("links"), issues)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-json", default=str(DATA_JSON))
    parser.add_argument("--report-json", default="")
    args = parser.parse_args()

    data_path = Path(args.data_json)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    issues: List[str] = []
    counts = Counter()

    if not data_path.exists():
        issues.append(f"missing {data_path}")

    data = _read_json(data_path) if data_path.exists() else {}

    shows = data.get("shows") if isinstance(data, dict) else None
    movies = data.get("movies") if isinstance(data, dict) else None
    if not isinstance(shows, list):
        issues.append("data.json shows must be a list")
        shows = []
    if not isinstance(movies, list):
        issues.append("data.json movies must be a list")
        movies = []

    seen_ids: set[tuple[str, int]] = set()
    calendar_entries = 0
    rows: list[tuple[str, int, Any]] = [("tv", idx, row) for idx, row in enumerate(shows)]
    rows.extend(("movie", idx, row) for idx, row in enumerate(movies))
    for media_kind, idx, row in rows:
        if not isinstance(row, dict):
            issues.append("data.json catalog entry must be an object")
            continue
        for field in ("id", "title"):
            if not _safe_text(row.get(field)):
                issues.append(f"data.json {media_kind}[{idx}] missing {field}")
        entity_id = int(row.get("id") or row.get("tmdb_id") or 0)
        entity_key = (media_kind, entity_id)
        if entity_id:
            if entity_key in seen_ids:
                issues.append(f"data.json duplicate catalog entry {media_kind}:{entity_id}")
            seen_ids.add(entity_key)
        if any(key in row for key in RETIRED_WATCH_KEYS):
            issues.append(f"data.json {media_kind}[{idx}] contains retired watch keys")
        _validate_catalog_entity(f"data.json {media_kind}[{idx}]", row, media_kind, issues, counts)
        if media_kind == "movie" and _safe_text(row.get("release_date"))[:10]:
            calendar_entries += 1
        if media_kind == "tv":
            for season in row.get("seasons") or []:
                if not isinstance(season, dict):
                    continue
                for episode in season.get("episodes") or []:
                    if isinstance(episode, dict) and _safe_text(episode.get("air_date"))[:10]:
                        calendar_entries += 1

    if not calendar_entries:
        issues.append("data.json must contain at least one dated movie or episode for calendar derivation")

    report = {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "result": "OK" if not issues else "FAIL",
        "issue_count": len(issues),
        "counts": dict(counts),
        "catalog_entry_count": len(shows) + len(movies),
        "derived_calendar_entry_count": calendar_entries,
        "issues_sample": issues[:100],
    }
    report_path = Path(args.report_json) if args.report_json else (REPORT_DIR / f"runtime_catalog_integrity_{_stamp()}.json")
    _write_json(report_path, report)
    print(json.dumps({"report": str(report_path), **report}, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
