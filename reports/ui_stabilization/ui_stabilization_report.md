# UI Stabilization Report

## Drift Checklist

| Area | Status | Result |
|---|---|---|
| Overlay folders | implemented | Removed tracked `overlay/`, `overlay_patch/`, root apply docs, and the untracked `overlay_ui_contract/` bundle. |
| Patch/apply scripts | implemented | Removed old tracked UI/docs apply scripts and overlay validation script. |
| Action/icon logic | implemented | `web/js/action_bar.js` owns popcorn, watch, ticket, double-heart, compact numeric rating. |
| Watch state | implemented | `web/js/watch_state_manager.js` owns local-first `watched_status`, `watch_list`, and `favourite`. |
| Popup handler | implemented | `web/js/trailer_watch_popup_fix.js` is the active non-blocking watch-source popup; app runtime handler is fallback-only. |
| Calendar completeness | implemented | Calendar day cells render all items directly and no longer hide releases behind a more/less expander. |
| Trakt scaffold | implemented | Config documents local-first mapping: watched history, watchlist, favourite local-only, `tmdb_id` matching. |
| Asset pipeline | deferred | Interrupted asset optimization was reverted; `scripts/optimize_runtime_assets.py` and `asset_optimization.json` establish the deterministic baseline and command path. |
| Validation | implemented | `scripts/validate_runtime.ps1` is the single repo-standard runtime validation entry point. |

## Canonical Owners

- Icons/actions: `web/js/action_bar.js`
- Local watch state: `web/js/watch_state_manager.js`
- Data/calendar loading: `web/js/data_loader.js`
- Watch-source popup: `web/js/trailer_watch_popup_fix.js`
- Layout/card spacing: `web/css/main_app.css`

## Compatibility Shims

- `web/js/runtime_render_fix.js`
- `web/js/ui_contract_fix.js`
- `web/css/runtime_layout_fix.css`
- `web/css/ui_contract_fix.css`

These remain loaded by `web/js/chrometv_focus.js` for compatibility only.

## Validation Command

```powershell
powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1
```

## Validation Results

- `scripts/validate_runtime.ps1`: passed
- HTTP shell smoke on port 8000: `/web/index.html`, `/web/calendar.html`, `/web/shows.html`, `/web/movies.html`, `/web/watch_me.html`, `/web/discover.html`, `/web/config.html` all returned 200
- `scripts/qa_browser_layout_check.mjs`: passed across Android phone, Android tablet, Android/TV CSS, and 1080p TV viewports
- `scripts/qa_browser_popup_check.mjs`: passed show and movie popup checks
