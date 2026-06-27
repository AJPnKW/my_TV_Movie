# Inputs Editor Operational History

This file records recurring Inputs Editor failures and the fixes that must not drift.

## Current Contract

- Canonical input file: `data/inputs.json`.
- Generated runtime files: `data/data.json`, `data/catalog_index.json`, `data/calendar.json`, `data/catalog_detail/*.json`, and runtime assets.
- Canonical editor UI: `web/inputs_editor.html`.
- Local editor server: `tools/inputs_editor/inputs_editor_server.py` on `127.0.0.1:8787`.
- Launcher: `run_local_servers.bat`; default browser launch opens only `http://127.0.0.1:8787/web/inputs_editor.html`.
- Full app smoke-test tabs require the explicit `-AllTabs` argument.

## Failure History

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

## Validation Hooks

- `scripts/validate_runtime.ps1` checks the launcher contract, editor publish contract, wrong-server UI guard, and conflict-guard terms.
- `scripts/qa_pipeline_integrity.py` checks that active inputs reconcile into generated runtime artifacts and that the editor publish path waits for generated artifact sync.
