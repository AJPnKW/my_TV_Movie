# Show Popup UI Contract

## Purpose

Dense, information-rich show detail popup. This is the canonical detailed surface for a series and must be materially richer than a browse card. It should feel closer to a reference panel than a lightweight summary.

## Popup Structure

1. Sticky popup header
Title, close button, focus entry point.

2. Hero block
Poster left, dense metadata and actions right.

3. Detail grid
High-signal facts in compact cards.

4. Narrative block
Overview plus links.

5. Season rail
Horizontal season carousel with previous/next controls.

6. Active season summary
Current season facts, release timing, counts, and overview.

7. Episode section
Episode cards using the canonical episode card model.

## Required Hero Fields

- title
- poster artwork
- show action strip
- overview
- status
- season count
- TMDB id

## Optional Hero Fields

- original name
- network list
- genre list
- first air date
- last air date
- next episode timing
- runtime
- creators
- origin countries
- in production
- provider summary
- IMDb or homepage links
- vote average and vote count

## Exact Data Mapping From `data/data.json`

- title: `title`, else `name`
- original title line: `original_name` if different
- poster: `poster_local`, `poster_path`
- backdrop: `backdrop_local`, `backdrop_path`
- genres: `genres[].name`
- networks: `networks[].name`
- creators: `created_by[].name`
- runtime: first value from `episode_run_time[]`
- status: `status`
- in production: `in_production`
- first aired: `first_air_date`
- last aired: `last_air_date`
- season count: `number_of_seasons`
- episode count: `number_of_episodes`
- current season: selected item from `seasons[]`
- current season episode count: `selectedSeason.episodes.length`
- next season / next episode data: `next_episode_to_air` where available
- previous / last aired episode: `last_episode_to_air`
- provider summary: `watch_providers`
- IDs and links: `tmdb_id`, `imdb_id`, `tvdb_id`, `trakt_id`, `homepage`, `links`
- rating percent: rounded `vote_average * 10`

## Detail Grid Minimum Content

- release window: first air date and last air date
- status / production state
- network list
- genres
- creators
- runtime
- seasons total
- episodes total
- current season label
- current season release date
- current season episode count
- next episode or next season timing if available
- rating and vote count
- TMDB id

## Season Carousel Contract

- horizontal only
- prev/next buttons outside the track
- active season visibly selected
- card body uses the canonical show/season icon strip contract
- season selection updates the season summary and the episode grid
- selected season should scroll into view when changed
- D-pad left/right must move across season cards and nav buttons without losing focus

## Episode Section Contract

- uses the exact episode-card contract
- no bespoke row layout separate from canonical episode cards
- selected season episodes render in a responsive grid
- clicking an episode card outside the action strip opens the show detail context, not a separate incompatible layout

## Alignment Rules

- poster column is fixed; metadata column is fluid
- detail cards use dense two-column layout on desktop, one-column on narrow screens
- section headings align with content edges
- action strip sits directly below the hero title block

## Spacing Rules

- popup body padding: 14px desktop, 12px tablet, 10px phone
- hero gap: 16px to 20px
- section spacing: 16px to 18px
- season cards maintain the same body spacing as browse cards

## Responsive Behavior

- phone: hero stacks vertically, detail grid becomes one column
- tablet: hero can remain two-column if poster and metadata both fit
- Android TV: popup remains centered, focused, and scrollable by D-pad; season carousel buttons and cards must be reachable in order

## TV / Focus Rules

- show popup is a trapped focus layer while open
- background content must not scroll
- topmost popup remains the active focus layer if a provider modal opens above it
- Tab and D-pad movement stay inside the popup

## Must Never Appear

- sparse movie-style metadata only
- vertical season dropdown as the primary season selector
- mixed legacy episode row layouts
- background page scrolling behind the popup
- action strip icons drifting onto the poster
