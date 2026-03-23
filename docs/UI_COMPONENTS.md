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

🍿 Watch Source\
⌚ Watch Status\
💕 Favorites\
🔖 Bookmark\
⭐ Rating

Rules

-   icons only
-   no text buttons
-   consistent order

## Episode Card

-   One shared episode-card family is active across dashboard schedule/history, calendar, watch_me, and the show popup rail.
-   Calendar is the visual layout baseline for the still image, overlay copy, badge placement, and image ratio.
-   Dashboard last-week is the action-row baseline for icon spacing and ordering.
-   `Up Next` is no longer a separate dashboard episode-card system.
