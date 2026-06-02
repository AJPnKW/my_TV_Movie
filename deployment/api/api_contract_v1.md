# API Contract v1

Session: CODEX-FOREST  
Date: 2026-06-02  
Base path: `/api/v1`

## User Narrative

The app needs a server mode that can write user state, keep JSON fallback behavior, sync with Trakt/commercial sources, run Media Library inventory and QA, and support WD TV Live/local-network workflows. The static UI can keep working against JSON, but writes must move to the API/PostgreSQL path when server mode is enabled. No API route should require image/media binaries to be stored in PostgreSQL.

## Interpretation

The API is the write boundary between the current web app and PostgreSQL. It must provide catalog reads, state writes, queue-backed Trakt sync, provider/runtime config reads, Media Library scan/QA/remux jobs, and audit visibility. JSON import/export routes support migration and static fallback, not a second writable source of truth.

## Architecture Decision

Server mode writes to PostgreSQL first and records audit/sync evidence. JSON remains import/export/static fallback. All state-changing routes create `audit_log` rows, and all external sync work creates `sync_queue` and/or `sync_history` rows. API responses must include enough state metadata for the UI to show local, pending, synced, blocked, or conflict status without pretending a write was silently accepted by an external provider.

## Deployment Runtime Alignment

This API contract is designed to run on the Lime Green X1 lab VM foundation without changing Lime-owned provisioning scripts.

- App root: `/opt/mytv_movie`.
- Static entrypoint/reverse proxy: Nginx on `80/tcp`, with `443/tcp` reserved for later TLS.
- Local API upstream: `127.0.0.1:8000`, matching the lab VM reserved API port.
- Public API path: Nginx should route `/api/v1/*` to the local upstream when API implementation begins.
- PostgreSQL: local VM PostgreSQL service on `5432/tcp`; it should not be exposed beyond the VM/admin network.
- Media tools: server-side API workers use installed `ffprobe` and `ffmpeg` for Media Library QA/remux.
- Static fallback: existing `web/`, `assets/`, and generated JSON artifacts remain serveable by Nginx even when the API service is stopped.

## Common Rules

- Request and response bodies are JSON.
- State-changing routes return the persisted local state immediately.
- Writes are local-first; live Trakt/commercial response is not required for immediate UI update.
- No title-only external writes. Use TMDB/IMDb/TVDB/Trakt IDs where available.
- `partial` watched status is local unless a deliberate Trakt progress mapping exists.
- Favourites are local-only by default unless a deliberate external mapping exists.
- Secrets are never returned by API responses. Runtime config may return `secret_ref` metadata, not secret values.
- Image/media payloads are not accepted by default. Routes accept paths, metadata, and scan/QA results.

## Endpoints

### Health

#### `GET /health`

Returns API and dependency status.

Response:

```json
{
  "status": "ok",
  "version": "v1",
  "mode": "server",
  "postgres": "ok",
  "json_fallback_available": true,
  "media_tools": {
    "ffprobe": "available",
    "ffmpeg": "available"
  }
}
```

### Catalog

#### `GET /catalog`

Returns paged catalog rows from PostgreSQL.

Query parameters:

- `type`: `show`, `movie`, `season`, `episode`, or omitted for all
- `q`: search text
- `page`: 1-based page number
- `page_size`: bounded page size
- `include_state`: boolean, default `true`

#### `GET /catalog/{media_item_id}`

Returns one media item with type-specific details, hierarchy, assets paths, provider availability summary, and current local state.

#### `POST /catalog/import-json`

Imports selected JSON files into PostgreSQL.

Request:

```json
{
  "sources": [
    "data/inputs.json",
    "data/data.json",
    "data/catalog_index.json",
    "data/calendar.json",
    "data/catalog_detail"
  ],
  "dry_run": true
}
```

Rules:

- Dry run reports row counts, unresolved identities, and conflicts.
- Non-dry-run upserts and writes audit rows.
- The route must not delete source JSON.

#### `GET /catalog/export-json`

Exports PostgreSQL-backed state into static fallback JSON artifacts. Export must not include secrets.

### Watch Status

#### `GET /watch-status`

Returns watch-state rows with optional filters.

Query parameters:

- `media_item_id`
- `type`
- `status`: `unwatched`, `partial`, `watched`
- `pending_sync`: boolean

#### `PUT /watch-status/{media_item_id}`

Writes local watch status.

Request:

```json
{
  "watched_status": "partial",
  "progress_percent": 42.5,
  "progress_seconds": 1200,
  "last_watched_at": "2026-06-02T20:00:00Z",
  "client_event_id": "uuid-or-local-event-key"
}
```

Response includes the persisted `watch_state`, audit id, and queued sync id when applicable.

### Watchlist

#### `GET /watchlist`

Returns active watchlist rows.

#### `PUT /watchlist/{media_item_id}`

Adds/removes a media item from the watchlist.

Request:

```json
{
  "is_active": true,
  "client_event_id": "uuid-or-local-event-key"
}
```

Watchlist is independent from watched status and favourites.

### Favourites

#### `GET /favourites`

Returns active favourite rows.

#### `PUT /favourites/{media_item_id}`

Adds/removes a media item from favourites.

Request:

```json
{
  "is_active": true,
  "client_event_id": "uuid-or-local-event-key"
}
```

Favourites are independent from watched status and watchlist. By default the API returns `local_only_reason` because Trakt has no default favourite mapping in this contract.

### Trakt Sync

#### `GET /sync/queue`

Returns queued/running/failed/blocked sync work.

#### `POST /sync/trakt/pull`

Queues or runs a Trakt pull.

Request:

```json
{
  "dry_run": true,
  "include": ["watchlist", "history_movies", "history_episodes"]
}
```

Pull maps to Trakt watchlist and history data, normalizes by IDs, compares with local state, and reports conflicts before changing local rows unless `apply` is true.

#### `POST /sync/trakt/push`

Queues or runs pending local changes against Trakt.

Request:

```json
{
  "dry_run": true,
  "operation_ids": []
}
```

Push writes only ID-resolved rows. `partial` and favourites remain local-only unless explicitly mapped later.

#### `POST /sync/trakt/reconcile`

Compares local PostgreSQL state, sync queue, and latest Trakt pull evidence.

Request:

```json
{
  "strategy": "local_wins_when_newer",
  "dry_run": true
}
```

Allowed strategies:

- `local_wins_when_newer`
- `remote_wins_when_newer`
- `manual_only`

Every applied conflict resolution writes `audit_log` and `sync_history`.

#### `GET /sync/history`

Returns sync history records with provider, direction, status, counts, conflicts, and error summaries.

### Commercial/Provider Sync

#### `GET /providers`

Returns public provider registry rows. Private notes and raw admin status text are not returned for public UI.

#### `POST /providers/refresh`

Queues provider health/availability refresh. Does not expose secrets or private notes.

### Media Library Inventory

#### `GET /media-library/inventory`

Returns media file inventory and QA buckets.

Query parameters:

- `location_profile`: `home`, `trailer`, `portable`, `unknown`
- `qa_status`
- `media_item_id`
- `device_name`

#### `POST /media-library/scan`

Queues or runs local/network path discovery.

Request:

```json
{
  "location_profile": "home",
  "network_cidr": "192.168.1.0/24",
  "roots": ["\\\\DEVICE\\Videos", "/mnt/media"],
  "dry_run": true
}
```

Rules:

- Home network profile is `192.168.1.x`.
- Trailer network profile is `192.168.2.x`.
- The API records device/path discovery metadata, expected filename, actual filename, and first/last seen timestamps.

### Media QA and Remux

#### `POST /media-library/qa`

Queues or runs ffprobe QA.

Request:

```json
{
  "media_file_ids": [1, 2, 3],
  "dry_run": true
}
```

QA records container readability, duration, video stream, audio stream, codec, size, truncation/error status, extension/container mismatch, VLC status, and X-plore status buckets.

#### `POST /media-library/remux`

Queues safe ffmpeg stream-copy remux for eligible files.

Request:

```json
{
  "media_file_ids": [1],
  "dry_run": true,
  "mode": "stream_copy"
}
```

Rules:

- Default remux is stream copy only.
- No transcode unless a future contract explicitly allows it.
- Unsafe files are marked `unsafe` or `quarantined`, not silently skipped.

### Runtime Config

#### `GET /runtime/config`

Returns effective runtime config for UI mode, API mode, provider visibility, media roots, and fallback settings. Secret values are omitted.

#### `PUT /runtime/config/{scope}/{key}`

Writes non-secret runtime config. Secret values must be configured through environment/secret storage and referenced by `secret_ref`.

### Audit Log

#### `GET /audit-log`

Returns audit events with filtering by entity, media item, actor, event type, outcome, and date range.

#### `GET /audit-log/{audit_log_id}`

Returns one audit event with before/after JSON when authorized.

## Validation

- API contract states PostgreSQL as primary writable store.
- API contract states JSON import/export/static fallback.
- API contract states image/media binaries remain files/assets by default.
- Watch status, watchlist, and favourites have independent routes and data semantics.
- Trakt pull/push/reconcile routes preserve local-first queue behavior and no silent loss.
- Media Library routes include inventory, scan, ffprobe QA, safe remux, VLC, and X-plore status.

## Risks

- The current static UI needs a later API-client bridge before these routes are consumed directly.
- Trakt token/device-auth implementation details need a secret-management design in deployment/API implementation.
- Local network discovery behavior will vary by OS, SMB/NFS permissions, and trailer/home network visibility.
