# Status Mapping Contract

## Purpose

Frontend-only placeholder contract for shared status controls before the local Trakt bridge exists.

## Local UI Values

| ui_value | label | local meaning | trakt_target_value |
|---|---|---|---|
| `watchlist` | Watchlist | queued / not started | `watchlist` |
| `watching` | Watching | in progress / active | `watching` |
| `paused` | Paused | temporarily stopped | `paused` |
| `completed` | Completed | finished | `completed` |
| `dropped` | Dropped | stopped intentionally | `dropped` |

## Mapping Direction

- UI to Trakt-facing payload:
  - send the local `ui_value` plus entity identity context
  - for season and episode, include parent show id and season/episode numbers
- Trakt-facing payload to UI:
  - map remote status back to the same local `ui_value`
  - preserve unknown remote values as local passthrough strings until normalized

## Local Storage Placeholder

- Current frontend placeholder uses a local status map keyed by entity type and identity context.
- Show/movie entries can fall back to legacy watchlist status values for backward compatibility.
- Backend bridge remains deferred.

