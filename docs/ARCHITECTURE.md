# My TV Hub -- Architecture Contract

## Core Principles

-   Single application system serving multiple views from the same
    dataset.
-   Trakt is the primary metadata authority.
-   TMDB is supplemental metadata and artwork provider.
-   All assets cached locally under /assets.

## Core Pages

-   Dashboard (index.html)
-   Shows (shows.html)
-   Movies (movies.html)
-   Calendar (calendar.html)
-   Watch Me (watch_me/watch_me.html)
-   Discover (discover.html)
-   Config (config.html)
-   Inputs Editor (inputs_editor.html)

## Shared Runtime Modules

web/js/app_runtime.js\
web/js/card_renderer.js\
web/js/action_bar.js

## Card Model

All media cards must use overlay layout.

Poster Image\
Overlay Gradient\
Title\
Metadata\
Icon Strip

Icon Strip Standard:

Movies / Episodes 🍿 ⌚ 💕 🔖 ⭐%

Shows / Seasons ⌚ 💕 🔖 ⭐%

## Calendar Layout

Calendar must render as a 7‑column wall calendar grid.

Each day cell contains compact episode cards.

No sidebar should be present on the calendar view.
