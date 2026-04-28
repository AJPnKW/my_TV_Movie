/*
FILE: web/js/watch_state_manager.js
VERSION: v1.2.0
UPDATED: 2026-04-27
CHANGE NOTES:
- Stores watched_status, watch_list, and favourite locally for offline/trailer use.
- Updates visible active states immediately after click.
- Does not require Trakt/network to respond before the UI changes.
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
  function keyFor(id,type){ return type + ':' + id; }
  function normalizeType(type){
    const clean = String(type || '').trim();
    return TYPES.has(clean) ? clean : '';
  }
  function typeFromAction(action){
    if (action === 'toggle-watch-list') return 'watch_list';
    if (action === 'toggle-watched-status') return 'watched_status';
    if (action === 'toggle-favourite' || action === 'toggle-favorite') return 'favourite';
    return '';
  }
  function get(id,type){
    const cleanType = normalizeType(type);
    if (!id || !cleanType) return false;
    return !!load()[keyFor(id,cleanType)];
  }
  function set(id,type,value){
    const cleanType = normalizeType(type);
    if (!id || !cleanType) return false;
    const data = load();
    const key = keyFor(id,cleanType);
    if (value) data[key] = true;
    else delete data[key];
    save(data);
    return !!value;
  }
  function toggle(id,type){ return set(id,type,!get(id,type)); }

  function applyButtonState(btn){
    if (!btn) return;
    const id = btn.getAttribute('data-id');
    const action = btn.getAttribute('data-watch-state-action');
    if (!id || !action) return;
    const type = typeFromAction(action);
    if (!type) return;
    const active = get(id,type);
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    btn.setAttribute('data-watch-state-active', active ? '1' : '0');
    btn.setAttribute('data-watch-state-type', type);
  }

  function refresh(root){
    Array.from((root || document).querySelectorAll('[data-watch-state-action]')).forEach(applyButtonState);
  }

  document.addEventListener('click',function(e){
    const btn = e.target && e.target.closest ? e.target.closest('[data-watch-state-action]') : null;
    if (!btn) return;
    const id = btn.getAttribute('data-id');
    const action = btn.getAttribute('data-watch-state-action');
    if (!id) return;
    const type = typeFromAction(action);
    if (!type) return;
    event.preventDefault();
    event.stopPropagation();
    toggle(id,type);
    applyButtonState(btn);
  }, true);

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function(){ refresh(document); });
  else refresh(document);

  window.MyTVHubWatchState = Object.assign(window.MyTVHubWatchState || {}, { load, save, get, set, toggle, refresh });
})();
