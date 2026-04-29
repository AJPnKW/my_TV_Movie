/*
FILE: web/js/ui_contract_fix.js
VERSION: v1.1.0
UPDATED: 2026-04-27
PURPOSE:
- Compatibility shim for legacy rendered nodes after repeated drift.
- Canonical icon/action rendering is owned by action_bar.js.
- This only repairs stale nodes and lazy image sizing after render.
*/
(function(){
  'use strict';
  if (window.__myTvHubUiContractFixLoaded) return;
  window.__myTvHubUiContractFixLoaded = true;

  const ICONS = {
    popcorn: '🍿',
    watch: '⌚',
    ticket: '🎫',
    doubleHeart: '💕'
  };

  function text(v){ return (v == null ? '' : String(v)).trim(); }

  function setIcon(el, icon, cls){
    if (!el) return;
    el.classList.add('ui-contract-icon-host');
    if (cls) el.classList.add(cls);
    const span = el.querySelector('.actionbar-btn__icon,.ui-contract-icon') || el;
    span.textContent = icon;
    span.classList.add('ui-contract-icon');
  }

  function classifyActionButton(el){
    const cls = text(el.className).toLowerCase();
    const label = text(el.getAttribute('aria-label') || el.getAttribute('title')).toLowerCase();
    const action = text(el.getAttribute('data-watch-state-action') || el.getAttribute('data-action') || el.getAttribute('data-action-menu')).toLowerCase();
    const watchSource = el.hasAttribute('data-watch-source-open');

    if (watchSource || cls.includes('popcorn') || label.includes('watch sources')) return 'popcorn';
    if (action.includes('watched-status') || action.includes('watched_status') || cls.includes('watched-status')) return 'watch';
    if (action.includes('watch-list') || action.includes('watch_list') || cls.includes('watch-list')) return 'ticket';
    if (action.includes('favourite') || action.includes('favorite') || cls.includes('favorite') || cls.includes('favourite')) return 'doubleHeart';
    return '';
  }

  function normalizeActionBars(root){
    const scope = root || document;
    const selectors = [
      '.actionbar-btn',
      '.iconstrip a',
      '.iconstrip button',
      '.card-actions a',
      '.card-actions button',
      '.media-actions a',
      '.media-actions button',
      '[data-watch-source-open]',
      '[data-watch-state-action]'
    ].join(',');

    Array.from(scope.querySelectorAll(selectors)).forEach(function(el){
      const kind = classifyActionButton(el);
      if (kind === 'popcorn') {
        setIcon(el, ICONS.popcorn, 'ui-popcorn');
      } else if (kind === 'watch') {
        setIcon(el, ICONS.watch, 'ui-watch-toggle');
      } else if (kind === 'ticket') {
        setIcon(el, ICONS.ticket, 'ui-ticket-toggle');
      } else if (kind === 'doubleHeart') {
        setIcon(el, ICONS.doubleHeart, 'ui-double-heart');
      }
    });

    Array.from(scope.querySelectorAll('.actionbar-rating__star,.iconstrip-star')).forEach(function(el){
      el.textContent = '';
      el.setAttribute('aria-hidden','true');
    });

    Array.from(scope.querySelectorAll('.actionbar-rating__text,.iconstrip-pct')).forEach(function(el){
      let raw = text(el.textContent).replace(/^\u2605/,'').trim();
      if (raw && raw !== '--' && !raw.includes('%')) raw = raw + '%';
      el.textContent = raw;
    });
  }

  function normalizeImages(root){
    Array.from((root || document).querySelectorAll('img')).forEach(function(img){
      if (!img.getAttribute('loading')) img.setAttribute('loading','lazy');
      if (!img.getAttribute('decoding')) img.setAttribute('decoding','async');
      const src = img.getAttribute('src') || '';
      if (src.includes('image.tmdb.org/t/p/')) {
        const isLogo = !!img.closest('.provider-chip,.trailer-provider-chip,.providerlogo');
        const target = isLogo ? 'w92' : 'w342';
        const next = src.replace(/\/t\/p\/(original|w1280|w780|w500|w400|w300|w200|w185|w154|w92)\//, '/t/p/' + target + '/');
        if (next !== src) img.setAttribute('src', next);
      }
    });
  }

  function refreshWatchState(root){
    if (window.MyTVHubWatchState && typeof window.MyTVHubWatchState.refresh === 'function') {
      window.MyTVHubWatchState.refresh(root || document);
    }
  }

  function run(root){
    normalizeActionBars(root || document);
    normalizeImages(root || document);
    refreshWatchState(root || document);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function(){ run(document); });
  } else {
    run(document);
  }

  const target = document.getElementById('appMain') || document.body;
  if (target && window.MutationObserver) {
    let pending = false;
    new MutationObserver(function(){
      if (pending) return;
      pending = true;
      setTimeout(function(){
        pending = false;
        run(target);
      }, 60);
    }).observe(target, { childList:true, subtree:true });
  }
})();
