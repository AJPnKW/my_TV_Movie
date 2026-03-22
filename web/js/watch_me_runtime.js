import * as configLoader from './config_loader.js';
import * as dataLoader from './data_loader.js';
import * as availabilityUi from './availability_ui.js';
import * as cardRenderer from './card_renderer.js';
import * as actionBar from './action_bar.js';

cardRenderer.applyRuntimeContract(document);
actionBar.applyRuntimeContract(document);

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const state = {
  config: null,
  data: null,
  filters: {
    search: '',
    type: 'all',
    windowDays: 14
  }
};

function safeText(value) {
  return String(value ?? '').trim();
}

function esc(value) {
  return safeText(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function setStatus(ok, text) {
  $('#watchMeStatusDot')?.classList.toggle('bad', !ok);
  const label = $('#watchMeStatusText');
  if (label) label.textContent = text;
}

function toDate(value) {
  const text = safeText(value);
  if (!text) return null;
  const date = new Date(text);
  return Number.isNaN(date.getTime()) ? null : date;
}

function pad2(value) {
  return String(value).padStart(2, '0');
}

function seTag(season, episode) {
  return `S${pad2(season)}E${pad2(episode)}`;
}

function dateKey(date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

function formatDate(date) {
  return date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
}

function repoBase() {
  const parts = (location.pathname || '').split('/').filter(Boolean);
  const index = parts.indexOf('web');
  return index > 0 ? `/${parts[0]}` : '';
}

function withBasePath(path) {
  const value = safeText(path);
  if (!value) return '';
  if (/^https?:\/\//i.test(value)) return value;
  if (value.startsWith('/')) return `${repoBase()}${value}`;
  return `${repoBase()}/${value}`;
}

function tmdbImageBase() {
  return safeText(state.config?.image_cache?.tmdb_image_base || 'https://image.tmdb.org/t/p').replace(/\/+$/, '');
}

function tmdbImageUrl(path, size = 'w500') {
  const value = safeText(path);
  if (!value) return '';
  if (/^https?:\/\//i.test(value)) return value;
  if (!value.startsWith('/')) return '';
  return `${tmdbImageBase()}/${size}${value}`;
}

function pickImage(item, localKey, pathKey, size = 'w500') {
  const local = withBasePath(item?.[localKey]);
  if (local) return local;
  return tmdbImageUrl(item?.[pathKey], size);
}

function ratingPercent(item) {
  const vote = Number(item?.vote_average ?? item?.rating ?? item?.rating_percent ?? 0);
  if (!Number.isFinite(vote) || vote <= 0) return null;
  return Math.round(vote <= 10 ? vote * 10 : vote);
}

function buildActionBar(kind, item, context = {}) {
  const id = item?.tmdb_id ?? item?.id ?? context.showId ?? '';
  const watchHref = kind === 'movie'
    ? `../watch.me.html?m=${encodeURIComponent(id)}`
    : `../watch.me.html?tv=${encodeURIComponent(context.showId || id)}`;
  return actionBar.renderActionBarHtml({
    kind,
    compact: true,
    watch: (kind === 'movie' || kind === 'episode') ? { kind, attrs: { href: watchHref } } : null,
    status: { attrs: { href: '#', 'data-no-default': '1', 'data-kind': kind, 'data-id': id } },
    favourite: { attrs: { href: '#', 'data-kind': kind, 'data-id': id } },
    watched: { attrs: { href: '#', 'data-kind': kind, 'data-id': id } },
    rating: { icon: ratingPercent(item) ? `${ratingPercent(item)}%` : '%' }
  });
}

function buildEpisodeEntries() {
  const today = new Date();
  const windowEnd = new Date(today);
  windowEnd.setDate(today.getDate() + Number(state.filters.windowDays || 14));
  const shows = Array.isArray(state.data?.shows) ? state.data.shows : [];
  const entries = [];
  for (const show of shows) {
    const showTitle = safeText(show?.title || show?.name);
    for (const season of show?.seasons || []) {
      const seasonNumber = Number(season?.season_number ?? season?.number ?? 0);
      for (const episode of season?.episodes || []) {
        const airDate = toDate(episode?.air_date || episode?.first_aired);
        if (!airDate || airDate < today || airDate > windowEnd) continue;
        const title = safeText(episode?.title || episode?.name || `Episode ${episode?.episode_number}`);
        entries.push({
          type: 'episode',
          show,
          showTitle,
          seasonNumber,
          episodeNumber: Number(episode?.episode_number ?? episode?.number ?? 0),
          date: airDate,
          key: dateKey(airDate),
          title,
          episode
        });
      }
    }
  }
  return entries;
}

function buildMovieEntries() {
  const today = new Date();
  const windowEnd = new Date(today);
  windowEnd.setDate(today.getDate() + Number(state.filters.windowDays || 14));
  const movies = Array.isArray(state.data?.movies) ? state.data.movies : [];
  return movies
    .map(movie => ({ movie, date: toDate(movie?.release_date) }))
    .filter(entry => entry.date && entry.date >= today && entry.date <= windowEnd)
    .map(entry => ({
      type: 'movie',
      key: dateKey(entry.date),
      date: entry.date,
      title: safeText(entry.movie?.title || entry.movie?.name),
      movie: entry.movie
    }));
}

function matchesSearch(texts) {
  const query = safeText(state.filters.search).toLowerCase();
  if (!query) return true;
  return texts.some(text => safeText(text).toLowerCase().includes(query));
}

function renderEpisodeCard(entry) {
  const episode = entry.episode;
  const watchHref = `../watch.me.html?tv=${encodeURIComponent(entry.show?.tmdb_id ?? '')}`;
  return cardRenderer.renderCompactEpisodeCardHtml({
    image: pickImage(episode, 'still_local', 'still_path'),
    eyebrow: entry.showTitle,
    title: entry.title,
    badgeHtml: availabilityUi.availabilityBadgeHtml(episode?.availability_status, { compact: true }),
    meta: [seTag(entry.seasonNumber, entry.episodeNumber), safeText(episode?.runtime) ? `${episode.runtime} min` : '']
      .filter(Boolean)
      .join(' • '),
    submeta: formatDate(entry.date),
    overlay: true,
    actionBarHtml: buildActionBar('episode', episode, { showId: entry.show?.tmdb_id }),
    posterAttrs: {
      'data-watch-link': watchHref,
      'aria-label': `Open ${entry.showTitle} ${seTag(entry.seasonNumber, entry.episodeNumber)}`
    },
    extraClass: 'watchme-episode-card'
  });
}

function renderMovieCard(entry) {
  const movie = entry.movie;
  const watchHref = `../watch.me.html?m=${encodeURIComponent(movie?.tmdb_id ?? '')}`;
  return cardRenderer.renderCompactCardHtml({
    kind: 'movie',
    id: movie?.tmdb_id ?? '',
    image: pickImage(movie, 'poster_local', 'poster_path'),
    title: entry.title,
    badgeHtml: availabilityUi.availabilityBadgeHtml(movie?.availability_status, { compact: true }),
    meta: formatDate(entry.date),
    submeta: safeText(movie?.runtime) ? `${movie.runtime} min` : '',
    overlay: true,
    actionBarHtml: buildActionBar('movie', movie),
    posterAttrs: {
      'data-watch-link': watchHref,
      'aria-label': `Open ${entry.title}`
    },
    extraClass: 'watchme-movie-card'
  });
}

function renderGroupedSection(title, items, renderer) {
  if (!items.length) {
    return `<section class="dashblock"><div class="dashhead"><h2>${esc(title)}</h2><span class="muted">No matches</span></div></section>`;
  }
  const grouped = new Map();
  for (const item of items) {
    if (!grouped.has(item.key)) grouped.set(item.key, []);
    grouped.get(item.key).push(item);
  }
  const groups = Array.from(grouped.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  return `
    <section class="dashblock">
      <div class="dashhead"><h2>${esc(title)}</h2><span class="muted">${items.length} items</span></div>
      ${groups.map(([, groupItems]) => `
        <div class="watchme-day-group" data-date-key="${esc(groupItems[0].key)}">
          <div class="watchme-day-group__head">
            <div class="watchme-day-group__title">${esc(formatDate(groupItems[0].date))}</div>
            <div class="watchme-day-group__meta">${esc(groupItems.length === 1 ? '1 title' : `${groupItems.length} titles`)}</div>
          </div>
          <div class="watchme-row">${groupItems.map(renderer).join('')}</div>
        </div>
      `).join('')}
    </section>
  `;
}

function render() {
  const episodes = buildEpisodeEntries().filter(entry => matchesSearch([entry.showTitle, entry.title]));
  const movies = buildMovieEntries().filter(entry => matchesSearch([entry.title]));
  const type = state.filters.type;
  const sections = [];
  if (type === 'all' || type === 'episodes') sections.push(renderGroupedSection('Upcoming Episodes', episodes, renderEpisodeCard));
  if (type === 'all' || type === 'movies') sections.push(renderGroupedSection('Upcoming Movies', movies, renderMovieCard));
  $('#watchMeSections').innerHTML = sections.join('') || `<section class="dashblock"><div class="muted">No items match the current filters.</div></section>`;
  $('#watchMeSummary').textContent = `${episodes.length} episodes • ${movies.length} movies • next ${state.filters.windowDays} days`;
  $$('.watchme-episode-card [data-watch-link], .watchme-movie-card [data-watch-link]').forEach(target => {
    target.addEventListener('click', event => {
      if (event.target.closest('.actionbar')) return;
      const href = target.getAttribute('data-watch-link');
      if (href) window.location.href = href;
    });
    target.addEventListener('keydown', event => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      if (event.target.closest('.actionbar')) return;
      const href = target.getAttribute('data-watch-link');
      if (!href) return;
      event.preventDefault();
      window.location.href = href;
    });
  });
}

function bind() {
  $('#watchMeSearch')?.addEventListener('input', event => {
    state.filters.search = event.target.value || '';
    render();
  });
  $('#watchMeType')?.addEventListener('change', event => {
    state.filters.type = event.target.value || 'all';
    render();
  });
  $('#watchMeWindow')?.addEventListener('change', event => {
    state.filters.windowDays = Number(event.target.value || 14);
    render();
  });
  $('#watchMeReset')?.addEventListener('click', () => {
    state.filters = { search: '', type: 'all', windowDays: 14 };
    $('#watchMeSearch').value = '';
    $('#watchMeType').value = 'all';
    $('#watchMeWindow').value = '14';
    render();
  });
  $('#watchMeToday')?.addEventListener('click', () => {
    const today = dateKey(new Date());
    const group = document.querySelector(`.watchme-day-group[data-date-key="${today}"]`);
    if (group instanceof HTMLElement){
      group.scrollIntoView({ block: 'start', inline: 'nearest', behavior: 'smooth' });
      const firstCard = group.querySelector('[data-watch-link]');
      if (firstCard instanceof HTMLElement) firstCard.focus({ preventScroll: true });
    }
  });
}

async function init() {
  setStatus(false, 'Loading data');
  bind();
  try {
    state.config = await configLoader.loadConfigFirst(['../config.json', './config.json']);
    state.data = await dataLoader.loadCatalogFirst(['../../data/data.json', '../data/data.json', '/data/data.json']);
    render();
    setStatus(true, 'Watch Me ready');
    $('#watchMeFooter').textContent = 'Watch Me uses the shared card and action-bar modules against data/data.json.';
  } catch (error) {
    $('#watchMeSections').innerHTML = `<section class="dashblock"><div class="inline-error">${esc(error?.message || String(error))}</div></section>`;
    setStatus(false, 'Load failed');
  }
}

init();
