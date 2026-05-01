# Master Contract Compliance Audit

Date: 2026-04-30

## Contract Read

- `docs/00_master_contract.html`

## Removed / Consolidated

- Kept `web/css/main_app.css` as the sole active UI contract stylesheet for the shared runtime pages.
- Kept the icon-only primary nav across active shells and added the active Discover entry back into the documented nav set.
- Consolidated Manage Watch State into its own standalone matrix/tree page at `web/manage_watch_state.html`.
- Added a dedicated discover feed registry at `data/discover_registry.json` so Discover can stay active without silently falling back to local catalog content.
- Reconciled the watch-state manager to use context-aware keys only, with no generic `type:id` fallback.
- Kept Watch Me as a lightweight compatibility/list surface rather than a watch-state manager.
- Removed the stray root analysis artifact `docs/gap_analysis_master_contract.html`.

## Fixed

- Calendar grid mode now stays at 7 columns on desktop/tablet and uses horizontal scrolling rather than collapsing.
- Header height stays compact and the logo renders as a preserved square/near-square mark with `object-fit: contain`.
- Nav icons remain standalone clickable/focusable targets with no button framing or pill styling.
- Action buttons render as equal-size rounded squares below the media, with the documented icon order and percent rating text.
- Dashboard sticky section headers remain sticky and do not overlap the card flow.
- Manage Watch State now renders a matrix/tree table with show -> season -> episode hierarchy plus top-level movies and compact controls for `watch_list`, `watched_status`, and `favourite`.
- Config remains app settings only and does not embed Manage Watch State.
- Discover renders an explicit config-needed empty state when the external discovery feed registry is not enabled.

## Validation Results

- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate_runtime.ps1`: passed.
- Runtime asset size report: `oversized_runtime_assets` count `0`.
- Browser QA passed on the key contract surfaces at:
  - `1920x1080`
  - `1366x768`
  - `1024x768`
  - `768x1024`
  - `430x932`
  - `390x844`
- Browser QA covered:
  - `web/index.html`
  - `web/calendar.html`
  - `web/manage_watch_state.html`
  - `web/discover.html`
- Popup QA covered:
  - `web/index.html` popcorn button opens the provider modal and renders TMDB/source options.
- Contract checks observed in browser:
  - icon-only nav with no visible button borders
  - compact square logo with preserved aspect ratio
  - 7-column calendar grid plus horizontal scroll on narrow widths
  - rounded-square action icons below the media
  - standalone manage-watch-state matrix/table
  - discover registry empty state with zero local fallback cards

## Rendered Evidence

- `web/index.html` and `web/calendar.html` loaded without page errors in the browser matrix.
- `web/manage_watch_state.html` rendered `304` matrix rows and `10` table columns in the browser matrix.
- `web/discover.html` rendered `1` registry row, `0` local cards, and the contract-safe empty state.
- `web/index.html` popcorn click opened the provider modal with watch options for the active card.
- The shared nav rendered the required icon set across the tested viewports with zero visible borders/radius.

## Blocked Items

- Discover’s non-local suggestion stream is blocked by missing source data / external feed configuration. The UI scaffold is present, but the registry currently marks the feed as config-needed and disabled.

## Remaining Risks

- `web/inputs_editor.html` still depends on its standalone editor runtime path, so it is outside the shared main-page surface even though the launcher and validator preserve reachability.
- Discover will remain an empty state until a real external feed is wired into `data/discover_registry.json` or a documented equivalent source registry.
