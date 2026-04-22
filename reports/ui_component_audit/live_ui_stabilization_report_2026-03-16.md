# Live UI Stabilization Report - 2026-03-16

## Scope

This report captures the live stabilization pass that produced commit `104a0c4` on `github/main`.

Pass goal:

- stabilize the visible shared web runtime
- restore correct page-shell ownership
- normalize shared card and action rendering
- remove broken live rendering behavior without introducing a parallel UI system

## Files Changed In The Stabilization Pass

- `web/js/action_bar.js`
- `web/js/app_runtime.js`
- `web/css/main_app.css`
- `web/shows.html`
- `web/movies.html`
- `web/calendar.html`
- `web/discover.html`
- `web/config.html`
- `docs/ARCHITECTURE_LOG.md`

## Implemented Fixes

### 1. Page shell ownership

- Restored `calendar` to a full-width wall-calendar shell.
- Removed sidebar ownership from the calendar runtime path.
- Kept left-sidebar browse shells for `shows` and `movies`.
- Preserved the `watch_me` page shell while aligning it to shared nav and shared card/action behavior.
- Corrected static active-nav ownership in the page shells so the active tab is right before and after runtime hydration.

### 2. Shared action strip stabilization

- Re-locked the shared icon strip to the content-type-specific canonical order.
- Removed icon-in-button pill drift from the shared action visuals.
- Restricted watch-source rendering to movie and episode contexts.
- Preserved status, favorites, watchlist, and rating ownership in the shared renderer.

Canonical ordering in live state:

- movies and episodes: `🍿`, `⌚`, `💕`, `🔖`, `⭐%`
- shows and seasons: `⌚`, `💕`, `🔖`, `⭐%`

### 3. Shared rendering repair

- Removed duplicate legacy function ownership inside `web/js/app_runtime.js`.
- Kept one canonical live render path for dashboard, calendar, discover, movie detail, and show detail.
- Restored overlay-copy behavior so card text is not visibly duplicated.
- Corrected dashboard and calendar shared-card rendering defects.

### 4. Show detail and season flow

- Re-stabilized season selection around the season carousel flow.
- Re-stabilized episode rendering under the selected season through the shared episode-card contract.
- Preserved normalized episode-card action ownership under show detail.

### 5. Calendar layout repair

- Added a dedicated calendar shell and toolbar structure in the runtime.
- Updated sticky-header calculations to use the calendar toolbar instead of the old browse header assumptions.
- Preserved weekday stickiness without overlap and removed the visible shell conflict introduced by the browse layout.

## Validation Performed

### Static validation

- `node --check web/js/action_bar.js`
- `node --check web/js/card_renderer.js`
- `node --check web/js/app_runtime.js`
- `git diff --check`

### Browser/runtime validation

Validated via local static server plus headless browser:

- `web/index.html`
- `web/shows.html`
- `web/movies.html`
- `web/calendar.html`
- `web/watch_me/watch_me.html`

## Validation Results

- dashboard
  - active nav correct
  - no loading-stuck state
  - no duplicate visible card copy
  - no horizontal overflow
- shows
  - active nav correct
  - sidebar present as expected
  - no duplicate visible card copy
  - no loading-stuck state
- movies
  - active nav correct
  - sidebar present as expected
  - no duplicate visible card copy
  - no loading-stuck state
- calendar
  - active nav correct
  - no sidebar present
  - calendar toolbar and sticky behavior present
  - no duplicate visible card copy
  - no loading-stuck state
- watch_me
  - active nav correct
  - no duplicate visible card copy
  - no loading-stuck state

## Non-Blocking Console Notes

- `/favicon.ico` 404 from local static validation server
- `/api/health` 404 from local static validation server
- `watch_me` watched-state LAN fallback request failure when the external endpoint is not available

These did not block rendering and did not create a loading-stuck condition in the validated pages.

## Result

The pushed live runtime was stabilized without changing the product’s active architecture direction:

- one shared runtime
- one shared card/action system
- page-specific shells where the product intentionally requires them
