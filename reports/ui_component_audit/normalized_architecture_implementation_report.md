FILE: reports/ui_component_audit/normalized_architecture_implementation_report.md
VERSION: v1.0
UPDATED: 2026-03-15T04:34:43Z
CHANGE NOTES:
- Documented the shared runtime extraction and thin-shell conversion for the main app family.
- Recorded the shared CSS/runtime module paths now used by all six main views.
- Captured validation evidence for normalized architecture implementation.

# Normalized Architecture Implementation Report

## Summary

This pass converted the main app from six large inline HTML mini-app copies into one shared runtime path:

- shared JS runtime entry: `web/js/app_runtime.js`
- shared JS support modules:
  - `web/js/config_loader.js`
  - `web/js/data_loader.js`
  - `web/js/card_renderer.js`
  - `web/js/popup_controller.js`
  - `web/js/action_bar.js`
- shared CSS usage in all six main views:
  - `web/css/my_tv_hub.css`
  - `web/css/main_app.css`

## What Changed

### Shared Runtime Extraction

The corrected dashboard-family runtime was extracted from `web/index.html` into `web/js/app_runtime.js`. The rebased runtime now imports and uses shared module helpers for:

- config loading
- catalog loading
- inputs loading
- normalized action-bar contract metadata
- normalized block metadata
- popup/detail contract metadata

### Thin Main View Shells

These pages were converted to thin shells:

- `web/index.html`
- `web/shows.html`
- `web/movies.html`
- `web/calendar.html`
- `web/discover.html`
- `web/config.html`

Each shell now:

- links shared CSS
- loads `./js/app_runtime.js` as a module
- avoids large inline `<style>` and `<script>` payloads
- stays on the same runtime family through `data-page`

### Calendar / Discover / Config Rebase

`calendar`, `discover`, and `config` no longer carry their old inline runtime/style forks. They now load the same shared runtime and shared CSS path as the corrected trio.

### Editor Transition

- `web/inputs_editor.html` remains the canonical editor.
- `web/library_editor.html` now serves as a deprecation/redirect notice.
- `web/config.DOC.md` was moved out of `web/` to `docs/config/config.md`.
- `web/config.json` no longer carries the hot dog icon for `media_videasy`.

## Validation Evidence

- All six main views reference `./js/app_runtime.js`.
- All six main views reference both `./css/my_tv_hub.css` and `./css/main_app.css`.
- All six main views no longer contain inline `<style>` or inline `<script>` blocks.
- `watchstatusband` is absent from all six rebased main view shells.
- `node --check` passed for `web/js/app_runtime.js` and all shared runtime support modules.

## Remaining Limits

This pass normalized architecture and rebased calendar/discover/config, but it did not redesign side surfaces or deeply split every runtime concern into small modules. The large behavior body now lives in one shared runtime file instead of six page copies, which was the required architectural correction for this phase.
