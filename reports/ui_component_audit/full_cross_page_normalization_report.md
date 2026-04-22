# Full Cross-Page Normalization

Date: 2026-03-15

## Implemented

- Moved active show and movie compact-card rendering onto the shared overlay card shell so compact cards no longer keep stacked title/year copy below the poster.
- Normalized dashboard episode cards onto the same compact overlay episode-card family used by calendar and `watch_me`.
- Normalized active show/movie compact-card action rows onto the shared `buildActionBarHtml()` path instead of page-local partial action markup.
- Normalized shared action-row sizing in shared CSS so the icon row no longer changes shape between main pages.
- Removed compact overlay episode fallback text blocks from dashboard and `watch_me` so overlay text is the single visible compact copy treatment.

## Browser Validation Summary

- Shows: all compact cards rendered overlay text; no visible stacked copy blocks remained.
- Movies: all compact cards rendered overlay text; sampled `A Haunting in Venice` matched the overlay card model.
- Dashboard: compact cards rendered as overlay cards; dashboard episode cards used the canonical episode overlay model.
- Calendar: episode cards remained on the corrected canonical overlay/action model.
- `watch_me`: compact episode/movie cards remained on the overlay family and no longer showed stacked episode title blocks.
- Shared action-row order was preserved in validated contexts:
  - shows: favourite, status, watched, heart, percent
  - movies: popcorn, favourite, status, watched, heart, percent
  - calendar episode rows: popcorn, status, watched, heart, percent
  - popup episode rows: popcorn, status, watched, heart, percent
