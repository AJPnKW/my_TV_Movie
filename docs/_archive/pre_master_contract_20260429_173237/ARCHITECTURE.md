# My TV Hub — Architecture Contract

## Purpose
This document is the active source of truth for runtime architecture, data flow, asset pipeline, watch-state architecture, Trakt integration design, and validation.

UI layout details belong in `docs/UI_COMPONENTS.md`.

## Canonical Runtime Data

| Artifact | Role |
|---|---|
| `data/inputs.json` | editable canonical input |
| `data/data.json` | compatibility/reference fallback; not preferred first-load dependency |
| `data/catalog_index.json` | first-load list/card data |
| `data/calendar.json` | calendar/dashboard date-grouped data |
| `data/watch_sources_index.json` | first lookup path for watch-source popup |
| `data/catalog_detail/<tmdb_id>.json` | lazy-loaded detail data |

## Runtime Loading Model

- List/dashboard/show/movie/watch surfaces should prefer `catalog_index.json`.
- Calendar/dashboard date-grouped views should prefer `calendar.json`.
- If `calendar.json` is empty, runtime may derive calendar days from `data/data.json`.
- Popup/watch-source flow must use `watch_sources_index.json` first.
- Detail JSON is lazy-loaded only when required.

## Watch-State Architecture

State types:
- `watched_status`
- `watch_list`
- `favourite`

State is local-first:
- UI updates immediately.
- No network call may block the UI state change.
- Offline changes are queued for future sync.

State key format:

```text
<state_type>:episode:<show_id>:<season_number>:<episode_number>
<state_type>:movie:<tmdb_id>
<state_type>:show:<tmdb_id>
<state_type>:season:<show_id>:<season_number>
```

## Trakt Integration Design

Planned mapping:

| Local State | Trakt Mapping |
|---|---|
| `watched_status` | watched/history |
| `watch_list` | watchlist |
| `favourite` | recommendation/favourite signal where supported; otherwise local-only with documented decision |

Required workflows:
- pull Trakt state
- compare Trakt vs local/runtime state
- queue offline local changes
- push local changes to Trakt
- pull after push to confirm final state
- identify unmatched TMDB IDs
- manage unmatched/ambiguous mappings through Config or a manage-watch-state view

Rules:
- primary matching key is `tmdb_id`
- never match by title alone
- all sync operations must report changed/skipped/error counts

## Asset Pipeline

Source originals:

```text
assets/original_downloads/
```

Runtime optimized asset folders:

```text
assets/posters/
assets/stills/
assets/backdrops/
assets/logos/
assets/icons/
```

Rules:
- originals are immutable
- runtime assets are regenerated from originals
- JSON paths should remain stable where possible
- do not store 4K episode stills as runtime card assets
- do not store 2000x3000 posters as runtime card assets

## Image Targets

| Asset Type | Runtime Target |
|---|---|
| show poster | 171x257 |
| movie poster | 171x257 |
| episode still source | 320x180 |
| episode narrow still | 256x180 after 10% side crop |
| backdrop/still large view | max 780px wide unless justified |
| provider logo | small optimized logo |

## Caching Strategy

Preferred cache candidates:
- provider logos
- dashboard episode stills
- current month calendar stills
- small runtime indexes

Avoid:
- caching full catalog without measurement
- heavy memory usage on Android/Chromecast TV

## Validation

Repo-standard validation command:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1
```

Validation should cover:
- JSON parse
- JS syntax
- Python syntax
- required file existence
- forbidden drift markers
- documentation consistency
- runtime asset report
- no conflict markers
- no sample stub scripts/docs
