# Architecture Log

## 2026-07-24

- Repaired Shows/Movies browse parity by removing the duplicate mobile-only Current implementation and routing Current through the canonical `state.filters.*.scope`, `setSegActive`, `renderShows`, and `renderMovies` path.
- Tightened the Current definition to configurable six-month defaults in `web/config.json -> browse.current`: shows require episode/activity within 183 days, movies require release within 183 days, and available future movies keep the 30-day lookahead.
- Restored phone Search by removing the coarse-pointer rule that hid primary browse controls, and compacted genre controls through the canonical `web/css/main_app.css` responsive grid.
- Advanced the app release version to `v1.5.3`, added deterministic version query parameters to active app shell CSS/JS references and `app_runtime.js` module imports, and documented the cache/release standard.
- Added regression documentation and focused browser QA evidence under `reports/ui_stabilization/`; updated validation to block retired mobile browse scripts/styles and unversioned active app shell assets.
- Validation: `node --check web/js/app_runtime.js` passed; `scripts/validate_runtime.ps1` passed; `node scripts/qa_browse_filter_parity.mjs` passed with `failures=[]`; `node scripts/qa_browser_layout_check.mjs` passed with `failures=[]`; `git diff --stat` confirmed a focused UI/docs/QA change with no generated catalogue or asset churn.
- Commit: direct-to-main UI parity repair commit; final SHA is recorded in Git history and the completion report.

## 2026-07-11

- Added VSEmbed as a default-visible Streaming popup provider through the existing `web/config.json -> streaming.embed_providers[]` registry, with TV episode template `https://vsembed.ru/embed/tv/{tmdb_id}/{season}/{episode}` and movie template `https://vsembed.ru/embed/movie/{tmdb_id}`.
- Updated the streaming provider contract, archived the previous master contract snapshot, and advanced streaming/browser/runtime validators so the ten-provider default list and TV/movie template split stay guarded.
- Validation: `python scripts/validate_streaming_config.py` passed; `python scripts/validate_streaming_episode_cards.py` passed with movie template coverage; `scripts/validate_runtime.ps1` passed; `scripts/qa_browser_layout_check.mjs` passed with `failures=[]`; `git diff --check` passed.
- Commit: `7ff5d3b42a` add vsembed streaming provider.

## 2026-07-03

- Simplified the app-shell Inputs Editor page back to a launcher/help surface only: it no longer embeds the editor iframe, shows the copyable `run_local_servers.bat` command, and opens the canonical local editor in its own tab.
- Converted `web/inputs_editor.html` from three always-visible columns into a three-step tabbed workflow: `Search`, `Saved Picks`, and `My List & Publish`; tab controls bind immediately so navigation still works while health/data loading is pending or failed.
- Kept the existing canonical editor, local server, API endpoints, and publish flow; no replacement process, alternate editor, or new runtime path was introduced.
- Hardened validation so the tabbed editor workflow, launcher copy/open contract, and no-iframe app-shell contract are required by `scripts/validate_runtime.ps1`.
- Corrected Watch Source episode popup TMDB metadata fallback uncovered by rendered QA, so episode popups keep a labelled `TMDB:` proof even when runtime minutes are absent.
- Validation: `node --check web/js/app_runtime.js` passed; Python compile passed for `tools/inputs_editor/inputs_editor_server.py` and `scripts/qa_pipeline_integrity.py`; `scripts/validate_runtime.ps1` passed; focused browser check passed for editor tabs and launcher contract; `scripts/qa_browser_layout_check.mjs` passed with `failures=[]`; `git diff --check` passed.
- Commit: `616217f784` simplify inputs editor workflow.

## 2026-07-02

- Verified the 2026-07-02 Inputs Editor additions in canonical `data/inputs.json`: TV rows for `Law & Order: Trial by Jury`, `Law & Order: LA`, `Law & Order: Organized Crime`, `Silent Witness`, and `Bodyguard`; movie rows for `Backrooms`, `Tuner`, `The Death of Robin Hood`, `Stop! That! Train!`, and `Heartstopper Forever`.
- Rebuilt generated runtime artifacts from the canonical pipeline with `shows=241`, `movies=123`, and `errors=0`; `Bodyguard` TMDB show `80307` is present in `data/catalog_index.json`, `data/data.json`, and `data/catalog_detail/80307.json`.
- Hardened Inputs Editor publish visibility by adding `/api/publish-status`, local/generated dirty-state checks, a visible publish status badge, and clearer local-only versus online-finish button copy; validation now guards this contract.
- Corrected Calendar episode action attributes so shared watched/watchlist/favourite actions expose stable TMDB context and pass the cross-view action contract.
- Validation: full `scripts/run_pipeline_tmdb_trakt.py` passed; `scripts/qa_pipeline_integrity.py` passed; `scripts/validate_runtime.ps1` passed; `scripts/qa_browser_layout_check.mjs` passed with `failures=[]`; focused Shows browser search returned one `Bodyguard` card for TMDB `80307` with 3 actions; `git diff --check` passed.
- Commit: `d0b2bdda91` harden inputs publish status and calendar actions.

## 2026-06-27

- Root-caused the Inputs Editor 404 report to opening `web/inputs_editor.html` from the static `127.0.0.1:8000` server instead of the dedicated local editor API server on `127.0.0.1:8787`; the editor now stops after a failed `/api/health` response and shows the correct local editor URL instead of continuing into a misleading `/api/inputs` 404.
- Changed the canonical local launcher behavior so `run_local_servers.bat` starts/reuses both required servers but opens only the live Inputs Editor tab by default; the previous full app tab fan-out is preserved for QA through `tools/run_smoke_test.ps1 -AllTabs`.
- Hardened the Inputs Editor online publish path so unresolved Git conflicts are detected before committing/rebasing/pushing, and the UI reports the conflicted paths instead of implying a local save completed the online app update.
- Added `docs/INPUTS_EDITOR_OPERATIONAL_HISTORY.md` to record the Inputs Editor failure history, root causes, fixes, and validation hooks for future maintenance.
- Verified `Canada's Drag Race: All Stars` TMDB show `314487` is present locally in canonical `data/inputs.json` with `season_spec: "*"`, and in generated runtime data after the full pipeline rebuild.
- Validation: full `scripts/run_pipeline_tmdb_trakt.py` passed after rebase with `shows=236`, `movies=118`, `errors=0`, `rebuilt_shows=1`; standalone `scripts/qa_pipeline_integrity.py` passed; `scripts/validate_runtime.ps1` passed; Python compile passed for the edited server and QA scripts; local HTTP checks passed for `/api/health`, `/api/inputs`, `data/catalog_index.json`, and `data/catalog_detail/314487.json`; `scripts/qa_browser_layout_check.mjs` passed with no failures and rendered `episode:314487:1:1`.
- Commit: `67ffba2d8d` fix inputs editor launch and publish recovery; `585eb0c9ae` rebuild runtime data for Drag Race All Stars.

## 2026-06-25

- Promoted the HP media VM path from a placeholder plan into an executable production deployment package under `deployment/vm_prod/`, including Ubuntu package installation, app-root sync to `/opt/mytv_movie`, PostgreSQL role/database setup, Python server venv, schema apply, JSON-to-PostgreSQL migration apply, systemd API service install, and Nginx static/API reverse proxy configuration.
- Deepened the server-mode JSON migration so `data/data.json` imports shows, seasons, episodes, and movies into the typed PostgreSQL tables instead of only the generic `media_items` table, while preserving JSON fallback and importing future watch-state queue/watchlist/favourite records where present.
- Corrected server-mode state write queue semantics so watchlist and favourites use schema-allowed operations (`watchlist_add`, `watchlist_remove`, `favourite_set`), added the `/favorites` alias, exposed joined state rows with media identity, and made `/api/v1/catalog/import-json` apply the real migration when PostgreSQL is configured.
- Extended the PostgreSQL sync queue operation contract to include provider refresh operations that the existing API already exposes.
- Validation: Python compile passed for changed API/PostgreSQL modules; `deployment/postgres/json_migration.py` dry-run found 12,597 catalog candidates; schema validation passed; schema dry-run passed; server-mode static validation passed; HP bootstrap and validation shell syntax checks passed; API smoke test passed for health, catalog JSON fallback, and migration dry-run; `scripts/validate_runtime.ps1` passed; `git diff --check` passed. Docker PostgreSQL live validation was not run because Docker Desktop's daemon was not available in this local environment; the HP validation script performs live schema/import/API proof on the VM.
- Commit: `6e7fb7b35f` implement-hp-vm-server-deployment-path.

## 2026-06-24

- Added incremental TMDB build caching for push-triggered data builds: unchanged active `data/inputs.json` rows with the same config/schema signature reuse the previous generated show/movie row instead of refetching the full TMDB season/episode tree.
- Added `--force-full-tmdb`/`--force-full-refresh` so scheduled and manual data builds still do complete TMDB refreshes, preventing long-lived stale show/episode metadata while keeping normal input-editor pushes fast.
- Added pipeline-integrity coverage requiring scheduled/manual builds to keep the full-refresh path wired when the incremental cache exists.
- Validation: Python compile passed for the changed pipeline scripts; `scripts/qa_pipeline_integrity.py` passed; `scripts/validate_runtime.ps1` passed; `git diff --check` passed.
- Commit: `7cb1cc082c` add-incremental-tmdb-build-cache.

- Added a root `index.html` redirect to the canonical `web/index.html` app shell so the deployed GitHub Pages site root no longer returns 404, and updated Pages staging to include that redirect artifact.
- Validation: root redirect content check passed; generated JSON parse checks passed; `git diff --check` passed.
- Commit: `7ad1f67fe8` add-pages-root-redirect.

- Reduced input-update workflow runtime by changing `build-data` from full-history/all-branch checkout to shallow single-ref checkout and suppressing checkout progress noise.
- Changed push-triggered data builds to resolve only missing Trakt IDs while scheduled/manual builds still use `--refresh-existing-trakt` for the deeper full recheck path.
- Kept generated runtime JSON validation on every build, while moving the expensive direct active-row TMDB identity diagnostics to scheduled/manual builds where they do not slow normal inputs-editor saves.
- Reduced Pages deployment upload scope by staging only static runtime/site directories and generated JSON assets under `_site` instead of uploading the whole repository.
- Validation: Python compile passed for the changed runners; `scripts/qa_pipeline_integrity.py` passed; `scripts/validate_runtime.ps1` passed; `git diff --check` passed. `scripts/qa_browser_layout_check.mjs` could not run because `puppeteer-core` is not installed in the checkout.
- Commit: `65f9abb74f` optimize-data-workflow-runtime.

## 2026-06-17

- Hardened the inputs-editor publish completion logic so it waits for actual generated runtime artifact changes after an input commit before reporting success, then fast-forwards and validates local reconciliation.
- Added pipeline integrity freshness validation requiring generated runtime data to be newer than saved canonical inputs, and added early `build-data` workflow validation before artifact commits.
- Added `tools/install_local_launcher.ps1` and runtime validation coverage so `run_local_servers.bat` can be registered for command-line use from any PowerShell location.
- Regenerated the full runtime dataset from canonical `data/inputs.json`; Cape Fear TMDB show `277439` is present in `data/catalog_index.json`, `data/data.json`, and `data/catalog_detail/277439.json`.
- Validation: full local `scripts/run_pipeline_tmdb_trakt.py` passed; `scripts/qa_pipeline_integrity.py` passed; `scripts/validate_runtime.ps1` passed; HTTP-served `catalog_index.json` contains Cape Fear on `127.0.0.1:8000`.
- Commit: `9d61099562` fix inputs publish pipeline sync.

## 2026-06-03

- Completed the live PostgreSQL runtime path for the X1 lab foundation instead of leaving server mode at scaffold/static-validation status.
- Updated `deployment/vm_lab/bootstrap_ubuntu_mytv_lab.sh` to install PostgreSQL runtime dependencies, create the local `mytv_movie` OS service account, create the matching PostgreSQL login role/database, create `/opt/mytv_movie/.venv`, install tracked psycopg v3 requirements, document the local peer-auth DSN through `.env.example`, verify connectivity, and invoke live schema validation when the repo is present.
- Updated `deployment/vm_lab/validate_mytv_lab.sh` to fail unless the repo checkout, local DSN documentation, OS app user, PostgreSQL app role/database, psycopg runtime, and live schema/write/read/rollback validation are all available and passing.
- Added `deployment/postgres/live_validate_postgres.py`, which connects to the expected database/user, applies `schema_v1.sql`, verifies required tables, inserts and reads a temporary runtime-config row, rolls the transaction back, and confirms cleanup.
- Added `deployment/postgres/README.md`, tracked `deployment/vm_lab/.env.example`, tracked `deployment/api/requirements-server.txt`, and updated API/VM docs plus the systemd example to run as the peer-authenticated `mytv_movie` account.
- Added `.gitattributes` enforcement for LF shell scripts so required Ubuntu bootstrap/validation scripts remain parseable from Windows checkouts.
- Updated `docs/00_master_contract.html` to MC-2026-06-03.2: scaffold-only, dry-run-only, or static-DDL-only results are incomplete until live PostgreSQL validation passes.
- Validation: both required `bash -n` checks passed; Python compile passed; schema validation and schema dry-run passed; focused server-mode validation passed; full runtime validation passed; no `POSTGRES_PASSWORD` references remain in the live lab config path.
- Live database proof: temporary PostgreSQL 16.14 container validation passed with expected `mytv_movie` database/user, all required schema tables, test insert, test read, rollback, and confirmed rollback cleanup. The temporary container and validation virtual environment were removed afterward.
- Remaining external action: run the documented bootstrap and VM validation commands on the actual X1 Ubuntu lab VM to install and prove the peer-authenticated runtime in that VM.
- Commit: `46be55f186` complete-live-postgres-runtime-validation.

- Implemented the first runnable server-mode scaffold under Forest-owned deployment paths without editing Lime-owned VM scripts, `deployment/webserver/*`, or existing UI runtime.
- Added `deployment/api/server_mode_api.py`, a dependency-light standard-library HTTP API bound by default to `127.0.0.1:8000` with `/api/v1` routes for health, catalog, watch status, watchlist, favourites, sync queue/history, providers, Media Library inventory, runtime config, and audit log.
- Added API configuration and PostgreSQL boundary modules: `server_mode_config.py` reads `/opt/mytv_movie`/repo-root and API/DSN environment, while `postgres_client.py` uses optional `psycopg` and reports unavailable write paths instead of pretending writes succeeded.
- Added PostgreSQL tooling: `apply_schema.py` supports schema dry-run/apply through `MYTV_POSTGRES_DSN`, `validate_schema.py` verifies required v1 tables and destructive-command absence, and `json_migration.py` dry-runs/imports current JSON artifacts into PostgreSQL candidates while preserving JSON fallback.
- Added worker scaffolds: `deployment/trakt_sync/trakt_worker.py` plans local-first Trakt pull/push/reconcile work without loading secrets, and `deployment/media_library/media_library_worker.py` plans scan/QA/remux work with home `192.168.1.x`, trailer `192.168.2.x`, ffprobe/ffmpeg, and non-binary storage rules.
- Added `deployment/api/mytv-api.service.example` for the lab VM API service on `/opt/mytv_movie` and `127.0.0.1:8000`, leaving Nginx reverse-proxy/provisioning ownership with Lime Green.
- Updated `docs/00_master_contract.html` to MC-2026-06-03.1, archived the prior master contract, updated `deployment/api/api_contract_v1.md`, and advanced `scripts/validate_runtime.ps1` freshness checks.
- Validation: Python syntax compile passed; `deployment/api/validate_server_mode.py` passed; `deployment/postgres/validate_schema.py` passed; `deployment/postgres/apply_schema.py --dry-run` passed; `deployment/postgres/json_migration.py` dry-run found 12,707 candidates; Trakt and Media Library worker dry-runs passed; HTTP checks for `/api/v1/health` and `/api/v1/catalog` passed; `scripts/validate_runtime.ps1` passed.
- Remaining limitations: live PostgreSQL apply/write tests were not run because no local DSN/driver was configured; Trakt network sync remains a queue-planning scaffold until credential/token handling is implemented; Media Library apply/remux remains dry-run-safe until path roots and write policy are configured.
- Commit: `47630e2175` implement-server-mode-scaffold.

## 2026-06-02

- Re-reviewed CODEX-FOREST server-mode work after pulling the completed Lime Green VM/webserver foundation and the follow-on generated data artifact commit.
- Determined the generated data update did not change the v1 database/API/state model, because the migration plan already treats generated JSON as fallback/import/export evidence.
- Added the missing runtime alignment between Forest API/database design and Lime deployment foundation: app root `/opt/mytv_movie`, Nginx static/reverse proxy on `80/tcp` with `443/tcp` reserved, local API upstream `127.0.0.1:8000`, local PostgreSQL on `5432/tcp`, and static JSON fallback still served by Nginx when the API is stopped.
- Updated `deployment/api/api_contract_v1.md`, `deployment/postgres/json_to_postgres_migration_plan.md`, `docs/00_master_contract.html`, and `docs/mytv_vm_migration_control_plan.html` without editing Lime-owned VM scripts or `deployment/webserver/*`.
- Validation: `git diff --check` passed; `scripts/validate_runtime.ps1` passed.
- Commit: `f0d6c7abc4` align-forest-api-with-lab-vm-foundation.

- CODEX-FOREST designed the v1 server-backed application architecture for PostgreSQL primary writes, JSON import/export/static fallback, API routes, local-first watch-state logic, Trakt/commercial sync queue/history, provider registry, runtime config, audit logging, and WD TV Live/local-network Media Library inventory.
- Added PostgreSQL DDL in `deployment/postgres/schema_v1.sql` for `media_items`, `shows`, `seasons`, `episodes`, `movies`, `watch_state`, `watchlist`, `favourites`, `sync_queue`, `sync_history`, `media_files`, `provider_registry`, `runtime_config`, and `audit_log`; schema stores image/media paths and metadata by default, not binaries.
- Added JSON-to-PostgreSQL migration mapping for canonical `data/inputs.json`, generated runtime JSON, watch queue, provider/watch-source files, web config, Media Library JSON, and media-renamer QA/config outputs.
- Added `/api/v1` contract for health, catalog, watch status, watchlist, favourites, Trakt pull/push/reconcile, providers, Media Library inventory/scan/QA/remux, runtime config, sync history/queue, and audit log.
- Added watch-state logic contract requiring local-first writes, durable queue behavior, explicit conflict resolution, independent watchlist/favourites, local-only defaults for `partial` and favourites where no external mapping exists, and no silent loss of user actions.
- Added WD TV Live Media Library design for home `192.168.1.x`, trailer `192.168.2.x`, local device/path discovery, expected vs actual filename handling, ffprobe QA, safe stream-copy remux, VLC and X-plore playback buckets, and non-binary database storage.
- Updated `docs/00_master_contract.html` to MC-2026-06-02.1, archived the prior master contract, updated `docs/mytv_vm_migration_control_plan.html` with WP2 design outputs, and advanced `scripts/validate_runtime.ps1` freshness checks for the new contract lineage.
- Validation: `git diff --check` passed; `scripts/validate_runtime.ps1` passed; static schema checks found no `DROP` or `TRUNCATE` commands; `psql` was unavailable locally, so live PostgreSQL parser validation was not run.
- Remaining risks: browser-local state can be fragmented across devices before import; Trakt does not directly map every local state field; WD TV Live/local share discovery depends on SMB/firewall/device availability; static UI API-client bridge remains a later implementation step.
- Commit: `2744b611d9` design-server-backed-app-architecture.

## 2026-05-27

- Closed the remaining active-input identity gap by making the direct TMDB audit fail on active unresolved IDs and title mismatches instead of relying on the previously generated catalog as evidence.
- Added the direct active-row TMDB identity audit to `build-data` diagnostics so stale generated data cannot mask a TMDB ID that now 404s or resolves to the wrong media title/type.
- Marked `Spider-Noir - MGM+ Premiere` inactive because TMDB movie id `1703288` now returns 404, regenerated runtime artifacts with `shows=228`, `movies=116`, and `errors=0`, and removed its stale detail split output.
- Commit: `2cc21f2e62` fix-active-TMDB-identity-validation.

- Root-caused wrong-ID catalog rows to trusted legacy/imported TMDB ID pairs plus editor saves that validated shape but not TMDB identity; active saves now reject title/TMDB ID mismatches before writing `data/inputs.json`.
- Extended pipeline integrity QA to fail on generated title/input title mismatches, unexpected catalog rows, runtime `data.errors`, and missing editor identity validation.
- Corrected bad active input IDs, removed the bogus `东方神娃`/`Presumed Innocent` row and the failing `Becoming Our Spider-Man` movie row, regenerated runtime artifacts with `shows=228`, `movies=117`, and `errors=0`.
- Made runtime asset optimization idempotent for already-sized images and changed `build-data` artifact commits to include generated JSON/detail data plus new asset files without committing mass rewrites of already tracked assets.
- Commit: `a9b17ed284` fix inputs identity validation and pipeline artifacts.

## 2026-05-29

- Hardened the inputs editor GitHub publish path into a complete save, push, generated-artifact wait, local fast-forward, and pipeline-integrity validation flow so adding shows/movies does not leave the local checkout behind or full of stale generated artifacts.
- Added validation guards so the publish/sync endpoint and UI button are required by runtime and pipeline integrity checks.
- Commit: `171dc458ba` harden inputs editor publish sync.

## 2026-05-25

- Hardened the canonical inputs scope flow so `scripts/fetch_tmdb.py` excludes `in_scope: false` rows before building runtime data, the inputs editor server normalizes/dedupes validated media rows with bounded JSON/error handling, and the editor UI exposes a save plus runtime refresh path.
- Extended pipeline/runtime validation to fail when inactive inputs remain in `catalog_index.json`; regenerated runtime data removed out-of-scope TMDB show `72590`.
- Commit: `df57ec829a` harden-inputs-scope-pipeline.
- Commit: `f9c1a7e708` update-runtime-data-for-input-scope.

- Removed tracked transitional clutter: overlay handoff bundles, Codex prompt handoff files, generated report artifacts, tracked local/build outputs, duplicate script reference docs, misspelled archived tools, and the obsolete palette swatch backup.
- Added repo-hygiene ignore coverage plus runtime validation guards so overlay/codex handoff folders and obsolete duplicate docs do not return as active tracked artifacts.
- Commit: `c03a69b2d1` cleanup repo transitional artifacts.

- Changed `build-data` workflow concurrency to cancel older in-progress data builds on `main`, so newer input/config pushes cannot leave stale data generation running behind the current commit.
- Commit: `30e459d91d` cancel-stale-data-builds.

- Hardened the inputs-editor update path so local runtime refresh uses the canonical `scripts/run_pipeline_tmdb_trakt.py` pipeline instead of the narrower asset refresh path.
- Prevented GitHub Pages from deploying raw `data/inputs.json` pushes before generated runtime artifacts exist by limiting push-triggered Pages deploys to web, asset, generated data, and docs paths; `build-data` remains responsible for dispatching Pages after generated artifacts are committed.
- Made `build-data` fail when `scripts/qa_pipeline_integrity.py` finds unreconciled active inputs, so “saved in inputs but missing from runtime catalog” is a hard pipeline failure.
- Commit: `8b3a9e0276` harden-input-update-pipeline.

## 2026-05-20

- Rebased Streaming popup provider buttons on `web/config.json -> streaming.embed_providers[]`, with `ok`/`warn` default-visible, `candidate` hidden unless explicitly enabled, and `blocked` suppressed.
- Added requested candidate/blocked provider registry entries without making them default-active.
- Consolidated Calendar, Dashboard Current/Recent, and show-detail episode cards through `buildSharedEpisodeCard` plus `renderEpisodeCardHtml`, with standard/compact density markers and shared still/backdrop/poster image fallback.
- Added streaming/card anti-drift validation and documentation in `docs/streaming_provider_registry.html` and `docs/episode_card_baseline.html`.
- Commit: `258c2ab112` Fix streaming providers and unify episode card rendering.

- Made the Media Library link a static primary-nav item in active app page shells, with the existing normalizer limited to correcting/moving the shell link into `.top > .nav[role="tablist"][aria-label="Primary"]`.
- Removed stale Watch Source fallback title text from active modal shells and normalized show popup provider wording to `Providers`.
- Archived retired runtime compatibility shims out of `web/js/`, removed retired provider/watch-option CSS selectors from active CSS, and restored required subordinate architecture/UI docs as pointers to the master contract.
- Hardened runtime and browser validation for static Media Library nav placement, rendered occlusion/new-tab proof, stale popup fallback titles, retired shim files in active runtime folders, and legacy provider/watch-option CSS reintroduction.
- Commit: `f591877365` fix-nav-legacy-drift-validation.

## 2026-05-19

- Corrected Watch Source Providers rendering so country rows use compact same-row provider logo/text hyperlink anchors, provider URLs stay in `href` only, and provider anchors do not render as buttons/cards.
- Corrected generated filename copy rendering so the visible primary copy control is the full generated filename string and the copied value stays identical to the displayed value.
- Added MC-2026-05-19.1 contract lineage and validation coverage for provider strip and filename-copy drift.
- Commit: `88ebac9aa3` fix-watch-source-provider-copy-rendering.
- Commit: `924940dfd3` normalize-watch-source-provider-labels.
- Commit: `039cb5ed24` cap-watch-source-provider-strip.

## 2026-05-18

- Implemented runtime recovery for Watch Source popup schema, plain Streaming/Providers rows, generated filename copy, popup reference label, shared episode card rendering, Media Library primary-nav placement, Full/Light runtime mode, and media QA pipeline enforcement.
- Hardened runtime, browser, and media-renamer validation for popup title/labels/rows, provider admin-text suppression, generated filename controls, sticky Exit, episode TMDB metadata, shared dashboard/calendar card markup, Media Library nav placement, Light mode image suppression, ffprobe/ffmpeg stream-copy QA, and contract lineage sections.
- Updated `docs/00_master_contract.html` additively and archived the prior contract snapshot under `docs/_archive/contracts/`.
- Commit: `560c14857` recover-watch-source-runtime-contracts.

## 2026-05-09

- Refactored the media renamer into a PySide6 one-screen home-user utility with folder choice, scan, batch safe fix, problem files, and reports sections.
- Normalized media renamer output rules to final `TV` and `Movies` folders only, with old third-folder content scanned for cleanup but never created as an output library.
- Rebuilt the media renamer scan/execution engine around catalog-only matching, 85% safe automation, quarantine, duplicate handling, sidecar movement, placeholder folder cleanup, and fixed report filenames.
- Updated HTML documentation, validator coverage, self-test launcher, compact media reference generation, and overlay package delivery.
- Commit: `27e14c2a4` refactor media renamer home utility.

## 2026-05-07

- Implemented MC-2026-05-07.1 interaction compliance for calendar containment, episode carousel shell structure, canonical watch-state action ownership, provider health filtering, and rendered QA proof.
- Added `data/provider_registry.json` as the runtime provider health registry and filtered blocked/archived providers from watch-source popup rendering.
- Corrected show action release-state handling so provider unavailability does not mark show actions as unreleased, while movie/episode release locks remain enforced through explicit release status.
- Extended browser QA and runtime validation to prove equal calendar columns, no cross-cell card overflow, true episode carousel movement/context, cross-view action queue consistency, blocked provider exclusion, and provider registry classification.
- Commit: `1681e8245` fix calendar carousel actions provider compliance.

## 2026-05-06

- Replaced independent sticky offsets for the app header, section headers, and calendar weekday header with one runtime-fed CSS variable model.
- Reworked calendar month rendering into paired `.calendar-week-header` and `.calendar-week-body` grids so weekday/date cells and day columns share the same column, gap, padding, and border model without overlaying the first row.
- Extended rendered validation to prove sticky app header persistence, section/calendar non-overlap, exact header/body column bounds, weekend styling in both header/body, duplicate-date prevention, and contained mobile calendar row scroll.
- Commit: `34bad4c2` fix sticky header calendar alignment.

- Implemented MC-2026-05-05.2 interaction compliance with canonical local watch-state resolution feeding card action render state across Dashboard, Shows, Movies, Discover, and popups.
- Updated Manage Watch State from a fixed first-page matrix into a searchable, sortable, pageable matrix with inline edits, row state keys, and persistent first/prev/next/last controls.
- Extended rendered browser QA to prove action icon changes, local state writes, queue writes, Manage Watch State row reflection, cross-view state consistency, and episode carousel controls with retained show/season context on Android TV and laptop viewports.
- Commit: `02d0f83d` implement interaction compliance validation.

## 2026-05-05

- Removed the live render compatibility shims from the focus bootstrap so the shared runtime owns card image normalization and watch-source popup handling directly.
- Removed duplicate Shows/Movies action-menu binding after render so card action handlers do not accumulate.
- Wired runtime asset optimization into the generated-data pipeline and extended it to resize runtime-only fetched assets that have no original-download source file, reducing oversized decode work before validation.
- Updated runtime validation to forbid reintroducing the removed render/popup shims and to enforce zero oversized runtime assets.
- Commit: `5718497f` remove legacy render shims and optimize runtime assets.

## 2026-05-04

- Updated GitHub workflow actions to Node-24-native major versions for checkout, setup-python, and setup-node to remove the Node 20 deprecation warning.
- Commit: `adf6cc48` update github actions to node24-native versions.

- Updated the build-data diagnostics artifact upload action from Node 20-era `actions/upload-artifact@v4` to the Node 24-native major line so pipeline warning annotations are not reintroduced by the diagnostics step.
- Commit: `816d5ada` fix github workflow node24 warnings.

- Replaced legacy branch-based GitHub Pages deployment with an explicit workflow using Node 24-native Pages actions, so Pages warnings are controlled in repository code instead of GitHub's generated legacy workflow.
- Commit: `816d5ada` fix github workflow node24 warnings.

- Updated build-data to explicitly dispatch the Pages workflow after generated artifact commits, because bot pushes made with `GITHUB_TOKEN` do not naturally fan out into a second workflow run.
- Commit: `1cfd0d35` trigger pages after data artifact builds.

- Restored GitHub validation workflow integrity by adding the missing availability source validator, aligning the validate workflow with the asset fetch precondition used by build-data, fixing the self-heal asset downloader call signature/base URL, and replacing the retired `watch_me_runtime.js` syntax check with the active shared watch-state runtime module.
- Commit: `f3f3948f` fix github validation workflow availability checks.

- Implemented MC-2026-05-05.1 Trakt two-way watch-state sync: file-backed `data/watch_state_queue.json`, local click queue records, inputs-editor queue/sync APIs, Trakt dry-run/live sync engine, exact watchlist/history endpoint payload generation, and validation/browser QA coverage for queue records and payload proof.
- Commit: `5d62716f` implement trakt two way watch state sync.

- Implemented MC-2026-04-30.4 contract updates for shared calendar column alignment, tri-state local-first watch-state records, queued Trakt workflow scaffolding, computed Manage Watch State statuses, popup media-detail rendering, Android TV popup focus trapping, and extended rendered validation.
- Commit: `0105895e` fix calendar trakt watch state popup and dpad contract compliance.

- Fixed dashboard duplicate rendering guards with shared card render keys, scoped dashboard dedupe, and non-accumulating dashboard navigation handlers.
- Restored the top app nav as a true sticky header and compacted dashboard recommendation card sizing.
- Extended runtime validation to cover duplicate dashboard render keys, sticky top nav pinning, compact recommendation dimensions, and local rendered performance thresholds against `docs/00_master_contract.html`.
- Commit: `7e5c6fe5` fix dashboard rendering and sticky nav validation.

## 2026-04-30

- Updated page shells to add Discover to the primary icon nav across active pages.
- Wired Discover to a separate discover registry source and config-needed empty state.
- Rebuilt Manage Watch State display rules so show/season rows derive watched status from released children.
- Aligned validation and rendered QA checks with the current master contract.
- Commit: `5f1af1c9` implement master contract compliance batch.

## 2026-06-02

- Added the X1 lab VM deployment foundation under `deployment/vm_lab/` with Ubuntu Server LTS sizing, network/port expectations, bootstrap installation, and validation checks for Git, Python, PostgreSQL, Nginx, ffmpeg/ffprobe, `/opt/mytv_movie`, and reserved API port ownership.
- Chose Nginx as the baseline VM web server for static file serving now and later API reverse proxying, while leaving API/database implementation to the separate application owner.
- Added the HP production folder as a promotion-plan-only target and a Windows-side lab package helper under `scripts/deployment/` without VM creation or secrets.
- Commit: `433af93294` add-x1-lab-vm-deployment-foundation.
