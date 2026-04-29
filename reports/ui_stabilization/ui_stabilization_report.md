# UI Stabilization Report

Date: 2026-04-29

## Drift Checklist

| Area | Status | Result |
|---|---|---|
| Action/icon logic | implemented | `web/js/action_bar.js` owns popcorn, watch, ticket, double-heart, compact percent rating. |
| Card shell | implemented | `web/js/card_renderer.js` keeps media, text, and actions in a stable non-overlapping layout. |
| Watch state | implemented | `web/js/watch_state_manager.js` owns local-first `watched_status`, `watch_list`, and `favourite`. |
| Watch state scope | implemented | State keys now include item context so one card toggle cannot update unrelated cards. |
| Popup handler | implemented | `web/js/trailer_watch_popup_fix.js` remains the non-blocking watch-source popup owner; app runtime remains fallback-only. |
| Header | implemented | Page shells use the compact logo asset and sticky header styling. |
| Dashboard/calendar overflow | implemented | Shared `+X more` expansion replaces fixed three-item truncation. |
| Asset pipeline | implemented | `assets/original_downloads/` remains immutable; runtime folders were optimized by `scripts/optimize_runtime_assets.py`. |
| Validation | implemented | `scripts/validate_runtime.ps1` is the single repo-standard runtime validation entry point. |

## Canonical Owners

- Icons/actions: `web/js/action_bar.js`
- Shared card shell: `web/js/card_renderer.js`
- Local watch state: `web/js/watch_state_manager.js`
- Data/calendar loading: `web/js/data_loader.js`
- Watch-source popup: `web/js/trailer_watch_popup_fix.js`
- Layout/card spacing: `web/css/main_app.css`
- Compatibility stabilization: `web/css/ui_contract_fix.css`, `web/js/ui_contract_fix.js`, `web/js/runtime_render_fix.js`

## Asset Optimization

- Source files scanned: `10,095`
- Runtime files processed: `10,069`
- Errors: `0`
- Original/runtime-before total: `928,544,464` bytes
- Runtime-after total: `128,752,073` bytes
- Savings: `799,792,391` bytes
- Runtime targets: posters `171x257`, stills `256x180` after side crop, backdrops max width `780`

## Validation Results

- `powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1`: passed
- Static page smoke on `http://127.0.0.1:8000`: passed for index, calendar, shows, movies, watch_me, discover, config, and inputs_editor
- Inputs Editor API smoke on `http://127.0.0.1:8787/api/health`: passed
- `scripts/qa_browser_layout_check.mjs`: passed at the requested TV, laptop, tablet, and phone viewports
- `scripts/qa_browser_popup_check.mjs`: passed for show and movie popup paths
- Rendered DOM audit: passed for logo load, visible action geometry, rating format, visible watch-state keys, card badge removal, modal focus, and horizontal overflow

## Remaining Issues

- No intentional runtime asset originals were modified; `assets/original_downloads/` remains the source of truth.
- Android TV emoji rendering may differ by device font, but the source icon contract is locked in `web/js/action_bar.js`.
