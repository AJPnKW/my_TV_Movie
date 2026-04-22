FILE: reports/ui_component_audit/action_bar_cleanup_report.md
VERSION: v1.0
UPDATED: 2026-03-15T17:58:07Z
CHANGE NOTES:
- Recorded the shared action-bar cleanup pass.
- Confirmed contract ordering remained consistent across main runtime surfaces.

# Action Bar Cleanup Report

## Shared Order Preserved

1. popcorn watch-now chooser
2. favourites
3. watch-status popup selector
4. watched toggle
5. heart icon
6. rating percent

## What Changed

- Restyled the action bar into a cleaner compact horizontal primitive.
- Kept show cards and show popup/detail free of direct popcorn launch.
- Kept movie cards, movie detail, calendar playable items, and episode rows on popcorn-enabled contexts.
- Removed the visual feel of leftover icon-strip-era controls from the cleaned main-card surfaces.

## Validation

- Shows page direct popcorn count: `0`
- Movies page direct popcorn count: `83`
- Show popup direct popcorn count: `0`
- Show popup episode popcorn count: `8`
- Movie popup popcorn count: `1`
