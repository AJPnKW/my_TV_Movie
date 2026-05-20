# UI Components

`docs/00_master_contract.html` remains the authoritative UI contract. This file summarizes component ownership for implementation passes.

## Primary Navigation

- Owner: active HTML page shells plus `web/js/media_library_header_button.js`
- Selector: `.top > .nav[role="tablist"][aria-label="Primary"]`
- Required Media Library link: `#mediaLibraryHeaderButton`
- Required behavior: opens `./Media_Library.html` in a new tab and remains visible within the normal icon row.

## Watch Source Popup

- Provider renderer: `renderWatchProvidersHtml` in `web/js/app_runtime.js`
- Filename copy renderer: `renderWatchSourceMediaDetailHtml` in `web/js/app_runtime.js`
- Copy binding: `openProviderModal` in `web/js/app_runtime.js`
- Popup media-detail block: `web/js/popup_controller.js`

## Cards and Actions

- Canonical cards: `web/js/card_renderer.js`
- Runtime card call-sites: `web/js/app_runtime.js`
- Action strip: `web/js/action_bar.js`
- Active CSS: `web/css/main_app.css`

