FILE: reports/ui_component_audit/runtime_repair_followup_report.md
VERSION: v1.0
UPDATED: 2026-03-15T05:22:36Z
CHANGE NOTES:
- Recorded the shared-runtime corrective repair after the thin-shell normalization broke live boot.
- Captured the actual runtime blockers fixed in this pass.
- Logged the live browser validation evidence for direct main-view routes.

# Runtime Repair Follow-Up Report

## What Broke

The normalized architecture extraction externalized shared runtime and CSS correctly, but the first pass left the main app in a partially wired state:

- boot stayed on `Loading`
- direct pages were not completing the shared runtime path
- the shell was missing required in-app panel containers
- `web/js/config_loader.js` had a syntax error that blocked module boot
- `Inputs Editor` existed as a nav link but was not yet integrated as an in-app routed view

## What Was Fixed

### Shared Runtime Boot

- fixed `web/js/config_loader.js` syntax corruption from the generated extraction pass
- verified `web/js/app_runtime.js` and `web/js/config_loader.js` with `node --check`

### Shared Shell Contract

- restored the missing panel contract inside the shared runtime with `ensureMainAppShell()`
- added shared in-app panels for:
  - calendar
  - shows
  - movies
  - discover
  - config
  - inputs editor
- kept the normalized architecture direction intact

### Direct View Routing

- confirmed direct-entry routes now boot correctly for:
  - dashboard
  - shows
  - movies
  - calendar
  - discover
  - config
- restored working tab activation and route selection through the shared runtime

### Inputs Editor Routing

- made `Inputs Editor` a true in-app routed main view via `#inputs-editor`
- retained `web/inputs_editor.html` as the canonical editor page
- kept `web/library_editor.html` as deprecation/redirect only

### Action Bar / Watch Contract

- confirmed action bar markup is present on main rendered surfaces
- confirmed movie surfaces render popcorn/watch-now chooser markup
- confirmed show surfaces do not expose a direct popcorn launch
- confirmed hot dog is absent from the checked runtime/render path

## Live Validation Evidence

Using Edge headless against the local server:

- `index.html` reached `Ready`
- `shows.html` activated `shows`
- `movies.html` activated `movies`
- `calendar.html` activated `calendar`
- `discover.html` activated `discover`
- `config.html` activated `config`
- `index.html#inputs-editor` activated `inputs-editor`

## Remaining Work

The main product is working again on the normalized shared-runtime path, but some deeper cleanup remains for later:

- further reduce legacy dashboard/calendar icon-strip-era internals that still coexist under the repaired runtime
- continue consolidating older local render fragments toward the shared action-bar contract
- add broader browser smoke coverage if a fuller test harness is introduced
