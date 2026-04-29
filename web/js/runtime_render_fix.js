/*
FILE: web/js/runtime_render_fix.js
VERSION: v1.1.0
UPDATED: 2026-04-24
CHANGE NOTES:
- Post-render safety pass for all main pages.
- Normalizes image loading/decoding and prevents broken images from collapsing card layouts.
- Downshifts oversized remote TMDB images to smaller responsive sizes.
- Refreshes local watch_state button feedback after runtime renders new cards.
- Normalizes rating chips to compact percent text when older runtime markup differs.
- Prefetches small runtime indexes when the browser is idle.
- Light-prefetches provider logos and visible card stills/posters through the browser cache.
*/
(function(){
  'use strict';
  if (window.__myTvHubRuntimeRenderFixLoaded) return;
  window.__myTvHubRuntimeRenderFixLoaded = true;

  function scheduleIdle(fn){
    if ('requestIdleCallback' in window) window.requestIdleCallback(fn, { timeout: 2500 });
    else setTimeout(fn, 600);
  }

  function prefetchJson(url){
    try {
      fetch(url, { cache: 'force-cache' }).catch(function(){});
    } catch (_) {}
  }

  function prefetchSmallIndexes(){
    scheduleIdle(function(){
      prefetchJson('../data/catalog_index.json');
      prefetchJson('../data/calendar.json');
      prefetchJson('../data/watch_sources_index.json');
    });
  }

  function downshiftTmdbImage(src, img){
    if (!src || src.indexOf('image.tmdb.org/t/p/') === -1) return src;
    var isLogo = !!img.closest('.provider-chip,.trailer-provider-chip,.providerlogo');
    var target = isLogo ? 'w92' : 'w342';
    return src.replace(/\/t\/p\/(original|w1280|w780|w500|w400|w300|w200|w154|w185)\//, '/t/p/' + target + '/');
  }

  function normalizeImages(root){
    Array.from((root || document).querySelectorAll('img')).forEach(function(img){
      if (!img.getAttribute('loading')) img.setAttribute('loading','lazy');
      if (!img.getAttribute('decoding')) img.setAttribute('decoding','async');
      var src = img.getAttribute('src') || '';
      var better = downshiftTmdbImage(src, img);
      if (better && better !== src) img.setAttribute('src', better);
      if (!img.getAttribute('sizes')) img.setAttribute('sizes', '(max-width: 700px) 45vw, 220px');
      img.addEventListener('error', function(){
        img.classList.add('image-load-failed');
        if (!img.closest('.provider-chip,.trailer-provider-chip')) img.style.visibility = 'hidden';
      }, { once:true });
    });
  }

  function normalizeRatings(root){
    Array.from((root || document).querySelectorAll('.actionbar-rating__text,.iconstrip-pct')).forEach(function(el){
      var raw = String(el.textContent || '').replace(/^\u2605/,'').trim();
      if (raw && raw !== '--' && raw.indexOf('%') === -1) raw = raw + '%';
      el.textContent = raw;
    });
  }

  function prefetchImage(src){
    if (!src) return;
    try {
      var img = new Image();
      img.decoding = 'async';
      img.loading = 'eager';
      img.src = src;
    } catch (_) {}
  }

  function prefetchRuntimeImages(root){
    scheduleIdle(function(){
      var scope = root || document;
      var selector = [
        '.provider-chip img',
        '.trailer-provider-chip img',
        '.providerlogo img',
        '.dashblock img',
        '.calendar-day img',
        '.calendar-tree-day img'
      ].join(',');
      Array.from(scope.querySelectorAll(selector)).slice(0, 80).forEach(function(img){
        prefetchImage(img.currentSrc || img.getAttribute('src') || '');
      });
    });
  }

  function refreshWatchState(root){
    if (window.MyTVHubWatchState && typeof window.MyTVHubWatchState.refresh === 'function'){
      window.MyTVHubWatchState.refresh(root || document);
    }
  }

  function run(root){
    normalizeImages(root || document);
    normalizeRatings(root || document);
    refreshWatchState(root || document);
    prefetchRuntimeImages(root || document);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function(){ run(document); prefetchSmallIndexes(); });
  else { run(document); prefetchSmallIndexes(); }

  var target = document.getElementById('appMain') || document.body;
  if (target && window.MutationObserver){
    var pending = false;
    new MutationObserver(function(){
      if (pending) return;
      pending = true;
      setTimeout(function(){ pending = false; run(target); }, 80);
    }).observe(target, { childList:true, subtree:true });
  }
})();
