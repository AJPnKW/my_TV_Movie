"""Small PostgreSQL wrapper used by server-mode scaffolds.

The repo intentionally does not vendor a database driver. On the VM, install
psycopg/psycopg-binary in the API runtime environment and set MYTV_POSTGRES_DSN.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Iterable

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover - depends on VM runtime packages
    psycopg = None
    dict_row = None


class PostgresUnavailable(RuntimeError):
    pass


class PostgresClient:
    def __init__(self, dsn: str | None):
        self.dsn = dsn

    @property
    def configured(self) -> bool:
        return bool(self.dsn)

    @property
    def driver_available(self) -> bool:
        return psycopg is not None

    @property
    def ready(self) -> bool:
        return self.configured and self.driver_available

    def status(self) -> str:
        if not self.configured:
            return "not_configured"
        if not self.driver_available:
            return "driver_unavailable"
        try:
            with self.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return "ok"
        except Exception as exc:  # pragma: no cover - requires live DB
            return f"error: {exc.__class__.__name__}"

    @contextmanager
    def connection(self):
        if not self.configured:
            raise PostgresUnavailable("MYTV_POSTGRES_DSN or DATABASE_URL is not configured")
        if not self.driver_available:
            raise PostgresUnavailable("psycopg is not installed in this Python environment")
        conn = psycopg.connect(self.dsn, row_factory=dict_row)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def fetch_all(self, sql: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params or ()))
                return list(cur.fetchall())

    def fetch_one(self, sql: str, params: Iterable[Any] | None = None) -> dict[str, Any] | None:
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> None:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params or ()))

    @staticmethod
    def json_param(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
