/*
FILE: web/js/popup_controller.js
VERSION: v1.0.0
UPDATED: 2026-03-15T04:28:23Z
CHANGE NOTES:
- Centralized popup/detail runtime contract markers for the normalized main app.
- Establishes the shared popup/detail baseline used by all rebased main views.
*/

export function applyRuntimeContract(doc = document){
  const root = doc.documentElement;
  if (!root) return;
  root.setAttribute('data-popup-contract', 'show_movie_detail_v3');
  root.setAttribute('data-season-model', 'show_detail_only');
}