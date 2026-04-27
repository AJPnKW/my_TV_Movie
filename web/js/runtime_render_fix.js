/*
FILE: web/js/runtime_render_fix.js
VERSION: v1.0.0
UPDATED: 2026-04-24
CHANGE NOTES:
- Post-render safety pass for all main pages.
- Normalizes image loading/decoding and prevents broken images from collapsing card layouts.
- Refreshes local watch_state button feedback after runtime renders new cards.
- Removes visible percent symbols from rating chips if older runtime markup still emits them.
*/
(function(){
  'use strict';
  if (window.__myTvHubRuntimeRenderFixLoaded) return;
  window.__myTvHubRuntimeRenderFixLoaded = true;

  function normalizeImages(root){
    Array.from((root || document).querySelectorAll('img')).forEach(function(img){
      if (!img.getAttribute('loading')) img.setAttribute('loading','lazy');
      if (!img.getAttribute('decoding')) img.setAttribute('decoding','async');
      img.addEventListener('error', function(){
        img.classList.add('image-load-failed');
        if (!img.closest('.provider-chip,.trailer-provider-chip')) img.style.visibility = 'hidden';
      }, { once:true });
    });
  }

  function normalizeRatings(root){
    Array.from((root || document).querySelectorAll('.actionbar-rating__text,.iconstrip-pct')).forEach(function(el){
      el.textContent = String(el.textContent || '').replace(/%/g,'').trim();
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
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function(){ run(document); });
  else run(document);

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
