# Documentation Standard

## Purpose

This file defines where current contracts live, which documents are historical only, and how future Codex runs update documentation without creating another parallel doc system.

## Source Of Truth

- Repo-wide architecture and runtime contracts live in `docs/ARCHITECTURE.md`.
- UI component contracts live in `docs/UI_COMPONENTS.md`.
- Data and feature-specific contracts live in the existing functional folders under `docs/architecture/`, `docs/data/`, `docs/design/`, `docs/impact/`, `docs/implementation/`, `docs/testing/`, `docs/ui/`, and `docs/workflows/`.
- Architecture/page-shell changes must also append `docs/ARCHITECTURE_LOG.md`.
- Validation is standardized through `scripts/validate_runtime.ps1`.
- Current stabilization evidence and checklist reports live under `reports/ui_stabilization/`.

## Historical Only

- `docs/_archive/`, `docs/_patch_notes/`, and `docs/spec/archive/` are historical.
- Date-stamped restart/status snapshots, including `docs/PROJECT_STATUS_2026-03-16.md` and `docs/THREAD_RESTART_HANDOFF_2026-03-16.md`, are historical context unless a current source-of-truth doc explicitly references them.
- Historical docs may contain old names or examples. They must not override `docs/ARCHITECTURE.md`, `docs/UI_COMPONENTS.md`, or this file.

## Change Recording

- Changelog-style implementation evidence belongs in `reports/ui_stabilization/` for UI/runtime stabilization work.
- Architecture or page-shell changes require an `docs/ARCHITECTURE_LOG.md` entry with the commit id after commit.
- Future Codex runs should update the existing source-of-truth document for the affected area, not create a new root-level doc.

## Source-Of-Truth Matrix

| Design / Function Area | Canonical File | Supporting Docs | Compatibility Shim, if any | Deprecated / Removed Files | Validation Command |
|---|---|---|---|---|---|
| action icons | `web/js/action_bar.js` | `docs/UI_COMPONENTS.md`, `docs/ARCHITECTURE.md` | `web/js/ui_contract_fix.js`, `web/css/ui_contract_fix.css` | legacy play, bookmark, single-heart, ruler, star, and percent-rating treatments | `powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1` |
| watched_status | `web/js/watch_state_manager.js` | `docs/ARCHITECTURE.md`, `docs/UI_COMPONENTS.md` | none | network-first watched toggles and shared id-only state keys | `powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1` |
| watch_list | `web/js/watch_state_manager.js` | `docs/ARCHITECTURE.md`, `docs/UI_COMPONENTS.md` | none | legacy bookmark icon/current wording | `powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1` |
| favourite | `web/js/watch_state_manager.js` | `docs/ARCHITECTURE.md`, `docs/UI_COMPONENTS.md` | `.favorite` class remains CSS compatibility only where emitted with `.favourite` | single yellow heart treatment | `powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1` |
| Trakt sync design | `docs/ARCHITECTURE.md` | `reports/ui_stabilization/ui_stabilization_report.md` | offline queue design only; no live API required for UI tests | title/fuzzy matching for sync | `powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1` |
| popup/watch-source flow | `web/js/trailer_watch_popup_fix.js` | `docs/ARCHITECTURE.md`, `docs/UI_COMPONENTS.md` | guarded fallback in `web/js/app_runtime.js` | blocking detail-first popup handlers | `powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1` |
| calendar/dashboard data flow | `web/js/data_loader.js` | `docs/ARCHITECTURE.md`, `docs/data/` | `data/data.json` fallback remains for generated runtime continuity | silent dashboard/calendar truncation | `powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1` |
| data split model | `scripts/build_split_runtime.py` | `docs/ARCHITECTURE.md`, `docs/data/` | `data/data.json` retained as fallback/reference | old flat runtime-only dependency | `powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1` |
| asset optimization pipeline | `scripts/optimize_runtime_assets.py` | `docs/ARCHITECTURE.md`, `reports/ui_stabilization/asset_optimization.json` | none | 4K/original-sized runtime assets; originals stay immutable in `assets/original_downloads/` | `powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1` |
| card layout | `web/css/main_app.css` | `docs/UI_COMPONENTS.md`, `reports/ui_stabilization/visual_gap_analysis.md` | `web/css/ui_contract_fix.css` | frame-within-frame wrappers and oversized cards | `powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1` |
| mobile/Android TV layout | `web/css/main_app.css` | `docs/UI_COMPONENTS.md`, `reports/ui_stabilization/visual_gap_analysis.md` | `web/css/runtime_layout_fix.css`, `web/css/ui_contract_fix.css` | giant mobile/TV cards and page-level overflow | `powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1` |
| D-pad navigation | `web/js/chrometv_focus.js` | `docs/ARCHITECTURE.md`, `reports/ui_stabilization/visual_gap_analysis.md` | none | offscreen focus and focus escape from active modal | `powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1` |
| local server launch | `run_local_servers.bat` | `docs/README.md`, `docs/ARCHITECTURE.md` | `run_server.bat`, `tools/run_local_servers.bat`, and `tools/start_inputs_editor.cmd` delegate to the canonical launcher | old `app.py`/port `8811` root launch path and editor-only server launcher logic | `powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1` |
| validation process | `scripts/validate_runtime.ps1` | `docs/README.md`, `reports/ui_stabilization/ui_stabilization_report.md` | existing browser QA scripts may be run after the server is started | duplicate one-off validation entry points | `powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1` |
| documentation process | `docs/DOCUMENTATION_STANDARD.md` | `docs/README.md`, `docs/ARCHITECTURE_LOG.md` | none | new root-level docs for feature-local changes | `powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1` |

## Current Icon Contract

The current action icon order is popcorn, watch, ticket, double-heart, compact numeric rating.

Movies and episodes render `🍿`, `⌚`, `🎫`, `💕`, and a compact rating number such as `76`.

Shows and seasons render `⌚`, `🎫`, `💕`, and a compact rating number.

The third icon is the ticket icon. The fourth icon is the double-heart icon. Compact ratings do not include a star or percent sign.
