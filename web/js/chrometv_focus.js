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

  function injectStyle(id, css){
    if (document.getElementById(id)) return;
    var style = document.createElement('style');
    style.id = id;
    style.textContent = css;
    document.head.appendChild(style);
  }

  loadCss('./css/runtime_layout_fix.css');
  loadCss('./css/ui_contract_fix.css');
  loadScript('./js/watch_state_manager.js');
  loadScript('./js/runtime_render_fix.js');
  loadScript('./js/trailer_watch_popup_fix.js');
  loadScript('./js/ui_contract_fix.js');

  injectStyle('mytv-direct-ui-contract-style', `
    :root{
      --app-sticky-top: 76px;
      --nav-icon-size: clamp(26px, 3.4vw, 38px);
      --nav-icon-glyph: clamp(18px, 2.6vw, 28px);
      --ui-action-box: clamp(21px, 2.4vw, 28px);
    }

    .top{
      min-height: 56px !important;
      padding: 6px 10px !important;
      gap: 10px !important;
      position: sticky !important;
      top: 0 !important;
      z-index: 100 !important;
      overflow: visible !important;
    }

    .brand{
      flex: 0 0 auto !important;
      min-width: 0 !important;
      max-width: 112px !important;
      overflow: hidden !important;
      align-self: center !important;
    }

    .logo{
      display: inline-flex !important;
      align-items: center !important;
      justify-content: flex-start !important;
      width: 96px !important;
      max-width: 96px !important;
      height: 44px !important;
      max-height: 44px !important;
      padding: 0 !important;
      border: 0 !important;
      border-radius: 0 !important;
      background: transparent !important;
      box-shadow: none !important;
      overflow: hidden !important;
    }

    .logo img,
    .brand .logo img{
      display: block !important;
      height: 44px !important;
      max-height: 44px !important;
      width: auto !important;
      max-width: 96px !important;
      object-fit: contain !important;
      object-position: left center !important;
      aspect-ratio: auto !important;
      transform: none !important;
    }

    .logo_txt{ display:none !important; }

    .nav{
      flex: 1 1 auto !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      gap: clamp(7px, 1.2vw, 14px) !important;
      min-width: 0 !important;
      flex-wrap: nowrap !important;
      overflow-x: auto !important;
      scrollbar-width: none !important;
    }

    .nav::-webkit-scrollbar{ display:none !important; }

    .nav .tab,
    .nav .tab:link,
    .nav .tab:visited{
      width: var(--nav-icon-size) !important;
      height: var(--nav-icon-size) !important;
      min-width: var(--nav-icon-size) !important;
      min-height: var(--nav-icon-size) !important;
      padding: 0 !important;
      border: 0 !important;
      border-radius: 10px !important;
      background: transparent !important;
      box-shadow: none !important;
      color: #dbeafe !important;
      font-size: var(--nav-icon-glyph) !important;
      line-height: 1 !important;
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
      text-decoration: none !important;
      overflow: visible !important;
    }

    .nav .tab.active,
    .nav .tab[aria-current="page"]{
      background: rgba(59,130,246,.18) !important;
      color: #93c5fd !important;
      text-shadow: 0 0 12px rgba(96,165,250,.75) !important;
      outline: 1px solid rgba(147,197,253,.22) !important;
      outline-offset: 2px !important;
    }

    .nav .tab:hover,
    .nav .tab:focus-visible{
      background: rgba(148,163,184,.12) !important;
      outline: 2px solid rgba(147,197,253,.50) !important;
      outline-offset: 2px !important;
    }

    .nav .tab[data-tab="watch-me"],
    .nav .tab[data-tab="discover"]{
      display: none !important;
    }

    .status{
      flex: 0 0 auto !important;
      padding: 6px 10px !important;
      min-height: 34px !important;
      max-height: 42px !important;
    }

    .actionbar{
      border: 0 !important;
      background: transparent !important;
      box-shadow: none !important;
      padding: 0 !important;
      margin-top: 6px !important;
      gap: 5px !important;
      overflow: visible !important;
      display: flex !important;
      align-items: center !important;
    }

    .actionbar-left,
    .actionbar-center,
    .actionbar-right{
      display: inline-flex !important;
      align-items: center !important;
      gap: 5px !important;
      flex-wrap: nowrap !important;
      overflow: visible !important;
      min-width: 0 !important;
    }

    .actionbar-btn,
    .media-card .actionbar-btn,
    .episode-row .actionbar-btn,
    .calendar-item .actionbar-btn,
    .watchme-episode-card .actionbar-btn,
    .watchme-movie-card .actionbar-btn,
    .popup-episode-card .actionbar-btn{
      width: var(--ui-action-box) !important;
      height: var(--ui-action-box) !important;
      min-width: var(--ui-action-box) !important;
      min-height: var(--ui-action-box) !important;
      max-width: var(--ui-action-box) !important;
      max-height: var(--ui-action-box) !important;
      border-radius: 8px !important;
      aspect-ratio: 1 / 1 !important;
      padding: 0 !important;
      background: rgba(71,85,105,.92) !important;
      border: 1px solid rgba(148,163,184,.38) !important;
      box-shadow: none !important;
      overflow: visible !important;
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
      line-height: 1 !important;
    }

    .actionbar-btn__icon{ font-size: calc(var(--ui-action-box) * .72) !important; line-height: 1 !important; }
    .actionbar-rating{ min-width: 28px !important; font-size: clamp(11px, 1.2vw, 14px) !important; padding: 0 2px !important; }

    .section-sticky-header,
    .dashhead{
      position: sticky !important;
      top: var(--app-sticky-top) !important;
      z-index: 45 !important;
      background: linear-gradient(180deg, rgba(15,22,32,.98), rgba(15,22,32,.92)) !important;
      backdrop-filter: blur(8px) !important;
      border-radius: 12px !important;
      padding: 7px 8px !important;
      margin: 0 0 8px 0 !important;
    }
  `);

  function iconForTab(tab){
    return {
      'dashboard': '⌂',
      'shows': '▤',
      'movies': '▣',
      'watch-me': '◉',
      'calendar': '□',
      'discover': '⌕',
      'config': '⚙',
      'inputs-editor': '✎',
      'manage-watch-state': '☑'
    }[tab] || '•';
  }

  function labelForTab(tab, fallback){
    return {
      'dashboard': 'Dashboard',
      'shows': 'Shows',
      'movies': 'Movies',
      'watch-me': 'Watch Me (deprecated)',
      'calendar': 'Calendar',
      'discover': 'Discover (deprecated)',
      'config': 'Config',
      'inputs-editor': 'Inputs Editor',
      'manage-watch-state': 'Manage Watch State'
    }[tab] || fallback || tab || 'Navigation';
  }

  function normalizeTopNav(){
    var nav = document.querySelector('.top .nav');
    if (!nav) return;

    Array.from(nav.querySelectorAll('.tab')).forEach(function(tab){
      var id = tab.getAttribute('data-tab') || '';
      var label = labelForTab(id, tab.textContent.trim());
      tab.setAttribute('aria-label', label);
      tab.setAttribute('title', label);
      tab.textContent = iconForTab(id);
    });

    if (!nav.querySelector('[data-tab="manage-watch-state"]')){
      var manage = document.createElement('a');
      manage.className = 'tab';
      manage.setAttribute('data-tab', 'manage-watch-state');
      manage.setAttribute('href', './manage_watch_state.html');
      manage.setAttribute('role', 'tab');
      manage.setAttribute('aria-label', 'Manage Watch State');
      manage.setAttribute('title', 'Manage Watch State');
      manage.textContent = iconForTab('manage-watch-state');
      nav.insertBefore(manage, nav.querySelector('[data-tab="config"]') || null);
    }

    var page = (document.body && document.body.getAttribute('data-page')) || '';
    Array.from(nav.querySelectorAll('.tab')).forEach(function(tab){
      var id = tab.getAttribute('data-tab') || '';
      var isActive = id === page || (page === 'dashboard' && id === 'dashboard') || (page === 'manage-watch-state' && id === 'manage-watch-state');
      tab.classList.toggle('active', isActive);
      if (isActive) tab.setAttribute('aria-current', 'page');
      else tab.removeAttribute('aria-current');
    });
  }

  function normalizeLogo(){
    var logo = document.querySelector('.brand .logo');
    if (!logo) return;
    var img = logo.querySelector('img');
    if (!img){
      img = document.createElement('img');
      img.src = '../assets/custom/the_boys_hub_logo2.png';
      img.alt = 'The Boys Hub';
      logo.textContent = '';
      logo.appendChild(img);
    }
    img.setAttribute('loading', 'eager');
    img.setAttribute('decoding', 'async');
  }

  function applyDirectUiContract(){
    normalizeLogo();
    normalizeTopNav();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', applyDirectUiContract);
  else applyDirectUiContract();
  window.addEventListener('pageshow', applyDirectUiContract);

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
    moveInRoot: moveInRoot,
    applyDirectUiContract: applyDirectUiContract
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
