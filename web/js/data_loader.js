/*
FILE: web/js/data_loader.js
VERSION: v1.1.0
UPDATED: 2026-04-24T00:00:00Z
CHANGE NOTES:
- Centralized shared catalog and inputs loading for the normalized main app runtime.
- Added in-memory caching to reduce repeated parse/load work across rebased views.
- Added fallback calendar derivation from data/data.json when data/calendar.json is empty.
*/

import { loadJsonFirst } from './config_loader.js';

let catalogIndexPromise = null;
let calendarPromise = null;
let discoverRegistryPromise = null;
let inputsPromise = null;
const detailPromises = new Map();

function safeText(value){
  return (value == null ? '' : String(value)).trim();
}

function safeInt(value, fallback = 0){
  const parsed = Number.parseInt(String(value ?? '').trim(), 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function hasCalendarDays(calendar){
  return !!(
    calendar &&
    typeof calendar === 'object' &&
    calendar.days &&
    typeof calendar.days === 'object' &&
    Object.keys(calendar.days).length > 0
  );
}

function firstNetwork(show){
  const networks = Array.isArray(show && show.networks) ? show.networks : [];
  return networks.find(item => item && typeof item === 'object') || {};
}

function hasWatchSources(entity){
  const sources = Array.isArray(entity && entity.watch_sources) ? entity.watch_sources : [];
  const watch = entity && typeof entity.watch === 'object' ? entity.watch : null;
  const embeds = Array.isArray(watch && watch.embed) ? watch.embed : [];
  return sources.length > 0 || embeds.length > 0;
}

function episodeEntry(show, season, episode){
  const dateKey = safeText(episode.air_date).slice(0, 10);
  const network = firstNetwork(show);
  const showId = safeInt(show.tmdb_id || show.id);
  return {
    kind: 'episode',
    date: dateKey,
    episode_tmdb_id: safeInt(episode.id || episode.tmdb_id || episode.episode_tmdb_id),
    episode_trakt_id: safeText(episode.trakt_id),
    episode_tvdb_id: safeText(episode.tvdb_id),
    show_id: showId,
    show_tmdb_id: showId,
    show_title: safeText(show.title || show.name),
    show_poster_local: safeText(show.poster_local),
    show_backdrop_local: safeText(show.backdrop_local),
    season_number: safeInt(episode.season_number || season.season_number || season.number),
    episode_number: safeInt(episode.episode_number || episode.number),
    episode_name: safeText(episode.name || episode.title),
    runtime: episode.runtime || null,
    thumb: safeText(episode.still_local || season.poster_local || show.poster_local || show.backdrop_local),
    still_local: safeText(episode.still_local),
    still_path: safeText(episode.still_path),
    network_name: safeText(network.name),
    network_logo_tmdb: safeText(network.logo_path),
    progress: episode.vote_average != null ? Math.round(Number(episode.vote_average || 0) * 10) : null,
    availability_status: safeText(episode.availability_status),
    availability_checked_at: safeText(episode.availability_checked_at),
    availability_source: safeText(episode.availability_source),
    availability_reason: safeText(episode.availability_reason),
    primary_watch_url_tested: safeText(episode.primary_watch_url_tested),
    has_watch_sources: hasWatchSources(episode)
  };
}

function movieEntry(movie){
  const dateKey = safeText(movie.release_date).slice(0, 10);
  const id = safeInt(movie.tmdb_id || movie.id);
  return {
    kind: 'movie',
    date: dateKey,
    id,
    tmdb_id: id,
    title: safeText(movie.title || movie.name),
    thumb: safeText(movie.poster_local || movie.backdrop_local),
    poster_local: safeText(movie.poster_local),
    backdrop_local: safeText(movie.backdrop_local),
    runtime: movie.runtime || null,
    progress: movie.vote_average != null ? Math.round(Number(movie.vote_average || 0) * 10) : null,
    availability_status: safeText(movie.availability_status),
    availability_checked_at: safeText(movie.availability_checked_at),
    availability_source: safeText(movie.availability_source),
    availability_reason: safeText(movie.availability_reason),
    primary_watch_url_tested: safeText(movie.primary_watch_url_tested),
    has_watch_sources: hasWatchSources(movie)
  };
}

function sortCalendarEntries(entries){
  entries.sort((a, b) => {
    const aKind = a.kind === 'episode' ? 0 : 1;
    const bKind = b.kind === 'episode' ? 0 : 1;
    if (aKind !== bKind) return aKind - bKind;
    return safeText(a.show_title || a.title).localeCompare(safeText(b.show_title || b.title));
  });
}

function deriveCalendarFromData(data){
  const days = {};
  const shows = Array.isArray(data && data.shows) ? data.shows : [];
  const movies = Array.isArray(data && data.movies) ? data.movies : [];

  for (const show of shows){
    if (!show || typeof show !== 'object') continue;
    const seasons = Array.isArray(show.seasons) ? show.seasons : [];
    for (const season of seasons){
      if (!season || typeof season !== 'object') continue;
      const episodes = Array.isArray(season.episodes) ? season.episodes : [];
      for (const episode of episodes){
        if (!episode || typeof episode !== 'object') continue;
        const dateKey = safeText(episode.air_date).slice(0, 10);
        if (dateKey.length !== 10) continue;
        if (!days[dateKey]) days[dateKey] = [];
        days[dateKey].push(episodeEntry(show, season, episode));
      }
    }
  }

  for (const movie of movies){
    if (!movie || typeof movie !== 'object') continue;
    const dateKey = safeText(movie.release_date).slice(0, 10);
    if (dateKey.length !== 10) continue;
    if (!days[dateKey]) days[dateKey] = [];
    days[dateKey].push(movieEntry(movie));
  }

  for (const entries of Object.values(days)) sortCalendarEntries(entries);

  return {
    meta: {
      generated_utc: new Date().toISOString(),
      schema: 'calendar.v1',
      source: 'runtime fallback from data/data.json',
      detail_dir: '/data/catalog_detail'
    },
    days: Object.fromEntries(Object.entries(days).sort(([a], [b]) => a.localeCompare(b)))
  };
}

async function loadCalendarWithFallback(urls){
  const calendar = await loadJsonFirst(urls);
  if (hasCalendarDays(calendar)) return calendar;
  const fullData = await loadJsonFirst(['../data/data.json']);
  return deriveCalendarFromData(fullData);
}

function emptyDiscoverRegistry(){
  return {
    meta: {
      generated_utc: new Date().toISOString(),
      schema: 'discover.registry.v1',
      status: 'config-needed'
    },
    sources: []
  };
}

export async function loadCatalogIndexFirst(urls = ['../data/catalog_index.json']){
  if (!catalogIndexPromise) catalogIndexPromise = loadJsonFirst(urls);
  return catalogIndexPromise;
}

export async function loadCalendarFirst(urls = ['../data/calendar.json']){
  if (!calendarPromise) calendarPromise = loadCalendarWithFallback(urls);
  return calendarPromise;
}

export async function loadDiscoverRegistryFirst(urls = ['../data/discover_registry.json']){
  if (!discoverRegistryPromise){
    discoverRegistryPromise = loadJsonFirst(urls).catch(() => emptyDiscoverRegistry());
  }
  return discoverRegistryPromise;
}

export async function loadCatalogDetailFirst(id, urls){
  const key = String(id ?? '').trim();
  if (!key) throw new Error('Catalog detail id is required');
  if (!detailPromises.has(key)){
    detailPromises.set(key, loadJsonFirst(Array.isArray(urls) && urls.length ? urls : [`../data/catalog_detail/${key}.json`]));
  }
  return detailPromises.get(key);
}

export async function loadInputsFirst(urls = ['../data/inputs.json', '../inputs.json']){
  if (!inputsPromise) inputsPromise = loadJsonFirst(urls);
  return inputsPromise;
}

export function clearDataLoaderCache(){
  catalogIndexPromise = null;
  calendarPromise = null;
  discoverRegistryPromise = null;
  inputsPromise = null;
  detailPromises.clear();
}
