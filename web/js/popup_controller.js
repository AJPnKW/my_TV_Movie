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
  root.setAttribute('data-popup-contract', 'show_movie_detail_v4_dense');
  root.setAttribute('data-season-model', 'show_detail_carousel_canonical_episode_cards');
}

function esc(value){
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

export function renderMediaDetailBlockHtml(options = {}){
  const kind = String(options.kind || '').trim().toLowerCase();
  const primary = String(options.primary || '').trim();
  const secondary = String(options.secondary || '').trim();
  const meta = String(options.meta || '').trim();
  const date = String(options.date || '').trim();
  const overview = String(options.overview || '').trim();
  if (!primary && !secondary && !meta && !date && !overview) return '';
  return `
    <section class="popup-media-detail popup-media-detail--${esc(kind || 'media')}" data-popup-media-detail="${esc(kind || 'media')}">
      ${primary ? `<div class="popup-media-detail__primary">${esc(primary)}</div>` : ''}
      ${secondary ? `<div class="popup-media-detail__secondary">${esc(secondary)}</div>` : ''}
      ${meta ? `<div class="popup-media-detail__meta">${esc(meta)}</div>` : ''}
      ${date ? `<div class="popup-media-detail__date">${esc(date)}</div>` : ''}
      ${overview ? `<div class="popup-media-detail__overview">${esc(overview)}</div>` : ''}
    </section>
  `;
}

if (typeof window !== 'undefined'){
  window.MyTVHubPopupController = Object.assign(window.MyTVHubPopupController || {}, {
    applyRuntimeContract,
    renderMediaDetailBlockHtml
  });
}
