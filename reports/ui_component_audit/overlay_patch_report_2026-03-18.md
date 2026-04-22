# Overlay Patch Report — 2026-03-18

## Scope

Stabilization patch for the shared runtime and docs after live regressions remained in dashboard, calendar, shows, and movies.

## Files Changed

- web/js/card_renderer.js
- web/js/action_bar.js
- web/js/app_runtime.js
- web/css/main_app.css
- docs/ARCHITECTURE_LOG.md
- docs/episode_card.md
- docs/show_card.md
- docs/movie_card.md
- docs/show_popup.md
- docs/movie_popup.md

## Key Fixes

- Added canonical `safeCardImage()` helper to prevent broken image icons and provide stable placeholders.
- Re-locked the icon strip to one row with fixed left / middle / right grouping.
- Applied responsive card overrides to reduce drift at mid-width and Android-TV-like viewport widths.
- Reasserted poster-first layout for show/movie cards and still-first layout for episode/calendar cards.

## Validation Performed

- `node --check` passed for:
  - `web/js/card_renderer.js`
  - `web/js/action_bar.js`
  - `web/js/app_runtime.js`

## Remaining Need

This patch does not audit the asset-download pipeline itself. Newly added items that still lack posters or stills should now degrade cleanly, but the separate asset acquisition workflow may still need attention.
