/*
FILE: web/js/ui_contract_fix.js
VERSION: v1.0.0
UPDATED: 2026-04-27
PURPOSE:
- Enforce icon contract after repeated drift.
- Correct order/icon meanings: popcorn, watch, ticket, double-heart, compact rating.
- Remove rating star icon.
- Improve D-pad/back behavior without changing app runtime.
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
      el.textContent = text(el.textContent).replace(/%/g,'').replace(/^★/,'').trim();
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

  function activeOverlay(){
    const provider = document.getElementById('providerBack');
    if (provider && provider.getAttribute('aria-hidden') !== 'true' && getComputedStyle(provider).display !== 'none') {
      return document.getElementById('providerCard') || provider;
    }
    const modal = document.getElementById('modalBack');
    if (modal && modal.getAttribute('aria-hidden') !== 'true' && getComputedStyle(modal).display !== 'none') {
      return document.getElementById('modalCard') || modal;
    }
    return null;
  }

  function closeTopOverlay(){
    const overlay = activeOverlay();
    if (!overlay) return false;
    const close = overlay.querySelector('button[id$="Close"], .calbtn, button');
    if (close) close.click();
    else {
      const back = overlay.closest('.app-modal-backdrop') || overlay;
      back.style.display = 'none';
      back.setAttribute('aria-hidden','true');
    }
    return true;
  }

  function focusables(root){
    return Array.from((root || document).querySelectorAll('a,button,input,select,textarea,[tabindex]'))
      .filter(function(el){
        if (el.disabled) return false;
        if (el.getAttribute('data-tv-skip') === '1') return false;
        const style = getComputedStyle(el);
        return style.display !== 'none' && style.visibility !== 'hidden' && el.getClientRects().length;
      });
  }

  function moveFocus(dir){
    const root = activeOverlay() || document.querySelector('.panel:not(.hidden)') || document.querySelector('main') || document.body;
    const items = focusables(root);
    if (!items.length) return false;
    const active = document.activeElement;
    if (!items.includes(active)) {
      items[0].focus({preventScroll:true});
      items[0].scrollIntoView({block:'nearest', inline:'nearest'});
      return true;
    }

    const ar = active.getBoundingClientRect();
    const ax = ar.left + ar.width / 2;
    const ay = ar.top + ar.height / 2;
    let best = null;
    let bestScore = Infinity;

    for (const el of items) {
      if (el === active) continue;
      const r = el.getBoundingClientRect();
      const x = r.left + r.width / 2;
      const y = r.top + r.height / 2;
      const dx = x - ax;
      const dy = y - ay;
      if (dir === 'ArrowLeft' && dx >= -2) continue;
      if (dir === 'ArrowRight' && dx <= 2) continue;
      if (dir === 'ArrowUp' && dy >= -2) continue;
      if (dir === 'ArrowDown' && dy <= 2) continue;
      const score = Math.abs(dx) + Math.abs(dy) * 1.25;
      if (score < bestScore) {
        best = el;
        bestScore = score;
      }
    }

    if (!best) return false;
    best.focus({preventScroll:true});
    best.scrollIntoView({block:'nearest', inline:'nearest'});
    return true;
  }

  function run(root){
    normalizeActionBars(root || document);
    normalizeImages(root || document);
    refreshWatchState(root || document);
  }

  document.addEventListener('keydown', function(event){
    if (event.key === 'Escape' || event.key === 'Backspace' || event.key === 'BrowserBack') {
      if (closeTopOverlay()) {
        event.preventDefault();
        event.stopPropagation();
      }
      return;
    }

    if (['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)) {
      const tag = (event.target && event.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || (event.target && event.target.isContentEditable)) return;
      if (moveFocus(event.key)) {
        event.preventDefault();
        event.stopPropagation();
      }
    }
  }, true);

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
