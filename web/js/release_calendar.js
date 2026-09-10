(() => {
  'use strict';

  const DAY_MS = 24 * 60 * 60 * 1000;
  const state = {
    month: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
    kind: 'all',
    events: []
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

  function showTitle(show){
    return show?.name || show?.title || show?.original_name || 'Untitled show';
  }

  function movieTitle(movie){
    return movie?.title || movie?.name || movie?.original_title || 'Untitled movie';
  }

  function posterUrl(item){
    const path = item?.poster_path || item?.poster || '';
    if (!path) return '';
    if (/^(https?:|\.\.\/|\.\/|\/)/.test(path)) return path;
    return `https://image.tmdb.org/t/p/w185${path.startsWith('/') ? '' : '/'}${path}`;
  }

  function buildEvents(data){
    const events = [];
    const shows = Array.isArray(data?.shows) ? data.shows : [];
    const movies = Array.isArray(data?.movies) ? data.movies : [];

    for (const movie of movies){
      const date = parseDate(movie?.release_date);
      if (!date) continue;
      events.push({
        id: `movie:${movie?.tmdb_id || movie?.id || movieTitle(movie)}:${dateKey(date)}`,
        date,
        dateKey: dateKey(date),
        kind: 'movie',
        title: movieTitle(movie),
        label: 'Movie Release',
        poster: posterUrl(movie)
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
          id: `show:${show?.tmdb_id || show?.id || showTitle(show)}:premiere:${dateKey(firstAir)}`,
          date: firstAir,
          dateKey: dateKey(firstAir),
          kind: 'show',
          title: showTitle(show),
          label: 'Series Premiere',
          poster: posterUrl(show)
        });
      }

      for (const { season, date } of seasonEvents){
        const seasonNumber = Number(season.season_number);
        const isSeriesPremiere = seasonNumber === 1 && firstAir && dateKey(firstAir) === dateKey(date);
        events.push({
          id: `show:${show?.tmdb_id || show?.id || showTitle(show)}:season:${seasonNumber}:${dateKey(date)}`,
          date,
          dateKey: dateKey(date),
          kind: 'show',
          title: showTitle(show),
          label: isSeriesPremiere ? 'Series Premiere • Season 1' : `Season ${seasonNumber} Premiere`,
          poster: posterUrl(season) || posterUrl(show)
        });
      }
    }

    const seen = new Set();
    return events
      .filter((event) => {
        if (seen.has(event.id)) return false;
        seen.add(event.id);
        return true;
      })
      .sort((a, b) => a.date - b.date || a.title.localeCompare(b.title));
  }

  function eventCard(event){
    const image = event.poster
      ? `<img src="${safe(event.poster)}" alt="" loading="lazy" />`
      : '<div class="release-calendar__placeholder">🎬</div>';

    return `<article class="release-calendar__event release-calendar__event--${event.kind}">
      <div class="release-calendar__thumb">${image}</div>
      <div class="release-calendar__event-copy">
        <div class="release-calendar__event-title">${safe(event.title)}</div>
        <div class="release-calendar__event-label">${safe(event.label)}</div>
      </div>
    </article>`;
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

  boot();
})();
