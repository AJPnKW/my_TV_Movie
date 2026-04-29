<!--
FILE: docs/ui_standardization/proposed_standard_components.md
VERSION: 1.0.0
UPDATED: 2026-03-13T00:00:00Z
CHANGE NOTES:
- Initial proposed baseline component standards
- Includes reuse scope, data contracts, accessibility, and rationale
-->
# Proposed Standard Components

## `standard_show_popup`
- Purpose: primary deep-detail surface for a show, seasons, and episodes
- Intended reuse scope: main app family (`index`, `shows`, `movies`, `discover`, `calendar`)
- Required sections:
  - backdrop header
  - poster block
  - title and TMDB id label
  - watch-status band
  - pill/fact strip
  - metadata facts
  - overview
  - season picker
  - season detail panel
  - episode carousel/list
- Optional sections:
  - network logo
  - production block
  - where-to-watch provider button
  - Rotten Tomatoes link
- Required actions:
  - close
  - season switch
  - open provider modal if data exists
  - open episode streaming links if data exists
- Optional actions:
  - toggle watched at show/season/episode level
  - watchlist status changes
- Required data fields:
  - `tmdb_id`
  - `title|name`
  - `overview`
  - `poster_local|poster_path`
  - `seasons[]`
- Optional data fields:
  - `backdrop_local|backdrop_path`
  - `genres[]`
  - `networks[]`
  - `vote_average`
  - `vote_count`
  - `production_companies`
  - `links`
  - episode `runtime`, `air_date`, `still_local|still_path`, `links`
- Responsive behavior expectations:
  - poster + facts collapse to single column below tablet width
  - episode list can remain horizontal but must degrade to stacked cards on narrow screens
- Accessibility expectations:
  - dialog semantics preserved
  - initial focus to close control or first interactive control
  - focus trap retained
  - season radios remain keyboard reachable
- Backward compatibility notes:
  - preserve current modal IDs and `data-watch-*` selectors initially
  - support episode number aliases and current image/link fallback helpers
- Merge rationale citing current variants:
  - layout from `SHOW_POPUP_APP_V1`
  - behavior from `SHOW_POPUP_APP_V2`
  - season copy/fallback clarity from `WATCHME_DETAIL_SHOW_V1` and `TREE_SEASON_CARD_V1`

## `standard_movie_popup`
- Purpose: primary deep-detail surface for a movie
- Intended reuse scope: main app family
- Required sections:
  - poster block
  - title and TMDB id label
  - watch-status band
  - overview
  - action row
- Optional sections:
  - backdrop
  - production chips
  - pill/fact strip
- Required actions:
  - close
  - provider modal
  - streaming links when present
- Optional actions:
  - watched toggle
  - watchlist status change
  - Rotten Tomatoes
- Required data fields:
  - `tmdb_id`
  - `title`
  - `overview`
  - `poster_local|poster_path`
- Optional data fields:
  - `backdrop_local|backdrop_path`
  - `runtime`
  - `genres[]`
  - `production_companies`
  - `links`
- Responsive behavior expectations:
  - 2-column hero becomes single column on small screens
- Accessibility expectations:
  - same dialog/focus rules as show popup
  - actionable links remain visible with keyboard focus
- Backward compatibility notes:
  - keep provider modal contract intact
- Merge rationale citing current variants:
  - behavior from `MOVIE_POPUP_APP_V2`
  - optional lighter fact row from `WATCHME_DETAIL_MOVIE_V1`

## `standard_show_card`
- Purpose: scan-friendly show browse card
- Intended reuse scope: main app family grids
- Required sections:
  - title
  - poster
  - metadata line
  - primary action surface
- Optional sections:
  - watch toggle
  - icon strip
  - status chip
- Required actions:
  - open show detail
- Optional actions:
  - toggle watched
  - watchlist status/icon strip actions
- Required data fields:
  - `tmdb_id`
  - `title|name`
  - `poster_local|poster_path`
- Optional data fields:
  - `first_air_date`
  - `last_air_date`
  - `vote_average`
  - watch-state inputs
- Responsive behavior expectations:
  - keep poster dominant
  - metadata truncates, not wraps uncontrolled
- Accessibility expectations:
  - single obvious primary click target
  - toggle/button controls must not steal full-card activation accidentally
- Backward compatibility notes:
  - preserve `data-show-open` and current icon-strip actions first
- Merge rationale citing current variants:
  - markup baseline from `SHOW_CARD_DISCOVER_V2`
  - lighter density option from `SHOW_CARD_APP_V1`

## `standard_movie_card`
- Purpose: scan-friendly movie browse card
- Intended reuse scope: main app family grids
- Required sections:
  - title
  - poster
  - metadata line
  - icon/action row
- Optional sections:
  - provider action stack
  - watched toggle
- Required actions:
  - open movie detail
- Optional actions:
  - direct provider launch
  - watched toggle
  - watchlist/icon-strip actions
- Required data fields:
  - `tmdb_id`
  - `title`
  - `poster_local|poster_path`
- Optional data fields:
  - `release_date`
  - `runtime`
  - `genres[]`
  - `links`
  - watch-state inputs
- Responsive behavior expectations:
  - keep action row compact; provider buttons may collapse to icons only
- Accessibility expectations:
  - provider buttons need labels/tooltips
- Backward compatibility notes:
  - preserve `data-movie-open`
- Merge rationale citing current variants:
  - action-capable baseline from `MOVIE_CARD_APP_V2`
  - lighter mode fallback from `MOVIE_CARD_APP_V1`

## `standard_episode_card`
- Purpose: reusable episode card for detail contexts
- Intended reuse scope: show popup and detail-oriented episode lists
- Required sections:
  - image or fallback media block
  - season/episode badge
  - title
  - metadata row
  - action row
- Optional sections:
  - overview/snippet
  - watched toggle
  - provider/status chips
  - secondary action bar
- Required actions:
  - provider links when available
- Optional actions:
  - watched toggle
  - TMDB link
  - history/list/rate actions in denser variants
- Required data fields:
  - `episode_number|number|ep`
  - `season_number`
  - `title|name`
- Optional data fields:
  - `overview`
  - `runtime`
  - `air_date`
  - `still_local|still_path`
  - `links`
  - watch-state inputs
- Responsive behavior expectations:
  - support a standard detail density and a compact density variant
- Accessibility expectations:
  - focusable card only when it has a clear primary action
  - toggle and provider links remain individually keyboard accessible
- Backward compatibility notes:
  - helper must support link cascade option
- Merge rationale citing current variants:
  - base shell from `EPISODE_CARD_POPUP_V2`
  - readable copy from `WATCHME_DETAIL_EPISODE_V1`
  - compact action concepts from `CAL_EPISODE_CARD_V1`

## Supporting Abstractions

### `standard_metadata_row`
- Required because date/runtime/genre/network/rating order drifts everywhere

### `standard_action_bar`
- Required because icon strip, provider stack, and mini buttons are all partial implementations of the same concept

### `standard_poster_block`
- Required because movie/show detail surfaces repeatedly combine poster, title, band, facts, and overview
