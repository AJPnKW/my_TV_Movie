# Project Status - 2026-03-16

## Current Runtime Truth

- Repo: `my_TV_Movie`
- Canonical curated input: `data/inputs.json`
- Generated runtime dataset: `data/data.json`
- Canonical local asset root: `assets/`
- Canonical editor: `web/inputs_editor.html`
- Retired editor surface: `web/library_editor.html`
- Active page surfaces:
  - `web/index.html`
  - `web/shows.html`
  - `web/movies.html`
  - `web/watch_me/watch_me.html`
  - `web/calendar.html`
  - `web/discover.html`
  - `web/config.html`
  - `web/inputs_editor.html`

## Current UI Architecture State

- Shared runtime entry: `web/js/app_runtime.js`
- Shared action strip contract: `web/js/action_bar.js`
- Shared card renderer: `web/js/card_renderer.js`
- Shared CSS ownership:
  - `web/css/main_app.css`
  - `web/css/my_tv_hub.css`

The current active architecture is a shared web runtime with page-specific shells:

- `calendar` owns a full-width wall-calendar shell and does not use the browse sidebar.
- `shows` and `movies` use left-sidebar browse shells with shared filters and shared cards.
- `watch_me` keeps its distinct shell, but uses the shared card/action system and the global top navigation.
- dashboard, show detail, season detail, movie detail, discover, and config render through the shared runtime path.

## Locked UI Contracts

- Movies and episodes use this icon order: `🍿`, `⌚`, `💕`, `🔖`, `⭐%`
- Shows and seasons use this icon order: `⌚`, `💕`, `🔖`, `⭐%`
- Icons render as a clean horizontal strip, not as button pills.
- Shared cards own image, title, meta text, and action strip behavior.
- Overlay text duplication is considered a defect and is now guarded against in the current live implementation.

## Latest Canonical Implementation Point

- Latest pushed UI stabilization commit: `104a0c4`
- Commit message: `ui: stabilize live rendering and normalize shared page behavior`

That pass restored:

- correct page-shell ownership
- canonical shared icon-strip behavior
- corrected active nav state across page shells
- stabilized dashboard and calendar card rendering
- corrected full-width calendar shell behavior
- restored show-detail season carousel and normalized episode-card flow

## Validation Snapshot

Validated against the pushed live state:

- `node --check`
  - `web/js/action_bar.js`
  - `web/js/card_renderer.js`
  - `web/js/app_runtime.js`
- browser/runtime validation
  - `web/index.html`
  - `web/shows.html`
  - `web/movies.html`
  - `web/calendar.html`
  - `web/watch_me/watch_me.html`

Confirmed in that pass:

- no loading-stuck state on validated pages
- calendar shell restored correctly with no sidebar
- no visible duplicate text rendering on shared cards
- correct active nav state
- icon strip order correct by content type
- no horizontal overflow in validated pages

## Known Non-Blocking Notes

- Static local-server validation no longer emits the earlier `/favicon.ico` and `/api/health` shell noise after the runtime and shell hardening passes.
- `watch_me` still attempts a watched-state LAN fallback request when that service is unavailable.
- The main local worktree may contain additional uncommitted user files that are not part of the pushed canonical remote state.
