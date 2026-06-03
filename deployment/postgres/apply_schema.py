"""Apply schema_v1.sql to the configured PostgreSQL database."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1] / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from postgres_client import PostgresClient, PostgresUnavailable
from server_mode_config import ServerModeConfig


def apply_schema(dry_run: bool = False) -> dict[str, object]:
    config = ServerModeConfig.from_env()
    schema_path = config.schema_path()
    sql = schema_path.read_text(encoding="utf-8-sig")
    result = {
        "schema_path": schema_path.as_posix(),
        "dry_run": dry_run,
        "postgres": "not_checked",
        "contains_destructive_commands": bool(re.search(r"(?im)^\s*(DROP|TRUNCATE|DELETE\s+FROM)\b", sql)),
    }
    if dry_run:
        result["statement_count_hint"] = sql.count(";")
        return result
    client = PostgresClient(config.postgres_dsn)
    if not client.ready:
        raise PostgresUnavailable(f"PostgreSQL unavailable: {client.status()}")
    with client.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    result["postgres"] = "applied"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply deployment/postgres/schema_v1.sql")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(apply_schema(dry_run=args.dry_run), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
