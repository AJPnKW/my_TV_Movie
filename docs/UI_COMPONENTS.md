# UI Components

`docs/00_master_contract.html` remains the authoritative UI contract. This file summarizes component ownership for implementation passes.

## Primary Navigation

- Owner: active HTML page shells plus `web/js/media_library_header_button.js`
- Selector: `.top > .nav[role="tablist"][aria-label="Primary"]`
- Required Release Calendar link: `[data-tab="release-calendar"]` -> `./release_calendar.html`
- Required Media Library link: `#mediaLibraryHeaderButton`
- Required Release Calendar behavior: opens the release-focused calendar in the same app tab and remains visible in the normal icon row between Movies and Calendar.
- Release Calendar icon: `🆕`, intentionally distinct from the existing schedule Calendar icon `📅` so the two calendar concepts are visually differentiable.
- Required Media Library behavior: opens `./Media_Library.html` in a new tab and remains visible within the normal icon row.

## Release Calendar

- Page shell: `web/release_calendar.html`
- Runtime: `web/js/release_calendar.js`
- Styling: `web/css/release_calendar.css`, layered on `web/css/main_app.css`
- Data source: canonical `data/data.json`
- Movie source field: `movies[].release_date`
- TV source fields: `shows[].first_air_date` and `shows[].seasons[].air_date`
- Season 0 / Specials are excluded.
- Same-date series premiere and Season 1 are rendered once as `Series Premiere • Season 1`.
- Normal episode air dates are deliberately excluded; those remain in the existing `web/calendar.html` schedule calendar.
- Filters: All, TV & Seasons, Movies.
- Month controls: Today, Prev, Next.
- Desktop/tablet: seven-column month grid.
- Phone: one-column day list using the same underlying event set and filters.
- Image rule for movies: prefer `poster_local`; otherwise resolve `poster_path` through the TMDB image host.
- Image rule for TV series premieres: prefer the show `poster_local`; otherwise resolve the show `poster_path` through TMDB.
- Image rule for season premieres: prefer the season's own `poster_local`, then the season's `poster_path`; only fall back to the parent show poster if the season has no usable poster.
- TMDB `poster_path` values beginning with `/` are TMDB API paths, not site-root URLs. They must be prefixed with the TMDB image host rather than requested directly from the GitHub Pages site root.
- Every rendered release entry is interactive. Mouse/touch click and keyboard Enter/Space open a modal rather than silently navigating away.
- Movie release entries open a Movie detail popup using the movie poster, title, release date, runtime when present, genres when present, TMDB ID, and overview.
- Series premiere entries open a Show detail popup using the show poster, title, premiere date, status when present, genres when present, TMDB ID, and overview.
- Season premiere entries open a Season detail popup using the season poster first, the show poster only as fallback, show + season name, premiere date, episode count when present, show TMDB ID, and season overview with show overview fallback.
- Release detail popups use the existing `.app-modal-*` shell classes from `main_app.css` so popup presentation remains consistent with the app family.
- Popup close behavior: Close button, clicking the backdrop outside the card, or Escape. The clicked release entry must expose `role="button"`, `tabindex="0"`, and an accessible label.

## Watch Source Popup

- Provider renderer: `renderWatchProvidersHtml` in `web/js/app_runtime.js`
- Filename copy renderer: `renderWatchSourceMediaDetailHtml` in `web/js/app_runtime.js`
- Copy binding: `openProviderModal` in `web/js/app_runtime.js`
- Popup media-detail block: `web/js/popup_controller.js`

## Cards and Actions

- Canonical cards: `web/js/card_renderer.js`
- Runtime card call-sites: `web/js/app_runtime.js`
- Action strip: `web/js/action_bar.js`
- Active CSS: `web/css/main_app.css`

## Browse Filters

- Canonical Shows search: `state.search.shows`, rendered as `#searchShows`
- Canonical Movies search: `state.search.movies`, rendered as `#searchMovies`
- Canonical Shows scope/status filter: `state.filters.shows.scope`, rendered as `#filterShowsScope [data-scope]`
- Canonical Movies scope/status filter: `state.filters.movies.scope`, rendered as `#filterMoviesScope [data-scope]`
- Current definitions and result filtering: `web/js/app_runtime.js`, using `web/config.json -> browse.current`
- Responsive filter and genre layout: `web/css/main_app.css`

Phone, tablet, desktop, and TV-style layouts must expose the same Search, filters, sorting, cards, actions, navigation views, Release Calendar event content, and release-entry popup interactions. CSS may change layout only.
