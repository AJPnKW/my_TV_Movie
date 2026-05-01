/*
FILE: web/js/watch_state_manager.js
VERSION: v1.4.0
UPDATED: 2026-04-29
CHANGE NOTES:
- Stores watched_status, watch_list, and favourite locally for offline/trailer use.
- Updates visible active states immediately after click.
- Does not require Trakt/network to respond before the UI changes.
- Keys state by item context so one card cannot toggle another item with the same local id.
*/
(function(){
  'use strict';
  const KEY='mytv_watch_state_v1';
  const TYPES = new Set(['watched_status','watch_list','favourite']);

  function load(){
    try {
      const parsed = JSON.parse(localStorage.getItem(KEY) || '{}') || {};
      return parsed && typeof parsed === 'object' ? parsed : {};
    }
    catch (_) { return {}; }
  }
  function save(data){ localStorage.setItem(KEY, JSON.stringify(data)); }
  function normalizeType(type){
    const clean = String(type || '').trim();
    return TYPES.has(clean) ? clean : '';
  }
  function contextKey(type, context){
    const cleanType = normalizeType(type);
    if (!cleanType) return '';
    const ctx = context && typeof context === 'object' ? context : { kind: String(context || '').trim().toLowerCase() };
    const kind = String(ctx.kind || '').trim().toLowerCase();
    const id = String(ctx.id || ctx.tmdb_id || ctx.movieId || ctx.showId || '').trim();
    const showId = String(ctx.showId || ctx.show || ctx.dataShow || '').trim();
    const season = String(ctx.season || ctx.seasonNumber || ctx.dataSeason || '').trim();
    const episode = String(ctx.episode || ctx.episodeNumber || ctx.dataEpisode || '').trim();
    if (showId && season && episode) return `${cleanType}:episode:${showId}:${season}:${episode}`;
    if (showId && season) return `${cleanType}:season:${showId}:${season}`;
    if (kind === 'movie' && id) return `${cleanType}:movie:${id}`;
    if (kind === 'show' && id) return `${cleanType}:show:${id}`;
    return '';
  }
  function typeFromAction(action){
    if (action === 'toggle-watch-list') return 'watch_list';
    if (action === 'toggle-watched-status') return 'watched_status';
    if (action === 'toggle-favourite' || action === 'toggle-favorite') return 'favourite';
    return '';
  }
  function get(context,type){
    const key = contextKey(type, context);
    return key ? !!load()[key] : false;
  }
  function set(context,type,value){
    const key = contextKey(type, context);
    if (!key) return false;
    const data = load();
    if (value) data[key] = true;
    else delete data[key];
    save(data);
    return !!value;
  }
  function toggle(id,type){ return set(id,type,!get(id,type)); }

  function contextKeyFromButton(btn,type){
    const cleanType = normalizeType(type);
    if (!btn || !cleanType) return '';
    const kind = String(btn.getAttribute('data-kind') || '').trim().toLowerCase();
    const id = String(btn.getAttribute('data-id') || '').trim();
    const showId = String(btn.getAttribute('data-show') || btn.getAttribute('data-status-show') || '').trim();
    const season = String(btn.getAttribute('data-season') || btn.getAttribute('data-status-season') || '').trim();
    const episode = String(btn.getAttribute('data-watch-episode') || btn.getAttribute('data-episode') || btn.getAttribute('data-status-episode') || '').trim();
    if (showId && season && episode) return `${cleanType}:episode:${showId}:${season}:${episode}`;
    if (showId && season) return `${cleanType}:season:${showId}:${season}`;
    if (kind === 'episode' || kind === 'season') return '';
    if (kind === 'movie' && id) return `${cleanType}:movie:${id}`;
    if (kind === 'show' && id) return `${cleanType}:show:${id}`;
    return '';
  }

  function getByKey(key){
    return key ? !!load()[key] : false;
  }

  function getValueByKey(key){
    if (!key) return '';
    const data = load();
    return Object.prototype.hasOwnProperty.call(data, key) ? data[key] : '';
  }

  function setByKey(key,value){
    if (!key) return false;
    const data = load();
    if (value) data[key] = true;
    else delete data[key];
    save(data);
    return !!value;
  }

  function setValueByKey(key,value){
    if (!key) return false;
    const data = load();
    if (value === false || value == null || value === '' || value === 'unwatched') delete data[key];
    else data[key] = value;
    save(data);
    return !!data[key];
  }

  function toggleByKey(key){
    return setByKey(key,!getByKey(key));
  }

  function applyButtonState(btn){
    if (!btn) return;
    const action = btn.getAttribute('data-watch-state-action');
    if (!action) return;
    const type = typeFromAction(action);
    if (!type) return;
    const key = contextKeyFromButton(btn,type);
    if (!key) return;
    const active = getByKey(key);
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    btn.setAttribute('data-watch-state-active', active ? '1' : '0');
    btn.setAttribute('data-watch-state-type', type);
    btn.setAttribute('data-watch-state-key', key);
  }

  function refresh(root){
    Array.from((root || document).querySelectorAll('[data-watch-state-action]')).forEach(applyButtonState);
  }

  document.addEventListener('click',function(e){
    const btn = e.target && e.target.closest ? e.target.closest('[data-watch-state-action]') : null;
    if (!btn) return;
    const id = btn.getAttribute('data-id');
    const action = btn.getAttribute('data-watch-state-action');
    const type = typeFromAction(action);
    if (!type) return;
    const key = contextKeyFromButton(btn,type);
    if (!key) return;
    e.preventDefault();
    e.stopPropagation();
    if (e.stopImmediatePropagation) e.stopImmediatePropagation();
    toggleByKey(key);
    applyButtonState(btn);
  }, true);

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function(){ refresh(document); });
  else refresh(document);

  window.MyTVHubWatchState = Object.assign(window.MyTVHubWatchState || {}, { load, save, get, set, toggle, getByKey, getValueByKey, setByKey, setValueByKey, toggleByKey, refresh });
})();
