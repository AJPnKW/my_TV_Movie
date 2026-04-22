import puppeteer from "puppeteer-core";

const BASE_URL = (process.env.BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

const browser = await puppeteer.launch({
  executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless: "new",
  defaultViewport: { width: 1920, height: 1080 },
  args: ["--no-sandbox"]
});

async function sleep(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function inspectPage(pathname, kind) {
  const page = await browser.newPage();
  const errors = [];
  const missing = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  page.on("pageerror", (err) => errors.push(err.message));
  page.on("response", (response) => {
    if (response.status() === 404) missing.push(response.url());
  });
  await page.goto(`${BASE_URL}/web/${pathname}`, { waitUntil: "load", timeout: 60000 });
  await sleep(3000);
  const selectors = kind === "tv"
    ? ["[data-show-open]", ".media-card--show", "[data-kind='tv'][data-tmdb-id]"]
    : ["[data-movie-open]", ".media-card--movie", "[data-kind='movie'][data-tmdb-id]"];
  await page.waitForSelector(selectors.join(","), { timeout: 15000 });
  const clicked = await page.evaluate((selectorList) => {
    for (const selector of selectorList) {
      const el = document.querySelector(selector);
      if (el) {
        el.click();
        return selector;
      }
    }
    return "";
  }, selectors);
  await sleep(3000);
  const result = await page.evaluate(() => ({
    title: document.querySelector("#modalBody .popup-title, #modalBody h1, #modalBody h2")?.textContent?.trim() || "",
    seasonButtons: document.querySelectorAll("#modalBody [data-season-pick]").length,
    episodeCards: document.querySelectorAll("#modalBody .popup-episode-card").length,
    watchPanels: document.querySelectorAll("#modalBody .watch-source-panel").length,
    descriptionText: document.querySelector("#modalBody .popup-description")?.textContent?.trim() || "",
    firstEpisodeWidth: Math.round(document.querySelector("#modalBody .popup-episode-card")?.getBoundingClientRect().width || 0),
    firstEpisodeSummary: document.querySelector("#modalBody .popup-episode-card .media-card__summary")?.textContent?.trim() || "",
    bodyOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2
  }));
  await page.close();
  return { clicked, errors, missing, ...result };
}

try {
  const show = await inspectPage("shows.html", "tv");
  const movie = await inspectPage("movies.html", "movie");
  const failures = [];
  if (!show.title) failures.push("show popup title missing");
  if (show.watchPanels !== 0) failures.push(`show popup should not render direct watch panels, found ${show.watchPanels}`);
  if (show.seasonButtons < 1) failures.push("show popup season buttons missing");
  if (show.episodeCards < 1) failures.push("show popup episode cards missing");
  if (show.firstEpisodeWidth < 240) failures.push(`show popup episode carousel card too narrow (${show.firstEpisodeWidth}px)`);
  if (!show.descriptionText) failures.push("show popup description missing");
  if (!movie.title) failures.push("movie popup title missing");
  if (movie.watchPanels < 1) failures.push("movie popup watch panels missing");
  if (show.errors.length || movie.errors.length) failures.push("browser console errors detected");
  if (show.missing.length || movie.missing.length) failures.push("404 assets detected");
  console.log(JSON.stringify({ show, movie }, null, 2));
  if (failures.length) {
    console.error(JSON.stringify({ failures }, null, 2));
    process.exitCode = 1;
  }
} finally {
  await browser.close();
}
