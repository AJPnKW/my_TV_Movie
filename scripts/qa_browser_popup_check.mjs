import puppeteer from "puppeteer-core";

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
  await page.goto(`http://127.0.0.1:8000/web/${pathname}`, { waitUntil: "load", timeout: 60000 });
  await sleep(3000);
  const selectors = kind === "tv"
    ? ["[data-show-open]", ".media-card--show", "[data-kind='tv'][data-tmdb-id]"]
    : ["[data-movie-open]", ".media-card--movie", "[data-kind='movie'][data-tmdb-id]"];
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
    watchPanels: document.querySelectorAll("#modalBody .watch-source-panel").length
  }));
  await page.close();
  return { clicked, errors, missing, ...result };
}

try {
  const show = await inspectPage("shows.html", "tv");
  const movie = await inspectPage("movies.html", "movie");
  console.log(JSON.stringify({ show, movie }, null, 2));
} finally {
  await browser.close();
}
