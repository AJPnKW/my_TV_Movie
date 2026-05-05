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
    if (msg.type() === "error" && !/Failed to load resource|favicon/i.test(msg.text())) errors.push(msg.text());
  });
  page.on("pageerror", (err) => errors.push(err.message));
  page.on("response", (response) => {
    if (response.status() === 404 && !/favicon\.ico$|127\.0\.0\.1:8787\/api\/watch-state-queue/i.test(response.url())) missing.push(response.url());
  });
  await page.goto(`${BASE_URL}/web/${pathname}`, { waitUntil: "load", timeout: 60000 });
  await sleep(2500);
  const metrics = await page.evaluate(async () => {
    const bodyOverflow = document.documentElement.scrollWidth > document.documentElement.clientWidth + 2;
    const rect = (el) => {
      const r = el?.getBoundingClientRect?.();
      return r ? { left: r.left, right: r.right, width: r.width, top: r.top, bottom: r.bottom, height: r.height } : null;
    };
    const firstCard = document.querySelector(".media-card, .calendar-day");
    const firstImg = document.querySelector(".calendar-item .media-card__poster img, .calendar-item .imgbox img, .media-card__poster img, .imgbox img");
    const dashCols = document.querySelector("#dashScheduleCols");
    const calendarGrid = document.querySelector(".calendar-month-grid");
    const calendarBand = document.querySelector(".calendar-week-band");
    const visibleCalendarItems = Array.from(document.querySelectorAll(".calendar-item")).filter(el => getComputedStyle(el).display !== "none" && !el.classList.contains("hidden"));
    const firstRect = firstCard?.getBoundingClientRect();
    const imageRect = firstImg?.getBoundingClientRect();
    const firstWeekHeaders = calendarBand ? Array.from(calendarBand.querySelectorAll(".calendar-week-band__day")).map(rect) : [];
    const firstWeekDays = Array.from(document.querySelectorAll(".calendar-month-grid > .calendar-day")).slice(0, 7).map(rect);
    const calendarAlignment = firstWeekHeaders.map((headerRect, index) => {
      const dayRect = firstWeekDays[index];
      return dayRect ? {
        index,
        leftDelta: Math.abs(headerRect.left - dayRect.left),
        rightDelta: Math.abs(headerRect.right - dayRect.right),
        widthDelta: Math.abs(headerRect.width - dayRect.width)
      } : { index, missingDay: true };
    });
    const calendarEpisodePosterImages = Array.from(document.querySelectorAll(".calendar-item.media-card--episode img")).filter(img => /poster/i.test(img.getAttribute("src") || "")).length;
    const weekendDay = document.querySelector(".calendar-day--weekend");
    const weekdayDay = Array.from(document.querySelectorAll(".calendar-day")).find(day => !day.classList.contains("calendar-day--weekend"));
    const popupDetailSample = window.MyTVHubSharedModules?.popupController?.renderMediaDetailBlockHtml?.({
      kind: "episode",
      primary: "Abbott Elementary",
      secondary: "Team Building",
      meta: "S05E01 • 22 min",
      date: "Oct 1, 2025",
      overview: "The teachers prepare for the upcoming school year with new faces and big changes on the horizon."
    }) || "";
    const queueBefore = JSON.parse(localStorage.getItem("mytv_watch_sync_queue_v1") || "[]");
    const watchButton = Array.from(document.querySelectorAll('[data-watch-state-action="toggle-watched-status"]')).find(btn => {
      const released = !/not_yet_released|unreleased/.test(btn.getAttribute("data-release-status") || btn.getAttribute("data-watch-availability") || "");
      const hasId = !!(btn.getAttribute("data-tmdb-id") || btn.getAttribute("data-trakt-id") || btn.getAttribute("data-tvdb-id"));
      return released && hasId;
    }) || document.querySelector('[data-watch-state-action="toggle-watched-status"][data-tmdb-id]');
    if (watchButton) watchButton.click();
    await new Promise(resolve => requestAnimationFrame(resolve));
    const queueAfter = JSON.parse(localStorage.getItem("mytv_watch_sync_queue_v1") || "[]");
    const queueBeforeItems = Array.isArray(queueBefore) ? queueBefore : (Array.isArray(queueBefore?.items) ? queueBefore.items : []);
    const queueAfterItems = Array.isArray(queueAfter) ? queueAfter : (Array.isArray(queueAfter?.items) ? queueAfter.items : []);
    const popupButton = document.querySelector("[data-watch-source-open]");
    let popupFocus = { attempted: false, opened: false, focusInside: false, closedByBack: false };
    if (popupButton) {
      popupButton.click();
      await new Promise(resolve => setTimeout(resolve, 500));
      const modal = document.querySelector('#providerBack[style*="flex"] #providerCard, #modalBack[style*="flex"] #modalCard');
      if (modal) {
        document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
        await new Promise(resolve => requestAnimationFrame(resolve));
        const focusInside = modal.contains(document.activeElement);
        document.dispatchEvent(new KeyboardEvent("keydown", { key: "Backspace", bubbles: true }));
        await new Promise(resolve => requestAnimationFrame(resolve));
        popupFocus = { attempted: true, opened: true, focusInside, closedByBack: !document.querySelector('#providerBack[style*="flex"], #modalBack[style*="flex"]') };
      } else {
        popupFocus = { attempted: true, opened: false, focusInside: false, closedByBack: false };
      }
    }
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
      calendarItemImages: visibleCalendarItems.filter(el => el.querySelector(".media-card__poster img, .imgbox img")).length,
      calendarDuplicateDateCount: document.querySelectorAll(".calendar-day__date").length,
      calendarWeekendStyled: !!weekendDay && !!weekdayDay && getComputedStyle(weekendDay).backgroundColor !== getComputedStyle(weekdayDay).backgroundColor,
      calendarEpisodePosterImages,
      calendarAlignment,
      watchedStatusValues: (document.documentElement.getAttribute("data-watched-status-values") || "").split(",").filter(Boolean),
      watchQueueBefore: queueBeforeItems.length,
      watchQueueAfter: queueAfterItems.length,
      watchQueueHasQueuedRecord: queueAfterItems.some(item => item && item.sync_status === "queued" && (item.item_key || item.id || item.state_key) && item.previous_value != null && item.new_value != null && item.ids && (item.ids.tmdb || item.ids.trakt || item.ids.tvdb || item.ids.imdb)),
      popupDetailOk: /Abbott Elementary/.test(popupDetailSample) && /Team Building/.test(popupDetailSample) && /S05E01 • 22 min/.test(popupDetailSample) && /Oct 1, 2025/.test(popupDetailSample) && /The teachers prepare/.test(popupDetailSample),
      popupFocus
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
    if (viewport.name === "android-tv-1080p" || viewport.name === "laptop") {
      results.push(await inspect("manage_watch_state.html", viewport));
    }
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
    if (result.pathname === "calendar.html" && result.calendarAlignment?.some(pair => pair.missingDay || pair.leftDelta > 1 || pair.rightDelta > 1 || pair.widthDelta > 1)) {
      failures.push(`${result.viewport} calendar.html: header/day column bounds misaligned`);
    }
    if (result.pathname === "calendar.html" && result.calendarDuplicateDateCount !== 0) failures.push(`${result.viewport} calendar.html: duplicate date row rendered`);
    if (result.pathname === "calendar.html" && !result.calendarWeekendStyled) failures.push(`${result.viewport} calendar.html: weekend styling missing`);
    if (result.pathname === "calendar.html" && result.calendarEpisodePosterImages > 0) failures.push(`${result.viewport} calendar.html: episode calendar image uses poster`);
    if (result.pathname === "index.html" && !result.watchedStatusValues.includes("partial")) failures.push(`${result.viewport} index.html: watched_status missing partial`);
    if (result.pathname === "index.html" && !result.watchQueueHasQueuedRecord) failures.push(`${result.viewport} index.html: watch-state click did not create/update queued event`);
    if (result.pathname === "index.html" && !result.popupDetailOk) failures.push(`${result.viewport} index.html: Abbott-style popup detail sample missing required fields`);
    if (result.viewport === "android-tv-1080p" && result.pathname === "index.html" && result.popupFocus.attempted && (!result.popupFocus.opened || !result.popupFocus.focusInside || !result.popupFocus.closedByBack)) {
      failures.push(`${result.viewport} index.html: popup D-pad focus trap/back close failed`);
    }
  }
  console.log(JSON.stringify({ results, failures }, null, 2));
  if (failures.length) process.exitCode = 1;
} finally {
  await browser.close();
}
