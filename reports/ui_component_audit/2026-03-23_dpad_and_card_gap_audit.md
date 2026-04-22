# 2026-03-23 D-Pad And Card Gap Audit

## Scope

- Chromecast / Android TV D-pad behavior
- dashboard, shows, movies, watch_me card/action layout
- show popup season band vs redundant provider section
- current live code vs active docs

## Confirmed drift before fixes

1. Two arrow-key systems were active at the same time.
   - `web/js/chrometv_focus.js`
   - `web/js/app_runtime.js`
   - Result: visible layer focus and background/intermediate form handling could diverge.

2. Shared card overlays still had clipping pressure.
   - overlay titles and meta lines were still line-clamped tightly
   - action-row right edge could compress rating text
   - some cards exposed lone `%` fallback text instead of a readable fallback token

3. Movie view cards were under-reporting metadata.
   - movie browse cards only showed year
   - full release date and runtime were not exposed in the card contract

4. Show popup docs and code had drift.
   - docs still allowed a dedicated provider block between season and episode sections
   - current product direction does not

## Fixes applied

- removed duplicate arrow-key interception from `web/js/app_runtime.js`
- kept `web/js/chrometv_focus.js` as the single global D-pad navigation path
- tightened active-layer detection in `web/js/chrometv_focus.js`
- expanded overlay title wrapping and reclaimed card-body/action-row spacing in `web/css/main_app.css`
- made rating fallback readable in `web/js/action_bar.js` as `--%`
- aligned `web/js/app_runtime.js` to stop passing bare `%` into the shared action bar
- added full release date + runtime to movie browse cards in `web/js/app_runtime.js`
- removed the redundant show-popup provider section from `web/js/app_runtime.js`
- marked native browse search/select controls as non-TV focus targets and removed the top primary browse row from coarse-pointer layouts
- updated the show-popup and TV-focus docs to match the live contract

## Validation

- `node --check web/js/app_runtime.js`
- `node --check web/js/action_bar.js`
- `node --check web/js/chrometv_focus.js`
- headless Edge render validation for dashboard/calendar/watch_me/discover
- focused D-pad harness validation against shows/movies sidebar behavior

## Residual risk

- desktop and mouse users still retain the native browse search/select row; this pass only removes it from the TV-primary path on coarse-pointer devices
- if the filters need fully couch-first search and sort, the next pass should replace the remaining native text/select controls with explicit segmented or chip-based controls instead of hiding them on TV surfaces
