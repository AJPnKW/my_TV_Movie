import puppeteer from "puppeteer-core";

const BASE_URL = (process.env.BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

const VIEWPORTS = [
  { name: "android-tv-1080p", width: 1920, height: 1080 },
  { name: "laptop", width: 1366, height: 768 },
  { name: "tablet-landscape", width: 1024, height: 768 },
  { name: "tablet-portrait", width: 768, height: 1024 },
  { name: "phone-large", width: 430, height: 932 },
  { name: "phone", width: 390, height: 844 }
];

const browser = await puppeteer.launch({
  executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless: "new",
  args: ["--no-sandbox"]
});

async function sleep(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function inspect(pathname, viewport) {
  const page = await browser.newPage();
  await page.setViewport({ width: viewport.width, height: viewport.height, deviceScaleFactor: 1 });
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
  await sleep(2500);
  const metrics = await page.evaluate(() => {
    const bodyOverflow = document.documentElement.scrollWidth > document.documentElement.clientWidth + 2;
    const firstCard = document.querySelector(".media-card, .calendar-day");
    const firstImg = document.querySelector(".calendar-item .media-card__poster img, .calendar-item .imgbox img, .media-card__poster img, .imgbox img");
    const dashCols = document.querySelector("#dashScheduleCols");
    const calendarGrid = document.querySelector(".calendar-month-grid");
    const calendarBand = document.querySelector(".calendar-week-band");
    const visibleCalendarItems = Array.from(document.querySelectorAll(".calendar-item")).filter(el => getComputedStyle(el).display !== "none" && !el.classList.contains("hidden"));
    const firstRect = firstCard?.getBoundingClientRect();
    const imageRect = firstImg?.getBoundingClientRect();
    return {
      bodyOverflow,
      cardWidth: Math.round(firstRect?.width || 0),
      cardHeight: Math.round(firstRect?.height || 0),
      imageWidth: Math.round(imageRect?.width || 0),
      imageHeight: Math.round(imageRect?.height || 0),
      dashboardColumns: dashCols ? getComputedStyle(dashCols).gridTemplateColumns.split(" ").filter(Boolean).length : 0,
      calendarColumns: calendarGrid ? getComputedStyle(calendarGrid).gridTemplateColumns.split(" ").filter(Boolean).length : 0,
      calendarBandColumns: calendarBand ? getComputedStyle(calendarBand).gridTemplateColumns.split(" ").filter(Boolean).length : 0,
      calendarItems: visibleCalendarItems.length,
      calendarItemImages: visibleCalendarItems.filter(el => el.querySelector(".media-card__poster img, .imgbox img")).length
    };
  });
  await page.close();
  return { pathname, viewport: viewport.name, errors, missing, ...metrics };
}

try {
  const results = [];
  for (const viewport of VIEWPORTS) {
    results.push(await inspect("index.html", viewport));
    results.push(await inspect("calendar.html", viewport));
  }
  const failures = [];
  for (const result of results) {
    if (result.errors.length) failures.push(`${result.viewport} ${result.pathname}: console errors`);
    if (result.missing.length) failures.push(`${result.viewport} ${result.pathname}: 404 responses`);
    if (result.bodyOverflow) failures.push(`${result.viewport} ${result.pathname}: page-level horizontal overflow`);
    const minCardWidth = result.pathname === "calendar.html" && result.viewport.startsWith("phone") ? 120 : 128;
    if (result.cardWidth > 0 && result.cardWidth < minCardWidth) failures.push(`${result.viewport} ${result.pathname}: card width too narrow (${result.cardWidth}px)`);
    if (result.imageWidth > 0 && result.imageWidth < 90) failures.push(`${result.viewport} ${result.pathname}: image width too narrow (${result.imageWidth}px)`);
    if ((result.viewport === "android-tv-1080p" || result.viewport === "laptop") && result.pathname === "calendar.html" && result.calendarColumns !== 7) {
      failures.push(`${result.viewport} calendar.html: expected 7 readable columns, found ${result.calendarColumns}`);
    }
    if ((result.viewport === "android-tv-1080p" || result.viewport === "laptop") && result.pathname === "calendar.html" && result.calendarBandColumns !== 7) {
      failures.push(`${result.viewport} calendar.html: expected 7 day/date band columns, found ${result.calendarBandColumns}`);
    }
    if ((result.viewport === "android-tv-1080p" || result.viewport === "laptop") && result.pathname === "calendar.html" && result.calendarItems > 0 && result.calendarItemImages < result.calendarItems) {
      failures.push(`${result.viewport} calendar.html: calendar episode/movie cards missing images (${result.calendarItemImages}/${result.calendarItems})`);
    }
  }
  console.log(JSON.stringify({ results, failures }, null, 2));
  if (failures.length) process.exitCode = 1;
} finally {
  await browser.close();
}
