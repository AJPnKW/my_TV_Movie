# Architecture Change Log

Purpose: Maintain a deterministic history of architectural decisions and structural corrections in the **my_TV_Movie** repository.

Only record architecture-level changes, not minor UI tweaks.

------------------------------------------------------------------------

## 2026-03-16 --- UI Stabilization Baseline

Summary

- `data/inputs.json` is the canonical user-maintained input file.
- `data/data.json` is the generated runtime dataset.
- `web/inputs_editor.html` is the only supported editor.
- `web/library_editor.html` remains retired / redirect-only.
- Shared rendering remains centered on:

    web/js/card_renderer.js
    web/js/action_bar.js
    web/js/app_runtime.js

- Calendar is a full-width wall calendar with no left sidebar.
- Shows and movies own sidebar-driven browse layouts.

------------------------------------------------------------------------

## 2026-03-17 --- UI Contract Baseline V2

Summary

- Added implementation-grade UI contracts for episode cards, show cards, movie cards, show popup, movie popup, TV focus navigation, and calendar view.
- Rebased the main page shells so the shared runtime owns the live browse and calendar layouts instead of stale carryover markup.
- Locked the icon strip to a single-row left / middle / right grouping across dashboard, shows, movies, calendar, popups, and watch-me.
- Densified the show popup, normalized the season selector into a horizontal carousel, and fixed popup focus trap plus background scroll lock behavior.
- Restored full-width calendar controls and corrected `+X more` / `Show less` collapse behavior.

Files

    docs/episode_card.md
    docs/show_card.md
    docs/movie_card.md
    docs/show_popup.md
    docs/movie_popup.md
    docs/focus_navigation_tv.md
    docs/calendar_view.md
    web/js/app_runtime.js
    web/js/card_renderer.js
    web/js/action_bar.js
    web/js/popup_controller.js
    web/css/main_app.css
    web/index.html
    web/shows.html
    web/movies.html
    web/calendar.html
    web/config.html
    web/watch_me/watch_me.html
    reports/ui_component_audit/2026-03-17_ui_contract_baseline.md

Commit

    8cd3442


## 2026-03-20 — Overlay v8 stabilization
- Re-enforced exact episode/movie/show icon strip glyph contract.
- Forced calendar back to a seven-column month grid with horizontal scroll instead of collapsing.
- Standardized portrait sizing for show/movie cards and trimmed episode stills for dashboard/calendar parity.
- Added explicit UI tuning keys in config for card sizing and calendar grid behavior.

## 2026-03-20 — Shell/editor/watch-me stabilization
- Rebased `web/index.html` back to the thin canonical shell so the shared runtime and shared stylesheet own the dashboard-family views.
- Moved shell Inputs Editor entry points to the real local editor flow on `http://127.0.0.1:8787/web/inputs_editor.html` and removed the dead embedded editor experience.
- Hardened `tools/inputs_editor/inputs_editor_server.py` with validation, backup creation, atomic save, and a runtime refresh endpoint.
- Rebuilt `web/watch_me/watch_me.html` around the shared shell, shared card renderer, and shared action bar instead of a separate card/icon system.
- Removed blocking prompts from the asset QA/repair scripts and added a current validation workflow under `.github/workflows/validate.yml`.
- Implementation commit: `6440404`

## 2026-03-21 — Shared card/action/focus cleanup
- Reduced the dashboard-family pages back to thin shell files so `web/js/app_runtime.js` owns the active view layout and there is no page-level drift between dashboard, shows, movies, calendar, discover, and config.
- Removed duplicate `showCardHtml`, `movieCardHtml`, `renderDiscover`, and `renderCalendar` implementations from `web/js/app_runtime.js` so one shared card/action/calendar path remains active.
- Restored shows and movies to the left-rail browse layout, kept calendar full-width, and kept `watch_me` on its own page while aligning it to the shared shell, card, action, and focus contract.
- Added `web/js/chrometv_focus.js` as the single shared D-pad engine and reduced the main runtime focus path to a wrapper over that module instead of a second spatial-navigation implementation.
- Normalized the action bar and calendar CSS contract by deleting contradictory legacy selectors that hid ratings or dimmed out-of-month cells under the new grid.
- Implementation commit: `aa70abc`

## 2026-03-21 — Availability status end-to-end
- Added a normalized availability layer driven by `data/watch_source_availability.json`, resolved into additive fields on `data/data.json`.
- Implemented shared availability validation/enrichment helpers under `scripts/availability_status_lib.py`, with dedicated validator, enricher, and QA scripts.
- Chained availability validation/enrichment into the actual TMDB→OMDB→Trakt runner in `scripts/run_pipeline_tmdb_trakt.py`.
- Extended the shared UI runtime so cards, calendar rows, watch_me cards, show seasons, and show/movie popups all render one shared availability badge/detail pattern from enriched `data.json`.
- Updated the availability docs set to match the live repo’s actual keys, workflow runner, validation mode, and QA artifacts.
- Implementation commit: `8d11c7b`

## 2026-03-21 — Availability status phase 2 hardening
- Hardened validation from structural-only to provider-aware validation in `scripts/availability_status_lib.py`, with optional cached network verification support that remains disabled by default.
- Added deterministic phase-2 QA and production-state validators for override precedence, runtime asset coverage, runtime catalog integrity, and browser-level badge placement.
- Moved shared availability badges onto the upper-right image surface for cards and popup visual surfaces instead of relying on copy-only placement.
- Updated the local TMDB→OMDB→Trakt runner to fetch missing TMDB assets before runtime asset validation so rebuilt `*_local` refs no longer fail the final production-state pass.
- Implementation commit: `680bef3`

## 2026-03-21 — Availability metadata hardening and secret drift cleanup
- Added `scripts/validate_secret_name_drift.py` plus runtime warnings in the Trakt helper scripts so `API_TRAKT_REDIRECT_URL` is the only canonical redirect secret name and deprecated typo usage is explicitly surfaced.
- Added `scripts/self_heal_asset_metadata.py` to classify unrecoverable upstream metadata gaps and deterministically repair recoverable `*_path` / `*_local` drift before final validation.
- Updated the local runner to execute secret drift validation and asset metadata self-heal before availability validation/enrichment, keeping the final runtime asset validator at the end of the chain.
- Implementation commit: `f036936`

## 2026-03-22 — Popup, calendar, and shared card cleanup
- Removed active popup drift in `web/js/app_runtime.js` by retiring duplicated legacy popup/dashboard definitions and restoring one active show-popup path.
- Rebuilt the active show popup around a dense series hero, plain fact rows, dedicated provider section, horizontal season rail, and horizontal episode rail.
- Re-aligned dashboard, calendar, watch_me, and popup episodes to one shared episode-card content order with the double-heart favourite icon restored.
- Corrected CSS contract drift that was collapsing the calendar grid, wrapping the action strip, forcing shows/movies off the left rail, and turning dashboard recommendation posters into widescreen cards.
- Added `docs/VIEW_NAVIGATION_TREE.md` as the review map for pages, views, modal layers, and shared card families.
- Implementation commit: `4a5aed2`

## 2026-03-22 — Discover/sidebar/calendar follow-up cleanup
- Removed the remaining Discover intro/counter/featured-copy drift so the active view is just a two-column browse surface with shows on the left and movies on the right.
- Re-asserted the left-rail sizing contract for shows, movies, and watch_me so sidebar controls cannot overflow into the main content area at TV-like widths.
- Replaced the lingering dashboard episode show-card fallback with the shared episode-card renderer and re-asserted the shared action-strip contract across dashboard, calendar, watch_me, and popup rails so icon rows stay on one line with the shared left/center/right spacing model.
- Tightened calendar cell presentation with stronger day outlines and corrected sticky day-head positioning relative to the calendar toolbar/weekday row.
- Archived spec working notes under `docs/spec/archive/working_notes/` and kept the normalized `Section N - ...` files as the active spec body.
- Implementation commit: `9dd68c1`

## 2026-03-22 — Calendar/header/dashboard episode-card normalization
- Removed the separate sticky weekday row from the calendar grid and made the in-cell day head the single active weekday/date header for each day cell.
- Restyled the calendar day-head surface so non-today cells use an accent-tinted header band and today uses the active-view accent color directly.
- Retired dashboard `Up Next` so dashboard episode browsing now flows through `Upcoming Schedule` and the paged `Last Week` history strip.
- Added week-step and jump-step controls to dashboard `Last Week`, preserving D-pad-friendly backward/forward navigation through prior week segments.
- Set the shared poster-width token back to one config-driven source across dashboard recommendations, discover, shows, and movies instead of changing dashboard recommendations independently.
- Documented the current episode-card baseline as calendar visual layout plus dashboard last-week action-row spacing.
- Implementation commit: `PENDING`
