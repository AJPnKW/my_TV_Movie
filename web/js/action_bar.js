/*
FILE: web/js/action_bar.js
VERSION: v1.0.0
UPDATED: 2026-03-15T04:28:23Z
CHANGE NOTES:
- Centralized normalized action-bar contract metadata for the shared main app runtime.
- Declares the locked action ordering and watch-status values.
*/

export const ACTION_BAR_ORDER = Object.freeze([
  'watch',
  'status',
  'favourite',
  'bookmark',
  'rating'
]);

export const WATCH_STATUS_VALUES = Object.freeze([
  'watchlist',
  'watching',
  'paused',
  'completed',
  'dropped'
]);

export function applyRuntimeContract(doc = document){
  const root = doc.documentElement;
  if (!root) return;
  root.setAttribute('data-action-bar-order', ACTION_BAR_ORDER.join(','));
  root.setAttribute('data-watch-status-values', WATCH_STATUS_VALUES.join(','));
}

function attrString(attrs = {}){
  return Object.entries(attrs)
    .filter(([, value]) => value != null && value !== '')
    .map(([key, value]) => ` ${String(key)}="${String(value).replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')}"`)
    .join('');
}

function splitAttrs(attrs = {}){
  const next = { ...attrs };
  const href = next.href || '#';
  delete next.href;
  return { href, attrs: next };
}

export function renderActionBarHtml(options = {}){
  const kind = String(options.kind || '').toLowerCase();
  const leftActions = [];
  const middleActions = [];
  const rightActions = [];

  if (options.watch && (kind === 'movie' || kind === 'episode')){
    const watchLink = splitAttrs(options.watch.attrs || {});
    leftActions.push(`<a class="actionbar-btn actionbar-btn--watch" href="${String(watchLink.href).replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')}" aria-label="Choose watch source" title="Choose watch source" data-watch-source-open="${options.watch.kind || 'movie'}"${attrString(watchLink.attrs)}><span class="actionbar-glyph" aria-hidden="true">🍿</span></a>`);
  }
  if (options.status){
    const statusLink = splitAttrs(options.status.attrs || {});
    middleActions.push(`<a class="actionbar-btn actionbar-btn--status" href="${String(statusLink.href).replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')}" aria-label="Watch status" title="Watch status" data-action-menu="status" data-no-default="1"${attrString(statusLink.attrs)}><span class="actionbar-glyph" aria-hidden="true">${options.status.icon || '⌚'}</span></a>`);
  }
  if (options.favourite){
    const favouriteLink = splitAttrs(options.favourite.attrs || {});
    middleActions.push(`<a class="actionbar-btn actionbar-btn--favorite${options.favourite.active ? ' active' : ''}" href="${String(favouriteLink.href).replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')}" aria-label="Toggle favourites" title="Toggle favourites" data-action="toggle-want"${attrString(favouriteLink.attrs)}><span class="actionbar-glyph" aria-hidden="true">${options.favourite.icon || '💕'}</span></a>`);
  }
  if (options.watched){
    const watchedLink = splitAttrs(options.watched.attrs || {});
    middleActions.push(`<a class="actionbar-btn actionbar-btn--bookmark${options.watched.active ? ' active' : ''}" href="${String(watchedLink.href).replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')}" aria-label="Toggle bookmark" title="Toggle bookmark" data-action="toggle-watched"${attrString(watchedLink.attrs)}><span class="actionbar-glyph" aria-hidden="true">${options.watched.icon || '🔖'}</span></a>`);
  }
  if (options.rating){
    rightActions.push(`<span class="actionbar-btn actionbar-btn--rating" aria-label="Ratings" title="Ratings"><span class="actionbar-rating" aria-hidden="true"><span class="actionbar-rating__star">★</span><span class="actionbar-rating__value">${options.rating.icon || '%'}</span></span></span>`);
  }

  return `<div class="actionbar action_bar${options.compact ? ' actionbar--minimal' : ''}" data-action-host="1"><span class="actionbar__group actionbar__group--left${leftActions.length ? '' : ' actionbar__group--empty'}">${leftActions.join('')}</span><span class="actionbar__group actionbar__group--middle">${middleActions.join('')}</span><span class="actionbar__group actionbar__group--right">${rightActions.join('')}</span>${options.menusHtml || ''}</div>`;
}

if (typeof window !== 'undefined'){
  window.MyTVHubActionBar = Object.assign(window.MyTVHubActionBar || {}, {
    ACTION_BAR_ORDER,
    WATCH_STATUS_VALUES,
    applyRuntimeContract,
    renderActionBarHtml
  });
}
