# Inputs Editor Operational History

This file records recurring Inputs Editor failures and the fixes that must not drift.

## Current Contract

- Canonical input file: `data/inputs.json`.
- Generated runtime catalog: `data/data.json`. Retired split artifacts such as `data/catalog_index.json`, `data/calendar.json`, and `data/catalog_detail/*.json` are not active runtime outputs.
- Canonical editor UI: `web/inputs_editor.html`.
- Local editor server: `tools/inputs_editor/inputs_editor_server.py` on `127.0.0.1:8787`.
- Launcher: `run_local_servers.bat`; default browser launch opens only `http://127.0.0.1:8787/web/inputs_editor.html`.
- Full app smoke-test tabs require the explicit `-AllTabs` argument.
- Canonical publish remote: the configured upstream of local `main`, normally `origin/main`. A redundant `github` alias may exist, but the editor must not use a requested secondary remote silently when it differs from the upstream repository.
- Editor operations are separate: `Save Local Input` only writes `data/inputs.json`; `Refresh Full Local Runtime` runs the full local pipeline and is local-only; `Save Online, Build Data, Deploy` reconciles canonical input, pushes an input-only commit, waits for GitHub build-data, fast-forwards the local checkout to the generated artifact commit, and verifies deployed Pages runtime data.
- Source reconciliation for `data/inputs.json` uses stable identity `media_type + tmdb_id`. Local-only and remote-only records are preserved; unchanged local records accept remote edits; unchanged remote records accept local edits; genuine same-field conflicts block with field-level details.
- Program consolidation rule: do not add another Inputs Editor launcher or helper program. `run_local_servers.bat` is the canonical user entrypoint; `run_server.bat`, `tools/run_local_servers.bat`, and `tools/start_inputs_editor.cmd` are compatibility wrappers only and must delegate to the root launcher.
- Cleanup rule: do not keep stale local generated reports or archived binary/spec workspace changes as incidental working-tree dirt. Regenerate through the existing pipeline when runtime data is needed, or restore stale local artifacts to the committed state.

## November 5 2026 Build-data Severity Hardening

The October-November scheduled-build incident established that a valid runtime can be blocked by one record-level metadata discrepancy. TMDB ID `1599993` had authored title `Animals` while TMDB's canonical title was `Animales`. TMDB generation completed and the rest of the catalog was usable, but the identity audit previously returned a failing exit code.

The build-data contract now classifies findings as `info`, `warning`, `recoverable_error`, or `fatal_error`:

- Stable TMDB-ID title differences are reported as recoverable and generated runtime uses the current TMDB title. The editor-authored `data/inputs.json` is not silently rewritten.
- Affected records that cannot be safely enriched or resolved are reported and quarantined/omitted while valid records continue.
- Missing optional metadata is a warning; it is included in the structured diagnostics report and GitHub Actions summary.
- Invalid canonical input JSON, invalid generated runtime JSON, missing required configuration/authentication, zero valid output, unusable structure, write failure, and unresolved duplicate stable identities remain fatal and block artifact publication.

`scripts/data_quality.py` defines the shared issue shape and severity counts. `scripts/audit_inputs_tmdb_type.py` and `scripts/qa_pipeline_integrity.py` preserve JSON evidence, write `reports/build_data_quality_summary.json`, and return nonzero only when fatal conditions exist. Diagnostics upload on every workflow outcome; artifact commit and Pages dispatch require successful generation, structural validation, and zero fatal diagnostics.

The deterministic regression fixture uses `Animals`/`Animales` with TMDB ID `1599993` and proves canonical runtime selection, structured reporting, zero fatal errors, and exit code `0`. Separate fixtures preserve fatal behavior for malformed input/runtime JSON, zero usable output, and duplicate identity ambiguity.

## Failure History

### September 16 2026 Version-Control Publish Verification

Symptom:

- After adding a batch of shows in the Inputs Editor, local and GitHub browser views appeared to disagree about the visible app version and generated runtime timestamp.
- Representative titles included `The Newsreader`, `Black Snow`, and `Kin`.

Forensic finding:

- The editor produced input commit `9a93d762fd` against `data/inputs.json`.
- GitHub `build-data` succeeded and produced generated artifact commit `e20833765b`.
- Pages deployment run `35048099402` succeeded for the generated commit.
- The publish added 23 TV inputs, including `The Newsreader` `130842`, `Black Snow` `210178`, and `Kin` `112693`; all 23 were present in local runtime, canonical remote runtime, and deployed Pages runtime.
- The final verified runtime counts were `316` shows and `134` movies with generated timestamp `2026-09-16T02:27:22Z`.

Architecture guard:

- Browser-visible app version and active shell cache keys must be advanced through `web/config.json -> _meta.version`, active HTML asset query strings, and `web/js/app_runtime.js` static module imports when a release-control pass is made.
- Documentation must capture the input commit, generated commit, workflow/Pages proof, runtime counts, and representative title IDs so version/control evidence is not only in chat history.

### Wrong Server 404

Symptom:

- Editor opens from `http://127.0.0.1:8000/web/inputs_editor.html`.
- The page tries `/api/inputs` on the static file server and reports `Could not load data/inputs.json. Error: Server returned non-JSON response (404)`.

Cause:

- The static server on port `8000` cannot serve the editor API.

Fix:

- The editor now treats `/api/health` returning non-OK as the wrong server and stops before loading inputs.
- The page shows the correct recovery URL: `http://127.0.0.1:8787/web/inputs_editor.html`.

### Launcher Opens Every App Tab

Symptom:

- Re-running `run_local_servers.bat` opens Dashboard, Calendar, Shows, Movies, Watch Me, Discover, Config, a static editor tab, and the live editor tab.

Cause:

- The canonical launcher delegated to `tools/run_smoke_test.ps1`, and that script always opened the full smoke-test URL list.

Fix:

- `tools/run_smoke_test.ps1` now opens only the live Inputs Editor by default.
- The old all-tabs behavior is preserved behind the explicit `-AllTabs` switch for QA.

### Saved Input Missing From Deployed App

Symptom:

- A show appears saved locally in the editor but is missing from the deployed Shows page or from a user-opened stale app tab.

Cause:

- Saving `data/inputs.json` is not sufficient. The generated runtime artifacts must also be built, committed, pushed, deployed, and loaded by the browser.
- A behind local checkout, dirty generated artifacts, or unresolved Git conflict can block publish/sync after the local save.

Fix:

- The publish path already waits for generated runtime artifact changes and validates pipeline reconciliation.
- The publish path now also refuses to continue when Git reports unmerged/conflicted files, returning the exact conflicted paths to the UI.
- The editor must not label local membership as online success. Search results distinguish `In local input`, `Local only - not published`, `Published input - build pending`, `Online - local runtime stale`, `Online`, and `Hidden from app`.

### Yaga / Local More Complete Than GitHub Incident

Symptom:

- The local editor reported the TV show `YAGA` as present, and the local Shows page rendered it.
- GitHub `data/inputs.json`, GitHub `data/data.json`, and the deployed Pages runtime did not contain the same show.
- Local runtime and GitHub runtime had matching movie counts but different TV completeness; timestamp recency was misleading because the GitHub runtime was newer but less complete.

Forensic finding:

- The local Yaga entry was `tmdb_id: 314360`, `season_spec: "*"`, `include_future: true`, `in_scope: true`, `tags: []`, `notes: ""`.
- The local input contained nine TV rows absent from canonical remote input: `Apple Tree Yard` `69773`, `Cooper & Fry` `296520`, `Deadwater Fell` `95442`, `Drag Race Down Under vs The World` `299268`, `Harry Wild` `156993`, `Number 10` `307974`, `The Chelsea Detective` `156240`, `Tommy & Tuppence` `318312`, and `YAGA` `314360`.

Architecture guard:

- `Save Online, Build Data, Deploy` now semantically merges local and remote inputs before committing.
- Generated local preview files are disposable and may be stashed during publish; only `data/inputs.json` may enter the user's input commit.
- Final success requires changed IDs to exist in canonical remote input, remote generated `data/data.json`, local generated `data/data.json`, and deployed Pages `data/data.json`.
- `scripts/qa_inputs_editor_workflow.py`, `scripts/qa_pipeline_integrity.py`, and `scripts/validate_runtime.ps1` guard the workflow state labels, canonical remote handling, semantic merge rules, input-only commits, and deployed-runtime verification hooks.

### Reusing the Wrong Local Process

Symptom:

- `run_local_servers.bat` reports servers are ready, but the editor talks to a stale process or a different checkout on port `8787`.

Cause:

- A plain HTTP 200 from `/api/health` only proves something is listening. It does not prove the server is this repo's Inputs Editor process.

Fix:

- The launcher now validates that `/api/health` returns `ok: true` and a `repo_root` matching the current checkout before reusing port `8787`.
- If port `8787` is occupied by another process, the launcher stops with an explicit message instead of opening an editor that can save to the wrong checkout.

### Failed Git Conflict Scan

Symptom:

- Online publish reaches later Git commands after the initial conflict check cannot run.

Cause:

- A failed `git diff --diff-filter=U` scan was previously indistinguishable from a clean checkout.

Fix:

- The publish guard now treats a failed conflict-state scan as publish-blocking and returns a dedicated Git error.
- Rebase failures also return any conflicted paths captured before aborting the rebase.

## June 27, 2026 Incident

Reported action:

- User searched for `drag race` and intended to add TMDB show `314487`, `Canada's Drag Race: All Stars`, with all seasons.

Local validation:

- `data/inputs.json` contains `Canada's Drag Race: All Stars`, `tmdb_id: 314487`, `season_spec: "*"`, `include_future: true`, `in_scope: true`.
- `data/catalog_index.json`, `data/data.json`, and `data/catalog_detail/314487.json` contain the show.
- The local generated detail file has season data for TMDB `314487`.

Repository-state finding:

- The local checkout was behind `origin/main` and had many generated artifact changes.
- `data/watch_state_queue.json` was in an unresolved conflict state, which blocks reliable publish/rebase/push behavior.

Applied guard:

- Online publish now fails early with a conflict-specific message until unmerged paths are resolved.
- Follow-up cleanup restored stale local dirt in `reports/ui_stabilization/asset_optimization.json` and the archived spec workspace file instead of preserving unrelated local artifacts as part of the Inputs Editor fix.

## Validation Hooks

- `scripts/validate_runtime.ps1` checks the launcher contract, editor publish contract, wrong-server UI guard, and conflict-guard terms.
- `scripts/qa_pipeline_integrity.py` checks that active inputs reconcile into generated runtime artifacts and that the editor publish path waits for generated artifact sync.

## November 4, 2026 — VisionQuest freshness and scheduled build incident

Symptom:

- VisionQuest (`tmdb_id: 213375`) appeared in the app, but its popup carried stale Season 1 episode names/dates and omitted current upcoming dates.
- Local `data/data.json`, GitHub `main`, and Pages all matched the same stale generated row.
- Scheduled `build-data` runs failed from October 23 through November 4 while inputs-editor push runs succeeded.

Forensic finding:

- Direct TMDB `/tv/213375` and `/tv/213375/season/1` returned `No Strings`, `Theseus`, `Reboot`, `Malware`, `Firewall`, `Deadlock`, `Immolation`, and `Forever` dated October 13 through November 10, 2026.
- The incremental cache reused VisionQuest solely because its input signature was unchanged. A controlled normal build reused all 368 TV rows; an isolated forced build rebuilt all 368 and produced the current TMDB dates.
- Scheduled/manual builds already force a full TMDB refresh, but they failed in the final integrity/identity validation before generated artifacts were committed. The exact blocking identity mismatch was movie `1599993`: input title `Animals`, TMDB title `Animales`. The canonical input was corrected.

Applied architecture:

- TV cache reuse now requires `_fetched_utc` freshness: active/current 24 hours, recently ended 7 days, stable ended 30 days. Old rows without freshness metadata are stale. Movies retain signature caching, and force-full refresh remains an explicit bypass.
- The pipeline emits `FAILED_STAGE=<stage>` and a GitHub error annotation so TMDB, Trakt, assets, self-heal, optimization, availability, and validation failures are actionable in one workflow log.
- `scripts/qa_pipeline_integrity.py` now exercises the freshness policy and verifies VisionQuest-like future episode retention and current runtime dates.

Operational verification requirement:

- A green build is not sufficient. Confirm the VisionQuest row in local `data/data.json`, `origin/main:data/data.json`, deployed Pages `data/data.json`, and the rendered Shows popup. Record the input commit, generated artifact commit, build-data run, Pages run, generated timestamp, and final `main` synchronization state.
