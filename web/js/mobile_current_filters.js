(() => {
  'use strict';

  const page = document.body?.dataset?.page || '';
  if (!['shows', 'movies'].includes(page)) return;

  let enabled = false;
  let currentIds = new Set();
  let dataLoaded = false;

  const dateValue = value => {
    const parsed = Date.parse(String(value || ''));
    return Number.isFinite(parsed) ? parsed : null;
  };

  const itemId = item => String(item?.tmdb_id ?? item?.id ?? '');

  function isCurrentShow(show, now) {
    const first = dateValue(show?.first_air_date);
    if (first && first > now) return false;
    const status = String(show?.status || '').toLowerCase();
    if (['ended', 'canceled', 'cancelled'].includes(status)) return false;

    const recentCutoff = now - (548 * 24 * 60 * 60 * 1000); // 18 months
    const last = dateValue(show?.last_air_date || show?.latest_episode_to_air?.air_date);
    const next = dateValue(show?.next_episode_to_air?.air_date);
    return Boolean(
      (next && next >= now - (30 * 24 * 60 * 60 * 1000)) ||
      (last && last >= recentCutoff) ||
      ['returning series', 'in production', 'planned', 'pilot'].includes(status)
    );
  }

  function isCurrentMovie(movie, now) {
    const release = dateValue(movie?.release_date);
    if (!release) return false;
    const recentCutoff = now - (548 * 24 * 60 * 60 * 1000); // 18 months
    const nearFuture = now + (30 * 24 * 60 * 60 * 1000);
    return release >= recentCutoff && release <= nearFuture;
  }

  async function loadCurrentIds() {
    try {
      const response = await fetch('../data/data.json', { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      const now = Date.now();
      const items = page === 'shows' ? (payload.shows || []) : (payload.movies || []);
      currentIds = new Set(items.filter(item => page === 'shows' ? isCurrentShow(item, now) : isCurrentMovie(item, now)).map(itemId).filter(Boolean));
    } catch (error) {
      console.warn('[current-filter] data load failed', error);
      currentIds = new Set();
    } finally {
      dataLoaded = true;
      applyFilter();
    }
  }

  function getCardId(card) {
    const trigger = card.querySelector(page === 'shows' ? '[data-show-open]' : '[data-movie-open]');
    if (trigger) return String(trigger.getAttribute(page === 'shows' ? 'data-show-open' : 'data-movie-open') || '');
    return String(card.getAttribute(page === 'shows' ? 'data-show-id' : 'data-movie-id') || card.dataset.tmdbId || '');
  }

  function cards() {
    const triggerSelector = page === 'shows' ? '[data-show-open]' : '[data-movie-open]';
    const found = new Set();
    document.querySelectorAll(triggerSelector).forEach(trigger => {
      const card = trigger.closest('.media-card, article, .card, .show-card, .movie-card');
      if (card) found.add(card);
    });
    return [...found];
  }

  function applyFilter() {
    if (!dataLoaded) return;
    let visible = 0;
    cards().forEach(card => {
      const show = !enabled || currentIds.has(getCardId(card));
      card.classList.toggle('current-filter-hidden', !show);
      if (show) visible += 1;
    });

    const result = document.querySelector('.browse-count, .result-count, [data-result-count]');
    if (result && enabled) result.textContent = `${visible} current results`;
  }

  function filterHost() {
    const scopeId = page === 'shows' ? '#filterShowsScope' : '#filterMoviesScope';
    return document.querySelector(scopeId) || document.querySelector('.browse-sidebar .segrow, .browse-filters .segrow, .filter-panel .segrow, .browse-sidebar');
  }

  function ensureButton() {
    if (document.querySelector('[data-current-filter]')) return;
    const host = filterHost();
    if (!host) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'current-filter-btn';
    button.dataset.currentFilter = page;
    button.setAttribute('aria-pressed', 'false');
    button.textContent = 'CURRENT';
    button.title = page === 'shows'
      ? 'Shows airing now or active within the last 18 months'
      : 'Movies released within the last 18 months';
    button.addEventListener('click', () => {
      enabled = !enabled;
      button.classList.toggle('active', enabled);
      button.setAttribute('aria-pressed', enabled ? 'true' : 'false');
      applyFilter();
    });
    host.appendChild(button);
  }

  function ensureMobileSearchVisible() {
    const expected = page === 'shows' ? '#filterShowsSearch' : '#filterMoviesSearch';
    const input = document.querySelector(expected) || document.querySelector('input[type="search"], .browse-sidebar input, .browse-filters input');
    if (input) {
      input.hidden = false;
      input.removeAttribute('aria-hidden');
      input.style.removeProperty('display');
      input.style.removeProperty('visibility');
    }
  }

  let scheduled = false;
  const refresh = () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      ensureButton();
      ensureMobileSearchVisible();
      applyFilter();
    });
  };

  const observer = new MutationObserver(refresh);
  observer.observe(document.documentElement, { childList: true, subtree: true });
  window.addEventListener('resize', refresh, { passive: true });
  document.addEventListener('DOMContentLoaded', refresh, { once: true });
  refresh();
  loadCurrentIds();
})();
