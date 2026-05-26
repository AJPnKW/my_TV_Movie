# my_TV_Movie

This repository uses `docs/00_master_contract.html` as the current source of truth. The short Markdown docs in `docs/` are navigation aids for agents and implementation passes.

## Active Entry Points

| Area | Path |
|---|---|
| Runtime app | `web/index.html` |
| Shows | `web/shows.html` |
| Movies | `web/movies.html` |
| Calendar | `web/calendar.html` |
| Discover | `web/discover.html` |
| Watch Me | `web/watch_me.html` |
| Manage Watch State | `web/manage_watch_state.html` |
| Canonical inputs editor | `web/inputs_editor.html` |
| Canonical input data | `data/inputs.json` |
| Generated runtime data | `data/data.json` |

## Repo Hygiene

Generated reports, overlay handoff bundles, Codex prompt bundles, local virtual environments, caches, logs, and build outputs are not active source files. Keep durable behavior in the canonical docs and runtime modules instead of adding parallel handoff folders.

## Validation

```powershell
powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1
python scripts/qa_pipeline_integrity.py
```
