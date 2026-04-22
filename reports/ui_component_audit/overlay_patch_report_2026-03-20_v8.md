# Overlay Patch Report — 2026-03-20 v8

## Scope
Best-effort stabilization patch against the uploaded `web/` bundle.

## Changes
- explicit glyphs for status/favourite/bookmark in shared action-bar path
- safe card image fallback helper added to shared renderer
- portrait poster baseline for show/movie cards
- trimmed 16:9 baseline for episode cards/dashboard/calendar
- calendar forced back to a 7-column grid with horizontal scroll under tighter widths
- out-of-month day dimming removed
- added `ui_tuning` config keys used as the contract source for current sizing/grid behavior

## Known limit
`watch_me/watch_me.html` was not present in the uploaded `web_folder.zip`, so this patch cannot directly repair that page’s local markup. It does update the shared runtime/CSS contract used by shared cards.
