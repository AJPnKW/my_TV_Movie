# Tracking UI Contract

Timestamp: `20260314T172445Z`

Frontend-only contract for this pass.

## Current UI Hooks

| concern | current hook |
|---|---|
| show watched | `data-watch-show` |
| movie watched | `data-watch-movie`, `data-watch-movie-card`, `data-watch-movie-popup` |
| season watched | `data-watch-season` |
| episode watched | `data-watch-episode`, existing popup/card compatibility via `data-watch-episode-card` |
| show/movie watch status | `data-watch-status-choice` with `data-watch-status-kind='show'|'movie'` |

## Deferred Frontend Contract

| concern | planned contract |
|---|---|
| season watch status | `data-watch-status-kind='season'` with scoped composite identity |
| episode watch status/history | `data-watch-status-kind='episode'` plus future history/date menus |
| season progress | derived from episode watched state now; API-backed summary later |
| episode progress/history | UI placeholder remains chooser/toggle compatible; API writeback deferred |
| API integration | future adapter layer should bind to existing `data-watch-*` and `data-watch-status-*` hooks |

## Future Integration Points

- watched toggle handlers can be redirected from local input state to API-backed services
- watch-status band actions can be redirected from local watchlist state to API-backed status endpoints
- chooser selection analytics or last-used source memory can attach at the modal-open and option-click points
