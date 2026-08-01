/*
FILE: web/js/app_runtime.js
VERSION: v1.0.0
UPDATED: 2026-03-15T04:28:23Z
CHANGE NOTES:
- Extracted the shared browser runtime from the corrected dashboard-family implementation.
- Rebased index, shows, movies, calendar, discover, and config onto one shared runtime entry.
- Centralized config/data loading through shared runtime modules.
*/

import * as configLoader from './config_loader.js?v=v1.5.6';
import * as dataLoader from './data_loader.js?v=v1.5.6';
import * as availabilityUi from './availability_ui.js?v=v1.5.6';
import * as cardRenderer from './card_renderer.js?v=v1.5.6';
import * as popupController from './popup_controller.js?v=v1.5.6';
import * as actionBar from './action_bar.js?v=v1.5.6';
import './watch_state_manager.js?v=v1.5.6';
import '../config.js?v=v1.5.6';

window.MyTVHubSharedModules = Object.freeze({
  configLoader,
  dataLoader,
  availabilityUi,
  cardRenderer,
  popupController,
  actionBar
});

cardRenderer.applyRuntimeContract(document);
actionBar.applyRuntimeContract(document);
popupController.applyRuntimeContract(document);
document.documentElement.setAttribute('data-runtime-family', 'normalized_main_app');
if (document.body) document.body.setAttribute('data-runtime-family', 'normalized_main_app');

(() => {
  const $ = (sel, el=document) => el.querySelector(sel);
  const $$ = (sel, el=document) => Array.from(el.querySelectorAll(sel));
  const PAGE = document.body?.dataset?.page || "dashboard";
  const on = (el, evt, fn) => { if (el) el.addEventListener(evt, fn); };
  const DAY_MS = 24 * 60 * 60 * 1000;
  const DEFAULT_CURRENT_SHOW_ACTIVITY_WINDOW_DAYS = 183;
  const DEFAULT_CURRENT_MOVIE_RELEASE_WINDOW_DAYS = 183;
  const DEFAULT_CURRENT_MOVIE_RELEASE_LOOKAHEAD_DAYS = 30;

  const state = {
    cfg: null,
    data: null,
    calendarData: null,
    watchStateQueue: null,
    providerRegistry: null,
    discoverRegistry: null,
    inputs: null,
    tab: PAGE,
    lastNonShowHash: `#${PAGE}`,
    calendarMonth: null,
    calendarView: new URLSearchParams(location.search).get("view") === "list" ? "list" : "grid",
    watchState: null,
    watchStateSource: null,
    apiAvailable: false,
    inputsEditorServerAvailable: false,
    inputsDirty: false,
    icons: {},
    ui: {},
    search: { shows: "", movies: "" },
    sort: { shows: "title", movies: "title" },
    filters: {
      shows: { genres: [], year: "", scope: "all", watchlist: "all", watch_status: [], availability: "all", watched: "all" },
      movies: { genres: [], year: "", collection: "", scope: "all", watchlist: "all", watch_status: [], availability: "all", watched: "all" },
      watchlist: { watch_status: "all", media_kind: "all", search: "" }
    },
    watchMe: {
      search: "",
      type: "all",
      windowDays: 14
    },
    showById: new Map(),
    movieById: new Map(),
    manageWatchStatePage: 0,
    manageWatchState: {
      search: "",
      type: "all",
      pageSize: 50,
      sortKey: "title",
      sortDir: "asc"
    },
    view: {
      shows: { eye: "show_all" },
      movies: { eye: "show_all" }
    },
    layout: {
      showsSidebarCollapsed: false,
      moviesSidebarCollapsed: false,
      watchMeSidebarCollapsed: false
    },
    dashboard: {
      lastWeekOffsetWeeks: 0
    },
    runtimeMode: "full",
    show: {
      tmdb_id: null,
      selectedSeasonNumber: null,
    }
  };
  let lastFocusEl = null;

  function ensureModalShell(){
    if (!$("#modalBack")){
      document.body.insertAdjacentHTML("beforeend", `
        <div id="modalBack" class="app-modal-backdrop" aria-hidden="true" role="dialog" aria-modal="true">
          <div id="modalCard" class="app-modal-card" tabindex="0">
            <div class="app-modal-header">
              <div id="modalTitle" class="app-modal-title">Details</div>
              <button id="modalClose" class="calbtn" type="button">Close</button>
            </div>
            <div id="modalBody" class="app-modal-body"></div>
          </div>
        </div>
      `);
    }
    if (!$("#providerBack")){
      document.body.insertAdjacentHTML("beforeend", `
        <div id="providerBack" class="app-modal-backdrop app-modal-backdrop--provider" aria-hidden="true" role="dialog" aria-modal="true">
          <div id="providerCard" class="app-modal-card app-modal-card--provider" tabindex="0">
            <div class="app-modal-header">
              <div id="providerTitle" class="app-modal-title">Providers</div>
              <button id="providerClose" class="calbtn" type="button">Close</button>
            </div>
            <div id="providerBody" class="app-modal-body"></div>
          </div>
        </div>
      `);
    }
  }

  function ensureMainAppShell(){
    ensureModalShell();
    const nav = $(".nav");
    if (nav && !$("[data-tab='inputs-editor']", nav)){
      nav.insertAdjacentHTML("beforeend", `<a class="tab" data-tab="inputs-editor" href="#inputs-editor" role="tab" aria-selected="false" aria-label="Inputs Editor" title="Inputs Editor" data-label="Inputs Editor">✎</a>`);
    }
    if (nav){
      $$(".tab", nav).forEach(tab => {
        const label = safeText(tab.getAttribute("data-label") || tab.getAttribute("aria-label") || tab.getAttribute("title") || tab.textContent).trim();
        if (label){
          tab.setAttribute("title", label);
          tab.setAttribute("aria-label", label);
          tab.setAttribute("data-label", label);
        }
      });
    }

    const main = $(".main");
    if (!main) return;
    main.innerHTML = "";

    const appendPanel = (id, html) => {
      if (!document.getElementById(id)){
        main.insertAdjacentHTML("beforeend", html);
      }
    };

    appendPanel("panel-dashboard", `
      <div id="panel-dashboard" class="panel hidden">
        <div class="dash">
          <section class="dashblock accent-pink">
            <div class="dashhead">
              <h2>Current / Recent</h2>
              <div class="dashhead__actions dashhead__actions--solo">
                <span class="muted dashrange-meta" id="dashLastWeekMeta"></span>
                <div class="dashnav" aria-label="Recent releases navigation">
                  <button class="calbtn dashnav__btn" type="button" data-dash-lastweek-nav="jump-back" aria-label="Jump back four weeks">«</button>
                  <button class="calbtn dashnav__btn" type="button" data-dash-lastweek-nav="back" aria-label="Previous week">‹</button>
                  <button class="calbtn dashnav__btn" type="button" data-dash-lastweek-nav="forward" aria-label="Next week">›</button>
                  <button class="calbtn dashnav__btn" type="button" data-dash-lastweek-nav="jump-forward" aria-label="Jump forward four weeks">»</button>
                </div>
              </div>
            </div>
            <div id="dashLastWeekCols" class="dashgrid"></div>
          </section>
          <section class="dashblock accent-pink">
            <div class="dashhead">
              <h2>Upcoming Schedule</h2>
              <span class="muted">Tomorrow through next week</span>
            </div>
            <div id="dashScheduleCols" class="dashgrid"></div>
          </section>
          <section class="dashblock accent-green">
            <div class="dashhead">
              <h2>Watchlist</h2>
              <span class="muted" id="dashWatchMeta"></span>
            </div>
            <div id="dashWatchlist" class="dashwatchlist"></div>
          </section>
          <section class="dashblock accent-yellow">
            <div class="dashhead">
              <h2>Recommendations</h2>
              <span class="muted">Shows and Movies</span>
            </div>
            <div class="dashrecs">
              <div class="dashreccol">
                <div class="dashhead dashhead--sub"><h2>Shows</h2></div>
                <div id="dashShowRecs" class="dashrecgrid"></div>
              </div>
              <div class="dashreccol">
                <div class="dashhead dashhead--sub"><h2>Movies</h2></div>
                <div id="dashMovieRecs" class="dashrecgrid"></div>
              </div>
            </div>
          </section>
        </div>
      </div>
    `);

    appendPanel("panel-watch-me", `
      <div id="panel-watch-me" class="panel hidden">
        <div class="browse-layout browse-layout--watch-me" data-sidebar-layout="watch-me">
          <aside class="browse-sidebar browse-sidebar--watch-me" id="watchMeSidebar" aria-label="Watch Me filters">
            <div class="browse-sidebar__header">
              <div class="browse-sidebar__eyebrow">Watch Me</div>
              <h2 class="browse-sidebar__title">Release Filters</h2>
              <p class="browse-sidebar__copy">Simple release list with shared actions and local state.</p>
              <button class="calbtn browse-sidebar__toggle" type="button" data-sidebar-toggle="watch-me" aria-expanded="true">Hide Filters</button>
            </div>
            <div class="control-panel">
              <div class="control-row control-row--primary">
                <input id="watchMeSearch" class="input control-input" type="search" placeholder="Search releases" tabindex="-1" data-tv-skip="1" />
                <select id="watchMeType" class="input control-select" tabindex="-1" data-tv-skip="1">
                  <option value="all">Episodes and Movies</option>
                  <option value="episodes">Episodes only</option>
                  <option value="movies">Movies only</option>
                </select>
                <select id="watchMeWindow" class="input control-select" tabindex="-1" data-tv-skip="1">
                  <option value="7">Next 7 days</option>
                  <option value="14" selected>Next 14 days</option>
                  <option value="30">Next 30 days</option>
                  <option value="60">Next 60 days</option>
                </select>
              </div>
              <div class="control-row control-row--actions">
                <button id="watchMeToday" class="calbtn" type="button">Jump To Today</button>
                <a class="calbtn" href="#calendar" data-tab-jump="calendar">Open Calendar</a>
                <button id="watchMeReset" class="calbtn" type="button">Reset Filters</button>
              </div>
            </div>
          </aside>
          <section class="browse-content browse-content--watch-me">
            <section class="dashblock watchme-hero">
              <div class="dashhead">
                <h2>Watch Me</h2>
                <div class="browse-content__toolbar">
                  <button class="calbtn browse-content__toggle" type="button" data-sidebar-toggle="watch-me" aria-expanded="true">Hide Filters</button>
                  <span id="watchMeSummary" class="muted">Preparing view</span>
                </div>
              </div>
              <p class="watchme-hero__copy">Upcoming episodes and movie releases in a compact list view.</p>
            </section>
            <div id="watchMeSections" class="watchme-sections"></div>
          </section>
        </div>
      </div>
    `);

    appendPanel("panel-manage-watch-state", `
      <div id="panel-manage-watch-state" class="panel hidden">
        <div id="manageWatchStateRoot"></div>
      </div>
    `);

    appendPanel("panel-show", `
      <div id="panel-show" class="panel hidden">
        <div id="showRoot"></div>
      </div>
    `);

    appendPanel("panel-calendar", `
      <div id="panel-calendar" class="panel hidden">
        <section class="dashblock dashblock--calendar">
          <div class="dashhead">
            <div class="calendar-toolbar__controls" aria-label="Calendar controls">
              <div class="calendar-toolbar__group calendar-toolbar__group--left">
                <span id="calTodayLabel" class="muted"></span>
                <button id="calToday" class="calbtn" type="button">Today</button>
              </div>
              <div class="calendar-toolbar__group calendar-toolbar__group--right">
                <div class="calendar-view-toggle" id="calendarViewToggle" aria-label="Calendar view mode">
                  <button class="segbtn active" type="button" data-calendar-view="grid">Grid</button>
                  <button class="segbtn" type="button" data-calendar-view="list">Month List</button>
                </div>
                <button id="calPrev" class="calbtn" type="button" aria-label="Previous month">Prev</button>
                <div id="calMonth" class="muted">Month</div>
                <button id="calNext" class="calbtn" type="button" aria-label="Next month">Next</button>
              </div>
            </div>
          </div>
          <div id="calendar" class="calendar-grid"></div>
        </section>
      </div>
    `);

    appendPanel("panel-shows", `
      <div id="panel-shows" class="panel hidden">
        <div class="browse-layout browse-layout--shows" data-sidebar-layout="shows">
            <aside class="browse-sidebar">
              <div class="browse-sidebar__header">
                <div class="browse-sidebar__eyebrow">Browse</div>
                <h2 class="browse-sidebar__title">Library Filters</h2>
                <p class="browse-sidebar__copy">Shared cards, shared actions, one left filter rail.</p>
                <button class="calbtn browse-sidebar__toggle" type="button" data-sidebar-toggle="shows" aria-expanded="true">Hide Filters</button>
              </div>
            <div class="control-panel">
              <div class="control-row control-row--primary">
                <input id="searchShows" class="input control-input" type="search" placeholder="Search shows" tabindex="-1" data-tv-skip="1" />
                <select id="filterShowsYear" class="input control-select" tabindex="-1" data-tv-skip="1"></select>
                <select id="sortShows" class="input control-select" tabindex="-1" data-tv-skip="1">
                  <option value="title">Title A-Z</option>
                  <option value="title_desc">Title Z-A</option>
                  <option value="release">Newest first</option>
                  <option value="popularity">Popularity</option>
                  <option value="vote">Rating</option>
                </select>
              </div>
              <div id="filterShowsScope" class="control-row control-row--chips">
                <button class="segbtn active" type="button" data-scope="all">All Shows</button>
                <button class="segbtn" type="button" data-scope="current">Current</button>
                <button class="segbtn" type="button" data-scope="upcoming">Upcoming</button>
                <button class="segbtn" type="button" data-scope="returning">Returning</button>
                <button class="segbtn" type="button" data-scope="ended">Ended</button>
              </div>
              <div class="control-row control-row--chips">
                <div id="filterShowsAvailability" style="display:flex;gap:8px;flex-wrap:wrap;">
                  <button class="segbtn active" type="button" data-availability="all">All availability</button>
                  <button class="segbtn" type="button" data-availability="available">Available</button>
                  <button class="segbtn" type="button" data-availability="unreleased">Unreleased</button>
                </div>
                <div id="filterShowsWatched" style="display:flex;gap:8px;flex-wrap:wrap;">
                  <button class="segbtn active" type="button" data-watched="all">All watched</button>
                  <button class="segbtn" type="button" data-watched="watched">Watched</button>
                  <button class="segbtn" type="button" data-watched="unwatched">Unwatched</button>
                </div>
                <div id="filterShowsWatchlist" style="display:flex;gap:8px;flex-wrap:wrap;">
                  <button class="segbtn active" type="button" data-watchlist="all">All watchlist</button>
                  <button class="segbtn" type="button" data-watchlist="watchlist">Watchlist</button>
                </div>
              </div>
              <div class="control-group">
                <div class="control-label">Genres</div>
                <div id="filterShowsGenres" class="control-checks"></div>
              </div>
            </div>
          </aside>
          <section class="browse-content">
            <div class="dashblock">
              <div class="dashhead dashhead--compact">
                <button class="calbtn browse-content__toggle" type="button" data-sidebar-toggle="shows" aria-expanded="true">Hide Filters</button>
                <span id="showsSummary" class="muted">Library</span>
              </div>
              <div id="showsGrid" class="media-grid media-grid--shows"></div>
            </div>
          </section>
        </div>
      </div>
    `);

    appendPanel("panel-movies", `
      <div id="panel-movies" class="panel hidden">
        <div class="browse-layout browse-layout--movies" data-sidebar-layout="movies">
            <aside class="browse-sidebar">
              <div class="browse-sidebar__header">
                <div class="browse-sidebar__eyebrow">Browse</div>
                <h2 class="browse-sidebar__title">Library Filters</h2>
                <p class="browse-sidebar__copy">Shared cards, shared actions, one left filter rail.</p>
                <button class="calbtn browse-sidebar__toggle" type="button" data-sidebar-toggle="movies" aria-expanded="true">Hide Filters</button>
              </div>
            <div class="control-panel">
              <div class="control-row control-row--primary">
                <input id="searchMovies" class="input control-input" type="search" placeholder="Search movies" tabindex="-1" data-tv-skip="1" />
                <select id="filterMoviesYear" class="input control-select" tabindex="-1" data-tv-skip="1"></select>
                <select id="filterMoviesCollection" class="input control-select" tabindex="-1" data-tv-skip="1"></select>
                <select id="sortMovies" class="input control-select" tabindex="-1" data-tv-skip="1">
                  <option value="title">Title A-Z</option>
                  <option value="title_desc">Title Z-A</option>
                  <option value="release">Newest first</option>
                  <option value="popularity">Popularity</option>
                  <option value="vote">Rating</option>
                </select>
              </div>
              <div id="filterMoviesScope" class="control-row control-row--chips">
                <button class="segbtn active" type="button" data-scope="all">All Movies</button>
                <button class="segbtn" type="button" data-scope="current">Current</button>
                <button class="segbtn" type="button" data-scope="upcoming">Upcoming</button>
                <button class="segbtn" type="button" data-scope="released">Released</button>
              </div>
              <div class="control-row control-row--chips">
                <div id="filterMoviesAvailability" style="display:flex;gap:8px;flex-wrap:wrap;">
                  <button class="segbtn active" type="button" data-availability="all">All availability</button>
                  <button class="segbtn" type="button" data-availability="available">Available</button>
                  <button class="segbtn" type="button" data-availability="unreleased">Unreleased</button>
                </div>
                <div id="filterMoviesWatched" style="display:flex;gap:8px;flex-wrap:wrap;">
                  <button class="segbtn active" type="button" data-watched="all">All watched</button>
                  <button class="segbtn" type="button" data-watched="watched">Watched</button>
                  <button class="segbtn" type="button" data-watched="unwatched">Unwatched</button>
                </div>
                <div id="filterMoviesWatchlist" style="display:flex;gap:8px;flex-wrap:wrap;">
                  <button class="segbtn active" type="button" data-watchlist="all">All watchlist</button>
                  <button class="segbtn" type="button" data-watchlist="watchlist">Watchlist</button>
                </div>
              </div>
              <div class="control-group">
                <div class="control-label">Genres</div>
                <div id="filterMoviesGenres" class="control-checks"></div>
              </div>
            </div>
          </aside>
          <section class="browse-content">
            <div class="dashblock">
              <div class="dashhead dashhead--compact">
                <button class="calbtn browse-content__toggle" type="button" data-sidebar-toggle="movies" aria-expanded="true">Hide Filters</button>
                <span id="moviesSummary" class="muted">Library</span>
              </div>
              <div id="moviesGrid" class="media-grid media-grid--movies"></div>
            </div>
          </section>
        </div>
      </div>
    `);

    appendPanel("panel-discover", `
      <div id="panel-discover" class="panel hidden">
        <div class="discover-split">
          <section class="dashblock accent-green">
            <div class="dashhead dashhead--compact"><span class="muted">Shows</span></div>
            <div id="discoverShowsGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--show_card_min),1fr));gap:12px;"></div>
          </section>
          <section class="dashblock accent-yellow">
            <div class="dashhead dashhead--compact"><span class="muted">Movies</span></div>
            <div id="discoverMoviesGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--movie_card_min),1fr));gap:12px;"></div>
          </section>
        </div>
      </div>
    `);

    appendPanel("panel-config", `
      <div id="panel-config" class="panel hidden">
        <div class="dash">
          <section class="dashblock">
            <div id="configRoot"></div>
          </section>
        </div>
      </div>
    `);

    appendPanel("panel-inputs-editor", `
      <div id="panel-inputs-editor" class="panel hidden">
        <div class="dash">
          <section class="dashblock accent-pink">
            <div class="dashhead"><h2>Inputs Editor</h2><span class="muted">Local tool for data/inputs.json</span></div>
            <div id="inputsEditorPanel" style="display:grid;gap:14px;max-width:940px;">
              <div id="inputsEditorPanelMeta" class="muted"></div>
              <div style="display:grid;gap:10px;padding:14px;border-radius:8px;border:1px solid rgba(255,255,255,0.12);background:rgba(255,255,255,0.04);">
                <div class="muted">Start the local servers from this repo, then open the editor in its own tab.</div>
                <code id="inputsEditorPanelCommand" style="display:block;padding:10px 12px;border-radius:8px;background:rgba(0,0,0,0.28);border:1px solid rgba(255,255,255,0.10);white-space:pre-wrap;">run_local_servers.bat</code>
                <div style="display:flex;gap:10px;flex-wrap:wrap;">
                  <button id="inputsEditorCopyCommand" class="calbtn" type="button">Copy Start Command</button>
                  <a id="inputsEditorOpen" class="calbtn" href="http://127.0.0.1:8787/web/inputs_editor.html" target="_blank" rel="noopener">Open Local Editor</a>
                  <button id="inputsEditorHelp" class="calbtn" type="button">Help</button>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    `);

    applyStickySectionHeads(main);
  }

  function setStatus(ok, msg) {
    const textEl = $("#statusText");
    const dotEl = $("#statusDot");
    if (textEl) textEl.textContent = msg;
    if (dotEl) dotEl.classList.toggle("bad", !ok);
  }

  function requestedRuntimeMode(){
    const queryMode = safeText(new URLSearchParams(location.search).get("mode")).toLowerCase();
    if (queryMode === "light" || queryMode === "trailer") return "light";
    return safeText(localStorage.getItem("mytv_runtime_mode")).toLowerCase() === "light" ? "light" : "full";
  }

  function isLightMode(){
    return state.runtimeMode === "light";
  }

  function applyRuntimeMode(mode, persist=false){
    state.runtimeMode = mode === "light" ? "light" : "full";
    document.documentElement.setAttribute("data-runtime-mode", state.runtimeMode);
    if (document.body) document.body.setAttribute("data-runtime-mode", state.runtimeMode);
    if (persist) localStorage.setItem("mytv_runtime_mode", state.runtimeMode);
    const select = $("#runtimeModeSelect");
    if (select) select.value = state.runtimeMode;
  }

  function ensureRuntimeModeControl(){
    const status = $(".top .status");
    if (!status || $("#runtimeModeSelect")) return;
    status.insertAdjacentHTML("beforeend", `
      <label class="runtime-mode-control" title="Runtime render mode">
        <span class="runtime-mode-control__label">Mode</span>
        <select id="runtimeModeSelect" class="runtime-mode-control__select" aria-label="Runtime mode">
          <option value="full">Full</option>
          <option value="light">Light</option>
        </select>
      </label>
    `);
    const select = $("#runtimeModeSelect");
    if (select){
      select.value = state.runtimeMode;
      select.addEventListener("change", () => {
        applyRuntimeMode(select.value, true);
        routeFromHash();
      });
    }
  }

  window.MyTVHubRuntimeMode = Object.assign(window.MyTVHubRuntimeMode || {}, {
    isLightMode,
    mode: () => state.runtimeMode
  });

  function appVersionText(){
    const globalCfg = window.MyTVHubConfig?.get_config?.() || null;
    return safeText(
      state.cfg?._meta?.version ||
      state.cfg?.version ||
      globalCfg?._meta?.version ||
      globalCfg?.version ||
      state.data?.meta?.version ||
      "v?"
    );
  }

  function setCalendarView(view){
    state.calendarView = view === "list" ? "list" : "grid";
    setSegActive($("#calendarViewToggle"), "calendar-view", state.calendarView);
    try {
      const url = new URL(window.location.href);
      if (state.calendarView === "list") url.searchParams.set("view", "list");
      else url.searchParams.delete("view");
      history.replaceState(null, "", url.toString());
    } catch (_) { /* noop */ }
  }

  function sidebarStateKey(kind){
    return kind === "shows"
      ? "showsSidebarCollapsed"
      : kind === "movies"
        ? "moviesSidebarCollapsed"
        : "watchMeSidebarCollapsed";
  }

  function applySidebarState(kind){
    const layout = document.querySelector(`[data-sidebar-layout="${kind}"]`);
    if (!layout) return;
    const collapsed = !!state.layout?.[sidebarStateKey(kind)];
    layout.classList.toggle("browse-layout--sidebar-hidden", collapsed);
    $$(`[data-sidebar-toggle="${kind}"]`).forEach(btn => {
      btn.textContent = collapsed ? "Show Filters" : "Hide Filters";
      btn.setAttribute("aria-expanded", collapsed ? "false" : "true");
    });
  }

  function setSidebarCollapsed(kind, collapsed){
    if (!state.layout) state.layout = {};
    state.layout[sidebarStateKey(kind)] = !!collapsed;
    applySidebarState(kind);
  }

  function canonicalPageForTab(tab){
    return {
      dashboard: "index.html",
      "watch-me": "watch_me.html",
      shows: "shows.html",
      movies: "movies.html",
      calendar: "calendar.html",
      discover: "discover.html",
      config: "config.html"
    }[tab] || "";
  }

  function syncCanonicalTabUrl(tab){
    const page = canonicalPageForTab(tab);
    if (!page) return;
    try {
      const url = new URL(window.location.href);
      const basePath = url.pathname.replace(/[^/]*$/, "");
      url.pathname = `${basePath}${page}`;
      if (!url.searchParams.get("view")) url.search = "";
      if (tab !== "calendar" || state.calendarView !== "list") url.searchParams.delete("view");
      if (tab === "calendar" && state.calendarView === "list") url.searchParams.set("view", "list");
      url.hash = "";
      history.replaceState(null, "", url.toString());
    } catch (_) { /* noop */ }
  }

  function pad2(n){ return String(n).padStart(2,"0"); }
  function seTag(s,e){ return `S${pad2(s)}E${pad2(e)}`; }

  function safeText(v){ return (v ?? "").toString(); }

  function stripJsonComments(input){
    let out = "";
    let inStr = false;
    let esc = false;
    let inLine = false;
    let inBlock = false;
    for (let i = 0; i < input.length; i++){
      const c = input[i];
      const n = input[i + 1];
      if (inLine){
        if (c === "\n"){
          inLine = false;
          out += c;
        }
        continue;
      }
      if (inBlock){
        if (c === "*" && n === "/"){
          inBlock = false;
          i++;
        }
        continue;
      }
      if (inStr){
        out += c;
        if (esc){
          esc = false;
        } else if (c === "\\"){
          esc = true;
        } else if (c === "\""){
          inStr = false;
        }
        continue;
      }
      if (c === "\""){
        inStr = true;
        out += c;
        continue;
      }
      if (c === "/" && n === "/"){
        inLine = true;
        i++;
        continue;
      }
      if (c === "/" && n === "*"){
        inBlock = true;
        i++;
        continue;
      }
      out += c;
    }
    return out;
  }

  function parseJsonc(text){
    return JSON.parse(stripJsonComments(text));
  }

  function iconSpec(key){
    const icons = state?.cfg?.icons;
    if (!icons || typeof icons !== "object") return null;
    const spec = icons[key];
    if (!spec || typeof spec !== "object") return null;
    return spec;
  }

  function iconChar(key, fallback=""){
    const spec = iconSpec(key);
    return safeText(spec?.icon || fallback);
  }

  function iconType(key, fallback="single-click"){
    const spec = iconSpec(key);
    return safeText(spec?.functionType || fallback);
  }

  function iconName(key, fallback=""){
    const spec = iconSpec(key);
    return safeText(spec?.name || fallback);
  }

  function iconClassForKey(key){
    const map = {
      media_vidrsc: "vidsrc",
      media_videasy: "videasy",
      meta_rt_critics: "rt",
      meta_rt_audience: "rt",
      meta_rating_summary: "rt"
    };
    return map[key] || "";
  }

  function applyIconText(){
    const icons = state?.cfg?.icons;
    if (!icons || typeof icons !== "object") return;
    $$("[data-icon-key]").forEach(el => {
      const key = safeText(el.getAttribute("data-icon-key"));
      if (!key) return;
      const spec = iconSpec(key);
      const icon = spec?.icon;
      if (icon) el.textContent = icon;
      if (spec?.functionType && !el.getAttribute("data-function-type")){
        el.setAttribute("data-function-type", spec.functionType);
      }
    });
  }
  const BASE_PATH = (() => {
    const p = location.pathname || "";
    const idx = p.indexOf("/web/");
    return idx > 0 ? p.slice(0, idx) : "";
  })();
  function withBasePath(path){
    const v = safeText(path).trim();
    if (!v) return "";
    if (/^https?:\/\//i.test(v)) return v;
    if (v.startsWith("/") && BASE_PATH && !v.startsWith(BASE_PATH + "/")) return BASE_PATH + v;
    return v;
  }

  function escHtml(s){
    return safeText(s)
      .replaceAll("&","&amp;")
      .replaceAll("<","&lt;")
      .replaceAll(">","&gt;")
      .replaceAll('"',"&quot;")
      .replaceAll("'","&#39;");
  }

  function fmtDate(d) {
    return formatDateShort(d);
  }

  function toDateKey(dt){
    return `${dt.getFullYear()}-${pad2(dt.getMonth()+1)}-${pad2(dt.getDate())}`;
  }

  function tmdbShowUrl(id){ return `https://www.themoviedb.org/tv/${id}`; }
  function tmdbMovieUrl(id){ return `https://www.themoviedb.org/movie/${id}`; }
  function tmdbEpisodeUrl(showId, s, e){ return `https://www.themoviedb.org/tv/${showId}/season/${s}/episode/${e}`; }
  function canonicalServiceLogoFromPath(path){
    const p = safeText(path).trim();
    if (!p) return "";
    const filename = p.split("/").pop();
    return filename ? withBasePath(`/assets/logos/services/${filename}`) : "";
  }
  function tmdbLogoUrl(path){
    const p = safeText(path).trim();
    return p ? `https://image.tmdb.org/t/p/w154${p}` : "";
  }
  function tmdbWatchUrl(kind, id){
    if (!id) return "";
    return kind === "movie"
      ? `https://www.themoviedb.org/movie/${id}/watch`
      : `https://www.themoviedb.org/tv/${id}/watch`;
  }

  function slugifyName(name){
    return safeText(name).toLowerCase().replace(/&/g, "and").replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  }

  function guessLocalNetworkLogo(name){
    const slug = slugifyName(name);
    if (!slug) return "";
    return withBasePath(`/assets/logos/services/${slug}.png`);
  }

  function getWatchBlock(item){
    if (!item || typeof item !== "object") return null;
    const watch = item.watch;
    return watch && typeof watch === "object" ? watch : null;
  }

  function getWatchProviders(item){
    const watch = getWatchBlock(item);
    const providers = watch?.providers;
    return providers && typeof providers === "object" ? providers : null;
  }

  function collectProvidersForRegion(wp, region){
    if (!wp || !region || !wp[region]) return [];
    const arr = Array.isArray(wp[region]) ? wp[region] : [];
    const out = [];
    const seen = new Set();
    return arr.filter(p => {
      const key = p?.provider_id ?? p?.provider_name ?? p?.name;
      if (!key || seen.has(key)) return false;
      seen.add(key);
      out.push(p);
      return true;
    });
  }

  function providerLogoUrl(p){
    if (!providerLogoUrl.cache) providerLogoUrl.cache = new Map();
    const cacheKey = `${safeText(p?.provider_name || p?.name || "")}|${safeText(p?.logo_local || "")}|${safeText(p?.logo_path || "")}`;
    if (providerLogoUrl.cache.has(cacheKey)) return providerLogoUrl.cache.get(cacheKey);
    const name = safeText(p?.provider_name || p?.name || "").trim();
    const explicitLocal = safeText(p?.logo_local || "").trim();
    const localFromPath = explicitLocal ? withBasePath(explicitLocal) : "";
    const tmdb = tmdbLogoUrl(p?.logo_path || "");
    const value = { name, local: localFromPath, tmdb };
    providerLogoUrl.cache.set(cacheKey, value);
    return value;
  }

  function providerLogoImgHtml(logo, cssClass="providerlogo"){
    if (isLightMode()) return "";
    const src = safeText(logo?.local || logo?.tmdb || "").trim();
    if (!src) return "";
    return `<img class="${escHtml(cssClass)}" src="${escHtml(src)}" loading="lazy" decoding="async" data-fallback="${escHtml(logo?.tmdb || "")}" alt="${escHtml(logo?.name || "Provider")}" onerror="const fallback=this.dataset.fallback||'';if(fallback&&this.src!==fallback){this.src=fallback;this.dataset.fallback='';return;}this.onerror=null;const chip=this.closest('.providerchip,.provider-anchor');if(chip){chip.classList.add('fallback-only');}this.remove();" />`;
  }

  function providerChipHtml(logo, href){
    const hasLogo = !!safeText(logo?.local || logo?.tmdb || "").trim();
    const stateClass = hasLogo ? "" : " no-logo";
    const inner = `${providerLogoImgHtml(logo)}<span class="providertext">${escHtml(logo?.name || "Provider")}</span>`;
    if (href){
      return `<a class="providerchip${stateClass}" href="${escHtml(href)}" target="_blank" rel="noopener">${inner}</a>`;
    }
    return `<span class="providerchip${stateClass}">${inner}</span>`;
  }

  function providerDisplayLabel(name){
    const raw = safeText(name).trim();
    const compact = raw.toLowerCase().replace(/\s+/g, " ");
    if (!compact) return "Provider";
    if (/^amazon video$|^amazon prime video$/.test(compact)) return "Amazon";
    if (/^apple tv store$/.test(compact)) return "Apple TV";
    if (/^google play movies$/.test(compact)) return "Google Play";
    if (/^netflix\b/.test(compact)) return "Netflix";
    if (/^outtv\b/.test(compact)) return "OUTtv";
    if (/^crave\b/.test(compact)) return "Crave";
    if (/^paramount plus (premium|essential|basic)/.test(compact)) return "Paramount Plus";
    if (/^paramount(\+| plus).*(amazon|apple tv|roku|channel)/.test(compact)) return "Paramount+";
    return raw.replace(/\s+$/g, "");
  }

  function providerGroupHtml(item, kind, limit=4){
    const wp = getWatchProviders(item);
    const id = item?.id ?? item?.tmdb_id;
    if (!wp || !id) return `<div class="provider_group"><div class="muted" style="font-size:11px;">Provider data unavailable</div></div>`;
    const providers = collectProvidersForRegion(wp, "CA").length
      ? collectProvidersForRegion(wp, "CA")
      : (collectProvidersForRegion(wp, "US").length ? collectProvidersForRegion(wp, "US") : collectProvidersForRegion(wp, "AU"));
    if (!providers.length) return `<div class="provider_group"><div class="muted" style="font-size:11px;">No providers</div></div>`;
    const watchUrl = safeText(providers[0]?.deep_link) || tmdbWatchUrl(kind, id);
    return `
      <div class="provider_group">
        <div class="providerchips">
          ${providers.slice(0, limit).map(p => providerChipHtml(providerLogoUrl(p), watchUrl)).join("")}
        </div>
      </div>
    `;
  }

  function renderWatchProvidersHtml(item, kind){
    const wp = getWatchProviders(item);
    const id = item?.id ?? item?.tmdb_id;
    if (!wp || !id) return "";
    const regions = ["CA", "US", "GB", "AU"];
    const rows = regions.map(region => {
      const providers = collectProvidersForRegion(wp, region);
      const regionLink = safeText(wp?.[region]?.link || "");
      const canonicalProviders = [];
      const seenLabels = new Set();
      providers.forEach(p => {
        const label = providerDisplayLabel(p?.provider_name || p?.name || "Provider");
        const key = label.toLowerCase();
        if (seenLabels.has(key)) return;
        seenLabels.add(key);
        canonicalProviders.push({ provider: p, label });
      });
      const chips = canonicalProviders.slice(0, 6).map(entry => {
        const p = entry.provider;
        const href = safeText(p?.deep_link) || regionLink || tmdbWatchUrl(kind, id);
        const label = entry.label;
        const logo = { ...providerLogoUrl(p), name: label };
        const hasLogo = !!safeText(logo?.local || logo?.tmdb || "").trim();
        const logoHtml = providerLogoImgHtml(logo, "providerlogo providerlogo--popup");
        const textClass = hasLogo && logoHtml ? "providertext providertext--fallback" : "providertext providertext--visible";
        return `<a class="provider-anchor${hasLogo ? "" : " no-logo"}" href="${escHtml(href)}" target="_blank" rel="noopener" title="${escHtml(label)}" aria-label="${escHtml(label)}">${logoHtml}<span class="${textClass}">${escHtml(label)}</span></a>`;
      }).join("");
      const fallbackHref = regionLink || tmdbWatchUrl(kind, id);
      const body = chips || (fallbackHref
        ? `<a class="provider-anchor no-logo" href="${escHtml(fallbackHref)}" target="_blank" rel="noopener" title="TMDB watch page" aria-label="TMDB watch page"><span class="providertext providertext--visible">TMDB watch page</span></a>`
        : `<span class="provider-empty">No providers</span>`);
      return `
        <div class="providerrow">
          <span class="providerlabel">${region}</span>
          <div class="providerchips providerchips--popup">${body}</div>
        </div>`;
    }).join("");

    return `
      <div class="providerblock">
        <div class="providerrows">${rows}</div>
      </div>`;
  }

  function renderPopupMediaDetailBlock(kind, item, context={}){
    const normalizedKind = safeText(kind).toLowerCase();
    if (normalizedKind === "episode"){
      const show = context.show || {};
      const seasonNum = Number(item?.season_number ?? context.seasonNum ?? context.seasonNumber ?? 0) || 0;
      const episodeNum = Number(item?.episode_number ?? context.episodeNum ?? context.episodeNumber ?? 0) || 0;
      return window.MyTVHubSharedModules.popupController.renderMediaDetailBlockHtml({
        kind: "episode",
        primary: safeText(show?.title || show?.name || item?.show_title || "Show"),
        secondary: safeText(item?.title || item?.name || item?.episode_name || `Episode ${episodeNum}`),
        meta: episodeMetaLine(seasonNum, episodeNum, item?.runtime, safeText(item?.episode_tmdb_id ?? item?.episode_id ?? item?.tmdb_episode_id ?? item?.id ?? "")),
        date: pickAirDate(item) ? fmtDate(pickAirDate(item)) : "",
        overview: truncateText(item?.overview || "", 320)
      });
    }
    if (normalizedKind === "movie"){
      const runtime = Number(item?.runtime);
      const releaseDate = pickAirDate(item) || item?.release_date || "";
      const meta = [
        Number.isFinite(runtime) && runtime > 0 ? `${runtime} min` : "",
        releaseDate ? fmtDate(releaseDate) : ""
      ].filter(Boolean).join(" • ");
      return window.MyTVHubSharedModules.popupController.renderMediaDetailBlockHtml({
        kind: "movie",
        primary: safeText(item?.title || "Movie"),
        meta,
        overview: truncateText(item?.overview || "", 320)
      });
    }
    return "";
  }

  function progressPercent(obj){
    if (!obj || typeof obj !== "object") return null;
    const raw = obj.watch_progress?.percent ?? obj.watch_progress?.pct ?? obj.watch_progress?.progress ??
      obj.progress?.percent ?? obj.progress?.pct ?? obj.progress?.progress ??
      obj.watch_progress ?? obj.progress;
    const num = Number(raw);
    if (!Number.isFinite(num)) return null;
    const pct = num <= 1 ? num * 100 : num;
    if (pct < 0 || pct > 100) return null;
    return pct;
  }

  function watchedEpisodePercent(showId, seasonNum, episodeNum){
    const ws = state.watchState;
    if (!ws || !ws.shows) return null;
    const show = ws.shows[String(showId)];
    if (!show || !show.seasons) return null;
    const season = show.seasons[String(seasonNum)];
    if (!season || !Array.isArray(season.episodes)) return null;
    if (season.episodes.includes(Number(episodeNum))) return 100;
    return null;
  }

  function watchedMoviePercent(movieId){
    const ws = state.watchState;
    if (!ws || !ws.movies) return null;
    return ws.movies[String(movieId)] ? 100 : null;
  }

  function watchFlagHtml(watched){
    return `<span class="flag ${watched ? "watched" : "unwatched"}">${watched ? "Watched" : "Unwatched"}</span>`;
  }

  function nowUtcIso(){
    try { return new Date().toISOString(); } catch { return ""; }
  }

  function todayKey(){
    const d = new Date();
    return toDateKey(d);
  }

  function isDateAvailable(dateStr){
    const key = safeText(dateStr).slice(0,10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(key)) return false;
    return key <= todayKey();
  }

  function availabilityStatusOf(item){
    const raw = safeText(item?.availability_status).toLowerCase();
    const release = pickAirDate(item);
    if (release) return isDateAvailable(release) ? "available" : "not_yet_released";
    if (raw === "available" || raw === "unavailable" || raw === "not_yet_released" || raw === "unknown") return raw;
    return "unknown";
  }

  function availabilityLabelOf(item){
    return window.MyTVHubSharedModules.availabilityUi.availabilityLabel(availabilityStatusOf(item));
  }

  function availabilityBadgeHtml(item, options = {}){
    return window.MyTVHubSharedModules.availabilityUi.availabilityBadgeHtml(availabilityStatusOf(item), options);
  }

  function isShowAvailable(show){
    return availabilityStatusOf(show) === "available";
  }

  function isSeasonAvailable(season){
    return availabilityStatusOf(season) === "available";
  }

  function isEpisodeAvailable(ep){
    return availabilityStatusOf(ep) === "available";
  }

  function pickAirDate(obj){
    return safeText(obj?.air_date || obj?.first_aired || obj?.first_air_date || obj?.release_date || "");
  }

  function isMovieAvailable(movie){
    return availabilityStatusOf(movie) === "available";
  }

  function editorApiUrl(path=""){
    const clean = safeText(path).startsWith("/") ? safeText(path) : `/${safeText(path)}`;
    return `http://127.0.0.1:8787${clean}`;
  }

  async function checkApiAvailable(){
    try {
      const r = await fetch(editorApiUrl("/api/health"), { cache: "no-store" });
      return r.ok;
    } catch {
      return false;
    }
  }

  async function checkInputsEditorServerAvailable(){
    try {
      const r = await fetch(editorApiUrl("/api/health"), { cache: "no-store" });
      return r.ok;
    } catch {
      return false;
    }
  }

  function ensureLocalWatchState(){
    if (!state.inputs) state.inputs = { tv: [], movies: [], watchlist: [] };
    if (!state.inputs.watch_state || typeof state.inputs.watch_state !== "object") state.inputs.watch_state = {};
    if (!state.inputs.watch_state.local || typeof state.inputs.watch_state.local !== "object") {
      state.inputs.watch_state.local = { generated_utc: nowUtcIso(), movies: {}, shows: {} };
    }
    const local = state.inputs.watch_state.local;
    if (!local.movies || typeof local.movies !== "object") local.movies = {};
    if (!local.shows || typeof local.shows !== "object") local.shows = {};
    return local;
  }

  function setWatchStateSource(){
    if (state.inputs){
      const local = ensureLocalWatchState();
      state.watchState = local;
      state.watchStateSource = "local";
      return;
    }
    const trakt = state.data?.watch_state?.trakt;
    if (trakt && typeof trakt === "object"){
      state.watchState = trakt;
      state.watchStateSource = "trakt";
      return;
    }
    state.watchState = null;
    state.watchStateSource = null;
  }

  async function saveInputs(){
    if (!state.apiAvailable){
      state.inputsDirty = true;
      return false;
    }
    try{
      const r = await fetch(editorApiUrl("/api/inputs"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(state.inputs || {})
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      state.inputsDirty = false;
      return true;
    }catch{
      state.inputsDirty = true;
      return false;
    }
  }

  function isEpisodeWatched(showId, seasonNum, episodeNum){
    if (canonicalStateValue("watched_status", {
      kind: "episode",
      showId,
      seasonNumber: seasonNum,
      episodeNumber: episodeNum
    }, "") === "watched") return true;
    const ws = state.watchState;
    const show = ws?.shows?.[String(showId)];
    const season = show?.seasons?.[String(seasonNum)];
    if (!season || !Array.isArray(season.episodes)) return false;
    return season.episodes.includes(Number(episodeNum));
  }

  function isSeasonWatched(showId, seasonNum, totalEpisodes){
    const ws = state.watchState;
    const show = ws?.shows?.[String(showId)];
    const season = show?.seasons?.[String(seasonNum)];
    if (!season || !Array.isArray(season.episodes)) return false;
    if (!Number.isFinite(totalEpisodes) || totalEpisodes <= 0) return season.episodes.length > 0;
    return season.episodes.length >= totalEpisodes;
  }

  function setMovieWatched(movieId, watched){
    const ws = ensureLocalWatchState();
    const key = String(movieId);
    if (watched){
      ws.movies[key] = ws.movies[key] || { last_watched_at: nowUtcIso(), plays: 1 };
      ws.movies[key].last_watched_at = nowUtcIso();
    } else {
      delete ws.movies[key];
    }
    ws.generated_utc = nowUtcIso();
    state.watchState = ws;
    state.watchStateSource = "local";
    saveInputs();
  }

  function setEpisodeWatched(showId, seasonNum, episodeNum, watched){
    const ws = ensureLocalWatchState();
    const sid = String(showId);
    const sn = String(seasonNum);
    const epn = Number(episodeNum);
    if (!ws.shows[sid]) ws.shows[sid] = { seasons: {} };
    if (!ws.shows[sid].seasons[sn]) ws.shows[sid].seasons[sn] = { episodes: [] };
    const arr = ws.shows[sid].seasons[sn].episodes || [];
    const has = arr.includes(epn);
    if (watched && !has) arr.push(epn);
    if (!watched && has) ws.shows[sid].seasons[sn].episodes = arr.filter(n => n !== epn);
    ws.shows[sid].seasons[sn].episodes = ws.shows[sid].seasons[sn].episodes.sort((a,b)=>a-b);
    if (!ws.shows[sid].seasons[sn].episodes.length){
      delete ws.shows[sid].seasons[sn];
    }
    if (!Object.keys(ws.shows[sid].seasons || {}).length){
      delete ws.shows[sid];
    }
    ws.generated_utc = nowUtcIso();
    state.watchState = ws;
    state.watchStateSource = "local";
    saveInputs();
  }

  function setSeasonWatched(showId, seasonNum, episodeNums, watched){
    const ws = ensureLocalWatchState();
    const sid = String(showId);
    const sn = String(seasonNum);
    if (!ws.shows[sid]) ws.shows[sid] = { seasons: {} };
    if (watched){
      ws.shows[sid].seasons[sn] = { episodes: (episodeNums || []).map(n => Number(n)).filter(n => Number.isFinite(n)).sort((a,b)=>a-b) };
    } else {
      delete ws.shows[sid].seasons[sn];
    }
    if (!Object.keys(ws.shows[sid].seasons || {}).length){
      delete ws.shows[sid];
    }
    ws.generated_utc = nowUtcIso();
    state.watchState = ws;
    state.watchStateSource = "local";
    saveInputs();
  }

  function setShowWatched(showId, seasons, watched){
    const ws = ensureLocalWatchState();
    const sid = String(showId);
    if (watched){
      ws.shows[sid] = { seasons: {} };
      for (const se of (seasons || [])){
        const sn = String(se?.season_number ?? se?.number ?? "");
        if (!sn) continue;
        const eps = (se?.episodes || []).map(e => Number(e?.episode_number ?? e?.number)).filter(n => Number.isFinite(n));
        ws.shows[sid].seasons[sn] = { episodes: eps.sort((a,b)=>a-b) };
      }
    } else {
      delete ws.shows[sid];
    }
    ws.generated_utc = nowUtcIso();
    state.watchState = ws;
    state.watchStateSource = "local";
    saveInputs();
  }

  function tmdbImageBase(){
    const base = safeText(state.cfg?.image_cache?.tmdb_image_base || "https://image.tmdb.org/t/p").trim();
    return base.replace(/\/+$/,"");
  }

  function tmdbSizeTag(kind){
    const sz = state.cfg?.image_sizes || {};
    let w = null;
    if (kind === "show_poster") w = Number(sz.show_width);
    else if (kind === "movie_poster") w = Number(sz.movie_width);
    else if (kind === "season_poster") w = Number(sz.season_width);
    else if (kind === "episode_still") w = Number(sz.episode_still_w);
    else if (kind === "backdrop") w = Number(sz.backdrop_w);
    const posterSizes = [92, 154, 185, 342, 500, 780];
    const stillSizes = [92, 185, 300, 500];
    const backdropSizes = [300, 780, 1280];
    const snap = (req, allowed) => {
      if (!Number.isFinite(req) || req <= 0) return null;
      for (const a of allowed){
        if (req <= a) return a;
      }
      return allowed[allowed.length - 1] || null;
    };
    if (kind === "show_poster" || kind === "movie_poster" || kind === "season_poster"){
      w = snap(w, posterSizes);
    } else if (kind === "episode_still") {
      w = snap(w, stillSizes);
    } else if (kind === "backdrop") {
      w = snap(w, backdropSizes);
    }
    return w ? `w${Math.round(w)}` : "original";
  }

  function tmdbImageUrl(kind, tmdbPath){
    const p = safeText(tmdbPath).trim();
    if (!p) return "";
    if (/^https?:\/\//i.test(p)) return p;
    if (!p.startsWith("/")) return "";
    return `${tmdbImageBase()}/${tmdbSizeTag(kind)}${p}`;
  }

  function inferPosterKind(obj){
    if (obj && Object.prototype.hasOwnProperty.call(obj, "season_number")) return "season_poster";
    if (obj && Object.prototype.hasOwnProperty.call(obj, "release_date") && !Object.prototype.hasOwnProperty.call(obj, "first_air_date")) return "movie_poster";
    return "show_poster";
  }

  function imageKindForKey(obj, key){
    const clean = safeText(key).toLowerCase();
    if (clean.includes("still") || clean.includes("thumb")) return "episode_still";
    if (clean.includes("backdrop")) return "backdrop";
    if (clean.includes("season")) return "season_poster";
    if (clean.includes("poster")) return inferPosterKind(obj);
    return inferPosterKind(obj);
  }

  function pickImage(obj, ...keys){
    if (isLightMode()) return "";
    if (!obj) return "";
    const searchKeys = keys.length ? keys : ["poster_local", "poster_path"];
    for (const key of searchKeys){
      const rawPath = safeText(obj[key]).trim();
      if (!rawPath) continue;
      if (/^https?:\/\//i.test(rawPath)) return rawPath;
      if (rawPath.startsWith("/assets/")) return withBasePath(rawPath);
      if (rawPath.startsWith("/")) {
        const tmdb = tmdbImageUrl(imageKindForKey(obj, key), rawPath);
        if (tmdb) return tmdb;
        return withBasePath(rawPath);
      }
      return withBasePath(rawPath);
    }
    return "";
  }

  function linkOrDisabled(iconKey, href, label){
    const ok = !!href;
    const safeHref = ok ? href : "#";
    const kind = iconClassForKey(iconKey);
    const icon = iconChar(iconKey, iconChar("action_external_links", ""));
    const title = label || iconName(iconKey, iconKey);
    const inner = `<span class="btnicon">${escHtml(icon)}</span>${escHtml(title)}`;
    return `<a class="btn ${kind}" href="${escHtml(safeHref)}" target="_blank" rel="noopener" aria-disabled="${ok?"false":"true"}" data-function-type="${escHtml(iconType(iconKey, "link"))}">${inner}</a>`;
  }

  function yearFromDate(d){
    const y = safeText(d).slice(0,4);
    return /^\d{4}$/.test(y) ? y : "";
  }

  function dateValue(value){
    const parsed = Date.parse(safeText(value));
    return Number.isFinite(parsed) ? parsed : null;
  }

  function currentWindowDays(key, fallback){
    const raw = state.cfg?.browse?.current?.[key];
    const value = Number(raw);
    return Number.isFinite(value) && value > 0 ? value : fallback;
  }

  function isCurrentShow(show, nowMs = Date.now()){
    const firstAir = dateValue(show?.first_air_date);
    if (firstAir !== null && firstAir > nowMs) return false;
    const statusText = safeText(show?.status).trim().toLowerCase();
    if (["ended", "canceled", "cancelled"].includes(statusText)) return false;
    const recentCutoff = nowMs - (currentWindowDays("show_activity_window_days", DEFAULT_CURRENT_SHOW_ACTIVITY_WINDOW_DAYS) * DAY_MS);
    const recentActivity = dateValue(
      show?.last_air_date ||
      show?.latest_episode_to_air?.air_date ||
      show?.last_episode_to_air?.air_date
    );
    return recentActivity !== null && recentActivity >= recentCutoff;
  }

  function isCurrentMovie(movie, nowMs = Date.now()){
    const release = dateValue(movie?.release_date);
    if (release === null) return false;
    const recentCutoff = nowMs - (currentWindowDays("movie_release_window_days", DEFAULT_CURRENT_MOVIE_RELEASE_WINDOW_DAYS) * DAY_MS);
    if (release < recentCutoff) return false;
    if (release <= nowMs) return true;
    const lookahead = nowMs + (currentWindowDays("movie_release_lookahead_days", DEFAULT_CURRENT_MOVIE_RELEASE_LOOKAHEAD_DAYS) * DAY_MS);
    return release <= lookahead && availabilityStatusOf(movie) === "available";
  }

  function uniqueSorted(arr){
    return Array.from(new Set(arr.filter(Boolean))).sort((a,b)=>safeText(a).localeCompare(safeText(b)));
  }

  const WATCHLIST_STATUS_OPTIONS = [
    { value: "watchlist", label: "Watchlist" },
    { value: "watching", label: "Watching" },
    { value: "paused", label: "Paused" },
    { value: "completed", label: "Completed" },
    { value: "dropped", label: "Dropped" }
  ];

  function populateFilters(){
    const shows = Array.isArray(state.data?.shows) ? state.data.shows : [];
    const movies = Array.isArray(state.data?.movies) ? state.data.movies : [];
    const watchlist = Array.isArray(state.inputs?.watchlist) ? state.inputs.watchlist : [];
    const hasWatchlist = watchlist.length > 0;

    const showGenres = uniqueSorted(shows.flatMap(s => (s.genres || []).map(g => g?.name)));
    const movieGenres = uniqueSorted(movies.flatMap(m => (m.genres || []).map(g => g?.name)));
    const showYears = uniqueSorted(shows.map(s => yearFromDate(s.first_air_date)).filter(Boolean)).sort((a,b)=>Number(b)-Number(a));
    const movieYears = uniqueSorted(movies.map(m => yearFromDate(m.release_date)).filter(Boolean)).sort((a,b)=>Number(b)-Number(a));
    const movieCollections = uniqueSorted(movies.map(m => m?.collection?.name).filter(Boolean));

    renderChecklist($("#filterShowsGenres"), showGenres, state.filters.shows.genres);
    renderChecklist($("#filterMoviesGenres"), movieGenres, state.filters.movies.genres);

    const showsYearSel = $("#filterShowsYear");
    if (showsYearSel){
      showsYearSel.innerHTML = `<option value="">All years</option>${showYears.map(year => `<option value="${escHtml(year)}">${escHtml(year)}</option>`).join("")}`;
      showsYearSel.value = state.filters.shows.year || "";
    }
    const moviesYearSel = $("#filterMoviesYear");
    if (moviesYearSel){
      moviesYearSel.innerHTML = `<option value="">All years</option>${movieYears.map(year => `<option value="${escHtml(year)}">${escHtml(year)}</option>`).join("")}`;
      moviesYearSel.value = state.filters.movies.year || "";
    }

    const moviesCollectionInput = $("#filterMoviesCollection");
    if (moviesCollectionInput){
      moviesCollectionInput.innerHTML = `<option value="">All collections</option>${movieCollections.map(name => `<option value="${escHtml(name)}">${escHtml(name)}</option>`).join("")}`;
      moviesCollectionInput.value = state.filters.movies.collection || "";
    }

    setSegActive($("#filterShowsAvailability"), "availability", state.filters.shows.availability || "all");
    setSegActive($("#filterMoviesAvailability"), "availability", state.filters.movies.availability || "all");

    setSegActive($("#filterShowsWatched"), "watched", state.filters.shows.watched || "all");
    setSegActive($("#filterMoviesWatched"), "watched", state.filters.movies.watched || "all");

    setSegActive($("#filterShowsWatchlist"), "watchlist", state.filters.shows.watchlist || "all");
    setSegActive($("#filterMoviesWatchlist"), "watchlist", state.filters.movies.watchlist || "all");
    setSegActive($("#filterShowsScope"), "scope", state.filters.shows.scope || "all");
    setSegActive($("#filterMoviesScope"), "scope", state.filters.movies.scope || "all");

    const sortShows = $("#sortShows");
    if (sortShows) sortShows.value = state.sort.shows || "title";
    const sortMovies = $("#sortMovies");
    if (sortMovies) sortMovies.value = state.sort.movies || "title";

    if (!hasWatchlist){
      $$("#filterShowsWatchlist .segbtn, #filterMoviesWatchlist .segbtn").forEach(btn => {
        btn.disabled = true;
      });
    }

    const watchlistStatusSel = $("#filterWatchlistStatus");
    if (watchlistStatusSel){
      watchlistStatusSel.innerHTML = `<option value="all">All Watch Status</option>${WATCHLIST_STATUS_OPTIONS.map(o => `<option value="${escHtml(o.value)}">${escHtml(o.label)}</option>`).join("")}`;
    }
    const watchlistKindSel = $("#filterWatchlistKind");
    if (watchlistKindSel){
      watchlistKindSel.innerHTML = `<option value="all">All Types</option><option value="show">Shows</option><option value="movie">Movies</option><option value="unknown">Unknown</option>`;
    }
  }

  function getSelectedValues(sel){
    if (!sel) return [];
    return Array.from(sel.selectedOptions || []).map(o => o.value).filter(Boolean);
  }

  function getCheckedValues(container){
    if (!container) return [];
    return $$("input[type='checkbox']", container).filter(i => i.checked).map(i => i.value);
  }

  function renderChecklist(container, options, selectedValues){
    if (!container) return;
    const selected = new Set(selectedValues || []);
    container.innerHTML = options.map(opt => {
      const value = typeof opt === "string" ? opt : opt.value;
      const label = typeof opt === "string" ? opt : opt.label;
      const checked = selected.has(value) ? "checked" : "";
      return `<label class="checkitem"><input type="checkbox" value="${escHtml(value)}" ${checked} /> <span>${escHtml(label)}</span></label>`;
    }).join("");
  }

  function actionMenuHtml(kind, id, title){
    return `
      <div class="actionmenu" data-action-menu-panel="1" data-menu-type="want">
        <button type="button" class="menu-close" data-menu-close="1" aria-label="Close">✕</button>
        <div class="menutitle">Want</div>
        <button type="button" data-menu-action="want_add" data-kind="${escHtml(kind)}" data-id="${escHtml(id)}" data-title="${escHtml(title)}">Add to want</button>
        <button type="button" data-menu-action="want_remove" data-kind="${escHtml(kind)}" data-id="${escHtml(id)}">Remove from want</button>
      </div>
      <div class="actionmenu" data-action-menu-panel="1" data-menu-type="watched">
        <button type="button" class="menu-close" data-menu-close="1" aria-label="Close">✕</button>
        <button type="button" data-menu-action="mark_watched" data-kind="${escHtml(kind)}" data-id="${escHtml(id)}">Mark watched</button>
        <button type="button" data-menu-action="mark_unwatched" data-kind="${escHtml(kind)}" data-id="${escHtml(id)}">Mark unwatched</button>
      </div>
      <div class="actionmenu" data-action-menu-panel="1" data-menu-type="rate">
        <button type="button" class="menu-close" data-menu-close="1" aria-label="Close">✕</button>
        <div class="menutitle">Rating</div>
        <button type="button" disabled>Rating not set</button>
      </div>
    `;
  }

  function statusMenuHtml(kind, id, title, context={}, available=false){
    const current = getLocalStatusValue(kind, id, context);
    const contextAttrs = [
      (context?.showId != null ? ` data-status-show="${escHtml(context.showId)}"` : ""),
      (context?.seasonNumber != null ? ` data-status-season="${escHtml(context.seasonNumber)}"` : ""),
      (context?.episodeNumber != null ? ` data-status-episode="${escHtml(context.episodeNumber)}"` : "")
    ].join("");
    const options = WATCHLIST_STATUS_OPTIONS.map(opt => {
      const active = opt.value === current;
      const color = watchStatusChoiceColor(opt.value, available);
      const label = watchStatusChoiceTitle(opt.value, available);
      return `<button type="button"${active ? ` class="active"` : ""} data-menu-action="status_set" data-kind="${escHtml(kind)}" data-id="${escHtml(id)}" data-title="${escHtml(title || "")}" data-status-value="${escHtml(opt.value)}"${contextAttrs} style="--watch-status-color:${escHtml(color)}"><span class="bulletrow"><span class="bulletdot"></span><span>${escHtml(label)}</span></span>${active ? `<span aria-hidden="true">•</span>` : ""}</button>`;
    }).join("");
    return `
      <div class="actionmenu statusmenu" data-action-menu-panel="1" data-menu-type="status">
        <button type="button" class="menu-close" data-menu-close="1" aria-label="Close">✕</button>
        <div class="menutitle">Watch status</div>
        ${options}
        <div class="divider"></div>
        <button type="button" data-menu-action="status_clear" data-kind="${escHtml(kind)}" data-id="${escHtml(id)}" data-title="${escHtml(title || "")}"${contextAttrs}>Clear status</button>
      </div>
    `;
  }

  function closeAllActionMenus(){
    $$("[data-action-menu-panel]").forEach(m => m.classList.remove("open"));
  }

  function positionActionMenu(menu, btn, host){
    if (!menu || !btn || !host) return;
    const wasOpen = menu.classList.contains("open");
    menu.classList.add("open");
    menu.style.visibility = "hidden";
    const hostRect = host.getBoundingClientRect();
    const btnRect = btn.getBoundingClientRect();
    const menuRect = menu.getBoundingClientRect();
    let left = btnRect.left - hostRect.left;
    let top = btnRect.bottom - hostRect.top + 6;
    if (left + menuRect.width > hostRect.width - 6){
      left = Math.max(6, hostRect.width - menuRect.width - 6);
    }
    if (left < 6) left = 6;
    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
    menu.style.visibility = "";
    if (!wasOpen){
      menu.classList.remove("open");
    }
  }

  function wireActionMenus(container){
    if (!container) return;
    $$("[data-action-menu]", container).forEach(btn => {
      const host = btn.closest("[data-action-host]") || btn.parentElement;
      const openMenu = () => {
        const target = safeText(btn.getAttribute("data-action-menu"));
        const menu = host ? host.querySelector(`[data-action-menu-panel][data-menu-type="${target}"]`) : null;
        if (!menu) return;
        positionActionMenu(menu, btn, host);
        const open = !menu.classList.contains("open");
        closeAllActionMenus();
        menu.classList.toggle("open", open);
      };
      const runDefault = () => {
        const target = safeText(btn.getAttribute("data-action-menu"));
        const menu = host ? host.querySelector(`[data-action-menu-panel][data-menu-type="${target}"]`) : null;
        if (!menu) return;
        const first = menu.querySelector("[data-menu-action]");
        if (first) first.click();
      };
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const target = safeText(btn.getAttribute("data-action-menu"));
        if (target === "status" || target === "rate"){
          openMenu();
          return;
        }
        if (btn.getAttribute("data-no-default") === "1" || btn.hasAttribute("data-action")) return;
        runDefault();
      });
      btn.addEventListener("dblclick", (e) => {
        e.stopPropagation();
        openMenu();
      });
    });
    $$("[data-menu-close]", container).forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        closeAllActionMenus();
      });
    });
    $$("[data-menu-action]", container).forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const action = safeText(btn.getAttribute("data-menu-action"));
        const kind = safeText(btn.getAttribute("data-kind"));
        const id = parseInt(btn.getAttribute("data-id") || "0", 10);
        const title = safeText(btn.getAttribute("data-title"));
        const context = {
          showId: btn.getAttribute("data-status-show"),
          seasonNumber: btn.getAttribute("data-status-season"),
          episodeNumber: btn.getAttribute("data-status-episode")
        };
        if (!action || !Number.isFinite(id)) return;
        if (action === "want_add"){
          setWatchlistEntry(id, title, kind, "watchlist");
        } else if (action === "want_remove"){
          removeWatchlistItem(id);
        } else if (action === "mark_watched"){
          if (kind === "movie") setMovieWatched(id, true);
          if (kind === "show"){
            const show = await getShowDetailById(id);
            if (show) setShowWatched(id, show.seasons || [], true);
          }
        } else if (action === "mark_unwatched"){
          if (kind === "movie") setMovieWatched(id, false);
          if (kind === "show"){
            const show = await getShowDetailById(id);
            if (show) setShowWatched(id, show.seasons || [], false);
          }
        } else if (action === "status_set"){
          const statusValue = safeText(btn.getAttribute("data-status-value")).toLowerCase();
          setLocalStatusValue(kind, id, context, statusValue, title);
        } else if (action === "status_clear"){
          setLocalStatusValue(kind, id, context, "", title);
        }
        await saveInputs();
        closeAllActionMenus();
        if ($("#modalBack")?.style.display === "flex"){
          if (kind === "movie"){
            await openMovieModal(id);
          } else {
            const showId = Number(context.showId || id) || 0;
            await openShowModal(showId);
          }
        }
        if (state.tab === "calendar") renderCalendar();
        if (state.tab === "shows") renderShows();
        if (state.tab === "movies") renderMovies();
        if (state.tab === "dashboard" && typeof renderDashboard === "function") renderDashboard();
      });
    });
  }

  async function toggleWantForKind(kind, id, title){
    if (!Number.isFinite(id)) return;
    const wanted = getWatchlistSet().has(String(id));
    if (wanted){
      removeWatchlistItem(id);
    } else {
      setWatchlistEntry(id, title, kind, "watchlist");
    }
  }

  async function toggleWatchedForKind(kind, id, context={}){
    if (!Number.isFinite(id)) return;
    if (kind === "movie"){
      setMovieWatched(id, !isMovieWatched(getMovieById(id) || { tmdb_id: id }));
      return;
    }
    if (kind === "episode"){
      const showId = Number(context.showId || 0);
      const seasonNum = Number(context.seasonNumber || 0);
      const episodeNum = Number(context.episodeNumber || id);
      if (!Number.isFinite(showId) || !Number.isFinite(seasonNum) || !Number.isFinite(episodeNum)) return;
      setEpisodeWatched(showId, seasonNum, episodeNum, !isEpisodeWatched(showId, seasonNum, episodeNum));
      return;
    }
    const show = await getShowDetailById(id);
    if (show) setShowWatched(id, show.seasons || [], !isShowWatched(show));
  }

  function openInfoForKind(kind, id){
    if (!Number.isFinite(id)) return;
    if (kind === "movie") return openMovieModal(id);
    return gotoShow(id);
  }

  function wireIconStripActions(container, onUpdate){
    if (!container) return;
    $$("[data-action='open-info']", container).forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const kind = safeText(btn.getAttribute("data-kind"));
        const id = parseInt(btn.getAttribute("data-id") || "0", 10);
        openInfoForKind(kind, id);
      });
    });
    $$("[data-action='toggle-want']", container).forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const kind = safeText(btn.getAttribute("data-kind"));
        const id = parseInt(btn.getAttribute("data-id") || "0", 10);
        const title = safeText(btn.getAttribute("data-title"));
        await toggleWantForKind(kind, id, title);
        await saveInputs();
        if (typeof onUpdate === "function") onUpdate();
      });
    });
    $$("[data-action='toggle-watched']", container).forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const kind = safeText(btn.getAttribute("data-kind"));
        const id = parseInt(btn.getAttribute("data-id") || "0", 10);
        const context = {
          showId: btn.getAttribute("data-show"),
          seasonNumber: btn.getAttribute("data-season"),
          episodeNumber: btn.getAttribute("data-watch-episode") || btn.getAttribute("data-episode")
        };
        await toggleWatchedForKind(kind, id, context);
        await saveInputs();
        if (typeof onUpdate === "function") onUpdate();
      });
    });
  }

  function getEyeMode(kind){
    return safeText(state.view?.[kind]?.eye || "show_all");
  }

  function applyEyeFilter(kind, item){
    const mode = getEyeMode(kind);
    if (mode === "show_all") return { hide:false, fade:false };
    const watched = kind === "movies" ? isMovieWatched(item) : isShowWatched(item);
    const id = String(item?.tmdb_id ?? "");
    const inWatchlist = !!(id && canonicalWatchListActive(kind === "movies" ? "movie" : "show", id, getWatchlistSet().has(id)));
    const inLibrary = !!(item?.in_library || item?.library || item?.inLibrary);
    const rated = !!(item?.rating || item?.user_rating || item?.rating_user);
    const listed = inWatchlist; // nearest proxy for now
    const map = {
      watched,
      unwatched: !watched,
      watchlist: inWatchlist,
      not_watchlist: !inWatchlist,
      library: inLibrary,
      not_library: !inLibrary,
      rated,
      not_rated: !rated,
      listed,
      not_listed: !listed
    };
    const isFade = mode.startsWith("fade_");
    const key = mode.replace(/^fade_/, "").replace(/^hide_/, "");
    const match = !!map[key];
    if (isFade) return { hide:false, fade:match };
    return { hide:match, fade:false };
  }

  function setSegActive(container, attr, value){
    if (!container) return;
    $$(`[data-${attr}]`, container).forEach(btn => {
      const active = btn.getAttribute(`data-${attr}`) === value;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function setSelectedValues(sel, values){
    if (!sel) return;
    const want = new Set((Array.isArray(values) ? values : []).map(String));
    Array.from(sel.options || []).forEach(opt => {
      opt.selected = want.has(String(opt.value));
    });
  }

  function initEyeMenu(btnId, menuId, kind){
    const btn = document.getElementById(btnId);
    const menu = document.getElementById(menuId);
    if (!btn || !menu) return;
    const close = () => {
      menu.classList.remove("open");
      menu.setAttribute("aria-hidden", "true");
    };
    const toggleDefault = () => {
      const curr = getEyeMode(kind);
      const next = curr === "show_all" ? "fade_watched" : "show_all";
      if (state.view?.[kind]) state.view[kind].eye = next;
      close();
      if (kind === "shows") renderShows();
      if (kind === "movies") renderMovies();
    };
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleDefault();
    });
    btn.addEventListener("dblclick", (e) => {
      e.stopPropagation();
      const open = !menu.classList.contains("open");
      menu.classList.toggle("open", open);
      menu.setAttribute("aria-hidden", open ? "false" : "true");
    });
    menu.addEventListener("click", (e) => {
      const closeBtn = e.target.closest("[data-menu-close]");
      if (closeBtn){
        e.stopPropagation();
        close();
        return;
      }
      const item = e.target.closest("[data-eye]");
      if (!item) return;
      const val = safeText(item.getAttribute("data-eye"));
      if (!val) return;
      if (state.view?.[kind]) state.view[kind].eye = val;
      close();
      if (kind === "shows") renderShows();
      if (kind === "movies") renderMovies();
    });
    document.addEventListener("click", (e) => {
      if (menu.classList.contains("open") && !menu.contains(e.target) && e.target !== btn){
        close();
      }
    });
  }

  function initDrawer(btnId, backId, closeId){
    const btn = document.getElementById(btnId);
    const back = document.getElementById(backId);
    const closeBtn = document.getElementById(closeId);
    if (!btn || !back) return;
    const open = () => {
      back.classList.add("open");
      back.setAttribute("aria-hidden", "false");
    };
    const close = () => {
      back.classList.remove("open");
      back.setAttribute("aria-hidden", "true");
    };
    btn.addEventListener("click", open);
    if (closeBtn) closeBtn.addEventListener("click", close);
    back.addEventListener("click", (e) => {
      if (e.target === back) close();
    });
  }

  function getWatchlistSet(){
    const list = Array.isArray(state.inputs?.watchlist) ? state.inputs.watchlist : [];
    const ids = list.map(x => String(x?.tmdb_id ?? "")).filter(Boolean);
    return new Set(ids);
  }

  function ensureWatchlist(){
    if (!state.inputs) state.inputs = { tv: [], movies: [], watchlist: [] };
    if (!Array.isArray(state.inputs.watchlist)) state.inputs.watchlist = [];
    return state.inputs.watchlist;
  }

  function getWatchlistItem(tmdbId){
    const id = String(tmdbId ?? "");
    if (!id) return null;
    const list = ensureWatchlist();
    return list.find(x => String(x?.tmdb_id ?? "") === id) || null;
  }

  function setWatchlistStatus(tmdbId, title, mediaKind, watchStatus){
    const id = String(tmdbId ?? "");
    if (!id) return;
    const list = ensureWatchlist();
    let item = list.find(x => String(x?.tmdb_id ?? "") === id) || null;
    if (!item){
      item = { tmdb_id: Number(id) || id };
      list.push(item);
    }
    if (title) item.title = title;
    if (mediaKind) item.media_kind = mediaKind;
    if (watchStatus) item.watch_status = watchStatus;
    if (!item.watch_status) item.watch_status = "watchlist";
    if (!item.added_utc) item.added_utc = nowUtcIso();
  }

  function removeWatchlistItem(tmdbId){
    const id = String(tmdbId ?? "");
    if (!id) return;
    const list = ensureWatchlist();
    state.inputs.watchlist = list.filter(x => String(x?.tmdb_id ?? "") !== id);
  }

  function isInWatchlist(tmdbId){
    const id = String(tmdbId ?? "");
    if (!id) return false;
    const list = ensureWatchlist();
    return list.some(x => String(x?.tmdb_id ?? "") === id);
  }

  function getWatchlistEntry(tmdbId){
    const id = String(tmdbId ?? "");
    if (!id) return null;
    const list = ensureWatchlist();
    return list.find(x => String(x?.tmdb_id ?? "") === id) || null;
  }

  function ensureLocalStatusMap(){
    if (!state.inputs) state.inputs = { tv: [], movies: [], watchlist: [] };
    if (!state.inputs.local_status_map || typeof state.inputs.local_status_map !== "object") state.inputs.local_status_map = {};
    return state.inputs.local_status_map;
  }

  function statusEntityKey(kind, id, context={}){
    const idStr = String(id ?? "");
    if (kind === "season") return `season:${context.showId || context.parentId || ""}:${context.seasonNumber || idStr}`;
    if (kind === "episode") return `episode:${context.showId || context.parentId || ""}:${context.seasonNumber || ""}:${context.episodeNumber || idStr}`;
    return `${kind}:${idStr}`;
  }

  function getLocalStatusValue(kind, id, context={}){
    const key = statusEntityKey(kind, id, context);
    const localMap = ensureLocalStatusMap();
    const local = localMap[key];
    const localValue = safeText(local?.watch_status).toLowerCase();
    if (localValue) return localValue;
    if (kind === "show" || kind === "movie"){
      const legacy = safeText(getWatchlistEntry(id)?.watch_status).toLowerCase();
      if (legacy) return legacy;
    }
    return "";
  }

  function setLocalStatusValue(kind, id, context, watchStatus, title){
    const key = statusEntityKey(kind, id, context);
    const localMap = ensureLocalStatusMap();
    if (!watchStatus){
      delete localMap[key];
      return;
    }
    localMap[key] = {
      key,
      tmdb_id: id,
      media_kind: kind,
      parent_tmdb_id: context.showId ?? context.parentId ?? null,
      season_number: context.seasonNumber ?? null,
      episode_number: context.episodeNumber ?? null,
      title: title || "",
      watch_status: watchStatus,
      updated_utc: nowUtcIso()
    };
  }

  function setWatchlistEntry(tmdbId, title, mediaKind, watchStatus){
    const id = String(tmdbId ?? "");
    if (!id) return;
    const list = ensureWatchlist();
    let item = list.find(x => String(x?.tmdb_id ?? "") === id) || null;
    if (!item){
      item = { tmdb_id: Number(id) || id };
      list.push(item);
    }
    if (title) item.title = title;
    if (mediaKind) item.media_kind = mediaKind;
    if (watchStatus) item.watch_status = watchStatus;
    if (!item.watch_status) item.watch_status = "watching";
    if (!item.added_utc) item.added_utc = nowUtcIso();
  }

  function cycleWatchStatus(curr){
    const order = ["watching","completed","dropped"];
    const idx = Math.max(0, order.indexOf(curr));
    return order[(idx + 1) % order.length];
  }

  function watchStatusDisplay(entry, available){
    const raw = safeText(entry?.watch_status || "watching").toLowerCase();
    if (raw === "watchlist") return { label: "Watchlist", color: (state.ui?.watch_status_colors?.to_be_watched || "#fef9c3") };
    if (raw === "watching" && !available) return { label: "To Be Watched", color: (state.ui?.watch_status_colors?.to_be_watched || "#fef9c3") };
    if (raw === "paused") return { label: "Paused", color: (state.ui?.watch_status_colors?.paused || "#fde68a") };
    if (raw === "completed") return { label: "Completed", color: (state.ui?.watch_status_colors?.completed || "#bfdbfe") };
    if (raw === "dropped") return { label: "Dropped", color: (state.ui?.watch_status_colors?.dropped || "#fecaca") };
    return { label: "Watching", color: (state.ui?.watch_status_colors?.watching || "#bbf7d0") };
  }

  function watchStatusChoiceColor(value, available){
    const colors = state.ui?.watch_status_colors || {};
    if (value === "watchlist") return colors.to_be_watched || "#fef9c3";
    if (value === "watching" && !available) return colors.to_be_watched || "#fef9c3";
    if (value === "paused") return colors.paused || "#fde68a";
    if (value === "completed") return colors.completed || "#bfdbfe";
    if (value === "dropped") return colors.dropped || "#fecaca";
    return colors.watching || "#bbf7d0";
  }

  function watchStatusChoiceTitle(value, available){
    if (value === "watchlist") return "Watchlist";
    if (value === "watching") return available ? "Watching" : "To Be Watched";
    if (value === "paused") return "Paused";
    if (value === "completed") return "Completed";
    if (value === "dropped") return "Dropped";
    return "Watching";
  }

  function watchToggleHtml(kind, attrs, checked){
    const pairs = Object.entries(attrs || {})
      .filter(([, value]) => value != null && value !== "")
      .map(([key, value]) => ` ${escHtml(key)}="${escHtml(value)}"`)
      .join("");
    return `
      <label class="switch ${escHtml(kind)}">
        <input type="checkbox"${pairs}${checked ? " checked" : ""} />
        <span class="track">
          <span class="thumb"></span>
          <span class="ontext">On</span>
          <span class="offtext">Off</span>
        </span>
      </label>
    `;
  }

  function buildActionBarHtml(kind, id, options={}){
    const title = safeText(options.title || options.titleText || "").trim();
    const statusContext = options.statusContext || {};
    const availabilityStatus = safeText(options.availabilityStatus || "").trim();
    const releaseStatus = /^(not_yet_released|unreleased)$/i.test(availabilityStatus) ? availabilityStatus : "";
    const episodeTmdbForState = safeText(options.tmdbId ?? options.tmdb_id ?? "");
    const episodeShowIdForState = safeText(options.showId ?? options.show_id ?? statusContext.showId ?? "");
    const explicitTmdbForState = safeText(options.tmdbId ?? options.tmdb_id ?? "");
    const tmdbForState = explicitTmdbForState || (kind === "episode" ? episodeShowIdForState : safeText(id));
    const actionContext = canonicalStateContext(kind, id, options);
    const watchedStatusValue = canonicalStateValue("watched_status", actionContext, options.watchedActive ? "watched" : "unwatched");
    const watchListValue = canonicalStateValue("watch_list", actionContext, (options.watchListActive || options.favoriteActive) ? "on" : "off");
    const favouriteValue = canonicalStateValue("favourite", actionContext, options.favouriteActive ? "on" : "off");
    const stateAttrs = {
      "data-kind": kind,
      "data-id": id,
      "data-tmdb-id": tmdbForState,
      "data-title": title,
      "data-no-default": "1",
      ...(releaseStatus ? { "data-release-status": releaseStatus, "data-watch-availability": releaseStatus } : {}),
      ...(options.traktId != null ? { "data-trakt-id": options.traktId } : {}),
      ...(options.imdbId != null ? { "data-imdb-id": options.imdbId } : {}),
      ...(options.tvdbId != null ? { "data-tvdb-id": options.tvdbId } : {}),
      ...(kind === "episode" && episodeTmdbForState ? { "data-episode-tmdb-id": episodeTmdbForState } : {}),
      ...(statusContext.showId != null ? { "data-status-show": statusContext.showId, "data-show": statusContext.showId } : {}),
      ...(statusContext.seasonNumber != null ? { "data-status-season": statusContext.seasonNumber, "data-season": statusContext.seasonNumber } : {}),
      ...(statusContext.episodeNumber != null ? { "data-status-episode": statusContext.episodeNumber, "data-episode": statusContext.episodeNumber } : {})
    };
    return window.MyTVHubSharedModules.actionBar.renderActionBarHtml({
      compact: !!options.compact,
      watch: options.popcornAttrs ? {
        kind: options.popcornKind || kind,
        attrs: options.popcornAttrs || {},
        availabilityStatus: safeText(options.availabilityStatus || "").trim()
      } : null,
      favourite: { active: favouriteValue === "on", attrs: stateAttrs },
      status: options.showStatusAction ? { active: watchedStatusValue !== "unwatched", attrs: stateAttrs } : null,
      watched: { active: watchListValue === "on", attrs: { ...stateAttrs, ...(options.watchedAttrs || {}) } },
      rating: { icon: Number.isFinite(options.pct) && options.pct > 0 ? `${Math.round(options.pct)}` : "--" },
      menusHtml: `${actionMenuHtml(kind, id, title)}${options.showStatusAction ? statusMenuHtml(kind, id, title, statusContext, !!options.available) : ""}`
    });
  }

  async function migrateWatchlist(){
    const list = ensureWatchlist();
    const shows = Array.isArray(state.data?.shows) ? state.data.shows : [];
    const movies = Array.isArray(state.data?.movies) ? state.data.movies : [];
    const showIds = new Set(shows.map(s => String(s?.tmdb_id ?? "")).filter(Boolean));
    const movieIds = new Set(movies.map(m => String(m?.tmdb_id ?? "")).filter(Boolean));
    let changed = false;
    for (const item of list){
      if (!item || typeof item !== "object") continue;
      const id = String(item.tmdb_id ?? "");
      if (!id) continue;
      if (!item.media_kind && item.kind){
        item.media_kind = String(item.kind);
        delete item.kind;
        changed = true;
      }
      if (!item.watch_status && item.status){
        item.watch_status = String(item.status);
        delete item.status;
        changed = true;
      }
      if (!item.media_kind){
        if (showIds.has(id)) item.media_kind = "show";
        else if (movieIds.has(id)) item.media_kind = "movie";
        else item.media_kind = "unknown";
        changed = true;
      }
      if (!item.watch_status){
        item.watch_status = "watchlist";
        changed = true;
      }
      if (!item.added_utc){
        item.added_utc = nowUtcIso();
        changed = true;
      }
    }
    if (changed) await saveInputs();
  }

  function buildMediaLinks(kind, id, links){
    const src = links && typeof links === "object" ? links : {};
    const item = (src && typeof src === "object" && src.watch) ? src : null;
    const embed = Array.isArray(item?.watch?.embed) ? item.watch.embed : [];
    const lookupEmbed = (key) => {
      const hit = embed.find(entry => safeText(entry?.key).trim().toLowerCase() === key && safeText(entry?.href).trim());
      return hit ? safeText(hit.href).trim() : "";
    };
    const vidsrc = lookupEmbed("vidsrc_net") || lookupEmbed("vidsrc");
    const videasy = lookupEmbed("videasy");
    const local = lookupEmbed("local");
    return { vidsrc, videasy, local };
  }

  function watchSourceButtonHtml(kind, attrs, label="Watch"){
    const pairs = Object.entries(attrs || {})
      .filter(([, value]) => value != null && value !== "")
      .map(([key, value]) => ` ${escHtml(key)}="${escHtml(value)}"`)
      .join("");
    return `<button class="btn watchsourcebtn" type="button" data-watch-source-open="${escHtml(kind)}"${pairs} data-function-type="${escHtml(iconType("action_play", "popup"))}"><span class="btnicon">🍿</span>${escHtml(label)}</button>`;
  }

  function fillStreamingTemplate(template, values){
    const src = safeText(template).trim();
    if (!src) return "";
    return src
      .replaceAll("{tmdb_id}", encodeURIComponent(safeText(values.tmdb_id)))
      .replaceAll("{season}", encodeURIComponent(safeText(values.season)))
      .replaceAll("{episode}", encodeURIComponent(safeText(values.episode)));
  }

  function streamingTemplateValues(kind, item, context = {}){
    const ctx = context && typeof context === "object" ? context : {};
    const showId = safeText(item?.show_tmdb_id ?? item?.show_id ?? ctx.showId ?? ctx.show?.tmdb_id ?? item?.tmdb_id ?? item?.id ?? "").trim();
    const movieId = safeText(item?.tmdb_id ?? item?.id ?? ctx.tmdb_id ?? "").trim();
    return {
      tmdb_id: kind === "movie" ? movieId : showId,
      season: safeText(item?.season_number ?? item?.season ?? ctx.seasonNumber ?? ctx.season ?? "").trim(),
      episode: safeText(item?.episode_number ?? item?.episode ?? ctx.episodeNumber ?? ctx.episode ?? "").trim()
    };
  }

  function collectConfiguredWatchSources(kind, item, context = {}){
    const providers = Array.isArray(state.cfg?.streaming?.embed_providers) ? state.cfg.streaming.embed_providers : [];
    const fallbackOrder = Array.isArray(state.cfg?.streaming?.fallback_order) ? state.cfg.streaming.fallback_order.map(v => safeText(v).trim().toLowerCase()) : [];
    const showCandidates = state.cfg?.streaming?.show_candidate_providers === true;
    const values = streamingTemplateValues(kind, item, context);
    return providers.map((entry, idx) => {
      if (!entry || typeof entry !== "object") return null;
      const key = safeText(entry.key).trim().toLowerCase();
      const status = safeText(entry.status || "ok").trim().toLowerCase();
      if (status === "blocked") return null;
      if (status === "candidate" && !showCandidates) return null;
      if (!["ok", "warn", "candidate"].includes(status)) return null;
      const template = kind === "movie" ? entry.movie_template : entry.tv_template;
      const href = fillStreamingTemplate(template, values);
      if (!href || href.includes("{}")) return null;
      if (kind === "episode" && (!values.tmdb_id || !values.season || !values.episode)) return null;
      if (kind === "movie" && !values.tmdb_id) return null;
      const priority = key ? fallbackOrder.indexOf(key) : -1;
      return {
        key,
        type: "external",
        label: safeText(entry.name || entry.label || `Source ${idx + 1}`),
        note: status === "warn" ? "degraded" : "",
        status,
        href,
        provider_status: status,
        provider_id: key,
        priority: priority >= 0 ? priority : 100 + idx
      };
    }).filter(Boolean).sort((a, b) => {
      const pa = Number.isFinite(a.priority) ? a.priority : 999;
      const pb = Number.isFinite(b.priority) ? b.priority : 999;
      if (pa !== pb) return pa - pb;
      return safeText(a.label).localeCompare(safeText(b.label));
    });
  }

  function collectWatchSourceOptions(kind, item, context={}){
    if (!item || typeof item !== "object") return [];
    if (kind !== "movie" && kind !== "episode") return [];
    const options = [];
    const push = (type, label, href, note="") => {
      const safeHref = safeText(href).trim();
      if (!safeHref) return;
      options.push({ type, label, href: safeHref, note });
    };
    collectConfiguredWatchSources(kind, item, context).forEach(opt => push(opt.type, opt.label, opt.href, opt.note));
    const seen = new Set();
    return options.filter(opt => {
      const key = `${opt.type}|${opt.href}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function renderWatchSourceChooserHtml(item, kind, context={}){
    const options = collectWatchSourceOptions(kind, item, context);
    const providerItem = (kind === "season" || kind === "episode") ? (context.show || item) : item;
    const providerKind = (kind === "movie") ? "movie" : "tv";
    const providerHtml = renderWatchProvidersHtml(providerItem, providerKind);
    const mediaDetailHtml = renderWatchSourceMediaDetailHtml(kind, item, context) || renderPopupMediaDetailBlock(kind, item, context);
    const optionHtml = options.length ? options.map(opt => `
      <a class="watch-source-row watch-source-row--${escHtml(safeText(opt.label).toLowerCase().replace(/[^a-z0-9]+/g, "-"))}" href="${escHtml(opt.href)}" target="_blank" rel="noopener" data-watch-source-type="${escHtml(opt.type)}">
        <span class="watch-source-row__label">${escHtml(opt.label)}${safeText(opt.note).toLowerCase() === "degraded" ? " ⚠" : ""}</span>
      </a>
    `).join("") : `<div class="muted" style="font-size:12px;">No configured direct watch sources for this item yet.</div>`;
    return `
      <div class="watch-source-popup" data-popup="watch-source">
        <div class="watch-source-grid">
          ${mediaDetailHtml}
          <div class="watch-source-panel watch-source-panel--links">
            <div class="watch-source-panel__title">Streaming</div>
            <div class="watch-source-links">${optionHtml}</div>
          </div>
          <div class="watch-source-panel watch-source-panel--providers">
            <div class="watch-source-panel__title">Providers</div>
            ${providerHtml}
          </div>
        </div>
        <div class="popup-ref-label">REF: POP-WATCH-SOURCE</div>
      </div>
    `;
  }

  function getSeasonItem(show, seasonNum){
    if (!show) return null;
    return (Array.isArray(show.seasons) ? show.seasons : []).find(season => Number(season?.season_number ?? season?.number ?? season?.season) === Number(seasonNum)) || null;
  }

  function getEpisodeItem(show, seasonNum, episodeNum){
    const season = getSeasonItem(show, seasonNum);
    return (Array.isArray(season?.episodes) ? season.episodes : []).find(ep => Number(ep?.episode_number ?? ep?.number ?? ep?.ep) === Number(episodeNum)) || null;
  }

  function wireWatchSourceButtons(container){
    if (!container) return;
    $$("[data-watch-source-open]", container).forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.preventDefault();
        e.stopPropagation();
        const kind = safeText(btn.getAttribute("data-watch-source-open"));
        if (kind === "movie"){
          const movieId = Number(btn.getAttribute("data-id") || "0");
          const movie = await getMovieDetailById(movieId);
          if (!movie) return;
          openProviderModal(`Watch • ${safeText(movie.title || "Movie")}`, renderWatchSourceChooserHtml(movie, "movie"));
          return;
        }
        const showId = Number(btn.getAttribute("data-show") || btn.getAttribute("data-id") || "0");
        const show = await getShowDetailById(showId);
        if (!show) return;
        if (kind === "episode"){
          const seasonNum = Number(btn.getAttribute("data-season") || "0");
          const episodeNum = Number(btn.getAttribute("data-episode") || "0");
          const episode = getEpisodeItem(show, seasonNum, episodeNum);
          if (!episode) return;
          const title = safeText(episode.title || episode.name || `Episode ${episodeNum}`);
          openProviderModal(`Watch • ${safeText(show.title || show.name || "Show")} • ${title} • ${seTag(seasonNum, episodeNum)}`, renderWatchSourceChooserHtml(episode, "episode", { show, showId: show.tmdb_id ?? show.id, seasonNumber: seasonNum, episodeNumber: episodeNum }));
        }
      });
    });
  }

  function getRtLink(obj){
    if (!obj || typeof obj !== "object") return "";
    const links = obj?.links && typeof obj.links === "object" ? obj.links : {};
    return safeText(
      links.rotten_tomatoes ||
      links.rottentomatoes ||
      links.rt ||
      links.rotten ||
      obj.rotten_tomatoes ||
      obj.rt ||
      ""
    ).trim();
  }

  function providerRegistryRecords(){
    const registry = state.providerRegistry && typeof state.providerRegistry === "object" ? state.providerRegistry : {};
    return Array.isArray(registry.providers) ? registry.providers : (Array.isArray(registry.items) ? registry.items : []);
  }

  function providerDomainFromUrl(href){
    try {
      return new URL(safeText(href)).hostname.toLowerCase().replace(/^www\./, "");
    } catch (_) {
      return "";
    }
  }

  function providerHealthForSource(key, href){
    const sourceKey = safeText(key).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
    const domain = providerDomainFromUrl(href);
    const record = providerRegistryRecords().find(item => {
      const providerId = safeText(item?.provider_id).toLowerCase();
      const itemDomain = safeText(item?.domain).toLowerCase().replace(/^www\./, "");
      return (sourceKey && providerId === sourceKey) || (domain && itemDomain === domain);
    });
    const status = safeText(record?.status || "active").toLowerCase();
    return {
      blocked: status === "blocked" || status === "archived",
      status,
      provider_id: safeText(record?.provider_id || sourceKey),
      note: safeText(record?.notes || "")
    };
  }

  function getCompanyNames(list){
    if (!Array.isArray(list)) return [];
    return list.map(c => c?.name).filter(Boolean);
  }

  function getCreatorNames(list){
    if (!Array.isArray(list)) return [];
    return list.map(person => person?.name).filter(Boolean);
  }

  function formatProviderSummary(item){
    const wp = getWatchProviders(item);
    const providers = collectProvidersForRegion(wp, "CA").length
      ? collectProvidersForRegion(wp, "CA")
      : (collectProvidersForRegion(wp, "US").length ? collectProvidersForRegion(wp, "US") : collectProvidersForRegion(wp, "AU"));
    const seen = new Set();
    const labels = [];
    providers.forEach(p => {
      const label = providerDisplayLabel(p?.provider_name || p?.name || "");
      const key = label.toLowerCase();
      if (!label || seen.has(key)) return;
      seen.add(key);
      labels.push(label);
    });
    return labels.join(" • ") || "Unavailable";
  }

  function getLastSeasonAirDate(season){
    const episodes = Array.isArray(season?.episodes) ? season.episodes : [];
    const today = new Date();
    const valid = episodes
      .map(ep => safeText(ep?.air_date || "").trim())
      .filter(Boolean)
      .map(value => ({ value, date: new Date(value) }))
      .filter(entry => !Number.isNaN(entry.date.valueOf()) && entry.date <= today)
      .sort((a, b) => a.date - b.date);
    return valid.length ? valid[valid.length - 1].value : "";
  }

  function episodeMetaLine(seasonNum, episodeNum, runtime, tmdbId=""){
    return [seTag(seasonNum, episodeNum), Number.isFinite(Number(runtime)) && Number(runtime) > 0 ? `${Number(runtime)} min` : "", safeText(tmdbId) ? `TMDB: ${safeText(tmdbId)}` : ""]
      .filter(Boolean)
      .join(" • ");
  }

  function formatDateForFilename(dateValue){
    const raw = safeText(dateValue).slice(0, 10);
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw);
    if (!match) return "";
    return `${match[2]}-${match[3]}-${match[1].slice(2)}`;
  }

  function generatedWatchFilename(kind, item, context={}){
    if (kind === "episode"){
      const show = context.show || {};
      const showTitle = safeText(show?.title || show?.name || item?.show_title || "Show");
      const seasonNum = Number(item?.season_number ?? context.seasonNum ?? context.seasonNumber ?? 0) || 0;
      const episodeNum = Number(item?.episode_number ?? context.episodeNum ?? context.episodeNumber ?? 0) || 0;
      const episodeTitle = safeText(item?.title || item?.name || item?.episode_name || `Episode ${episodeNum}`);
      const date = formatDateForFilename(pickAirDate(item));
      const tmdb = safeText(show?.tmdb_id ?? show?.id ?? item?.episode_tmdb_id ?? item?.episode_id ?? item?.tmdb_episode_id ?? item?.id ?? "");
      return `${showTitle} - ${seTag(seasonNum, episodeNum)} - ${episodeTitle}${date ? ` [${date}]` : ""}${tmdb ? ` [${tmdb}]` : ""}`;
    }
    const title = safeText(item?.title || "Movie");
    const runtime = Number(item?.runtime);
    const release = pickAirDate(item) || item?.release_date || "";
    const date = formatDateForFilename(release);
    const tmdb = safeText(item?.tmdb_id ?? item?.id ?? "");
    return [title, Number.isFinite(runtime) && runtime > 0 ? `${runtime} min` : "", date ? `[${date}]` : "", tmdb ? `[${tmdb}]` : ""].filter(Boolean).join(" ");
  }

  function renderWatchSourceMediaDetailHtml(kind, item, context={}){
    const normalizedKind = safeText(kind).toLowerCase();
    const filename = generatedWatchFilename(normalizedKind, item, context);
    const detailRow = (label, value) => safeText(value)
      ? `<tr><th>${escHtml(label)}</th><td>${escHtml(value)}</td></tr>`
      : "";
    if (normalizedKind === "episode"){
      const show = context.show || {};
      const showTitle = safeText(show?.title || show?.name || item?.show_title || "Show");
      const seasonNum = Number(item?.season_number ?? context.seasonNum ?? context.seasonNumber ?? 0) || 0;
      const episodeNum = Number(item?.episode_number ?? context.episodeNum ?? context.episodeNumber ?? 0) || 0;
      const episodeTitle = safeText(item?.title || item?.name || item?.episode_name || `Episode ${episodeNum}`);
      const episodeTmdb = safeText(item?.episode_tmdb_id ?? item?.episode_id ?? item?.tmdb_episode_id ?? item?.id ?? "");
      const showTmdb = safeText(show?.tmdb_id ?? show?.id ?? item?.show_tmdb_id ?? item?.show_id ?? "");
      const tmdb = episodeTmdb || showTmdb;
      const aired = pickAirDate(item) ? fmtDate(pickAirDate(item)) : "";
      const runtime = Number(item?.runtime);
      return `
        <section class="watch-source-panel watch-source-panel--detail popup-media-detail popup-media-detail--episode watch-source-detail" data-popup-media-detail="episode">
          <div class="watch-source-panel__title">Details</div>
          <table class="watch-source-detail-table">
            <tbody>
              ${detailRow("Show", showTitle)}
              ${detailRow("Episode", `${seTag(seasonNum, episodeNum)} - ${episodeTitle}`)}
              ${detailRow("Aired", aired)}
              ${detailRow("TMDB", tmdb ? `TMDB: ${tmdb}` : "")}
              ${detailRow("Runtime", Number.isFinite(runtime) && runtime > 0 ? `${runtime} min` : "")}
            </tbody>
          </table>
          <div class="generated-filename-line"><button class="copy-inline-btn copy-inline-btn--icon" type="button" data-copy-watch-filename-icon="${escHtml(filename)}" aria-label="Copy filename" title="Copy filename">⧉</button><button class="generated-filename-copy" type="button" data-copy-watch-filename="${escHtml(filename)}" data-copy-preserve-label="1">${escHtml(filename)}</button></div>
        </section>
      `;
    }
    const title = safeText(item?.title || "Movie");
    const runtime = Number(item?.runtime);
    const release = pickAirDate(item) || item?.release_date || "";
    const tmdb = safeText(item?.tmdb_id ?? item?.id ?? "");
    return `
      <section class="watch-source-panel watch-source-panel--detail popup-media-detail popup-media-detail--movie watch-source-detail" data-popup-media-detail="movie">
        <div class="watch-source-panel__title">Details</div>
        <table class="watch-source-detail-table">
          <tbody>
            ${detailRow("Title", title)}
            ${detailRow("Released", release ? fmtDate(release) : "")}
            ${detailRow("Runtime", Number.isFinite(runtime) && runtime > 0 ? `${runtime} min` : "")}
            ${detailRow("TMDB", tmdb ? `TMDB: ${tmdb}` : "")}
          </tbody>
        </table>
        <div class="generated-filename-line"><button class="copy-inline-btn copy-inline-btn--icon" type="button" data-copy-watch-filename-icon="${escHtml(filename)}" aria-label="Copy filename" title="Copy filename">⧉</button><button class="generated-filename-copy" type="button" data-copy-watch-filename="${escHtml(filename)}" data-copy-preserve-label="1">${escHtml(filename)}</button></div>
      </section>
    `;
  }

  function openModal(title, html) {
    lastFocusEl = document.activeElement;
    $("#modalTitle").textContent = title;
    $("#modalBody").innerHTML = html;
    $("#modalBack").style.display = "flex";
    $("#modalBack").setAttribute("aria-hidden", "false");
    setModalState();
    const card = $("#modalCard");
    if (card) {
      card.scrollTop = 0;
      wirePopupDpad(card);
      bindFloatingNavControls(card, card, { vertical: true, horizontal: false });
      $("#modalClose")?.focus();
    } else {
      $("#modalClose").focus();
    }
  }

  async function copyTextToClipboard(text){
    const value = safeText(text);
    try{
      if (navigator?.clipboard?.writeText){
        await navigator.clipboard.writeText(value);
        return true;
      }
    }catch(_){/* noop */}
    try{
      const area = document.createElement("textarea");
      area.value = value;
      area.setAttribute("readonly", "true");
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.focus();
      area.select();
      const ok = document.execCommand("copy");
      area.remove();
      return !!ok;
    }catch(_){
      return false;
    }
  }

  function openInputsEditorHelp(){
    openModal("Start Inputs Editor", `
      <div style="display:grid;gap:14px;">
        <div>The browser cannot start <code>run_local_servers.bat</code> directly. Local script launch is blocked by browser security.</div>
        <div>Start the editor on this PC first, then reopen the editor tab.</div>
        <div style="padding:12px 14px;border-radius:14px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.04);">
          <div style="font-weight:700;margin-bottom:8px;">Run from the repo root:</div>
          <code id="inputsEditorStartCommand" style="display:block;white-space:pre-wrap;word-break:break-word;">run_local_servers.bat</code>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;">
          <button id="copyInputsEditorCommand" class="calbtn" type="button">Copy Start Command</button>
          <a class="calbtn" href="http://127.0.0.1:8787/web/inputs_editor.html" target="_blank" rel="noopener">Open Editor After Start</a>
        </div>
        <div class="muted">Workflow: start <code>run_local_servers.bat</code>, wait for the local server windows to open, then use <code>http://127.0.0.1:8787/web/inputs_editor.html</code>.</div>
      </div>
    `);
    const copyBtn = $("#copyInputsEditorCommand");
    if (copyBtn){
      copyBtn.addEventListener("click", async () => {
        const ok = await copyTextToClipboard("run_local_servers.bat");
        copyBtn.textContent = ok ? "Copied" : "Copy Failed";
      }, { once: true });
    }
  }
  function closeModal(){
    $("#modalBack").style.display = "none";
    $("#modalBack").setAttribute("aria-hidden", "true");
    $("#modalBody").innerHTML = "";
    setModalState();
    if (lastFocusEl && typeof lastFocusEl.focus === "function") {
      lastFocusEl.focus();
    }
  }

  function openProviderModal(title, html){
    lastFocusEl = document.activeElement;
    $("#providerTitle").textContent = title;
    $("#providerBody").innerHTML = html;
    $("#providerBack").style.display = "flex";
    $("#providerBack").setAttribute("aria-hidden", "false");
    setModalState();
    $$("a[data-watch-source-type]", $("#providerBody")).forEach(link => {
      link.addEventListener("click", () => {
        setTimeout(() => closeProviderModal(), 0);
      });
    });
    $$("[data-copy-watch-filename]", $("#providerBody")).forEach(btn => {
      btn.addEventListener("click", async () => {
        const ok = await copyTextToClipboard(btn.getAttribute("data-copy-watch-filename") || "");
        if (btn.getAttribute("data-copy-preserve-label") === "1"){
          btn.setAttribute("data-copy-result", ok ? "copied" : "failed");
          btn.setAttribute("title", ok ? "Copied" : "Copy failed");
        } else {
          btn.textContent = ok ? "Copied" : "Copy Failed";
        }
      });
    });
    $$("[data-copy-watch-filename-icon]", $("#providerBody")).forEach(btn => {
      btn.addEventListener("click", async () => {
        const ok = await copyTextToClipboard(btn.getAttribute("data-copy-watch-filename-icon") || "");
        btn.setAttribute("data-copy-result", ok ? "copied" : "failed");
        btn.setAttribute("title", ok ? "Copied" : "Copy failed");
      });
    });
    const card = $("#providerCard");
    if (card){
      card.scrollTop = 0;
      wirePopupDpad(card);
      bindFloatingNavControls(card, card, { vertical: true, horizontal: false });
      $("#providerClose")?.focus();
    } else {
      $("#providerClose").focus();
    }
  }
  function closeProviderModal(){
    $("#providerBack").style.display = "none";
    $("#providerBack").setAttribute("aria-hidden", "true");
    $("#providerBody").innerHTML = "";
    setModalState();
    if (lastFocusEl && typeof lastFocusEl.focus === "function") {
      lastFocusEl.focus();
    }
  }

  const FOCUSABLE_SELECTOR = [
    "button:not([disabled])",
    "a[href]",
    "input:not([disabled])",
    "select:not([disabled])",
    "textarea:not([disabled])",
    "[tabindex]:not([tabindex='-1'])"
  ].join(",");

  function isModalOpen(){
    return $("#providerBack")?.style.display === "flex" || $("#modalBack")?.style.display === "flex";
  }

  function activeModalCard(){
    if ($("#providerBack")?.style.display === "flex") return $("#providerCard");
    if ($("#modalBack")?.style.display === "flex") return $("#modalCard");
    return null;
  }

  function setModalState(){
    const modalOpen = isModalOpen();
    document.body.classList.toggle("app-modal-open", modalOpen);
    const appRoot = document.querySelector(".app");
    if (!appRoot) return;
    if (modalOpen){
      appRoot.setAttribute("inert", "");
      appRoot.setAttribute("aria-hidden", "true");
      return;
    }
    appRoot.removeAttribute("inert");
    appRoot.removeAttribute("aria-hidden");
  }

  function activeRoot(){
    const modal = activeModalCard();
    if (modal) return modal;
    const panel = $(".panel:not(.hidden)") || $("#panel-calendar");
    return panel || document.body;
  }

  function isVisible(el){
    if (!el) return false;
    const style = getComputedStyle(el);
    if (style.visibility === "hidden" || style.display === "none") return false;
    const rects = el.getClientRects();
    return rects.length > 0;
  }

  function getFocusables(root){
    if (!root) return [];
    return $$(FOCUSABLE_SELECTOR, root).filter(el => isVisible(el));
  }

  function wirePopupDpad(root){
    if (!root || root.dataset.popupDpadBound === "1") return;
    root.dataset.popupDpadBound = "1";
    root.addEventListener("keydown", (e) => {
      if (!isModalOpen()) return;
      if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) return;
      const focusables = getFocusables(root);
      if (!focusables.length) return;
      const active = document.activeElement;
      const currentIndex = Math.max(0, focusables.indexOf(active));
      const delta = (e.key === "ArrowLeft" || e.key === "ArrowUp") ? -1 : 1;
      const nextIndex = (currentIndex + delta + focusables.length) % focusables.length;
      e.preventDefault();
      focusables[nextIndex]?.focus();
    });
  }

  function isTypingField(el){
    if (!el) return false;
    const tag = (el.tagName || "").toLowerCase();
    if (tag === "textarea") return true;
    if (tag === "input"){
      const type = (el.getAttribute("type") || "text").toLowerCase();
      return !["button","submit","checkbox","radio","range","color"].includes(type);
    }
    return el.isContentEditable;
  }

  function moveFocus(dir){
    if (window.MyTVHubFocus?.moveInRoot){
      return window.MyTVHubFocus.moveInRoot(activeRoot(), dir, document.activeElement);
    }
    const root = activeRoot();
    const focusables = getFocusables(root);
    if (!focusables.length) return false;
    const first = focusables[0];
    first.focus({ preventScroll: true });
    first.scrollIntoView({ block: "nearest", inline: "nearest" });
    return true;
  }

  function scrollActiveModal(dy){
    const card = activeModalCard();
    if (!card) return;
    card.scrollTop += dy;
  }

  function trapTabInModal(e){
    if (!isModalOpen() || e.key !== "Tab") return;
    const root = activeModalCard();
    if (!root) return;
    const focusables = getFocusables(root);
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first){
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last){
      e.preventDefault();
      first.focus();
    }
  }

  function footerText(){
    const meta = state.data?.meta || {};
    const counts = meta.counts || {};
    const showsN = counts.shows ?? (state.data?.shows?.length ?? 0);
    const moviesN = counts.movies ?? (state.data?.movies?.length ?? 0);
    const errorsN = state.data?.errors?.length ?? 0;
    const generatedAt = safeText(meta.generated_utc || "");
    return `${appVersionText()} • loaded • errors=${errorsN} • shows=${showsN} • movies=${moviesN}${generatedAt ? ` • generated=${generatedAt}` : ""}`;
  }

  async function fetchJsonFirst(urls){
    for (const u of urls){
      try {
        const r = await fetch(u, {cache:"no-store"});
        if (!r.ok) continue;
        const text = await r.text();
        return parseJsonc(text);
      } catch {
        // try next
      }
    }
    return null;
  }

  function applyUiPaletteFromConfig(cfg){
    try{
      const ui = cfg && typeof cfg === "object" ? cfg.ui_palette : null;
      if (!ui || typeof ui !== "object") return;
      const active = safeText(ui.active || "night_tv");
      const palettes = ui.palettes && typeof ui.palettes === "object" ? ui.palettes : null;
      const palette = palettes && palettes[active] ? palettes[active] : null;
      if (!palette || typeof palette !== "object") return;
      const tokens = palette.tokens && typeof palette.tokens === "object" ? palette.tokens : null;
      const derived = palette.derived && typeof palette.derived === "object" ? palette.derived : null;
      const root = document.documentElement;
      if (tokens){
        for (const [k, v] of Object.entries(tokens)){
          if (k && v != null) root.style.setProperty(`--${k}`, String(v));
        }
      }
      if (derived){
        for (const [k, v] of Object.entries(derived)){
          if (k && v != null) root.style.setProperty(`--${k}`, String(v));
        }
      }
      const alias = ui.alias_to_legacy_vars && typeof ui.alias_to_legacy_vars === "object" ? ui.alias_to_legacy_vars : null;
      if (alias){
        for (const [legacyVar, tokenKey] of Object.entries(alias)){
          if (!legacyVar || !tokenKey) continue;
          root.style.setProperty(`--${legacyVar}`, `var(--${tokenKey})`);
        }
      }
      const legacy = ui.legacy_vars && typeof ui.legacy_vars === "object" ? ui.legacy_vars : null;
      if (legacy){
        if (legacy.chip != null) root.style.setProperty("--chip", String(legacy.chip));
        if (legacy.chip2 != null) root.style.setProperty("--chip2", String(legacy.chip2));
      }
    }catch(_){/* fail-safe */}
  }

  async function loadAll(){
    setStatus(true, "Loading");
    try {
      state.cfg = await window.MyTVHubSharedModules.configLoader.loadConfigFirst(["./config.json", "../web/config.json"]);
      applyUiPaletteFromConfig(state.cfg);
      state.icons = (state.cfg && typeof state.cfg === "object" && state.cfg.icons && typeof state.cfg.icons === "object")
        ? state.cfg.icons
        : {};
      applyIconText();

      // Apply config.json image sizing (cards + calendar thumbs)
      try{
        const sz = (state.cfg && typeof state.cfg === 'object') ? state.cfg.image_sizes : null;
        if (sz && typeof sz === 'object'){
          const sw = Number(sz.show_width);
          const mw = Number(sz.movie_width);
          const ew = Number(sz.episode_still_w);
          const cw = Number(sz.calendar_thumb_w);
          const hpw = Number(sz.hero_poster_w);
          const hpm = Number(sz.hero_poster_min);
          const epw = Number(sz.episode_card_w);
          const nwm = Number(sz.network_logo_max_w);
          const pwm = Number(sz.provider_logo_max_w);
          if (Number.isFinite(sw) && sw > 0) document.documentElement.style.setProperty('--show_card_min', `${sw}px`);
          if (Number.isFinite(mw) && mw > 0) document.documentElement.style.setProperty('--movie_card_min', `${mw}px`);
          if (Number.isFinite(sw) && sw > 0) document.documentElement.style.setProperty('--browse_show_card_min', `${Math.max(200, Math.min(sw, sw - 78))}px`);
          if (Number.isFinite(mw) && mw > 0) document.documentElement.style.setProperty('--browse_movie_card_min', `${Math.max(200, Math.min(mw, mw - 78))}px`);
          if (Number.isFinite(ew) && ew > 0) document.documentElement.style.setProperty('--episode_thumb', `${ew}px`);
          if (Number.isFinite(cw) && cw > 0) document.documentElement.style.setProperty('--cal-thumb-w', `${cw}px`);
          if (Number.isFinite(hpw) && hpw > 0) document.documentElement.style.setProperty('--hero-poster-w', `${hpw}px`);
          if (Number.isFinite(hpm) && hpm > 0) document.documentElement.style.setProperty('--hero-poster-min', `${hpm}px`);
          if (Number.isFinite(epw) && epw > 0) document.documentElement.style.setProperty('--epcard-w', `${epw}px`);
          if (Number.isFinite(nwm) && nwm > 0) document.documentElement.style.setProperty('--netlogo-max-w', `${nwm}px`);
          if (Number.isFinite(pwm) && pwm > 0) document.documentElement.style.setProperty('--provider-logo-max-w', `${pwm}px`);
        }
      }catch(_){/* noop */}

      // Apply config.json UI tuning (logo sizing)
      try{
        const ui = (state.cfg && typeof state.cfg === 'object') ? state.cfg.ui_tuning : null;
        if (ui && typeof ui === 'object'){
          const lh = Number(ui.logo_height);
          if (Number.isFinite(lh) && lh > 0) document.documentElement.style.setProperty('--logo-h', `${lh}px`);
          const plh = Number(ui.provider_logo_height);
          if (Number.isFinite(plh) && plh > 0) document.documentElement.style.setProperty('--provider-logo-h', `${plh}px`);
          const urlScale = Number(ui.url_button_scale);
          if (Number.isFinite(urlScale) && urlScale > 0) document.documentElement.style.setProperty('--url-btn-scale', `${urlScale}`);
          const tw = Number(ui.watch_toggle_width);
          if (Number.isFinite(tw) && tw > 0) document.documentElement.style.setProperty('--toggle-w', `${tw}px`);
          const tcolors = ui.watch_toggle_colors && typeof ui.watch_toggle_colors === "object" ? ui.watch_toggle_colors : null;
          if (tcolors){
            if (tcolors.show) document.documentElement.style.setProperty('--toggle-show', String(tcolors.show));
            if (tcolors.season) document.documentElement.style.setProperty('--toggle-season', String(tcolors.season));
            if (tcolors.episode) document.documentElement.style.setProperty('--toggle-episode', String(tcolors.episode));
            if (tcolors.movie) document.documentElement.style.setProperty('--toggle-movie', String(tcolors.movie));
            if (tcolors.watchlist) document.documentElement.style.setProperty('--toggle-watchlist', String(tcolors.watchlist));
          }
          state.ui = state.ui || {};
          if (ui.watch_status_colors && typeof ui.watch_status_colors === "object"){
            state.ui.watch_status_colors = {
              watching: ui.watch_status_colors.watching || "#bbf7d0",
              to_be_watched: ui.watch_status_colors.to_be_watched || "#fef9c3",
              completed: ui.watch_status_colors.completed || "#bfdbfe",
              dropped: ui.watch_status_colors.dropped || "#fecaca"
            };
          }
        }
      }catch(_){/* noop */}


      state.data = await window.MyTVHubSharedModules.dataLoader.loadCatalogDataFirst(["../data/data.json"]);
      state.calendarData = await window.MyTVHubSharedModules.dataLoader.loadCalendarFirst(["../data/data.json"]);
      state.discoverRegistry = await window.MyTVHubSharedModules.dataLoader.loadDiscoverRegistryFirst(["../data/discover_registry.json"]);
      state.watchStateQueue = await window.MyTVHubSharedModules.configLoader.loadJsonFirst(["../data/watch_state_queue.json"]).catch(() => ({ items: [] }));
      state.providerRegistry = await window.MyTVHubSharedModules.configLoader.loadJsonFirst(["../data/provider_registry.json"]).catch(() => ({ providers: [] }));

      if (!state.data || typeof state.data !== "object") throw new Error("data.json not loaded");
      if (!state.calendarData || typeof state.calendarData !== "object") throw new Error("calendar could not be derived from data.json");

      // Enforce contract shape (graceful defaults)
      state.data.movies = Array.isArray(state.data.movies) ? state.data.movies : [];
      state.data.shows  = Array.isArray(state.data.shows)  ? state.data.shows  : [];
      state.data.errors = Array.isArray(state.data.errors) ? state.data.errors : [];
      state.data.meta   = state.data.meta && typeof state.data.meta === "object" ? state.data.meta : {};
      state.data.shows = dedupeItems(state.data.shows, item => `show:${safeText(item?.tmdb_id ?? item?.id ?? "")}`);
      state.data.movies = dedupeItems(state.data.movies, item => `movie:${safeText(item?.tmdb_id ?? item?.id ?? "")}`);
      state.showById = new Map(state.data.shows.map(item => [String(item?.tmdb_id ?? item?.id ?? ""), item]).filter(([key]) => !!key));
      state.movieById = new Map(state.data.movies.map(item => [String(item?.tmdb_id ?? item?.id ?? ""), item]).filter(([key]) => !!key));
      state.calendarData.days = state.calendarData.days && typeof state.calendarData.days === "object" ? state.calendarData.days : {};
      state.inputs = await window.MyTVHubSharedModules.dataLoader.loadInputsFirst(["../data/inputs.json"]);

      // Local editor probes are deferred to the editor view to avoid noisy failed
      // localhost requests during normal static browsing.
      state.apiAvailable = false;
      state.inputsEditorServerAvailable = false;

      // Prefer local watch_state (inputs/data), fallback to Trakt
      setWatchStateSource();

      // Normalize watchlist entries (kind + watch_status)
      await migrateWatchlist();

      populateFilters();

      const footer = $("#footer");
      if (footer) footer.textContent = footerText();
      const vb = $("#verBadge");
      if (vb) vb.textContent = appVersionText();
      setStatus(true, "Ready");
      initCalendarMonth();
      routeFromHash();
    } catch (e){
      console.error(e);
      const footer = $("#footer");
      if (footer) footer.textContent = footerText();
      setStatus(false, "Failed");
      const msg = escHtml(e?.message || String(e));
      const errPanel = $("#panel-dashboard") || $("#panel-calendar") || $(".panel");
      if (errPanel) errPanel.innerHTML = `
        <div style="padding:12px 14px;border-radius:16px;border:1px solid rgba(220,38,38,.35);background:rgba(220,38,38,.10);">
          Failed to fetch data/config. Run a local server from repo root, then open: <code>http://127.0.0.1:8000/web/index.html</code><br/>
          Details: <code>${msg}</code>
        </div>
      `;
    }
  }

  function initCalendarMonth(){
    const today = new Date();
    state.calendarMonth = new Date(today.getFullYear(), today.getMonth(), 1);
  }

  function getAvailableTabs(){
    const tabs = new Set();
    if ($("#panel-dashboard")) tabs.add("dashboard");
    if ($("#panel-watch-me")) tabs.add("watch-me");
    if ($("#panel-calendar")) tabs.add("calendar");
    if ($("#panel-shows")) tabs.add("shows");
    if ($("#panel-movies")) tabs.add("movies");
    if ($("#panel-show")) tabs.add("show");
    if ($("#panel-config")) tabs.add("config");
    if ($("#panel-manage-watch-state")) tabs.add("manage-watch-state");
    if ($("#panel-discover")) tabs.add("discover");
    if ($("#panel-inputs-editor")) tabs.add("inputs-editor");
    return tabs;
  }

  function setTab(tab){
    const available = getAvailableTabs();
    if (!available.has(tab)) return;
    state.tab = tab;
    syncCanonicalTabUrl(tab);
    for (const b of $$(".tab")){
      const is = b.dataset.tab === tab;
      b.classList.toggle("active", is);
      b.setAttribute("aria-selected", is ? "true" : "false");
    }

    const panelCalendar = $("#panel-calendar");
    const panelWatchMe = $("#panel-watch-me");
    const panelShows = $("#panel-shows");
    const panelMovies = $("#panel-movies");
    const panelShow = $("#panel-show");
    const panelConfig = $("#panel-config");
    const panelManageWatchState = $("#panel-manage-watch-state");
    const panelDashboard = $("#panel-dashboard");
    const panelDiscover = $("#panel-discover");
    const panelInputsEditor = $("#panel-inputs-editor");
    if (panelWatchMe) panelWatchMe.classList.toggle("hidden", tab !== "watch-me");
    if (panelCalendar) panelCalendar.classList.toggle("hidden", tab !== "calendar");
    if (panelShows) panelShows.classList.toggle("hidden", tab !== "shows");
    if (panelMovies) panelMovies.classList.toggle("hidden", tab !== "movies");
    if (panelShow) panelShow.classList.toggle("hidden", tab !== "show");
    if (panelConfig) panelConfig.classList.toggle("hidden", tab !== "config");
    if (panelManageWatchState) panelManageWatchState.classList.toggle("hidden", tab !== "manage-watch-state");
    if (panelDashboard) panelDashboard.classList.toggle("hidden", tab !== "dashboard");
    if (panelDiscover) panelDiscover.classList.toggle("hidden", tab !== "discover");
    if (panelInputsEditor) panelInputsEditor.classList.toggle("hidden", tab !== "inputs-editor");

    if (tab === "watch-me") renderWatchMe();
    if (tab === "calendar") renderCalendar();
    if (tab === "shows") renderShows();
    if (tab === "movies") renderMovies();
    if (tab === "dashboard") renderDashboard();
    if (tab === "discover") renderDiscover();
    if (tab === "config") renderConfig();
    if (tab === "manage-watch-state") renderManageWatchState();
    if (tab === "inputs-editor") renderInputsEditor();
  }

  function routeFromHash(){
    const h = safeText(location.hash || "").trim();

    if (h.startsWith("#show/")){
      const id = parseInt(h.slice("#show/".length), 10);
      if (!Number.isFinite(id)){
        location.hash = state.lastNonShowHash || "#calendar";
        return;
      }
      state.show.tmdb_id = id;
      openShowModal(id);
      const available = getAvailableTabs();
      const fallback = state.lastNonShowHash || (available.has("dashboard") ? "#dashboard" : "#calendar");
      const tab = fallback.startsWith("#") ? fallback.slice(1) : fallback;
      if (getAvailableTabs().has(tab)){
        setTab(tab);
      }
      return;
    }

    // non-show routes
    if (getAvailableTabs().has(h.replace("#",""))){
      state.lastNonShowHash = h;
      setTab(h.slice(1));
      return;
    }

    // default
    const available = getAvailableTabs();
    const fallback = available.has(PAGE) ? PAGE : (available.values().next().value || "calendar");
    state.lastNonShowHash = `#${fallback}`;
    setTab(fallback);
  }

  function gotoShow(tmdbId){
    if (!Number.isFinite(tmdbId)) return;
    const current = safeText(location.hash || "");
    if (!current.startsWith("#show/")) state.lastNonShowHash = current || `#${PAGE}`;
    openShowModal(tmdbId);
  }

  function getShowById(id){
    const key = String(id ?? "").trim();
    if (!key) return null;
    return state.showById?.get(key) || (state.data?.shows || []).find(s => String(s?.id ?? s?.tmdb_id ?? "") === key) || null;
  }

  function getMovieById(id){
    const key = String(id ?? "").trim();
    if (!key) return null;
    return state.movieById?.get(key) || (state.data?.movies || []).find(m => String(m?.id ?? m?.tmdb_id ?? "") === key) || null;
  }

  function hasDirectWatchSources(item){
    if (!item || typeof item !== "object") return false;
    if (Array.isArray(item?.watch?.embed) && item.watch.embed.length > 0) return true;
    if (Number(item?.watch_embed_count || item?.embed_count || 0) > 0 || !!item?.has_watch_sources) return true;
    const providers = Array.isArray(state.cfg?.streaming?.embed_providers) ? state.cfg.streaming.embed_providers : [];
    const showCandidates = state.cfg?.streaming?.show_candidate_providers === true;
    const hasVisibleProvider = (templateKey) => providers.some(provider => {
      const status = safeText(provider?.status || "ok").toLowerCase();
      if (status === "blocked") return false;
      if (status === "candidate" && !showCandidates) return false;
      return !!safeText(provider?.[templateKey]).trim();
    });
    const isEpisode = !!(item?.season_number || item?.episode_number || item?.season || item?.episode || item?.kind === "episode");
    if (isEpisode){
      return !!(item?.show_tmdb_id || item?.show_id || item?.tmdb_id) && hasVisibleProvider("tv_template");
    }
    const isMovie = item?.kind === "movie" || (Object.prototype.hasOwnProperty.call(item, "release_date") && !Object.prototype.hasOwnProperty.call(item, "first_air_date"));
    return isMovie && !!(item?.tmdb_id || item?.id) && hasVisibleProvider("movie_template");
  }

  async function getCatalogDetailById(id){
    const safeId = Number(id) || 0;
    if (!safeId) return null;
    return await window.MyTVHubSharedModules.dataLoader.loadCatalogDetailFirst(safeId);
  }

  async function getShowDetailById(id){
    const key = String(Number(id) || 0);
    return key && state.showById?.get(key) ? state.showById.get(key) : null;
  }

  async function getMovieDetailById(id){
    const key = String(Number(id) || 0);
    return key && state.movieById?.get(key) ? state.movieById.get(key) : null;
  }

  function buildCalendarEventsForMonth(monthDate){
    const days = state.calendarData?.days && typeof state.calendarData.days === "object" ? state.calendarData.days : {};
    const eventsByDate = new Map();
    for (const [dateKey, items] of Object.entries(days)){
      if (!/^\d{4}-\d{2}-\d{2}$/.test(dateKey)) continue;
      eventsByDate.set(dateKey, dedupeItems(Array.isArray(items) ? items : [], item => itemRenderKey(item, dateKey)));
    }
    return eventsByDate;
  }

  function itemRenderKey(item, fallback = ""){
    const parts = [safeText(item?.kind || "item").toLowerCase()];
    const showId = safeText(item?.show_tmdb_id ?? item?.show_id ?? item?.showId ?? "");
    const tmdbId = safeText(item?.tmdb_id ?? item?.id ?? "");
    const season = safeText(item?.season_number ?? item?.seasonNumber ?? "");
    const episode = safeText(item?.episode_number ?? item?.episodeNumber ?? "");
    if (showId) parts.push(`show:${showId}`);
    if (tmdbId) parts.push(`id:${tmdbId}`);
    if (season) parts.push(`s:${season}`);
    if (episode) parts.push(`e:${episode}`);
    if (fallback) parts.push(`d:${fallback}`);
    return parts.join("|");
  }

  function dedupeItems(items, keyFn){
    const seen = new Set();
    const out = [];
    for (const item of Array.isArray(items) ? items : []){
      const key = safeText(keyFn ? keyFn(item) : itemRenderKey(item));
      if (!key || seen.has(key)) continue;
      seen.add(key);
      out.push(item);
    }
    return out;
  }

  function updateCalendarStickyVars(){
    const topBar = $(".top");
    const calbar = $("#panel-calendar .dashhead");
    const headerHeight = topBar ? Math.ceil(topBar.getBoundingClientRect().height) : 42;
    const sectionTop = headerHeight + 8;
    const sectionHeight = calbar ? Math.ceil(calbar.getBoundingClientRect().height) : 0;
    document.documentElement.style.setProperty("--app-header-height", `${headerHeight}px`);
    document.documentElement.style.setProperty("--sticky-app-top", "0px");
    document.documentElement.style.setProperty("--sticky-section-top", `${sectionTop}px`);
    document.documentElement.style.setProperty("--sticky-calendar-top", `${sectionTop + sectionHeight + 8}px`);
    document.documentElement.style.setProperty("--sticky-top", `${sectionTop}px`);
    document.documentElement.style.setProperty("--calbar-h", `${sectionHeight}px`);
  }

  function applyStickySectionHeads(root=document){
    updateCalendarStickyVars();
    $$(".dashblock > .dashhead, .panel > .dashhead, .watch-state-manager > .dashhead", root).forEach(head => {
      head.classList.add("sticky-section-head");
      head.setAttribute("data-sticky-section-head", "1");
    });
  }

  function updateTodayLabel(){
    const el = $("#calTodayLabel");
    if (!el) return;
    const today = new Date();
    el.textContent = today.toLocaleDateString("en-US", { weekday:"long", month:"long", day:"numeric", year:"numeric" });
  }

  function scrollToDayCell(dateKey){
    const cell = document.querySelector(`[data-daycell="${CSS.escape(dateKey)}"]`);
    if (!cell) return false;
    updateCalendarStickyVars();
    const rootStyle = getComputedStyle(document.documentElement);
    const offset = parseFloat(rootStyle.getPropertyValue("--sticky-calendar-top")) || 0;
    const top = cell.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo({ top, behavior:"smooth" });
    cell.classList.add("today-jump");
    setTimeout(() => cell.classList.remove("today-jump"), 1200);
    return true;
  }

  function sortByTitle(a,b,desc=false){
    const r = safeText(a?.title || a?.name).localeCompare(safeText(b?.title || b?.name));
    return desc ? -r : r;
  }

  function getSeasonEpisodeNumbers(season){
    const eps = Array.isArray(season?.episodes) ? season.episodes : [];
    return eps.map(e => Number(e?.episode_number ?? e?.number ?? e?.ep)).filter(n => Number.isFinite(n));
  }

  function isShowWatched(show){
    const id = String(show?.tmdb_id ?? "");
    if (id && canonicalStateValue("watched_status", { kind: "show", id, tmdb_id: id, showId: id }, "") === "watched") return true;
    const ws = state.watchState;
    if (!ws || !ws.shows || !id) return false;
    const entry = ws.shows[id];
    if (!entry || !entry.seasons || typeof entry.seasons !== "object") return false;
    const seasons = Array.isArray(show?.seasons) ? show.seasons : [];
    const seasonCounts = Array.isArray(show?.season_episode_counts) ? show.season_episode_counts : [];
    const targets = seasons.length
      ? seasons.map(season => ({
          seasonNumber: Number(season?.season_number ?? season?.number),
          episodeCount: getSeasonEpisodeNumbers(season).length,
          episodeNums: getSeasonEpisodeNumbers(season)
        }))
      : seasonCounts.map(season => ({
          seasonNumber: Number(season?.season_number),
          episodeCount: Number(season?.episode_count ?? 0),
          episodeNums: null
        }));
    if (!targets.length) return false;
    for (const target of targets){
      const sn = String(target.seasonNumber || "");
      if (!sn) continue;
      const watched = entry.seasons[sn];
      if (!watched || !Array.isArray(watched.episodes)) return false;
      if (Array.isArray(target.episodeNums) && target.episodeNums.length){
        for (const epn of target.episodeNums){
          if (!watched.episodes.includes(Number(epn))) return false;
        }
      } else if (Number(target.episodeCount) > 0 && watched.episodes.length < Number(target.episodeCount)) {
        return false;
      }
    }
    return true;
  }

  function isMovieWatched(m){
    const id = String(m?.tmdb_id ?? "");
    if (id && canonicalStateValue("watched_status", { kind: "movie", id, tmdb_id: id }, "") === "watched") return true;
    const ws = state.watchState;
    return !!(ws && ws.movies && id && ws.movies[id]);
  }

  function collectUpcomingEvents(dayWindow=14, startOffsetDays=0){
    const out = [];
    const startBase = new Date();
    const start = new Date(startBase.getFullYear(), startBase.getMonth(), startBase.getDate() + (Number(startOffsetDays) || 0));
    const end = new Date(start.getFullYear(), start.getMonth(), start.getDate() + dayWindow - 1);
    const months = new Map();
    const cursor = new Date(start.getFullYear(), start.getMonth(), 1);
    while (cursor <= end){
      const key = `${cursor.getFullYear()}-${pad2(cursor.getMonth()+1)}`;
      if (!months.has(key)) months.set(key, buildCalendarEventsForMonth(cursor));
      cursor.setMonth(cursor.getMonth() + 1);
    }
    for (let d = new Date(start.getFullYear(), start.getMonth(), start.getDate()); d <= end; d.setDate(d.getDate()+1)){
      const key = toDateKey(d);
      for (const m of months.values()){
        const list = m.get(key) || [];
        for (const item of list){
          out.push({ date: new Date(d), dateKey: key, item });
        }
      }
    }
    return out.sort((a,b)=>a.date.getTime()-b.date.getTime());
  }

  function collectPastEvents(dayWindow=7, offsetWeeks=0, includeToday=false){
    const out = [];
    const end = new Date();
    end.setDate(end.getDate() - (includeToday ? 0 : 1) - (Math.max(0, Number(offsetWeeks) || 0) * 7));
    const start = new Date(end.getFullYear(), end.getMonth(), end.getDate() - (dayWindow - 1));
    const months = new Map();
    const cursor = new Date(start.getFullYear(), start.getMonth(), 1);
    while (cursor <= end){
      const key = `${cursor.getFullYear()}-${pad2(cursor.getMonth()+1)}`;
      if (!months.has(key)) months.set(key, buildCalendarEventsForMonth(cursor));
      cursor.setMonth(cursor.getMonth() + 1);
    }
    for (let d = new Date(start.getFullYear(), start.getMonth(), start.getDate()); d <= end; d.setDate(d.getDate()+1)){
      const key = toDateKey(d);
      for (const m of months.values()){
        const list = m.get(key) || [];
        for (const item of list){
          out.push({ date: new Date(d), dateKey: key, item });
        }
      }
    }
    return out.sort((a,b)=>a.date.getTime()-b.date.getTime());
  }

  function formatDateShort(value){
    const raw = safeText(value).trim();
    if (!raw) return "";
    const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (iso){
      const y = Number(iso[1]);
      const m = Number(iso[2]);
      const d = Number(iso[3]);
      if (Number.isFinite(y) && Number.isFinite(m) && Number.isFinite(d)){
        return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-US", { month:"short", day:"numeric", year:"numeric", timeZone:"UTC" });
      }
    }
    const parsed = new Date(raw);
    if (!Number.isFinite(parsed?.getTime?.())) return "";
    return new Date(Date.UTC(parsed.getUTCFullYear(), parsed.getUTCMonth(), parsed.getUTCDate()))
      .toLocaleDateString("en-US", { month:"short", day:"numeric", year:"numeric", timeZone:"UTC" });
  }

  function normalizeImageSrc(src){
    if (isLightMode()) return "";
    const raw = safeText(src).trim();
    if (!raw) return "";
    if (raw.startsWith("/")) return withBasePath(raw);
    if (raw.startsWith("./")) return withBasePath("/" + raw.replace(/^\.\/+/, ""));
    if (raw.startsWith("assets/") || raw.startsWith("assets\\")) return withBasePath("/" + raw.replace(/^assets[\\/]/, "assets/"));
    return raw;
  }

  function truncateText(text, max = 140){
    const value = safeText(text).trim().replace(/\s+/g, " ");
    if (!value || value.length <= max) return value;
    return `${value.slice(0, Math.max(0, max - 1)).trimEnd()}...`;
  }

  function factChipHtml(text, tone = ""){
    const value = safeText(text).trim();
    if (!value) return "";
    const toneClass = tone ? ` ${tone}` : "";
    return `<span class="fact-chip${toneClass}">${escHtml(value)}</span>`;
  }

  function compactOverviewHtml(text, max = 150){
    const value = truncateText(text, max);
    return value ? `<div class="media-card__summary">${escHtml(value)}</div>` : "";
  }

  function buildMediaCardShell(kind, id, options = {}){
    return window.MyTVHubSharedModules.cardRenderer.renderCompactCardHtml({
      kind,
      id,
      title: safeText(options.title || "(Untitled)"),
      image: safeText(options.image || "").trim(),
      badgeHtml: safeText(options.badgeHtml || "").trim(),
      meta: safeText(options.meta || "").trim(),
      submeta: safeText(options.submeta || "").trim(),
      actionBarHtml: safeText(options.actionBar || ""),
      overlay: true,
      extraClass: options.eyeClass || "",
      renderKey: `${kind}:${safeText(id)}`
    });
  }

  function buildDashboardCard(kind, id, options = {}){
    const title = safeText(options.title || "(Untitled)");
    const subtitle = safeText(options.subtitle || "").trim();
    const tertiary = safeText(options.tertiary || "").trim();
    const image = safeText(options.image || "").trim();
    const pct = options.pct;
    const actionBar = buildIconStripHtml(kind, id, pct, title);
    return window.MyTVHubSharedModules.cardRenderer.renderCompactCardHtml({
      kind,
      id,
      title,
      image,
      badgeHtml: safeText(options.badgeHtml || "").trim(),
      meta: tertiary || subtitle,
      actionBarHtml: actionBar,
      overlay: true,
      extraClass: `dashcard dashcard--clean dashcard--poster${options.extraClass ? ` ${options.extraClass}` : ""}`,
      renderKey: options.renderKey || `dash:${kind}:${safeText(id)}`
    });
  }

  const EPISODE_STILL_PLACEHOLDER = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 135'%3E%3Crect width='240' height='135' fill='%23111827'/%3E%3Cpath d='M96 44h48v47H96z' fill='%23233447'/%3E%3Cpath d='M106 58l27 16-27 16z' fill='%239fb0c8'/%3E%3C/svg%3E";

  function episodeStillImageForCard(item, context = {}){
    if (isLightMode()) return "";
    const still = normalizeImageSrc(pickImage(
      item,
      "still_local",
      "episode_still_local",
      "still_path",
      "episode_still_path",
      "still",
      "thumb"
    ));
    if (still && !/poster/i.test(still)) return still;
    return EPISODE_STILL_PLACEHOLDER;
  }

  function buildSharedEpisodeCard(item, options = {}){
    const showId = Number(item?.show_tmdb_id ?? item?.show_id ?? item?.tmdb_id) || 0;
    const seasonNum = Number(item?.season_number ?? item?.season ?? 0) || 0;
    const episodeNum = Number(item?.episode_number ?? item?.episode ?? 0) || 0;
    const episodeTmdbId = safeText(item?.episode_tmdb_id ?? item?.episode_id ?? item?.tmdb_episode_id ?? item?.id ?? "");
    const pct = Number.isFinite(item?.progress) ? Math.max(0, Math.min(100, item.progress)) : (Number.isFinite(options.pct) ? options.pct : null);
    const available = isEpisodeAvailable(item);
    const watched = state.watchState ? isEpisodeWatched(showId, seasonNum, episodeNum) : false;
    const hasSources = hasDirectWatchSources(item);
    const density = safeText(options.density || "standard").toLowerCase() === "compact" ? "compact" : "standard";
    const articleAttrs = {
      tabindex: "0",
      "data-kind": "episode",
      "data-show": showId,
      "data-season": seasonNum,
      "data-episode": episodeNum,
      "data-episode-card-renderer": "buildSharedEpisodeCard",
      "data-episode-card-density": density,
      "data-image-resolver": "episodeStillImageForCard",
      ...(options.articleAttrs || {})
    };
    const image = normalizeImageSrc(options.image || episodeStillImageForCard(item, options));
    return window.MyTVHubSharedModules.cardRenderer.renderEpisodeCardHtml({
      id: showId,
      image,
      eyebrow: safeText(options.eyebrow || item?.show_title || "Show"),
      title: safeText(options.title || item?.episode_name || "Episode"),
      badgeHtml: "",
      meta: options.meta || episodeMetaLine(seasonNum, episodeNum, item?.runtime, episodeTmdbId),
      submeta: options.submeta || "",
      description: safeText(options.description || item?.overview || ""),
      density,
      overlay: options.overlay !== false,
      actionBarHtml: buildActionBarHtml("episode", episodeNum, {
        title: safeText(options.title || item?.episode_name || "Episode"),
        compact: true,
        tmdbId: episodeTmdbId,
        traktId: safeText(item?.trakt_id || item?.episode_trakt_id || ""),
        tvdbId: safeText(item?.tvdb_id || item?.episode_tvdb_id || ""),
        pct,
        showWatchedAction: true,
        watchedActive: watched,
        watchedAttrs: { "data-show": showId, "data-season": seasonNum, "data-watch-episode": episodeNum },
        showStatusAction: true,
        statusContext: { showId, seasonNumber: seasonNum, episodeNumber: episodeNum },
        popcornAttrs: hasSources ? { "data-show": showId, "data-season": seasonNum, "data-episode": episodeNum } : null,
        popcornKind: "episode",
        availabilityStatus: availabilityStatusOf(item),
        available
      }),
      articleAttrs,
      renderKey: options.renderKey || `episode:${showId}:${seasonNum}:${episodeNum}`,
      extraClass: `episode-card--${density}${options.extraClass ? ` ${options.extraClass}` : ""}`
    });
  }

  function renderMoreButton(hiddenCount, targetId){
    return hiddenCount > 0
      ? `<button class="more-toggle" type="button" data-more-target="${escHtml(targetId)}">+${hiddenCount} more</button>`
      : "";
  }

  function expandableClass(hidden){
    return hidden ? " is-overflow-hidden" : "";
  }

  function bindMoreToggles(root){
    if (!root) return;
    $$("[data-more-target]", root).forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const target = root.querySelector(`[data-more-id="${CSS.escape(btn.getAttribute("data-more-target") || "")}"]`);
        if (!target) return;
        target.classList.add("is-expanded");
        target.setAttribute("data-expanded", "1");
      });
    });
  }

  function bindCalendarWeekScroll(root){
    if (!root) return;
    $$(".calendar-week-header", root).forEach(header => {
      const week = header.getAttribute("data-calendar-week") || "";
      const body = root.querySelector(`.calendar-week-body[data-calendar-week-body="${CSS.escape(week)}"]`);
      if (!body) return;
      let syncing = false;
      const sync = (source, target) => {
        if (syncing) return;
        syncing = true;
        target.scrollLeft = source.scrollLeft;
        requestAnimationFrame(() => { syncing = false; });
      };
      header.addEventListener("scroll", () => sync(header, body), { passive:true });
      body.addEventListener("scroll", () => sync(body, header), { passive:true });
    });
  }

  function scrollMetric(target, axis){
    if (!target) return { pos:0, size:0, scrollSize:0 };
    const horizontal = axis === "x";
    return {
      pos: horizontal ? target.scrollLeft : target.scrollTop,
      size: horizontal ? target.clientWidth : target.clientHeight,
      scrollSize: horizontal ? target.scrollWidth : target.scrollHeight
    };
  }

  function bindFloatingNavControls(host, scrollTarget, options = {}){
    if (!host || !scrollTarget) return;
    const horizontal = options.horizontal !== false;
    const vertical = options.vertical === true;
    if (!host.style.position && getComputedStyle(host).position === "static") host.style.position = "relative";
    let nav = host.querySelector(":scope > .floating-nav");
    if (!nav){
      host.insertAdjacentHTML("beforeend", `
        <div class="floating-nav" data-floating-nav-host="1" aria-label="Floating navigation controls">
          <button class="floating-nav__btn" type="button" data-floating-nav="left" aria-label="Scroll left">‹</button>
          <button class="floating-nav__btn" type="button" data-floating-nav="right" aria-label="Scroll right">›</button>
          <button class="floating-nav__btn" type="button" data-floating-nav="up" aria-label="Scroll up">⌃</button>
          <button class="floating-nav__btn" type="button" data-floating-nav="down" aria-label="Scroll down">⌄</button>
        </div>
      `);
      nav = host.querySelector(":scope > .floating-nav");
    }
    const buttons = $$("[data-floating-nav]", nav);
    const amount = (axis) => {
      const metric = scrollMetric(scrollTarget, axis);
      return Math.max(axis === "x" ? 180 : 160, Math.floor(metric.size * 0.82));
    };
    const update = () => {
      const x = scrollMetric(scrollTarget, "x");
      const y = scrollMetric(scrollTarget, "y");
      const canLeft = horizontal && x.pos > 1;
      const canRight = horizontal && x.pos + x.size < x.scrollSize - 1;
      const canUp = vertical && y.pos > 1;
      const canDown = vertical && y.pos + y.size < y.scrollSize - 1;
      const available = { left: canLeft, right: canRight, up: canUp, down: canDown };
      buttons.forEach(btn => {
        const dir = btn.getAttribute("data-floating-nav") || "";
        const show = !!available[dir];
        btn.hidden = !show;
        btn.disabled = !show;
      });
      nav.toggleAttribute("data-floating-nav-active", Object.values(available).some(Boolean));
    };
    buttons.forEach(btn => {
      if (btn.dataset.floatingBound === "1") return;
      btn.dataset.floatingBound = "1";
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const dir = btn.getAttribute("data-floating-nav") || "";
        if (dir === "left") scrollTarget.scrollBy({ left: -amount("x"), behavior: "smooth" });
        if (dir === "right") scrollTarget.scrollBy({ left: amount("x"), behavior: "smooth" });
        if (dir === "up") scrollTarget.scrollBy({ top: -amount("y"), behavior: "smooth" });
        if (dir === "down") scrollTarget.scrollBy({ top: amount("y"), behavior: "smooth" });
        setTimeout(update, 180);
      });
    });
    scrollTarget.addEventListener("scroll", update, { passive:true });
    window.addEventListener("resize", update, { passive:true });
    requestAnimationFrame(update);
  }

  function focusVisibleCarouselCard(carousel, dir){
    const viewport = $(".episode-carousel-viewport, .carousel-viewport", carousel);
    const cards = $$(".episode-carousel-track > .episode-card, .carousel-track > .media-card, .carousel-track > [tabindex]", carousel).filter(isVisible);
    if (!viewport || !cards.length) return;
    const viewportRect = viewport.getBoundingClientRect();
    const visibleCards = cards.filter(card => {
      const cardRect = card.getBoundingClientRect();
      return cardRect.right > viewportRect.left + 4 && cardRect.left < viewportRect.right - 4;
    });
    const target = dir < 0 ? visibleCards[0] : visibleCards[visibleCards.length - 1];
    if (target && typeof target.focus === "function") target.focus({ preventScroll:true });
  }

  function bindManualCarousels(root){
    if (!root) return;
    $$("[data-manual-carousel]", root).forEach(carousel => {
      if (carousel.dataset.manualCarouselBound === "1") return;
      carousel.dataset.manualCarouselBound = "1";
      const viewport = $(".episode-carousel-viewport, .carousel-viewport", carousel);
      const track = $(".episode-carousel-track, .carousel-track", carousel);
      const buttons = $$("[data-carousel-nav], [data-ep-nav]", carousel);
      if (!viewport || !track || !buttons.length) return;
      const pageAmount = () => Math.max(240, Math.floor(viewport.clientWidth * 0.86));
      const update = () => {
        const metric = scrollMetric(viewport, "x");
        const canPrev = metric.pos > 1;
        const canNext = metric.pos + metric.size < metric.scrollSize - 1;
        buttons.forEach(btn => {
          const action = btn.getAttribute("data-carousel-nav") || btn.getAttribute("data-ep-nav") || "";
          const enabled = /prev/.test(action) ? canPrev : /next/.test(action) ? canNext : true;
          btn.disabled = !enabled;
          btn.setAttribute("aria-disabled", enabled ? "false" : "true");
        });
      };
      const move = (direction) => {
        viewport.scrollBy({ left: direction * pageAmount(), behavior: "smooth" });
        setTimeout(() => {
          focusVisibleCarouselCard(carousel, direction);
          update();
        }, 220);
      };
      buttons.forEach(btn => {
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();
          const action = btn.getAttribute("data-carousel-nav") || btn.getAttribute("data-ep-nav") || "";
          if (/prev/.test(action)) move(-1);
          if (/next/.test(action)) move(1);
        });
      });
      carousel.addEventListener("keydown", (e) => {
        if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
        e.preventDefault();
        e.stopPropagation();
        move(e.key === "ArrowLeft" ? -1 : 1);
      });
      viewport.addEventListener("scroll", update, { passive:true });
      bindFloatingNavControls(carousel, viewport, { horizontal: true, vertical: false });
      requestAnimationFrame(update);
    });
  }

  function imageForCalendarItem(item){
    if (item?.kind === "episode"){
      return episodeStillImageForCard(item);
    }
    if (item?.kind === "movie"){
      const movie = getMovieById(item?.tmdb_id ?? "");
      return normalizeImageSrc(pickImage(movie || item, "poster_local", "poster_path"));
    }
    const show = getShowById(item?.show_tmdb_id ?? item?.show_id ?? item?.tmdb_id ?? "");
    return normalizeImageSrc(pickImage(show || item, "poster_local", "poster_path", "show_poster_local"));
  }

  function bindCalendarItemActions(root){
    if (!root) return;
    $$(".calendar-item[data-kind='episode']", root).forEach(card => card.addEventListener("click", (e) => {
      if (e.target.closest(".actionbar")) return;
      gotoShow(parseInt(card.getAttribute("data-show") || "0", 10));
    }));
    $$(".calendar-item[data-kind='movie']", root).forEach(card => card.addEventListener("click", (e) => {
      if (e.target.closest(".actionbar")) return;
      openMovieModal(parseInt(card.getAttribute("data-movie") || "0", 10));
    }));
    wireActionMenus(root);
    wireIconStripActions(root, renderCalendar);
    wireWatchSourceButtons(root);
    if (window.MyTVHubWatchState && typeof window.MyTVHubWatchState.refresh === "function") {
      window.MyTVHubWatchState.refresh(root);
    }
  }

  function buildIconStripHtml(kind, id, pct, titleText){
    const hasTarget = kind && id;
    if (!hasTarget) return "";
    const idStr = String(id || "");
    const item = kind === "movie" ? getMovieById(id) : getShowById(id);
    const watched = kind === "movie"
      ? isMovieWatched(item || { tmdb_id: id })
      : isShowWatched(item || { tmdb_id: id });
    const watchedToggleHtml = kind === "movie"
      ? watchToggleHtml("movie", { "data-watch-movie": idStr }, watched)
      : watchToggleHtml("show", { "data-watch-show": idStr }, watched);
    const popcornAttrs = kind === "movie" ? { "data-id": idStr } : null;
    return buildActionBarHtml(kind, idStr, {
      title: titleText || "",
      pct,
      favoriteActive: getWatchlistSet().has(idStr),
      watchedActive: watched,
      showWatchedAction: true,
      showStatusAction: true,
      watchedToggleHtml,
      popcornAttrs,
      popcornKind: kind === "movie" ? "movie" : kind,
      availabilityStatus: kind === "movie" ? availabilityStatusOf(item || {}) : "",
      available: kind === "movie" ? isMovieAvailable(item || {}) : isShowAvailable(item || {})
    });
  }

  function buildWatchMeEntries(){
    return collectUpcomingEvents(Number(state.watchMe?.windowDays) || 14, 0);
  }

  function watchMeMatches(entry){
    const query = safeText(state.watchMe?.search || "").trim().toLowerCase();
    if (!query) return true;
    const item = entry?.item || {};
    const values = [
      item?.show_title,
      item?.episode_name,
      item?.title,
      item?.name,
      item?.overview
    ].map(v => safeText(v).toLowerCase());
    return values.some(v => v.includes(query));
  }

  function renderWatchMeMovieRow(entry){
    const item = entry?.item || {};
    const movieId = Number(item?.tmdb_id ?? 0) || 0;
    const pct = Number.isFinite(item?.progress) ? Math.max(0, Math.min(100, item.progress)) : null;
    const watched = state.watchState ? isMovieWatched({ tmdb_id: movieId }) : false;
    const title = safeText(item?.title || "Movie");
    return `
      <article class="watchme-list-item watchme-movie-card" data-kind="movie" data-movie="${escHtml(movieId)}" tabindex="0" data-render-key="watchme:movie:${escHtml(movieId)}:${escHtml(entry?.dateKey || "")}">
        <button type="button" class="watchme-list-item__media" data-movie-open="${escHtml(movieId)}" aria-label="${escHtml(title)}">
          ${imageForCalendarItem(item) ? `<img src="${escHtml(imageForCalendarItem(item))}" alt="" loading="lazy" decoding="async" />` : `<span class="posterFallback__label">No Poster</span>`}
        </button>
        <div class="watchme-list-item__copy">
          <div class="watchme-list-item__eyebrow">Movie</div>
          <button type="button" class="watchme-list-item__title" data-movie-open="${escHtml(movieId)}">${escHtml(title)}</button>
          <div class="watchme-list-item__meta">${escHtml([watchMeDateLabel(entry?.dateKey), safeText(item?.runtime) ? `${item.runtime} min` : ""].filter(Boolean).join(" • "))}</div>
        </div>
        <div class="watchme-list-item__actions">
          ${buildActionBarHtml("movie", movieId, {
            title,
            compact: true,
            pct,
            favoriteActive: getWatchlistSet().has(String(movieId)),
            watchedActive: watched,
            showWatchedAction: true,
            showStatusAction: true,
            popcornAttrs: hasDirectWatchSources(item) ? { "data-id": movieId } : null,
            popcornKind: "movie",
            availabilityStatus: availabilityStatusOf(item),
            available: isMovieAvailable(item)
          })}
        </div>
      </article>
    `;
  }

  function renderWatchMeEpisodeRow(entry){
    const item = entry?.item || {};
    const showId = Number(item?.show_tmdb_id ?? item?.tmdb_id ?? 0) || 0;
    const seasonNum = Number(item?.season_number || 0);
    const episodeNum = Number(item?.episode_number || 0);
    const title = safeText(item?.episode_name || "Episode");
    const showTitle = safeText(item?.show_title || "Show");
    return `
      <article class="watchme-list-item watchme-episode-card" data-kind="episode" data-show="${escHtml(showId)}" tabindex="0" data-render-key="watchme:episode:${escHtml(showId)}:${escHtml(seasonNum)}:${escHtml(episodeNum)}:${escHtml(entry?.dateKey || "")}">
        <button type="button" class="watchme-list-item__media watchme-list-item__media--episode" data-show-open="${escHtml(showId)}" aria-label="${escHtml(`${showTitle}: ${title}`)}">
          ${imageForCalendarItem(item) ? `<img src="${escHtml(imageForCalendarItem(item))}" alt="" loading="lazy" decoding="async" />` : `<span class="posterFallback__label">No Still</span>`}
        </button>
        <div class="watchme-list-item__copy">
          <div class="watchme-list-item__eyebrow">${escHtml(showTitle)}</div>
          <button type="button" class="watchme-list-item__title" data-show-open="${escHtml(showId)}">${escHtml(title)}</button>
          <div class="watchme-list-item__meta">${escHtml([episodeMetaLine(seasonNum, episodeNum, item?.runtime), watchMeDateLabel(entry?.dateKey)].filter(Boolean).join(" • "))}</div>
        </div>
        <div class="watchme-list-item__actions">
          ${buildActionBarHtml("episode", episodeNum, {
        title,
        compact: true,
        tmdbId: safeText(item?.episode_tmdb_id ?? item?.episode_id ?? item?.tmdb_episode_id ?? item?.id ?? ""),
        traktId: safeText(item?.trakt_id || item?.episode_trakt_id || ""),
        tvdbId: safeText(item?.tvdb_id || item?.episode_tvdb_id || ""),
        pct: progressPercent(item),
        watchedActive: state.watchState ? isEpisodeWatched(showId, seasonNum, episodeNum) : false,
        showWatchedAction: true,
        showStatusAction: true,
        watchedAttrs: { "data-show": showId, "data-season": seasonNum, "data-watch-episode": episodeNum },
        popcornAttrs: hasDirectWatchSources(item) ? { "data-show": showId, "data-season": seasonNum, "data-episode": episodeNum } : null,
        popcornKind: "episode",
        availabilityStatus: availabilityStatusOf(item),
        available: isEpisodeAvailable(item),
        statusContext: { showId, seasonNumber: seasonNum, episodeNumber: episodeNum }
      })}
        </div>
      </article>
    `;
  }

  function watchMeDateLabel(dateKey){
    return dateKey ? formatDateShort(dateKey) : "";
  }

  function renderWatchMeGroup(title, entries){
    if (!entries.length){
      return `<section class="dashblock"><div class="dashhead"><h2>${escHtml(title)}</h2><span class="muted">No matches</span></div></section>`;
    }
    const grouped = new Map();
    dedupeItems(entries, entry => `${safeText(entry?.dateKey || "")}|${itemRenderKey(entry?.item || {}, safeText(entry?.dateKey || ""))}`).forEach(entry => {
      const key = safeText(entry?.dateKey || "");
      if (!key) return;
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key).push(entry);
    });
    return `
      <section class="dashblock">
        <div class="dashhead">
          <h2>${escHtml(title)}</h2>
          <span class="muted">${entries.length} ${entries.length === 1 ? "item" : "items"}</span>
        </div>
        ${Array.from(grouped.entries()).sort((a, b) => a[0].localeCompare(b[0])).map(([dateKey, groupItems]) => `
          <div class="watchme-day-group" data-date-key="${escHtml(dateKey)}">
            <div class="watchme-day-group__head">
              <div class="watchme-day-group__title">${escHtml(watchMeDateLabel(dateKey))}</div>
              <div class="watchme-day-group__meta">${escHtml(groupItems.length === 1 ? "1 title" : `${groupItems.length} titles`)}</div>
            </div>
            <div class="watchme-list">
              ${groupItems.map(entry => entry.item?.kind === "episode" ? renderWatchMeEpisodeRow(entry) : renderWatchMeMovieRow(entry)).join("")}
            </div>
          </div>
        `).join("")}
      </section>
    `;
  }

  function renderWatchMe(){
    const root = $("#watchMeSections");
    if (!root) return;
    const entries = dedupeItems(buildWatchMeEntries().filter(watchMeMatches), entry => `${safeText(entry?.dateKey || "")}|${itemRenderKey(entry?.item || {}, safeText(entry?.dateKey || ""))}`);
    const type = safeText(state.watchMe?.type || "all");
    const episodes = entries.filter(entry => safeText(entry?.item?.kind) === "episode");
    const movies = entries.filter(entry => safeText(entry?.item?.kind) === "movie");
    const sections = [];
    if (type === "all" || type === "episodes") sections.push(renderWatchMeGroup("Upcoming Episodes", episodes));
    if (type === "all" || type === "movies") sections.push(renderWatchMeGroup("Upcoming Movies", movies));
    root.innerHTML = sections.join("") || `<section class="dashblock"><div class="muted">No items match the current filters.</div></section>`;
    const summary = $("#watchMeSummary");
    if (summary) summary.textContent = `${episodes.length} episodes • ${movies.length} movies • next ${Number(state.watchMe?.windowDays) || 14} days`;
    wireActionMenus(root);
    wireIconStripActions(root, renderWatchMe);
    wireWatchSourceButtons(root);
    $$(".watchme-episode-card[data-show]", root).forEach(card => card.addEventListener("click", (e) => {
      if (e.target.closest(".actionbar")) return;
      if (e.target.closest("button[data-show-open]")) return;
      gotoShow(parseInt(card.getAttribute("data-show") || "0", 10));
    }));
    $$(".watchme-movie-card[data-movie]", root).forEach(card => card.addEventListener("click", (e) => {
      if (e.target.closest(".actionbar")) return;
      if (e.target.closest("button[data-movie-open]")) return;
      openMovieModal(parseInt(card.getAttribute("data-movie") || "0", 10));
    }));
  }

  function renderShows(){
    const q = state.search.shows.trim().toLowerCase();
    const sort = state.sort.shows;
    const f = state.filters.shows;
    const scope = safeText(f.scope || "all");
    const wantGenres = Array.isArray(f.genres) ? f.genres : [];
    const wantYear = safeText(f.year);
    const wantWatched = safeText(f.watched);
    const wantWatchlist = safeText(f.watchlist);
    const wantWatchStatus = Array.isArray(f.watch_status) ? f.watch_status : [];
    const wantAvailability = safeText(f.availability || "all");
    const watchlistSet = getWatchlistSet();

    const shows = (state.data?.shows || []).filter(s => {
      const t = safeText(s?.title || s?.name).toLowerCase();
      if (q && !t.includes(q)) return false;
      if (wantGenres.length){
        const g = Array.isArray(s?.genres) ? s.genres.map(x => x?.name).filter(Boolean) : [];
        if (!wantGenres.some(w => g.includes(w))) return false;
      }
      if (wantYear){
        const y = yearFromDate(s?.first_air_date);
        if (y !== wantYear) return false;
      }
      const id = String(s?.tmdb_id ?? "");
      if (wantWatchlist === "watchlist"){
        if (!id || !canonicalWatchListActive("show", id, watchlistSet.has(id))) return false;
      }
      if (wantWatchStatus.length){
        const status = safeText(getLocalStatusValue("show", id)).toLowerCase();
        if (status){
          if (!wantWatchStatus.includes(status)) return false;
        } else if (wantWatchlist === "watchlist"){
          return false;
        }
      }
      const statusText = safeText(s?.status).toLowerCase();
      const firstAirRaw = safeText(s?.first_air_date);
      const firstAirDate = firstAirRaw ? new Date(firstAirRaw) : null;
      const isUpcoming = firstAirDate instanceof Date && !Number.isNaN(firstAirDate.valueOf()) && firstAirDate > new Date();
      if (scope === "current" && !isCurrentShow(s)) return false;
      if (scope === "upcoming" && !isUpcoming) return false;
      if (scope === "returning" && statusText !== "returning series") return false;
      if (scope === "ended" && statusText !== "ended") return false;
      if (wantAvailability !== "all"){
        const status = availabilityStatusOf(s);
        if (wantAvailability === "available" && status !== "available") return false;
        if (wantAvailability === "unreleased" && status !== "not_yet_released") return false;
      }
      if (wantWatched === "watched" && !isShowWatched(s)) return false;
      if (wantWatched === "unwatched" && isShowWatched(s)) return false;
      const eye = applyEyeFilter("shows", s);
      if (eye.hide) return false;
      return true;
    });

    if (sort === "title") shows.sort((a,b)=>sortByTitle(a,b,false));
    if (sort === "title_desc") shows.sort((a,b)=>sortByTitle(a,b,true));
    if (sort === "popularity") shows.sort((a,b)=>(Number(b?.popularity)||0)-(Number(a?.popularity)||0));
    if (sort === "vote") shows.sort((a,b)=>(Number(b?.vote_average)||0)-(Number(a?.vote_average)||0));
    if (sort === "release") shows.sort((a,b)=>safeText(b?.first_air_date).localeCompare(safeText(a?.first_air_date)));

    $("#showsGrid").innerHTML = shows.map(s => showCardHtml(s, applyEyeFilter("shows", s))).join("");
    const showsSummary = $("#showsSummary");
    if (showsSummary) showsSummary.textContent = `${shows.length} results`;
    wireActionMenus($("#showsGrid"));
    wireIconStripActions($("#showsGrid"), renderShows);
    if (window.MyTVHubWatchState && typeof window.MyTVHubWatchState.refresh === "function") {
      window.MyTVHubWatchState.refresh($("#showsGrid"));
    }

    $$("[data-show-open]", $("#showsGrid")).forEach(el => {
      el.addEventListener("click", () => {
        const id = parseInt(el.getAttribute("data-show-open"), 10);
        gotoShow(id);
      });
    });
    $$("[data-watch-show]", $("#showsGrid")).forEach(el => {
      el.addEventListener("change", async (e) => {
        e.stopPropagation();
        const id = parseInt(el.getAttribute("data-watch-show"), 10);
        if (!Number.isFinite(id)) return;
        const on = el.checked;
        const show = await getShowDetailById(id);
        if (!show) return;
        setShowWatched(id, show.seasons || [], on);
        await saveInputs();
        renderShows();
      });
    });
    wireWatchSourceButtons($("#showsGrid"));
    $$("[data-action='toggle-watched'][data-kind='show']", $("#showsGrid")).forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const id = parseInt(btn.getAttribute("data-id") || "0", 10);
        if (!Number.isFinite(id)) return;
        const show = await getShowDetailById(id);
        if (!show) return;
        const on = !isShowWatched(show);
        setShowWatched(id, show.seasons || [], on);
        await saveInputs();
        renderShows();
      });
    });
  }

  function renderMovies(){
    const q = state.search.movies.trim().toLowerCase();
    const sort = state.sort.movies;
    const f = state.filters.movies;
    const scope = safeText(f.scope || "all");
    const wantGenres = Array.isArray(f.genres) ? f.genres : [];
    const wantYear = safeText(f.year);
    const wantWatched = safeText(f.watched);
    const wantWatchlist = safeText(f.watchlist);
    const wantWatchStatus = Array.isArray(f.watch_status) ? f.watch_status : [];
    const wantAvailability = safeText(f.availability || "all");
    const wantCollection = safeText(f.collection).toLowerCase();
    const watchlistSet = getWatchlistSet();

    const movies = (state.data?.movies || []).filter(m => {
      const t = safeText(m?.title).toLowerCase();
      if (q && !t.includes(q)) return false;
      if (wantGenres.length){
        const g = Array.isArray(m?.genres) ? m.genres.map(x => x?.name).filter(Boolean) : [];
        if (!wantGenres.some(w => g.includes(w))) return false;
      }
      if (wantYear){
        const y = yearFromDate(m?.release_date);
        if (y !== wantYear) return false;
      }
      if (wantCollection){
        const cn = safeText(m?.collection?.name).toLowerCase();
        if (!cn.includes(wantCollection)) return false;
      }
      const id = String(m?.tmdb_id ?? "");
      if (wantWatchlist === "watchlist"){
        if (!id || !canonicalWatchListActive("movie", id, watchlistSet.has(id))) return false;
      }
      if (wantWatchStatus.length){
        const status = safeText(getLocalStatusValue("movie", id)).toLowerCase();
        if (status){
          if (!wantWatchStatus.includes(status)) return false;
        } else if (wantWatchlist === "watchlist"){
          return false;
        }
      }
      const releaseRaw = safeText(m?.release_date);
      const releaseDate = releaseRaw ? new Date(releaseRaw) : null;
      const isUpcoming = releaseDate instanceof Date && !Number.isNaN(releaseDate.valueOf()) && releaseDate > new Date();
      if (scope === "current" && !isCurrentMovie(m)) return false;
      if (scope === "upcoming" && !isUpcoming) return false;
      if (scope === "released" && isUpcoming) return false;
      if (wantAvailability !== "all"){
        const status = availabilityStatusOf(m);
        if (wantAvailability === "available" && status !== "available") return false;
        if (wantAvailability === "unreleased" && status !== "not_yet_released") return false;
      }
    if (wantWatched === "watched" && !isMovieWatched(m)) return false;
    if (wantWatched === "unwatched" && isMovieWatched(m)) return false;
    const eye = applyEyeFilter("movies", m);
    if (eye.hide) return false;
      return true;
    });

    if (sort === "title") movies.sort((a,b)=>safeText(a?.title).localeCompare(safeText(b?.title)));
    if (sort === "title_desc") movies.sort((a,b)=>safeText(b?.title).localeCompare(safeText(a?.title)));
    if (sort === "popularity") movies.sort((a,b)=>(Number(b?.popularity)||0)-(Number(a?.popularity)||0));
    if (sort === "vote") movies.sort((a,b)=>(Number(b?.vote_average)||0)-(Number(a?.vote_average)||0));
    if (sort === "release") movies.sort((a,b)=>safeText(b?.release_date).localeCompare(safeText(a?.release_date)));

    $("#moviesGrid").innerHTML = movies.map(m => movieCardHtml(m, applyEyeFilter("movies", m))).join("");
    const moviesSummary = $("#moviesSummary");
    if (moviesSummary) moviesSummary.textContent = `${movies.length} results`;
    wireActionMenus($("#moviesGrid"));
    wireIconStripActions($("#moviesGrid"), renderMovies);
    if (window.MyTVHubWatchState && typeof window.MyTVHubWatchState.refresh === "function") {
      window.MyTVHubWatchState.refresh($("#moviesGrid"));
    }

    $$("[data-movie-open]", $("#moviesGrid")).forEach(el => {
      el.addEventListener("click", () => {
        const id = parseInt(el.getAttribute("data-movie-open"), 10);
        openMovieModal(id);
      });
    });
    $$("[data-watch-movie]", $("#moviesGrid")).forEach(el => {
      el.addEventListener("click", (e) => e.stopPropagation());
      el.addEventListener("mousedown", (e) => e.stopPropagation());
      el.addEventListener("touchstart", (e) => e.stopPropagation(), { passive: true });
      el.addEventListener("change", async (e) => {
        e.stopPropagation();
        const id = parseInt(el.getAttribute("data-watch-movie"), 10);
        if (!Number.isFinite(id)) return;
        setMovieWatched(id, el.checked);
        await saveInputs();
        renderMovies();
      });
    });
    wireWatchSourceButtons($("#moviesGrid"));
    $$("[data-action='toggle-watched'][data-kind='movie']", $("#moviesGrid")).forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const id = parseInt(btn.getAttribute("data-id") || "0", 10);
        if (!Number.isFinite(id)) return;
        const on = !isMovieWatched(getMovieById(id));
        setMovieWatched(id, on);
        await saveInputs();
        renderMovies();
      });
    });
  }

  function renderWatchlist(){
    const list = ensureWatchlist();
    const q = state.filters.watchlist.search.trim().toLowerCase();
    const statusFilter = safeText(state.filters.watchlist.watch_status);
    const kindFilter = safeText(state.filters.watchlist.media_kind);
    const shows = Array.isArray(state.data?.shows) ? state.data.shows : [];
    const movies = Array.isArray(state.data?.movies) ? state.data.movies : [];
    const showMap = new Map(shows.map(s => [String(s?.tmdb_id ?? ""), s]));
    const movieMap = new Map(movies.map(m => [String(m?.tmdb_id ?? ""), m]));

    const items = list.map(item => {
      const id = String(item?.tmdb_id ?? "");
      const show = id ? showMap.get(id) : null;
      const movie = id ? movieMap.get(id) : null;
      const kind = safeText(item?.media_kind || (show ? "show" : (movie ? "movie" : "unknown"))).toLowerCase() || "unknown";
      const title = safeText(item?.title || show?.title || show?.name || movie?.title || "Untitled");
      const status = safeText(item?.watch_status || "watchlist").toLowerCase();
      return { item, id, show, movie, kind, title, status };
    }).filter(entry => {
      if (q && !entry.title.toLowerCase().includes(q)) return false;
      if (statusFilter && statusFilter !== "all" && entry.status !== statusFilter) return false;
      if (kindFilter && kindFilter !== "all" && entry.kind !== kindFilter) return false;
      return true;
    });

    const html = items.map(entry => {
      const poster = entry.show ? pickImage(entry.show, "poster_local", "poster_path")
        : (entry.movie ? pickImage(entry.movie, "poster_local", "poster_path") : "");
      const watched = entry.show ? isShowWatched(entry.show) : (entry.movie ? isMovieWatched(entry.movie) : false);
      const flag = state.watchState ? watchFlagHtml(watched) : "";
      const statusOptions = WATCHLIST_STATUS_OPTIONS.map(o => {
        const sel = o.value === entry.status ? "selected" : "";
        return `<option value="${escHtml(o.value)}" ${sel}>${escHtml(o.label)}</option>`;
      }).join("");
      const openBtn = entry.kind === "show"
        ? `<button class="btn" type="button" data-watchlist-open="show" data-id="${escHtml(entry.id)}">Open</button>`
        : (entry.kind === "movie"
          ? `<button class="btn" type="button" data-watchlist-open="movie" data-id="${escHtml(entry.id)}">Open</button>`
          : "");
      return `
        <div class="watchlistcard" data-watchlist-id="${escHtml(entry.id)}">
          <div class="watchlistthumb">
            ${poster ? `<img loading="lazy" decoding="async" src="${escHtml(poster)}" alt=""/>` : ""}
          </div>
          <div class="watchlistbody">
            <div class="watchlisttitle">${escHtml(entry.title)}</div>
            <div class="watchlistmeta">${escHtml(entry.kind || "unknown")}</div>
            ${flag}
            <select class="input" data-watchlist-status="${escHtml(entry.id)}">
              ${statusOptions}
            </select>
            <div class="watchlistactions">
              ${openBtn}
              <button class="btn" type="button" data-watchlist-remove="${escHtml(entry.id)}">Remove</button>
            </div>
          </div>
        </div>
      `;
    }).join("");

    $("#watchlistGrid").innerHTML = html || `<div class="muted" style="padding:10px;">No watchlist items match your filters.</div>`;

    $$("[data-watchlist-status]", $("#watchlistGrid")).forEach(sel => {
      sel.addEventListener("change", async () => {
        const id = sel.getAttribute("data-watchlist-status");
        const card = sel.closest("[data-watchlist-id]");
        const title = card ? safeText($(".watchlisttitle", card)?.textContent || "") : "";
        const kind = card ? safeText($(".watchlistmeta", card)?.textContent || "") : "";
        setWatchlistStatus(id, title, kind, sel.value || "watchlist");
        await saveInputs();
        renderWatchlist();
      });
    });

    $$("[data-watchlist-remove]", $("#watchlistGrid")).forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-watchlist-remove");
        removeWatchlistItem(id);
        await saveInputs();
        renderWatchlist();
      });
    });

    $$("[data-watchlist-open]", $("#watchlistGrid")).forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.getAttribute("data-id") || "0", 10);
        if (!Number.isFinite(id)) return;
        const kind = btn.getAttribute("data-watchlist-open");
        if (kind === "show") gotoShow(id);
        if (kind === "movie") openMovieModal(id);
      });
    });
  }

  async function renderInputsEditor(){
    const meta = $("#inputsEditorPanelMeta");
    const openBtn = $("#inputsEditorOpen");
    const copyBtn = $("#inputsEditorCopyCommand");
    const helpBtn = $("#inputsEditorHelp");
    const localServerUrl = `http://127.0.0.1:8787/web/inputs_editor.html`;
    if (!meta || !openBtn) return;

    state.inputsEditorServerAvailable = await checkInputsEditorServerAvailable();
    state.apiAvailable = state.inputsEditorServerAvailable;

    openBtn.href = localServerUrl;
    openBtn.textContent = state.inputsEditorServerAvailable ? "Open Local Editor" : "Open After Start";
    openBtn.title = state.inputsEditorServerAvailable ? "Open the local Inputs Editor in a new tab" : "Start run_local_servers.bat first, then open the editor";
    openBtn.tabIndex = 0;
    openBtn.setAttribute("aria-disabled", "false");
    openBtn.classList.remove("disabled");
    openBtn.onclick = null;
    meta.textContent = state.inputsEditorServerAvailable
      ? "Local server is running. Open the editor in its own tab to avoid duplicate shells and failed embedded refreshes."
      : "Local server is not running. Copy the command below, run it from the repo, then open the editor.";
    if (copyBtn && !copyBtn.dataset.bound){
      copyBtn.dataset.bound = "1";
      copyBtn.addEventListener("click", async () => {
        const ok = await copyTextToClipboard("run_local_servers.bat");
        copyBtn.textContent = ok ? "Copied" : "Copy Failed";
        setTimeout(() => { copyBtn.textContent = "Copy Start Command"; }, 1800);
      });
    }
    if (helpBtn && !helpBtn.dataset.bound){
      helpBtn.dataset.bound = "1";
      helpBtn.addEventListener("click", openInputsEditorHelp);
    }
  }

  function wireMoviePopup(movieId){
    const host = $("#modalBody");
    if (!host) return;
    wirePopupDpad(host);
    const watchedBtn = $("[data-action='toggle-watched'][data-kind='movie']", host);
    if (watchedBtn){
      watchedBtn.addEventListener("click", async (e) => {
        e.preventDefault();
        setMovieWatched(movieId, !isMovieWatched(getMovieById(movieId)));
        await saveInputs();
        openMovieModal(movieId);
      });
    }
    const favBtn = $("[data-action='toggle-want'][data-kind='movie']", host);
    if (favBtn){
      favBtn.addEventListener("click", async (e) => {
        e.preventDefault();
        const movie = getMovieById(movieId);
        await toggleWantForKind("movie", movieId, safeText(movie?.title || "Movie"));
        await saveInputs();
        openMovieModal(movieId);
      });
    }
    wireActionMenus(host);
    wireWatchSourceButtons(host);
    if (window.MyTVHubWatchState && typeof window.MyTVHubWatchState.refresh === "function") {
      window.MyTVHubWatchState.refresh(host);
    }
  }

  async function openShowModal(showId){
    const showIndex = getShowById(showId);
    if (!showIndex){
      openModal("Show", `<div>Show not found: ${escHtml(showId)}</div>`);
      return;
    }
    state.show.tmdb_id = showId;
    openModal("Show", `<div class="muted">Loading show details…</div>`);
    const show = await getShowDetailById(showId);
    if (!show){
      $("#modalBody").innerHTML = `<div class="inline-error">Show detail not found: ${escHtml(showId)}</div>`;
      return;
    }
    $("#modalBody").innerHTML = buildShowPopupHtml(show);
    wireShowPopup(showId, show);
  }

  function wireShowPopup(showId, show){
    const host = $("#modalBody");
    if (!host || !show) return;

    $$("[data-season-pick]", host).forEach(btn => {
      btn.addEventListener("click", () => {
        const v = Number(btn.getAttribute("data-season-pick") || "0");
        if (!Number.isFinite(v)) return;
        state.show.selectedSeasonNumber = v;
        $("#modalBody").innerHTML = buildShowPopupHtml(show);
        wireShowPopup(showId, show);
      });
    });

    $$("[data-watch-show]", host).forEach(btn => {
      btn.addEventListener("change", async () => {
        const id = parseInt(btn.getAttribute("data-watch-show") || "0", 10);
        if (!Number.isFinite(id)) return;
        setShowWatched(id, show.seasons || [], !!btn.checked);
        await saveInputs();
        await openShowModal(id);
      });
    });
    $$("[data-action='toggle-want'][data-kind='show']", host).forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.preventDefault();
        await toggleWantForKind("show", showId, safeText(show?.title || show?.name || "Show"));
        await saveInputs();
        await openShowModal(showId);
      });
    });
    $$("[data-action='toggle-watched'][data-kind='show']", host).forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.preventDefault();
        setShowWatched(showId, show.seasons || [], !isShowWatched(show));
        await saveInputs();
        await openShowModal(showId);
      });
    });
    $$("[data-watch-season]", host).forEach(btn => {
      btn.addEventListener("change", async () => {
        const id = parseInt(btn.getAttribute("data-show") || "0", 10);
        const seasonNum = Number(btn.getAttribute("data-season") || "0");
        if (!Number.isFinite(id) || !Number.isFinite(seasonNum)) return;
        const season = (show.seasons || []).find(s => Number(s?.season_number ?? s?.number) === Number(seasonNum)) || null;
        const eps = (season?.episodes || []).map(e => Number(e?.episode_number ?? e?.number)).filter(n => Number.isFinite(n));
        setSeasonWatched(id, seasonNum, eps, !!btn.checked);
        await saveInputs();
        await openShowModal(id);
      });
    });

    $$("[data-watch-episode]", host).forEach(btn => {
      btn.addEventListener("change", async () => {
        const id = parseInt(btn.getAttribute("data-show") || "0", 10);
        const seasonNum = Number(btn.getAttribute("data-season") || "0");
        const episodeNum = Number(btn.getAttribute("data-watch-episode") || btn.getAttribute("data-episode") || "0");
        if (!Number.isFinite(id) || !Number.isFinite(seasonNum) || !Number.isFinite(episodeNum)) return;
        setEpisodeWatched(id, seasonNum, episodeNum, !!btn.checked);
        await saveInputs();
        await openShowModal(id);
      });
    });
    $$("[data-action='toggle-watched'][data-kind='episode'][data-watch-episode]", host).forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.preventDefault();
        const id = parseInt(btn.getAttribute("data-show") || "0", 10);
        const seasonNum = Number(btn.getAttribute("data-season") || "0");
        const episodeNum = Number(btn.getAttribute("data-watch-episode") || btn.getAttribute("data-episode") || "0");
        if (!Number.isFinite(id) || !Number.isFinite(seasonNum) || !Number.isFinite(episodeNum)) return;
        setEpisodeWatched(id, seasonNum, episodeNum, !isEpisodeWatched(id, seasonNum, episodeNum));
        await saveInputs();
        await openShowModal(id);
      });
    });

    wireActionMenus(host);
    wireWatchSourceButtons(host);
    if (window.MyTVHubWatchState && typeof window.MyTVHubWatchState.refresh === "function") {
      window.MyTVHubWatchState.refresh(host);
    }

    const bindCarousel = (trackSelector, attrName) => {
      const track = $(trackSelector, host);
      const buttons = $$(`[${attrName}]`, host);
      if (!track || !buttons.length) return;
      const scrollBy = (multiplier = 1) => Math.max(220, Math.floor(track.clientWidth * 0.72 * multiplier));
      buttons.forEach(btn => {
        btn.addEventListener("click", () => {
          const action = safeText(btn.getAttribute(attrName));
          if (action === "prev") track.scrollBy({ left: -scrollBy(1), behavior: "smooth" });
          if (action === "next") track.scrollBy({ left: scrollBy(1), behavior: "smooth" });
          if (action === "jump-prev") track.scrollBy({ left: -scrollBy(2), behavior: "smooth" });
          if (action === "jump-next") track.scrollBy({ left: scrollBy(2), behavior: "smooth" });
        });
      });
    };

    bindCarousel("[data-season-track]", "data-season-nav");
    bindFloatingNavControls($(".seasonrail", host), $("[data-season-track]", host), { horizontal: true, vertical: false });
    bindManualCarousels(host);
  }

  function renderCalendar(){
    const month = state.calendarMonth;
    const calMonth = $("#calMonth");
    if (calMonth) calMonth.textContent = month.toLocaleDateString(undefined, { month: "long", year: "numeric" });
    updateTodayLabel();

    const today = toDateKey(new Date());
    const firstDow = new Date(month.getFullYear(), month.getMonth(), 1).getDay();
    const startOffset = (firstDow + 6) % 7;
    const gridStart = new Date(month.getFullYear(), month.getMonth(), 1 - startOffset);
    const eventsByDate = buildCalendarEventsForMonth(month);
    const days = [];
    for (let i = 0; i < 42; i++){
      const dt = new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + i);
      days.push({ dt, key: toDateKey(dt), inMonth: dt.getMonth() === month.getMonth(), num: dt.getDate() });
    }
    const weeks = Array.from({ length: 6 }, (_, idx) => days.slice(idx * 7, idx * 7 + 7));

    const renderItem = (item, dateKey, hidden = false) => {
      if (item.kind === "episode"){
        const showId = Number(item.show_tmdb_id) || 0;
        const seasonNum = Number(item.season_number) || 0;
        const episodeNum = Number(item.episode_number) || 0;
        return buildSharedEpisodeCard(item, {
          image: imageForCalendarItem(item),
          eyebrow: item.show_title || "Show",
          title: item.episode_name || "Episode",
          meta: episodeMetaLine(seasonNum, episodeNum, item.runtime, safeText(item?.episode_tmdb_id ?? item?.episode_id ?? item?.tmdb_episode_id ?? item?.id ?? "")),
          submeta: "",
          overlay: true,
          density: "compact",
          articleAttrs: { "data-day": dateKey, "data-kind": "episode", "data-show": showId, tabindex: "0" },
          extraClass: `calendar-item calendar-item--episode${expandableClass(hidden)}`
        });
      }

      const movieId = Number(item.tmdb_id) || 0;
      const pct = Number.isFinite(item.progress) ? Math.max(0, Math.min(100, item.progress)) : null;
      const hasSources = hasDirectWatchSources(item);
      const watched = state.watchState ? isMovieWatched({ tmdb_id: movieId }) : false;
      return window.MyTVHubSharedModules.cardRenderer.renderCompactCardHtml({
        kind: "movie",
        id: movieId,
        image: imageForCalendarItem(item),
        title: item.title || "Movie",
        badgeHtml: "",
        meta: "Movie",
        submeta: "Release day",
        overlay: true,
        actionBarHtml: buildActionBarHtml("movie", movieId, {
          title: item.title || "Movie",
          compact: true,
          pct,
          favoriteActive: getWatchlistSet().has(String(movieId)),
          showWatchedAction: true,
          watchedActive: watched,
          showStatusAction: true,
          popcornAttrs: hasSources ? { "data-id": movieId } : null,
          popcornKind: "movie",
          availabilityStatus: availabilityStatusOf(item),
          available: isDateAvailable(item.release_date || dateKey)
        }),
        articleAttrs: { "data-day": dateKey, "data-kind": "movie", "data-movie": movieId, tabindex: "0" },
        extraClass: `calendar-item calendar-item--movie${expandableClass(hidden)}`,
        renderKey: `calendar:movie:${movieId}:${dateKey}`
      });
    };

    const renderBandDay = ({ dt, key, inMonth }) => `
      <div class="calendar-week-band__day${inMonth ? "" : " is-other-month"}${key === today ? " is-today" : ""}${(dt.getDay() === 0 || dt.getDay() === 6) ? " is-weekend" : ""}">
        <span class="calendar-week-band__weekday">${escHtml(dt.toLocaleDateString(undefined, { weekday: "short" }))}</span>
        <span class="calendar-week-band__date">${escHtml(dt.toLocaleDateString(undefined, { month: "short", day: "numeric" }))}</span>
      </div>
    `;
    const renderDayCell = ({ dt, key, inMonth, num }) => {
      const items = dedupeItems(eventsByDate.get(key) || [], item => itemRenderKey(item, key));
      const visibleLimit = state.calendarView === "list" ? items.length : 4;
      const visible = items.map((item, index) => renderItem(item, key, index >= visibleLimit)).join("");
      const more = renderMoreButton(Math.max(0, items.length - visibleLimit), `calendar-${key}`);
      return `
        <section class="calendar-day${inMonth ? "" : " calendar-day--other-month"}${key === today ? " calendar-day--today" : ""}${(dt.getDay() === 0 || dt.getDay() === 6) ? " calendar-day--weekend" : ""}" data-daycell="${key}">
          <div class="calendar-day__items" data-more-id="calendar-${escHtml(key)}">
            ${visible || `<div class="calendar-day__empty">${inMonth ? "No releases" : ""}</div>`}
            ${more}
          </div>
        </section>
      `;
    };
    const renderTreeDay = ({ dt, key, num }) => {
      const items = dedupeItems(eventsByDate.get(key) || [], item => itemRenderKey(item, key));
      return `
        <details class="calendar-tree-day${key === today ? " is-today" : ""}${(dt.getDay() === 0 || dt.getDay() === 6) ? " calendar-tree-day--weekend" : ""}" data-daycell="${key}"${key === today ? " open" : ""}>
          <summary class="calendar-tree-day__summary">
            <span class="calendar-tree-day__date">
              <span class="calendar-tree-day__weekday">${escHtml(dt.toLocaleDateString(undefined, { weekday: "short" }))}</span>
              <span class="calendar-tree-day__label">${escHtml(dt.toLocaleDateString(undefined, { month: "short" }))} ${num}</span>
            </span>
            <span class="calendar-tree-day__count">${escHtml(items.length === 0 ? "No releases" : items.length === 1 ? "1 release" : `${items.length} releases`)}</span>
          </summary>
          <div class="calendar-tree-day__items">
            ${items.length ? items.map(item => renderItem(item, key)).join("") : `<div class="calendar-day__empty">No releases</div>`}
          </div>
        </details>
      `;
    };
    $("#calendar").innerHTML = state.calendarView === "list"
      ? `
        <div class="calendar-tree-list">
          ${days.filter(day => day.inMonth).map(renderTreeDay).join("")}
        </div>
      `
      : `
        <div class="calendar-scroller calendar-month-grid">
          ${weeks.map((week, weekIndex) => `
            <div class="calendar-week-header calendar-week-band" data-calendar-week="${weekIndex}">
              ${week.map(renderBandDay).join("")}
            </div>
            <div class="calendar-week-body" data-calendar-week-body="${weekIndex}">
              ${week.map(renderDayCell).join("")}
            </div>
          `).join("")}
        </div>
      `;
    requestAnimationFrame(() => updateCalendarStickyVars());
    applyStickySectionHeads($("#panel-calendar"));
    bindCalendarItemActions($("#calendar"));
    bindMoreToggles($("#calendar"));
    bindCalendarWeekScroll($("#calendar"));
    bindFloatingNavControls($("#calendar"), $(".calendar-scroller", $("#calendar")), { horizontal: true, vertical: false });
  }

  function renderDashboard(){
    const scheduleCols = $("#dashScheduleCols");
    const lastWeekCols = $("#dashLastWeekCols");
    const watchlistEl = $("#dashWatchlist");
    const showRecs = $("#dashShowRecs");
    const movieRecs = $("#dashMovieRecs");
    if (!scheduleCols || !lastWeekCols || !watchlistEl || !showRecs || !movieRecs) return;

    const showMap = state.showById || new Map();
    const movieMap = state.movieById || new Map();
    const events = dedupeItems(collectUpcomingEvents(7, 1), entry => `${entry.dateKey}|${itemRenderKey(entry.item, entry.dateKey)}`);
    const lastWeekOffset = Math.max(0, Number(state.dashboard?.lastWeekOffsetWeeks) || 0);
    const pastEvents = dedupeItems(collectPastEvents(7, lastWeekOffset, true), entry => `${entry.dateKey}|${itemRenderKey(entry.item, entry.dateKey)}`);

    const percentForItem = (item) => {
      let pct = progressPercent(item);
      if (pct == null){
        const raw = Number(item?.vote_average ?? item?.rating ?? 0);
        if (Number.isFinite(raw) && raw > 0) pct = Math.round(raw * 10);
      }
      return pct;
    };
    const infoTarget = (item) => item?.kind === "movie"
      ? { kind: "movie", id: item?.tmdb_id }
      : { kind: "show", id: item?.show_tmdb_id || item?.tmdb_id };
    const imageForItem = (item) => {
      if (item?.kind === "episode") return episodeStillImageForCard(item);
      if (item?.thumb) return normalizeImageSrc(item.thumb);
      const media = item?.kind === "movie" ? movieMap.get(String(item?.tmdb_id ?? "")) : showMap.get(String(item?.tmdb_id ?? ""));
      return normalizeImageSrc(pickImage(media || item, "poster_local", "poster_path", "backdrop_local", "backdrop_path"));
    };
    const eventCard = (item, tertiary = "", hidden = false, renderKey = "") => {
      if (item.kind === "episode"){
        const showId = Number(item.show_tmdb_id) || 0;
        const seasonNum = Number(item.season_number) || 0;
        const episodeNum = Number(item.episode_number) || 0;
        return buildSharedEpisodeCard(item, {
          image: imageForItem(item),
          eyebrow: safeText(item.show_title || "Show"),
          title: safeText(item.episode_name || "Episode"),
          meta: episodeMetaLine(seasonNum, episodeNum, item.runtime, safeText(item?.episode_tmdb_id ?? item?.episode_id ?? item?.tmdb_episode_id ?? item?.id ?? "")),
          submeta: tertiary,
          overlay: true,
          density: "standard",
          pct: percentForItem(item),
          articleAttrs: { "data-show": showId, tabindex: "0" },
          renderKey: renderKey || `dashboard:event:episode:${showId}:${seasonNum}:${episodeNum}`,
          extraClass: `dashcard dashcard--clean${expandableClass(hidden)}`
        });
      }
      const target = infoTarget(item);
      return buildDashboardCard(target.kind, target.id, {
        title: safeText(item.title || "Movie"),
        subtitle: "Movie release",
        tertiary,
        image: imageForItem(item),
        pct: percentForItem(item),
        extraClass: expandableClass(hidden),
        renderKey: renderKey || `dashboard:event:${target.kind}:${safeText(target.id)}`,
        facts: [
          factChipHtml("Movie"),
          item.network_name ? factChipHtml(item.network_name) : ""
        ]
      });
    };

    const buildDateColumns = (entries, { descending = false } = {}) => {
      const deduped = dedupeItems(entries, entry => `${safeText(entry?.dateKey || "")}|${itemRenderKey(entry?.item || {}, safeText(entry?.dateKey || ""))}`);
      const dateKeys = Array.from(new Set(deduped.map(e => e.dateKey)));
      const ordered = descending ? dateKeys.sort((a, b) => b.localeCompare(a)) : dateKeys.sort((a, b) => a.localeCompare(b));
      return ordered.slice(0, 7).map(dateKey => {
        const dayEntries = deduped.filter(e => e.dateKey === dateKey);
        const visibleLimit = 4;
        return `
        <div class="dashcol dashcol--clean">
          <div class="dashcolhead">${escHtml(formatDateShort(dateKey))}</div>
          <div class="dashcolstack" data-more-id="dashboard-${escHtml(dateKey)}">
            ${dayEntries.map(({ item }, index) => {
              const rowKey = itemRenderKey(item, dateKey);
              const section = descending ? "recent" : "upcoming";
              return eventCard(item, "", index >= visibleLimit, `dashboard:${section}:${dateKey}:${rowKey}`);
            }).join("") || `<div class="muted">No items</div>`}
            ${renderMoreButton(Math.max(0, dayEntries.length - visibleLimit), `dashboard-${dateKey}`)}
          </div>
        </div>
      `; }).join("");
    };
    scheduleCols.innerHTML = buildDateColumns(events) || `<div class="muted">No upcoming schedule.</div>`;
    const lastWeekMeta = $("#dashLastWeekMeta");
    if (lastWeekMeta) {
      if (pastEvents.length) {
        const sortedPast = pastEvents.slice().sort((a, b) => b.dateKey.localeCompare(a.dateKey));
        const newest = sortedPast[0]?.dateKey ? formatDateShort(sortedPast[0].dateKey) : "";
        const oldest = sortedPast[sortedPast.length - 1]?.dateKey ? formatDateShort(sortedPast[sortedPast.length - 1].dateKey) : "";
        lastWeekMeta.textContent = oldest && newest ? `${oldest} - ${newest}` : "Recently released";
      } else {
        lastWeekMeta.textContent = "No recent items";
      }
    }
    lastWeekCols.innerHTML = buildDateColumns(pastEvents, { descending: true }) || `<div class="muted">No recent schedule.</div>`;

    const uniqueWatchlist = dedupeItems(ensureWatchlist(), entry => `${safeText(entry?.kind || entry?.type || "watchlist")}:${safeText(entry?.tmdb_id ?? entry?.id ?? entry?.title ?? "")}`).slice(0, 8);
    const watchMeta = $("#dashWatchMeta");
    if (watchMeta) watchMeta.textContent = uniqueWatchlist.length ? `${uniqueWatchlist.length} tracked items` : "No items";
    watchlistEl.innerHTML = uniqueWatchlist.length ? uniqueWatchlist.map(entry => {
      const id = String(entry?.tmdb_id ?? "");
      const show = showMap.get(id);
      const movie = movieMap.get(id);
      const media = show || movie || entry;
      return buildDashboardCard(show ? "show" : "movie", media?.tmdb_id, {
        title: safeText(entry?.title || show?.title || show?.name || movie?.title || "Untitled"),
        subtitle: safeText(entry?.watch_status || "watchlist"),
        image: normalizeImageSrc(pickImage(media, "poster_local", "poster_path", "backdrop_local", "backdrop_path")),
        badgeHtml: "",
        pct: percentForItem(media),
        renderKey: `dashboard:watchlist:${show ? "show" : "movie"}:${safeText(media?.tmdb_id ?? id)}`,
        facts: [factChipHtml(show ? "Show" : "Movie"), factChipHtml("Watchlist", "tone-accent")]
      });
    }).join("") : `<div class="muted">No watchlist items.</div>`;

    const shows = dedupeItems((state.data?.shows || []).slice().sort((a, b) => (Number(b?.popularity) || 0) - (Number(a?.popularity) || 0)), show => `show:${safeText(show?.tmdb_id ?? show?.id ?? show?.title ?? show?.name ?? "")}`).slice(0, 8);
    showRecs.innerHTML = shows.length ? shows.map(show => buildDashboardCard("show", show?.tmdb_id, {
      title: safeText(show?.title || show?.name || "Show"),
      subtitle: truncateText(show?.overview || "", 84),
      tertiary: show?.first_air_date ? formatDateShort(show.first_air_date) : "",
      image: normalizeImageSrc(pickImage(show, "poster_local", "poster_path", "backdrop_local", "backdrop_path")),
      badgeHtml: "",
      pct: percentForItem(show),
      renderKey: `dashboard:recommendation:show:${safeText(show?.tmdb_id ?? show?.id ?? show?.title ?? show?.name ?? "")}`,
      facts: [factChipHtml("Discover"), (show?.genres || []).length ? factChipHtml(show.genres[0]?.name || "") : ""]
    })).join("") : `<div class="muted">No recommendations.</div>`;

    const movies = dedupeItems((state.data?.movies || []).slice().sort((a, b) => (Number(b?.popularity) || 0) - (Number(a?.popularity) || 0)), movie => `movie:${safeText(movie?.tmdb_id ?? movie?.id ?? movie?.title ?? "")}`).slice(0, 8);
    movieRecs.innerHTML = movies.length ? movies.map(movie => buildDashboardCard("movie", movie?.tmdb_id, {
      title: safeText(movie?.title || "Movie"),
      subtitle: truncateText(movie?.overview || "", 84),
      tertiary: movie?.release_date ? formatDateShort(movie.release_date) : "",
      image: normalizeImageSrc(pickImage(movie, "poster_local", "poster_path", "backdrop_local", "backdrop_path")),
      badgeHtml: "",
      pct: percentForItem(movie),
      renderKey: `dashboard:recommendation:movie:${safeText(movie?.tmdb_id ?? movie?.id ?? movie?.title ?? "")}`,
      facts: [factChipHtml("Movie"), (movie?.genres || []).length ? factChipHtml(movie.genres[0]?.name || "") : ""]
    })).join("") : `<div class="muted">No recommendations.</div>`;

    [scheduleCols, lastWeekCols, watchlistEl, showRecs, movieRecs].forEach(root => {
      wireActionMenus(root);
      wireIconStripActions(root, renderDashboard);
      wireWatchSourceButtons(root);
      if (window.MyTVHubWatchState && typeof window.MyTVHubWatchState.refresh === "function") {
        window.MyTVHubWatchState.refresh(root);
      }
      bindMoreToggles(root);
      $$(".episode-row[data-show]", root).forEach(card => card.addEventListener("click", (e) => {
        if (e.target.closest(".actionbar")) return;
        gotoShow(parseInt(card.getAttribute("data-show") || "0", 10));
      }));
    });
    applyStickySectionHeads($("#panel-dashboard"));
    $$("[data-dash-lastweek-nav]").forEach(btn => btn.onclick = () => {
      const action = btn.getAttribute("data-dash-lastweek-nav") || "";
      const current = Math.max(0, Number(state.dashboard?.lastWeekOffsetWeeks) || 0);
      if (action === "back") state.dashboard.lastWeekOffsetWeeks = current + 1;
      if (action === "jump-back") state.dashboard.lastWeekOffsetWeeks = current + 4;
      if (action === "forward") state.dashboard.lastWeekOffsetWeeks = Math.max(0, current - 1);
      if (action === "jump-forward") state.dashboard.lastWeekOffsetWeeks = Math.max(0, current - 4);
      renderDashboard();
    });
    $$("[data-dash-lastweek-nav='forward'], [data-dash-lastweek-nav='jump-forward']").forEach(btn => {
      btn.disabled = lastWeekOffset === 0;
    });
  }

  function showCardHtml(show, eye){
    const id = Number(show?.tmdb_id) || 0;
    const title = safeText(show?.title || show?.name || "(Untitled)");
    return buildMediaCardShell("show", id, {
      title,
      image: pickImage(show, "poster_local", "poster_path"),
      badgeHtml: "",
      actionBar: buildActionBarHtml("show", id, {
        title,
        compact: true,
        pct: (() => {
          let v = progressPercent(show);
          if (v == null){
            const raw = Number(show?.vote_average ?? show?.rating ?? 0);
            if (Number.isFinite(raw) && raw > 0) v = Math.round(raw <= 10 ? raw * 10 : raw);
          }
          return v;
        })(),
        favoriteActive: getWatchlistSet().has(String(id)),
        watchedActive: isShowWatched(show),
        showWatchedAction: true,
        showStatusAction: true,
        watchedToggleHtml: watchToggleHtml("show", { "data-watch-show": id }, isShowWatched(show)),
        available: isShowAvailable(show)
      }),
      meta: yearFromDate(show?.first_air_date),
      eyeClass: eye?.fade ? " faded" : ""
    });
  }

  function movieCardHtml(movie, eye){
    const id = Number(movie?.tmdb_id) || 0;
    const title = safeText(movie?.title || "(Untitled)");
    const releaseDate = safeText(movie?.release_date || "").trim();
    const runtime = Number(movie?.runtime);
    return buildMediaCardShell("movie", id, {
      title,
      image: pickImage(movie, "poster_local", "poster_path"),
      badgeHtml: "",
      actionBar: buildActionBarHtml("movie", id, {
        title,
        compact: true,
        pct: (() => {
          let v = progressPercent(movie);
          if (v == null){
            const raw = Number(movie?.vote_average ?? movie?.rating ?? 0);
            if (Number.isFinite(raw) && raw > 0) v = Math.round(raw <= 10 ? raw * 10 : raw);
          }
          return v;
        })(),
        favoriteActive: getWatchlistSet().has(String(id)),
        watchedActive: isMovieWatched(movie),
        showWatchedAction: true,
        showStatusAction: true,
        watchedToggleHtml: watchToggleHtml("movie", { "data-watch-movie": id }, isMovieWatched(movie)),
        popcornAttrs: hasDirectWatchSources(movie) ? { "data-id": id } : null,
        popcornKind: "movie",
        availabilityStatus: availabilityStatusOf(movie),
        available: isMovieAvailable(movie)
      }),
      meta: releaseDate ? formatDateShort(releaseDate) : yearFromDate(movie?.release_date),
      submeta: Number.isFinite(runtime) && runtime > 0 ? `${runtime} min` : "",
      eyeClass: eye?.fade ? " faded" : ""
    });
  }

  function renderDiscover(){
    const showsRoot = $("#discoverShowsGrid");
    const moviesRoot = $("#discoverMoviesGrid");
    const panel = $("#panel-discover");
    if (!showsRoot || !moviesRoot || !panel) return;

    const registry = state.discoverRegistry && typeof state.discoverRegistry === "object" ? state.discoverRegistry : { meta: { status: "config-needed" }, sources: [] };
    const sources = Array.isArray(registry.sources) ? registry.sources : [];
    const localShowIds = new Set((state.data?.shows || []).map(show => safeText(show?.tmdb_id ?? show?.id ?? "")).filter(Boolean));
    const localMovieIds = new Set((state.data?.movies || []).map(movie => safeText(movie?.tmdb_id ?? movie?.id ?? "")).filter(Boolean));
    const localWatchState = readLocalWatchState();
    const localStateKeySet = new Set(Object.keys(localWatchState));
    const sourceItems = (source) => {
      const items = [];
      if (Array.isArray(source?.items)) items.push(...source.items);
      if (Array.isArray(source?.results)) items.push(...source.results);
      if (Array.isArray(source?.shows)) items.push(...source.shows.map(item => ({ ...item, kind: item?.kind || "show" })));
      if (Array.isArray(source?.movies)) items.push(...source.movies.map(item => ({ ...item, kind: item?.kind || "movie" })));
      return items.filter(item => item && typeof item === "object");
    };
    const itemId = (item) => safeText(item?.tmdb_id ?? item?.id ?? item?.trakt_id ?? "");
    const itemKind = (item) => safeText(item?.kind || item?.media_type || item?.type || "");
    const isExcluded = (item) => {
      const id = itemId(item);
      const kind = itemKind(item);
      if (!id) return true;
      if (kind === "movie" && localMovieIds.has(id)) return true;
      if ((kind === "show" || kind === "tv" || !kind) && localShowIds.has(id)) return true;
      if (Array.from(localStateKeySet).some(key => key.includes(`:movie:${id}`) || key.includes(`:show:${id}`))) return true;
      if (Array.from(localStateKeySet).some(key => key.includes(`:episode:${id}:`))) return true;
      return false;
    };
    const activeSources = sources.filter(source => source && source.enabled !== false);
    const externalShows = [];
    const externalMovies = [];
    for (const source of activeSources){
      for (const item of sourceItems(source)){
        if (isExcluded(item)) continue;
        if (safeText(item.kind || item.media_type || item.type).toLowerCase() === "movie") externalMovies.push(item);
        else externalShows.push({ ...item, kind: "show" });
      }
    }
    externalShows.sort((a, b) => (Number(b?.popularity) || 0) - (Number(a?.popularity) || 0));
    externalMovies.sort((a, b) => (Number(b?.popularity) || 0) - (Number(a?.popularity) || 0));

    const registryHtml = `
      <section class="dashblock discover-registry">
        <div class="dashhead dashhead--compact">
          <span class="muted">Discovery feed registry</span>
          <span class="muted">${activeSources.length ? `${activeSources.length} configured source${activeSources.length === 1 ? "" : "s"}` : "config-needed"}</span>
        </div>
        <div class="discover-registry__body">
          <table class="discover-registry__table">
            <thead>
              <tr>
                <th>Source name</th>
                <th>Type</th>
                <th>Normalization</th>
                <th>Cadence</th>
                <th>ID fields</th>
                <th>Exclusions</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${sources.length ? sources.map(source => `
                <tr>
                  <td>${escHtml(safeText(source.source_name || source.name || "Unnamed source"))}</td>
                  <td>${escHtml(safeText(source.source_type || source.type || "unknown"))}</td>
                  <td><code>${escHtml(safeText(source.normalization_path || "discover.sources[]"))}</code></td>
                  <td>${escHtml(safeText(source.refresh_cadence || "manual"))}</td>
                  <td><code>${escHtml(Array.isArray(source.id_fields) ? source.id_fields.join(", ") : safeText(source.id_fields || "tmdb_id"))}</code></td>
                  <td>${escHtml(Array.isArray(source.exclusion_rules) ? source.exclusion_rules.join(", ") : safeText(source.exclusion_rules || "watched, watch_list, favourite, locally_known"))}</td>
                  <td>${source.enabled === false ? "configured / disabled" : "enabled"}</td>
                </tr>
              `).join("") : `<tr><td colspan="7" class="inline-empty">No discovery source is configured yet.</td></tr>`}
            </tbody>
          </table>
        </div>
      </section>
    `;
    const emptyState = `
      <section class="dashblock discover-empty">
        <div class="dashhead dashhead--compact">
          <span class="muted">Discover</span>
          <span class="muted">config-needed</span>
        </div>
        <div class="discover-empty__copy">
          <p>No external discovery feed is configured yet.</p>
          <p>Register a non-local Trakt-style source, then normalization can fill this surface with suggestions that are not already watched, watching, watchlisted, or locally known.</p>
        </div>
      </section>
    `;

    if (!activeSources.length || (!externalShows.length && !externalMovies.length)){
      showsRoot.innerHTML = `<div class="discover-column">${emptyState}${registryHtml}</div>`;
      moviesRoot.innerHTML = `<div class="discover-column">${emptyState}</div>`;
    } else {
      showsRoot.innerHTML = externalShows.slice(0, 12).map(show => showCardHtml(show, { fade: false })).join("") || emptyState;
      moviesRoot.innerHTML = externalMovies.slice(0, 12).map(movie => movieCardHtml(movie, { fade: false })).join("") || emptyState;
    }

    [showsRoot, moviesRoot, panel].forEach(root => {
      if (!root) return;
      applyStickySectionHeads(root);
      wireActionMenus(root);
      wireIconStripActions(root, renderDiscover);
      wireWatchSourceButtons(root);
      if (window.MyTVHubWatchState && typeof window.MyTVHubWatchState.refresh === "function") {
        window.MyTVHubWatchState.refresh(root);
      }
      $$("[data-show-open]", root).forEach(el => el.addEventListener("click", () => gotoShow(parseInt(el.getAttribute("data-show-open") || "0", 10))));
      $$("[data-movie-open]", root).forEach(el => el.addEventListener("click", () => openMovieModal(parseInt(el.getAttribute("data-movie-open") || "0", 10))));
    });
  }

  function readLocalWatchState(){
    return window.MyTVHubWatchState && typeof window.MyTVHubWatchState.load === "function"
      ? window.MyTVHubWatchState.load()
      : {};
  }

  function syncQueueCount(){
    return readWatchSyncQueue().length;
  }

  function readWatchSyncQueue(){
    const fileQueue = Array.isArray(state.watchStateQueue?.items) ? state.watchStateQueue.items : [];
    if (window.MyTVHubWatchState && typeof window.MyTVHubWatchState.loadQueue === "function") {
      const localQueue = window.MyTVHubWatchState.loadQueue();
      const seen = new Set();
      return [...localQueue, ...fileQueue].filter(item => {
        const key = safeText(item?.id || item?.item_key || item?.key || item?.state_key || item);
        if (!key || seen.has(`${key}:${safeText(item?.state_type)}`)) return false;
        seen.add(`${key}:${safeText(item?.state_type)}`);
        return true;
      });
    }
    try {
      const queue = JSON.parse(localStorage.getItem("mytv_watch_sync_queue_v1") || "[]");
      const localQueue = Array.isArray(queue) ? queue : (Array.isArray(queue?.items) ? queue.items : []);
      return [...localQueue, ...fileQueue];
    } catch (_) {
      return fileQueue;
    }
  }

  function stateRecordValue(record, type){
    if (window.MyTVHubWatchState && typeof window.MyTVHubWatchState.valueOf === "function") {
      return window.MyTVHubWatchState.valueOf(record, type);
    }
    const cleanType = safeText(type);
    if (record && typeof record === "object" && !Array.isArray(record)){
      const value = safeText(record.new_value).toLowerCase();
      if (cleanType === "watched_status") return ["unwatched","partial","watched"].includes(value) ? value : "unwatched";
      return value === "on" ? "on" : "off";
    }
    if (cleanType === "watched_status"){
      if (record === true) return "watched";
      const text = safeText(record).toLowerCase();
      return ["unwatched","partial","watched"].includes(text) ? text : "unwatched";
    }
    return record ? "on" : "off";
  }

  function canonicalStateKey(type, context = {}){
    const ctx = context && typeof context === "object" ? context : {};
    if (window.MyTVHubWatchState && typeof window.MyTVHubWatchState.contextKey === "function"){
      return window.MyTVHubWatchState.contextKey(type, ctx);
    }
    return "";
  }

  function canonicalStateValue(type, context = {}, fallback = ""){
    const key = canonicalStateKey(type, context);
    const data = readLocalWatchState();
    if (key && Object.prototype.hasOwnProperty.call(data, key)){
      return stateRecordValue(data[key], type);
    }
    if (type === "watched_status") return fallback === true ? "watched" : (["unwatched","partial","watched"].includes(safeText(fallback).toLowerCase()) ? safeText(fallback).toLowerCase() : "unwatched");
    return fallback === true || safeText(fallback).toLowerCase() === "on" ? "on" : "off";
  }

  function canonicalStateContext(kind, id, options = {}){
    const statusContext = options.statusContext || {};
    const tmdbId = safeText(options.tmdbId ?? options.tmdb_id ?? (kind === "episode" ? "" : id));
    return {
      kind,
      id: safeText(id),
      tmdb_id: tmdbId,
      trakt_id: safeText(options.traktId ?? options.trakt_id ?? ""),
      imdb_id: safeText(options.imdbId ?? options.imdb_id ?? ""),
      tvdb_id: safeText(options.tvdbId ?? options.tvdb_id ?? ""),
      showId: safeText(statusContext.showId ?? options.showId ?? options.show_id ?? ""),
      seasonNumber: safeText(statusContext.seasonNumber ?? options.seasonNumber ?? options.season_number ?? ""),
      episodeNumber: safeText(statusContext.episodeNumber ?? options.episodeNumber ?? options.episode_number ?? ""),
      release_status: safeText(options.availabilityStatus || (options.available === false ? "unreleased" : ""))
    };
  }

  function canonicalWatchListActive(kind, id, fallback = false){
    return canonicalStateValue("watch_list", { kind, id, tmdb_id: id, showId: kind === "show" ? id : "" }, fallback ? "on" : "off") === "on";
  }

  function canonicalFavouriteActive(kind, id, fallback = false){
    return canonicalStateValue("favourite", { kind, id, tmdb_id: id, showId: kind === "show" ? id : "" }, fallback ? "on" : "off") === "on";
  }

  function traktAuthAvailable(){
    return !!state.cfg?.trakt_sync?.enabled;
  }

  function renderWatchStateManagerHtml(){
    const localState = readLocalWatchState();
    const keys = Object.keys(localState);
    const typeCounts = keys.reduce((acc, key) => {
      if (key.startsWith("watched_status:")) acc.watched_status += 1;
      else if (key.startsWith("watch_list:")) acc.watch_list += 1;
      else if (key.startsWith("favourite:")) acc.favourite += 1;
      return acc;
    }, { watched_status: 0, watch_list: 0, favourite: 0 });
    const syncQueue = readWatchSyncQueue();
    const queuedKeys = new Set(syncQueue.map(item => safeText(item?.item_key || item?.key || item?.state_key || item?.id || item)).filter(Boolean));
    const releaseStatus = (dateText, fallback = "") => {
      const raw = safeText(dateText || "");
      if (!raw) return safeText(fallback || "unknown");
      const releaseDate = new Date(raw);
      if (Number.isNaN(releaseDate.getTime())) return safeText(fallback || raw);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      releaseDate.setHours(0, 0, 0, 0);
      return releaseDate > today ? "unreleased" : "released";
    };
    const stateKey = (type, row) => {
      if (!row || !row.kind) return "";
      if (row.kind === "episode") return `${type}:episode:${row.showId}:${row.seasonNumber}:${row.episodeNumber}`;
      if (row.kind === "season") return `${type}:season:${row.showId}:${row.seasonNumber}`;
      if (row.kind === "movie") return `${type}:movie:${row.tmdbId}`;
      if (row.kind === "show") return `${type}:show:${row.tmdbId}`;
      return "";
    };
    const stateValue = (type, row) => {
      const key = stateKey(type, row);
      const raw = key ? localState[key] : "";
      return stateRecordValue(raw, type);
    };
    const rowRecords = row => ["watch_list","watched_status","favourite"]
      .map(type => localState[stateKey(type, row)])
      .filter(record => record && typeof record === "object" && !Array.isArray(record));
    const rowHasTraktId = row => !!safeText(row?.item?.trakt_id || row?.item?.trakt || row?.traktId || "");
    const rowIssue = row => {
      if (!row.tmdbId && row.kind !== "season" && row.kind !== "episode") return "missing tmdb_id";
      if (row.kind === "episode" && (!row.showId || !row.seasonNumber || !row.episodeNumber)) return "missing episode key";
      if ((row.kind === "movie" || row.kind === "episode") && row.release === "unreleased") return "locked until release";
      return "";
    };
    const computedStatus = row => {
      const records = rowRecords(row);
      const issue = rowIssue(row);
      const recordIssue = records.find(record => record.validation_status && record.validation_status !== "ok");
      if (issue || recordIssue) return recordIssue?.sync_status || "validation_issue";
      if (["watch_list","watched_status","favourite"].some(type => queuedKeys.has(stateKey(type, row)))) return "queued";
      const explicit = records.map(record => safeText(record.sync_status)).find(Boolean);
      if (explicit) return explicit;
      if (!traktAuthAvailable()) return "auth_required";
      if (!rowHasTraktId(row) && (row.kind === "movie" || row.kind === "show")) return "missing_id";
      return records.length ? "local_only" : "synced";
    };
    const computedMismatch = row => rowRecords(row).some(record => safeText(record.sync_status) === "mismatch");
    const computedQueued = row => ["watch_list","watched_status","favourite"].some(type => queuedKeys.has(stateKey(type, row)));
    const computedValidationIssue = row => {
      const issue = rowIssue(row);
      const recordIssue = rowRecords(row).find(record => record.validation_status && record.validation_status !== "ok");
      return issue || safeText(recordIssue?.sync_error || recordIssue?.validation_status || "");
    };
    const shows = (Array.isArray(state.data?.shows) ? state.data.shows : []).filter(item => item?.tmdb_id);
    const movies = (Array.isArray(state.data?.movies) ? state.data.movies : []).filter(item => item?.tmdb_id);
    const seasonMap = new Map();
    const showEpisodesMap = new Map();
    const rows = [];
    shows.forEach(show => {
      const showId = safeText(show?.tmdb_id ?? show?.id ?? "");
      const seasons = Array.isArray(show?.seasons) ? show.seasons : [];
      rows.push({
        kind:"show",
        level:0,
        title:safeText(show?.title || show?.name || "Show"),
        release: releaseStatus(show?.first_air_date, show?.status),
        ids:`tmdb:${showId}${show?.trakt_id ? ` / trakt:${safeText(show.trakt_id)}` : ""}`,
        tmdbId:showId,
        traktId:safeText(show?.trakt_id || ""),
        showId,
        item:show
      });
      const showEpisodeRows = [];
      seasons.forEach(season => {
        const seasonNumber = Number(season?.season_number);
        if (!Number.isFinite(seasonNumber)) return;
        const seasonKey = `${showId}:${seasonNumber}`;
        const episodes = Array.isArray(season?.episodes) ? season.episodes : [];
        seasonMap.set(seasonKey, episodes);
        showEpisodeRows.push(...episodes);
        rows.push({
          kind:"season",
          level:1,
          title:safeText(season?.name || `Season ${seasonNumber}`),
          release: releaseStatus(season?.air_date, ""),
          ids:`show:${showId} / S${seasonNumber}`,
          tmdbId:showId,
          traktId:safeText(show?.trakt_id || ""),
          showId,
          seasonNumber,
          item:season
        });
        episodes.forEach(episode => {
          const episodeNumber = Number(episode?.episode_number);
          if (!Number.isFinite(episodeNumber)) return;
          rows.push({
            kind:"episode",
            level:2,
            title:safeText(episode?.name || `Episode ${episodeNumber}`),
            release: releaseStatus(episode?.air_date, ""),
            ids:`show:${showId} / S${seasonNumber}E${episodeNumber}${episode?.id ? ` / tmdb:${safeText(episode.id)}` : ""}`,
            tmdbId:safeText(episode?.id || ""),
            traktId:safeText(episode?.trakt_id || ""),
            showId,
            seasonNumber,
            episodeNumber,
            item:episode
          });
        });
      });
      showEpisodesMap.set(showId, showEpisodeRows);
    });
    movies.forEach(movie => {
      const movieId = safeText(movie?.tmdb_id ?? movie?.id ?? "");
      rows.push({
        kind:"movie",
        level:0,
        title:safeText(movie?.title || "Movie"),
        release: releaseStatus(movie?.release_date, movie?.status),
        ids:`tmdb:${movieId}${movie?.trakt_id ? ` / trakt:${safeText(movie.trakt_id)}` : ""}`,
        tmdbId:movieId,
        traktId:safeText(movie?.trakt_id || ""),
        item:movie
      });
    });
    const unmatched = keys.filter(key => !/^(watched_status|watch_list|favourite):(movie|show|season|episode):/.test(key)).length;
    const manageState = state.manageWatchState || (state.manageWatchState = { search: "", type: "all", pageSize: 50, sortKey: "title", sortDir: "asc" });
    const searchText = safeText(manageState.search).toLowerCase();
    const typeFilter = safeText(manageState.type || "all");
    const sortKey = safeText(manageState.sortKey || "title");
    const sortDir = safeText(manageState.sortDir || "asc") === "desc" ? "desc" : "asc";
    const pageSize = Math.max(1, Number(manageState.pageSize) || 50);
    const derivedWatchStateText = row => {
      if (row.kind === "movie" || row.kind === "episode") return stateValue("watched_status", row);
      const episodes = row.kind === "season" ? (seasonMap.get(`${row.showId}:${row.seasonNumber}`) || []) : (showEpisodesMap.get(row.showId) || []);
      const eligible = episodes.filter(episode => releaseStatus(episode?.air_date, "") === "released");
      const values = eligible.map(episode => {
        const epRow = {
          kind:"episode",
          showId: row.showId,
          seasonNumber: row.kind === "season" ? row.seasonNumber : Number(episode?.season_number || episode?.season || 0),
          episodeNumber: Number(episode?.episode_number || episode?.number || 0),
          release: releaseStatus(episode?.air_date, "")
        };
        return stateValue("watched_status", epRow);
      });
      return !eligible.length ? "unwatched" : values.every(v => v === "watched") ? "watched" : values.some(v => v !== "unwatched") ? "partial" : "unwatched";
    };
    const sortValue = (row, key) => {
      if (key === "kind" || key === "type") return row.kind;
      if (key === "release") return row.release;
      if (key === "watch_list") return stateValue("watch_list", row);
      if (key === "watched_status") return row.kind === "movie" || row.kind === "episode" ? stateValue("watched_status", row) : safeText(derivedWatchStateText(row));
      if (key === "favourite") return stateValue("favourite", row);
      if (key === "trakt") return computedStatus(row);
      if (key === "mismatch") return computedMismatch(row) ? "true" : "false";
      if (key === "queued") return computedQueued(row) ? "true" : "false";
      if (key === "validation") return computedValidationIssue(row);
      return row.title;
    };
    const sortRows = inputRows => inputRows.slice().sort((a, b) => {
      const av = safeText(sortValue(a, sortKey)).toLowerCase();
      const bv = safeText(sortValue(b, sortKey)).toLowerCase();
      const result = av.localeCompare(bv, undefined, { numeric: true, sensitivity: "base" });
      return sortDir === "desc" ? -result : result;
    });
    const filteredRows = sortRows(rows.filter(row => {
      if (typeFilter !== "all" && row.kind !== typeFilter) return false;
      if (!searchText) return true;
      return [row.title, row.kind, row.ids, row.release].some(value => safeText(value).toLowerCase().includes(searchText));
    }));
    const sortButton = (key, label) => {
      const active = sortKey === key;
      return `<button class="watch-state-sort" type="button" data-manage-watch-sort="${escHtml(key)}" aria-sort="${active ? sortDir : "none"}">${escHtml(label)}${active ? ` ${sortDir === "desc" ? "↓" : "↑"}` : ""}</button>`;
    };
    const watchedButtons = (row, lock = false) => {
      const key = stateKey("watched_status", row);
      const value = stateValue("watched_status", row);
      const disabled = lock || row.release === "unreleased";
      return `
        <div class="watch-state-tristate${disabled ? " is-locked" : ""}" role="group" aria-label="watched_status">
          ${["unwatched","partial","watched"].map(option => `<button class="watch-state-tristate__option" type="button" data-manage-watch-key="${escHtml(key)}" data-kind="${escHtml(row.kind)}" data-tmdb-id="${escHtml(row.tmdbId)}" data-trakt-id="${escHtml(row.traktId || "")}" data-show="${escHtml(row.showId || "")}" data-season="${escHtml(row.seasonNumber || "")}" data-episode="${escHtml(row.episodeNumber || "")}" data-release-status="${escHtml(row.release)}" data-manage-watch-value="${option}" aria-pressed="${value === option ? "true" : "false"}" title="${disabled ? "Derived from released children" : option}" ${disabled ? "disabled aria-disabled=\"true\"" : ""}>${option === "unwatched" ? "0" : option === "partial" ? "1/2" : "✓"}</button>`).join("")}
        </div>
      `;
    };
    const derivedWatchState = row => {
      if (row.kind === "movie" || row.kind === "episode") return watchedButtons(row, row.release === "unreleased");
      if (row.kind === "season") {
        const derived = derivedWatchStateText(row);
        return `<div class="watch-state-derived" title="Derived from released child episodes"><span class="watch-state-derived__value">${escHtml(derived)}</span><span class="watch-state-derived__note">derived</span></div>`;
      }
      if (row.kind === "show") {
        const derived = derivedWatchStateText(row);
        return `<div class="watch-state-derived" title="Derived from released child seasons and episodes"><span class="watch-state-derived__value">${escHtml(derived)}</span><span class="watch-state-derived__note">derived</span></div>`;
      }
      return watchedButtons(row, false);
    };
    const toggleCell = (type, row, label) => {
      const key = stateKey(type, row);
      const active = stateRecordValue(localState[key], type) === "on";
      return `<button class="watch-state-toggle" type="button" data-manage-watch-key="${escHtml(key)}" data-kind="${escHtml(row.kind)}" data-tmdb-id="${escHtml(row.tmdbId)}" data-trakt-id="${escHtml(row.traktId || "")}" data-show="${escHtml(row.showId || "")}" data-season="${escHtml(row.seasonNumber || "")}" data-episode="${escHtml(row.episodeNumber || "")}" data-release-status="${escHtml(row.release)}" aria-label="${escHtml(label)}" title="${escHtml(label)}" aria-pressed="${active ? "true" : "false"}">${active ? "✓" : ""}</button>`;
    };
    const pageCount = Math.max(1, Math.ceil(filteredRows.length / pageSize));
    const currentPage = Math.min(Math.max(0, Number(state.manageWatchStatePage) || 0), pageCount - 1);
    state.manageWatchStatePage = currentPage;
    const pageRows = filteredRows.slice(currentPage * pageSize, currentPage * pageSize + pageSize);
    const pageHtml = pageRows.map(row => {
      const watchKey = stateKey("watch_list", row);
      const favKey = stateKey("favourite", row);
      const watchedKey = stateKey("watched_status", row);
      const queueHit = queuedKeys.has(watchKey) || queuedKeys.has(favKey) || queuedKeys.has(watchedKey);
      const issue = computedValidationIssue(row);
      return `
        <tr class="watch-state-matrix__row" data-watch-state-row-key="${escHtml(watchedKey)}" data-watch-list-row-key="${escHtml(watchKey)}" data-favourite-row-key="${escHtml(favKey)}" data-kind="${escHtml(row.kind)}" data-level="${escHtml(row.level)}" data-release="${escHtml(row.release)}" data-render-key="${escHtml(`${row.kind}:${row.tmdbId || row.showId || ""}:${row.seasonNumber || ""}:${row.episodeNumber || ""}`)}">
          <th scope="row" class="watch-state-matrix__title watch-state-matrix__title--level-${escHtml(row.level)}"><span>${escHtml(row.title)}</span><small>${escHtml(row.kind)}</small></th>
          <td>${escHtml(row.release)}</td>
          <td><code>${escHtml(row.ids)}</code></td>
          <td>${toggleCell("watch_list", row, "Toggle watch_list")}</td>
          <td>${derivedWatchState(row)}</td>
          <td>${toggleCell("favourite", row, "Toggle favourite")}</td>
          <td data-computed-status="trakt">${escHtml(computedStatus(row))}</td>
          <td data-computed-status="mismatch">${computedMismatch(row) ? "true" : "false"}</td>
          <td data-computed-status="queued">${queueHit || computedQueued(row) ? "true" : "false"}</td>
          <td>${issue ? escHtml(issue) : ""}</td>
        </tr>
      `;
    }).join("");
    const pager = `
      <div class="watch-state-pager" aria-label="Watch state pagination">
        <button class="calbtn" type="button" data-manage-watch-page="first" ${currentPage === 0 ? "disabled" : ""}>First</button>
        <button class="calbtn" type="button" data-manage-watch-page="prev" ${currentPage === 0 ? "disabled" : ""}>Prev</button>
        <span class="watch-state-pager__label">Page ${currentPage + 1} / ${pageCount} • ${pageRows.length} / ${filteredRows.length} rows shown</span>
        <button class="calbtn" type="button" data-manage-watch-page="next" ${currentPage >= pageCount - 1 ? "disabled" : ""}>Next</button>
        <button class="calbtn" type="button" data-manage-watch-page="last" ${currentPage >= pageCount - 1 ? "disabled" : ""}>Last</button>
      </div>
    `;
    return `
      <section class="watch-state-manager" id="manageWatchState" aria-label="Manage watch state" data-watch-state-total-rows="${filteredRows.length}" data-watch-state-page-size="${pageSize}">
        <div class="dashhead">
          <h2>Manage Watch State</h2>
          <span class="muted">Local first, Trakt ready</span>
        </div>
        <div class="config-quicklinks" aria-label="Watch state status">
          <span class="pill">watched_status ${typeCounts.watched_status}</span>
          <span class="pill">watch_list ${typeCounts.watch_list}</span>
          <span class="pill">favourite ${typeCounts.favourite}</span>
          <span class="pill">Trakt mapping scaffolded</span>
          <span class="pill">unmatched IDs ${unmatched}</span>
          <span class="pill">sync queue ${syncQueueCount()}</span>
        </div>
        <div class="watch-state-controls" aria-label="Manage Watch State controls">
          <label class="watch-state-control"><span>Search</span><input class="input" type="search" data-manage-watch-search value="${escHtml(manageState.search)}" placeholder="Search title, type, ID, release"></label>
          <label class="watch-state-control"><span>Type</span><select class="input" data-manage-watch-type>
            ${["all","show","season","episode","movie"].map(value => `<option value="${value}"${typeFilter === value ? " selected" : ""}>${value === "all" ? "All" : value}</option>`).join("")}
          </select></label>
          <label class="watch-state-control"><span>Rows</span><select class="input" data-manage-watch-page-size>
            ${[10,25,50,100,250].map(value => `<option value="${value}"${pageSize === value ? " selected" : ""}>${value}</option>`).join("")}
          </select></label>
        </div>
        ${pager}
        <div class="watch-state-matrix-wrap">
          <table class="watch-state-matrix">
            <thead>
              <tr>
                <th scope="col">${sortButton("title", "Title / hierarchy")}</th>
                <th scope="col">${sortButton("release", "Release status")}</th>
                <th scope="col">IDs</th>
                <th scope="col">${sortButton("watch_list", "watch_list")}</th>
                <th scope="col">${sortButton("watched_status", "watched_status")}</th>
                <th scope="col">${sortButton("favourite", "favourite")}</th>
                <th scope="col">${sortButton("trakt", "Trakt status")}</th>
                <th scope="col">${sortButton("mismatch", "Mismatch")}</th>
                <th scope="col">${sortButton("queued", "Queued")}</th>
                <th scope="col">${sortButton("validation", "Validation issue")}</th>
              </tr>
            </thead>
            <tbody>${pageHtml || `<tr><td colspan="10" class="inline-empty">No catalog items available for local watch-state management.</td></tr>`}</tbody>
          </table>
        </div>
        ${pager}
      </section>
    `;
  }

  function bindWatchStateManager(root){
    if (!root) return;
    const manageState = state.manageWatchState || (state.manageWatchState = { search: "", type: "all", pageSize: 50, sortKey: "title", sortDir: "asc" });
    const searchInput = root.querySelector("[data-manage-watch-search]");
    if (searchInput){
      searchInput.addEventListener("input", () => {
        manageState.search = searchInput.value || "";
        state.manageWatchStatePage = 0;
        renderManageWatchState();
      });
    }
    const typeSelect = root.querySelector("[data-manage-watch-type]");
    if (typeSelect){
      typeSelect.addEventListener("change", () => {
        manageState.type = typeSelect.value || "all";
        state.manageWatchStatePage = 0;
        renderManageWatchState();
      });
    }
    const pageSizeSelect = root.querySelector("[data-manage-watch-page-size]");
    if (pageSizeSelect){
      pageSizeSelect.addEventListener("change", () => {
        manageState.pageSize = Number(pageSizeSelect.value) || 50;
        state.manageWatchStatePage = 0;
        renderManageWatchState();
      });
    }
    $$("[data-manage-watch-sort]", root).forEach(btn => {
      btn.addEventListener("click", () => {
        const key = safeText(btn.getAttribute("data-manage-watch-sort"));
        if (!key) return;
        if (manageState.sortKey === key) {
          manageState.sortDir = manageState.sortDir === "desc" ? "asc" : "desc";
        } else {
          manageState.sortKey = key;
          manageState.sortDir = "asc";
        }
        state.manageWatchStatePage = 0;
        renderManageWatchState();
      });
    });
    $$("[data-manage-watch-key]", root).forEach(btn => {
      btn.addEventListener("click", () => {
        const key = safeText(btn.getAttribute("data-manage-watch-key"));
        const value = btn.getAttribute("data-manage-watch-value");
        const next = value ? value : btn.getAttribute("aria-pressed") !== "true";
        const context = {
          kind: safeText(btn.getAttribute("data-kind")),
          tmdb_id: safeText(btn.getAttribute("data-tmdb-id")),
          trakt_id: safeText(btn.getAttribute("data-trakt-id")),
          showId: safeText(btn.getAttribute("data-show")),
          seasonNumber: safeText(btn.getAttribute("data-season")),
          episodeNumber: safeText(btn.getAttribute("data-episode")),
          release_status: safeText(btn.getAttribute("data-release-status"))
        };
        if (value && window.MyTVHubWatchState && typeof window.MyTVHubWatchState.setValueByKey === "function") {
          window.MyTVHubWatchState.setValueByKey(key, next, context);
        } else if (window.MyTVHubWatchState && typeof window.MyTVHubWatchState.setByKey === "function") {
          window.MyTVHubWatchState.setByKey(key, next, context);
        } else {
          const data = readLocalWatchState();
          if (value && next !== "unwatched") data[key] = next;
          else if (value) delete data[key];
          else if (next) data[key] = true;
          else delete data[key];
          localStorage.setItem("mytv_watch_state_v1", JSON.stringify(data));
        }
        document.dispatchEvent(new CustomEvent("mytv:watch-state-changed", { detail: { key, source: "manage-watch-state" } }));
        renderManageWatchState();
        if (window.MyTVHubWatchState && typeof window.MyTVHubWatchState.refresh === "function") {
          window.MyTVHubWatchState.refresh(document);
        }
      });
    });
    $$("[data-manage-watch-page]", root).forEach(btn => {
      btn.addEventListener("click", () => {
        const action = safeText(btn.getAttribute("data-manage-watch-page"));
        const tableRoot = root.querySelector("#manageWatchState") || root;
        const pageSize = Number(tableRoot.getAttribute("data-watch-state-page-size") || manageState.pageSize || 50);
        const rowCount = Number(tableRoot.getAttribute("data-watch-state-total-rows") || 0);
        const pageCount = Math.max(1, Math.ceil((rowCount || 1) / pageSize));
        if (action === "first") state.manageWatchStatePage = 0;
        else if (action === "prev") state.manageWatchStatePage = Math.max(0, (Number(state.manageWatchStatePage) || 0) - 1);
        else if (action === "next") state.manageWatchStatePage = Math.min(pageCount - 1, (Number(state.manageWatchStatePage) || 0) + 1);
        else if (action === "last") state.manageWatchStatePage = pageCount - 1;
        renderManageWatchState();
      });
    });
  }

  function renderManageWatchState(){
    const root = $("#manageWatchStateRoot");
    if (!root) return;
    root.innerHTML = renderWatchStateManagerHtml();
    bindWatchStateManager(root);
    applyStickySectionHeads(root);
  }

  async function renderConfig(){
    const root = $("#configRoot");
    if (!root) return;
    const cfg = state.cfg || {};
    root.innerHTML = `
      <section class="config-hero">
        <div>
          <div class="discover-hero__eyebrow">System</div>
          <h2>Runtime configuration at a glance</h2>
          <p>Validation and raw config are still available below, but the important runtime facts are visible first.</p>
        </div>
        <div class="config-stats">
          <div class="config-stat"><strong>${Object.keys(cfg?.icons || {}).length}</strong><span>icon contracts</span></div>
          <div class="config-stat"><strong>${Object.values(cfg?.streaming || {}).filter(v => safeText(v).trim()).length}</strong><span>streaming targets</span></div>
          <div class="config-stat"><strong>${Object.keys(cfg?.image_cache?.folders || {}).length}</strong><span>asset folders</span></div>
          <div class="config-stat"><strong>${cfg?.trakt_sync?.enabled ? "on" : "off"}</strong><span>Trakt sync</span></div>
        </div>
      </section>
      <section class="config-quicklinks">
        <a class="btn" href="./index.html#inputs-editor">Open Inputs Editor</a>
        <a class="btn" href="http://127.0.0.1:8787/web/inputs_editor.html" target="_blank" rel="noopener">Open Local Editor</a>
      </section>
      <div id="configRuntimeSurface"></div>
    `;
    const runtimeRoot = $("#configRuntimeSurface", root);
    try{
      if (window.MyTVHubConfig?.render_config_view){
        await window.MyTVHubConfig.load_config_once();
        window.MyTVHubConfig.render_config_view(runtimeRoot, cfg || window.MyTVHubConfig.get_config(), {});
      } else {
        runtimeRoot.innerHTML = `<div class="inline-error">Config renderer unavailable.</div>`;
      }
    } catch (error){
      runtimeRoot.innerHTML = `<div class="inline-error">Failed to render config view: ${escHtml(error?.message || String(error))}</div>`;
    }
  }

  function buildMoviePopupHtml(movie){
    const title = safeText(movie?.title || "Movie");
    const runtime = Number(movie?.runtime);
    const genres = Array.isArray(movie?.genres) ? movie.genres.map(g => g?.name).filter(Boolean) : [];
    const studioNames = getCompanyNames(movie?.production_companies);
    const studios = studioNames.filter((_, index) => index < 3).join(" • ") || "Unavailable";
    const backdrop = pickImage(movie, "backdrop_local", "backdrop_path");
    const poster = pickImage(movie, "poster_local", "poster_path");
    return `
      <div class="popup-shell popup-shell--movie"${backdrop ? ` style="--popup-backdrop-image:url('${escHtml(backdrop).replace(/'/g, "%27")}')"` : ""}>
        <div class="popup-hero-header">
          <h2 class="popup-hero__title">${escHtml(title)}</h2>
          ${buildActionBarHtml("movie", movie?.tmdb_id ?? "", {
            title,
            pct: (() => {
              let v = progressPercent(movie);
              if (v == null){
                const raw = Number(movie?.vote_average ?? movie?.rating ?? 0);
                if (Number.isFinite(raw) && raw > 0) v = Math.round(raw * 10);
              }
              return v;
            })(),
            favoriteActive: getWatchlistSet().has(String(movie?.tmdb_id ?? "")),
            watchedToggleHtml: watchToggleHtml("movie", { "data-watch-movie-popup": movie?.tmdb_id ?? "" }, isMovieWatched(movie)),
            watchedActive: isMovieWatched(movie),
            showWatchedAction: true,
            showStatusAction: true,
            popcornAttrs: { "data-id": movie?.tmdb_id ?? "" },
            popcornKind: "movie",
            availabilityStatus: availabilityStatusOf(movie),
            available: isMovieAvailable(movie)
          })}
        </div>
        <div class="popup-hero popup-hero--dense">
          <div class="popup-hero__poster">
            ${poster ? `<img loading="lazy" decoding="async" src="${escHtml(poster)}" alt="" />` : `<div class="posterFallback">No Poster</div>`}
          </div>
          <div class="popup-hero__body">
            <div class="popup-detail-grid popup-detail-grid--compact">
              <div class="popup-detail"><span>Availability</span><strong>${escHtml(availabilityLabelOf(movie))}</strong></div>
              <div class="popup-detail"><span>Providers</span><strong>${escHtml(formatProviderSummary(movie))}</strong></div>
              <div class="popup-detail"><span>Genres</span><strong>${escHtml(genres.join(" • ") || "Unavailable")}</strong></div>
              <div class="popup-detail"><span>Runtime</span><strong>${escHtml(Number.isFinite(runtime) && runtime > 0 ? `${runtime} min` : "Unavailable")}</strong></div>
              <div class="popup-detail"><span>Studios</span><strong>${escHtml(studios)}</strong></div>
              <div class="popup-detail"><span>TMDB</span><strong>${escHtml(String(movie?.tmdb_id ?? ""))}</strong></div>
            </div>
            <div class="popup-description">${compactOverviewHtml(movie?.overview || "", 320)}</div>
            <div class="popup-watch-surface">${renderWatchSourceChooserHtml(movie, "movie")}</div>
            <div class="showactions">${linkOrDisabled("meta_rt_critics", getRtLink(movie), "Rotten Tomatoes")}</div>
          </div>
        </div>
      </div>
    `;
  }

  async function openMovieModal(tmdbId){
    const movieIndex = getMovieById(tmdbId);
    if (!movieIndex){
      openModal("Movie", `<div>Movie not found: ${escHtml(tmdbId)}</div>`);
      return;
    }
    openModal(safeText(movieIndex?.title || "Movie"), `<div class="muted">Loading movie details…</div>`);
    const movie = await getMovieDetailById(tmdbId);
    if (!movie){
      $("#modalBody").innerHTML = `<div class="inline-error">Movie detail not found: ${escHtml(tmdbId)}</div>`;
      return;
    }
    $("#modalBody").innerHTML = buildMoviePopupHtml(movie);
    wireMoviePopup(Number(movie?.tmdb_id) || 0);
  }

  function buildShowPopupHtml(show){
    const title = safeText(show.title || show.name || "(Untitled)");
    const seasons = Array.isArray(show.seasons) ? show.seasons : [];
    const seasonItems = seasons.map((season, idx) => ({ n: Number(season?.season_number ?? season?.season ?? season?.number ?? (idx + 1)), s: season }));
    let selected = seasonItems.find(it => Number(it.n) === Number(state.show.selectedSeasonNumber)) || seasonItems.find(it => Array.isArray(it.s?.episodes) && it.s.episodes.length) || seasonItems[0] || null;
    if (selected) state.show.selectedSeasonNumber = selected.n;
    const season = selected?.s || null;
    const episodes = Array.isArray(season?.episodes) ? season.episodes : [];
    const networks = Array.isArray(show.networks) ? show.networks.map(n => n?.name).filter(Boolean) : [];
    const genres = Array.isArray(show?.genres) ? show.genres.map(g => g?.name).filter(Boolean) : [];
    const totalEpisodes = Number(show?.number_of_episodes ?? episodes.length) || episodes.length;
    const premiered = pickAirDate(show);
    const lastAir = safeText(show?.last_air_date || "").trim();
    const seasonEpisodeCount = episodes.length;
    const seasonLabel = safeText(season?.name || (selected ? `Season ${selected.n}` : "Season"));
    const backdrop = pickImage(show, "backdrop_local", "backdrop_path");
    const poster = pickImage(show, "poster_local", "poster_path");
    const showPct = (() => {
      let v = progressPercent(show);
      if (v == null){
        const raw = Number(show?.vote_average ?? show?.rating ?? 0);
        if (Number.isFinite(raw) && raw > 0) v = Math.round(raw * 10);
      }
      return v;
    })();
    const showActionBar = buildActionBarHtml("show", show.tmdb_id ?? "", {
      title,
      pct: showPct,
      favoriteActive: getWatchlistSet().has(String(show.tmdb_id ?? "")),
      watchedActive: isShowWatched(show),
      showWatchedAction: true,
      showStatusAction: true,
      availabilityStatus: availabilityStatusOf(show),
      available: isShowAvailable(show)
    });
    const detailLine = (label, value) => `<div class="popup-detail-line"><span>${escHtml(label)}:</span><strong>${escHtml(value || "Unavailable")}</strong></div>`;
    const showDetailHtml = [
      detailLine("Availability", availabilityLabelOf(show)),
      detailLine("Providers", formatProviderSummary(show)),
      detailLine("Status", safeText(show?.status || "Unavailable")),
      detailLine("Network(s)", networks.join(" • ") || "Unavailable"),
      detailLine("Seasons", seasonItems.length ? `${seasonItems.length} seasons` : "Unavailable"),
      detailLine("Episodes", totalEpisodes ? `${totalEpisodes}` : "Unavailable"),
      detailLine("Premiered", premiered ? fmtDate(premiered) : "Unavailable"),
      detailLine("Last aired", lastAir ? fmtDate(lastAir) : "Unavailable"),
      detailLine("Genres", genres.join(" • ") || "Unavailable"),
      detailLine("TMDB Score", show?.vote_average != null ? `${show.vote_average}${show?.vote_count != null ? ` (${show.vote_count})` : ""}` : "Unavailable")
    ].join("");
    const seasonActionBarHtml = it => {
      const seasonEpisodes = Array.isArray(it.s?.episodes) ? it.s.episodes : [];
      const seasonWatched = isSeasonWatched(show.tmdb_id, it.n, seasonEpisodes.length);
      return buildActionBarHtml("season", it.n, {
        title: safeText(it.s?.name || `Season ${it.n}`),
        compact: true,
        watchedActive: seasonWatched,
        showWatchedAction: true,
        showStatusAction: true,
        statusContext: { showId: show.tmdb_id ?? "", seasonNumber: it.n },
        watchedAttrs: { "data-show": show.tmdb_id ?? "", "data-season": it.n },
        availabilityStatus: availabilityStatusOf(it.s),
        available: isSeasonAvailable(it.s)
      });
    };
    return `
      <div class="popup-shell popup-shell--show"${backdrop ? ` style="--popup-backdrop-image:url('${escHtml(backdrop).replace(/'/g, "%27")}')"` : ""}>
        <div class="popup-hero-header">
          <h2 class="popup-hero__title">${escHtml(title)}</h2>
        </div>
        <div class="popup-hero popup-hero--dense">
          <div class="popup-hero__media">
            <div class="popup-hero__poster popup-hero__poster--show">
              ${poster ? `<img loading="lazy" decoding="async" src="${escHtml(poster)}" alt="" />` : `<div class="posterFallback">No Poster</div>`}
            </div>
            <div class="popup-hero__poster-actions">${showActionBar}</div>
          </div>
          <div class="popup-hero__body">
            <div class="popup-detail-list popup-detail-list--show">
              ${showDetailHtml}
              <div class="popup-detail-description">${compactOverviewHtml(show?.overview || "", 520)}</div>
            </div>
            <div class="showactions">${linkOrDisabled("meta_rt_critics", getRtLink(show), "Rotten Tomatoes")}</div>
          </div>
        </div>
        <div class="section section-card">
          <div class="seasonrail">
            <div class="carousel-controls">
              <button class="epnavbtn" type="button" data-season-nav="jump-prev" aria-label="Jump back seasons">«</button>
              <button class="epnavbtn" type="button" data-season-nav="prev" aria-label="Previous seasons">‹</button>
              <button class="epnavbtn" type="button" data-season-nav="next" aria-label="Next seasons">›</button>
              <button class="epnavbtn" type="button" data-season-nav="jump-next" aria-label="Jump forward seasons">»</button>
            </div>
            <div class="seasonlist seasonlist--carousel" data-season-track>
              ${seasonItems.map(it => `
                <div class="seasonopt${Number(it.n) === Number(selected?.n) ? " is-active" : ""}">
                  <button class="seasonopt__pick" type="button" data-season-pick="${escHtml(it.n)}">
                    <span class="labelrow">
                      <span class="label">${escHtml(it.s?.name || `Season ${it.n}`)}</span>
                      <span class="seasonopt__meta">${escHtml([Array.isArray(it.s?.episodes) ? `${it.s.episodes.length} eps` : "", pickAirDate(it.s) ? fmtDate(pickAirDate(it.s)) : ""].filter(Boolean).join(" • "))}</span>
                    </span>
                  </button>
                  <span class="seasonopt__actions" data-season-action-cell="1">${seasonActionBarHtml(it)}</span>
                </div>
              `).join("") || `<div class="muted">No seasons available.</div>`}
            </div>
          </div>
        </div>
        <div class="section section-card">
          <div class="manual-carousel episode-carousel" data-manual-carousel="episodes" aria-label="${escHtml(`${title} ${seasonLabel} episodes`)}">
            <div class="episode-carousel-header carousel-header">
              <div class="carousel-heading">
                <div class="carousel-title">${escHtml(title)}</div>
                <div class="carousel-context">${escHtml(`${seasonLabel} • ${seasonEpisodeCount ? `${seasonEpisodeCount} episodes` : "No episodes"}`)}</div>
              </div>
              <div class="episode-carousel-controls carousel-controls" aria-label="Episode carousel navigation">
                <button class="epnavbtn" type="button" data-carousel-nav="prev" data-ep-nav="prev" aria-label="Previous episodes">‹</button>
                <button class="epnavbtn" type="button" data-carousel-nav="next" data-ep-nav="next" aria-label="Next episodes">›</button>
              </div>
            </div>
            <div class="episode-carousel-viewport carousel-viewport" tabindex="0" data-carousel-viewport>
              <div class="episode-carousel-track carousel-track" role="list" data-carousel-track>
                ${episodes.map(ep => {
                  const seasonNum = Number(ep?.season_number ?? season?.season_number ?? selected?.n ?? 0) || 0;
                  const episodeNum = Number(ep?.episode_number ?? ep?.number ?? 0) || 0;
                  const epPct = (() => {
                    let v = progressPercent(ep);
                    if (v == null){
                      const raw = Number(ep?.vote_average ?? ep?.rating ?? ep?.rating_percent ?? ep?.rating_pct ?? 0);
                      if (Number.isFinite(raw) && raw > 0) v = Math.round(raw <= 10 ? raw * 10 : raw);
                    }
                    return v;
                  })();
                  const normalizedEp = {
                    ...ep,
                    kind: "episode",
                    show_tmdb_id: show.tmdb_id ?? "",
                    show_title: title,
                    season_number: seasonNum,
                    episode_number: episodeNum,
                    episode_name: safeText(ep?.title || ep?.name || `Episode ${episodeNum}`)
                  };
                  return buildSharedEpisodeCard(normalizedEp, {
                    image: episodeStillImageForCard(normalizedEp, { show }),
                    eyebrow: title,
                    title: safeText(ep?.title || ep?.name || `Episode ${episodeNum}`),
                    meta: episodeMetaLine(seasonNum, episodeNum, ep?.runtime, safeText(ep?.episode_tmdb_id ?? ep?.episode_id ?? ep?.tmdb_episode_id ?? ep?.id ?? "")),
                    submeta: safeText(pickAirDate(ep) ? fmtDate(pickAirDate(ep)) : ""),
                    description: safeText(ep?.overview || ""),
                    overlay: false,
                    density: "standard",
                    pct: epPct,
                    articleAttrs: { tabindex: "0", "data-show": show.tmdb_id ?? "", "data-season": seasonNum, "data-episode": episodeNum },
                    extraClass: "popup-episode-card episode-card",
                    renderKey: `popup:episode:${show.tmdb_id ?? ""}:${seasonNum}:${episodeNum}`
                  });
                }).join("") || `<div class="muted">No episodes available for this season.</div>`}
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  applyRuntimeMode(requestedRuntimeMode(), false);
  ensureMainAppShell();
  ensureRuntimeModeControl();
  setCalendarView(state.calendarView);
  applySidebarState("shows");
  applySidebarState("movies");
  applySidebarState("watch-me");
  if ($("#modalClose")) $("#modalClose").textContent = "Exit";
  if ($("#providerClose")) $("#providerClose").textContent = "Exit";
  document.addEventListener("mytv:watch-state-changed", () => {
    if ($("#manageWatchStateRoot")) renderManageWatchState();
    if (window.MyTVHubWatchState && typeof window.MyTVHubWatchState.refresh === "function") {
      window.MyTVHubWatchState.refresh(document);
    }
  });

  // NAV
  $$(".tab").forEach(btn => {
    on(btn, "click", (e) => {
      const t = btn.dataset.tab;
      if (!t || btn.disabled) return;
      if (getAvailableTabs().has(t)){
        e.preventDefault();
        location.hash = `#${t}`;
      }
    });
  });
  initDrawer("showsFilterBtn", "showsFilterBack", "showsFilterClose");
  initDrawer("moviesFilterBtn", "moviesFilterBack", "moviesFilterClose");

  on($("#calPrev"), "click", () => {
    const m = state.calendarMonth;
    state.calendarMonth = new Date(m.getFullYear(), m.getMonth()-1, 1);
    renderCalendar();
  });
  on($("#calNext"), "click", () => {
    const m = state.calendarMonth;
    state.calendarMonth = new Date(m.getFullYear(), m.getMonth()+1, 1);
    renderCalendar();
  });
  on($("#calToday"), "click", () => {
    initCalendarMonth();
    renderCalendar();
    requestAnimationFrame(() => scrollToDayCell(toDateKey(new Date())));
  });
  on($("#calendarViewToggle"), "click", (e) => {
    const btn = e.target.closest("[data-calendar-view]");
    if (!btn) return;
    setCalendarView(btn.getAttribute("data-calendar-view") || "grid");
    renderCalendar();
  });
  on(window, "resize", () => updateCalendarStickyVars());

  on($("#searchShows"), "input", (e) => {
    state.search.shows = e.target.value || "";
    renderShows();
  });
  on($("#filterShowsGenres"), "change", () => {
    state.filters.shows.genres = getCheckedValues($("#filterShowsGenres"));
    renderShows();
  });
  on($("#filterShowsYear"), "change", (e) => {
    state.filters.shows.year = e.target.value || "";
    renderShows();
  });
  on($("#filterShowsScope"), "click", (e) => {
    const btn = e.target.closest("[data-scope]");
    if (!btn) return;
    state.filters.shows.scope = btn.getAttribute("data-scope") || "all";
    setSegActive($("#filterShowsScope"), "scope", state.filters.shows.scope);
    renderShows();
  });
  on($("#filterShowsAvailability"), "click", (e) => {
    const btn = e.target.closest("[data-availability]");
    if (!btn) return;
    state.filters.shows.availability = btn.getAttribute("data-availability") || "all";
    setSegActive($("#filterShowsAvailability"), "availability", state.filters.shows.availability);
    renderShows();
  });
  on($("#filterShowsWatched"), "click", (e) => {
    const btn = e.target.closest("[data-watched]");
    if (!btn) return;
    state.filters.shows.watched = btn.getAttribute("data-watched") || "all";
    setSegActive($("#filterShowsWatched"), "watched", state.filters.shows.watched);
    renderShows();
  });
  on($("#filterShowsWatchlist"), "click", (e) => {
    const btn = e.target.closest("[data-watchlist]");
    if (!btn || btn.disabled) return;
    state.filters.shows.watchlist = btn.getAttribute("data-watchlist") || "all";
    setSegActive($("#filterShowsWatchlist"), "watchlist", state.filters.shows.watchlist);
    renderShows();
  });
  on($("#sortShows"), "change", (e) => {
    state.sort.shows = e.target.value || "title";
    renderShows();
  });

  on($("#searchMovies"), "input", (e) => {
    state.search.movies = e.target.value || "";
    renderMovies();
  });
  on($("#filterMoviesGenres"), "change", () => {
    state.filters.movies.genres = getCheckedValues($("#filterMoviesGenres"));
    renderMovies();
  });
  on($("#filterMoviesYear"), "change", (e) => {
    state.filters.movies.year = e.target.value || "";
    renderMovies();
  });
  on($("#filterMoviesCollection"), "change", (e) => {
    state.filters.movies.collection = e.target.value || "";
    renderMovies();
  });
  on($("#filterMoviesScope"), "click", (e) => {
    const btn = e.target.closest("[data-scope]");
    if (!btn) return;
    state.filters.movies.scope = btn.getAttribute("data-scope") || "all";
    setSegActive($("#filterMoviesScope"), "scope", state.filters.movies.scope);
    renderMovies();
  });
  on($("#filterMoviesAvailability"), "click", (e) => {
    const btn = e.target.closest("[data-availability]");
    if (!btn) return;
    state.filters.movies.availability = btn.getAttribute("data-availability") || "all";
    setSegActive($("#filterMoviesAvailability"), "availability", state.filters.movies.availability);
    renderMovies();
  });
  on($("#filterMoviesWatched"), "click", (e) => {
    const btn = e.target.closest("[data-watched]");
    if (!btn) return;
    state.filters.movies.watched = btn.getAttribute("data-watched") || "all";
    setSegActive($("#filterMoviesWatched"), "watched", state.filters.movies.watched);
    renderMovies();
  });
  on($("#filterMoviesWatchlist"), "click", (e) => {
    const btn = e.target.closest("[data-watchlist]");
    if (!btn || btn.disabled) return;
    state.filters.movies.watchlist = btn.getAttribute("data-watchlist") || "all";
    setSegActive($("#filterMoviesWatchlist"), "watchlist", state.filters.movies.watchlist);
    renderMovies();
  });
  on($("#sortMovies"), "change", (e) => {
    state.sort.movies = e.target.value || "title";
    renderMovies();
  });

  on($("#watchMeSearch"), "input", (e) => {
    state.watchMe.search = e.target.value || "";
    renderWatchMe();
  });
  on($("#watchMeType"), "change", (e) => {
    state.watchMe.type = e.target.value || "all";
    renderWatchMe();
  });
  on($("#watchMeWindow"), "change", (e) => {
    state.watchMe.windowDays = Number(e.target.value || 14);
    renderWatchMe();
  });
  on($("#watchMeReset"), "click", () => {
    state.watchMe = { search: "", type: "all", windowDays: 14 };
    if ($("#watchMeSearch")) $("#watchMeSearch").value = "";
    if ($("#watchMeType")) $("#watchMeType").value = "all";
    if ($("#watchMeWindow")) $("#watchMeWindow").value = "14";
    renderWatchMe();
  });
  on($("#watchMeToday"), "click", () => {
    const today = toDateKey(new Date());
    const group = document.querySelector(`.watchme-day-group[data-date-key="${CSS.escape(today)}"]`);
    if (!group) return;
    group.scrollIntoView({ block: "start", inline: "nearest", behavior: "smooth" });
    const firstCard = group.querySelector("[data-show], [data-movie]");
    if (firstCard instanceof HTMLElement) firstCard.focus({ preventScroll: true });
  });

  $$("[data-sidebar-toggle]").forEach(btn => {
    on(btn, "click", () => {
      const kind = safeText(btn.getAttribute("data-sidebar-toggle"));
      if (!kind) return;
      const key = sidebarStateKey(kind);
      setSidebarCollapsed(kind, !state.layout[key]);
    });
  });

  $$("[data-tab-jump]").forEach(link => {
    on(link, "click", (e) => {
      const target = safeText(link.getAttribute("data-tab-jump"));
      if (!target || !getAvailableTabs().has(target)) return;
      e.preventDefault();
      location.hash = `#${target}`;
    });
  });


  // Modal close
  on($("#modalClose"), "click", closeModal);
  on($("#modalBack"), "click", (e) => { if (e.target === $("#modalBack")) closeModal(); });
  on($("#providerClose"), "click", closeProviderModal);
  on($("#providerBack"), "click", (e) => { if (e.target === $("#providerBack")) closeProviderModal(); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" || e.key === "Backspace" || e.key === "BrowserBack"){
      closeAllActionMenus();
      if ($("#providerBack")?.style.display === "flex") return closeProviderModal();
      if ($("#modalBack")?.style.display === "flex") return closeModal();
      return;
    }
    if (isModalOpen() && ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)){
      e.preventDefault();
      e.stopPropagation();
      moveFocus(e.key);
      return;
    }
    if (e.key === "Tab"){
      return trapTabInModal(e);
    }
    if (e.key === "Enter" || e.key === " "){
      const active = document.activeElement;
      const fnType = safeText(active?.getAttribute?.("data-function-type"));
      if (fnType){
        e.preventDefault();
        if (fnType === "link"){
          const href = active?.getAttribute?.("href") || active?.getAttribute?.("data-href") || "";
          if (href){
            window.open(href, "_blank", "noopener");
          } else if (active?.click){
            active.click();
          }
        } else if (active?.click){
          active.click();
        }
        return;
      }
    }
  });

  document.addEventListener("click", () => closeAllActionMenus());
  document.addEventListener("focusin", (e) => {
    if (!isModalOpen()) return;
    const root = activeModalCard();
    if (!root || root.contains(e.target)) return;
    e.stopPropagation();
    const first = getFocusables(root)[0];
    if (first && typeof first.focus === "function") first.focus({ preventScroll: true });
  }, true);

  window.addEventListener("hashchange", routeFromHash);

  loadAll();
})();
