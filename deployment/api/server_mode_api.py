"""Runnable /api/v1 server-mode scaffold.

Run locally:
    python deployment/api/server_mode_api.py

The server uses PostgreSQL when MYTV_POSTGRES_DSN or DATABASE_URL is configured
and psycopg is installed. Read-only fallback endpoints use generated JSON.
"""

from __future__ import annotations

import json
import shutil
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

API_DIR = Path(__file__).resolve().parent
POSTGRES_DIR = API_DIR.parent / "postgres"
for path in (API_DIR, POSTGRES_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from json_migration import import_to_postgres, migration_summary
from postgres_client import PostgresClient, PostgresUnavailable
from server_mode_config import ServerModeConfig


def load_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except Exception:
        return default


def response(handler: BaseHTTPRequestHandler, code: int, payload: dict) -> None:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def read_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length") or 0)
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8") or "{}")


def public_provider(row: dict) -> dict:
    private_keys = {"private_notes", "notes", "raw_status", "admin_notes"}
    return {key: value for key, value in row.items() if key not in private_keys}


def runtime_catalog_rows(config: ServerModeConfig) -> list[dict]:
    payload = load_json(config.data_path("data.json"), {})
    rows = []
    if not isinstance(payload, dict):
        return rows
    for media_type, key in (("movie", "movies"), ("show", "shows")):
        for item in payload.get(key, []) if isinstance(payload.get(key), list) else []:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "media_type": media_type,
                    "canonical_title": item.get("title") or item.get("name"),
                    "tmdb_id": item.get("tmdb_id") or item.get("id"),
                    "release_date": item.get("release_date") or item.get("first_air_date"),
                    "runtime_minutes": item.get("runtime"),
                    "poster_path": item.get("poster_local") or item.get("poster_path"),
                    "backdrop_path": item.get("backdrop_local") or item.get("backdrop_path"),
                    "source_json_path": "data/data.json",
                }
            )
    return rows


class ServerModeHandler(BaseHTTPRequestHandler):
    config = ServerModeConfig.from_env()
    db = PostgresClient(config.postgres_dsn)

    def log_message(self, fmt: str, *args):  # noqa: A003 - inherited API name
        sys.stderr.write("[server-mode-api] " + fmt % args + "\n")

    def route(self):
        parsed = urlparse(self.path)
        base = self.config.base_path
        if not parsed.path.startswith(base):
            return None, {}, []
        relative = parsed.path[len(base):].strip("/")
        return parsed, parse_qs(parsed.query), [part for part in relative.split("/") if part]

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API
        parsed, query, parts = self.route()
        if parsed is None:
            return response(self, 404, {"error": "path must start with /api/v1"})
        try:
            if parts == ["health"]:
                return response(self, 200, self.health())
            if parts == ["catalog"]:
                return response(self, 200, self.catalog(query))
            if len(parts) == 2 and parts[0] == "catalog":
                return response(self, 200, self.catalog_detail(parts[1]))
            if parts == ["watch-status"]:
                return response(self, 200, self.db_or_empty("watch_state"))
            if parts == ["watchlist"]:
                return response(self, 200, self.db_or_empty("watchlist"))
            if parts in (["favourites"], ["favorites"]):
                return response(self, 200, self.db_or_empty("favourites"))
            if parts == ["sync", "queue"]:
                return response(self, 200, self.db_or_empty("sync_queue"))
            if parts == ["sync", "history"]:
                return response(self, 200, self.db_or_empty("sync_history"))
            if parts == ["providers"]:
                return response(self, 200, self.providers())
            if parts == ["media-library", "inventory"]:
                return response(self, 200, self.db_or_empty("media_files"))
            if parts == ["runtime", "config"]:
                return response(self, 200, self.runtime_config())
            if parts == ["audit-log"]:
                return response(self, 200, self.db_or_empty("audit_log"))
            if len(parts) == 2 and parts[0] == "audit-log":
                return response(self, 200, self.audit_detail(parts[1]))
            return response(self, 404, {"error": "unknown endpoint", "parts": parts})
        except Exception as exc:
            return response(self, 500, {"error": str(exc), "type": exc.__class__.__name__})

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler API
        parsed, _query, parts = self.route()
        if parsed is None:
            return response(self, 404, {"error": "path must start with /api/v1"})
        body = read_body(self)
        try:
            if parts == ["catalog", "import-json"]:
                return response(self, 200, import_to_postgres(self.config, dry_run=bool(body.get("dry_run", True))))
            if parts == ["providers", "refresh"]:
                return response(self, 202, self.queue_operation("provider_registry", "providers_refresh", body))
            if len(parts) == 3 and parts[:2] == ["sync", "trakt"]:
                return response(self, 202, self.queue_operation("trakt", f"trakt_{parts[2]}", body))
            if parts == ["media-library", "scan"]:
                return response(self, 202, self.queue_operation("media_library", "media_inventory_scan", body))
            if parts == ["media-library", "qa"]:
                return response(self, 202, self.queue_operation("media_library", "media_file_qa", body))
            if parts == ["media-library", "remux"]:
                return response(self, 202, self.queue_operation("media_library", "media_file_remux", body))
            return response(self, 404, {"error": "unknown endpoint", "parts": parts})
        except Exception as exc:
            return response(self, 500, {"error": str(exc), "type": exc.__class__.__name__})

    def do_PUT(self):  # noqa: N802 - BaseHTTPRequestHandler API
        parsed, _query, parts = self.route()
        if parsed is None:
            return response(self, 404, {"error": "path must start with /api/v1"})
        body = read_body(self)
        try:
            if len(parts) == 2 and parts[0] == "watch-status":
                return response(self, 200, self.write_watch_status(parts[1], body))
            if len(parts) == 2 and parts[0] == "watchlist":
                return response(self, 200, self.write_boolean_state("watchlist", parts[1], body))
            if len(parts) == 2 and parts[0] in {"favourites", "favorites"}:
                return response(self, 200, self.write_boolean_state("favourites", parts[1], body))
            if len(parts) == 3 and parts[0] == "runtime" and parts[1] == "config":
                return response(self, 200, self.write_runtime_config(parts[2], body))
            return response(self, 404, {"error": "unknown endpoint", "parts": parts})
        except Exception as exc:
            return response(self, 500, {"error": str(exc), "type": exc.__class__.__name__})

    def health(self) -> dict:
        return {
            "status": "ok",
            "version": "v1",
            "mode": "server",
            "api_bind": f"{self.config.api_host}:{self.config.api_port}",
            "base_path": self.config.base_path,
            "repo_root": self.config.repo_root.as_posix(),
            "postgres": self.db.status(),
            "json_fallback_available": self.config.data_path("data.json").exists(),
            "media_tools": {
                "ffprobe": "available" if shutil.which("ffprobe") else "missing",
                "ffmpeg": "available" if shutil.which("ffmpeg") else "missing",
            },
            "stores_binary_assets": False,
        }

    def catalog(self, query: dict) -> dict:
        page = max(int(query.get("page", ["1"])[0]), 1)
        page_size = min(max(int(query.get("page_size", ["50"])[0]), 1), 250)
        media_type = query.get("type", [None])[0]
        q = (query.get("q", [""])[0] or "").lower()
        if self.db.ready:
            where = []
            params = []
            if media_type:
                where.append("media_type = %s")
                params.append(media_type)
            if q:
                where.append("lower(canonical_title) LIKE %s")
                params.append(f"%{q}%")
            clause = " WHERE " + " AND ".join(where) if where else ""
            rows = self.db.fetch_all(
                f"SELECT media_item_id, media_type, canonical_title, tmdb_id, release_date, poster_path, backdrop_path, still_path FROM media_items{clause} ORDER BY canonical_title LIMIT %s OFFSET %s",
                (*params, page_size, (page - 1) * page_size),
            )
            return {"source": "postgres", "page": page, "page_size": page_size, "items": rows}
        items = []
        for value in runtime_catalog_rows(self.config):
            title = value.get("canonical_title")
            row_type = value.get("media_type")
            if media_type and row_type != media_type:
                continue
            if q and title and q not in str(title).lower():
                continue
            items.append(
                {
                    "media_type": value.get("media_type"),
                    "canonical_title": value.get("canonical_title"),
                    "tmdb_id": value.get("tmdb_id"),
                    "release_date": value.get("release_date"),
                    "poster_path": value.get("poster_path"),
                    "backdrop_path": value.get("backdrop_path"),
                    "source_json_path": value.get("source_json_path"),
                }
            )
        start = (page - 1) * page_size
        return {"source": "json_fallback", "page": page, "page_size": page_size, "items": items[start:start + page_size], "total": len(items)}

    def catalog_detail(self, item_id: str) -> dict:
        path = self.config.data_path("catalog_detail", f"{item_id}.json")
        if path.exists():
            return {"source": "json_fallback", "item": load_json(path, {})}
        if self.db.ready and item_id.isdigit():
            row = self.db.fetch_one("SELECT * FROM media_items WHERE media_item_id = %s", (int(item_id),))
            if row:
                return {"source": "postgres", "item": row}
        return {"error": "not_found", "media_item_id": item_id}

    def providers(self) -> dict:
        payload = load_json(self.config.data_path("provider_registry.json"), [])
        rows = payload.values() if isinstance(payload, dict) else payload
        public = [public_provider(row) for row in rows if isinstance(row, dict)]
        return {"source": "json_fallback", "providers": public}

    def runtime_config(self) -> dict:
        config_json = load_json(self.config.web_path("config.json"), {})
        return {
            "source": "json_fallback",
            "api": {"base_path": self.config.base_path, "upstream": f"{self.config.api_host}:{self.config.api_port}"},
            "config": config_json,
            "secrets_returned": False,
        }

    def db_or_empty(self, table: str) -> dict:
        if not self.db.ready:
            return {"source": "not_configured", "postgres": self.db.status(), "items": []}
        if table in {"watch_state", "watchlist", "favourites"}:
            rows = self.db.fetch_all(
                f"""
                SELECT s.*, m.media_type, m.canonical_title, m.tmdb_id, m.parent_media_item_id
                FROM {table} s
                JOIN media_items m ON m.media_item_id = s.media_item_id
                ORDER BY s.updated_at DESC
                LIMIT 250
                """
            )
            return {"source": "postgres", "items": rows}
        rows = self.db.fetch_all(f"SELECT * FROM {table} ORDER BY 1 DESC LIMIT 250")
        return {"source": "postgres", "items": rows}

    def audit_detail(self, audit_id: str) -> dict:
        if not self.db.ready:
            return {"source": "not_configured", "postgres": self.db.status()}
        return {"source": "postgres", "item": self.db.fetch_one("SELECT * FROM audit_log WHERE audit_log_id = %s", (int(audit_id),))}

    def queue_operation(self, provider_key: str, operation_type: str, payload: dict) -> dict:
        if payload.get("dry_run", False):
            return {"queued": False, "dry_run": True, "operation_type": operation_type, "payload": payload}
        if not self.db.ready:
            return self.write_unavailable(operation_type)
        self.db.execute(
            "INSERT INTO sync_queue (provider_key, operation_type, payload_json) VALUES (%s, %s, %s::jsonb)",
            (provider_key, operation_type, PostgresClient.json_param(payload)),
        )
        return {"queued": True, "operation_type": operation_type}

    def write_unavailable(self, operation: str) -> dict:
        return {
            "queued": False,
            "operation": operation,
            "postgres": self.db.status(),
            "error": "PostgreSQL write path is unavailable; configure MYTV_POSTGRES_DSN and psycopg.",
        }

    def write_watch_status(self, item_id: str, body: dict) -> dict:
        status = body.get("watched_status")
        if status not in {"unwatched", "partial", "watched"}:
            return {"error": "watched_status must be unwatched, partial, or watched"}
        if not self.db.ready:
            return self.write_unavailable("watch_state_set")
        media_item_id = int(item_id)
        before = self.db.fetch_one("SELECT * FROM watch_state WHERE media_item_id = %s", (media_item_id,))
        self.db.execute(
            """
            INSERT INTO watch_state (media_item_id, watched_status, progress_percent, progress_seconds, pending_sync)
            VALUES (%s, %s, %s, %s, true)
            ON CONFLICT (media_item_id) DO UPDATE SET
                watched_status = EXCLUDED.watched_status,
                progress_percent = EXCLUDED.progress_percent,
                progress_seconds = EXCLUDED.progress_seconds,
                pending_sync = true
            """,
            (media_item_id, status, body.get("progress_percent", 100 if status == "watched" else 0), body.get("progress_seconds")),
        )
        after = self.db.fetch_one("SELECT * FROM watch_state WHERE media_item_id = %s", (media_item_id,))
        self.db.execute(
            "INSERT INTO audit_log (actor_type, event_type, entity_table, entity_id, media_item_id, before_json, after_json) VALUES ('api', 'watch_state_set', 'watch_state', %s, %s, %s::jsonb, %s::jsonb)",
            (after["watch_state_id"], media_item_id, PostgresClient.json_param(before), PostgresClient.json_param(after)),
        )
        self.queue_operation("trakt", "watch_state_set", {"media_item_id": media_item_id, "watched_status": status})
        return {"source": "postgres", "watch_state": after, "pending_sync": True}

    def write_boolean_state(self, table: str, item_id: str, body: dict) -> dict:
        if not self.db.ready:
            return self.write_unavailable(f"{table}_set")
        raw_active = body.get("is_active", True)
        if not isinstance(raw_active, bool):
            return {"error": "is_active must be true or false"}
        is_active = raw_active
        media_item_id = int(item_id)
        before = self.db.fetch_one(f"SELECT * FROM {table} WHERE media_item_id = %s", (media_item_id,))
        if table == "watchlist":
            sql = """
                INSERT INTO watchlist (media_item_id, is_active, list_source, removed_at, pending_sync)
                VALUES (%s, %s, 'api_import', CASE WHEN %s THEN NULL ELSE now() END, true)
                ON CONFLICT (media_item_id) DO UPDATE SET
                    is_active = EXCLUDED.is_active,
                    list_source = 'api_import',
                    removed_at = EXCLUDED.removed_at,
                    pending_sync = true
            """
            params = (media_item_id, is_active, is_active)
            provider = "trakt"
            operation_type = "watchlist_add" if is_active else "watchlist_remove"
            audit_event = operation_type
        else:
            sql = """
                INSERT INTO favourites (media_item_id, is_active, favourite_source, removed_at, pending_sync)
                VALUES (%s, %s, 'api_import', CASE WHEN %s THEN NULL ELSE now() END, true)
                ON CONFLICT (media_item_id) DO UPDATE SET
                    is_active = EXCLUDED.is_active,
                    favourite_source = 'api_import',
                    removed_at = EXCLUDED.removed_at,
                    pending_sync = true
            """
            params = (media_item_id, is_active, is_active)
            provider = "local"
            operation_type = "favourite_set"
            audit_event = operation_type
        self.db.execute(sql, params)
        after = self.db.fetch_one(f"SELECT * FROM {table} WHERE media_item_id = %s", (media_item_id,))
        entity_id = after["watchlist_id"] if table == "watchlist" else after["favourite_id"]
        self.db.execute(
            "INSERT INTO audit_log (actor_type, event_type, entity_table, entity_id, media_item_id, before_json, after_json) VALUES ('api', %s, %s, %s, %s, %s::jsonb, %s::jsonb)",
            (audit_event, table, entity_id, media_item_id, PostgresClient.json_param(before), PostgresClient.json_param(after)),
        )
        self.queue_operation(provider, operation_type, {"media_item_id": media_item_id, "is_active": is_active})
        return {"source": "postgres", table: after, "pending_sync": True}

    def write_runtime_config(self, key: str, body: dict) -> dict:
        if body.get("is_secret") and not body.get("secret_ref"):
            return {"error": "secret runtime config must use secret_ref; secret values are not stored"}
        if not self.db.ready:
            return self.write_unavailable("runtime_config_set")
        scope = body.get("scope", "global")
        self.db.execute(
            """
            INSERT INTO runtime_config (config_scope, config_key, config_value, secret_ref, is_secret, description)
            VALUES (%s, %s, %s::jsonb, %s, %s, %s)
            ON CONFLICT (config_scope, config_key) DO UPDATE SET
                config_value = EXCLUDED.config_value,
                secret_ref = EXCLUDED.secret_ref,
                is_secret = EXCLUDED.is_secret,
                description = EXCLUDED.description
            """,
            (scope, key, PostgresClient.json_param(body.get("value", {})), body.get("secret_ref"), bool(body.get("is_secret", False)), body.get("description")),
        )
        return {"source": "postgres", "scope": scope, "key": key, "stored_secret_value": False}


def main() -> int:
    config = ServerModeConfig.from_env()
    server = ThreadingHTTPServer((config.api_host, config.api_port), ServerModeHandler)
    print(f"server-mode API listening on http://{config.api_host}:{config.api_port}{config.base_path}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
