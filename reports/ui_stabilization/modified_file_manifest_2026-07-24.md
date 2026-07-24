# Modified File Manifest - UI-PARITY-CURRENT-SEARCH-CACHE-2026-07-24

## Runtime

- `web/js/app_runtime.js` - canonical Current scope controls, Current predicates, provider fallback anchor for empty TMDB provider rows, versioned module imports.
- `web/css/main_app.css` - compact genre grid, phone browse controls remain visible, responsive browse layout cleanup.
- `web/config.json` - release version advanced to `v1.5.2`.

## Page Shells

- `web/index.html`
- `web/shows.html`
- `web/movies.html`
- `web/calendar.html`
- `web/discover.html`
- `web/config.html`
- `web/watch_me.html`
- `web/manage_watch_state.html`

These active shells now load shared CSS and JavaScript with deterministic `?v=v1.5.2` query parameters. Shows and Movies no longer load mobile-only Current/Search fixes.

## Removed Duplicate Mobile Implementation

- `web/js/mobile_current_filters.js`
- `web/css/mobile_browse_fixes.css`

## Validation and QA

- `scripts/validate_runtime.ps1` - guards canonical Current ownership, feature parity, retired mobile files, touch Search visibility, and versioned active shell assets.
- `scripts/qa_browse_filter_parity.mjs` - focused rendered regression QA for Shows/Movies Current, Search, Genre, navigation, and cache-version behavior.

## Documentation

- `docs/00_master_contract.html`
- `docs/ARCHITECTURE.md`
- `docs/UI_COMPONENTS.md`
- `docs/UI_GAP_ANALYSIS.md`
- `docs/ARCHITECTURE_LOG.md`
- `docs/_archive/contracts/00_master_contract_pre_ui_parity_current_cache_20260724.html`
- `reports/ui_stabilization/current_search_cache_regression_2026-07-24.md`
- `reports/ui_stabilization/browse_filter_parity_2026-07-24.json`
- `reports/ui_stabilization/screenshots/shows-phone-current-search-genre.png`
- `reports/ui_stabilization/screenshots/movies-phone-current-search-genre.png`
- `reports/ui_stabilization/screenshots/shows-desktop-current.png`
- `reports/ui_stabilization/screenshots/movies-tv-current.png`

## Out Of Scope And Unmodified

- `data/data.json`
- `data/inputs.json`
- `data/calendar.json`
- `data/catalog_detail/**`
- `assets/**`
- requested-title import outputs
- provider metadata
- TMDB/content pipeline scripts
