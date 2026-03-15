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
  'favourite',
  'watched',
  'like',
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
  const actions = [];
  if (options.watch){
    const watchLink = splitAttrs(options.watch.attrs || {});
    actions.push(`<a class="actionbar-btn popcorn" href="${String(watchLink.href).replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')}" aria-label="Watch" title="Watch" data-watch-source-open="${options.watch.kind || 'movie'}"${attrString(watchLink.attrs)}><span aria-hidden="true">🍿</span></a>`);
  }
  if (options.favourite){
    const favouriteLink = splitAttrs(options.favourite.attrs || {});
    actions.push(`<a class="actionbar-btn favorite${options.favourite.active ? ' active' : ''}" href="${String(favouriteLink.href).replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')}" aria-label="Favourite" title="Favourite" data-action="toggle-want"${attrString(favouriteLink.attrs)}><span aria-hidden="true">${options.favourite.icon || '☆'}</span></a>`);
  }
  if (options.watched){
    const watchedLink = splitAttrs(options.watched.attrs || {});
    actions.push(`<a class="actionbar-btn${options.watched.active ? ' favorite active' : ''}" href="${String(watchedLink.href).replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')}" aria-label="Watched" title="Watched" data-action="toggle-watched"${attrString(watchedLink.attrs)}><span aria-hidden="true">${options.watched.icon || '✓'}</span></a>`);
  }
  if (options.like){
    const likeLink = splitAttrs(options.like.attrs || {});
    actions.push(`<a class="actionbar-btn rate" href="${String(likeLink.href).replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')}" aria-label="Like" title="Like" data-action-menu="rate"${attrString(likeLink.attrs)}><span aria-hidden="true">${options.like.icon || '♥'}</span></a>`);
  }
  if (options.rating){
    actions.push(`<span class="actionbar-btn rate" aria-label="Rating" title="Rating"><span aria-hidden="true">${options.rating.icon || '%'}</span></span>`);
  }
  return `<div class="actionbar action_bar${options.compact ? ' actionbar--minimal' : ''}" data-action-host="1"><div class="actionbar-left">${actions.join('')}</div><div class="actionbar-right"></div>${options.menusHtml || ''}</div>`;
}

if (typeof window !== 'undefined'){
  window.MyTVHubActionBar = Object.assign(window.MyTVHubActionBar || {}, {
    ACTION_BAR_ORDER,
    WATCH_STATUS_VALUES,
    applyRuntimeContract,
    renderActionBarHtml
  });
}
