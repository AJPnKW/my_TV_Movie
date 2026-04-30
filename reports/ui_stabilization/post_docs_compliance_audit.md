# Master Contract Compliance Audit

Date: 2026-04-29

## Contract Read

- `docs/00_master_contract.html`

## Removed / Consolidated

- Removed `web/css/my_tv_hub.css` from active shared-runtime page shells so `web/css/main_app.css` is the sole active UI contract stylesheet for Dashboard, Shows, Movies, Calendar, Discover, Config, Manage Watch State, and Watch Me.
- Replaced the old primary nav symbols with the documented icon-only nav: Dashboard, Shows, Movies, Calendar, Discover, Tracking, Config, and Inputs Editor.
- Removed the Manage Watch State card/grid surface and replaced it with a standalone table/tree matrix.
- Removed Discover’s use of local Shows/Movies catalog items. Discover now renders only explicit external non-local suggestions; because no external discovery feed is present in `data/data.json`, it renders a contract-safe empty state.
- Removed the obsolete `🎫` watch-list card action icon in favor of the required `🎟️`.
- Removed active `overflow-x:clip` rules from shared runtime layout CSS.

## Fixed

- Calendar grid mode is forced to a 7-column Mon-Sun layout at every viewport; narrow screens use horizontal scrolling instead of collapsing.
- Header height was reduced and the logo remains the square `assets/custom/the_boys_hub_logo2.png` mark with preserved aspect ratio, no stretch, and no clipping.
- Nav icons are standalone clickable/focusable targets with no border or default framed button background.
- Action buttons render as equal-size rounded squares with the required order: `🍿 ⌚ 🎟️ 💕 76%`.
- Dashboard sticky section headers are present for Current / Recent, Upcoming, Watchlist, and Recommendations.
- Manage Watch State is standalone at `web/manage_watch_state.html`, uses a Shows -> Seasons -> Episodes plus Movies matrix, and exposes compact controls for `watch_list`, three-state `watched_status`, and `favourite`.
- Config remains app settings only and does not render Manage Watch State.
- Watch Me remains a simple list-style release page, not a duplicate Dashboard or Shows page.

## Validation Results

- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate_runtime.ps1`: passed.
- Runtime asset size report: `oversized_runtime_assets` count `0`.
- Rendered Chromium validation passed for:
  - `index.html`
  - `shows.html`
  - `movies.html`
  - `calendar.html`
  - `discover.html`
  - `config.html`
  - `manage_watch_state.html`
  - `watch_me.html`
- Rendered viewport coverage:
  - Android TV: `1920x1080`
  - Desktop/laptop: `1366x768`
  - Tablet: `768x1024`
  - Mobile: `390x844`

## Rendered Assertions

- Primary nav contains required icon-only entries and no visible button text.
- Nav icons have no visible framed button border/radius.
- Logo natural and rendered ratio remain square/near-square and stay inside the compact header.
- Calendar grid mode renders 7 computed columns and 7 weekday-band columns at every viewport.
- Action icons render below card media, are equal width/height, and have rounded-square radius.
- Dashboard section headers compute as sticky.
- Manage Watch State renders as a matrix table with at least 10 columns and no media/card UI.
- Config does not contain Manage Watch State.
- Watch Me renders list rows.
- Discover does not render local catalog cards.

## Remaining Risks / Gaps

- `data/data.json` currently has no external discovery source, so Discover cannot show non-local suggestions yet without a documented feed.
- The user prompt referred to master contract v3, while the active file title says `Master Contract v2`; the implementation followed the existing active file path exactly.
- `web/watch.me.html` and `web/watch_me/watch_me.html` remain redirect compatibility shells by contract.
