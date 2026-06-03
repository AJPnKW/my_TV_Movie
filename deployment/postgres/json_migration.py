"""JSON import/export scaffolding for server-mode PostgreSQL migration."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

API_DIR = Path(__file__).resolve().parents[1] / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from postgres_client import PostgresClient, PostgresUnavailable
from server_mode_config import ServerModeConfig


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def iter_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for item in value:
            yield from iter_dicts(item)


def title_from(row: dict[str, Any]) -> str | None:
    for key in ("title", "name", "canonical_title", "show_title", "movie_title"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def media_type_from(row: dict[str, Any], fallback: str | None = None) -> str | None:
    raw = row.get("media_type") or row.get("type") or fallback
    if not isinstance(raw, str):
        return None
    raw = raw.lower().strip()
    if raw in {"tv", "series"}:
        return "show"
    if raw in {"show", "season", "episode", "movie"}:
        return raw
    return None


def tmdb_id_from(row: dict[str, Any]) -> int | None:
    for key in ("tmdb_id", "tmdb", "id"):
        value = row.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def collect_catalog_candidates(config: ServerModeConfig) -> list[dict[str, Any]]:
    candidates: dict[tuple[str, int | str], dict[str, Any]] = {}
    sources = [
        config.data_path("inputs.json"),
        config.data_path("data.json"),
        config.data_path("catalog_index.json"),
        config.data_path("calendar.json"),
    ]
    detail_root = config.data_path("catalog_detail")
    if detail_root.exists():
        sources.extend(sorted(detail_root.glob("*.json")))

    for source in sources:
        if not source.exists():
            continue
        try:
            payload = load_json(source)
        except Exception as exc:
            candidates[(f"error:{source}", source.as_posix())] = {
                "source_json_path": source.as_posix(),
                "import_error": str(exc),
            }
            continue
        fallback_type = None
        if source.name == "calendar.json":
            fallback_type = "episode"
        for row in iter_dicts(payload):
            title = title_from(row)
            media_type = media_type_from(row, fallback_type)
            tmdb_id = tmdb_id_from(row)
            if not title or not media_type:
                continue
            key = (media_type, tmdb_id if tmdb_id is not None else f"{source}:{title}")
            candidates.setdefault(
                key,
                {
                    "media_type": media_type,
                    "canonical_title": title,
                    "tmdb_id": tmdb_id,
                    "source_json_path": source.as_posix(),
                    "source_json_key": str(tmdb_id or title),
                    "source_hash": stable_hash(row),
                    "raw_json": row,
                },
            )
    return list(candidates.values())


def migration_summary(config: ServerModeConfig) -> dict[str, Any]:
    candidates = collect_catalog_candidates(config)
    by_type: dict[str, int] = {}
    for row in candidates:
        by_type[row.get("media_type", "unknown")] = by_type.get(row.get("media_type", "unknown"), 0) + 1
    return {
        "mode": "dry_run",
        "candidate_count": len(candidates),
        "by_type": by_type,
        "sources": {
            "inputs_json": config.data_path("inputs.json").exists(),
            "data_json": config.data_path("data.json").exists(),
            "catalog_index_json": config.data_path("catalog_index.json").exists(),
            "calendar_json": config.data_path("calendar.json").exists(),
            "catalog_detail_dir": config.data_path("catalog_detail").exists(),
        },
        "postgres_primary": True,
        "json_fallback": True,
        "stores_binary_assets": False,
    }


def import_to_postgres(config: ServerModeConfig, dry_run: bool = True) -> dict[str, Any]:
    summary = migration_summary(config)
    if dry_run:
        return summary
    client = PostgresClient(config.postgres_dsn)
    if not client.ready:
        raise PostgresUnavailable(f"PostgreSQL unavailable: {client.status()}")

    inserted = 0
    for row in collect_catalog_candidates(config):
        if "import_error" in row:
            continue
        existing = None
        if row.get("tmdb_id") is not None:
            existing = client.fetch_one(
                "SELECT media_item_id FROM media_items WHERE media_type = %s AND tmdb_id = %s",
                (row["media_type"], row["tmdb_id"]),
            )
        if existing:
            continue
        client.execute(
            """
            INSERT INTO media_items (
                media_type, canonical_title, tmdb_id, source_json_path,
                source_json_key, source_hash, raw_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                row["media_type"],
                row["canonical_title"],
                row.get("tmdb_id"),
                row.get("source_json_path"),
                row.get("source_json_key"),
                row.get("source_hash"),
                PostgresClient.json_param(row.get("raw_json", {})),
            ),
        )
        inserted += 1
    summary["mode"] = "applied"
    summary["inserted_media_items"] = inserted
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import current JSON artifacts into PostgreSQL.")
    parser.add_argument("--apply", action="store_true", help="Apply inserts; default is dry run.")
    args = parser.parse_args(argv)
    result = import_to_postgres(ServerModeConfig.from_env(), dry_run=not args.apply)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
