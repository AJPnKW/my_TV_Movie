import puppeteer from "puppeteer-core";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

const BASE_URL = (process.env.BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
const DAY_MS = 24 * 60 * 60 * 1000;
const REPORT_PATH = "reports/ui_stabilization/browse_filter_parity_2026-07-24.json";
const SCREENSHOT_DIR = "reports/ui_stabilization/screenshots";

const VIEWPORTS = [
  { name: "phone", width: 390, height: 844, screenshot: true },
  { name: "tablet", width: 768, height: 1024 },
  { name: "desktop", width: 1366, height: 768, screenshot: true },
  { name: "android-tv-1080p", width: 1920, height: 1080, screenshot: true }
];

const config = JSON.parse(readFileSync("web/config.json", "utf8"));
const RELEASE_VERSION = String(config._meta?.version || "v1.5.5");
const currentConfig = config.browse?.current || {};
const CURRENT_SHOW_ACTIVITY_WINDOW_DAYS = Number(currentConfig.show_activity_window_days) || 183;
const CURRENT_MOVIE_RELEASE_WINDOW_DAYS = Number(currentConfig.movie_release_window_days) || 183;
const CURRENT_MOVIE_RELEASE_LOOKAHEAD_DAYS = Number(currentConfig.movie_release_lookahead_days) || 30;
const data = JSON.parse(readFileSync("data/data.json", "utf8"));
const showsById = new Map((data.shows || []).map(item => [String(item.tmdb_id ?? item.id ?? ""), item]));
const moviesById = new Map((data.movies || []).map(item => [String(item.tmdb_id ?? item.id ?? ""), item]));

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function dateValue(value) {
  const parsed = Date.parse(String(value || ""));
  return Number.isFinite(parsed) ? parsed : null;
}

function isCurrentShow(show, nowMs = Date.now()) {
  const firstAir = dateValue(show?.first_air_date);
  if (firstAir !== null && firstAir > nowMs) return false;
  const status = String(show?.status || "").trim().toLowerCase();
  if (["ended", "canceled", "cancelled"].includes(status)) return false;
  const recentCutoff = nowMs - (CURRENT_SHOW_ACTIVITY_WINDOW_DAYS * DAY_MS);
  const recentActivity = dateValue(
    show?.last_air_date ||
    show?.latest_episode_to_air?.air_date ||
    show?.last_episode_to_air?.air_date
  );
  return recentActivity !== null && recentActivity >= recentCutoff;
}

function availabilityStatusOf(item) {
  const raw = String(item?.availability_status || "").toLowerCase();
  if (raw) return raw;
  const release = dateValue(item?.release_date || item?.first_air_date);
  if (release !== null && release > Date.now()) return "not_yet_released";
  return "available";
}

function isCurrentMovie(movie, nowMs = Date.now()) {
  const release = dateValue(movie?.release_date);
  if (release === null) return false;
  const recentCutoff = nowMs - (CURRENT_MOVIE_RELEASE_WINDOW_DAYS * DAY_MS);
  if (release < recentCutoff) return false;
  if (release <= nowMs) return true;
  const lookahead = nowMs + (CURRENT_MOVIE_RELEASE_LOOKAHEAD_DAYS * DAY_MS);
  return release <= lookahead && availabilityStatusOf(movie) === "available";
}

function currentPredicate(kind, item) {
  return kind === "shows" ? isCurrentShow(item) : isCurrentMovie(item);
}

function titleOf(kind, item) {
  return String(kind === "shows" ? (item?.title || item?.name || "") : (item?.title || ""));
}

function genresOf(item) {
  return Array.isArray(item?.genres) ? item.genres.map(genre => genre?.name).filter(Boolean) : [];
}

function searchToken(title) {
  return String(title || "").split(/\s+/).map(part => part.replace(/[^A-Za-z0-9]/g, "")).find(part => part.length >= 4) || String(title || "").slice(0, 4);
}

async function waitForCards(page, kind) {
  const grid = kind === "shows" ? "#showsGrid" : "#moviesGrid";
  await page.waitForSelector(`${grid} .media-card`, { timeout: 60000 });
}

async function visibleState(page, kind) {
  return page.evaluate((kindArg) => {
    const grid = kindArg === "shows" ? document.querySelector("#showsGrid") : document.querySelector("#moviesGrid");
    const triggerAttr = kindArg === "shows" ? "data-show-open" : "data-movie-open";
    const ids = Array.from(grid?.querySelectorAll(`.media-card [${triggerAttr}]`) || []).map(node => node.getAttribute(triggerAttr)).filter(Boolean);
    const titles = Array.from(grid?.querySelectorAll(".media-card__title") || []).map(node => node.textContent.trim());
    const summary = document.querySelector(kindArg === "shows" ? "#showsSummary" : "#moviesSummary")?.textContent?.trim() || "";
    return { ids, titles, count: ids.length, summary };
  }, kind);
}

async function scopeState(page, kind) {
  return page.evaluate((kindArg) => {
    const root = document.querySelector(kindArg === "shows" ? "#filterShowsScope" : "#filterMoviesScope");
    const all = root?.querySelector('[data-scope="all"]');
    const current = root?.querySelector('[data-scope="current"]');
    return {
      controlCount: root?.querySelectorAll('[data-scope="current"]').length || 0,
      allActive: !!all?.classList.contains("active"),
      currentActive: !!current?.classList.contains("active"),
      allPressed: all?.getAttribute("aria-pressed") || "",
      currentPressed: current?.getAttribute("aria-pressed") || ""
    };
  }, kind);
}

async function setSearch(page, kind, value) {
  const selector = kind === "shows" ? "#searchShows" : "#searchMovies";
  await page.focus(selector);
  await page.evaluate((sel) => { const input = document.querySelector(sel); input.value = ""; input.dispatchEvent(new Event("input", { bubbles: true })); }, selector);
  await page.type(selector, value);
  await page.waitForFunction((sel, expected) => document.querySelector(sel)?.value === expected, {}, selector, value);
}

async function clickScope(page, kind, scope) {
  const root = kind === "shows" ? "#filterShowsScope" : "#filterMoviesScope";
  await page.click(`${root} [data-scope="${scope}"]`);
  await page.waitForFunction((rootSel, value) => {
    const btn = document.querySelector(`${rootSel} [data-scope="${value}"]`);
    return btn?.classList.contains("active") && btn?.getAttribute("aria-pressed") === "true";
  }, {}, root, scope);
}

async function chooseGenre(page, kind, genre) {
  const selector = kind === "shows" ? "#filterShowsGenres" : "#filterMoviesGenres";
  const ok = await page.evaluate((rootSel, value) => {
    const input = Array.from(document.querySelectorAll(`${rootSel} input[type="checkbox"]`)).find(node => node.value === value);
    if (!input) return false;
    input.checked = true;
    input.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }, selector, genre);
  if (!ok) throw new Error(`${kind}: genre not found: ${genre}`);
}

async function clearGenres(page, kind) {
  const selector = kind === "shows" ? "#filterShowsGenres" : "#filterMoviesGenres";
  await page.evaluate((rootSel) => {
    document.querySelectorAll(`${rootSel} input[type="checkbox"]`).forEach(input => {
      input.checked = false;
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }, selector);
}

async function inspectLayout(page, kind) {
  return page.evaluate((kindArg) => {
    const search = document.querySelector(kindArg === "shows" ? "#searchShows" : "#searchMovies");
    const genreRoot = document.querySelector(kindArg === "shows" ? "#filterShowsGenres" : "#filterMoviesGenres");
    const searchStyle = search ? getComputedStyle(search) : null;
    const searchRect = search?.getBoundingClientRect();
    const items = Array.from(genreRoot?.querySelectorAll(".checkitem") || []);
    const rects = items.slice(0, 24).map(item => item.getBoundingClientRect()).filter(rect => rect.width > 0 && rect.height > 0);
    const rows = [];
    rects.forEach(rect => {
      const row = rows.find(existing => Math.abs(existing.top - rect.top) < 3);
      if (row) row.bottom = Math.max(row.bottom, rect.bottom);
      else rows.push({ top: rect.top, bottom: rect.bottom });
    });
    rows.sort((a, b) => a.top - b.top);
    const rowGaps = rows.slice(1).map((row, index) => Math.round(row.top - rows[index].bottom));
    return {
      searchVisible: !!searchRect && searchStyle?.display !== "none" && searchStyle?.visibility !== "hidden" && searchRect.width > 40 && searchRect.height > 20,
      searchRect: searchRect ? { width: Math.round(searchRect.width), height: Math.round(searchRect.height) } : null,
      genreItemCount: items.length,
      genreMinHeight: rects.length ? Math.round(Math.min(...rects.map(rect => rect.height))) : 0,
      genreMaxRowGap: rowGaps.length ? Math.max(...rowGaps) : 0,
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
      duplicateSearchIds: document.querySelectorAll(kindArg === "shows" ? "#searchShows" : "#searchMovies").length,
      duplicateCurrentControls: document.querySelectorAll(kindArg === "shows" ? '#filterShowsScope [data-scope="current"]' : '#filterMoviesScope [data-scope="current"]').length,
      assetUrls: {
        mainCss: document.querySelector('link[href*="main_app.css"]')?.getAttribute("href") || "",
        appRuntime: document.querySelector('script[src*="app_runtime.js"]')?.getAttribute("src") || "",
        mobileCurrent: document.querySelectorAll('script[src*="mobile_current_filters.js"]').length,
        mobileCss: document.querySelectorAll('link[href*="mobile_browse_fixes.css"]').length
      },
      serviceWorkerController: !!navigator.serviceWorker?.controller
    };
  }, kind);
}

async function runCase(browser, kind, viewport) {
  const pageName = kind === "shows" ? "shows.html" : "movies.html";
  const page = await browser.newPage();
  await page.setViewport({ width: viewport.width, height: viewport.height, deviceScaleFactor: 1 });
  await page.evaluateOnNewDocument(() => {
    try { localStorage.setItem("mytv_runtime_mode", "full"); } catch (_) {}
  });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", msg => {
    if (msg.type() === "error" && !/Failed to load resource|favicon/i.test(msg.text())) errors.push(msg.text());
  });

  await page.goto(`${BASE_URL}/web/${pageName}`, { waitUntil: "load", timeout: 60000 });
  await waitForCards(page, kind);

  const map = kind === "shows" ? showsById : moviesById;
  const initial = await visibleState(page, kind);
  const layoutInitial = await inspectLayout(page, kind);
  await clickScope(page, kind, "current");
  await sleep(250);
  const current = await visibleState(page, kind);
  const active = await scopeState(page, kind);
  const invalidCurrentIds = current.ids.filter(id => !currentPredicate(kind, map.get(String(id))));
  const firstCurrentItem = current.ids.map(id => map.get(String(id))).find(Boolean);
  const token = searchToken(titleOf(kind, firstCurrentItem));
  await setSearch(page, kind, token);
  await sleep(250);
  const searched = await visibleState(page, kind);
  const invalidSearchIds = searched.ids.filter(id => {
    const item = map.get(String(id));
    return !item || !currentPredicate(kind, item) || !titleOf(kind, item).toLowerCase().includes(token.toLowerCase());
  });
  const genre = genresOf(searched.ids.map(id => map.get(String(id))).find(Boolean))[0] || genresOf(firstCurrentItem)[0];
  await chooseGenre(page, kind, genre);
  await sleep(250);
  const genreFiltered = await visibleState(page, kind);
  const invalidGenreIds = genreFiltered.ids.filter(id => {
    const item = map.get(String(id));
    return !item || !currentPredicate(kind, item) || !titleOf(kind, item).toLowerCase().includes(token.toLowerCase()) || !genresOf(item).includes(genre);
  });
  const layoutGenre = await inspectLayout(page, kind);
  if (viewport.name === "phone" && kind === "shows") {
    await page.screenshot({ path: join(SCREENSHOT_DIR, "shows-phone-current-search-genre.png"), fullPage: true });
  }
  if (viewport.name === "phone" && kind === "movies") {
    await page.screenshot({ path: join(SCREENSHOT_DIR, "movies-phone-current-search-genre.png"), fullPage: true });
  }
  if (viewport.name === "desktop" && kind === "shows") {
    await page.screenshot({ path: join(SCREENSHOT_DIR, "shows-desktop-current.png"), fullPage: true });
  }
  if (viewport.name === "android-tv-1080p" && kind === "movies") {
    await page.screenshot({ path: join(SCREENSHOT_DIR, "movies-tv-current.png"), fullPage: true });
  }

  await setSearch(page, kind, "");
  await clearGenres(page, kind);
  await clickScope(page, kind, "all");
  await sleep(250);
  const allAgain = await visibleState(page, kind);
  const allActive = await scopeState(page, kind);
  await page.goto(`${BASE_URL}/web/index.html`, { waitUntil: "load", timeout: 60000 });
  await page.goBack({ waitUntil: "load", timeout: 60000 });
  await waitForCards(page, kind);
  const afterBack = await inspectLayout(page, kind);
  await page.reload({ waitUntil: "load", timeout: 60000 });
  await waitForCards(page, kind);
  const afterReload = await inspectLayout(page, kind);
  await page.close();

  const checks = {
    searchVisible: layoutInitial.searchVisible && afterBack.searchVisible && afterReload.searchVisible,
    currentActiveExclusive: active.controlCount === 1 && active.currentActive && !active.allActive && active.currentPressed === "true" && active.allPressed === "false",
    currentFiltersRecords: current.count > 0 && invalidCurrentIds.length === 0,
    resultCountUpdates: current.count > 0 && current.count < initial.count && /results/.test(current.summary),
    searchCombinesWithCurrent: searched.count > 0 && invalidSearchIds.length === 0,
    genreCombinesWithSearchAndCurrent: genreFiltered.count > 0 && invalidGenreIds.length === 0,
    allRestoresFullSet: allActive.allActive && !allActive.currentActive && allAgain.count === initial.count,
    compactGenreLayout: viewport.name !== "phone" || (layoutGenre.genreItemCount > 0 && layoutGenre.genreMinHeight >= 30 && layoutGenre.genreMaxRowGap <= 10 && !layoutGenre.horizontalOverflow),
    noDuplicateControls: layoutInitial.duplicateSearchIds === 1 && layoutInitial.duplicateCurrentControls === 1,
    noMobileForkAssets: layoutInitial.assetUrls.mobileCurrent === 0 && layoutInitial.assetUrls.mobileCss === 0,
    versionedAssets: layoutInitial.assetUrls.mainCss.includes(`?v=${RELEASE_VERSION}`) && layoutInitial.assetUrls.appRuntime.includes(`?v=${RELEASE_VERSION}`),
    noServiceWorkerController: !layoutInitial.serviceWorkerController
  };

  return {
    kind,
    viewport: viewport.name,
    page: pageName,
    errors,
    initialCount: initial.count,
    currentCount: current.count,
    searchedCount: searched.count,
    genreFilteredCount: genreFiltered.count,
    allAgainCount: allAgain.count,
    searchToken: token,
    genre,
    invalidCurrentIds,
    invalidSearchIds,
    invalidGenreIds,
    layoutInitial,
    layoutGenre,
    afterBack,
    afterReload,
    checks,
    passed: errors.length === 0 && Object.values(checks).every(Boolean)
  };
}

mkdirSync(dirname(REPORT_PATH), { recursive: true });
mkdirSync(SCREENSHOT_DIR, { recursive: true });

const browser = await puppeteer.launch({
  executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless: "new",
  args: ["--no-sandbox"]
});

const results = [];
for (const viewport of VIEWPORTS) {
  for (const kind of ["shows", "movies"]) {
    results.push(await runCase(browser, kind, viewport));
  }
}
await browser.close();

const screenshots = [
  "reports/ui_stabilization/screenshots/shows-phone-current-search-genre.png",
  "reports/ui_stabilization/screenshots/movies-phone-current-search-genre.png",
  "reports/ui_stabilization/screenshots/shows-desktop-current.png",
  "reports/ui_stabilization/screenshots/movies-tv-current.png"
];
const failures = results.filter(result => !result.passed).map(result => ({
  kind: result.kind,
  viewport: result.viewport,
  errors: result.errors,
  failedChecks: Object.entries(result.checks).filter(([, ok]) => !ok).map(([key]) => key)
}));
const report = {
  issue_id: "UI-PARITY-CURRENT-SEARCH-CACHE-2026-07-24",
  base_url: BASE_URL,
  release_version: RELEASE_VERSION,
  current_show_rule: { activity_window_days: CURRENT_SHOW_ACTIVITY_WINDOW_DAYS },
  current_movie_rule: {
    release_window_days: CURRENT_MOVIE_RELEASE_WINDOW_DAYS,
    lookahead_days: CURRENT_MOVIE_RELEASE_LOOKAHEAD_DAYS,
    future_requires_available: true
  },
  screenshots,
  results,
  failures
};
writeFileSync(REPORT_PATH, `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify({ report: REPORT_PATH, screenshots, failures }, null, 2));
if (failures.length) process.exit(1);
