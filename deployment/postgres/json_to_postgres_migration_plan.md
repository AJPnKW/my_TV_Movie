# JSON to PostgreSQL Migration Plan

Session: CODEX-FOREST  
Date: 2026-06-02  
Scope: server-backed application architecture for writable state, sync, and Media Library inventory.

## User Narrative

The project is moving from a static GitHub Pages-style media app into a server-backed local/VM runtime. The existing JSON files must not be thrown away: `data/inputs.json` remains the canonical input file, `data/data.json` and related catalog JSON remain generated runtime/static fallback outputs, and JSON export must remain available for recovery or GitHub Pages fallback. The new server mode needs PostgreSQL for writable watch status, watchlist, favourites, sync queue/history, provider registry, runtime config, audit records, and Media Library file inventory. Images and media files stay on disk under `assets/`, local shares, or configured media roots; PostgreSQL stores only identifiers, metadata, paths, and QA state by default.

## Interpretation

Server mode imports the current JSON/runtime artifacts into normalized PostgreSQL tables, then uses PostgreSQL as the primary write store for state changes. JSON remains:

- import source for catalog bootstrap and recovery
- export target for static fallback
- compatibility bridge for existing UI data loaders until API-client mode is implemented
- audit evidence for generated runtime data

The migration must be additive and reversible at the data level: no destructive migration commands, no deletion of source JSON, no silent loss of user watch actions, no secret values stored in database seed files.

## Architecture Decision

Use `deployment/postgres/schema_v1.sql` as the v1 PostgreSQL DDL. Migration tooling should perform read/validate/upsert/export steps rather than direct destructive rewrites.

The migration plan aligns with the Lime Green VM foundation:

- migration/import/export tooling runs from the app root `/opt/mytv_movie` on the X1 lab VM or equivalent local checkout
- PostgreSQL writes target the local VM PostgreSQL service on `5432/tcp`
- API-triggered imports use the local API upstream reserved on `127.0.0.1:8000` and exposed through Nginx as `/api/v1/*`
- Nginx can continue serving static JSON fallback artifacts from `web/`, `assets/`, and generated `data/` files while PostgreSQL/API implementation is being staged
- VM provisioning scripts remain owned by Lime Green; this plan defines data behavior only

Recommended flow:

1. Read `data/inputs.json` and reject malformed active rows before database writes.
2. Read generated `data/data.json`, `data/catalog_index.json`, `data/calendar.json`, and `data/catalog_detail/*.json` as enrichment/runtime snapshots.
3. Upsert identity rows into `media_items`, then type-specific rows into `shows`, `seasons`, `episodes`, and `movies`.
4. Import local watch state from current runtime state JSON/queue artifacts into `watch_state`, `watchlist`, and `favourites`.
5. Import provider/config files into `provider_registry` and `runtime_config`, storing logo/artwork paths only.
6. Import Media Library inventory/QA outputs into `media_files`.
7. Write `audit_log` entries for import batches and any conflict decisions.
8. Export PostgreSQL state back to JSON fallback files when static mode artifacts need to be regenerated.

## Source to Table Map

| Existing file/source | Table(s) | Mapping rule |
|---|---|---|
| `data/inputs.json` | `media_items`, `shows`, `movies`, `audit_log` | Canonical user-maintained show/movie input. Active rows become identity seeds. Inactive rows can be retained as import audit evidence but must not produce active runtime catalog rows unless explicitly restored. |
| `data/data.json` | `media_items`, `shows`, `seasons`, `episodes`, `movies` | Generated runtime output enriches titles, release dates, runtime, overviews, poster/backdrop/still paths, season/episode structure, and TMDB-derived metadata. |
| `data/catalog_index.json` | `media_items` | Catalog lookup snapshot. Use to verify generated catalog membership and source JSON keys. |
| `data/catalog_detail/*.json` | `media_items.raw_json`, type-specific tables | Detail snapshots preserve fetched metadata and per-item raw source evidence. Store compact raw JSON references where useful; do not store image binaries. |
| `data/calendar.json` | `episodes`, `media_items` | Air-date-oriented episode data. Use as validation/enrichment for `episodes.air_date` and release state. |
| `data/watch_state_queue.json` | `sync_queue`, `watch_state`, `watchlist`, `favourites`, `audit_log` | Existing local-first queue becomes pending queue records. Payloads map to state/watchlist/favourite rows without dropping unprocessed actions. |
| Browser local watch state/exported state artifacts, when present | `watch_state`, `watchlist`, `favourites` | Import as local source with `pending_sync` preserved when not confirmed by sync history. Watchlist and favourites remain independent from watched status. |
| `data/provider_registry.json` | `provider_registry` | Provider key/name/status/health/template/logo path. Blocked/candidate/degraded states are preserved; public UI must not expose private admin notes. |
| `data/watch_source_availability.json` | `provider_registry.health_json`, `sync_history` | Availability/health evidence. Preserve blocked/degraded reasons as private health metadata. |
| `web/config.json` | `runtime_config`, `provider_registry` | Runtime config, streaming embed provider registry, candidate/blocked flags, Full/Light settings, and API mode defaults. Secret values must remain environment/secret references, not literal database values. |
| `web/Media_Library.json` | `media_files`, `runtime_config` | Static Media Library page data and summary buckets become inventory rows and display config. |
| `tools/media_renamer/media_reference.json` | `media_items`, `media_files` | Catalog-to-file matching reference. Use expected filenames and media identity links. |
| `tools/media_renamer/media_library_config.json` | `runtime_config` | Local root/share/device/path profiles, including home/trailer behavior. |
| `tools/media_renamer/media_rules.json` | `runtime_config` | Filename/rules config for expected filename generation and QA classification. |
| Media QA reports: `media_file_qa.csv`, `media_file_qa.json`, `repair_actions.log.txt`, `unrepaired_files.csv`, `final_summary.html` | `media_files`, `sync_history`, `audit_log` | Import scan/QA/remux outcomes. Keep report files as external artifacts; store status, paths, checks, and summary JSON. |

## Import Semantics

### Identity

- Prefer stable provider IDs over titles: TMDB, IMDb, TVDB, Trakt ID, Trakt slug.
- Title-only writes are not allowed for watch-state sync.
- `media_items.media_type` distinguishes show, season, episode, and movie rows.
- Show hierarchy is normalized as show -> season -> episode through `shows`, `seasons`, and `episodes`, with `media_items.parent_media_item_id` as a generic parent reference.

### State

- `watch_state` owns `unwatched`, `partial`, and `watched`.
- `watchlist` owns watchlist membership.
- `favourites` owns favourite membership.
- Importers must not collapse these into one field or infer one from another.
- Pending queued actions from JSON stay pending until pushed/reconciled or intentionally marked blocked with audit evidence.

### Sync

- `sync_queue` stores pending work derived from local writes or import recovery.
- `sync_history` stores completed/failed/blocked sync attempts.
- Trakt pull/push/reconcile outcomes must create history rows and audit entries.
- Partial watched status remains local unless a future Trakt progress mapping is implemented deliberately.
- Favourites remain local-only by default unless a specific external mapping is designed.

### Providers

- Provider health states are preserved: active, degraded, candidate, blocked, retired.
- Candidate providers do not render by default.
- Blocked providers never render.
- Admin/private provider notes stay private metadata.

### Media Files

- `media_files` stores local/network paths, expected filename, actual filename, ffprobe results, remux status, VLC/X-plore buckets, and QA summary JSON.
- Image binaries and media binaries are not stored in PostgreSQL by default.
- Home network paths are associated with `192.168.1.x`; trailer network paths are associated with `192.168.2.x`.

## Export Semantics

PostgreSQL server mode must be able to export JSON fallback artifacts without changing the canonical source rule:

- `data/inputs.json` remains canonical manual input.
- `data/data.json`, `data/catalog_index.json`, `data/calendar.json`, and `data/catalog_detail/*.json` remain generated runtime outputs.
- exported watch-state JSON can be used by static mode, but server mode should treat PostgreSQL as primary for writes.
- exported provider/runtime JSON must not include secrets.

## Validation

- SQL file is PostgreSQL DDL and uses non-destructive `CREATE ... IF NOT EXISTS` / index creation.
- Migration plan states PostgreSQL primary write store and JSON fallback/import/export role.
- Migration plan states image/media binaries remain files/assets by default.
- Migration plan preserves watchlist/favourite/watch-state independence.
- Migration plan preserves queued local actions and requires audit evidence for conflict decisions.

## Risks

- Existing browser-local state may be fragmented across machines or profiles. Import needs explicit capture/export from each relevant browser if those states matter.
- Generated JSON can be stale relative to `data/inputs.json`; import tooling must validate identity before trusting generated data.
- Trakt/commercial provider IDs may be incomplete for some catalog rows; those rows can be imported but must not be pushed by title only.
- Media Library paths differ between home, trailer, and portable devices; path profile metadata must be preserved instead of normalized into one path.
