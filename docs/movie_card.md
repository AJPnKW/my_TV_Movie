# Movie Card UI Contract

## Purpose

Canonical card for movie browse, dashboard recommendations, calendar release items, and watch-me movie rows.

## Layout Zones

1. Poster zone
Poster-first artwork, with backdrop fallback where poster is unavailable.

2. Overlay zone
Bottom gradient with movie title and one meta line.

3. Title zone
Movie title.

4. Meta zone
Release date and runtime or release context.

5. Optional submeta zone
Collection, status, or studio context where useful.

6. Icon strip zone
Single-row action strip under the copy.

## Required Fields

- `title`
- `tmdb_id`
- one artwork source

## Optional Fields

- `release_date`
- `runtime`
- `collection`
- `status`
- `genres`
- `production_companies`
- `vote_average`
- `overview`
- `watch_providers`

## Data Mapping

- title: `title`
- image: `poster_local`, `poster_path`, fallback `backdrop_local`, `backdrop_path`
- meta: `release_date`, optional runtime
- submeta: `collection.name`, `status`, studio names
- summary: `overview`
- rating percent: rounded `vote_average * 10`
- providers: `watch_providers`
- watch source links: `links` plus derived config providers

## Icon Strip Contract

Movies and episodes share this exact grouping:

- left: popcorn
- middle: watch-status, favourites, bookmark
- right: gold star + rating percent

Rules:

- single row only
- no wrapping
- popcorn is the only left-group icon
- middle group remains centered even when rating text width changes
- star and percentage are locked together on the right

## Alignment Rules

- title aligns left
- meta aligns left under the title
- icon strip spans the full body width
- movie cards and show cards must share the same grid rhythm

## Spacing Rules

- card padding matches show cards
- action strip sits directly below the copy with 10px to 12px separation
- compact calendar/watch-me versions reduce copy spacing but preserve strip order

## Overlay Text Rules

- overlay shows title then meta
- no floating icons or badges inside the overlay
- release date can appear in overlay on compact variants

## Responsive Behavior

- poster remains readable at phone widths
- tablet and desktop browse use equal-height cards
- Android TV keeps the popcorn and right rating accessible with D-pad traversal

## Context Differences

- movies page: can show runtime in meta
- dashboard: often only release date or recommendation context
- calendar: compact release-day card with minimal body text
- watch-me: tighter vertical layout but same action grouping

## Must Never Appear

- show hierarchy eyebrow on a pure movie card
- left group collapse that causes centered icons to drift
- rating percent detached from the gold star
