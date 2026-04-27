/*
FILE: web/js/action_bar.js
VERSION: v1.2.0
UPDATED: 2026-04-24T00:00:00Z
CHANGE NOTES:
- Standardized action order: popcorn, watched_status, watch_list, favourite, rating.
- Uses Unicode text icons so buttons resize with card density and TV/browser font scaling.
- Renamed ambiguous bookmark/status concepts to watch_list and watched_status in data attributes.
- Removes percent sign from rating text to save horizontal card space.
*/

export const ACTION_BAR_ORDER = Object.freeze([
  'watch_source',
  'watched_status',
  'watch_list',
  'favourite',
  'rating'
]);

const CONTRACT_ICONS = Object.freeze({
  watch_source: '🍿',
  watched_status: '▶',
  watch_list: '🎟',
  favourite: '💛',
  rating: '★'
});

export const WATCHED_STATUS_VALUES = Object.freeze([
  'unwatched',
  'watched'
]);

export const WATCH_LIST_VALUES = Object.freeze([
  'off',
  'on'
]);

export function applyRuntimeContract(doc = document){
  const root = doc.documentElement;
  if (!root) return;
  root.setAttribute('data-action-bar-order', ACTION_BAR_ORDER.join(','));
  root.setAttribute('data-watched-status-values', WATCHED_STATUS_VALUES.join(','));
  root.setAttribute('data-watch-list-values', WATCH_LIST_VALUES.join(','));
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
  const valueText = String(value || '').trim().toLowerCase();
  return valueText === 'available' || valueText === 'unavailable' || valueText === 'not_yet_released' ? valueText : '';
}

function normalizeRatingText(value){
  const raw = String(value == null || value === '' ? '--' : value).trim();
  return raw.replace(/%/g, '');
}

function renderAnchor(cls, href, label, title, icon, attrs = {}, options = {}){
  const availabilityStatus = cls === 'popcorn' ? normalizeWatchAvailabilityStatus(options.availabilityStatus) : '';
  const availabilityAttr = availabilityStatus ? ` data-watch-availability="${escAttr(availabilityStatus)}"` : '';
  return `<a class="actionbar-btn ${cls}" href="${escAttr(href)}" aria-label="${escAttr(label)}" title="${escAttr(title)}"${availabilityAttr}${attrString(attrs)}><span class="actionbar-btn__icon" aria-hidden="true">${icon}</span></a>`;
}

export function renderActionBarHtml(options = {}){
  const left = [];
  const center = [];
  const right = [];

  if (options.watch){
    const watchLink = splitAttrs(options.watch.attrs || {});
    left.push(renderAnchor('popcorn', watchLink.href, 'Watch sources', 'Watch sources', CONTRACT_ICONS.watch_source, {
      'data-watch-source-open': options.watch.kind || 'movie',
      ...watchLink.attrs
    }, {
      availabilityStatus: options.watch.availabilityStatus
    }));
  }

  if (options.status){
    const statusLink = splitAttrs(options.status.attrs || {});
    center.push(renderAnchor('watched-status', statusLink.href, 'Toggle watched status', 'Watched status', CONTRACT_ICONS.watched_status, {
      'data-watch-state-action': 'toggle-watched-status',
      'data-action-menu': 'watched_status',
      'data-no-default': '1',
      ...statusLink.attrs
    }));
  }

  if (options.watched){
    const watchedLink = splitAttrs(options.watched.attrs || {});
    center.push(renderAnchor(`watch-list${options.watched.active ? ' active' : ''}`, watchedLink.href, 'Toggle watch list', 'Watch list', CONTRACT_ICONS.watch_list, {
      'data-watch-state-action': 'toggle-watch-list',
      'data-action': 'toggle-watch-list',
      ...watchedLink.attrs
    }));
  }

  if (options.favourite){
    const favouriteLink = splitAttrs(options.favourite.attrs || {});
    center.push(renderAnchor(`favorite${options.favourite.active ? ' active' : ''}`, favouriteLink.href, 'Favourite', 'Favourite', CONTRACT_ICONS.favourite, {
      'data-action': 'toggle-favourite',
      ...favouriteLink.attrs
    }));
  }

  const ratingText = normalizeRatingText(options.rating && options.rating.text ? options.rating.text : (options.rating && options.rating.icon ? options.rating.icon : '--'));
  right.push(`<span class="actionbar-rating" aria-label="Rating" title="Rating"><span class="actionbar-rating__star" aria-hidden="true">${CONTRACT_ICONS.rating}</span><span class="actionbar-rating__text">${ratingText}</span></span>`);

  return `<div class="actionbar action_bar${options.compact ? ' actionbar--minimal' : ''}" data-action-host="1" data-action-order="${ACTION_BAR_ORDER.join(',')}">
    <div class="actionbar-left">${left.join('')}</div>
    <div class="actionbar-center">${center.join('')}</div>
    <div class="actionbar-right">${right.join('')}</div>
    ${options.menusHtml || ''}
  </div>`;
}

if (typeof window !== 'undefined'){
  window.MyTVHubActionBar = Object.assign(window.MyTVHubActionBar || {}, {
    ACTION_BAR_ORDER,
    WATCHED_STATUS_VALUES,
    WATCH_LIST_VALUES,
    applyRuntimeContract,
    renderActionBarHtml
  });
}
