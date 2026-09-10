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
- Primary-nav normalizer for Media Library and Release Calendar: `web/js/media_library_header_button.js`
- Release Calendar page: `web/release_calendar.html`
- Release Calendar runtime: `web/js/release_calendar.js`
- Release Calendar responsive styling: `web/css/release_calendar.css`
- Active app styling: `web/css/main_app.css`
- Responsive layout may reposition Shows/Movies Search and filters through `web/css/main_app.css`, but must not hide, replace, or fork functionality by device type.

## Data And Generated Artifacts

- Canonical curated input: `data/inputs.json`
- Single generated web runtime catalog: `data/data.json`
- Calendar entries, show/movie detail views, seasons, episodes, and Release Calendar events are derived from `data/data.json`. Do not add a parallel generated release-calendar JSON file.
- Release Calendar movie events use `movies[].release_date`.
- Release Calendar TV events use `shows[].first_air_date` plus `shows[].seasons[].air_date` for season premieres. Season 0 / specials are excluded from the release calendar.
- When Season 1 has the same date as `first_air_date`, the view renders one combined `Series Premiere • Season 1` event instead of duplicate events.
- Release Calendar visual identity: the primary-navigation icon is `🆕`; the existing schedule Calendar keeps `📅`. The two views must not use visually interchangeable calendar icons.
- Release Calendar image selection is media-specific: movies use the movie poster; series premieres use the show poster; season premieres use the season poster first and fall back to the parent show poster only when the season poster is unavailable.
- Local poster assets (`poster_local`) are preferred. TMDB `poster_path` values are remote API paths and must be resolved through the TMDB image host rather than treated as GitHub Pages root-relative URLs.
- Streaming embed provider templates, ordering, enabled/disabled state, tier, capability metadata, and inactive-provider records are owned only by `web/config.json -> streaming.embed_providers[]`; generated data must not duplicate full embed URLs for every row.
- The Watch Source popup keeps configured Streaming sources, the visible TMDB Watch Page action, and TMDB regional Providers rows separate. TMDB watch page must not render as a Providers row fallback.
- Pages deploys only the explicit runtime JSON set above plus canonical `data/inputs.json`, `data/discover_registry.json`, and `data/watch_state_queue.json`; helper/report JSON and retired provider registry JSON under `data/` must not be deployed by wildcard.
- Reports, logs, backup snapshots, cleaned-input previews, screenshots, old requested-title queues/reports, OMDb sidecars, service-logo export reports, asset-refresh summaries, retired watch-source indexes, and one-off analysis outputs are local evidence only. They must stay ignored and must not be tracked as active architecture or runtime inputs.

## Page Shells

The active app shells are `web/index.html`, `web/shows.html`, `web/movies.html`, `web/calendar.html`, `web/release_calendar.html`, `web/discover.html`, `web/config.html`, `web/watch_me.html`, and `web/manage_watch_state.html`.

The primary `.top > .nav[role="tablist"][aria-label="Primary"]` row must contain the view icons, including the Release Calendar link `data-tab="release-calendar"` to `web/release_calendar.html` and the static `#mediaLibraryHeaderButton` link to `web/Media_Library.html`.

The existing Calendar and the Release Calendar are intentionally separate views:

- `web/calendar.html` remains the schedule/episode calendar.
- `web/release_calendar.html` shows only movie releases, TV series premieres, and TV season premiere dates.

Active app shells must load shared CSS and JavaScript through deterministic release-version query parameters matching `web/config.json` `_meta.version`; page-specific Release Calendar assets may use their own deterministic revision token when changed independently.

## Release Calendar View Contract

- Purpose: a release-focused monthly calendar that excludes normal episode-by-episode airings.
- Data authority: derive directly from canonical `data/data.json`; no duplicate generated data source.
- Movie event: one event for each valid movie `release_date`.
- TV series event: use `first_air_date` when no same-date Season 1 premiere event already represents it.
- Season event: one event for each valid season `air_date` where `season_number >= 1`.
- Duplicate rule: combine same-date series premiere and Season 1 into one `Series Premiere • Season 1` event.
- Filters: All, TV & Seasons, Movies.
- Navigation: Today, previous month, next month.
- Desktop/tablet: seven-column calendar grid.
- Phone: one-column day list while preserving the same event content and filters.
- Feature parity: phone, tablet, desktop, and TV layouts must expose the same release events and controls; only layout may change.
- Missing-date rule: an item without a valid release/air date is omitted rather than assigned an inferred date.
- Poster rule: movie release = movie poster; series premiere = show poster; season premiere = season poster, then show-poster fallback.

## Retired Runtime Code

Retired compatibility shims are archived under `docs/_archive/runtime_shims/` and must not be restored under `web/js/` or loaded by `web/js/chrometv_focus.js`.

Device-specific browse scripts must not inject duplicate Search or Current controls, maintain parallel filter state, or hide cards outside the canonical Shows/Movies renderers.
