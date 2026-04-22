# 2026-03-21 Shared System Cleanup

## Scope
- Eliminate duplicate card/action/calendar implementations still active in the runtime.
- Reassert one shell/layout contract across dashboard, shows, movies, calendar, discover, config, and `watch_me`.
- Reassert one D-pad focus engine.

## Root Causes Fixed
- `web/js/app_runtime.js` still contained duplicate `showCardHtml`, `movieCardHtml`, `renderDiscover`, and `renderCalendar` implementations. The later shared versions were active, but the older versions remained in-file and encouraged drift.
- `web/css/main_app.css` still contained contradictory legacy action-bar and calendar selectors, including a hidden right rating block for minimal bars and a dimmed out-of-month day style from the old calendar.
- `web/watch_me/watch_me.html` had already been reduced to the shared shell, but `web/js/watch_me_runtime.js` still allowed an extra card-level focus target before the real poster/action controls.
- The main runtime still contained a second spatial-navigation algorithm even after `web/js/chrometv_focus.js` was introduced.

## Implementation
- Rebuilt the active HTML files as thin shells that hand layout ownership to `web/js/app_runtime.js`.
- Removed the duplicate card/discover/calendar renderers from `web/js/app_runtime.js`.
- Kept shows and movies on the restored left sidebar layout and kept calendar as a dedicated full-width month-grid view.
- Forced `web/js/action_bar.js` to use one icon contract and one left/center/right row structure.
- Removed the contradictory legacy CSS that hid the rating block on compact action bars and dimmed out-of-month calendar cells.
- Reduced the main app focus handler to the shared `window.MyTVHubFocus.moveInRoot(...)` path.
- Moved Watch Me navigation focus to the actual poster button targets so D-pad navigation lands on usable controls directly.

## Validation
- `node --check web/js/app_runtime.js`
- `node --check web/js/action_bar.js`
- `node --check web/js/watch_me_runtime.js`
- `node --check web/js/chrometv_focus.js`
- Live browser validation with headless Edge against:
  - `web/index.html`
  - `web/shows.html`
  - `web/movies.html`
  - `web/calendar.html`
  - `web/watch_me/watch_me.html`

## Validation Results
- Dashboard rendered and reached `Ready`.
- Shows and movies both rendered with one left sidebar and shared media cards.
- Calendar rendered as a true 7-column month grid with 42 day cells and no legacy dimmed-cell class.
- Shared action bars rendered with one row and `nowrap` in dashboard, shows, movies, calendar, and watch_me.
- Focus navigation moved successfully in both shows and watch_me using the shared focus engine.

## Files Changed
- `web/index.html`
- `web/shows.html`
- `web/movies.html`
- `web/calendar.html`
- `web/discover.html`
- `web/config.html`
- `web/watch_me/watch_me.html`
- `web/js/action_bar.js`
- `web/js/app_runtime.js`
- `web/js/watch_me_runtime.js`
- `web/js/chrometv_focus.js`
- `web/css/main_app.css`
- `docs/ARCHITECTURE_LOG.md`

## Remaining Non-Blocking Items
- `tools/start_inputs_editor.ps1`, `web/inputs_editor.html`, and `web/library_editor.html` were already dirty and were intentionally left out of this pass.
- Untracked overlay patch reports remain local and were intentionally not included.

## Implementation Commit
- `aa70abc` — `Stabilize shared shell cards calendar and focus runtime`
