"""Static validation for schema_v1.sql."""

from __future__ import annotations

import json
from pathlib import Path


REQUIRED_TABLES = [
    "media_items",
    "shows",
    "seasons",
    "episodes",
    "movies",
    "watch_state",
    "watchlist",
    "favourites",
    "sync_queue",
    "sync_history",
    "media_files",
    "provider_registry",
    "runtime_config",
    "audit_log",
]


def validate_schema(path: Path | None = None) -> dict[str, object]:
    schema = path or Path(__file__).resolve().with_name("schema_v1.sql")
    text = schema.read_text(encoding="utf-8-sig")
    upper = text.upper()
    missing = [table for table in REQUIRED_TABLES if f"CREATE TABLE IF NOT EXISTS {table}" not in text]
    forbidden = [token for token in ("DROP TABLE", "DROP DATABASE", "TRUNCATE", "DELETE FROM") if token in upper]
    result = {
        "schema": schema.as_posix(),
        "required_tables": REQUIRED_TABLES,
        "missing_tables": missing,
        "forbidden_commands": forbidden,
        "postgresql_ddl": "BIGSERIAL" in text and "JSONB" in text and "TIMESTAMPTZ" in text,
        "json_fallback_documented": "JSON remains import/export/static fallback" in text,
        "binary_storage_default": "stores metadata and paths only" in text,
        "passed": not missing and not forbidden,
    }
    return result


def main() -> int:
    result = validate_schema()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
