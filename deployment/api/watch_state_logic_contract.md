# Watch State Logic Contract

Session: CODEX-FOREST  
Date: 2026-06-02

## User Narrative

The app must support writable watched status, watchlist, favourites, Trakt/commercial sync, and static fallback without losing local user actions. Clicking an action in the UI must immediately change local state and must not wait for Trakt or another external provider. Watchlist and favourites are separate choices, not byproducts of watched status.

## Interpretation

PostgreSQL becomes the server-mode write store for watch state. JSON queue/export files remain compatibility and fallback artifacts. The state model must protect user intent when the network is offline, Trakt is unavailable, a provider mapping is missing, or multiple clients make changes.

## Architecture Decision

Use a local-first, queue-backed state machine:

- `watch_state` stores `unwatched`, `partial`, and `watched`.
- `watchlist` stores watchlist membership.
- `favourites` stores favourite membership.
- `sync_queue` stores pending external sync work.
- `sync_history` records completed/failed/blocked sync attempts.
- `audit_log` records every local write, import, conflict resolution, and sync state change.

## Canonical State Fields

### Watch Status

Allowed values:

- `unwatched`
- `partial`
- `watched`

Rules:

- `unwatched` means no completed local watch state.
- `partial` means local progress exists but completion is not asserted.
- `watched` means the user or trusted external history says the item is complete.
- `partial` remains local-only unless a future Trakt progress mapping is explicitly implemented.
- A transition to `watched` may set `progress_percent` to `100`.
- A transition to `unwatched` clears completion markers but must keep audit evidence.

### Watchlist

Allowed values:

- active
- inactive/removed

Rules:

- Watchlist membership is independent from watched status.
- Removing an item from watchlist must not mark it watched or unwatched.
- Watching an item must not silently remove it from watchlist unless a future explicit user preference is designed.

### Favourites

Allowed values:

- active
- inactive/removed

Rules:

- Favourite membership is independent from watched status and watchlist.
- Favourites are local-only by default.
- If a future Trakt ratings/list mapping is designed, the UI/API must label the mapping clearly and preserve local-only fallback.

## Local-First Write Flow

For any UI/API write:

1. Validate the media identity and reject title-only external sync payloads.
2. Persist the local row in PostgreSQL.
3. Write an `audit_log` entry with before/after state.
4. Create or update a `sync_queue` record when the change has an external sync target.
5. Return the local persisted state immediately.
6. Render the UI from local state plus sync metadata: pending, synced, failed, blocked, or conflict.

The local write is the user-visible truth until a later reconcile operation intentionally changes it with audit evidence.

## Queue Behavior

Queue records are durable and idempotent by `client_event_id` or operation key where available.

Statuses:

- `queued`: waiting to run
- `running`: actively syncing
- `succeeded`: external system confirmed or local-only operation recorded
- `failed`: retryable or terminal failure with error text
- `blocked`: cannot sync because identity, mapping, auth, or provider state is insufficient
- `cancelled`: explicitly cancelled with audit evidence

Rules:

- Multiple rapid writes to the same field may coalesce only if no user intent is lost.
- A newer local write supersedes older pending writes for the same field, but the older event remains auditable.
- Failed writes are not deleted automatically.
- Blocked writes remain visible until resolved or explicitly dismissed with audit evidence.
- Favourites with no Trakt mapping should become local-only history, not fake Trakt success.

## Conflict Resolution

Conflict inputs:

- local row value and `updated_at`
- pending queue records
- latest external pull evidence
- last successful sync history
- media identity confidence

Default strategy:

- Local wins when local update is newer than last confirmed external state.
- Remote wins only when the local value has no newer local write and the remote pull is trusted.
- Manual review is required when both sides changed after last sync or identity confidence is weak.

Conflict statuses:

- `none`
- `local_newer`
- `remote_newer`
- `conflict`
- `resolved`

No conflict may be resolved silently. Applied resolutions must write `audit_log` and `sync_history`.

## Import and Static Fallback

JSON import:

- Can seed PostgreSQL state.
- Must preserve pending queue actions from `data/watch_state_queue.json`.
- Must not overwrite newer PostgreSQL local state without conflict handling.

JSON export:

- Can publish local state to static fallback files.
- Must not make JSON the primary writable store in server mode.
- Must not export secrets.

Static fallback:

- May read exported JSON.
- May show queued/pending state from exported artifacts.
- Must not pretend external sync occurred if it did not.

## No Silent Loss Rules

The system fails validation if it:

- drops a queued local action because Trakt is offline
- changes watchlist when only watched status changed
- changes favourites when only watched status changed
- marks `partial` as synced to Trakt history without an explicit progress mapping
- marks favourites as synced to Trakt without an explicit mapping
- deletes failed/blocked sync attempts without audit evidence
- overwrites a newer local state from a stale JSON import
- pushes external writes using only title matching

## Validation

- Watch status, watchlist, and favourites are independent rows/routes.
- Every state write creates audit evidence.
- External sync is queue-backed.
- Conflict resolution records before/after evidence.
- JSON fallback remains import/export/static fallback.
- PostgreSQL is primary write store in server mode.

## Risks

- Multiple browsers may hold divergent static/local state until imported.
- Trakt history and watchlist semantics do not match every local state field.
- Existing UI code still needs later API-client integration to consume this server contract directly.
