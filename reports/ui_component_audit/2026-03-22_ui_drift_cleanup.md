# UI Drift Cleanup Report

Date: 2026-03-22

## Root causes fixed

- `web/js/app_runtime.js` still contained duplicated legacy popup and dashboard functions. The later simplified popup path was active and overrode the denser earlier show-popup structure.
- `web/css/main_app.css` still had legacy responsive rules that:
  - collapsed the calendar away from a true 7-column grid
  - wrapped the shared action bar into multiple rows
  - collapsed the shows/movies left rail too early
  - forced dashboard recommendation posters into a widescreen ratio
- Episode cards were still using shared rendering, but not a fully aligned text contract across dashboard, calendar, watch_me, and popup contexts.
- The provider popup close flow was not consistently returning users to the underlying page/popup after launching a source.
- The runtime docs were ahead of the live popup implementation and needed to be brought back in sync with the actual active code.

## Changes made

- Retired duplicated legacy popup/dashboard definitions by renaming the obsolete implementations out of the active runtime path.
- Rebuilt the active show popup with:
  - dense hero facts
  - plain fact rows
  - dedicated where-to-watch section
  - horizontal season rail
  - season detail summary
  - horizontal episode rail
- Restored the shared double-heart favourite icon in the action bar contract.
- Normalized calendar header controls to a single-line toolbar and shortened the Today label.
- Restored left-rail behavior for shows and movies at TV-like widths.
- Restored poster ratio for dashboard recommendation show/movie cards.
- Forced action bars back to a single-row no-wrap contract.
- Focus now lands on `Exit` first in both modal layers, and provider launch closes the provider layer.
- Added a navigation-tree doc for structured page/view review.

## Validation

- `node --check web/js/app_runtime.js`
- `node --check web/js/action_bar.js`
- `node --check web/js/watch_me_runtime.js`
- Headless Edge same-origin runtime harness against:
  - `web/shows.html`
  - show popup
  - `web/calendar.html`
  - `web/index.html`
  - `web/watch_me/watch_me.html`

## Live validation highlights

- Shows layout kept the left rail: `280px 1184px`
- Shows action icons now start: `⌚`, `💕`, `🔖`
- Show popup rendered:
  - `12` plain fact rows
  - season track present
  - `4` season nav buttons
  - `8` popup episode cards on the sampled show
  - `4` episode nav buttons
  - modal close label `Exit`
- Provider popup auto-close behavior validated:
  - provider modal hidden after launch
  - parent modal remained visible
- Calendar rendered:
  - month label `March 2026`
  - today label `Today 03/22/26`
  - toolbar wrap `nowrap`
  - no duplicate `Calendar` heading in the panel header
  - `7` weekday cells
- Dashboard recommendation poster ratio returned to `2 / 3`

## Remaining non-blocking gaps

- Some sampled episode cards still show `SxxExx` without runtime because the underlying episode runtime is absent in the catalog for those specific entries.
- The first sampled show during automation only had one season, so the season rail structure validated, but not a multi-season visual comparison against the prior Game of Thrones example.
- The worktree still contains unrelated local docs-cleanup changes and local-only artifacts outside this pass.

## Clarifications to confirm in the next pass

- Whether the season detail area should also expose a full season-level action strip, or stay as summary + watched toggle only.
- Whether `Discover` should keep section labels like `Featured Show` / `Featured Movie`, or move to fully neutral labels as well.
- Whether a dedicated episode popup is still wanted, or whether the show popup episode rail should remain the only episode-detail surface.

## Implementation commit

- UI drift cleanup implementation commit: `4a5aed2`
