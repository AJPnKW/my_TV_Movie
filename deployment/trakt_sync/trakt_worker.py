"""Trakt sync worker scaffold.

This worker intentionally does not store credentials. It reads pending work from
PostgreSQL when configured and supports dry-run planning without network calls.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1] / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from postgres_client import PostgresClient
from server_mode_config import ServerModeConfig


def plan(operation: str) -> dict[str, object]:
    config = ServerModeConfig.from_env()
    client = PostgresClient(config.postgres_dsn)
    pending = []
    if client.ready:
        pending = client.fetch_all(
            "SELECT sync_queue_id, media_item_id, provider_key, operation_type, status, attempts FROM sync_queue WHERE provider_key = 'trakt' AND status IN ('queued', 'failed') ORDER BY priority, created_at LIMIT 100"
        )
    return {
        "operation": operation,
        "dry_run": True,
        "postgres": client.status(),
        "pending_trakt_items": pending,
        "local_first": True,
        "title_only_external_writes_allowed": False,
        "partial_default": "local_only",
        "favourites_default": "local_only",
        "secrets_loaded": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan Trakt sync queue work.")
    parser.add_argument("operation", choices=["pull", "push", "reconcile"], nargs="?", default="reconcile")
    args = parser.parse_args(argv)
    print(json.dumps(plan(args.operation), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
