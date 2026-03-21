(function(){
  function activeRoot(){
    var providerBack = document.getElementById('providerBack');
    if (providerBack && getComputedStyle(providerBack).display !== 'none'){
      return document.getElementById('providerCard') || providerBack;
    }
    var modalBack = document.getElementById('modalBack');
    if (modalBack && getComputedStyle(modalBack).display !== 'none'){
      return document.getElementById('modalCard') || modalBack;
    }
    return document.querySelector('.panel:not(.hidden)') || document.querySelector('main') || document.body;
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
    if (tag === 'textarea' || tag === 'select') return true;
    if (tag === 'input'){
      var type = (el.getAttribute('type') || 'text').toLowerCase();
      return ['button','submit','checkbox','radio','range','color'].indexOf(type) === -1;
    }
    return !!el.isContentEditable;
  }

  function getCandidates(root){
    if (!root) return [];
    return Array.from(root.querySelectorAll('a,button,input,select,textarea,[tabindex]')).filter(function(el){
      return !el.disabled && isVisible(el);
    });
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
      var score = Math.abs(dx) * ((dir === 'ArrowLeft' || dir === 'ArrowRight') ? 1 : 1.4) +
        Math.abs(dy) * ((dir === 'ArrowUp' || dir === 'ArrowDown') ? 1 : 1.4);
      if (score < bestScore){
        best = el;
        bestScore = score;
      }
    });
    if (!best) return false;
    best.focus({ preventScroll: true });
    try { best.scrollIntoView({ block:'nearest', inline:'nearest', behavior:'smooth' }); } catch (_) {}
    return true;
  }

  function handleArrowKey(event){
    if (!event || ['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].indexOf(event.key) === -1) return false;
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
})();
