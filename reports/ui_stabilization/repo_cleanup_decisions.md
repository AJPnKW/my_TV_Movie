# Repo Cleanup Decisions

Date: 2026-04-28

## Keep Active

| Area | Files |
|---|---|
| Runtime shell | `web/index.html`, `web/calendar.html`, `web/shows.html`, `web/movies.html`, `web/watch_me.html`, `web/discover.html`, `web/config.html` |
| Canonical runtime owners | `web/js/action_bar.js`, `web/js/watch_state_manager.js`, `web/js/data_loader.js`, `web/js/trailer_watch_popup_fix.js`, `web/css/main_app.css` |
| Compatibility shims | `web/js/runtime_render_fix.js`, `web/js/ui_contract_fix.js`, `web/css/runtime_layout_fix.css`, `web/css/ui_contract_fix.css` |
| Validation | `scripts/validate_runtime.ps1`, existing browser QA scripts called manually after server start |
| Data/runtime assets | `data/*.json`, `assets/posters`, `assets/stills`, `assets/backdrops`, `assets/logos`, `assets/icons` |

## Keep Historical

| Area | Files |
|---|---|
| Archived docs | `docs/_archive/`, `docs/_patch_notes/`, `docs/spec/archive/` |
| Historical reports | `reports/ui_component_audit/` |
| Restart/status snapshots | `docs/PROJECT_STATUS_2026-03-16.md`, `docs/THREAD_RESTART_HANDOFF_2026-03-16.md` |

## Already Removed From Active Repo

| Drift Type | Decision |
|---|---|
| Overlay folders | Removed as active files; validation fails if `overlay/`, `overlay_patch/`, or `overlay_ui_contract/` return. |
| Root apply docs | Removed as active files; validation fails if root overlay apply docs return. |
| Old apply/overlay scripts | Removed as active files; validation fails if old UI patch or image-fix script names return. |
| Placeholder files | Forbidden as active tracked filenames; real form `placeholder` attributes remain allowed where they are actual UI input hints. |

## Ignore Local Generated Files

| Area | Decision |
|---|---|
| Logs | Treat generated files under `logs/` as local evidence unless explicitly requested. |
| Original assets | `assets/original_downloads/` remains immutable input storage and must not be deleted or optimized in place. |
| Runtime optimized assets | Current runtime asset folders stay active; oversized files are reported by validation and `reports/ui_stabilization/asset_optimization.json`. |
