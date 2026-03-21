# UI Component Audit - 2026-03-17

## Scope

Grouped pass against the shared-runtime baseline covering:

- dashboard
- shows
- movies
- calendar
- watch-me
- show popup
- movie popup
- config shell

## Contracts Written

- `docs/episode_card.md`
- `docs/show_card.md`
- `docs/movie_card.md`
- `docs/show_popup.md`
- `docs/movie_popup.md`
- `docs/focus_navigation_tv.md`
- `docs/calendar_view.md`

## Centralized Implementation Changes

- normalized the icon strip into one shared left / middle / right action-bar model in `web/js/action_bar.js`
- restored episode hierarchy into overlay rendering in `web/js/card_renderer.js`
- updated `web/js/app_runtime.js` to:
  - use the full-width calendar toolbar
  - lock popup background scroll
  - keep focus trapped in the active popup layer
  - densify the show popup metadata
  - make the season selector a horizontal carousel
  - apply parent-show favourite state to season and episode contexts
  - fix calendar `+X more` and `Show less`
- rebased main page shells onto the shared runtime instead of stale sidebar/dashboard markup
- aligned popup contract markers in `web/js/popup_controller.js`
- added final CSS overrides in `web/css/main_app.css` for the UI contract baseline
- kept `watch_me` on its own page while preserving the shared card/action system

## Validation

Static:

- `node --check web/js/app_runtime.js`
- `node --check web/js/card_renderer.js`
- `node --check web/js/action_bar.js`
- `node --check web/js/popup_controller.js`

Browser/runtime:

- temporary local server via `py -m http.server 4173 --directory C:/Users/andrew/PROJECTS/GitHub/my_TV_Movie`
- Puppeteer runtime checks against local Edge

Verified:

- dashboard action bars render as a single row with three groups and no overflow
- shows grid action bars render as a single row with no poster drift
- show popup opens, traps focus, locks background scroll, and renders 16 dense metadata tiles in the sampled show
- season carousel renders and remains within the popup focus layer
- movies grid and movie popup action bars remain single-row with no overflow
- calendar toolbar keeps previous / today / next on one line
- calendar `+X more` expands and `Show less` collapses correctly after the fix
- watch-me action bars remain single-row and use the shared action-bar structure
- config route renders the shared runtime config hero and runtime surface

## Residual Note

- watch-me now shares the canonical action-bar structure and single-row behavior, but it still exposes a reduced action set compared with the richer main-app episode/movie surfaces because its page-level logic remains separate by design.
