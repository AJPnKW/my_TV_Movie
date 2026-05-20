# Architecture

`docs/00_master_contract.html` is the source of truth. This file is a navigation aid for agents and must not replace or fork the contract.

## Runtime Ownership

- Runtime shell and routing: `web/js/app_runtime.js`
- Shared card renderers: `web/js/card_renderer.js`
- Shared action strip: `web/js/action_bar.js`
- Watch-state persistence and refresh: `web/js/watch_state_manager.js`
- Popup media-detail schema: `web/js/popup_controller.js`
- Media Library primary-nav normalizer: `web/js/media_library_header_button.js`
- Active app styling: `web/css/main_app.css`

## Page Shells

The active app shells are `web/index.html`, `web/shows.html`, `web/movies.html`, `web/calendar.html`, `web/discover.html`, `web/config.html`, `web/watch_me.html`, and `web/manage_watch_state.html`.

The primary `.top > .nav[role="tablist"][aria-label="Primary"]` row must contain the view icons, including the static `#mediaLibraryHeaderButton` link to `web/Media_Library.html`.

## Retired Runtime Code

Retired compatibility shims are archived under `docs/_archive/runtime_shims/` and must not be restored under `web/js/` or loaded by `web/js/chrometv_focus.js`.

