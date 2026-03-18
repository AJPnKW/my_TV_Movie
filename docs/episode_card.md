# Episode Card UI Contract

## Purpose

Canonical card for episode releases across dashboard, calendar, watch-me, and show detail. The episode card must always communicate show hierarchy first, then episode identity, then quick actions in a single stable strip.

## Layout Zones

1. Poster zone
Still image or fallback artwork.

2. Overlay zone
Bottom gradient overlay pinned inside the poster.

3. Hierarchy zone
Show title as eyebrow.

4. Primary title zone
Episode title or `Episode {number}` fallback.

5. Meta zone
`SxxExx`, air date, runtime in one line.

6. Optional summary zone
Short overview only where vertical space exists, never inside compact calendar cards.

7. Icon strip zone
Single-row action strip under the copy block.

## Required Fields

- `show_title` or resolved parent show `title` / `name`
- `season_number`
- `episode_number`
- `name` or `title`
- one image source from `still_local`, `still_path`, or resolved show fallback

## Optional Fields

- `air_date`
- `runtime`
- `overview`
- `vote_average`
- `vote_count`
- `links`
- parent show watchlist state
- episode watched state
- local watch-status state

## Exact Field Mapping From `data/data.json`

- show eyebrow: parent show `title` or `name`
- card title: episode `title`, else `name`, else `Episode {episode_number}`
- poster/still: episode `still_local`, else `still_path`, else parent show `backdrop_local`, `backdrop_path`, `poster_local`, `poster_path`
- season/episode tag: episode `season_number`, `episode_number`
- air date: episode `air_date`
- runtime: episode `runtime`
- summary: episode `overview`
- rating percent: `vote_average * 10`, rounded, fallback from any normalized `rating_percent` field if present
- popcorn availability: episode `links` and derived watch source options
- favourite state: parent show watchlist entry
- bookmark state: episode watched state
- watch-status state: local status map entry keyed by show + season + episode

## Icon Strip Contract

Movies and episodes share this exact grouping:

- left: popcorn
- middle: watch-status, favourites, bookmark
- right: gold star + rating percent

Rules:

- single row only
- no wrapping
- no icons floating over artwork
- no absolute positioning
- no icon inside pill or button shells
- left group anchors to the left edge
- middle group is centered between the left and right groups
- right group anchors to the right edge
- rating star and percent are inseparable

## Alignment Rules

- eyebrow aligns left above the title
- title aligns left and can use two lines maximum
- meta aligns left on one line where space allows
- summary aligns left and is optional
- icon strip always sits below text, never over poster
- compact variants still preserve left, center, right strip grouping

## Spacing Rules

- poster to body: 0
- body padding: 12px to 14px desktop, 10px to 12px compact/mobile
- eyebrow to title: 4px to 6px
- title to meta: 4px
- copy block to icon strip: 10px to 12px
- icon gap inside groups: 10px to 12px desktop, 8px compact

## Overlay Text Rules

- overlay must show hierarchy and title in this order:
  - show eyebrow
  - episode title
  - meta line
- overlay text uses the bottom gradient only
- no badges or drifting controls inside the overlay
- long show titles truncate before the episode title disappears

## Responsive Behavior

- dashboard and show-detail cards can show summary if vertical room exists
- calendar cards hide summary and keep only hierarchy, title, meta, icon strip
- phone layout keeps one-column cards with full-width poster
- tablet can use grid cards but strip stays one row
- Android TV uses larger focus rings and must keep the icon strip reachable by D-pad without wrap

## Context Differences

- dashboard: overlay-first presentation, show eyebrow is mandatory
- calendar: compact body, max 3 visible items before expansion
- show popup: canonical full episode card model inside the episode grid
- watch-me: same hierarchy and action strip contract, tighter type and poster height

## Must Never Appear

- show title omitted from an episode card
- icon strip on top of the poster
- wrapping icons
- action pills or outlined shells around glyph-only icons
- standalone rating percent without the gold star
- season card styling reused as episode styling
