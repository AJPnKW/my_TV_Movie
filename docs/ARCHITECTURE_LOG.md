# Architecture Change Log

Purpose: Maintain a deterministic history of architectural decisions and structural corrections in the **my_TV_Movie** repository.

Only record architecture-level changes, not minor UI tweaks.

------------------------------------------------------------------------

## 2026-03-16 --- UI Stabilization Baseline

Summary

- `data/inputs.json` is the canonical user-maintained input file.
- `data/data.json` is the generated runtime dataset.
- `web/inputs_editor.html` is the only supported editor.
- `web/library_editor.html` remains retired / redirect-only.
- Shared rendering remains centered on:

    web/js/card_renderer.js
    web/js/action_bar.js
    web/js/app_runtime.js

- Calendar is a full-width wall calendar with no left sidebar.
- Shows and movies own sidebar-driven browse layouts.

------------------------------------------------------------------------

## 2026-03-17 --- UI Contract Baseline V2

Summary

- Added implementation-grade UI contracts for episode cards, show cards, movie cards, show popup, movie popup, TV focus navigation, and calendar view.
- Rebased the main page shells so the shared runtime owns the live browse and calendar layouts instead of stale carryover markup.
- Locked the icon strip to a single-row left / middle / right grouping across dashboard, shows, movies, calendar, popups, and watch-me.
- Densified the show popup, normalized the season selector into a horizontal carousel, and fixed popup focus trap plus background scroll lock behavior.
- Restored full-width calendar controls and corrected `+X more` / `Show less` collapse behavior.

Files

    docs/episode_card.md
    docs/show_card.md
    docs/movie_card.md
    docs/show_popup.md
    docs/movie_popup.md
    docs/focus_navigation_tv.md
    docs/calendar_view.md
    web/js/app_runtime.js
    web/js/card_renderer.js
    web/js/action_bar.js
    web/js/popup_controller.js
    web/css/main_app.css
    web/index.html
    web/shows.html
    web/movies.html
    web/calendar.html
    web/config.html
    web/watch_me/watch_me.html
    reports/ui_component_audit/2026-03-17_ui_contract_baseline.md

Commit

    8cd3442


## 2026-03-20 — Overlay v8 stabilization
- Re-enforced exact episode/movie/show icon strip glyph contract.
- Forced calendar back to a seven-column month grid with horizontal scroll instead of collapsing.
- Standardized portrait sizing for show/movie cards and trimmed episode stills for dashboard/calendar parity.
- Added explicit UI tuning keys in config for card sizing and calendar grid behavior.

## 2026-03-20 — Shell/editor/watch-me stabilization
- Rebased `web/index.html` back to the thin canonical shell so the shared runtime and shared stylesheet own the dashboard-family views.
- Moved shell Inputs Editor entry points to the real local editor flow on `http://127.0.0.1:8787/web/inputs_editor.html` and removed the dead embedded editor experience.
- Hardened `tools/inputs_editor/inputs_editor_server.py` with validation, backup creation, atomic save, and a runtime refresh endpoint.
- Rebuilt `web/watch_me/watch_me.html` around the shared shell, shared card renderer, and shared action bar instead of a separate card/icon system.
- Removed blocking prompts from the asset QA/repair scripts and added a current validation workflow under `.github/workflows/validate.yml`.
- Implementation commit: `6440404`

## 2026-03-21 — Shared card/action/focus cleanup
- Reduced the dashboard-family pages back to thin shell files so `web/js/app_runtime.js` owns the active view layout and there is no page-level drift between dashboard, shows, movies, calendar, discover, and config.
- Removed duplicate `showCardHtml`, `movieCardHtml`, `renderDiscover`, and `renderCalendar` implementations from `web/js/app_runtime.js` so one shared card/action/calendar path remains active.
- Restored shows and movies to the left-rail browse layout, kept calendar full-width, and kept `watch_me` on its own page while aligning it to the shared shell, card, action, and focus contract.
- Added `web/js/chrometv_focus.js` as the single shared D-pad engine and reduced the main runtime focus path to a wrapper over that module instead of a second spatial-navigation implementation.
- Normalized the action bar and calendar CSS contract by deleting contradictory legacy selectors that hid ratings or dimmed out-of-month cells under the new grid.
- Implementation commit: `aa70abc`

## 2026-03-21 — Availability status end-to-end
- Added a normalized availability layer driven by `data/watch_source_availability.json`, resolved into additive fields on `data/data.json`.
- Implemented shared availability validation/enrichment helpers under `scripts/availability_status_lib.py`, with dedicated validator, enricher, and QA scripts.
- Chained availability validation/enrichment into the actual TMDB→OMDB→Trakt runner in `scripts/run_pipeline_tmdb_trakt.py`.
- Extended the shared UI runtime so cards, calendar rows, watch_me cards, show seasons, and show/movie popups all render one shared availability badge/detail pattern from enriched `data.json`.
- Updated the availability docs set to match the live repo’s actual keys, workflow runner, validation mode, and QA artifacts.
- Implementation commit: `8d11c7b`

## 2026-03-21 — Availability status phase 2 hardening
- Hardened validation from structural-only to provider-aware validation in `scripts/availability_status_lib.py`, with optional cached network verification support that remains disabled by default.
- Added deterministic phase-2 QA and production-state validators for override precedence, runtime asset coverage, runtime catalog integrity, and browser-level badge placement.
- Moved shared availability badges onto the upper-right image surface for cards and popup visual surfaces instead of relying on copy-only placement.
- Updated the local TMDB→OMDB→Trakt runner to fetch missing TMDB assets before runtime asset validation so rebuilt `*_local` refs no longer fail the final production-state pass.
- Implementation commit: `680bef3`

## 2026-03-21 — Availability metadata hardening and secret drift cleanup
- Added `scripts/validate_secret_name_drift.py` plus runtime warnings in the Trakt helper scripts so `API_TRAKT_REDIRECT_URL` is the only canonical redirect secret name and deprecated typo usage is explicitly surfaced.
- Added `scripts/self_heal_asset_metadata.py` to classify unrecoverable upstream metadata gaps and deterministically repair recoverable `*_path` / `*_local` drift before final validation.
- Updated the local runner to execute secret drift validation and asset metadata self-heal before availability validation/enrichment, keeping the final runtime asset validator at the end of the chain.
- Implementation commit: `f036936`

## 2026-03-22 — Popup, calendar, and shared card cleanup
- Removed active popup drift in `web/js/app_runtime.js` by retiring duplicated legacy popup/dashboard definitions and restoring one active show-popup path.
- Rebuilt the active show popup around a dense series hero, plain fact rows, dedicated provider section, horizontal season rail, and horizontal episode rail.
- Re-aligned dashboard, calendar, watch_me, and popup episodes to one shared episode-card content order with the double-heart favourite icon restored.
- Corrected CSS contract drift that was collapsing the calendar grid, wrapping the action strip, forcing shows/movies off the left rail, and turning dashboard recommendation posters into widescreen cards.
- Added `docs/VIEW_NAVIGATION_TREE.md` as the review map for pages, views, modal layers, and shared card families.
- Implementation commit: `4a5aed2`

## 2026-03-22 — Discover/sidebar/calendar follow-up cleanup
- Removed the remaining Discover intro/counter/featured-copy drift so the active view is just a two-column browse surface with shows on the left and movies on the right.
- Re-asserted the left-rail sizing contract for shows, movies, and watch_me so sidebar controls cannot overflow into the main content area at TV-like widths.
- Replaced the lingering dashboard episode show-card fallback with the shared episode-card renderer and re-asserted the shared action-strip contract across dashboard, calendar, watch_me, and popup rails so icon rows stay on one line with the shared left/center/right spacing model.
- Tightened calendar cell presentation with stronger day outlines and corrected sticky day-head positioning relative to the calendar toolbar/weekday row.

## 2026-04-03 — Calendar/popup/push flow follow-up
- Reworked the shared calendar toolbar into explicit left and right control groups, restored a sticky week-band above the month grid, and removed redundant per-card episode dates so the grouped date structure stays readable on smaller screens.
- Changed dashboard schedule windows so `Last Week` leads with today and moves backward while `Upcoming Schedule` starts tomorrow and runs forward through the next week.
- Rebuilt the active show/movie popup surfaces to use the backdrop as the popup background, moved title/action content into a dense header, embedded a two-column watch source panel, prioritized Canada in provider summaries, and removed the retired bottom-backdrop treatment.
- Hardened the inputs editor git push path to fetch and rebase against the selected remote branch before pushing so non-fast-forward GitHub updates can be integrated from the editor workflow.
- Implementation commit: `18f3c57`

## 2026-04-03 — Runtime QA drift cleanup
- Removed the stale duplicate `legacyRenderDashboard()` implementation so the active dashboard order and card/date behavior cannot silently diverge from the shared runtime path.
- Pointed shared runtime save/health probes at the local inputs editor server on `127.0.0.1:8787` instead of the static-site origin so dashboard/watch-state writeback and editor availability checks no longer emit false 404s under the canonical local server workflow.
- Updated the canonical shell pages and the inputs editor shell to declare an explicit favicon and aligned the smoke-test page list to the real dashboard/calendar/shows/movies/config/watch-me shells used by the app.
- Implementation commit: `9f1cdc4`

## 2026-04-03 — Final retirement cleanup
- Repointed shared watch-me navigation and action links to the canonical `web/watch_me/watch_me.html` shell instead of the legacy `web/watch.me.html` page path.
- Retired `web/watch.me.html` into a redirect-only shell that preserves incoming `?tv=` / `?m=` query parameters and forwards them to the canonical watch-me page.
- Simplified remaining editor quick links so config and retired editor surfaces no longer show duplicated in-app route buttons.

## 2026-04-03 — Dead runtime path cleanup
- Deleted the remaining unused legacy movie-popup and show-popup builder functions from `web/js/app_runtime.js` so only the active popup implementation remains in the shared runtime.
- Updated the project status note to reflect that the prior `/favicon.ico` and `/api/health` shell noise has been resolved in the current hardened local-server flow.
- Revalidated the canonical dashboard, calendar, inputs editor, and retired watch redirect paths with headless Chrome after the cleanup pass.
- Archived spec working notes under `docs/spec/archive/working_notes/` and kept the normalized `Section N - ...` files as the active spec body.
- Implementation commit: `9dd68c1`

## 2026-03-22 — Calendar/header/dashboard episode-card normalization
- Removed the separate sticky weekday row from the calendar grid and made the in-cell day head the single active weekday/date header for each day cell.
- Restyled the calendar day-head surface so non-today cells use an accent-tinted header band and today uses the active-view accent color directly.
- Retired dashboard `Up Next` so dashboard episode browsing now flows through `Upcoming Schedule` and the paged `Last Week` history strip.
- Added week-step and jump-step controls to dashboard `Last Week`, preserving D-pad-friendly backward/forward navigation through prior week segments.
- Set the shared poster-width token back to one config-driven source across dashboard recommendations, discover, shows, and movies instead of changing dashboard recommendations independently.
- Documented the current episode-card baseline as calendar visual layout plus dashboard last-week action-row spacing.
- Implementation commit: `115837e`

## 2026-03-23 — TV focus and shared card hardening
- Removed the duplicate arrow-key interception from `web/js/app_runtime.js` so the global TV focus path stays owned by `web/js/chrometv_focus.js`.
- Tightened active-layer detection for provider modal, popup modal, and visible panel focus routing.
- Reduced overlay/action-row clipping pressure in the shared card CSS so long dashboard/show/movie titles and rating text do not truncate as aggressively.
- Updated movie browse cards to expose full release date plus runtime instead of year-only metadata.
- Removed the redundant show-popup provider block so the popup now flows hero facts -> season band -> episode rail.
- Added a focused UI audit report at `reports/ui_component_audit/2026-03-23_dpad_and_card_gap_audit.md`.
- Implementation commit: `cd17cf8`

## 2026-03-29 — Restored production data-build workflow
- Restored a real GitHub Actions production rebuild workflow in `.github/workflows/build-data.yml` so pushes affecting `data/inputs.json`, pipeline scripts, or `web/config.json` can regenerate `data/data.json` and changed `assets/**` automatically instead of only validating tracked state.
- Re-aligned `scripts/run_pipeline_tmdb_trakt.py` with the live end-to-end build path by restoring the explicit `fetch_tmdb_assets.py` step before final self-heal and runtime validation.
- Hardened `scripts/validate_secret_name_drift.py` to ignore local artifact trees like `.ai_downloads` and `.codex.files`, preventing false pipeline failures from local handoff bundles.
- Rebuilt the runtime dataset locally and confirmed `Happy's Place` moved from `data/inputs.json` into `data/data.json` with runtime availability and local poster metadata.
- Updated workflow docs to reflect the current live repo reality: the repo now has both `.github/workflows/build-data.yml` and `.github/workflows/validate.yml`, and it explicitly notes that `scripts/fetch_trakt_primary.py` exists while the active production runner remains the TMDB-first chain.
- Implementation commit: `be0efbd`

## 2026-04-03 — Inputs editor local launch clarification
- Rebased the shared app shells so the `Inputs Editor` nav route stays in-app first instead of hard-jumping every page to `http://127.0.0.1:8787`, preventing dead localhost navigation when the editor server is not running.
- Simplified the shared inputs-editor panel to one local-editor launch action and replaced the refused-connection iframe state with an explicit local-only startup message tied to live `127.0.0.1:8787` health detection.
- Redirected the retired `web/library_editor.html` surface back to the in-app inputs-editor route while keeping `web/inputs_editor.html` as the canonical editor served by the dedicated local server.
- Implementation commit: `3d0cb6c`

## 2026-04-03 — Inputs editor duplicate, season, and GitHub sync restoration
- Restored live duplicate-state signaling in the canonical `web/inputs_editor.html` TMDB and queue surfaces so existing movies and shows are visibly marked before add/update actions.
- Replaced silent show overwrite behavior with a season-aware editor flow backed by TMDB show-detail lookup, allowing existing shows to add, replace, or remove selected seasons while preserving the single canonical `data/inputs.json` entry.
- Added a dedicated editor-side GitHub sync path so the local inputs editor can save `data/inputs.json` and push that file through the `github` remote without depending on the unavailable `origin` server on `theboys-hp290:3000`.
- Implementation commit: `da8deea`

## 2026-04-04 — Canonical pipeline and TV-first watch-source hardening
- Removed residual active-production drift around legacy txt and `inputs_parsed.json` assumptions by enforcing `data/inputs.json` as the canonical build input and `data/data.json` as the canonical generated runtime output across the TMDB builder, availability library, pipeline integrity QA, and GitHub pipeline QA.
- Expanded the generated streaming-source contract from the researched provider artifacts so runtime entities now carry normalized `watch_sources[]` blocks for movie, show, season, and episode contexts, with canonical fallback ordering and stricter schema validation shared by local and GitHub-facing QA.
- Hardened the TV-first dashboard and calendar surfaces so the seven-day week grid stays visible without horizontal overflow, sticky day/date presentation no longer collides with card content, and the runtime watch-source chooser consumes the expanded provider data consistently.
- Refreshed generated runtime artifacts and newly discovered canonical assets, and preserved the passing pipeline integrity artifact under `reports/_qa_pipeline_integrity_2026-04-05_00-10-21.json`.
- Implementation commit: `fe58ce0`

## 2026-04-05 — Split runtime activation and HP static deployment
- Replaced active first-load runtime dependence on `data/data.json` by moving shared list/dashboard/watch-me loaders to `data/catalog_index.json`, moving date-oriented rendering to `data/calendar.json`, and lazy-loading popup/detail views from `data/catalog_detail/<tmdb_id>.json`.
- Added a dedicated split-runtime builder plus matching validation so the final active runtime contract now uses one normalized `watch.embed[]` and `watch.providers.{CA,US,GB,AU}[]` model without leaking `watch_sources`, `source_options`, or `watch_providers` into split artifacts.
- Retired the old standalone `web/tv_shows_listing.html` utility as a redirect shell to avoid leaving an active page bound to the old monolithic runtime shape.
- Fixed popup drift in the shared runtime by restoring a defined popup D-pad handler and stopping provider-logo 404 churn by honoring only verified local logo assets in split detail output.
- Added the HP deployment unit `deploy/my-tv-movie-static.service`, synced the built static payload into `/srv/my_tv_movie/app`, and enabled the host-side service-managed static app on port `8011`.
- Implementation commit: `db11f0e`

## 2026-04-10 — Responsive card, popup, and asset hardening
- Reworked the shared card CSS baseline so action icons render without mismatched square button fills, image surfaces fit their available card areas, and dashboard/calendar cards avoid page-level horizontal overflow.
- Updated dashboard and calendar layout rules so TV/desktop widths preserve readable seven-column presentation while tablet/mobile use responsive date/day frames instead of squeezing seven unusable columns onto the screen.
- Removed direct watch-source panels from show and season contexts in the shared runtime; movie and episode watch panels remain the direct streaming-source surfaces.
- Fixed the show popup episode carousel by rendering readable episode body content and enforcing usable carousel card widths across desktop, tablet, and phone viewports.
- Changed TMDB asset fetching to request configured right-sized image buckets instead of `original`, then regenerated split runtime artifacts and newly referenced canonical assets from `data/inputs.json`.
- Added browser QA coverage for popup/source invariants and responsive dashboard/calendar layout across Android phone, Android tablet, and 1080p TV viewports.
- Implementation commit: `e9ba70c2`

## 2026-04-11 — Reusable watch-party page module
- Added `web/js/watch_party.js` and `web/css/watch_party.css` as a reusable static-site watch-party module for single-title pages that do not alter the canonical catalog runtime.
- Wired `web/heated-rivalry.html` to the module with episode selection, shareable room links, Google Drive episode handoff, a shared playback timer, and embedded Jitsi voice/video room support.
- Corrected Heated Rivalry episode still references to existing canonical assets so the page no longer emits missing-image requests during browser validation.
- Updated `docs/ARCHITECTURE.md` with the reusable page-module contract and guardrails against creating a parallel catalog/editor/watch-state system.
- Implementation commit: `d4fabbf2`

## 2026-04-11 — Heated Rivalry in-page help overlays
- Replaced the static top-right report-problem link in `web/heated-rivalry.html` with an in-page Help dropdown.
- Added modal overlay content for Report a Problem, Watch Party Info, and How to Watch Together so support/help flows stay on the current page instead of opening a new tab or replacing the show page.
- Embedded the existing Google Form inside the Report a Problem overlay and kept the watch-party guidance as local in-page HTML content.
- Implementation commit: `7d088003`

## 2026-04-11 — Watch-party host/join workflow correction
- Simplified the reusable watch-party module around the tested device workflow: Host Watch Party, Join Watch Party, Open Episode, Copy Invite, and shared timer controls.
- Removed the misleading embedded Jitsi call path from the primary experience because public Jitsi rooms can require a signed-in moderator before guests can join.
- Updated the Heated Rivalry help overlay copy to explain the host/moderator step and the Google Drive playback limitation.
- Updated `docs/ARCHITECTURE.md` so the module is documented as external voice/video room handoff rather than embedded conferencing.
- Implementation commit: `bae45b9d`

## 2026-04-11 — Local watch-party player prototype
- Added `tools/watch_party_player_server.js` as a local-only server that serves the repo, lists local videos from `.videos_local/` or `videos_local/`, streams selected media with byte-range support, and coordinates watch-party rooms over WebSocket.
- Added `web/js/watch_party_player.js` and `web/css/watch_party_player.css` as the reusable controlled-player watch-party client intended to stabilize on Heated Rivalry before later index/dashboard integration.
- Rewired `web/heated-rivalry.html` to use the local HTML5 player prototype instead of the Jitsi handoff module for the active watch-party panel.
- Added `npm run watch-party` as the local launch command.
- Implementation commit: `c696a061`

## 2026-04-11 — Watch-party page-owned episode sources
- Replaced the local-video picker in `web/js/watch_party_player.js` with a page-owned source contract so show pages pass the selected episode/watch URL into the reusable watch-party player.
- Updated `web/heated-rivalry.html` to publish each Heated Rivalry episode as a Google Drive watch source and to switch the watch-party panel from the episode card selection.
- Updated the WebSocket room state to sync `sourceId` plus timer/playback state, preserving the future controlled-player path while treating Google Drive as external playback.
- Implementation commit: `1ea7ccba`

## 2026-04-11 — Watch-party episode selection clarity
- Added an explicit Season / episode selector inside the reusable watch-party player while keeping episode-card Watch Party buttons wired to the same selected source.
- Removed the low-value status badge from the watch-party header so the setup state is communicated by the active step and enabled buttons instead.
- Replaced the generic disconnect copy with server-specific guidance that explains the local WebSocket server requirement and the GitHub Pages limitation.
- Implementation commit: `e11345d1`

## 2026-04-11 — Watch-party room-server preflight
- Added `/api/watch-party/health` to the local watch-party server so the client can verify that room sync is available before enabling Start Watch Party or Join Watch Party.
- Updated the reusable watch-party player to disable room actions when the WebSocket server is unavailable, making static GitHub Pages mode read as offline instead of failing after a click.
- Implementation commit: `27791050`

## 2026-04-11 — Watch-party user-flow alignment
- Updated the reusable watch-party player so Open Episode works independently of room sync, matching the Google Drive playback workflow.
- Restored a user-facing Copy Invite action that carries selected room and episode source through `partyRoom` and `partySource` query parameters.
- Corrected Heated Rivalry help overlay copy to remove the retired Jitsi/moderator workflow and explain the room-server requirement in the active product language.
- Implementation commit: `40e9b8d7`

## 2026-04-11 — Hosted watch-party service container
- Added `deploy/watch-party/` with a Dockerized watch-party room server and Cloudflare quick tunnel service for public HTTPS/WSS proof-of-concept access from GitHub Pages.
- Updated `tools/watch_party_player_server.js` with CORS and WebSocket origin controls for hosted room-sync use.
- Updated `web/js/watch_party_player.js` and `web/heated-rivalry.html` so the GitHub Pages page can connect to an external hosted watch-party server through `serverUrl`.
- Deployed the stack on the Minisforum under `/srv/my_tv_movie/watch-party` and validated public WSS room state sync through the active Cloudflare tunnel.
- Implementation commits: `929dddf6`, `e303b580`

## 2026-04-22 — Watch-me shell normalization and calendar list mode
- Moved the canonical Watch Me shell to `web/watch_me.html`, converted `web/watch_me/watch_me.html` into a redirect-only compatibility path, and kept `web/watch.me.html` as the legacy redirect shell.
- Folded Watch Me into the shared `web/js/app_runtime.js` page family, deleting the separate `web/js/watch_me_runtime.js` path so dashboard, watch-me, calendar, shows, and movies share one runtime entry.
- Added a month list/tree calendar mode and repointed retired `web/tv_shows_listing.html` traffic to that canonical list view instead of the shows library.
- Added visible hide/show toggles for browse-style filter rails, tightened shows/movies grid density, and fixed the version badge/footer to read canonical config metadata instead of a hard-coded runtime string.
- Implementation commit: `ab465134`

## 2026-04-28 — UI contract, drift cleanup, and runtime validation
- Re-centered icon/action ownership on `web/js/action_bar.js` and local-first watch-state ownership on `web/js/watch_state_manager.js`.
- Kept runtime compatibility shims loaded from `web/js/chrometv_focus.js` while removing direct duplicate page-shell script loads.
- Made the non-blocking watch-source popup path canonical through `web/js/trailer_watch_popup_fix.js`, with the older app-runtime popup handler reduced to fallback-only.
- Removed tracked overlay folders, patch apply docs, old apply scripts, overlay validation, and abandoned overlay reports from active repo paths.
- Added `scripts/validate_runtime.ps1` as the single runtime validation entry point and documented canonical owners, compatibility shims, and the validation command.
- Added deterministic asset pipeline tooling/reporting via `scripts/optimize_runtime_assets.py` and `reports/ui_stabilization/asset_optimization.json`.
- Implementation commit: `d1f2746c`

## 2026-04-28 — Documentation consolidation, UI contract QA, and validation hardening
- Added `docs/DOCUMENTATION_STANDARD.md` with current source-of-truth rules, historical-only doc paths, changelog/report handling, and the canonical owner matrix.
- Aligned active architecture and component docs to the current action contract: popcorn, watch, ticket, double-heart, and compact numeric rating.
- Scoped local watch state keys by item context so watched status, watch list, and favourite toggles do not affect unrelated cards.
- Tightened action button sizing, reduced nested frame treatment, lowered recommendation/card density, and kept mobile/tablet calendar layouts denser without horizontal overflow.
- Expanded `scripts/validate_runtime.ps1` to check doc consistency, icon ownership, duplicate handler drift, required reports, forbidden markers, and runtime asset-size reporting.
- Browser QA passed across the requested TV, laptop, tablet, and phone viewports.
- Implementation commit: `ec0248b8`

## 2026-04-28 — Local server launcher consolidation
- Made `tools/run_local_servers.bat` the canonical local launcher for both app pages and the local Inputs Editor API server.
- Converted root `run_server.bat` into a compatibility delegator so it no longer runs obsolete `app.py`, dependency bootstrap, or port `8811` logic.
- Updated the launcher to start/reuse `127.0.0.1:8000` for static app pages and `127.0.0.1:8787` for `tools/inputs_editor/inputs_editor_server.py`.
- Corrected launcher health checks so 404 responses no longer count as an available server.
- Updated in-app Inputs Editor guidance to point to `tools/run_local_servers.bat` instead of the editor-only launcher.
- Added launcher contract checks to `scripts/validate_runtime.ps1`.
- Implementation commit: `81c26ee4`

## 2026-04-28 — Root launcher ownership and root artifact cleanup
- Promoted root `run_local_servers.bat` to the canonical double-click launcher for both the static app server and the local Inputs Editor API server.
- Kept `run_server.bat`, `tools/run_local_servers.bat`, and `tools/start_inputs_editor.cmd` as compatibility delegators only; removed the separate editor-only PowerShell launcher.
- Fixed `run_schema.bat` so it runs from the repo root and supports `--no-pause` validation.
- Reworked `scripts/generate_schema.py` to use only the standard library, removing the undeclared `genson` dependency and interactive pause from automated runs.
- Removed tracked root archive zips: `docs.zip`, `docs (2).zip`, and `reports.zip`.
- Added validation checks for launcher ownership, schema helper syntax, removed root archive artifacts, and editor-only launcher drift.
- Implementation commit: `2f476cce`

## 2026-04-29 — Card system, watch-state, and asset runtime stabilization
- Unified shared card/action behavior so action rows sit below media, card availability badges are suppressed, compact percent ratings render through `web/js/action_bar.js`, and page shells use the compact logo header.
- Tightened local-first watch-state identity so episode, movie, and show actions receive context-specific keys and visible buttons refresh after dynamic dashboard/calendar renders.
- Updated dashboard/calendar overflow to the shared `+X more` expansion pattern and kept modal keyboard focus inside the active modal.
- Enforced runtime asset targets through `scripts/optimize_runtime_assets.py`: posters `171x257`, stills `256x180` after side crop, and backdrops no wider than `780px`.
- Expanded `scripts/validate_runtime.ps1` and reports to cover the current UI contract, asset report, local launcher, and rendered watch-state key audit.
- Implementation commit: `35943062`
