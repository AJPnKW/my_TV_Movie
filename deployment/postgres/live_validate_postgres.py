"""Apply the v1 schema and prove live PostgreSQL write/read/rollback behavior."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception as exc:  # pragma: no cover - validated on the lab VM
    print(json.dumps({"passed": False, "error": f"psycopg import failed: {exc}"}))
    raise SystemExit(1)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "deployment" / "postgres" / "schema_v1.sql"


def validate_live_database(dsn: str, expected_database: str, expected_user: str) -> dict[str, object]:
    checks: dict[str, object] = {
        "postgres_reachable": False,
        "database_exists": False,
        "app_user_exists": False,
        "schema_applied": False,
        "test_insert": False,
        "test_read": False,
        "rollback_cleanup": False,
    }
    schema_sql = SCHEMA.read_text(encoding="utf-8-sig")

    with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as conn:
        identity = conn.execute(
            "SELECT current_database() AS database_name, current_user AS user_name, version() AS version"
        ).fetchone()
        checks["postgres_reachable"] = True
        checks["database_exists"] = identity["database_name"] == expected_database
        checks["app_user_exists"] = identity["user_name"] == expected_user
        checks["database_name"] = identity["database_name"]
        checks["user_name"] = identity["user_name"]
        checks["server_version"] = identity["version"].split(",", 1)[0]
        conn.execute(schema_sql)
        missing_tables = conn.execute(
            """
            SELECT required.table_name
            FROM unnest(%s::text[]) AS required(table_name)
            LEFT JOIN information_schema.tables actual
              ON actual.table_schema = 'public'
             AND actual.table_name = required.table_name
            WHERE actual.table_name IS NULL
            """,
            (
                [
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
                ],
            ),
        ).fetchall()
        checks["missing_tables"] = [row["table_name"] for row in missing_tables]
        checks["schema_applied"] = not checks["missing_tables"]

    test_key = f"live_validation_{uuid.uuid4().hex}"
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        inserted = conn.execute(
            """
            INSERT INTO runtime_config (config_scope, config_key, config_value, description)
            VALUES ('api', %s, %s::jsonb, 'temporary live PostgreSQL validation row')
            RETURNING runtime_config_id, config_key
            """,
            (test_key, json.dumps({"validation": True})),
        ).fetchone()
        checks["test_insert"] = inserted["config_key"] == test_key
        read_back = conn.execute(
            "SELECT config_key, config_value FROM runtime_config WHERE runtime_config_id = %s",
            (inserted["runtime_config_id"],),
        ).fetchone()
        checks["test_read"] = bool(
            read_back
            and read_back["config_key"] == test_key
            and read_back["config_value"].get("validation") is True
        )
        conn.rollback()

    with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as conn:
        remaining = conn.execute(
            "SELECT count(*) AS count FROM runtime_config WHERE config_key = %s",
            (test_key,),
        ).fetchone()
        checks["rollback_cleanup"] = remaining["count"] == 0

    required_checks = (
        "postgres_reachable",
        "database_exists",
        "app_user_exists",
        "schema_applied",
        "test_insert",
        "test_read",
        "rollback_cleanup",
    )
    checks["passed"] = all(checks[name] is True for name in required_checks)
    checks["stores_binary_assets"] = False
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the live my_TV_Movie PostgreSQL runtime.")
    parser.add_argument(
        "--dsn",
        default=os.environ.get("MYTV_POSTGRES_DSN") or os.environ.get("DATABASE_URL"),
        help="PostgreSQL DSN. Defaults to MYTV_POSTGRES_DSN or DATABASE_URL.",
    )
    parser.add_argument("--expected-database", default="mytv_movie")
    parser.add_argument("--expected-user", default="mytv_movie")
    args = parser.parse_args(argv)
    if not args.dsn:
        print(json.dumps({"passed": False, "error": "MYTV_POSTGRES_DSN or --dsn is required"}, indent=2))
        return 1
    try:
        result = validate_live_database(args.dsn, args.expected_database, args.expected_user)
    except Exception as exc:
        result = {"passed": False, "error": str(exc), "error_type": exc.__class__.__name__}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
