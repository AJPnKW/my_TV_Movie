(() => {
  'use strict';

  const DAY_MS = 24 * 60 * 60 * 1000;
  const state = {
    month: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
    kind: 'all',
    events: [],
    eventById: new Map()
  };

  const $ = (selector) => document.querySelector(selector);
  const safe = (value) => String(value ?? '').replace(/[&<>'"]/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[ch]));

  function parseDate(value){
    const text = String(value || '').slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return null;
    const [year, month, day] = text.split('-').map(Number);
    const date = new Date(year, month - 1, day);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function dateKey(date){
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  }

  function displayDate(date){
    return date.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  }

  function showTitle(show){
    return show?.name || show?.title || show?.original_name || 'Untitled show';
  }

  function movieTitle(movie){
    return movie?.title || movie?.name || movie?.original_title || 'Untitled movie';
  }

  function normalizeLocalImagePath(path){
    const value = String(path || '').trim();
    if (!value) return '';
    if (/^https?:\/\//i.test(value)) return value;
    if (value.startsWith('../') || value.startsWith('./')) return value;
    if (value.startsWith('/assets/')) return `..${value}`;
    if (value.startsWith('assets/')) return `../${value}`;
    return value;
  }

  function posterUrl(item){
    const local = normalizeLocalImagePath(item?.poster_local || item?.poster || '');
    if (local) return local;

    const remote = String(item?.poster_path || '').trim();
    if (!remote) return '';
    if (/^https?:\/\//i.test(remote)) return remote;
    if (remote.startsWith('/assets/')) return `..${remote}`;
    if (remote.startsWith('assets/')) return `../${remote}`;
    return `https://image.tmdb.org/t/p/w342${remote.startsWith('/') ? '' : '/'}${remote}`;
  }

  function tmdbId(item){
    return item?.tmdb_id || item?.id || '';
  }

  function genresText(item){
    const genres = Array.isArray(item?.genres) ? item.genres : [];
    return genres.map((genre) => typeof genre === 'string' ? genre : genre?.name).filter(Boolean).join(' • ');
  }

  function buildEvents(data){
    const events = [];
    const shows = Array.isArray(data?.shows) ? data.shows : [];
    const movies = Array.isArray(data?.movies) ? data.movies : [];

    for (const movie of movies){
      const date = parseDate(movie?.release_date);
      if (!date) continue;
      events.push({
        id: `movie:${tmdbId(movie) || movieTitle(movie)}:${dateKey(date)}`,
        date,
        dateKey: dateKey(date),
        kind: 'movie',
        popupKind: 'movie',
        title: movieTitle(movie),
        label: 'Movie Release',
        poster: posterUrl(movie),
        source: movie
      });
    }

    for (const show of shows){
      const seasons = Array.isArray(show?.seasons) ? show.seasons : [];
      const seasonEvents = seasons
        .map((season) => ({ season, date: parseDate(season?.air_date) }))
        .filter(({ season, date }) => date && Number(season?.season_number) >= 1);

      const firstAir = parseDate(show?.first_air_date);
      const seasonOne = seasonEvents.find(({ season }) => Number(season?.season_number) === 1);

      if (firstAir && (!seasonOne || dateKey(seasonOne.date) !== dateKey(firstAir))){
        events.push({
          id: `show:${tmdbId(show) || showTitle(show)}:premiere:${dateKey(firstAir)}`,
          date: firstAir,
          dateKey: dateKey(firstAir),
          kind: 'show',
          popupKind: 'show',
          title: showTitle(show),
          label: 'Series Premiere',
          poster: posterUrl(show),
          source: show
        });
      }

      for (const { season, date } of seasonEvents){
        const seasonNumber = Number(season.season_number);
        const isSeriesPremiere = seasonNumber === 1 && firstAir && dateKey(firstAir) === dateKey(date);
        events.push({
          id: `show:${tmdbId(show) || showTitle(show)}:season:${seasonNumber}:${dateKey(date)}`,
          date,
          dateKey: dateKey(date),
          kind: 'show',
          popupKind: 'season',
          title: showTitle(show),
          label: isSeriesPremiere ? 'Series Premiere • Season 1' : `Season ${seasonNumber} Premiere`,
          poster: posterUrl(season) || posterUrl(show),
          source: show,
          season
        });
      }
    }

    const seen = new Set();
    const normalized = events
      .filter((event) => {
        if (seen.has(event.id)) return false;
        seen.add(event.id);
        return true;
      })
      .sort((a, b) => a.date - b.date || a.title.localeCompare(b.title));

    state.eventById = new Map(normalized.map((event) => [event.id, event]));
    return normalized;
  }

  function eventCard(event){
    const image = event.poster
      ? `<img src="${safe(event.poster)}" alt="" loading="lazy" />`
      : '<div class="release-calendar__placeholder">🎬</div>';

    return `<article class="release-calendar__event release-calendar__event--${event.kind}" role="button" tabindex="0" data-release-event-id="${safe(event.id)}" aria-label="Open ${safe(event.label)} details for ${safe(event.title)}">
      <div class="release-calendar__thumb">${image}</div>
      <div class="release-calendar__event-copy">
        <div class="release-calendar__event-title">${safe(event.title)}</div>
        <div class="release-calendar__event-label">${safe(event.label)}</div>
      </div>
    </article>`;
  }

  function popupHtml(event){
    const source = event.source || {};
    const season = event.season || null;
    const poster = event.poster ? `<img class="release-popup__poster" src="${safe(event.poster)}" alt="" />` : '';
    let heading = event.title;
    let subheading = event.label;
    let metadata = '';
    let overview = source?.overview || '';

    if (event.popupKind === 'movie'){
      const runtime = Number(source?.runtime) > 0 ? `${Number(source.runtime)} min` : '';
      metadata = [displayDate(event.date), runtime, genresText(source), tmdbId(source) ? `TMDB: ${tmdbId(source)}` : ''].filter(Boolean).join(' • ');
    } else if (event.popupKind === 'season'){
      const number = Number(season?.season_number || 0);
      const seasonName = season?.name || `Season ${number}`;
      heading = `${event.title} — ${seasonName}`;
      subheading = event.label;
      metadata = [displayDate(event.date), Number(season?.episode_count) > 0 ? `${Number(season.episode_count)} episodes` : '', tmdbId(source) ? `Show TMDB: ${tmdbId(source)}` : ''].filter(Boolean).join(' • ');
      overview = season?.overview || source?.overview || '';
    } else {
      metadata = [displayDate(event.date), source?.status || '', genresText(source), tmdbId(source) ? `TMDB: ${tmdbId(source)}` : ''].filter(Boolean).join(' • ');
    }

    return `<div class="release-popup">
      ${poster}
      <div class="release-popup__copy">
        <div class="release-popup__type">${safe(subheading)}</div>
        <h2>${safe(heading)}</h2>
        ${metadata ? `<div class="release-popup__meta">${safe(metadata)}</div>` : ''}
        ${overview ? `<p class="release-popup__overview">${safe(overview)}</p>` : ''}
      </div>
    </div>`;
  }

  function openReleasePopup(event){
    const back = $('#modalBack');
    const title = $('#modalTitle');
    const body = $('#modalBody');
    if (!back || !title || !body || !event) return;
    title.textContent = event.popupKind === 'movie' ? 'Movie' : event.popupKind === 'season' ? 'Season' : 'Show';
    body.innerHTML = popupHtml(event);
    back.classList.add('open');
    back.setAttribute('aria-hidden', 'false');
    $('#modalClose')?.focus();
  }

  function closeReleasePopup(){
    const back = $('#modalBack');
    if (!back) return;
    back.classList.remove('open');
    back.setAttribute('aria-hidden', 'true');
  }

  function activateEventFromTarget(target){
    const card = target?.closest?.('[data-release-event-id]');
    if (!card) return false;
    const event = state.eventById.get(card.getAttribute('data-release-event-id'));
    if (!event) return false;
    openReleasePopup(event);
    return true;
  }

  function filteredEvents(){
    return state.kind === 'all'
      ? state.events
      : state.events.filter((event) => event.kind === state.kind);
  }

  function render(){
    const monthStart = new Date(state.month.getFullYear(), state.month.getMonth(), 1);
    const nextMonth = new Date(state.month.getFullYear(), state.month.getMonth() + 1, 1);
    const monthEvents = filteredEvents().filter((event) => event.date >= monthStart && event.date < nextMonth);
    const eventsByDay = new Map();

    for (const event of monthEvents){
      if (!eventsByDay.has(event.dateKey)) eventsByDay.set(event.dateKey, []);
      eventsByDay.get(event.dateKey).push(event);
    }

    $('#releaseMonth').textContent = monthStart.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
    const showCount = monthEvents.filter((event) => event.kind === 'show').length;
    const movieCount = monthEvents.filter((event) => event.kind === 'movie').length;
    $('#releaseSummary').textContent = `${monthEvents.length} releases • ${showCount} TV/season • ${movieCount} movies`;

    document.querySelectorAll('[data-release-kind]').forEach((button) => {
      const active = button.dataset.releaseKind === state.kind;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', active ? 'true' : 'false');
    });

    const firstCell = new Date(monthStart);
    firstCell.setDate(1 - monthStart.getDay());
    const todayKey = dateKey(new Date());

    let html = '<div class="release-calendar__weekdays">' +
      ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => `<div>${day}</div>`).join('') +
      '</div><div class="release-calendar__grid">';

    for (let index = 0; index < 42; index++){
      const day = new Date(firstCell.getTime() + (index * DAY_MS));
      const key = dateKey(day);
      const outside = day.getMonth() !== monthStart.getMonth();
      const events = eventsByDay.get(key) || [];
      html += `<section class="release-calendar__day${outside ? ' is-outside' : ''}${key === todayKey ? ' is-today' : ''}">
        <div class="release-calendar__date">${day.getDate()}</div>
        <div class="release-calendar__events">${events.map(eventCard).join('')}</div>
      </section>`;
    }

    html += '</div>';
    $('#releaseCalendar').innerHTML = html;
  }

  async function boot(){
    try {
      const response = await fetch('../data/data.json', { cache: 'no-store' });
      if (!response.ok) throw new Error(`data.json returned HTTP ${response.status}`);
      state.events = buildEvents(await response.json());
      $('#statusText').textContent = 'Ready';
      render();
    } catch (error){
      console.error(error);
      $('#statusText').textContent = 'Data error';
      $('#releaseCalendar').innerHTML = `<div class="release-calendar__error">Unable to load release data: ${safe(error.message)}</div>`;
    }
  }

  $('#releasePrev')?.addEventListener('click', () => {
    state.month = new Date(state.month.getFullYear(), state.month.getMonth() - 1, 1);
    render();
  });
  $('#releaseNext')?.addEventListener('click', () => {
    state.month = new Date(state.month.getFullYear(), state.month.getMonth() + 1, 1);
    render();
  });
  $('#releaseToday')?.addEventListener('click', () => {
    const now = new Date();
    state.month = new Date(now.getFullYear(), now.getMonth(), 1);
    render();
  });
  document.querySelectorAll('[data-release-kind]').forEach((button) => {
    button.addEventListener('click', () => {
      state.kind = button.dataset.releaseKind || 'all';
      render();
    });
  });

  $('#releaseCalendar')?.addEventListener('click', (event) => activateEventFromTarget(event.target));
  $('#releaseCalendar')?.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    if (activateEventFromTarget(event.target)) event.preventDefault();
  });
  $('#modalClose')?.addEventListener('click', closeReleasePopup);
  $('#modalBack')?.addEventListener('click', (event) => {
    if (event.target === $('#modalBack')) closeReleasePopup();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && $('#modalBack')?.classList.contains('open')) closeReleasePopup();
  });

  boot();
})();
