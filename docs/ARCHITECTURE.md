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
- Watch Me: `web/watch_me/watch_me.html`
- Config: `web/config.html`
- Inputs Editor: `web/inputs_editor.html`
- Single-title feature pages may use reusable page modules when they do not alter the canonical catalog runtime.

## Reusable Page Modules

- Watch party UI is provided by:
  - `web/js/watch_party.js`
  - `web/css/watch_party.css`
- The watch party module is static-site compatible and may be mounted by single-title pages using page-local episode data.
- The module supports shareable room state, episode handoff, a shared playback timer, and embedded voice/video conferencing through an external meeting provider.
- The module must not become a parallel catalog runtime, editor, watch-state system, or replacement for the shared card/action system.

## Layout Rules

- Calendar is full-width with no left sidebar.
- Shows and movies keep left-sidebar filters.
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
