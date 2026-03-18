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
