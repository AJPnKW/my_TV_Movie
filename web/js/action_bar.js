/*
FILE: web/js/action_bar.js
VERSION: v1.1.0
UPDATED: 2026-03-21T00:00:00Z
CHANGE NOTES:
- Enforced shared left/center/right action strip contract.
- Standardized glyphs toward popcorn / watch-status / favourites / bookmark / star+percent.
*/

export const ACTION_BAR_ORDER = Object.freeze([
  'watch',
  'status',
  'favourite',
  'bookmark',
  'rating'
]);

const CONTRACT_ICONS = Object.freeze({
  watch: '🍿',
  status: '⌚',
  favourite: '💕',
  bookmark: '🔖',
  star: '★'
});

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

function escAttr(v){
  return String(v)
    .replaceAll('&', '&amp;')
    .replaceAll('"', '&quot;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function attrString(attrs = {}){
  return Object.entries(attrs)
    .filter(([, value]) => value != null && value !== '')
    .map(([key, value]) => ` ${String(key)}="${escAttr(value)}"`)
    .join('');
}

function splitAttrs(attrs = {}){
  const next = { ...attrs };
  const href = next.href || '#';
  delete next.href;
  return { href, attrs: next };
}

function normalizeWatchAvailabilityStatus(value){
  const text = String(value || '').trim().toLowerCase();
  return text === 'available' || text === 'unavailable' || text === 'not_yet_released' ? text : '';
}

function renderAnchor(cls, href, label, title, icon, attrs = {}, options = {}){
  const availabilityStatus = cls === 'popcorn' ? normalizeWatchAvailabilityStatus(options.availabilityStatus) : '';
  const availabilityAttr = availabilityStatus ? ` data-watch-availability="${escAttr(availabilityStatus)}"` : '';
  const iconHtml = cls === 'popcorn'
    ? `<span class="actionbar-btn__glyph actionbar-btn__glyph--watch${availabilityStatus ? ` actionbar-btn__glyph--${availabilityStatus}` : ''}" aria-hidden="true"><span class="actionbar-btn__icon">${icon}</span></span>`
    : `<span aria-hidden="true">${icon}</span>`;
  return `<a class="actionbar-btn ${cls}" href="${escAttr(href)}" aria-label="${escAttr(label)}" title="${escAttr(title)}"${availabilityAttr}${attrString(attrs)}>${iconHtml}</a>`;
}

export function renderActionBarHtml(options = {}){
  const left = [];
  const center = [];
  const right = [];

  if (options.watch){
    const watchLink = splitAttrs(options.watch.attrs || {});
    left.push(renderAnchor('popcorn', watchLink.href, 'Watch source', 'Watch source', CONTRACT_ICONS.watch, {
      'data-watch-source-open': options.watch.kind || 'movie',
      ...watchLink.attrs
    }, {
      availabilityStatus: options.watch.availabilityStatus
    }));
  }
  if (options.status){
    const statusLink = splitAttrs(options.status.attrs || {});
    center.push(renderAnchor('status', statusLink.href, 'Watch status', 'Watch status', CONTRACT_ICONS.status, {
      'data-action-menu': 'status',
      'data-no-default': '1',
      ...statusLink.attrs
    }));
  }
  if (options.favourite){
    const favouriteLink = splitAttrs(options.favourite.attrs || {});
    center.push(renderAnchor(`favorite${options.favourite.active ? ' active' : ''}`, favouriteLink.href, 'Favourite', 'Favourite', CONTRACT_ICONS.favourite, {
      'data-action': 'toggle-want',
      ...favouriteLink.attrs
    }));
  }
  if (options.watched){
    const watchedLink = splitAttrs(options.watched.attrs || {});
    center.push(renderAnchor(`bookmark${options.watched.active ? ' active' : ''}`, watchedLink.href, 'Bookmark', 'Bookmark', CONTRACT_ICONS.bookmark, {
      'data-action': 'toggle-watched',
      ...watchedLink.attrs
    }));
  }
  const ratingText = (options.rating && options.rating.text) ? options.rating.text : (options.rating && options.rating.icon ? options.rating.icon : '--%');
  right.push(`<span class="actionbar-rating" aria-label="Rating" title="Rating"><span class="actionbar-rating__star" aria-hidden="true">${CONTRACT_ICONS.star}</span><span class="actionbar-rating__text">${ratingText}</span></span>`);

  return `<div class="actionbar action_bar${options.compact ? ' actionbar--minimal' : ''}" data-action-host="1">
    <div class="actionbar-left">${left.join('')}</div>
    <div class="actionbar-center">${center.join('')}</div>
    <div class="actionbar-right">${right.join('')}</div>
    ${options.menusHtml || ''}
  </div>`;
}

if (typeof window !== 'undefined'){
  window.MyTVHubActionBar = Object.assign(window.MyTVHubActionBar || {}, {
    ACTION_BAR_ORDER,
    WATCH_STATUS_VALUES,
    applyRuntimeContract,
    renderActionBarHtml
  });
}
