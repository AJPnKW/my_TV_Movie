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
- Implementation commit: `pending grouped commit`
