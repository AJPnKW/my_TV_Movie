# 2026-03-20 Stabilization Pass

## Root Causes Fixed

- Rebased `web/index.html` back to a thin canonical shell so `web/js/app_runtime.js` and `web/css/main_app.css` are authoritative again.
- Removed the fake embedded Inputs Editor surface from the main shell and pointed all app-shell editor links to the real local-server flow on `127.0.0.1:8787`.
- Hardened the editor server save path with payload validation, backup creation, atomic write, CORS-safe health checks, and a runtime refresh endpoint.
- Rebuilt `web/watch_me/watch_me.html` around the shared shell plus shared card/action modules instead of a separate custom icon/card implementation.
- Removed blocking `input()` pauses from asset QA/repair scripts so they can run in automation and through the editor refresh flow.
- Restored a tracked `.gitignore` and a current GitHub Actions validation workflow using current action versions and Node 24.

## Validation

- `python -m compileall scripts tools/inputs_editor`
- `node --check web/js/app_runtime.js web/js/card_renderer.js web/js/action_bar.js web/js/config_loader.js web/js/data_loader.js web/js/popup_controller.js web/js/watch_me_runtime.js`
- Headless Chrome smoke validation against:
  - `http://127.0.0.1:8000/web/index.html`
  - `http://127.0.0.1:8000/web/shows.html`
  - `http://127.0.0.1:8000/web/movies.html`
  - `http://127.0.0.1:8000/web/calendar.html`
  - `http://127.0.0.1:8000/web/watch_me/watch_me.html`
  - `http://127.0.0.1:8787/web/inputs_editor.html`
- Verified:
  - dashboard loaded to `Ready`
  - shows and movies grids rendered
  - calendar rendered as a 7-column month grid and `Show less` toggle worked
  - watch-source popup auto-closed after stream/source click from the movie popup on `movies.html`
  - watch_me rendered shared episode cards under the shared shell
  - live Inputs Editor loaded from port `8787`
- Asset QA run:
  - `python scripts/qa_assets_against_data_json.py --no-pause`
  - output folder: `logs/asset_qa_20260320_223413`

## Remaining Non-Blocking Items

- Asset debt remains high in the current dataset: QA still reports `6683` missing local asset references and `2914` orphan local assets, mostly episode stills.
- The dashboard smoke test validated shared show popup wiring; movie popup validation was confirmed from `movies.html`, where watch-source auto-close now works reliably.
- Static-site smoke checks still report `404` for `/api/health` on port `8000` and `/favicon.ico`; these do not block app use because the live editor flow is intentionally on port `8787`.
