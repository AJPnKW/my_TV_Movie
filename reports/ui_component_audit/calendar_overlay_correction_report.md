# Calendar Overlay Correction Report

- Date: 2026-03-15
- Scope: calendar + compact overlay card correction pass

## Outcome

- Kept the normalized runtime baseline and corrected the compact card presentation through the shared renderer instead of adding another card family.
- Calendar remains on the full-width single-column shell with no visible left rail.
- Compact cards now use an overlay-text treatment where density benefits from image-first presentation.

## Changes

- Added overlay-capable compact card rendering to `web/js/card_renderer.js`.
- Switched calendar compact episode/movie cards to the overlay model in `web/js/app_runtime.js`.
- Switched dashboard rail cards to the same overlay-family rendering path in `web/js/app_runtime.js`.
- Switched `watch_me` cards to the overlay variant of the shared renderer.
- Tightened shared compact-card CSS in `web/css/main_app.css` so overlay cards stay shorter and don’t waste vertical space on stacked text blocks.

## Validation Notes

- Calendar: no visible left rail, full-width shell column, 165 overlay cards rendered.
- Dashboard: 42 compact overlay cards rendered across rails.
- Watch Me: 31 shared overlay cards rendered across 2 rows.
- Main surfaces were not stuck on loading in headless validation.
