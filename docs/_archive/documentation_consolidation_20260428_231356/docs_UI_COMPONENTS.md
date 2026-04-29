# UI Component Contract

## Media Card

Structure

::: media-card
`<img class="poster">`{=html}

::: overlay
    <div class="title"></div>
    <div class="meta"></div>
    <div class="actions"></div>
:::
:::

## Icon Strip

Canonical owner: `web/js/action_bar.js`.

🍿 Watch Source\
⌚ Watched Status\
🎫 Watch List\
💕 Favourite\
Compact Percent Rating

Rules

-   icons only
-   no text buttons
-   consistent order: popcorn, watched status, watch list, favourite, rating
-   rating is compact percent text such as `76%`, with no star icon
-   movie and episode availability state is shown on the popcorn icon with a tight solid square:
-   green = available
-   orange = not yet released
-   red = unavailable
-   watched-status and watch-list icons use green when active and grey when inactive
-   no play icon for watched status
-   no ruler icon for watch list
-   no single yellow heart for favourite
-   legacy bookmark, single-heart, play, ruler, and star treatments are deprecated outside historical docs
-   cards do not place availability badges over poster or still copy; availability is represented by popcorn state only
-   app version badges must read shared metadata, not hard-coded per-page strings

## Card Layout

-   `web/js/card_renderer.js` is the shared card shell for dashboard, calendar, discover, watch-me, shows, and movies.
-   Poster and still media must never sit behind action icons.
-   The action row is always below the media area.
-   At least one title/meta text row must remain outside the image overlay.
-   Dashboard, shows, movies, discover, and watch-me cards must use the same shared card/action system rather than page-local renderers.

## Header And Sections

-   Page shells use `assets/custom/the_boys_hub_logo2.png` as the compact left-aligned logo.
-   Navigation buttons are icon-first and expose their labels through `title`, `aria-label`, and `data-label`.
-   Dashboard section headers use the shared sticky section pattern so the active header is replaced by the next section header without overlapping cards.

## Watch State Keys

-   Episode watched keys are `watched_status:episode:<show_id>:<season>:<episode>`.
-   Movie watched keys are `watched_status:movie:<tmdb_id>`.
-   Show watched keys are `watched_status:show:<tmdb_id>`.
-   `watch_list` and `favourite` use the same item identity context, with `favourite` remaining local-only.

## Asset Runtime Targets

-   `assets/original_downloads/` is immutable source material.
-   Runtime posters in `assets/posters/` target `171x257`.
-   Runtime episode stills in `assets/stills/` target `256x180` after a 10 percent side crop from the source.
-   Runtime backdrops in `assets/backdrops/` target a maximum width of `780`.

## Filter Rails

-   browse/filter rails must provide a visible hide/show toggle
-   shows, movies, and watch-me use the same collapsible filter-rail pattern

## Calendar Modes

-   calendar keeps the wall-grid month view
-   calendar also exposes a month list/tree view for release browsing from the same shared runtime

## Episode Card

-   One shared episode-card family is active across dashboard schedule/history, calendar, watch_me, and the show popup rail.
-   Calendar is the visual layout baseline for the still image, overlay copy, badge placement, and image ratio.
-   Dashboard last-week is the action-row baseline for icon spacing and ordering.
-   `Up Next` is no longer a separate dashboard episode-card system.
