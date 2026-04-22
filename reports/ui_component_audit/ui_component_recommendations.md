<!--
FILE: reports/ui_component_audit/ui_component_recommendations.md
VERSION: 1.0.0
UPDATED: 2026-03-13T00:00:00Z
CHANGE NOTES:
- Initial baseline recommendations and phased implementation order
-->
# UI Component Recommendations

## Baseline Recommendations

### `standard_show_popup`
- Baseline source: `SHOW_POPUP_APP_V2` from `web/discover.html`
- Merge in:
  - visual hero balance and spacing already shared with `SHOW_POPUP_APP_V1`
  - `watch.me` section clarity for season summary copy
  - `tv_shows_listing` explicit empty-state language for missing seasons/episodes
- Retire:
  - toggle-less fork as an independent implementation
- Preserve page-specific exceptions:
  - calendar may keep extra episode action density outside popup

### `standard_movie_popup`
- Baseline source: `MOVIE_POPUP_APP_V2` from `web/discover.html` / `web/calendar.html`
- Merge in:
  - `watch.me` pill-row simplicity for metadata ordering
- Retire:
  - `MOVIE_POPUP_APP_V1` once equivalent controls exist
- Preserve page-specific exceptions:
  - no playback modal behavior should be mixed in from `heated-rivalry`

### `standard_show_card`
- Baseline source: `SHOW_CARD_DISCOVER_V2`
- Merge in:
  - lighter density option from `SHOW_CARD_APP_V1`
  - keyboard affordance lessons from `watch_me/watch_me`
- Preserve page-specific exceptions:
  - utility tree card remains separate

### `standard_movie_card`
- Baseline source: `MOVIE_CARD_APP_V2`
- Merge in:
  - icon-strip-only fallback mode from `MOVIE_CARD_APP_V1`
  - compact release card action grouping from `WATCHME_CAROUSEL_MOVIE_V1`
- Preserve page-specific exceptions:
  - calendar compact movie chip remains distinct

### `standard_episode_card`
- Baseline source: `EPISODE_CARD_POPUP_V2`
- Merge in:
  - calendar action bar ideas from `CAL_EPISODE_CARD_V1`
  - text hierarchy from `WATCHME_DETAIL_EPISODE_V1`
  - explicit link-cascade rule from `TREE_EPISODE_ROW_V1`
- Preserve page-specific exceptions:
  - compact weekly card in `watch_me/watch_me`
  - bespoke campaign card in `heated-rivalry`

## Supporting Abstractions Worth Introducing Later
- `standard_action_bar`
  - because icon strip, action stack, provider row, and compact link row are solving the same problem differently
- `standard_metadata_row`
  - because runtime/date/genre/network/rating ordering drifts across every family
- `standard_poster_block`
  - because poster + backdrop + title + pills + watch band repeats in show/movie detail surfaces
- `standard_episode_list_item`
  - because episode cards are the highest-drift component

## What Must Remain Page-Specific
- Calendar chip density and multi-action layout
- `watch_me/watch_me` weekly carousel compact interaction model
- `tv_shows_listing` expandable tree utility
- `heated-rivalry` promotional/player experience

## Phased Implementation Order
1. Extract and approve standards on paper only.
2. Implement shared markup/helpers for popup internals first, without changing visual output.
3. Convert show popup forks to one standard.
4. Convert movie popup forks to one standard.
5. Convert show/movie grid cards next.
6. Standardize popup episode cards, then optionally add density variants for calendar/weekly views.

## Why This Order
- Popups carry the heaviest behavior drift and the highest coupling to state, focus, and re-render logic.
- Cards can tolerate staged unification more safely once popup behavior is stable.
- Episode cards should come after popup shell unification because they are nested inside the show popup and also reused elsewhere conceptually.
