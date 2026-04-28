/*
FILE: web/js/trailer_watch_popup_fix.js
VERSION: v1.2.0
UPDATED: 2026-04-24
CHANGE NOTES:
- Opens the Watch/Popcorn provider popup immediately on weak networks and TV devices.
- Uses data/watch_sources_index.json first so the popup does not need full detail JSON for normal use.
- Shows a useful TMDB providers link immediately while local detail data loads opportunistically.
- Reduces full-detail fallback timeout so the UI does not feel frozen.
*/
(function(){
  'use strict';
  if (window.__myTvHubTrailerWatchPopupFixLoaded) return;
  window.__myTvHubTrailerWatchPopupFixLoaded = true;

  const WATCH_INDEX_TIMEOUT_MS = 1800;
  const DETAIL_TIMEOUT_MS = 1800;
  const WATCH_INDEX_URL = '/data/watch_sources_index.json';
  let watchIndexPromise = null;

  function $(selector, root){ return (root || document).querySelector(selector); }
  function text(value){ return (value == null ? '' : String(value)).trim(); }
  function escapeHtml(value){
    return text(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }
  function appBasePath(){
    const path = location.pathname || '';
    const idx = path.indexOf('/web/');
    return idx > 0 ? path.slice(0, idx) : '';
  }
  function withBase(path){
    const value = text(path);
    if (!value) return '';
    if (/^https?:\/\//i.test(value)) return value;
    if (value.startsWith('/')) return appBasePath() + value;
    return value;
  }
  function providerElements(){
    return { back: $('#providerBack'), card: $('#providerCard'), title: $('#providerTitle'), body: $('#providerBody'), close: $('#providerClose') };
  }
  function openProvider(title, html){
    const el = providerElements();
    if (!el.back || !el.body) return false;
    if (el.title) el.title.textContent = title || 'Where to watch';
    el.body.innerHTML = html || '';
    el.back.style.display = 'flex';
    el.back.setAttribute('aria-hidden', 'false');
    if (el.card) {
      el.card.scrollTop = 0;
      try { el.card.focus({ preventScroll: true }); } catch (_) { el.card.focus(); }
    }
    return true;
  }
  function closeProvider(){
    const el = providerElements();
    if (!el.back) return;
    el.back.style.display = 'none';
    el.back.setAttribute('aria-hidden', 'true');
    if (el.body) el.body.innerHTML = '';
  }
  function tmdbWatchUrl(kind, id){
    const clean = text(id);
    if (!clean) return '';
    return kind === 'movie'
      ? 'https://www.themoviedb.org/movie/' + encodeURIComponent(clean) + '/watch'
      : 'https://www.themoviedb.org/tv/' + encodeURIComponent(clean) + '/watch';
  }
  function immediateHtml(label, fallbackUrl){
    const link = fallbackUrl ? '<a class="calbtn trailer-watch-link" href="' + escapeHtml(fallbackUrl) + '" target="_blank" rel="noopener">Open TMDB providers page</a>' : '';
    return '<div class="trailer-watch-panel">' +
      '<div class="trailer-watch-title">Opening watch options…</div>' +
      '<div class="trailer-watch-note">' + escapeHtml(label || 'The popup is ready. Local watch links will appear if they load quickly.') + '</div>' +
      link +
      '</div>';
  }
  function errorHtml(label, fallbackUrl){
    const link = fallbackUrl ? '<a class="calbtn trailer-watch-link" href="' + escapeHtml(fallbackUrl) + '" target="_blank" rel="noopener">Open TMDB providers page</a>' : '';
    return '<div class="trailer-watch-panel trailer-watch-panel--warn">' +
      '<div class="trailer-watch-title">Local watch links did not load fast enough</div>' +
      '<div class="trailer-watch-note">' + escapeHtml(label || 'The external TMDB providers page is available below while local links continue to be optimized.') + '</div>' +
      link +
      '</div>';
  }
  function sourceButton(source){
    const href = text(source && source.href);
    if (!href) return '';
    const label = text(source.label || source.key || source.type || 'Watch source');
    const note = text(source.note || source.status || '');
    return '<a class="trailer-watch-source" href="' + escapeHtml(href) + '" target="_blank" rel="noopener">' +
      '<span class="trailer-watch-source__label">' + escapeHtml(label) + '</span>' +
      (note ? '<span class="trailer-watch-source__note">' + escapeHtml(note) + '</span>' : '') +
      '</a>';
  }
  function providersFromWatch(item){
    if (!item || typeof item !== 'object') return [];
    if (Array.isArray(item.providers_flat)) return item.providers_flat;
    const watch = item.watch && typeof item.watch === 'object' ? item.watch : null;
    const providers = watch && typeof watch.providers === 'object' ? watch.providers : null;
    if (!providers) return [];
    const region = providers.CA || providers.US || providers.GB || providers.AU || [];
    if (!Array.isArray(region)) return [];
    return region.slice(0, 8).map(function(provider){
      const name = text(provider.provider_name || provider.name || 'Provider');
      const logo = withBase(provider.logo_local || '');
      const tmdbLogo = provider.logo_path ? 'https://image.tmdb.org/t/p/w92' + provider.logo_path : '';
      return { name: name, logo: logo || tmdbLogo };
    });
  }
  function providerChipsHtml(item){
    const providers = providersFromWatch(item);
    if (!providers.length) return '';
    return '<div class="trailer-provider-chips">' + providers.map(function(provider){
      const img = provider.logo ? '<img src="' + escapeHtml(withBase(provider.logo)) + '" alt="" loading="lazy" decoding="async" onerror="this.remove()" />' : '';
      return '<span class="trailer-provider-chip">' + img + '<span>' + escapeHtml(provider.name || 'Provider') + '</span></span>';
    }).join('') + '</div>';
  }
  function collectSources(item){
    if (!item || typeof item !== 'object') return [];
    if (Array.isArray(item.sources)) return item.sources.filter(function(source){ return !!text(source && source.href); });
    const watch = item.watch && typeof item.watch === 'object' ? item.watch : null;
    const embeds = watch && Array.isArray(watch.embed) ? watch.embed : [];
    return embeds.map(function(entry, index){
      return { key: text(entry.key || ''), type: text(entry.type || 'external'), label: text(entry.label || entry.key || ('Source ' + (index + 1))), note: text(entry.note || entry.status || ''), href: text(entry.href || '') };
    }).filter(function(entry){ return !!entry.href; });
  }
  function renderSources(title, item, kind, id){
    const sources = collectSources(item);
    const fallback = text(item && item.tmdb_provider_url) || tmdbWatchUrl(kind === 'movie' ? 'movie' : 'tv', id);
    const buttons = sources.length ? sources.map(sourceButton).join('') : '<div class="trailer-watch-note">No direct local watch links are configured for this item yet.</div>';
    const fallbackLink = fallback ? '<a class="calbtn trailer-watch-link" href="' + escapeHtml(fallback) + '" target="_blank" rel="noopener">Open TMDB providers page</a>' : '';
    return '<div class="trailer-watch-panel">' +
      '<div class="trailer-watch-title">' + escapeHtml(title || 'Watch options') + '</div>' +
      '<div class="trailer-watch-grid">' + buttons + '</div>' +
      providerChipsHtml(item) +
      fallbackLink +
      '</div>';
  }
  async function fetchJsonWithTimeout(url, timeoutMs){
    const controller = new AbortController();
    const timeout = setTimeout(function(){ controller.abort(); }, timeoutMs);
    try {
      const response = await fetch(url, { cache: 'force-cache', signal: controller.signal });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return await response.json();
    } finally { clearTimeout(timeout); }
  }
  async function loadWatchIndex(){
    if (!watchIndexPromise) watchIndexPromise = fetchJsonWithTimeout(withBase(WATCH_INDEX_URL), WATCH_INDEX_TIMEOUT_MS).catch(function(){ return null; });
    return watchIndexPromise;
  }
  function watchIndexKeys(ctx){
    if (ctx.kind === 'movie') return ['movie:' + ctx.id];
    return ['episode:' + ctx.showId + ':' + ctx.season + ':' + ctx.episode, 'tv:' + ctx.showId];
  }
  function lookupWatchIndex(index, ctx){
    if (!index || typeof index !== 'object' || !index.items || typeof index.items !== 'object') return null;
    for (const key of watchIndexKeys(ctx)) if (index.items[key]) return index.items[key];
    return null;
  }
  async function loadDetail(id){
    const clean = text(id);
    if (!clean) return null;
    return fetchJsonWithTimeout(withBase('/data/catalog_detail/' + encodeURIComponent(clean) + '.json'), DETAIL_TIMEOUT_MS);
  }
  function findEpisode(show, seasonNumber, episodeNumber){
    const seasons = Array.isArray(show && show.seasons) ? show.seasons : [];
    const season = seasons.find(function(item){ return Number(item.season_number || item.number || item.season) === Number(seasonNumber); });
    const episodes = Array.isArray(season && season.episodes) ? season.episodes : [];
    return episodes.find(function(item){ return Number(item.episode_number || item.number || item.ep) === Number(episodeNumber); }) || null;
  }
  function contextFromButton(button){
    const kind = text(button.getAttribute('data-watch-source-open'));
    return { kind: kind, id: text(button.getAttribute('data-id')), showId: text(button.getAttribute('data-show') || button.getAttribute('data-id')), season: text(button.getAttribute('data-season')), episode: text(button.getAttribute('data-episode')) };
  }
  async function handleWatchClick(event){
    const button = event.target && event.target.closest ? event.target.closest('[data-watch-source-open]') : null;
    if (!button) return;
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();

    const ctx = contextFromButton(button);
    const isMovie = ctx.kind === 'movie';
    const detailId = isMovie ? ctx.id : ctx.showId;
    const fallback = tmdbWatchUrl(isMovie ? 'movie' : 'tv', detailId);
    openProvider('Where to watch', immediateHtml('The popup is ready. Loading local watch links now.', fallback));

    try {
      const index = await loadWatchIndex();
      const indexed = lookupWatchIndex(index, ctx);
      if (indexed) {
        openProvider(text(indexed.title || 'Watch options'), renderSources(indexed.title || 'Watch options', indexed, indexed.kind || ctx.kind, detailId));
        return;
      }
    } catch (_) {}

    try {
      const detail = await loadDetail(detailId);
      if (!detail) throw new Error('No detail data loaded');
      if (isMovie) {
        openProvider((detail.title || 'Movie') + ' • Watch options', renderSources(detail.title || 'Movie', detail, 'movie', detailId));
        return;
      }
      const episode = findEpisode(detail, ctx.season, ctx.episode);
      if (!episode) {
        openProvider((detail.title || detail.name || 'Show') + ' • Watch options', renderSources(detail.title || detail.name || 'Show', detail, 'tv', detailId));
        return;
      }
      const title = (detail.title || detail.name || 'Show') + ' • ' + (episode.title || episode.name || ('Episode ' + ctx.episode));
      openProvider(title, renderSources(title, episode, 'episode', detailId));
    } catch (_) {
      openProvider('Where to watch', errorHtml('Local watch links did not load quickly on this connection.', fallback));
    }
  }
  function installStyles(){
    if (document.getElementById('trailerWatchPopupFixStyles')) return;
    const style = document.createElement('style');
    style.id = 'trailerWatchPopupFixStyles';
    style.textContent = '' +
      '.trailer-watch-panel{display:grid;gap:12px;padding:10px;}' +
      '.trailer-watch-title{font-size:20px;font-weight:800;line-height:1.15;}' +
      '.trailer-watch-note{color:#cbd5e1;font-size:14px;line-height:1.35;}' +
      '.trailer-watch-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px;}' +
      '.trailer-watch-source{display:grid;gap:3px;padding:12px;border-radius:12px;text-decoration:none;color:#fff;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.16);}' +
      '.trailer-watch-source:focus,.trailer-watch-source:hover{outline:2px solid rgba(96,165,250,.9);background:rgba(96,165,250,.18);}' +
      '.trailer-watch-source__label{font-weight:800;}' +
      '.trailer-watch-source__note{font-size:12px;color:#cbd5e1;}' +
      '.trailer-watch-link{width:max-content;max-width:100%;}' +
      '.trailer-provider-chips{display:flex;gap:6px;flex-wrap:wrap;}' +
      '.trailer-provider-chip{display:inline-flex;align-items:center;gap:5px;max-width:170px;padding:6px 8px;border-radius:999px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);font-size:12px;}' +
      '.trailer-provider-chip img{width:20px;height:20px;object-fit:contain;border-radius:4px;background:#fff;}' ;
    document.head.appendChild(style);
  }
  function boot(){
    installStyles();
    loadWatchIndex();
    const close = $('#providerClose');
    const back = $('#providerBack');
    if (close && !close.dataset.trailerFixCloseBound) {
      close.dataset.trailerFixCloseBound = '1';
      close.addEventListener('click', closeProvider, true);
    }
    if (back && !back.dataset.trailerFixBackBound) {
      back.dataset.trailerFixBackBound = '1';
      back.addEventListener('click', function(event){ if (event.target === back) closeProvider(); }, true);
    }
    document.addEventListener('click', handleWatchClick, true);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();
