/*
FILE: web/js/action_bar.js
VERSION: v1.5.1
UPDATED: 2026-08-11T00:00:00Z
CHANGE NOTES:
- Standardized action order: popcorn, watched_status, favourite, watch_list, rating.
- Uses Unicode text icons so buttons resize with card density and TV/browser font scaling.
- Popcorn/watch-source buttons now carry a normalized deterministic data payload where available.
- Popcorn click contract: open popup first, resolve watch-source data second.
*/

export const ACTION_BAR_ORDER = Object.freeze([
  'watch_source',
  'watched_status',
  'favourite',
  'watch_list',
  'rating'
]);

const CONTRACT_ICONS = Object.freeze({
  watch_source: '🍿',
  watched_status: '⌚',
  watch_list: '🎫',
  favourite: '💕',
  rating: ''
});

export const WATCHED_STATUS_VALUES = Object.freeze([
  'unwatched',
  'partial',
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
  root.setAttribute('data-popcorn-contract', 'open_popup_first_resolve_second');
  root.setAttribute('data-watch-state-click-contract', 'ui_local_state_queue_payload');
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

function firstValue(...values){
  for (const value of values){
    const text = String(value == null ? '' : value).trim();
    if (text) return text;
  }
  return '';
}

function normalizeWatchKind(value){
  const text = String(value || '').trim().toLowerCase();
  if (text === 'movie') return 'movie';
  if (text === 'episode') return 'episode';
  if (text === 'show' || text === 'tv') return 'tv';
  return 'movie';
}

function normalizeWatchAttrs(watchOptions = {}, attrs = {}){
  const rawKind = normalizeWatchKind(watchOptions.kind || attrs['data-kind'] || attrs['data-watch-source-open']);
  const id = firstValue(watchOptions.id, attrs['data-id'], attrs['data-tmdb-id'], attrs['data-movie-id'], attrs['data-movie-open'], attrs['data-show-id'], attrs['data-show'], attrs['data-show-open']);
  const showId = firstValue(watchOptions.showId, attrs['data-show-id'], attrs['data-show'], attrs['data-show-open'], rawKind === 'movie' ? '' : id);
  const movieId = firstValue(watchOptions.movieId, attrs['data-movie-id'], attrs['data-movie-open'], rawKind === 'movie' ? id : '');
  const season = firstValue(watchOptions.season, attrs['data-season'], attrs['data-season-number']);
  const episode = firstValue(watchOptions.episode, attrs['data-episode'], attrs['data-episode-number']);
  const normalized = {
    ...attrs,
    'data-watch-source-open': rawKind,
    'data-kind': rawKind,
    'data-popcorn-action': 'open-provider-popup',
    'data-popcorn-contract': 'open-first'
  };
  if (id) normalized['data-id'] = id;
  if (movieId) normalized['data-movie-id'] = movieId;
  if (showId) normalized['data-show-id'] = showId;
  if (showId) normalized['data-show'] = showId;
  if (season) normalized['data-season'] = season;
  if (episode) normalized['data-episode'] = episode;
  return normalized;
}

function normalizeWatchAvailabilityStatus(value){
  const valueText = String(value || '').trim().toLowerCase();
  return valueText === 'available' || valueText === 'unavailable' || valueText === 'not_yet_released' ? valueText : '';
}

function normalizeRatingText(value){
  const raw = String(value == null || value === '' ? '--' : value).trim();
  if (raw === '--') return raw;
  const numeric = raw.replace(/%/g, '').trim();
  return numeric ? `${numeric}%` : '--';
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
    left.push(renderAnchor('popcorn', watchLink.href, 'Watch sources', 'Watch sources', CONTRACT_ICONS.watch_source, normalizeWatchAttrs(options.watch, watchLink.attrs), {
      availabilityStatus: options.watch.availabilityStatus
    }));
  }

  if (options.status){
    const statusLink = splitAttrs(options.status.attrs || {});
    center.push(renderAnchor(`watched-status${options.status.active ? ' active' : ''}`, statusLink.href, 'Toggle watched status', 'Watched status', CONTRACT_ICONS.watched_status, {
      'data-watch-state-action': 'toggle-watched-status',
      'aria-pressed': options.status.active ? 'true' : 'false',
      ...statusLink.attrs
    }));
  }

  if (options.favourite){
    const favouriteLink = splitAttrs(options.favourite.attrs || {});
    center.push(renderAnchor(`favourite favorite${options.favourite.active ? ' active' : ''}`, favouriteLink.href, 'Favourite', 'Favourite', CONTRACT_ICONS.favourite, {
      'data-watch-state-action': 'toggle-favourite',
      'data-action': 'toggle-favourite',
      'data-no-default': '1',
      'aria-pressed': options.favourite.active ? 'true' : 'false',
      ...favouriteLink.attrs
    }));
  }

  if (options.watched){
    const watchedLink = splitAttrs(options.watched.attrs || {});
    center.push(renderAnchor(`watch-list${options.watched.active ? ' active' : ''}`, watchedLink.href, 'Toggle watch list', 'Watch list', CONTRACT_ICONS.watch_list, {
      'data-watch-state-action': 'toggle-watch-list',
      'data-action': 'toggle-watch-list',
      'aria-pressed': options.watched.active ? 'true' : 'false',
      ...watchedLink.attrs
    }));
  }

  const ratingText = normalizeRatingText(options.rating && options.rating.text ? options.rating.text : (options.rating && options.rating.icon ? options.rating.icon : '--'));
  right.push(`<span class="actionbar-rating" aria-label="Rating" title="Rating"><span class="actionbar-rating__text">${ratingText}</span></span>`);

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
