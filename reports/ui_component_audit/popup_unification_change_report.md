# Popup Unification Change Report

Timestamp: `20260314T160015Z`

Files changed:
- `web/shows.html`
- `web/movies.html`

Implemented:
- standardized icon-strip info action to the shared `View` button treatment for the standalone pages
- added movie popup watch-status band rendering in both standalone pages
- added standalone movie popup watch-status wiring in both standalone pages
- updated `web/shows.html` show popup to use the same popup watch-status band contract as the dashboard baseline
- updated `web/shows.html` season and episode popup internals to use the same popup-era helper path (`pickAirDate`) and popup watch hook wiring as the dashboard baseline

Preserved:
- modal IDs and close button IDs
- existing `data-*` hooks used by popup actions
- page-local structure outside the popup standardization slice
- deferred surfaces outside the touched files

Not changed:
- `web/index.html`
- non-popup grid/card layouts beyond the icon-strip info presentation
- provider modal behavior

Validation target mapping:
- shared helper layer exists: confirmed pre-existing in all three app-family pages
- preserved contract manifest exists: created in this pass
- show popup and movie popup unified for main app family: completed for `index`, `shows`, and `movies`
- popup episode-card behavior standardized enough for popup use: completed for standalone show popup path
- selectors, IDs, and hooks remain compatible: confirmed in validation log
- deferred surfaces stay untouched: confirmed by file scope
