/*
FILE: web/js/watch_state_manager.js
VERSION: v1.1.0
UPDATED: 2026-04-24
CHANGE NOTES:
- Stores watch_list and watched_status locally for offline/trailer use.
- Updates visible active states immediately after click.
- Does not require Trakt/network to respond before the UI changes.
*/
(function(){
  'use strict';
  const KEY='mytv_watch_state_v1';

  function load(){
    try { return JSON.parse(localStorage.getItem(KEY) || '{}') || {}; }
    catch (_) { return {}; }
  }
  function save(data){ localStorage.setItem(KEY, JSON.stringify(data)); }
  function keyFor(id,type){ return type + ':' + id; }
  function get(id,type){ return !!load()[keyFor(id,type)]; }
  function set(id,type,value){
    const data = load();
    const key = keyFor(id,type);
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
    const type = action === 'toggle-watch-list' ? 'watch_list' : action === 'toggle-watched-status' ? 'watched_status' : '';
    if (!type) return;
    const active = get(id,type);
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    btn.setAttribute('data-watch-state-active', active ? '1' : '0');
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
    if (action === 'toggle-watch-list') toggle(id,'watch_list');
    if (action === 'toggle-watched-status') toggle(id,'watched_status');
    applyButtonState(btn);
  }, true);

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function(){ refresh(document); });
  else refresh(document);

  window.MyTVHubWatchState = Object.assign(window.MyTVHubWatchState || {}, { load, save, get, set, toggle, refresh });
})();
