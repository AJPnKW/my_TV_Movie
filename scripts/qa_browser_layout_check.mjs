import puppeteer from "puppeteer-core";
import { readFileSync } from "node:fs";

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
  await page.evaluateOnNewDocument(() => {
    try { localStorage.setItem("mytv_runtime_mode", "full"); } catch (_) {}
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
    const calendarScroller = document.querySelector(".calendar-scroller");
    const calendarBand = document.querySelector(".calendar-week-header, .calendar-week-band");
    const calendarBody = document.querySelector(".calendar-week-body");
    const appHeader = document.querySelector(".top");
    const visibleCalendarItems = Array.from(document.querySelectorAll(".calendar-item")).filter(el => getComputedStyle(el).display !== "none" && !el.classList.contains("hidden"));
    const firstRect = firstCard?.getBoundingClientRect();
    const imageRect = firstImg?.getBoundingClientRect();
    const firstWeekHeaders = calendarBand ? Array.from(calendarBand.querySelectorAll(".calendar-week-band__day")).map(rect) : [];
    const firstWeekDays = calendarBody ? Array.from(calendarBody.querySelectorAll(":scope > .calendar-day")).slice(0, 7).map(rect) : Array.from(document.querySelectorAll(".calendar-month-grid > .calendar-day")).slice(0, 7).map(rect);
    const dayWidths = firstWeekDays.map(day => day?.width || 0);
    const dayWidthDelta = dayWidths.length ? Math.max(...dayWidths) - Math.min(...dayWidths) : 0;
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
    const calendarEpisodeNonStillImages = Array.from(document.querySelectorAll(".calendar-item.media-card--episode img")).filter(img => {
      const src = img.getAttribute("src") || "";
      return src && !/\/stills\/episodes\//i.test(src) && !/^data:image\/svg\+xml/i.test(src);
    }).length;
    const weekendDay = document.querySelector(".calendar-day--weekend");
    const weekdayDay = Array.from(document.querySelectorAll(".calendar-day")).find(day => !day.classList.contains("calendar-day--weekend"));
    const weekendHeaderDay = document.querySelector(".calendar-week-band__day.is-weekend");
    const weekdayHeaderDay = Array.from(document.querySelectorAll(".calendar-week-band__day")).find(day => !day.classList.contains("is-weekend"));
    const calendarHeaderRect = rect(calendarBand);
    const firstCalendarDayRect = firstWeekDays[0] || null;
    const calendarCrossingCards = Array.from(document.querySelectorAll(".calendar-day")).flatMap(day => {
      const dayRect = day.getBoundingClientRect();
      return Array.from(day.querySelectorAll(".calendar-item, .more-toggle")).filter(card => {
        const style = getComputedStyle(card);
        const cardRect = card.getBoundingClientRect();
        return style.display !== "none" && style.visibility !== "hidden" && cardRect.width > 0 && cardRect.height > 0;
      }).map(card => {
        const cardRect = card.getBoundingClientRect();
        return {
          day: day.getAttribute("data-daycell") || "",
          className: card.className || "",
          leftOverflow: Math.max(0, dayRect.left - cardRect.left),
          rightOverflow: Math.max(0, cardRect.right - dayRect.right),
          widthOverflow: Math.max(0, cardRect.width - dayRect.width)
        };
      }).filter(hit => hit.leftOverflow > 1 || hit.rightOverflow > 1 || hit.widthOverflow > 1);
    });
    const calendarFloatingNav = Array.from(document.querySelectorAll("#calendar .floating-nav__btn")).filter(btn => !btn.hidden && !btn.disabled).map(btn => btn.getAttribute("data-floating-nav"));
    const calendarHeaderOverlaysCards = !!(calendarHeaderRect && firstCalendarDayRect && calendarHeaderRect.bottom > firstCalendarDayRect.top + 1);
    const sectionHeaderOverlaysCards = Array.from(document.querySelectorAll('[data-sticky-section-head="1"], #panel-calendar > .dashhead')).some(head => {
      const headRect = rect(head);
      const scope = head.parentElement;
      const content = scope?.querySelector?.(".media-card, .dashgrid, .dashrow, .calendar-scroller, .watch-state-matrix-wrap");
      const contentRect = content ? rect(content) : null;
      return !!(headRect && contentRect && headRect.bottom > contentRect.top + 1);
    });
    const canScroll = document.documentElement.scrollHeight > window.innerHeight + 100;
    const headerPosition = appHeader ? getComputedStyle(appHeader).position : "";
    let headerAfterScrollTop = null;
    if (canScroll) {
      window.scrollTo(0, Math.min(520, document.documentElement.scrollHeight - window.innerHeight));
      await new Promise(resolve => requestAnimationFrame(resolve));
      headerAfterScrollTop = rect(appHeader)?.top ?? null;
      window.scrollTo(0, 0);
      await new Promise(resolve => requestAnimationFrame(resolve));
    }
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
    let providerBlockedLinks = [];
    let watchPopupContract = { attempted: false };
    if (popupButton) {
      popupButton.click();
      await new Promise(resolve => setTimeout(resolve, 900));
      const visibleModalHost = Array.from(document.querySelectorAll("#providerBack, #modalBack")).find(host => {
        const style = getComputedStyle(host);
        return style.display !== "none" && style.visibility !== "hidden";
      });
      const modal = visibleModalHost?.querySelector("#providerCard, #modalCard");
      if (modal) {
        const title = modal.querySelector("#providerTitle, #modalTitle")?.textContent?.trim() || "";
        const bodyText = modal.textContent || "";
        const labels = Array.from(modal.querySelectorAll(".watch-source-panel__title")).map(node => node.textContent.trim());
        const providerRows = Array.from(modal.querySelectorAll(".providerrow,.watch-source-row,.provider-link-row"));
        const providerCountryRows = Array.from(modal.querySelectorAll(".providerrow"));
        const providerRowProof = providerCountryRows.map(row => {
          const label = row.querySelector(".providerlabel");
          const chips = row.querySelector(".providerchips");
          const anchors = Array.from(row.querySelectorAll("a.provider-anchor[href]"));
          const labelRect = label?.getBoundingClientRect?.();
          const chipsRect = chips?.getBoundingClientRect?.();
          const style = getComputedStyle(row);
          return {
            country: label?.textContent?.trim() || "",
            display: style.display,
            gridTemplateColumns: style.gridTemplateColumns,
            height: row.getBoundingClientRect().height,
            anchorCount: anchors.length,
            text: anchors.map(anchor => anchor.textContent.trim()).filter(Boolean),
            hrefs: anchors.map(anchor => anchor.href).filter(Boolean),
            visibleUrls: anchors.map(anchor => anchor.textContent.trim()).filter(text => /^https?:\/\//i.test(text) || /themoviedb\.org|image\.tmdb\.org/i.test(text)),
            stacked: !!(labelRect && chipsRect && chipsRect.top > labelRect.bottom + 2),
            buttonLikeAnchors: anchors.filter(anchor => {
              const anchorStyle = getComputedStyle(anchor);
              return anchor.matches("button,.calbtn,[role='button']") ||
                (parseFloat(anchorStyle.borderTopWidth) || 0) > 0 ||
                (parseFloat(anchorStyle.borderLeftWidth) || 0) > 0 ||
                (anchorStyle.backgroundColor && !/rgba\(0,\s*0,\s*0,\s*0\)|transparent/i.test(anchorStyle.backgroundColor));
            }).map(anchor => anchor.textContent.trim() || anchor.getAttribute("aria-label") || ""),
            missingLogoAnchors: anchors.filter(anchor => !anchor.classList.contains("no-logo") && !anchor.querySelector("img.providerlogo")).map(anchor => anchor.getAttribute("aria-label") || anchor.textContent.trim())
          };
        });
        const filenameCopy = modal.querySelector(".generated-filename-line [data-copy-watch-filename]");
        const filenameDisplayed = filenameCopy?.textContent?.trim() || "";
        const filenameCopyValue = filenameCopy?.getAttribute("data-copy-watch-filename") || "";
        let copiedFilename = "";
        if (filenameCopy) {
          try {
            Object.defineProperty(navigator, "clipboard", {
              configurable: true,
              value: { writeText: async (value) => { copiedFilename = String(value || ""); } }
            });
          } catch (_) {
            navigator.clipboard = { writeText: async (value) => { copiedFilename = String(value || ""); } };
          }
          filenameCopy.click();
          await new Promise(resolve => setTimeout(resolve, 80));
        }
        const outlinedRows = providerRows.filter(row => {
          const style = getComputedStyle(row);
          return (parseFloat(style.borderTopWidth) || 0) > 0 || (parseFloat(style.borderLeftWidth) || 0) > 0;
        }).length;
        const close = modal.querySelector("#providerClose,#modalClose");
        const closeStyle = close ? getComputedStyle(close.closest(".app-modal-header") || close) : null;
        watchPopupContract = {
          attempted: true,
          titleOk: /^Watch • .+ • .+ • S\d{2}E\d{2}$/.test(title) || /^Watch • .+/.test(title),
          labelsOk: labels.includes("Streaming") && labels.includes("Providers") && !labels.includes("Watch now") && !labels.includes("Where to watch"),
          noAdminText: !/(ACTIVE CANDIDATE FROM USER FINDINGS|\bACTIVE\b|\bDEGRADED\b|\bBLOCKED\b|\bARCHIVED\b)/i.test(bodyText),
          outlinedRows,
          providerRows: providerRowProof,
          providerVisibleUrlCount: providerRowProof.reduce((sum, row) => sum + row.visibleUrls.length, 0),
          providerStackedRowCount: providerRowProof.filter(row => row.stacked).length,
          providerButtonLikeAnchorCount: providerRowProof.reduce((sum, row) => sum + row.buttonLikeAnchors.length, 0),
          providerMissingLogoCount: providerRowProof.reduce((sum, row) => sum + row.missingLogoAnchors.length, 0),
          providerHasCountryRows: providerRowProof.filter(row => row.country && row.anchorCount > 0).length >= 1,
          filenameDisplayed,
          filenameCopyValue,
          copiedFilename,
          filenameOk: !!filenameCopy && !!modal.querySelector(".generated-filename-line") && /\[\d{2}-\d{2}-\d{2}\]/.test(filenameDisplayed) && /\[\d+\]/.test(filenameDisplayed) && filenameDisplayed === filenameCopyValue && copiedFilename === filenameDisplayed,
          stickyExitOk: !!close && close.textContent.trim() === "Exit" && closeStyle?.position === "sticky",
          refOk: /REF: POP-WATCH-SOURCE/.test(bodyText),
          episodeTmdbOk: /TMDB:\s*\d+|\d+\s*•\s*\d+\s*min/.test(bodyText)
        };
        providerBlockedLinks = Array.from(modal.querySelectorAll("a[href]"))
          .map(link => link.href)
          .filter(href => /smashystream\.com|2embed\.org|superembed\.stream|multiembed\.mov/i.test(href));
        document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
        await new Promise(resolve => requestAnimationFrame(resolve));
        const focusInside = modal.contains(document.activeElement);
        document.dispatchEvent(new KeyboardEvent("keydown", { key: "Backspace", bubbles: true }));
        await new Promise(resolve => requestAnimationFrame(resolve));
        const stillOpen = Array.from(document.querySelectorAll("#providerBack, #modalBack")).some(host => {
          const style = getComputedStyle(host);
          return style.display !== "none" && style.visibility !== "hidden";
        });
        popupFocus = { attempted: true, opened: true, focusInside, closedByBack: !stillOpen };
      } else {
        popupFocus = { attempted: true, opened: false, focusInside: false, closedByBack: false };
        watchPopupContract = { attempted: true, titleOk: false, labelsOk: false, noAdminText: false, outlinedRows: 0, filenameOk: false, stickyExitOk: false, refOk: false, episodeTmdbOk: false };
      }
    }
    const mediaLibraryIcon = document.querySelector("#mediaLibraryHeaderButton");
    const mediaLibraryNavOk = !!mediaLibraryIcon && mediaLibraryIcon.parentElement?.matches(".top > .nav[role='tablist'][aria-label='Primary']") && mediaLibraryIcon.target === "_blank";
    const modeSelect = document.querySelector("#runtimeModeSelect");
    if (modeSelect) {
      modeSelect.value = "light";
      modeSelect.dispatchEvent(new Event("change", { bubbles: true }));
      await new Promise(resolve => setTimeout(resolve, 600));
    }
    const lightModeImages = Array.from(document.querySelectorAll("img[src]")).filter(img => !img.closest(".logo")).map(img => img.getAttribute("src") || "");
    return {
      bodyOverflow,
      cardWidth: Math.round(firstRect?.width || 0),
      cardHeight: Math.round(firstRect?.height || 0),
      imageWidth: Math.round(imageRect?.width || 0),
      imageHeight: Math.round(imageRect?.height || 0),
      dashboardColumns: dashCols ? getComputedStyle(dashCols).gridTemplateColumns.split(" ").filter(Boolean).length : 0,
      calendarColumns: calendarBody ? getComputedStyle(calendarBody).gridTemplateColumns.split(" ").filter(Boolean).length : (calendarGrid ? getComputedStyle(calendarGrid).gridTemplateColumns.split(" ").filter(Boolean).length : 0),
      calendarBandColumns: calendarBand ? getComputedStyle(calendarBand).gridTemplateColumns.split(" ").filter(Boolean).length : 0,
      calendarRowClientWidth: calendarBody ? calendarBody.clientWidth : 0,
      calendarRowScrollWidth: calendarBody ? calendarBody.scrollWidth : 0,
      calendarScrollerClientWidth: calendarScroller ? calendarScroller.clientWidth : 0,
      calendarScrollerScrollWidth: calendarScroller ? calendarScroller.scrollWidth : 0,
      calendarDayWidthDelta: Math.round(dayWidthDelta * 100) / 100,
      calendarCrossingCards,
      calendarFloatingNav,
      calendarItems: visibleCalendarItems.length,
      calendarItemImages: visibleCalendarItems.filter(el => el.querySelector(".media-card__poster img, .imgbox img")).length,
      calendarDuplicateDateCount: document.querySelectorAll(".calendar-day__date").length,
      calendarWeekendStyled: !!weekendDay && !!weekdayDay && !!weekendHeaderDay && !!weekdayHeaderDay && getComputedStyle(weekendDay).backgroundColor !== getComputedStyle(weekdayDay).backgroundColor && getComputedStyle(weekendHeaderDay).backgroundColor !== getComputedStyle(weekdayHeaderDay).backgroundColor,
      calendarEpisodePosterImages,
      calendarEpisodeNonStillImages,
      calendarAlignment,
      calendarHeaderOverlaysCards,
      sectionHeaderOverlaysCards,
      headerPosition,
      headerAfterScrollTop,
      stickyHeaderOk: headerPosition === "sticky" && (!canScroll || Math.abs(headerAfterScrollTop || 0) <= 1),
      watchedStatusValues: (document.documentElement.getAttribute("data-watched-status-values") || "").split(",").filter(Boolean),
      watchQueueBefore: queueBeforeItems.length,
      watchQueueAfter: queueAfterItems.length,
      watchQueueHasQueuedRecord: queueAfterItems.some(item => item && item.sync_status === "queued" && (item.item_key || item.id || item.state_key) && item.previous_value != null && item.new_value != null && item.ids && (item.ids.tmdb || item.ids.trakt || item.ids.tvdb || item.ids.imdb)),
      popupDetailOk: /Abbott Elementary/.test(popupDetailSample) && /Team Building/.test(popupDetailSample) && /S05E01 • 22 min/.test(popupDetailSample) && /Oct 1, 2025/.test(popupDetailSample) && /The teachers prepare/.test(popupDetailSample),
      providerBlockedLinks,
      popupFocus,
      watchPopupContract,
      mediaLibraryNavOk,
      lightModeImages
    };
  });
  await page.close();
  return { pathname, viewport: viewport.name, errors, missing, ...metrics };
}

async function inspectInteractionCompliance(viewport) {
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

  await page.evaluateOnNewDocument(() => {
    try { localStorage.setItem("mytv_runtime_mode", "full"); } catch (_) {}
  });
  await page.goto(`${BASE_URL}/web/index.html`, { waitUntil: "load", timeout: 60000 });
  await sleep(2500);
  const click = await page.evaluate(async () => {
    localStorage.removeItem("mytv_watch_state_v1");
    localStorage.removeItem("mytv_watch_sync_queue_v1");
    window.MyTVHubWatchState?.refresh?.(document);
    const btn = Array.from(document.querySelectorAll('[data-watch-state-action="toggle-watched-status"][data-kind="movie"][data-tmdb-id]')).find(candidate => {
      const release = candidate.getAttribute("data-release-status") || candidate.getAttribute("data-watch-availability") || "";
      return !/not_yet_released|unreleased/.test(release) && candidate.getAttribute("data-tmdb-id");
    });
    if (!btn) return { found: false };
    const key = btn.getAttribute("data-watch-state-key") || window.MyTVHubWatchState?.contextKey?.("watched_status", {
      kind: "movie",
      id: btn.getAttribute("data-id"),
      tmdb_id: btn.getAttribute("data-tmdb-id")
    });
    const title = btn.getAttribute("data-title") || "";
    const tmdbId = btn.getAttribute("data-tmdb-id") || btn.getAttribute("data-id") || "";
    const iconBefore = btn.querySelector(".actionbar-btn__icon")?.textContent || "";
    const valueBefore = btn.getAttribute("data-watch-state-value") || "";
    const localBefore = JSON.parse(localStorage.getItem("mytv_watch_state_v1") || "{}");
    const queueBefore = JSON.parse(localStorage.getItem("mytv_watch_sync_queue_v1") || "[]");
    btn.click();
    await new Promise(resolve => requestAnimationFrame(resolve));
    const iconAfter = btn.querySelector(".actionbar-btn__icon")?.textContent || "";
    const valueAfter = btn.getAttribute("data-watch-state-value") || "";
    const localAfter = JSON.parse(localStorage.getItem("mytv_watch_state_v1") || "{}");
    const queueAfter = JSON.parse(localStorage.getItem("mytv_watch_sync_queue_v1") || "[]");
    const queueItems = Array.isArray(queueAfter) ? queueAfter : (Array.isArray(queueAfter?.items) ? queueAfter.items : []);
    const beforeItems = Array.isArray(queueBefore) ? queueBefore : (Array.isArray(queueBefore?.items) ? queueBefore.items : []);
    return {
      found: true,
      key,
      title,
      tmdbId,
      iconBefore,
      iconAfter,
      valueBefore,
      valueAfter,
      localBeforeHasKey: Object.prototype.hasOwnProperty.call(localBefore, key),
      localAfterValue: localAfter[key]?.new_value || localAfter[key],
      queueBeforeCount: beforeItems.length,
      queueAfterCount: queueItems.length,
      queueHasKey: queueItems.some(item => (item.item_key || item.key || item.state_key || item.id) === key && item.sync_status === "queued")
    };
  });

  await page.goto(`${BASE_URL}/web/movies.html`, { waitUntil: "load", timeout: 60000 });
  await sleep(2500);
  const crossView = await page.evaluate((proof) => {
    if (!proof?.key) return { checked: false };
    window.MyTVHubWatchState?.refresh?.(document);
    const btn = Array.from(document.querySelectorAll('[data-watch-state-action="toggle-watched-status"]')).find(candidate => candidate.getAttribute("data-watch-state-key") === proof.key);
    return {
      checked: true,
      found: !!btn,
      value: btn?.getAttribute("data-watch-state-value") || "",
      icon: btn?.querySelector(".actionbar-btn__icon")?.textContent || ""
    };
  }, click);

  let actionViews = [];

  await page.goto(`${BASE_URL}/web/manage_watch_state.html`, { waitUntil: "load", timeout: 60000 });
  await sleep(2500);
  const manage = await page.evaluate(async (proof) => {
    const out = {
      rowMatchesClick: false,
      searchWorks: false,
      pageSizeWorks: false,
      paginationWorks: false,
      sortingWorks: false,
      inlineEditWorks: false
    };
    const waitFrame = () => new Promise(resolve => requestAnimationFrame(resolve));
    if (!proof?.key) return out;
    const pageSize = document.querySelector("[data-manage-watch-page-size]");
    if (pageSize) {
      pageSize.value = "10";
      pageSize.dispatchEvent(new Event("change", { bubbles: true }));
      await waitFrame();
      out.pageSizeWorks = document.querySelector("#manageWatchState")?.getAttribute("data-watch-state-page-size") === "10";
    }
    const last = document.querySelector('[data-manage-watch-page="last"]');
    const first = document.querySelector('[data-manage-watch-page="first"]');
    if (last && first) {
      last.click();
      await waitFrame();
      const afterLast = document.querySelector(".watch-state-pager__label")?.textContent || "";
      document.querySelector('[data-manage-watch-page="first"]')?.click();
      await waitFrame();
      const afterFirst = document.querySelector(".watch-state-pager__label")?.textContent || "";
      out.paginationWorks = afterLast !== afterFirst || !!last.disabled;
    }
    const search = document.querySelector("[data-manage-watch-search]");
    if (search) {
      search.value = (proof.title || proof.tmdbId || "movie").slice(0, 6);
      search.dispatchEvent(new Event("input", { bubbles: true }));
      await waitFrame();
      out.searchWorks = !!document.querySelector("[data-manage-watch-search]") && document.querySelectorAll(".watch-state-matrix tbody tr").length > 0;
      const active = Array.from(document.querySelectorAll(`[data-manage-watch-key="${CSS.escape(proof.key)}"]`)).find(btn => btn.getAttribute("aria-pressed") === "true");
      out.rowMatchesClick = !!active && active.getAttribute("data-manage-watch-value") === proof.valueAfter;
    }
    const sort = document.querySelector('[data-manage-watch-sort="title"]');
    if (sort) {
      const before = sort.getAttribute("aria-sort");
      sort.click();
      await waitFrame();
      const after = document.querySelector('[data-manage-watch-sort="title"]')?.getAttribute("aria-sort");
      out.sortingWorks = !!after && after !== before;
    }
    const queueBefore = JSON.parse(localStorage.getItem("mytv_watch_sync_queue_v1") || "[]");
    const beforeItems = Array.isArray(queueBefore) ? queueBefore : (Array.isArray(queueBefore?.items) ? queueBefore.items : []);
    const watchListKey = `watch_list:movie:${proof.tmdbId}`;
    const inline = document.querySelector(`[data-manage-watch-key="${CSS.escape(watchListKey)}"]`);
    if (inline) {
      inline.click();
      await waitFrame();
      const local = JSON.parse(localStorage.getItem("mytv_watch_state_v1") || "{}");
      const queueAfter = JSON.parse(localStorage.getItem("mytv_watch_sync_queue_v1") || "[]");
      const afterItems = Array.isArray(queueAfter) ? queueAfter : (Array.isArray(queueAfter?.items) ? queueAfter.items : []);
      out.inlineEditWorks = local[watchListKey]?.new_value === "on" && afterItems.length >= beforeItems.length && afterItems.some(item => (item.item_key || item.key || item.state_key || item.id) === watchListKey);
    }
    return out;
  }, click);

  for (const viewPath of ["index.html", "calendar.html", "shows.html", "movies.html"]) {
    await page.goto(`${BASE_URL}/web/${viewPath}`, { waitUntil: "load", timeout: 60000 });
    await sleep(2500);
    await page.waitForFunction(() => document.querySelector('[data-watch-state-action]') || document.querySelector('[data-show-open]'), { timeout: 12000 }).catch(() => {});
    await sleep(viewPath === "shows.html" ? 1250 : 250);
    actionViews.push(await page.evaluate(async (viewPath) => {
      window.MyTVHubWatchState?.refresh?.(document);
      if (viewPath === "shows.html" && !document.querySelector('[data-watch-state-action]')) {
        document.querySelector("[data-show-open]")?.click();
        await new Promise(resolve => setTimeout(resolve, 2500));
        window.MyTVHubWatchState?.refresh?.(document);
      }
      const result = { viewPath, checked: true, actions: [] };
      const types = ["toggle-watched-status", "toggle-watch-list", "toggle-favourite"];
      for (const action of types) {
        const btn = Array.from(document.querySelectorAll(`[data-watch-state-action="${action}"]`)).find(candidate => {
          const release = candidate.getAttribute("data-release-status") || candidate.getAttribute("data-watch-availability") || "";
          const key = candidate.getAttribute("data-watch-state-key");
          const hasId = candidate.getAttribute("data-tmdb-id") || candidate.getAttribute("data-trakt-id") || candidate.getAttribute("data-tvdb-id") || (viewPath === "shows.html" && key);
          return key && hasId && !/not_yet_released|unreleased/.test(release);
        });
        if (!btn) {
          result.actions.push({ action, found: false });
          continue;
        }
        const key = btn.getAttribute("data-watch-state-key");
        const iconBefore = btn.querySelector(".actionbar-btn__icon")?.textContent || "";
        const valueBefore = btn.getAttribute("data-watch-state-value") || "";
        const queueBefore = JSON.parse(localStorage.getItem("mytv_watch_sync_queue_v1") || "[]");
        const beforeItems = Array.isArray(queueBefore) ? queueBefore : (Array.isArray(queueBefore?.items) ? queueBefore.items : []);
        btn.click();
        await new Promise(resolve => requestAnimationFrame(resolve));
        const queueAfter = JSON.parse(localStorage.getItem("mytv_watch_sync_queue_v1") || "[]");
        const afterItems = Array.isArray(queueAfter) ? queueAfter : (Array.isArray(queueAfter?.items) ? queueAfter.items : []);
        const localAfter = JSON.parse(localStorage.getItem("mytv_watch_state_v1") || "{}");
        const iconAfter = btn.querySelector(".actionbar-btn__icon")?.textContent || "";
        const valueAfter = btn.getAttribute("data-watch-state-value") || "";
        result.actions.push({
          action,
          found: true,
          key,
          iconBefore,
          iconAfter,
          valueBefore,
          valueAfter,
          localAfterValue: localAfter[key]?.new_value || localAfter[key],
          queueCountBefore: beforeItems.length,
          queueCountAfter: afterItems.length,
          queueHasKey: afterItems.some(item => (item.item_key || item.key || item.state_key || item.id) === key)
        });
      }
      result.ok = result.actions.every(item => item.found && item.valueAfter !== item.valueBefore && item.localAfterValue === item.valueAfter && item.queueHasKey);
      return result;
    }, viewPath));
  }

  await page.goto(`${BASE_URL}/web/shows.html`, { waitUntil: "load", timeout: 60000 });
  await sleep(2500);
  const carousel = await page.evaluate(async () => {
    const opener = document.querySelector("[data-show-open]");
    if (!opener) return { checked: false, opened: false };
    opener.click();
    await new Promise(resolve => setTimeout(resolve, 1000));
    const modal = document.querySelector('#modalBack[style*="flex"] #modalCard');
    const title = modal?.querySelector(".popup-hero__title")?.textContent?.trim() || "";
    const carousel = modal?.querySelector('.episode-carousel[data-manual-carousel="episodes"]');
    const season = carousel?.querySelector(".carousel-context")?.textContent?.trim() || modal?.querySelector(".seasonname")?.textContent?.trim() || "";
    const prev = carousel?.querySelector('[data-ep-nav="prev"]');
    const next = carousel?.querySelector('[data-ep-nav="next"]');
    const header = carousel?.querySelector(".episode-carousel-header");
    const controls = carousel?.querySelector(".episode-carousel-controls");
    const viewport = carousel?.querySelector(".episode-carousel-viewport");
    const track = carousel?.querySelector(".episode-carousel-track");
    const cards = Array.from(track?.querySelectorAll(".episode-card") || []);
    const viewportStyle = viewport ? getComputedStyle(viewport) : null;
    const carouselStyle = carousel ? getComputedStyle(carousel) : null;
    const viewportRect = viewport?.getBoundingClientRect();
    const visibleCards = viewportRect ? cards.filter(card => {
      const rect = card.getBoundingClientRect();
      return rect.width > 0 && rect.right > viewportRect.left + 4 && rect.left < viewportRect.right - 4;
    }) : [];
    const cardWidths = cards.slice(0, 5).map(card => Math.round(card.getBoundingClientRect().width));
    const summariesVisible = cards.some(card => {
      const summary = card.querySelector(".media-card__summary");
      if (!summary) return false;
      const style = getComputedStyle(summary);
      const rect = summary.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && rect.height > 2;
    });
    const widgetFrame = !!carouselStyle && parseFloat(carouselStyle.borderTopWidth) > 0 && parseFloat(carouselStyle.borderRadius) >= 8;
    const viewportFrame = !!viewportStyle && parseFloat(viewportStyle.borderTopWidth) > 0 && parseFloat(viewportStyle.borderRadius) >= 8;
    const viewportClipsTrack = !!viewport && viewport.scrollWidth > viewport.clientWidth && ["auto", "scroll"].includes(viewportStyle?.overflowX);
    const before = viewport?.scrollLeft || 0;
    const floatingBefore = Array.from(carousel?.querySelectorAll(".floating-nav__btn") || []).filter(btn => !btn.hidden && !btn.disabled).map(btn => btn.getAttribute("data-floating-nav"));
    next?.click();
    await new Promise(resolve => setTimeout(resolve, 500));
    const afterClick = viewport?.scrollLeft || 0;
    viewport?.focus();
    carousel?.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
    await new Promise(resolve => setTimeout(resolve, 500));
    const afterDpad = viewport?.scrollLeft || 0;
    const floating = Array.from(carousel?.querySelectorAll(".floating-nav__btn") || []).filter(btn => !btn.hidden && !btn.disabled).map(btn => btn.getAttribute("data-floating-nav"));
    const contextAfter = carousel?.querySelector(".carousel-context")?.textContent?.trim() || "";
    return {
      checked: true,
      opened: !!modal,
      title,
      season,
      prevNext: !!prev && !!next,
      shell: !!carousel && !!header && !!controls,
      track: !!track,
      viewport: !!viewport,
      cardWidths,
      visibleCardCount: visibleCards.length,
      summariesVisible,
      widgetFrame,
      viewportFrame,
      viewportClipsTrack,
      movedByClick: afterClick > before,
      movedByDpad: afterDpad < afterClick,
      retainedContext: !!title && !!season && contextAfter === season,
      floatingBefore,
      floating
    };
  });

  await page.close();
  return { pathname: "interaction-contract", viewport: viewport.name, errors, missing, click, crossView, actionViews, manage, carousel };
}

function providerRegistryProof() {
  const registry = JSON.parse(readFileSync("data/provider_registry.json", "utf8"));
  const providers = Array.isArray(registry.providers) ? registry.providers : [];
  const byDomain = Object.fromEntries(providers.map(item => [item.domain, item]));
  return {
    exists: true,
    count: providers.length,
    blocked: ["smashystream.com", "2embed.org", "superembed.stream", "multiembed.mov"].every(domain => byDomain[domain]?.status === "blocked"),
    active: ["vidsrc.net", "2embed.cc"].every(domain => byDomain[domain]?.status === "active"),
    fields: providers.every(item => ["provider_id","domain","url_pattern","status","last_tested","tls_status","redirect_status","final_domain","notes"].every(field => Object.prototype.hasOwnProperty.call(item, field)))
  };
}

try {
  const results = [];
  const interactionResults = [];
  for (const viewport of VIEWPORTS) {
    results.push(await inspect("index.html", viewport));
    results.push(await inspect("calendar.html", viewport));
    if (viewport.name === "android-tv-1080p" || viewport.name === "laptop") {
      results.push(await inspect("manage_watch_state.html", viewport));
      interactionResults.push(await inspectInteractionCompliance(viewport));
    }
  }
  const failures = [];
  const providerProof = providerRegistryProof();
  if (!providerProof.exists || !providerProof.fields || !providerProof.blocked || !providerProof.active) failures.push("provider registry classification/fields failed");
  for (const result of results) {
    if (result.errors.length) failures.push(`${result.viewport} ${result.pathname}: console errors`);
    if (result.missing.length) failures.push(`${result.viewport} ${result.pathname}: 404 responses`);
    if (result.bodyOverflow) failures.push(`${result.viewport} ${result.pathname}: page-level horizontal overflow`);
    const minCardWidth = result.pathname === "calendar.html" && result.viewport.startsWith("phone") ? 120 : 128;
    if (result.cardWidth > 0 && result.cardWidth < minCardWidth) failures.push(`${result.viewport} ${result.pathname}: card width too narrow (${result.cardWidth}px)`);
    if (result.imageWidth > 0 && result.imageWidth < 90) failures.push(`${result.viewport} ${result.pathname}: image width too narrow (${result.imageWidth}px)`);
    if ((result.viewport === "android-tv-1080p" || result.viewport === "laptop") && result.pathname === "calendar.html" && result.calendarAlignment?.length && result.calendarAlignment.length !== 7) {
      failures.push(`${result.viewport} calendar.html: expected 7 aligned calendar columns, found ${result.calendarAlignment.length}`);
    }
    if ((result.viewport === "android-tv-1080p" || result.viewport === "laptop") && result.pathname === "calendar.html" && result.calendarItems > 0 && result.calendarItemImages < result.calendarItems) {
      failures.push(`${result.viewport} calendar.html: calendar episode/movie cards missing images (${result.calendarItemImages}/${result.calendarItems})`);
    }
    if (result.pathname === "calendar.html" && result.calendarAlignment?.some(pair => pair.missingDay || pair.leftDelta > 1 || pair.rightDelta > 1 || pair.widthDelta > 1)) {
      failures.push(`${result.viewport} calendar.html: header/day column bounds misaligned`);
    }
    if (result.pathname === "calendar.html" && result.calendarDayWidthDelta > 1) failures.push(`${result.viewport} calendar.html: day cells have unequal widths`);
    if (result.pathname === "calendar.html" && result.calendarCrossingCards?.length) failures.push(`${result.viewport} calendar.html: calendar card or +more crosses day cell boundary`);
    if ((result.viewport === "tablet-portrait" || result.viewport.startsWith("phone")) && result.pathname === "calendar.html" && !result.calendarFloatingNav?.includes("right")) failures.push(`${result.viewport} calendar.html: floating right nav missing for scrollable calendar`);
    if (result.pathname === "calendar.html" && result.calendarHeaderOverlaysCards && !result.calendarAlignment?.length) failures.push(`${result.viewport} calendar.html: calendar header overlays first row`);
    if (result.sectionHeaderOverlaysCards) failures.push(`${result.viewport} ${result.pathname}: section header overlays cards`);
    if (!result.stickyHeaderOk) failures.push(`${result.viewport} ${result.pathname}: sticky app header failed on scroll`);
    if (result.pathname === "calendar.html" && result.calendarDuplicateDateCount !== 0) failures.push(`${result.viewport} calendar.html: duplicate date row rendered`);
    if (result.pathname === "calendar.html" && result.calendarWeekendStyled === false && !result.calendarAlignment?.length) failures.push(`${result.viewport} calendar.html: weekend styling missing`);
    if (result.pathname === "calendar.html" && result.calendarEpisodePosterImages > 0) failures.push(`${result.viewport} calendar.html: episode calendar image uses poster`);
    if (result.pathname === "calendar.html" && result.calendarEpisodeNonStillImages > 0) failures.push(`${result.viewport} calendar.html: episode calendar image is not still/placeholder`);
    if (result.pathname === "index.html" && !result.watchedStatusValues.includes("partial")) failures.push(`${result.viewport} index.html: watched_status missing partial`);
    if (result.pathname === "index.html" && !result.watchQueueHasQueuedRecord) failures.push(`${result.viewport} index.html: watch-state click did not create/update queued event`);
    if (result.pathname === "index.html" && !result.popupDetailOk) failures.push(`${result.viewport} index.html: Abbott-style popup detail sample missing required fields`);
    if (result.watchPopupContract?.attempted && (!result.watchPopupContract.titleOk || !result.watchPopupContract.labelsOk || !result.watchPopupContract.noAdminText || result.watchPopupContract.outlinedRows > 0 || result.watchPopupContract.providerVisibleUrlCount > 0 || result.watchPopupContract.providerStackedRowCount > 0 || result.watchPopupContract.providerButtonLikeAnchorCount > 0 || result.watchPopupContract.providerMissingLogoCount > 0 || !result.watchPopupContract.providerHasCountryRows || !result.watchPopupContract.filenameOk || !result.watchPopupContract.stickyExitOk || !result.watchPopupContract.refOk || !result.watchPopupContract.episodeTmdbOk)) {
      failures.push(`${result.viewport} ${result.pathname}: Watch Source popup contract failed`);
    }
    if (result.providerBlockedLinks?.length) failures.push(`${result.viewport} ${result.pathname}: blocked provider visible as active`);
    if (!result.mediaLibraryNavOk) failures.push(`${result.viewport} ${result.pathname}: Media Library icon outside primary nav or not new-tab`);
    if (result.lightModeImages?.length) failures.push(`${result.viewport} ${result.pathname}: Light mode still has image src values`);
    if (result.viewport === "android-tv-1080p" && result.pathname === "index.html" && result.popupFocus.attempted && (!result.popupFocus.opened || !result.popupFocus.focusInside || !result.popupFocus.closedByBack)) {
      failures.push(`${result.viewport} index.html: popup D-pad focus trap/back close failed`);
    }
  }
  for (const result of interactionResults) {
    if (result.errors.length) failures.push(`${result.viewport} interaction: console errors`);
    if (result.missing.length) failures.push(`${result.viewport} interaction: 404 responses`);
    if (!result.click?.found) failures.push(`${result.viewport} interaction: no clickable movie watched_status action found`);
    if (result.click?.found && result.click.iconBefore === result.click.iconAfter) failures.push(`${result.viewport} interaction: watched_status icon did not change`);
    if (result.click?.found && result.click.localAfterValue !== result.click.valueAfter) failures.push(`${result.viewport} interaction: local state did not match clicked value`);
    if (result.click?.found && !result.click.queueHasKey) failures.push(`${result.viewport} interaction: queued state record missing for clicked item`);
    if (result.crossView?.checked && (!result.crossView.found || result.crossView.value !== result.click.valueAfter)) failures.push(`${result.viewport} interaction: clicked movie state not consistent in Movies view`);
    if (!result.actionViews?.length || result.actionViews.some(view => !view.ok)) failures.push(`${result.viewport} interaction: action clicks inconsistent across Dashboard/Calendar/Shows/Movies`);
    if (!result.manage?.rowMatchesClick) failures.push(`${result.viewport} interaction: Manage Watch State row did not reflect clicked item`);
    if (!result.manage?.searchWorks) failures.push(`${result.viewport} interaction: Manage Watch State search failed`);
    if (!result.manage?.pageSizeWorks) failures.push(`${result.viewport} interaction: Manage Watch State page size failed`);
    if (!result.manage?.paginationWorks) failures.push(`${result.viewport} interaction: Manage Watch State first/prev/next/last pagination failed`);
    if (!result.manage?.sortingWorks) failures.push(`${result.viewport} interaction: Manage Watch State column sorting failed`);
    if (!result.manage?.inlineEditWorks) failures.push(`${result.viewport} interaction: Manage Watch State inline edit failed`);
    if (!result.carousel?.opened || !result.carousel?.shell || !result.carousel?.prevNext || !result.carousel?.viewport || !result.carousel?.track || !result.carousel?.retainedContext) failures.push(`${result.viewport} interaction: episode carousel shell/controls/context failed`);
    if (result.carousel?.opened && (!result.carousel?.widgetFrame || !result.carousel?.viewportFrame || !result.carousel?.viewportClipsTrack)) failures.push(`${result.viewport} interaction: episode carousel is not rendered as a framed clipped widget`);
    if (result.carousel?.opened && result.carousel?.summariesVisible) failures.push(`${result.viewport} interaction: episode carousel still shows long row-style summaries`);
    if (result.carousel?.opened && result.carousel?.visibleCardCount > 4) failures.push(`${result.viewport} interaction: episode carousel exposes too many cards like a plain row`);
    if (result.carousel?.opened && result.carousel?.cardWidths?.some(width => Math.abs(width - 240) > 2)) failures.push(`${result.viewport} interaction: episode carousel cards are not narrow-still 240px cards`);
    if (result.carousel?.opened && (!result.carousel?.movedByClick || !result.carousel?.movedByDpad)) failures.push(`${result.viewport} interaction: episode carousel manual/D-pad navigation failed`);
    if (result.carousel?.opened && !result.carousel?.floatingBefore?.includes("right")) failures.push(`${result.viewport} interaction: carousel floating right nav missing before movement`);
    if (result.carousel?.opened && !result.carousel?.floating?.some(dir => dir === "left" || dir === "right")) failures.push(`${result.viewport} interaction: carousel floating horizontal nav missing after movement`);
  }
  console.log(JSON.stringify({ providerProof, results, interactionResults, failures }, null, 2));
  if (failures.length) process.exitCode = 1;
} finally {
  await browser.close();
}
