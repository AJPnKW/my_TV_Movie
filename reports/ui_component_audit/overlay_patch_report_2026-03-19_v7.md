# Overlay Patch Report 2026-03-19 v7

## Scope
- dashboard episode card repair
- icon strip parity
- calendar fixed-width 7-column grid
- show/movie browse poster sizing consistency

## Files
- web/js/app_runtime.js
- web/js/action_bar.js
- web/css/main_app.css
- docs/ARCHITECTURE_LOG.md
- docs/episode_card.md
- docs/show_card.md
- docs/movie_card.md
- docs/show_popup.md

## Notes
- dashboard episode cards now render through the episode action path rather than show-card fallback
- out-of-month days are no longer dimmed
- calendar keeps 7 columns by scrolling horizontally instead of collapsing
