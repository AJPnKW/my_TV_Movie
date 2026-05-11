/*
FILE: web/js/provider_popup_guard.js
VERSION: v1.0.0
UPDATED: 2026-05-08
CHANGE NOTES:
- Runtime guard for popcorn/watch-source popup behavior.
- Suppresses provider registry/admin notes/status text from public popup rendering.
- Filters blocked/archived providers before display.
- Provides a local fallback popup when the main runtime click handler fails.
- Keeps provider UI simple: provider names only for active providers.
*/
(function(){
  'use strict';
  if (window.__myTvMovieProviderPopupGuardLoaded) return;
  window.__myTvMovieProviderPopupGuardLoaded = true;

  const PROVIDER_REGISTRY_URL = './data/provider_registry.json';
  const WATCH_SOURCE_INDEX_URL = './data/watch_sources_index.json';
  const BLOCKED_STATUSES = new Set(['blocked', 'archived']);
  const NAME_ONLY_SELECTOR = '.trailer-watch-source__note,.provider-note,.provider-status,.watch-provider-note,.watch-provider-status,[data-provider-note],[data-provider-status]';
  const registryPromise = fetchJson(PROVIDER_REGISTRY_URL).catch(() => null);
  const sourceIndexPromise = fetchJson(WATCH_SOURCE_INDEX_URL).catch(() => null);

  function text(value){ return value == null ? '' : String(value).trim(); }
  function lower(value){ return text(value).toLowerCase(); }
  function esc(value){
    return text(value)
      .replaceAll('&','&amp;')
      .replaceAll('<','&lt;')
      .replaceAll('>','&gt;')
      .replaceAll('"','&quot;')
      .replaceAll("'",'&#39;');
  }
  function fetchJson(path){
    return fetch(path, { cache: 'no-cache' }).then(response => {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.json();
    });
  }
  function normalizeDomain(value){
    const raw = text(value);
    if (!raw) return '';
    try {
      const url = raw.includes('://') ? new URL(raw) : new URL('https://' + raw);
      return url.hostname.replace(/^www\./i, '').toLowerCase();
    } catch (_) {
      return raw.replace(/^https?:\/\//i, '').replace(/^www\./i, '').split('/')[0].toLowerCase();
    }
  }
  function registryItems(registry){
    if (!registry) return [];
    if (Array.isArray(registry)) return registry;
    if (Array.isArray(registry.providers)) return registry.providers;
    if (Array.isArray(registry.items)) return registry.items;
    if (registry.providers && typeof registry.providers === 'object') return Object.values(registry.providers);
    return [];
  }
  function providerByDomain(registry, hrefOrDomain){
    const domain = normalizeDomain(hrefOrDomain);
    if (!domain) return null;
    return registryItems(registry).find(item => {
      const itemDomain = normalizeDomain(item.domain || item.provider_domain || item.url || item.href || item.url_pattern || item.provider_id);
      return itemDomain && (domain === itemDomain || domain.endsWith('.' + itemDomain));
    }) || null;
  }
  function providerStatus(registry, hrefOrDomain){
    const item = providerByDomain(registry, hrefOrDomain);
    return lower(item && item.status) || 'unknown';
  }
  function isProviderAllowed(registry, href){
    const status = providerStatus(registry, href);
    return !BLOCKED_STATUSES.has(status);
  }
  function labelFromSource(source){
    return text(source.label || source.name || source.provider_name || source.provider_id || source.key || 'Watch source');
  }
  function hrefFromSource(source){
    return text(source.href || source.url || source.link || source.embed_url || '');
  }
  function sourceListFromIndex(index, context){
    if (!index) return [];
    const items = index.items || index.sources || index;
    const keys = [];
    if (context.mediaType === 'movie' && context.tmdbId) keys.push('movie:' + context.tmdbId);
    if (context.showId && context.season && context.episode) keys.push('episode:' + context.showId + ':' + context.season + ':' + context.episode);
    if (context.tmdbId && context.season && context.episode) keys.push('episode:' + context.tmdbId + ':' + context.season + ':' + context.episode);
    if (context.showId) keys.push('tv:' + context.showId);
    if (context.tmdbId) keys.push('tv:' + context.tmdbId);
    for (const key of keys){
      const found = items && items[key];
      if (found){
        if (Array.isArray(found)) return found;
        if (Array.isArray(found.sources)) return found.sources;
        if (found.watch && Array.isArray(found.watch.embed)) return found.watch.embed;
      }
    }
    return [];
  }
  function getContext(button){
    const host = button.closest('[data-tmdb-id],[data-id],[data-show-id],[data-show],[data-movie-id],[data-season],[data-episode],.media-card,.episode-card,.episode-row,.calendar-item,.watchme-item') || button;
    const attr = names => {
      for (const name of names){
        const value = text(button.getAttribute(name) || host.getAttribute(name));
        if (value) return value;
      }
      return '';
    };
    const season = attr(['data-season','data-season-number']);
    const episode = attr(['data-episode','data-episode-number']);
    const movieId = attr(['data-movie-id','data-movie-open']);
    const showId = attr(['data-show-id','data-show','data-show-open']);
    const tmdbId = movieId || showId || attr(['data-tmdb-id','data-id']);
    return {
      mediaType: movieId ? 'movie' : (season && episode ? 'episode' : 'tv'),
      tmdbId,
      movieId,
      showId: showId || (!movieId ? tmdbId : ''),
      season,
      episode,
      title: text(button.getAttribute('aria-label') || button.getAttribute('title') || host.getAttribute('aria-label') || host.getAttribute('title') || 'Watch now')
    };
  }
  function isPopcornTarget(target){
    const el = target && target.closest ? target.closest('button,a,[role="button"],.actionbar-btn') : null;
    if (!el) return null;
    const marker = lower(el.getAttribute('data-watch-source-open') || el.getAttribute('data-action') || el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent);
    if (marker.includes('🍿') || marker.includes('watch source') || marker.includes('where to watch') || marker.includes('watch now') || marker.includes('provider')) return el;
    if (el.classList && (el.classList.contains('popcorn') || el.classList.contains('watch-source'))) return el;
    return null;
  }
  function ensurePopupShell(){
    let back = document.getElementById('providerBack');
    if (back) return back;
    back = document.createElement('div');
    back.id = 'providerBack';
    back.className = 'app-modal-backdrop app-modal-backdrop--provider';
    back.setAttribute('aria-hidden', 'true');
    back.setAttribute('role', 'dialog');
    back.setAttribute('aria-modal', 'true');
    back.innerHTML = '<div id="providerCard" class="app-modal-card app-modal-card--provider" tabindex="0"><div class="app-modal-header"><div id="providerTitle" class="app-modal-title">Watch now</div><button id="providerClose" class="calbtn" type="button">Close</button></div><div id="providerBody" class="app-modal-body"></div></div>';
    document.body.appendChild(back);
    return back;
  }
  function openPopup(html){
    const back = ensurePopupShell();
    const title = document.getElementById('providerTitle');
    const body = document.getElementById('providerBody');
    const card = document.getElementById('providerCard');
    if (title) title.textContent = 'Watch now';
    if (body) body.innerHTML = html;
    back.style.display = 'flex';
    back.setAttribute('aria-hidden', 'false');
    setTimeout(cleanProviderPopup, 0);
    if (card) {
      try { card.focus({ preventScroll: true }); } catch (_) { card.focus(); }
    }
  }
  function providerButton(source){
    const href = hrefFromSource(source);
    if (!href) return '';
    const label = labelFromSource(source);
    return '<a class="trailer-watch-source provider-popup-link" href="' + esc(href) + '" target="_blank" rel="noopener"><span class="trailer-watch-source__label">' + esc(label) + '</span></a>';
  }
  function fallbackProviderButtons(context){
    const tvPath = context.season && context.episode ? '/' + encodeURIComponent(context.season) + '/' + encodeURIComponent(context.episode) : '';
    const ids = context.mediaType === 'movie' ? '/movie/' + encodeURIComponent(context.tmdbId || '') : '/tv/' + encodeURIComponent(context.showId || context.tmdbId || '') + tvPath;
    const sources = [];
    if (context.tmdbId || context.showId){
      sources.push({ label: 'VidSrc', href: 'https://vidsrc.net/embed' + ids });
      sources.push({ label: '2Embed CC', href: context.mediaType === 'movie'
        ? 'https://www.2embed.cc/embed/' + encodeURIComponent(context.tmdbId || '')
        : 'https://www.2embed.cc/embedtv/' + encodeURIComponent(context.showId || context.tmdbId || '') + (context.season && context.episode ? '&s=' + encodeURIComponent(context.season) + '&e=' + encodeURIComponent(context.episode) : '') });
    }
    return sources;
  }
  async function handlePopcornClick(event){
    const button = isPopcornTarget(event.target);
    if (!button) return;
    const context = getContext(button);
    const [registry, index] = await Promise.all([registryPromise, sourceIndexPromise]);
    let sources = sourceListFromIndex(index, context);
    if (!sources.length) sources = fallbackProviderButtons(context);
    const allowed = sources.filter(source => {
      const href = hrefFromSource(source);
      return href && isProviderAllowed(registry, href);
    });
    if (!allowed.length) return;
    event.preventDefault();
    event.stopPropagation();
    if (event.stopImmediatePropagation) event.stopImmediatePropagation();
    const html = '<div class="trailer-watch-panel"><div class="trailer-watch-grid">' + allowed.map(providerButton).join('') + '</div></div>';
    openPopup(html);
  }
  function cleanProviderPopup(){
    const body = document.getElementById('providerBody');
    if (!body) return;
    body.querySelectorAll(NAME_ONLY_SELECTOR).forEach(node => node.remove());
    const forbiddenTexts = ['active candidate from user findings', 'active', 'degraded', 'blocked', 'archived'];
    Array.from(body.querySelectorAll('span,div,p,small')).forEach(node => {
      const value = lower(node.textContent);
      if (forbiddenTexts.includes(value)) node.remove();
    });
  }
  function installCloseHandlers(){
    document.addEventListener('click', event => {
      if (event.target && event.target.id === 'providerClose') {
        const back = document.getElementById('providerBack');
        const body = document.getElementById('providerBody');
        if (back) {
          back.style.display = 'none';
          back.setAttribute('aria-hidden', 'true');
        }
        if (body) body.innerHTML = '';
      }
    }, true);
  }
  function installObserver(){
    const observer = new MutationObserver(cleanProviderPopup);
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }
  function install(){
    installCloseHandlers();
    installObserver();
    document.addEventListener('click', handlePopcornClick, true);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true });
  else install();
})();
