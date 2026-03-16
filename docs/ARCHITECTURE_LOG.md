# Architecture Change Log

## 2026-03-16

- Live UI stabilization pass completed for the shared web layer.
- Restored page-shell ownership so `calendar` uses a full-width calendar toolbar/shell while `shows` and `movies` keep sidebar-driven browse shells.
- Removed duplicate legacy runtime function ownership in `web/js/app_runtime.js` so one canonical render path controls dashboard, calendar, discover, movie detail, and show detail behavior.
- Re-locked shared action-strip semantics in `web/js/action_bar.js` and `web/js/app_runtime.js` to the canonical content-type order:
  - movies and episodes: `🍿`, `⌚`, `💕`, `🔖`, `⭐%`
  - shows and seasons: `⌚`, `💕`, `🔖`, `⭐%`
- Re-stabilized show detail season and episode rendering around the shared card renderer and season carousel flow.
- Normalized static nav ownership in the active page shells so the correct page is active before and after runtime hydration.
