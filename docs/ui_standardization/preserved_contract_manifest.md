# Preserved Contract Manifest

Timestamp: `20260314T160015Z`

Scope:
- `web/shows.html`
- `web/movies.html`

Preserved stable IDs:
- `modalBack`
- `modalCard`
- `modalClose`

Preserved popup/action hooks:
- `data-action="open-info"`
- `data-watch-status-choice`
- `data-watch-season`
- `data-watch-episode`
- `data-watch-episode-card`
- `data-where-watch="show"`
- `data-where-watch="movie"`

Preserved behavior boundaries:
- modal container and close controls remain unchanged
- popup watch-status interactions continue to use existing `data-watch-status-choice` contract
- season and episode popup controls continue to use existing `data-watch-season` and `data-watch-episode` hooks
- existing popup episode-card baseline hook `data-watch-episode-card` remains present
- deferred surfaces outside `web/shows.html` and `web/movies.html` were not changed

Standardization applied in this pass:
- aligned standalone movie popup behavior with the dashboard baseline
- aligned standalone show popup watch-status and popup episode-card behavior with the dashboard baseline
- aligned the info action presentation to the app-family `View` treatment while preserving `data-action="open-info"`
