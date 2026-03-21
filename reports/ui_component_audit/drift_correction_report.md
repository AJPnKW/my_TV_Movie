# Drift Correction Report

- Date: 2026-03-15
- Scope: normalized runtime corrective pass

## Outcome

- Retired nested `web/assets` drift after confirming the in-scope runtime does not depend on it.
- Kept the canonical asset root at `assets/...`.
- Updated provider/logo resolution to prefer canonical root service-logo files by TMDB filename, then fall back to TMDB-hosted logos, then text-only chip fallback.
- Removed remaining layout ownership drift from `web/css/my_tv_hub.css` for main-app shell/button-strip structures.
- Fixed `watch_me` bootstrap drift so the page renders shared renderer/action-bar cards promptly even when the LAN watched-state API is unavailable.

## Drift Removed

- `web/assets/logos/services/*` removed as duplicate nested asset root drift.
- `web/watch_me/watch_me.html` no longer stalls before first render waiting on watched-state bootstrap.
- `web/watch_me/watch_me.html` keyboard navigation and layout selectors now target canonical shared card classes instead of the retired local `.card` shape.
- `web/css/my_tv_hub.css` no longer owns old shell/nav/panel/icon-strip layout blocks that belong to component/layout CSS.

## Validation Notes

- Main pages no longer depend on `web/assets`.
- Provider/logo 404 noise was reduced to non-provider misses (`/api/health`, `/favicon.ico`, and `data/watched_github.json` in static smoke mode).
- `watch_me` rendered 2 rows, 24 shared episode cards, 7 shared movie cards, and 31 shared action bars in headless validation.
