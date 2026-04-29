# Post-Documentation Compliance Audit

Date: 2026-04-29

## Docs Read

- `docs/README.md`
- `docs/DOCUMENTATION_STANDARD.md`
- `docs/UI_COMPONENTS.md`
- `docs/ARCHITECTURE.md`

## Files Checked

- `web/js/action_bar.js`
- `web/js/card_renderer.js`
- `web/js/watch_state_manager.js`
- `web/js/app_runtime.js`
- `web/js/chrometv_focus.js`
- `web/js/trailer_watch_popup_fix.js`
- `web/js/runtime_render_fix.js`
- `web/css/main_app.css`
- `web/css/ui_contract_fix.css`
- `scripts/validate_runtime.ps1`
- `scripts/optimize_runtime_assets.py`

## Gaps Found

- `web/css/ui_contract_fix.css` was still acting as an active presentation contract owner even though the finalized documentation makes `web/css/main_app.css` the canonical CSS owner and allows the shim only as compatibility.
- After consolidating the CSS rules, rendered QA exposed a more-specific older `.media-card .actionbar-btn` cascade that kept action buttons at `border-radius: 0`, violating the rounded-square icon-box contract.

## Fixes Applied

- Consolidated the active card/action/header/sticky/more CSS contract into `web/css/main_app.css`.
- Reduced `web/css/ui_contract_fix.css` to a compatibility-only file with no active selectors.
- Hardened `scripts/validate_runtime.ps1` so it fails if active selectors return to `ui_contract_fix.css` or if `main_app.css` no longer owns the finalized adaptive action-box contract.
- Added final specific action-button overrides in `main_app.css` so rendered media-card action buttons remain square, rounded, visible, and unclipped above older specific rules.

## Compliance Confirmed

- Card layout remains image, title/meta, action row.
- Action row stays below media and does not overlay poster/still artwork.
- Availability badges are not visible on card artwork; popcorn color carries availability state.
- Action icon order remains popcorn, watch, ticket, double-heart, compact percent rating where applicable.
- Watch-state keys remain scoped by type and item context.
- Dashboard, Shows, Movies, Watch Me, Calendar, and popup cards continue through shared renderer/action systems.
- Header uses `assets/custom/the_boys_hub_logo2.png` and remains sticky/compact.
- Inputs Editor, Discover, and Watch Me routes remain reachable.
- Trakt remains documented/scaffolded; no fake live sync path was introduced.
- Asset source/runtime split and target dimensions remain enforced by existing validation and optimizer targets.

## Validation Results

- Baseline `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate_runtime.ps1`: passed.
- Post-fix `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate_runtime.ps1`: passed.
- Runtime asset size report: `oversized_runtime_assets` count `0`.
- Local static server: `http://127.0.0.1:8000` already listening.
- Rendered QA: passed across all requested pages and viewport sizes.

Rendered pages:

- `http://127.0.0.1:8000/web/index.html`
- `http://127.0.0.1:8000/web/calendar.html`
- `http://127.0.0.1:8000/web/shows.html`
- `http://127.0.0.1:8000/web/movies.html`
- `http://127.0.0.1:8000/web/watch_me.html`
- `http://127.0.0.1:8000/web/discover.html`
- `http://127.0.0.1:8000/web/config.html`
- `http://127.0.0.1:8000/web/inputs_editor.html`

Rendered viewports:

- `1920x1080`
- `1366x768`
- `1024x768`
- `768x1024`
- `430x932`
- `390x844`

Rendered checks covered:

- compact logo load
- sticky header
- Inputs Editor reachability
- action row below media
- rounded square icon boxes
- no visible card availability overlays
- compact percent rating text
- sticky section headers where present
- Dashboard/Calendar `+X more`
- modal focus containment and Escape close

## Remaining Risks

- Device font rendering can still vary for emoji glyphs on Android/TV browsers, but rendered geometry now validates square rounded boxes and no clipping in Chromium.
- The in-app Browser plugin Node REPL control tool was not exposed in this session, so rendered QA used local headless Chromium through `puppeteer-core` instead.
