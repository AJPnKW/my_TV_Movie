/*
FILE: web/js/watch_state_manager.js
VERSION: v2.0.0
UPDATED: 2026-04-30
CHANGE NOTES:
- Stores local-first watch_state records with sync/validation metadata.
- watched_status is tri-state: unwatched -> partial -> watched -> unwatched.
- Every valid action-bar or Manage Watch State click creates/updates a local queue event.
- Trakt network is not required for immediate UI updates.
*/
(function(){
  'use strict';

  const KEY = 'mytv_watch_state_v1';
  const QUEUE_KEY = 'mytv_watch_sync_queue_v1';
  const TYPES = new Set(['watched_status','watch_list','favourite']);
  const WATCHED_VALUES = ['unwatched','partial','watched'];
  const BINARY_VALUES = ['off','on'];
  const SYNC_STATUS_VALUES = ['local_only','queued','synced','mismatch','missing_id','validation_issue','auth_required','failed'];

  function nowIso(){ return new Date().toISOString(); }
  function safeText(value){ return String(value == null ? '' : value).trim(); }

  function loadRaw(){
    try {
      const parsed = JSON.parse(localStorage.getItem(KEY) || '{}') || {};
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
    } catch (_) {
      return {};
    }
  }

  function save(data){ localStorage.setItem(KEY, JSON.stringify(data)); }

  function loadQueue(){
    try {
      const parsed = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]') || [];
      if (Array.isArray(parsed)) return parsed;
      if (parsed && typeof parsed === 'object' && Array.isArray(parsed.items)) return parsed.items;
      return [];
    } catch (_) {
      return [];
    }
  }

  function saveQueue(queue){ localStorage.setItem(QUEUE_KEY, JSON.stringify(queue)); }

  function normalizeType(type){
    const clean = safeText(type);
    return TYPES.has(clean) ? clean : '';
  }

  function itemTypeForKind(kind){
    const clean = safeText(kind).toLowerCase();
    if (clean === 'movie') return 'movie';
    if (clean === 'episode') return 'episode';
    if (clean === 'season') return 'season';
    if (clean === 'show' || clean === 'tv') return 'show';
    return clean;
  }

  function normalizeValue(type, value){
    const cleanType = normalizeType(type);
    if (cleanType === 'watched_status'){
      const text = safeText(value).toLowerCase();
      return WATCHED_VALUES.includes(text) ? text : (value === true ? 'watched' : 'unwatched');
    }
    const text = safeText(value).toLowerCase();
    if (BINARY_VALUES.includes(text)) return text;
    return value === true ? 'on' : 'off';
  }

  function valueOf(record, type){
    const cleanType = normalizeType(type);
    if (record && typeof record === 'object' && !Array.isArray(record)){
      return normalizeValue(cleanType, record.new_value);
    }
    if (cleanType === 'watched_status'){
      if (record === true) return 'watched';
      return normalizeValue(cleanType, record);
    }
    return record ? 'on' : 'off';
  }

  function parseKey(key){
    const parts = safeText(key).split(':');
    const stateType = normalizeType(parts[0]);
    const itemType = itemTypeForKind(parts[1]);
    if (!stateType || !itemType) return null;
    if (itemType === 'episode' && parts.length >= 5){
      return { state_type: stateType, item_type: 'episode', show_id: parts[2], season_number: parts[3], episode_number: parts[4], tmdb_id: parts[2] };
    }
    if (itemType === 'season' && parts.length >= 4){
      return { state_type: stateType, item_type: 'season', show_id: parts[2], season_number: parts[3], tmdb_id: parts[2] };
    }
    if ((itemType === 'movie' || itemType === 'show') && parts.length >= 3){
      return { state_type: stateType, item_type: itemType, tmdb_id: parts[2], show_id: itemType === 'show' ? parts[2] : '' };
    }
    return null;
  }

  function contextKey(type, context){
    const cleanType = normalizeType(type);
    if (!cleanType) return '';
    const ctx = context && typeof context === 'object' ? context : { kind: safeText(context).toLowerCase() };
    const kind = itemTypeForKind(ctx.kind || ctx.item_type);
    const id = safeText(ctx.id || ctx.tmdb_id || ctx.movieId || ctx.showId);
    const showId = safeText(ctx.showId || ctx.show_id || ctx.show || ctx.dataShow || (kind === 'show' ? id : ''));
    const season = safeText(ctx.season || ctx.seasonNumber || ctx.season_number || ctx.dataSeason);
    const episode = safeText(ctx.episode || ctx.episodeNumber || ctx.episode_number || ctx.dataEpisode);
    if (kind === 'episode' && showId && season && episode) return `${cleanType}:episode:${showId}:${season}:${episode}`;
    if (kind === 'season' && showId && season) return `${cleanType}:season:${showId}:${season}`;
    if (kind === 'movie' && id) return `${cleanType}:movie:${id}`;
    if (kind === 'show' && (showId || id)) return `${cleanType}:show:${showId || id}`;
    if (showId && season && episode) return `${cleanType}:episode:${showId}:${season}:${episode}`;
    return '';
  }

  function typeFromAction(action){
    if (action === 'toggle-watch-list') return 'watch_list';
    if (action === 'toggle-watched-status') return 'watched_status';
    if (action === 'toggle-favourite' || action === 'toggle-favorite') return 'favourite';
    return '';
  }

  function contextFromButton(btn, type){
    const kind = itemTypeForKind(btn.getAttribute('data-kind') || btn.getAttribute('data-item-type') || '');
    const showId = safeText(btn.getAttribute('data-show') || btn.getAttribute('data-status-show') || btn.getAttribute('data-show-id'));
    const season = safeText(btn.getAttribute('data-season') || btn.getAttribute('data-status-season') || btn.getAttribute('data-season-number'));
    const episode = safeText(btn.getAttribute('data-watch-episode') || btn.getAttribute('data-episode') || btn.getAttribute('data-status-episode') || btn.getAttribute('data-episode-number'));
    const tmdbAttr = safeText(btn.getAttribute('data-tmdb-id'));
    const id = safeText(btn.getAttribute('data-id') || tmdbAttr || btn.getAttribute('data-movie-id') || (kind === 'episode' ? showId : ''));
    return {
      kind,
      id,
      tmdb_id: tmdbAttr || (kind === 'episode' ? '' : id || showId),
      trakt_id: safeText(btn.getAttribute('data-trakt-id')),
      imdb_id: safeText(btn.getAttribute('data-imdb-id')),
      tvdb_id: safeText(btn.getAttribute('data-tvdb-id')),
      showId,
      seasonNumber: season,
      episodeNumber: episode,
      title: safeText(btn.getAttribute('data-title')),
      release_status: safeText(btn.getAttribute('data-release-status') || btn.getAttribute('data-watch-availability')),
      state_type: normalizeType(type)
    };
  }

  function contextKeyFromButton(btn, type){
    if (!btn) return '';
    return contextKey(type, contextFromButton(btn, type));
  }

  function validationFor(key, context, nextValue){
    const parsed = parseKey(key);
    if (!parsed) return { sync_status: 'validation_issue', validation_status: 'validation_issue', sync_error: 'missing item key' };
    const contextTmdb = safeText(context?.tmdb_id);
    const contextTrakt = safeText(context?.trakt_id);
    const contextImdb = safeText(context?.imdb_id);
    const contextTvdb = safeText(context?.tvdb_id);
    const hasAnyExternalId = !!(contextTmdb || contextTrakt || contextImdb || contextTvdb || parsed.tmdb_id);
    if (!hasAnyExternalId && parsed.item_type !== 'season'){
      return { sync_status: 'missing_id', validation_status: 'missing_id', sync_error: 'missing tmdb_id' };
    }
    if (parsed.item_type === 'episode' && !contextTmdb && !contextTrakt && !contextTvdb){
      return { sync_status: 'validation_issue', validation_status: 'validation_issue', sync_error: 'missing episode ID; title-only matching is forbidden' };
    }
    if (parsed.item_type === 'episode' && (!parsed.show_id || !parsed.season_number || !parsed.episode_number)){
      return { sync_status: 'validation_issue', validation_status: 'validation_issue', sync_error: 'missing show_id/season_number/episode_number' };
    }
    const releaseStatus = safeText(context?.release_status).toLowerCase();
    if (parsed.state_type === 'watched_status' && nextValue === 'watched' && (releaseStatus === 'not_yet_released' || releaseStatus === 'unreleased')){
      return { sync_status: 'validation_issue', validation_status: 'validation_issue', sync_error: 'unreleased movie/episode cannot become watched' };
    }
    return { sync_status: 'queued', validation_status: 'ok', sync_error: '' };
  }

  function buildRecord(key, nextValue, context = {}, previousValue = ''){
    const parsed = parseKey(key) || {};
    const stateType = parsed.state_type || normalizeType(context.state_type);
    const value = normalizeValue(stateType, nextValue);
    const validation = validationFor(key, context, value);
    const itemType = parsed.item_type || itemTypeForKind(context.kind);
    return {
      item_key: key,
      item_type: itemType,
      tmdb_id: safeText(context.tmdb_id || (itemType === 'episode' ? '' : parsed.tmdb_id)),
      trakt_id: safeText(context.trakt_id),
      imdb_id: safeText(context.imdb_id),
      tvdb_id: safeText(context.tvdb_id),
      show_id: safeText(context.showId || context.show_id || parsed.show_id),
      season_number: safeText(context.seasonNumber || context.season_number || parsed.season_number),
      episode_number: safeText(context.episodeNumber || context.episode_number || parsed.episode_number),
      state_type: stateType,
      previous_value: normalizeValue(stateType, previousValue),
      new_value: value,
      changed_at: nowIso(),
      sync_status: validation.sync_status,
      validation_status: validation.validation_status,
      sync_error: validation.sync_error
    };
  }

  function queueRecordFromStateRecord(record){
    if (!record || typeof record !== 'object') return null;
    const id = safeText(record.item_key || record.key || record.state_key || record.id);
    if (!id) return null;
    const mediaType = itemTypeForKind(record.item_type || record.media_type);
    const queueRecord = {
      id,
      media_type: mediaType,
      state_type: normalizeType(record.state_type),
      previous_value: normalizeValue(record.state_type, record.previous_value),
      new_value: normalizeValue(record.state_type, record.new_value),
      ids: {
        trakt: safeText(record.trakt_id || record.ids?.trakt),
        tmdb: safeText(record.tmdb_id || record.ids?.tmdb),
        imdb: safeText(record.imdb_id || record.ids?.imdb),
        tvdb: safeText(record.tvdb_id || record.ids?.tvdb)
      },
      show: {
        season: safeText(record.season_number || record.show?.season),
        episode: safeText(record.episode_number || record.show?.episode)
      },
      changed_at: safeText(record.changed_at) || nowIso(),
      sync_status: safeText(record.sync_status) || 'queued',
      validation_status: safeText(record.validation_status) || 'ok',
      error: safeText(record.sync_error || record.error),
      item_key: id,
      item_type: mediaType,
      tmdb_id: safeText(record.tmdb_id || record.ids?.tmdb),
      trakt_id: safeText(record.trakt_id || record.ids?.trakt),
      show_id: safeText(record.show_id || record.showId),
      season_number: safeText(record.season_number || record.show?.season),
      episode_number: safeText(record.episode_number || record.show?.episode),
      key: id,
      state_key: id,
      queue_status: safeText(record.sync_status) === 'queued' ? 'pending' : safeText(record.sync_status || 'queued')
    };
    return queueRecord;
  }

  function postQueueRecord(record){
    if (!record || typeof fetch !== 'function') return;
    fetch('http://127.0.0.1:8787/api/watch-state-queue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ record })
    }).catch(() => {});
  }

  function upsertQueue(record){
    const queueRecord = queueRecordFromStateRecord(record);
    if (!queueRecord) return;
    const queue = loadQueue().filter(item => !(safeText(item.item_key || item.key || item.state_key || item.id) === queueRecord.id && safeText(item.state_type) === queueRecord.state_type));
    queue.push(queueRecord);
    saveQueue(queue);
    postQueueRecord(queueRecord);
  }

  function load(){
    return loadRaw();
  }

  function get(context,type){
    const key = contextKey(type, context);
    return key ? getByKey(key) : false;
  }

  function getValue(context,type){
    const key = contextKey(type, context);
    return key ? getValueByKey(key) : normalizeValue(type, '');
  }

  function set(context,type,value){
    const key = contextKey(type, context);
    return setValueByKey(key, normalizeValue(type, value), { ...(context || {}), state_type: type });
  }

  function toggle(context,type){
    const key = contextKey(type, context);
    return toggleByKey(key, context);
  }

  function getByKey(key){
    const parsed = parseKey(key);
    const value = getValueByKey(key);
    return parsed?.state_type === 'watched_status' ? value !== 'unwatched' : value === 'on';
  }

  function getValueByKey(key){
    const parsed = parseKey(key);
    if (!parsed) return '';
    return valueOf(loadRaw()[key], parsed.state_type);
  }

  function setByKey(key,value,context = {}){
    const parsed = parseKey(key);
    const next = parsed?.state_type === 'watched_status' ? (value ? 'watched' : 'unwatched') : (value ? 'on' : 'off');
    return setValueByKey(key, next, context);
  }

  function setValueByKey(key,value,context = {}){
    const parsed = parseKey(key);
    if (!parsed) return false;
    const data = loadRaw();
    const previous = valueOf(data[key], parsed.state_type);
    const next = normalizeValue(parsed.state_type, value);
    const record = buildRecord(key, next, { ...context, state_type: parsed.state_type }, previous);
    if (record.sync_status === 'validation_issue' || record.validation_status === 'validation_issue'){
      data[key] = { ...record, new_value: previous };
    } else if (parsed.state_type === 'watched_status' && next === 'unwatched'){
      data[key] = record;
    } else if (parsed.state_type !== 'watched_status' && next === 'off'){
      data[key] = record;
    } else {
      data[key] = record;
    }
    save(data);
    upsertQueue(data[key]);
    return getByKey(key);
  }

  function nextValueForKey(key){
    const parsed = parseKey(key);
    if (!parsed) return '';
    const current = getValueByKey(key);
    if (parsed.state_type === 'watched_status'){
      const idx = WATCHED_VALUES.indexOf(current);
      return WATCHED_VALUES[(idx + 1) % WATCHED_VALUES.length];
    }
    return current === 'on' ? 'off' : 'on';
  }

  function toggleByKey(key,context = {}){
    const next = nextValueForKey(key);
    if (!next) return false;
    return setValueByKey(key, next, context);
  }

  function applyButtonState(btn){
    if (!btn) return;
    const action = btn.getAttribute('data-watch-state-action');
    if (!action) return;
    const type = typeFromAction(action);
    if (!type) return;
    const key = contextKeyFromButton(btn,type);
    if (!key) return;
    const value = getValueByKey(key);
    const active = type === 'watched_status' ? value !== 'unwatched' : value === 'on';
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    btn.setAttribute('data-watch-state-active', active ? '1' : '0');
    btn.setAttribute('data-watch-state-type', type);
    btn.setAttribute('data-watch-state-key', key);
    btn.setAttribute('data-watch-state-value', value);
    const icon = btn.querySelector('.actionbar-btn__icon');
    if (icon){
      const nextIcon = type === 'watched_status'
        ? (value === 'watched' ? '✓' : value === 'partial' ? '◐' : '⌚')
        : type === 'watch_list'
          ? (value === 'on' ? '🎟' : '🎫')
          : (value === 'on' ? '💕' : '♡');
      icon.textContent = nextIcon;
      btn.setAttribute('data-watch-state-icon', nextIcon);
    }
  }

  function refresh(root){
    Array.from((root || document).querySelectorAll('[data-watch-state-action]')).forEach(applyButtonState);
  }

  document.addEventListener('click',function(e){
    const btn = e.target && e.target.closest ? e.target.closest('[data-watch-state-action]') : null;
    if (!btn) return;
    const action = btn.getAttribute('data-watch-state-action');
    const type = typeFromAction(action);
    if (!type) return;
    const context = contextFromButton(btn, type);
    const key = contextKey(type, context);
    if (!key) return;
    e.preventDefault();
    e.stopPropagation();
    if (e.stopImmediatePropagation) e.stopImmediatePropagation();
    toggleByKey(key, context);
    refresh(document);
    document.dispatchEvent(new CustomEvent('mytv:watch-state-changed', { detail: { key, state_type: type, value: getValueByKey(key) } }));
  }, true);

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function(){ refresh(document); });
  else refresh(document);

  window.MyTVHubWatchState = Object.assign(window.MyTVHubWatchState || {}, {
    TYPES: Array.from(TYPES),
    WATCHED_VALUES,
    BINARY_VALUES,
    SYNC_STATUS_VALUES,
    load,
    save,
    loadQueue,
    saveQueue,
    contextKey,
    contextKeyFromButton,
    parseKey,
    get,
    getValue,
    set,
    toggle,
    getByKey,
    getValueByKey,
    setByKey,
    setValueByKey,
    toggleByKey,
    refresh
  });
})();
