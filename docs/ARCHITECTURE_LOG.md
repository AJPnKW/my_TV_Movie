# Architecture Log

## 2026-05-20

- Rebased Streaming popup provider buttons on `web/config.json -> streaming.embed_providers[]`, with `ok`/`warn` default-visible, `candidate` hidden unless explicitly enabled, and `blocked` suppressed.
- Added requested candidate/blocked provider registry entries without making them default-active.
- Consolidated Calendar, Dashboard Current/Recent, and show-detail episode cards through `buildSharedEpisodeCard` plus `renderEpisodeCardHtml`, with standard/compact density markers and shared still/backdrop/poster image fallback.
- Added streaming/card anti-drift validation and documentation in `docs/streaming_provider_registry.html` and `docs/episode_card_baseline.html`.
- Commit: pending `Fix streaming providers and unify episode card rendering`.

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
