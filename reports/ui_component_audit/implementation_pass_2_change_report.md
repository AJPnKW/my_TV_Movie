# Implementation Pass 2 Change Report

Timestamp: `20260314T172445Z`

## Scope Completed

- locked baseline contract v2 around the revised component set
- retired `season_card` from the primary baseline contract
- rendered the previously stubbed watch-status band helper
- rendered watched toggles on popup/card surfaces where existing handlers already existed
- introduced popcorn-only watch-source chooser entry helpers
- moved movie and popup episode watch actions toward chooser-based entry
- preserved current modal IDs and existing `data-watch-*` compatibility hooks

## Files Updated In Code

- `web/index.html`
- `web/shows.html`
- `web/movies.html`

## Key Compatibility Notes

- existing modal shell IDs remain unchanged
- existing provider modal shell remains the chooser shell
- existing watch toggle hooks remain intact
- existing watch-status choice hook remains intact
- no new third-party backup provider integrations were added
