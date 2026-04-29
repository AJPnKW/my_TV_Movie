<!--
FILE: docs/ui_standardization/mockup_notes.md
VERSION: 1.0.0
UPDATED: 2026-03-13T00:00:00Z
CHANGE NOTES:
- Initial rationale notes for static review mockups
-->
# Mockup Notes

## Variant Influence By Mockup

### `mockup_show_popup.html`
- Primary influence: `SHOW_POPUP_APP_V2` from `web/discover.html`
- Secondary influence:
  - `SHOW_POPUP_APP_V1` for the existing hero/backdrop rhythm
  - `WATCHME_DETAIL_SHOW_V1` for cleaner section separation
  - `TREE_SEASON_CARD_V1` for explicit season/empty-state thinking

### `mockup_movie_popup.html`
- Primary influence: `MOVIE_POPUP_APP_V2`
- Secondary influence:
  - `WATCHME_DETAIL_MOVIE_V1` for a simpler metadata cadence

### `mockup_show_card.html`
- Primary influence: `SHOW_CARD_DISCOVER_V2`
- Secondary influence:
  - `SHOW_CARD_APP_V1` for lighter density

### `mockup_movie_card.html`
- Primary influence: `MOVIE_CARD_APP_V2`
- Secondary influence:
  - `MOVIE_CARD_APP_V1` for the simpler fallback mode
  - `WATCHME_CAROUSEL_MOVIE_V1` for direct action emphasis

### `mockup_episode_card.html`
- Primary influence: `EPISODE_CARD_POPUP_V2`
- Secondary influence:
  - `WATCHME_DETAIL_EPISODE_V1` for text readability
  - `CAL_EPISODE_CARD_V1` for action-bar density ideas
  - `TREE_EPISODE_ROW_V1` for fallback/link-contract awareness

## Intentionally Kept
- Dark cinematic styling direction already used across the repo
- Poster/backdrop-first hierarchy
- Pill/fact-strip language
- A dedicated watch-status band in popup detail surfaces
- Direct provider actions where they shorten the task flow

## Intentionally Excluded
- Calendar-only micro-actions such as history/date/list/rate on every episode card
- `heated-rivalry` promotional styling and player behavior
- `tv_shows_listing` tree/twisty utility layout
- Production page wiring or live data loading

## What Remains Page-Specific
- Calendar compact chips and dense side actions
- `watch_me/watch_me` weekly carousel density and keyboard model
- `tv_shows_listing` expand/collapse tree
- `heated-rivalry` campaign/player experience

## Assumptions
- The next phase will standardize the main app family before standalone watch pages
- Current modal IDs and existing `data-*` selectors should stay stable during the first implementation pass
- Episode link fallback behavior should be centralized before any broad episode-card swap
