# UI-PARITY-CURRENT-SEARCH-CACHE-2026-07-24

## Issue Title

Shows/Movies mobile browse parity regression: Current filter, Search visibility, genre spacing, and stale app shell cache.

## Date Reported

2026-07-24.

## Affected Views

- `web/shows.html`
- `web/movies.html`

## Affected Devices

Phone, tablet, desktop, Android TV style 1920x1080 viewport, Google TV, Chromecast, and NVIDIA Shield style browsing surfaces.

## Screenshots and Observed Symptoms

The user supplied phone screenshots showing `CURRENT` visible but not functionally selected, Search absent on phone, sparse genre rows, and old UI appearing until refresh.

Captured QA evidence from this repair:

- `reports/ui_stabilization/screenshots/shows-phone-current-search-genre.png`
- `reports/ui_stabilization/screenshots/movies-phone-current-search-genre.png`
- `reports/ui_stabilization/screenshots/shows-desktop-current.png`
- `reports/ui_stabilization/screenshots/movies-tv-current.png`
- `reports/ui_stabilization/browse_filter_parity_2026-07-24.json`

## Reproduction Steps

1. Load `web/shows.html` or `web/movies.html` at phone width.
2. Observe Search missing because `.browse-sidebar .control-row--primary` is hidden for coarse pointers.
3. Click the visible `CURRENT` control.
4. Observe `All Shows` or `All Movies` remains active and the canonical result pipeline is not updated.
5. Inspect scripts/styles and observe `mobile_current_filters.js` and `mobile_browse_fixes.css` loaded after the canonical runtime/style.
6. Navigate normally after a release and observe unversioned shared CSS/JS URLs can be reused from stale cache.

## Confirmed Root Cause

The first incorrect behavior occurred after the canonical page renderer loaded:

HTML shell -> loaded `app_runtime.js` and `main_app.css` -> canonical Search/filter controls rendered -> `mobile_current_filters.js` then injected a second `CURRENT` control into the scope row -> the injected control used private `enabled` and `currentIds` state -> it hid already-rendered cards with `.current-filter-hidden` and changed visible count text -> it never updated `state.filters.shows.scope`, `state.filters.movies.scope`, `setSegActive`, or the canonical renderers.

Search was missing on phone because `main_app.css` contained a coarse-pointer rule hiding `.browse-sidebar .control-row--primary`, which contains Search, Year, Sort, and Collection controls.

Genre spacing regressed because the late mobile CSS override tried to force broad mobile layout through a separate stylesheet instead of compacting the canonical control layout.

The old-page-before-refresh symptom was caused by active page shells loading shared CSS and JavaScript with unversioned URLs. No active service worker registration or cache-storage owner was found.

## Contributing Factors

- Recent mobile-only files created a parallel functional implementation instead of changing shared runtime state.
- The mobile script ran after the canonical renderer, so it could make the UI look changed while leaving canonical state unchanged.
- Responsive CSS changed functionality by pointer/device type.
- Active app shells did not version shared CSS/JS references.

## Rejected Hypotheses

- Generated catalogue data was not the cause; no generated catalogue, calendar, provider, requested-title import, or asset pipeline output was needed.
- Service worker/PWA cache was not the cause; no active service worker registration was present.
- Local storage state was not the cause; the injected Current control failed without writing canonical state.
- Duplicate old HTML files were not the primary cause for Shows/Movies; active shells explicitly loaded the duplicate mobile script/style.

## Why The Previous Implementation Failed

The previous implementation treated mobile as a separate product surface. It created a second filter button, a second Current predicate, a second result-hiding path, and a second count updater. It could not deactivate All, update `aria-pressed` on the canonical buttons, combine correctly with Search/Genre/Year, or survive a canonical re-render because it was outside the shared state and renderer.

## Files Removed

- `web/js/mobile_current_filters.js`
- `web/css/mobile_browse_fixes.css`

## Files Modified

See `reports/ui_stabilization/modified_file_manifest_2026-07-24.md`.

## Fix Design

- Added `Current` as a normal `data-scope="current"` option in the existing Shows and Movies scope rows.
- Added one Current show predicate and one Current movie predicate to `web/js/app_runtime.js`.
- Routed Current through `state.filters.shows.scope`, `state.filters.movies.scope`, `setSegActive`, `aria-pressed`, `renderShows`, `renderMovies`, and the existing result-count summaries.
- Removed coarse-pointer hiding of primary browse controls.
- Compacted genre controls in `main_app.css` with a responsive grid and stable touch/focus dimensions.
- Removed mobile-only script/style references from Shows and Movies.
- Advanced `web/config.json` `_meta.version` to `v1.5.3`.
- Versioned active app shell CSS/JS references and `app_runtime.js` module imports with `?v=v1.5.3`.
- Added configurable Current windows in `web/config.json -> browse.current`.
- Added validator coverage blocking retired mobile browse files and unversioned active app assets.

## Current Rules

Current shows:

- first air date is not in the future;
- status is not Ended, Canceled, or Cancelled;
- `last_air_date`, `latest_episode_to_air.air_date`, or `last_episode_to_air.air_date` is within `web/config.json -> browse.current.show_activity_window_days = 183`.
- status alone and `next_episode_to_air` alone do not make a show Current.

Current movies:

- `release_date` is within `web/config.json -> browse.current.movie_release_window_days = 183` ending today;
- future releases are included only up to `web/config.json -> browse.current.movie_release_lookahead_days = 30`;
- future releases also require existing availability metadata to resolve to `available`.

## Tests Performed

- `node --check web/js/app_runtime.js`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1`
- `node scripts/qa_browse_filter_parity.mjs`
- `node scripts/qa_browser_layout_check.mjs`
- `git diff --stat`

## Results

- Focused browse QA passed for Shows and Movies at phone, tablet, desktop, and Android TV style 1920x1080 viewports.
- Search was visible after normal load, back navigation, and reload.
- Current became the sole active scope option with correct `aria-pressed`.
- Current filtered visible records to the documented predicates.
- Search + Current and Search + Current + Genre combinations passed.
- Genre rows were compact on phone with no horizontal overflow.
- The full rendered browser suite passed with `failures: []`.
- Stale service-worker control was not present.
- Active app assets were release-versioned with `v1.5.2`.

## Residual Risks

GitHub Pages edge-cache timing after `origin/main` push can only be fully proven once Pages deploys the pushed commit. The app-shell fix is deterministic: old HTML may live briefly at the edge, but any new HTML loads versioned shared CSS/JS URLs.

## Prevention Controls

- `scripts/validate_runtime.ps1` now fails if retired mobile browse files return, if active shells reference them, if Current is not canonical, if touch CSS hides primary browse controls, or if active app assets are not release-versioned.
- `scripts/qa_browse_filter_parity.mjs` records behavior across phone, tablet, desktop, and TV-style viewports.
- `docs/00_master_contract.html`, `docs/ARCHITECTURE.md`, `docs/UI_COMPONENTS.md`, and `docs/UI_GAP_ANALYSIS.md` now define feature parity, shared state ownership, Current predicates, and release cache rules.
