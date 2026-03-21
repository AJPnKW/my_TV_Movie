# Movie Popup UI Contract

## Purpose

Canonical detailed popup for a movie, using the same structural language as the show popup but with a denser movie-focused facts grid and no season rail.

## Popup Structure

1. Sticky popup header
2. Hero block with poster and metadata
3. Detail grid
4. Overview block
5. Backdrop block when available
6. External link row

## Required Fields

- title
- poster
- movie action strip
- overview
- release date
- runtime or unavailable state
- rating percent
- TMDB id

## Optional Fields

- original title
- collection
- tagline
- status
- genres
- studios
- countries
- providers
- IMDb/homepage/Rotten Tomatoes links
- vote count

## Data Mapping

- title: `title`
- original title: `original_title` if different
- poster: `poster_local`, `poster_path`
- backdrop: `backdrop_local`, `backdrop_path`
- release date: `release_date`
- runtime: `runtime`
- status: `status`
- genres: `genres[].name`
- collection: `collection.name` when object, or string form if already normalized
- studios: `production_companies[].name`
- countries: `production_countries[].name`
- provider summary: `watch_providers`
- summary: `overview`
- tagline: `tagline`
- IDs and links: `tmdb_id`, `imdb_id`, `trakt_id`, `homepage`, `links`
- rating percent: rounded `vote_average * 10`

## Icon Strip Contract

Movie popup action strip uses the same movie contract as movie cards:

- left: popcorn
- middle: watch-status, favourites, bookmark
- right: gold star + rating percent

## Alignment Rules

- poster left, detail content right on desktop
- action strip directly under the title block
- detail cards align in a tight grid
- backdrop sits below the hero, not behind the copy

## Spacing Rules

- same popup body spacing as the show popup
- detail cards keep compact vertical spacing for fast scanning

## Responsive Behavior

- phone stacks poster above the metadata column
- tablet uses two columns when space allows
- Android TV keeps the action strip and close button in a predictable D-pad order

## Must Never Appear

- season or episode controls
- floating action icons over the poster
- rating detached from the gold star


## Patch focus

Movie popup mirrors the show popup language but removes season-specific sections and emphasizes provider/runtime/release/rating data.

### Current enforcement

- single shared action row
- no wrapping icons
- no broken-image placeholders
- consistent overlay hierarchy
- responsive behavior must remain stable at Android-TV-like widths
