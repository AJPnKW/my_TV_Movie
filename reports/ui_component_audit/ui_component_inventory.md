<!--
FILE: reports/ui_component_audit/ui_component_inventory.md
VERSION: 1.0.0
UPDATED: 2026-03-13T00:00:00Z
CHANGE NOTES:
- Initial UI component inventory for card/popup ecosystem
- Grouped variants by page and render path
- Marked direct observations versus inference
-->
# UI Component Inventory

## Scope
- Repo root confirmed: `C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie`
- Directly observed files: `web/index.html`, `web/shows.html`, `web/movies.html`, `web/discover.html`, `web/calendar.html`, `web/watch.me.html`, `web/watch_me/watch_me.html`, `web/tv_shows_listing.html`, `web/heated-rivalry.html`, `web/inputs_editor.html`, `web/library_editor.html`, `web/css/my_tv_hub.css`, `build/InputsEditor/xref-InputsEditor.html`
- Inference boundary: pages with matching naming/layout patterns but truncated output were treated as same-family only when backed by direct function/class evidence

## Stable Audit IDs
- `SHOW_CARD_APP_V1`: poster-first show grid card used by the main app family
- `SHOW_CARD_DISCOVER_V2`: app show card with inline watched toggle support
- `MOVIE_CARD_APP_V1`: poster-first movie grid card with icon strip only
- `MOVIE_CARD_APP_V2`: poster-first movie grid card with icon action stack
- `SHOW_POPUP_APP_V1`: hero/backdrop show popup without watch toggles
- `SHOW_POPUP_APP_V2`: hero/backdrop show popup with show/season/episode toggles and watch-status band
- `MOVIE_POPUP_APP_V1`: movie popup without popup watch controls
- `MOVIE_POPUP_APP_V2`: movie popup with popup watch controls and watch-status band
- `EPISODE_CARD_POPUP_V1`: show-popup episode carousel card without watch toggle
- `EPISODE_CARD_POPUP_V2`: show-popup episode carousel card with watch toggle
- `CAL_EPISODE_CARD_V1`: calendar day episode chip/epcard hybrid
- `CAL_MOVIE_CARD_V1`: calendar day movie chip
- `WATCHME_DETAIL_MOVIE_V1`: single-item movie detail page
- `WATCHME_DETAIL_SHOW_V1`: single-item show detail page with season rail
- `WATCHME_DETAIL_EPISODE_V1`: single-item detail episode card in horizontal scroller
- `WATCHME_CAROUSEL_EPISODE_V1`: compact weekly episode card in `web/watch_me/watch_me.html`
- `WATCHME_CAROUSEL_MOVIE_V1`: compact movie release card in `web/watch_me/watch_me.html`
- `TREE_SHOW_CARD_V1`: expandable utility show row/card in `tv_shows_listing`
- `TREE_SEASON_CARD_V1`: expandable season subcard in `tv_shows_listing`
- `TREE_EPISODE_ROW_V1`: episode row in `tv_shows_listing`
- `HEATED_EPISODE_CARD_V1`: bespoke promotional episode card in `heated-rivalry`
- `HEATED_MODAL_PLAYER_V1`: iframe player modal in `heated-rivalry`

## Page Inventory

### `web/index.html`
- View name: Main app shell with dashboard, calendar, shows, movies, watchlist, modal overlays
- Relevant cards found:
  - `SHOW_CARD_APP_V1` via `showCardHtml()` at `web/index.html:4635`
  - `MOVIE_CARD_APP_V1` via `movieCardHtml()` at `web/index.html:4880`
  - `CAL_EPISODE_CARD_V1` and `CAL_MOVIE_CARD_V1` via `renderCalendar()` and calendar item template literals around `web/index.html:3795`, `web/index.html:3851`, `web/index.html:3927`, `web/index.html:3987`
  - Dashboard/supporting cards: `dashcard`, `dashwatchcard`, `watchlistcard`
- Relevant popups found:
  - Shared modal shell `#modalBack/#modalCard` at `web/index.html:2031`
  - Shared provider modal `#providerBack/#providerCard` at `web/index.html:2041`
  - `MOVIE_POPUP_APP_V2` via `openMovieModal()` at `web/index.html:4930`
  - `SHOW_POPUP_APP_V1` via `openShowModal()` and `buildShowPopupHtml()` at `web/index.html:5025`
- Renderer locations:
  - `renderShows()`, `renderMovies()`, `renderWatchlist()`, `renderCalendar()`
  - `buildIconStripHtml()`, `renderWatchProvidersHtml()`, `buildMediaLinks()`
- CSS/style dependencies:
  - Heavy inline CSS in file
  - Class cluster: `.card`, `.cardbody`, `.imgbox`, `.showwrap`, `.showoverlay`, `.epcard`, `.popupwatch`, `.watchlistcard`
- Data dependencies:
  - `state.data.shows[]`, `state.data.movies[]`
  - show fields: `tmdb_id`, `title|name`, `poster_local|poster_path`, `backdrop_local|backdrop_path`, `genres[]`, `networks[]`, `seasons[]`, `links`, `production_companies`
  - episode fields: `episode_number|number|ep`, `still_local|still_path`, `runtime`, `air_date`, `overview`, `links`
- Interaction triggers:
  - `data-show-open`, `data-movie-open`, `data-where-watch`, `data-ep-nav`, icon-strip actions, calendar chip buttons
- Uniqueness/drift notes:
  - Main baseline for overall visual language
  - Show popup omits watch toggles despite wiring support existing
  - Movie popup is richer than show popup in state controls

### `web/shows.html`
- View name: Shows-first app variant
- Relevant cards found:
  - `SHOW_CARD_APP_V1` at `web/shows.html:4749`
  - `MOVIE_CARD_APP_V2` at `web/shows.html:4999`
  - Dashboard/supporting cards same family as `index`
- Relevant popups found:
  - Shared modal shell
  - `MOVIE_POPUP_APP_V1` at `web/shows.html:5047`
  - `SHOW_POPUP_APP_V2` at `web/shows.html:5110`
- Renderer locations:
  - `renderShows()`, `renderMovies()`, `buildShowPopupHtml()`, `wireShowPopup()`
- CSS/style dependencies:
  - Same inline app CSS family as `index`
  - `.actionstack` present on movie cards
  - `.switch.show|season|episode|movie` active in popup family
- Data dependencies:
  - Same main app data contracts plus local watch-state persistence
- Interaction triggers:
  - Same grid triggers plus popup watched toggles and watch-status band
- Uniqueness/drift notes:
  - Strongest show popup candidate
  - Movie popup is visibly poorer than index/discover because it lacks popup watch band

### `web/movies.html`
- View name: Movies-first app variant
- Relevant cards/popups:
  - Same family signatures as `web/shows.html` from `rg` hits: `renderShows()`, `renderMovies()`, `openMovieModal()`, `openShowModal()`, `buildShowPopupHtml()`
- Renderer locations:
  - `web/movies.html:4788`, `web/movies.html:5041`, `web/movies.html:5104`, `web/movies.html:5115`
- CSS/style dependencies:
  - Same inline app CSS family
- Data dependencies:
  - Same main app contracts
- Interaction triggers:
  - Same app-family trigger set
- Uniqueness/drift notes:
  - Directly observed as a forked copy of the same renderer family
  - By naming and line symmetry it participates in the same drift pattern as `shows.html` and `discover.html`

### `web/discover.html`
- View name: Discover-first app variant
- Relevant cards found:
  - `SHOW_CARD_DISCOVER_V2` at `web/discover.html:4629`
  - `MOVIE_CARD_APP_V2` at `web/discover.html:4878`
  - Calendar/dashboard variants same family as `index`
- Relevant popups found:
  - `MOVIE_POPUP_APP_V2` at `web/discover.html:4932`
  - `SHOW_POPUP_APP_V2` at `web/discover.html:5032`
- Renderer locations:
  - `renderShows()`, `renderMovies()`, `openMovieModal()`, `buildShowPopupHtml()`
- CSS/style dependencies:
  - Same inline app CSS family
  - `actionstack`, `popupwatch`, `watchStatusBandHtml`, `switch` classes all active
- Data dependencies:
  - Same main app contracts
- Interaction triggers:
  - card image buttons, inline toggles, provider buttons, watch-status choices, season radios, episode toggles
- Uniqueness/drift notes:
  - Most complete unified behavior set across show/movie cards and popups
  - Best candidate as behavioral source, but not always best as-is for density

### `web/calendar.html`
- View name: Calendar-first app variant
- Relevant cards found:
  - `CAL_EPISODE_CARD_V1` at `web/calendar.html:3835` and `web/calendar.html:3960`
  - `CAL_MOVIE_CARD_V1` at `web/calendar.html:3879`, `web/calendar.html:4011`
  - `SHOW_CARD_APP_V1` and app movie/show grids via `renderShows()` and `renderMovies()`
- Relevant popups found:
  - Shared modal shell at `web/calendar.html:1989`
  - `MOVIE_POPUP_APP_V2` at `web/calendar.html:4917`
  - `SHOW_POPUP_APP_V1` at `web/calendar.html:5017`
- Renderer locations:
  - `buildCalendarEventsForMonth()`, `renderCalendar()`, `openMovieModal()`, `buildShowPopupHtml()`
- CSS/style dependencies:
  - Calendar-specific variables: `--show_card_min`, `--movie_card_min`, `--episode_thumb`, `--epcard-w`
  - calendar-only chips: `.chip.cal-episode`, `.ep-side-actions`, `.watch-toggle`
- Data dependencies:
  - Requires flattened event items derived from canonical `shows[].seasons[].episodes[]` plus movies
- Interaction triggers:
  - calendar chip buttons, watch toggles inside chips, shared modal controls
- Uniqueness/drift notes:
  - Strongest episode card/action density
  - Show popup lags behind calendar card capability

### `web/watch.me.html`
- View name: Single-item watch detail page
- Relevant cards found:
  - `WATCHME_DETAIL_EPISODE_V1` via `renderSeasonDetail()` at `web/watch.me.html:987`
- Relevant popups found:
  - None; page itself is the detail surface
- Detail views found:
  - `WATCHME_DETAIL_MOVIE_V1` via `renderMovie()` at `web/watch.me.html:809`
  - `WATCHME_DETAIL_SHOW_V1` via `renderShow()` at `web/watch.me.html:875`
- Renderer locations:
  - `renderMovie()`, `renderShow()`, `renderSeasonDetail()`, `buildPills()`, `renderPillRow()`
- CSS/style dependencies:
  - Local classes: `.infoCard`, `.sectionCard`, `.episodesScroller`, `.epCard`, `.miniBtn`
- Data dependencies:
  - Direct `../data/data.json` fetch
- Interaction triggers:
  - Season radio list, episode link buttons, TMDB/movie link buttons
- Uniqueness/drift notes:
  - Strong information architecture for single-item detail page
  - Not a popup, but it solves the same detail problem with clearer sectioning than some popups

### `web/watch_me/watch_me.html`
- View name: Weekly carousel watch surface
- Relevant cards found:
  - `WATCHME_CAROUSEL_EPISODE_V1` via `episodeCard()` at `web/watch_me/watch_me.html:672`
  - `WATCHME_CAROUSEL_MOVIE_V1` via `movieCard()` at `web/watch_me/watch_me.html:684`
- Relevant popups found:
  - None
- Renderer locations:
  - `buildTvWeeks()`, `buildMovieModes()`, `tvCarouselHtml()`, `moviesCarouselHtml()`, `render()`
- CSS/style dependencies:
  - Shared external `../css/my_tv_hub.css?v=1.1.3`
  - Local compact card classes: `.card`, `.media`, `.ov`, `.cb`, `.watched-toggle`
- Data dependencies:
  - `data/data.json`
  - external watched API and tuning config
- Interaction triggers:
  - filter sidebar, keyboard navigation, watched toggle buttons, provider icon anchors
- Uniqueness/drift notes:
  - Most compact and keyboard-oriented card implementation
  - Useful supporting abstraction source for action bar and metadata chips

### `web/tv_shows_listing.html`
- View name: Utility listing/tree explorer
- Relevant cards found:
  - `TREE_SHOW_CARD_V1` at `web/tv_shows_listing.html:614`
  - `TREE_SEASON_CARD_V1` at `web/tv_shows_listing.html:548`
  - `TREE_EPISODE_ROW_V1` at `web/tv_shows_listing.html:509`
  - `TREE_MOVIE_CARD_V1` at `web/tv_shows_listing.html:692`
- Relevant popups found:
  - None
- Renderer locations:
  - `buildEpisodeRow()`, `buildSeasonCard()`, `buildShowCard()`, `buildMovieCard()`
- CSS/style dependencies:
  - `.card`, `.subcard`, `.ep-row`, `.pillbar`, `.children`, `.thumb`
- Data dependencies:
  - canonical `show.seasons[]` and `season.episodes[]`
  - explicit link cascade `episode.links -> season.links -> show.links`
- Interaction triggers:
  - twisty expand/collapse buttons, streaming link buttons
- Uniqueness/drift notes:
  - Best explicit data-contract documentation in code
  - Layout is utilitarian, not visual baseline, but excellent dependency reference

### `web/heated-rivalry.html`
- View name: bespoke show landing page
- Relevant cards found:
  - `HEATED_EPISODE_CARD_V1` via `renderEpisodeCards()` at `web/heated-rivalry.html:1454`
- Relevant popups found:
  - `HEATED_MODAL_PLAYER_V1` at `web/heated-rivalry.html:1148`, wired by `modalBackdrop/modalIframe`
- Renderer locations:
  - `buildSeasonPicker()`, `renderEpisodeCards()`, `setActiveEpisode()`
- CSS/style dependencies:
  - `.episode-card`, `.episode-hero-image-shell`, `.episode-card-actions`, `.modal-backdrop`, `.modal-player`
- Data dependencies:
  - local `EPISODES` constant plus `config.json` icon loading
- Interaction triggers:
  - episode card click, title/play/download actions, modal close
- Uniqueness/drift notes:
  - Deliberately bespoke; not a baseline candidate for general app cards/popups
  - Good reference for “hero stills + action row” treatment only

### `web/inputs_editor.html`
- View name: input/admin editor
- Relevant cards found:
  - admin-only `inputs_editor_card`
- Relevant popups found:
  - none
- Notes:
  - Included for completeness only; does not materially affect user-facing card/popup baseline targets

### `web/library_editor.html`
- View name: library/admin editor
- Relevant cards found:
  - admin-only `.card` sections at `web/library_editor.html:189`, `web/library_editor.html:243`
- Relevant popups found:
  - none
- Notes:
  - Same as `inputs_editor`; not part of the consumer-facing baseline

## Observed Cross-Page Families
- Main app family: `index`, `shows`, `movies`, `discover`, `calendar`
- Single-item detail family: `watch.me`
- Compact weekly carousel family: `watch_me/watch_me`
- Utility tree family: `tv_shows_listing`
- Bespoke campaign family: `heated-rivalry`
