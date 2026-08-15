# Architecture

`docs/00_master_contract.html` is the source of truth. This file is a navigation aid for agents and must not replace or fork the contract.

## Runtime Ownership

- Runtime shell and routing: `web/js/app_runtime.js`
- Shows/Movies Search state, release/status scope state, Current predicates, filter events, result rendering, active-state rendering, and counts: `web/js/app_runtime.js`
- Configurable Current windows: `web/config.json -> browse.current`
- Shared card renderers: `web/js/card_renderer.js`
- Shared action strip: `web/js/action_bar.js`
- Watch-state persistence and refresh: `web/js/watch_state_manager.js`
- Popup media-detail schema: `web/js/popup_controller.js`
- Media Library primary-nav normalizer: `web/js/media_library_header_button.js`
- Active app styling: `web/css/main_app.css`
- Responsive layout may reposition Shows/Movies Search and filters through `web/css/main_app.css`, but must not hide, replace, or fork functionality by device type.

## Data And Generated Artifacts

- Canonical curated input: `data/inputs.json`
- Single generated web runtime catalog: `data/data.json`
- Calendar entries, show/movie detail views, seasons, and episodes are derived from `data/data.json` in the shared runtime loader. Do not add parallel generated catalog/detail JSON for production runtime.
- Streaming embed provider templates, ordering, enabled/disabled state, tier, capability metadata, and inactive-provider records are owned only by `web/config.json -> streaming.embed_providers[]`; generated data must not duplicate full embed URLs for every row.
- The Watch Source popup keeps configured Streaming sources, the visible TMDB Watch Page action, and TMDB regional Providers rows separate. TMDB watch page must not render as a Providers row fallback.
- Pages deploys only the explicit runtime JSON set above plus canonical `data/inputs.json`, `data/discover_registry.json`, and `data/watch_state_queue.json`; helper/report JSON and retired provider registry JSON under `data/` must not be deployed by wildcard.
- Reports, logs, backup snapshots, cleaned-input previews, screenshots, old requested-title queues/reports, OMDb sidecars, service-logo export reports, asset-refresh summaries, retired watch-source indexes, and one-off analysis outputs are local evidence only. They must stay ignored and must not be tracked as active architecture or runtime inputs.

## Page Shells

The active app shells are `web/index.html`, `web/shows.html`, `web/movies.html`, `web/calendar.html`, `web/discover.html`, `web/config.html`, `web/watch_me.html`, and `web/manage_watch_state.html`.

The primary `.top > .nav[role="tablist"][aria-label="Primary"]` row must contain the view icons, including the static `#mediaLibraryHeaderButton` link to `web/Media_Library.html`.

Active app shells must load shared CSS and JavaScript through deterministic release-version query parameters matching `web/config.json` `_meta.version`.

## Retired Runtime Code

Retired compatibility shims are archived under `docs/_archive/runtime_shims/` and must not be restored under `web/js/` or loaded by `web/js/chrometv_focus.js`.

Device-specific browse scripts must not inject duplicate Search or Current controls, maintain parallel filter state, or hide cards outside the canonical Shows/Movies renderers.

