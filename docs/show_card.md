# Show Card UI Contract

## Purpose

Canonical browse and recommendation card for full series entities on dashboard, shows, discover, and watchlist surfaces.

## Layout Zones

1. Poster zone
Series poster or backdrop fallback.

2. Overlay zone
Title-first overlay at the bottom of the image.

3. Eyebrow zone
Used for browse context such as status or network only when explicitly needed.

4. Title zone
Show title.

5. Meta zone
Release timing and high-signal status.

6. Optional submeta zone
Genres, network, or season totals.

7. Icon strip zone
Single-row actions under the copy block.

## Required Fields

- `title` or `name`
- poster or backdrop artwork
- first-air or release timing signal
- TMDB id

## Optional Fields

- `status`
- `genres`
- `networks`
- `number_of_seasons`
- `number_of_episodes`
- `vote_average`
- `overview`
- `watch_providers`
- watchlist, watched, and local status state

## Data Mapping

- title: `title`, else `name`
- image: `poster_local`, `poster_path`, fallback `backdrop_local`, `backdrop_path`
- meta: `first_air_date`
- submeta: `status`, `networks[].name`, `number_of_seasons`
- rating percent: rounded `vote_average * 10`
- providers: `watch_providers`
- local navigation id: `tmdb_id`

## Icon Strip Contract

Shows and seasons share this exact grouping:

- left: empty
- middle: watch-status, favourites, bookmark
- right: gold star + rating percent

Rules:

- single row only
- no wrapping
- no floating icons over poster
- no absolute drift
- no pill shells around icons
- middle group stays visually centered even when left is empty
- right rating stays flush right

## Alignment Rules

- title aligns left
- meta aligns left below title
- optional submeta sits below meta, never above title
- icon strip aligns to the full card width, not the title width

## Spacing Rules

- image aspect should remain consistent with movie cards
- body padding matches movie card padding
- title and meta use the same rhythm as movie cards to keep browse grids stable

## Overlay Text Rules

- overlay can contain title and one meta line
- eyebrow only appears if the context requires it
- no status chips over the image

## Responsive Behavior

- desktop browse grid uses equal-height cards
- phone becomes one-column or narrow two-column only if the title remains readable
- Android TV requires strong focus styling and no hover-only behavior

## Context Differences

- shows page: may include submeta about status and season count
- dashboard and discover: prioritize clean title plus one timing line
- watchlist: can use media-kind or watch-status as the eyebrow if needed

## Must Never Appear

- popcorn on show cards
- a left-side blank gap larger than the centered middle group needs
- more than one row of icons
- badge clutter over the poster
