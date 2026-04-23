# My TV Hub -- Architecture Contract

## Canonical Inputs And Outputs

- Editable canonical input: `data/inputs.json`
- Generated reference artifact: `data/data.json`
- Active runtime index: `data/catalog_index.json`
- Active runtime detail: `data/catalog_detail/<tmdb_id>.json`
- Active calendar feed: `data/calendar.json`
- Canonical asset root: `assets/`

## Runtime Model

- First-load list, dashboard, shows, movies, and watch-me views must load from `catalog_index.json`.
- Calendar and weekly dashboard date-grouped views must load from `calendar.json`.
- Popup and detail views must lazy-load `catalog_detail/<tmdb_id>.json`.
- `data/data.json` may exist for build/reference/QA purposes but must not be the active first-load runtime dependency.

## Detail Schema Contract

- Movie detail uses one normalized watch block:
  - `watch.embed[]`
  - `watch.providers.{CA,US,GB,AU}[]`
- TV detail uses the same normalized watch block at show level and episode level.
- TV episode data must exist only under `seasons[].episodes[]`.
- Active runtime artifacts must not leak competing watch structures such as `watch_sources`, `source_options`, or `watch_providers`.

## Core Pages

- Dashboard: `web/index.html`
- Shows: `web/shows.html`
- Movies: `web/movies.html`
- Calendar: `web/calendar.html`
- Watch Me: `web/watch_me.html`
- Config: `web/config.html`
- Inputs Editor: `web/inputs_editor.html`
- Legacy redirects:
  - `web/watch_me/watch_me.html`
  - `web/watch.me.html`
  - `web/tv_shows_listing.html`
- Single-title feature pages may use reusable page modules when they do not alter the canonical catalog runtime.

## Reusable Page Modules

- Watch party UI is provided by:
  - `web/js/watch_party.js`
  - `web/css/watch_party.css`
  - `web/js/watch_party_player.js`
  - `web/css/watch_party_player.css`
  - `tools/watch_party_player_server.js`
- The watch party module is static-site compatible and may be mounted by single-title pages using page-local episode data.
- The module supports shareable room state, invite links with selected room/source query parameters, episode handoff, and a shared playback timer.
- The watch-party player is server-backed for room/timer synchronization, but playback source selection is owned by the host page. Single-title pages pass their selected episode/watch URL into `web/js/watch_party_player.js`; local-only media directories are retained only as development/testing fallbacks and must remain untracked.
- Hosted watch-party room sync is deployed as an isolated Docker Compose service under `deploy/watch-party/`. The browser client supports cross-origin HTTPS/WSS room endpoints through the `serverUrl` init option or `window.MyTvMovieWatchPartyServerUrl`.
- The local watch-party player is the reusable path intended for later dashboard/index integration after stabilization.
- The module must not become a parallel catalog runtime, editor, watch-state system, or replacement for the shared card/action system.

## Layout Rules

- Calendar is full-width with no left sidebar.
- Calendar supports two month-level views from the same shared runtime:
  - wall calendar grid
  - month list/tree view
- Shows and movies keep left-sidebar filters.
- Browse-style filter rails must expose a visible hide/show toggle instead of being permanently pinned open.
- Watch Me keeps its own page but uses the shared root shell/runtime, shared cards/actions, and the same collapsible filter-rail pattern.
- Dashboard and calendar weekly layouts must stay TV-first:
  - 7 visible columns at TV/desktop widths where the cards remain readable
  - responsive day/date frames on tablet and mobile instead of squeezing seven columns into unusable cards
  - no page-level horizontal scrolling
  - clean day/date anchors
  - no sticky-header overlap with cards
- Card action icon order is locked:
  - Movies and episodes: popcorn, watch-status, favorites, bookmark, rating
  - Shows and seasons: watch-status, favorites, bookmark, rating

## Pipeline Contract

- Production build flow is `inputs.json -> TMDB -> OMDB -> Trakt -> availability/status -> split-runtime build -> QA`.
- No active production dependency may return to:
  - `tv_list.txt`
  - `movies_list.txt`
  - `live_tv_list.txt`
  - `inputs_parsed.json`
- Local validation and GitHub Actions must enforce the same runtime artifact and schema rules.

## Version Contract

- The visible app version badge/footer must derive from canonical runtime/config metadata, not from hard-coded version strings inside page runtimes.
- `web/config.json > _meta.version` is the current UI-facing version source unless a newer documented shared metadata source replaces it.
