(function(){
  if (window.__myTvHubFocusBootLoaded) return;
  window.__myTvHubFocusBootLoaded = true;

  function loadCss(href){
    if (!href || document.querySelector('link[href="' + href + '"]')) return;
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    document.head.appendChild(link);
  }

  function loadScript(src){
    if (!src || document.querySelector('script[src="' + src + '"]')) return;
    var script = document.createElement('script');
    script.src = src;
    script.defer = true;
    document.head.appendChild(script);
  }

  loadCss('./css/runtime_layout_fix.css');
  loadScript('./js/watch_state_manager.js');
  loadScript('./js/runtime_render_fix.js');
  loadScript('./js/trailer_watch_popup_fix.js');

  function activeRoot(){
    var providerBack = document.getElementById('providerBack');
    if (providerBack && getComputedStyle(providerBack).display !== 'none' && providerBack.getAttribute('aria-hidden') !== 'true'){
      return document.getElementById('providerCard') || providerBack;
    }
    var modalBack = document.getElementById('modalBack');
    if (modalBack && getComputedStyle(modalBack).display !== 'none' && modalBack.getAttribute('aria-hidden') !== 'true'){
      return document.getElementById('modalCard') || modalBack;
    }
    return document.querySelector('.panel:not(.hidden):not([aria-hidden="true"])') || document.querySelector('main') || document.body;
  }

  function isVisible(el){
    if (!el) return false;
    var style = getComputedStyle(el);
    if (style.visibility === 'hidden' || style.display === 'none') return false;
    return el.getClientRects().length > 0;
  }

  function isTypingField(el){
    if (!el) return false;
    var tag = (el.tagName || '').toLowerCase();
    if (tag === 'textarea') return true;
    if (tag === 'input'){
      var type = (el.getAttribute('type') || 'text').toLowerCase();
      return ['button','submit','checkbox','radio','range','color'].indexOf(type) === -1;
    }
    return !!el.isContentEditable;
  }

  function getCandidates(root){
    if (!root) return [];
    return Array.from(root.querySelectorAll('a,button,input,select,textarea,[tabindex]')).filter(function(el){
      if (el.disabled || !isVisible(el)) return false;
      if (el.getAttribute('data-tv-skip') === '1') return false;
      return true;
    });
  }

  function nearestScope(el){
    if (!el) return activeRoot();
    return el.closest('.browse-sidebar, .watchme-sidebar, #modalCard, #providerCard, .panel') || activeRoot();
  }

  function redirectSkippedFocus(target){
    if (!target || target.getAttribute('data-tv-skip') !== '1') return false;
    var scope = nearestScope(target);
    var list = getCandidates(scope);
    if (!list.length) return false;
    var fallback = list[0];
    fallback.focus({ preventScroll: true });
    try { fallback.scrollIntoView({ block:'nearest', inline:'nearest', behavior:'smooth' }); } catch (_) {}
    return true;
  }

  function moveInRoot(root, dir, current){
    var list = getCandidates(root);
    if (!list.length) return false;
    var active = current || document.activeElement;
    if (!active || list.indexOf(active) === -1){
      list[0].focus({ preventScroll: true });
      try { list[0].scrollIntoView({ block:'nearest', inline:'nearest', behavior:'smooth' }); } catch (_) {}
      return true;
    }
    var from = active.getBoundingClientRect();
    var fx = from.left + from.width / 2;
    var fy = from.top + from.height / 2;
    var best = null;
    var bestScore = Infinity;
    list.forEach(function(el){
      if (el === active) return;
      var rect = el.getBoundingClientRect();
      var x = rect.left + rect.width / 2;
      var y = rect.top + rect.height / 2;
      var dx = x - fx;
      var dy = y - fy;
      if (dir === 'ArrowLeft' && dx >= -1) return;
      if (dir === 'ArrowRight' && dx <= 1) return;
      if (dir === 'ArrowUp' && dy >= -1) return;
      if (dir === 'ArrowDown' && dy <= 1) return;
      var score = Math.abs(dx) * ((dir === 'ArrowLeft' || dir === 'ArrowRight') ? 1 : 1.4) + Math.abs(dy) * ((dir === 'ArrowUp' || dir === 'ArrowDown') ? 1 : 1.4);
      if (score < bestScore){ best = el; bestScore = score; }
    });
    if (!best) return false;
    best.focus({ preventScroll: true });
    try { best.scrollIntoView({ block:'nearest', inline:'nearest', behavior:'smooth' }); } catch (_) {}
    return true;
  }

  function handleArrowKey(event){
    if (!event || ['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].indexOf(event.key) === -1) return false;
    if (event.target && event.target.getAttribute && event.target.getAttribute('data-tv-skip') === '1'){
      event.preventDefault();
      redirectSkippedFocus(event.target);
      return moveInRoot(activeRoot(), event.key, document.activeElement);
    }
    if (isTypingField(event.target)) return false;
    event.preventDefault();
    return moveInRoot(activeRoot(), event.key, document.activeElement);
  }

  window.MyTVHubFocus = Object.assign(window.MyTVHubFocus || {}, {
    activeRoot: activeRoot,
    getCandidates: getCandidates,
    handleArrowKey: handleArrowKey,
    isTypingField: isTypingField,
    moveInRoot: moveInRoot
  });

  document.addEventListener('keydown', function(event){
    if (document.body && document.body.dataset.focusGlobal === 'off') return;
    handleArrowKey(event);
  }, true);

  document.addEventListener('focusin', function(event){
    if (document.body && document.body.dataset.focusGlobal === 'off') return;
    redirectSkippedFocus(event.target);
  }, true);
  document.addEventListener('focus', function(event){
    if (document.body && document.body.dataset.focusGlobal === 'off') return;
    redirectSkippedFocus(event.target);
  }, true);
})();
