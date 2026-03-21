<!--
FILE: reports/ui_component_audit/ui_component_dependency_map.md
VERSION: 1.0.0
UPDATED: 2026-03-13T00:00:00Z
CHANGE NOTES:
- Initial file-to-file and render-chain dependency mapping
- Highlighted hidden DOM and data assumptions
-->
# UI Component Dependency Map

## 1. Main App Family Dependency Cluster

### Files
- `web/index.html`
- `web/shows.html`
- `web/movies.html`
- `web/discover.html`
- `web/calendar.html`

### Render Chain
- `loadAll()` loads `config.json`, `data/data.json`, `inputs.json`, watch-state source
- `renderShows()` -> `showCardHtml()` -> `buildIconStripHtml()` -> action wiring
- `renderMovies()` -> `movieCardHtml()` -> `buildIconStripHtml()` and sometimes `.actionstack`
- `renderCalendar()` -> calendar template literals -> chip/card wiring
- `openShowModal()` -> `buildShowPopupHtml()` -> `wireShowPopup()`
- `openMovieModal()` -> movie popup HTML -> `wireMoviePopup()`
- `renderWatchProvidersHtml()` -> provider modal

### Shared Helpers
- `buildMediaLinks()`
- `renderWatchProvidersHtml()`
- `getRtLink()`
- `pickImage()`
- `pickAirDate()`
- `isShowWatched()`, `isMovieWatched()`, `isSeasonWatched()`, `isEpisodeWatched()`
- `setShowWatched()`, `setSeasonWatched()`, `setEpisodeWatched()`, `setMovieWatched()`
- `watchStatusBandHtml()`

### Hidden DOM Assumptions
- `wireShowPopup()` assumes:
  - `.seasonopt` wrapper contains radio input
  - `.carousel` exists with `[data-ep-nav]` buttons
  - watch selectors use exact `data-watch-*` attributes
- `wireMoviePopup()` assumes popup body is fully replaced on every toggle and rebound after re-render
- Modal focus trap depends on `#modalBack`, `#modalCard`, `#providerBack`, `#providerCard` IDs

### Hidden Data Assumptions
- Show identity is always numeric `tmdb_id`
- Episodes may use `episode_number`, `number`, or `ep`
- Images may be local or TMDB paths; helper order matters
- `networks[0]` is treated as canonical display network
- Watchlist/watch-state availability changes which controls render

### CSS Coupling
- Inline CSS in each HTML file defines most component shapes
- `buildShowPopupHtml()` depends on exact classes:
  - `.showwrap`, `.showback`, `.showoverlay`, `.showinner`, `.hero`, `.poster`, `.heroright`, `.seasonsgrid`, `.seasondetails`, `.episodeswrap`, `.epcard`
- Card renderers depend on `.card`, `.cardbody`, `.cardhead`, `.imgbox`, `.cardmeta`

## 2. `watch.me` Detail Page Cluster

### Files
- `web/watch.me.html`

### Render Chain
- URL param parse -> `loadDataJson()` -> `renderMovie()` or `renderShow()` -> `renderSeasonDetail()`

### Hidden Assumptions
- Single active item only
- Uses direct element IDs instead of delegated event wiring
- Episode links are direct on episode object; no cascade implemented

### CSS Coupling
- Strong coupling to `.infoCard`, `.sectionCard`, `.epCard`, `.miniBtn`

## 3. `watch_me/watch_me` Carousel Cluster

### Files
- `web/watch_me/watch_me.html`
- `web/css/my_tv_hub.css`

### Render Chain
- `loadWatchMeTuning()` + `loadData()` + `loadWatchedMap()`
- `flattenData()` -> `filtEpisodes()` / `filtMovies()`
- `buildTvWeeks()` / `buildMovieModes()` -> `tvCarouselHtml()` / `moviesCarouselHtml()` -> `episodeCard()` / `movieCard()`
- `wireKeyboardNav()` and watched-toggle API calls

### Hidden Assumptions
- Compact cards are keyboard focus targets
- Watched state depends on external API or fallback JSON
- Media provider UI is configurable via config

### CSS Coupling
- Reuses shared stylesheet but overrides local card proportions and overlay layout

## 4. `tv_shows_listing` Utility Tree Cluster

### Files
- `web/tv_shows_listing.html`

### Render Chain
- `loadJson()` -> sort/filter -> `buildShowCard()` / `buildMovieCard()`
- show expand -> `buildSeasonCard()` -> season expand -> `buildEpisodeRow()`

### Hidden Assumptions
- Canonical data path is `show.seasons[].episodes[]`
- Links may be missing on episode and season nodes; cascade is mandatory

### CSS Coupling
- Tree behavior depends on `.children[data-open]`, twisty button state, and row composition

## 5. `heated-rivalry` Bespoke Cluster

### Files
- `web/heated-rivalry.html`

### Render Chain
- local `EPISODES` constant -> `buildSeasonPicker()` -> `renderEpisodeCards()` -> `setActiveEpisode()` -> player modal

### Hidden Assumptions
- Local episode data schema includes drive/download fields not used elsewhere
- Modal purpose is playback, not detail browsing

## 6. Cross-Cluster Reuse Opportunities
- `standard_action_bar`: merge icon strip, action stack, compact provider links
- `standard_metadata_row`: unify title/date/runtime/network/genre patterns
- `standard_poster_block`: shared poster/backdrop/pill header shell
- `standard_episode_list_item`: unify episode image badge meta action block, with density variants

## 7. Standardization Constraints
- Do not rename modal IDs before rewriting focus-trap logic
- Do not collapse calendar chips into popup episode markup without preserving chip-only actions
- Do not centralize CSS by moving classes globally without namespacing family-specific `.card` semantics
- Do not remove direct card provider buttons from pages where they reduce clicks unless a replacement is approved
