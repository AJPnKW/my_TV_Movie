const state = {
  channels: [],
  filtered: [],
  sources: null,
  selected: null,
  hls: null,
  guideLoaded: false,
  guidePrograms: new Map(),
  favorites: new Set(JSON.parse(localStorage.getItem("hungary-tv:favorites") || "[]")),
  displayNames: JSON.parse(localStorage.getItem("hungary-tv:names") || "{}"),
  events: JSON.parse(localStorage.getItem("hungary-tv:events") || "[]"),
  worker: null,
};

const el = {};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  bindElements();
  bindEvents();
  setupWorker();
  detectBrowserSupport();
  renderEvents();

  try {
    const [channelPayload, sources] = await Promise.all([
      fetchJson("data/channels.json"),
      fetchJson("data/sources.json"),
    ]);
    state.channels = channelPayload.channels || [];
    state.sources = sources;
    renderSources();
    renderFilters();
    applyFilters();
    logEvent(`Loaded ${state.channels.length} curated Hungary channels.`);
  } catch (error) {
    setScreenState("The channel index could not be loaded.");
    logEvent(`Channel load failed: ${error.message}`);
  }

  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
}

function bindElements() {
  [
    "sourcePills",
    "browserBadge",
    "streamBadge",
    "guideBadge",
    "searchInput",
    "categoryFilter",
    "sortSelect",
    "favoritesOnly",
    "loadGuide",
    "channelCount",
    "channelList",
    "videoPlayer",
    "screenState",
    "playPause",
    "liveEdge",
    "toggleCaptions",
    "pictureInPicture",
    "fullscreen",
    "selectedLogo",
    "selectedName",
    "selectedMeta",
    "renameForm",
    "displayNameInput",
    "favoriteSelected",
    "infoLinks",
    "streamSelect",
    "retryStream",
    "copyStream",
    "statusState",
    "bufferState",
    "captionState",
    "qualityState",
    "guideStatus",
    "programList",
    "sourceGrid",
    "copySourceLinks",
    "exportSettings",
    "clearLog",
    "eventLog",
  ].forEach((id) => {
    el[id] = document.getElementById(id);
  });
}

function bindEvents() {
  el.searchInput.addEventListener("input", applyFilters);
  el.categoryFilter.addEventListener("change", applyFilters);
  el.sortSelect.addEventListener("change", applyFilters);
  el.favoritesOnly.addEventListener("click", () => {
    const active = el.favoritesOnly.getAttribute("aria-pressed") !== "true";
    el.favoritesOnly.setAttribute("aria-pressed", String(active));
    applyFilters();
  });
  el.loadGuide.addEventListener("click", loadGuide);
  el.channelList.addEventListener("click", onChannelClick);
  el.renameForm.addEventListener("submit", saveDisplayName);
  el.favoriteSelected.addEventListener("click", () => toggleFavorite(state.selected?.id));
  el.streamSelect.addEventListener("change", () => loadSelectedStream(false));
  el.retryStream.addEventListener("click", () => loadSelectedStream(true));
  el.copyStream.addEventListener("click", copyCurrentStream);
  el.copySourceLinks.addEventListener("click", copySourceLinks);
  el.exportSettings.addEventListener("click", exportSettings);
  el.clearLog.addEventListener("click", clearEvents);
  el.playPause.addEventListener("click", togglePlay);
  el.liveEdge.addEventListener("click", seekLiveEdge);
  el.toggleCaptions.addEventListener("click", toggleCaptions);
  el.pictureInPicture.addEventListener("click", togglePictureInPicture);
  el.fullscreen.addEventListener("click", toggleFullscreen);

  el.videoPlayer.addEventListener("waiting", () => {
    el.statusState.textContent = "Buffering";
    setScreenState("Buffering...");
  });
  el.videoPlayer.addEventListener("playing", () => {
    el.statusState.textContent = "Playing";
    setScreenState("");
    updateCaptionState();
  });
  el.videoPlayer.addEventListener("pause", () => {
    el.statusState.textContent = "Paused";
  });
  el.videoPlayer.addEventListener("error", () => {
    const message = mediaErrorMessage(el.videoPlayer.error);
    setScreenState(message);
    logEvent(`${displayName(state.selected)} playback error: ${message}`);
  });
  el.videoPlayer.addEventListener("loadedmetadata", updateCaptionState);
  setInterval(updateBufferState, 1500);
}

function setupWorker() {
  if (!window.Worker) return;
  state.worker = new Worker("js/channel_worker.js");
  state.worker.onmessage = (event) => {
    state.filtered = event.data.rows || [];
    renderChannels();
  };
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-cache" });
  if (!response.ok) throw new Error(`${url} returned ${response.status}`);
  return response.json();
}

function detectBrowserSupport() {
  const video = document.createElement("video");
  const nativeHls = video.canPlayType("application/vnd.apple.mpegurl");
  const mse = "MediaSource" in window;
  const pip = "pictureInPictureEnabled" in document;
  const tracks = "textTracks" in video;
  const labels = [];

  labels.push(nativeHls ? "Native HLS" : mse ? "HLS.js ready" : "Limited HLS");
  labels.push(pip ? "PiP" : "No PiP");
  labels.push(tracks ? "Captions ready" : "No caption API");
  el.browserBadge.textContent = labels.join(" | ");
}

function renderSources() {
  const pills = [];
  (state.sources.playlists || []).forEach((source) => pills.push(`${source.type.toUpperCase()}: ${source.label}`));
  (state.sources.epg || []).forEach((source) => pills.push(`${source.type.toUpperCase()}: ${source.label}`));
  el.sourcePills.innerHTML = pills.map((text) => `<span>${escapeHtml(text)}</span>`).join("");

  const blocks = [
    ...(state.sources.playlists || []),
    ...(state.sources.epg || []),
    ...(state.sources.apis || []),
  ];
  el.sourceGrid.innerHTML = blocks.map((source) => `
    <article class="source-item">
      <strong>${escapeHtml(source.label)}</strong>
      <p>${escapeHtml(source.notes || source.url)}</p>
      <p><a class="source-link" href="${escapeAttr(source.url)}" target="_blank" rel="noopener">Open link</a></p>
    </article>
  `).join("");
}

function renderFilters() {
  const categories = ["all", ...new Set(state.channels.map((channel) => channel.category).filter(Boolean).sort())];
  el.categoryFilter.innerHTML = categories.map((category) => {
    const label = category === "all" ? "All categories" : category;
    return `<option value="${escapeAttr(category)}">${escapeHtml(label)}</option>`;
  }).join("");
}

function applyFilters() {
  const payload = {
    channels: state.channels,
    query: el.searchInput.value,
    category: el.categoryFilter.value,
    sort: el.sortSelect.value,
    favoritesOnly: el.favoritesOnly.getAttribute("aria-pressed") === "true",
    favorites: [...state.favorites],
    names: state.displayNames,
  };

  if (state.worker) {
    state.worker.postMessage(payload);
    return;
  }

  state.filtered = state.channels.filter((channel) => {
    if (payload.favoritesOnly && !state.favorites.has(channel.id)) return false;
    if (payload.category !== "all" && channel.category !== payload.category) return false;
    const query = payload.query.trim().toLowerCase();
    if (!query) return true;
    return [channel.name, displayName(channel), channel.category, ...(channel.altNames || [])].join(" ").toLowerCase().includes(query);
  });
  renderChannels();
}

function renderChannels() {
  el.channelCount.textContent = `${state.filtered.length} channels`;
  if (!state.filtered.length) {
    el.channelList.innerHTML = `<p>No matching channels.</p>`;
    return;
  }

  el.channelList.innerHTML = state.filtered.map((channel) => {
    const favorite = state.favorites.has(channel.id);
    const selected = state.selected?.id === channel.id;
    const reliability = channel.reliability?.length ? channel.reliability[0] : `${channel.streams.length} stream option${channel.streams.length === 1 ? "" : "s"}`;
    return `
      <button class="channel-card" type="button" data-channel-id="${escapeAttr(channel.id)}" aria-current="${selected}">
        <img src="${escapeAttr(channel.logo || "")}" alt="" loading="lazy">
        <span>
          <strong>${escapeHtml(displayName(channel))}</strong><br>
          <small>${escapeHtml(channel.category)} | ${escapeHtml(reliability)}</small>
        </span>
        <span class="favorite-mark" aria-label="${favorite ? "Favorite" : "Not favorite"}">${favorite ? "Fav" : ""}</span>
      </button>
    `;
  }).join("");
}

function onChannelClick(event) {
  const button = event.target.closest("[data-channel-id]");
  if (!button) return;
  const channel = state.channels.find((item) => item.id === button.dataset.channelId);
  if (!channel) return;
  selectChannel(channel);
}

function selectChannel(channel) {
  state.selected = channel;
  el.selectedLogo.src = channel.logo || "";
  el.selectedName.textContent = displayName(channel);
  el.selectedMeta.textContent = [channel.category, channel.network, channel.owners?.join(", ")].filter(Boolean).join(" | ") || "Hungary";
  el.displayNameInput.value = state.displayNames[channel.id] || channel.name;
  el.favoriteSelected.setAttribute("aria-pressed", String(state.favorites.has(channel.id)));
  el.favoriteSelected.textContent = state.favorites.has(channel.id) ? "Favorited" : "Favorite";
  el.streamSelect.innerHTML = channel.streams.map((stream, index) => {
    const label = stream.url.startsWith("https:") ? `Stream ${index + 1}` : `Stream ${index + 1} - HTTP`;
    return `<option value="${index}">${escapeHtml(label)}</option>`;
  }).join("");
  el.infoLinks.innerHTML = [
    channel.website ? `<a href="${escapeAttr(channel.website)}" target="_blank" rel="noopener">Channel site</a>` : "",
    channel.infoUrl ? `<a href="${escapeAttr(channel.infoUrl)}" target="_blank" rel="noopener">Info lookup</a>` : "",
  ].join("");
  renderProgramsForSelected();
  renderChannels();
  loadSelectedStream(false);
}

function loadSelectedStream(forceReload) {
  if (!state.selected) return;
  const stream = currentStream();
  if (!stream) return;

  if (location.protocol === "https:" && stream.url.startsWith("http:")) {
    setScreenState("This HTTP stream may be blocked on an HTTPS page. Try an HTTPS alternate when available.");
  } else {
    setScreenState("Opening stream...");
  }

  destroyHls();
  el.statusState.textContent = "Loading";
  el.streamBadge.textContent = stream.url.startsWith("https:") ? "HTTPS stream selected" : "HTTP stream selected";

  if (forceReload) {
    el.videoPlayer.removeAttribute("src");
    el.videoPlayer.load();
  }

  if (el.videoPlayer.canPlayType("application/vnd.apple.mpegurl")) {
    el.videoPlayer.src = stream.url;
  } else if (window.Hls && Hls.isSupported()) {
    state.hls = new Hls({
      lowLatencyMode: true,
      backBufferLength: 90,
      maxBufferLength: 45,
    });
    state.hls.on(Hls.Events.ERROR, (_, data) => {
      const detail = `${data.type || "hls"} ${data.details || "error"}`;
      logEvent(`${displayName(state.selected)} HLS event: ${detail}`);
      if (data.fatal) {
        setScreenState("The stream stopped. Try retry or another stream.");
        state.hls.recoverMediaError();
      }
    });
    state.hls.on(Hls.Events.LEVEL_SWITCHED, (_, data) => {
      el.qualityState.textContent = `Quality: level ${data.level + 1}`;
    });
    state.hls.loadSource(stream.url);
    state.hls.attachMedia(el.videoPlayer);
  } else {
    setScreenState("This browser does not support HLS playback for this stream.");
    return;
  }

  el.videoPlayer.play().catch((error) => {
    setScreenState("Press Play to start this channel.");
    logEvent(`${displayName(state.selected)} autoplay blocked: ${error.message}`);
  });
  logEvent(`Selected ${displayName(state.selected)}.`);
}

function currentStream() {
  if (!state.selected) return null;
  return state.selected.streams[Number(el.streamSelect.value || 0)] || state.selected.streams[0];
}

async function loadGuide() {
  const epg = state.sources?.epg?.[0];
  if (!epg) return;
  el.guideStatus.textContent = "Loading program guide...";
  el.guideBadge.textContent = "Guide loading";

  try {
    const response = await fetch("data/guide.json", { cache: "no-cache" });
    if (!response.ok) throw new Error(`Local guide returned ${response.status}`);
    parseGuideSnapshot(await response.json());
    state.guideLoaded = true;
    el.guideStatus.textContent = "Guide loaded from the curated XMLTV snapshot. Times are shown in your browser timezone.";
    el.guideBadge.textContent = "Guide loaded";
    renderProgramsForSelected();
    logEvent("Program guide loaded.");
  } catch (error) {
    el.guideStatus.textContent = "The local guide snapshot could not be loaded.";
    el.guideBadge.textContent = "Guide blocked";
    logEvent(`Guide load failed: ${error.message}`);
  }
}

function parseGuideSnapshot(payload) {
  const nextMap = new Map();
  const now = Date.now();
  const horizon = now + 36 * 60 * 60 * 1000;
  const channels = payload.channels || {};

  Object.entries(channels).forEach(([id, channel]) => {
    const channelId = normalizeGuideId(id);
    (channel.programs || []).forEach((item) => {
      const start = new Date(item.start);
      const stop = item.stop ? new Date(item.stop) : null;
    if (!start || start.getTime() > horizon || (stop && stop.getTime() < now - 60 * 60 * 1000)) return;
      const title = item.title || "Program";
      const desc = item.desc || "";
    if (!nextMap.has(channelId)) nextMap.set(channelId, []);
    nextMap.get(channelId).push({ start, stop, title, desc });
    });
  });

  [...nextMap.values()].forEach((items) => items.sort((a, b) => a.start - b.start));
  state.guidePrograms = nextMap;
}

function renderProgramsForSelected() {
  if (!state.selected) {
    el.programList.innerHTML = `<p>Select a channel to see its schedule.</p>`;
    return;
  }

  if (!state.guideLoaded) {
    el.programList.innerHTML = `<p>Load the guide to see programs for ${escapeHtml(displayName(state.selected))}.</p>`;
    return;
  }

  const keys = guideKeysForChannel(state.selected);
  const programs = keys.flatMap((key) => state.guidePrograms.get(key) || []).slice(0, 12);

  if (!programs.length) {
    el.programList.innerHTML = `<p>No guide rows matched ${escapeHtml(displayName(state.selected))}. Try the channel site link for its own schedule.</p>`;
    return;
  }

  el.programList.innerHTML = programs.map((program) => `
    <article class="program-item">
      <div class="program-time">${escapeHtml(formatProgramTime(program.start, program.stop))}</div>
      <strong>${escapeHtml(program.title)}</strong>
      ${program.desc ? `<p>${escapeHtml(program.desc)}</p>` : ""}
    </article>
  `).join("");
}

function guideKeysForChannel(channel) {
  const base = channel.id.replace(/@.*$/, "");
  const nameKey = normalizeGuideId(channel.name.replace(/\s+/g, ""));
  const noTvKey = normalizeGuideId(channel.name.replace(/\s*tv\b/i, "").replace(/\s+/g, ""));
  const keys = new Set([
    normalizeGuideId(channel.id),
    normalizeGuideId(base),
    normalizeGuideId(`${base}@SD`),
    normalizeGuideId(`${base}@HD`),
    nameKey.endsWith(".hu") ? nameKey : `${nameKey}.hu`,
    noTvKey.endsWith(".hu") ? noTvKey : `${noTvKey}.hu`,
  ]);
  (channel.guideIds || []).forEach((guide) => keys.add(normalizeGuideId(guide.channel || channel.id)));
  if (channel.id === "Duna.hu") keys.add("dunatelevizio.hu");
  if (channel.id === "CoolTV.hu") keys.add("cool.hu");
  if (channel.id === "RTL.hu") keys.add("rtlklub.hu");
  if (channel.id === "RTLKetto.hu") keys.add("rtlii.hu");
  if (channel.id === "FIXTV.hu") keys.add("fix.hu");
  return [...keys];
}

function formatProgramTime(start, stop) {
  const startText = start.toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" });
  if (!stop) return startText;
  const stopText = stop.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return `${startText} - ${stopText}`;
}

function saveDisplayName(event) {
  event.preventDefault();
  if (!state.selected) return;
  const value = el.displayNameInput.value.trim();
  if (!value || value === state.selected.name) {
    delete state.displayNames[state.selected.id];
  } else {
    state.displayNames[state.selected.id] = value;
  }
  localStorage.setItem("hungary-tv:names", JSON.stringify(state.displayNames));
  el.selectedName.textContent = displayName(state.selected);
  applyFilters();
  logEvent(`Saved display name for ${state.selected.name}.`);
}

function toggleFavorite(id) {
  if (!id) return;
  if (state.favorites.has(id)) {
    state.favorites.delete(id);
  } else {
    state.favorites.add(id);
  }
  localStorage.setItem("hungary-tv:favorites", JSON.stringify([...state.favorites]));
  if (state.selected?.id === id) {
    el.favoriteSelected.setAttribute("aria-pressed", String(state.favorites.has(id)));
    el.favoriteSelected.textContent = state.favorites.has(id) ? "Favorited" : "Favorite";
  }
  applyFilters();
}

function displayName(channel) {
  if (!channel) return "Channel";
  return state.displayNames[channel.id] || channel.displayName || channel.name;
}

function setScreenState(message) {
  el.screenState.textContent = message || "";
}

function updateBufferState() {
  const video = el.videoPlayer;
  let seconds = 0;
  for (let index = 0; index < video.buffered.length; index += 1) {
    if (video.buffered.start(index) <= video.currentTime && video.buffered.end(index) >= video.currentTime) {
      seconds = Math.max(0, video.buffered.end(index) - video.currentTime);
      break;
    }
  }
  el.bufferState.textContent = `Buffer: ${seconds.toFixed(0)}s`;
}

function updateCaptionState() {
  const tracks = [...el.videoPlayer.textTracks || []];
  el.captionState.textContent = tracks.length ? `Captions: ${tracks.length} track${tracks.length === 1 ? "" : "s"}` : "Captions: none detected";
}

function toggleCaptions() {
  const tracks = [...el.videoPlayer.textTracks || []];
  if (!tracks.length) {
    el.captionState.textContent = "Captions: none detected";
    return;
  }
  const showing = tracks.some((track) => track.mode === "showing");
  tracks.forEach((track, index) => {
    track.mode = !showing && index === 0 ? "showing" : "disabled";
  });
  updateCaptionState();
}

function togglePlay() {
  if (el.videoPlayer.paused) {
    el.videoPlayer.play().catch((error) => logEvent(`Play failed: ${error.message}`));
  } else {
    el.videoPlayer.pause();
  }
}

function seekLiveEdge() {
  const video = el.videoPlayer;
  if (!video.seekable.length) return;
  video.currentTime = video.seekable.end(video.seekable.length - 1);
}

async function togglePictureInPicture() {
  if (!document.pictureInPictureEnabled) return;
  if (document.pictureInPictureElement) {
    await document.exitPictureInPicture();
  } else {
    await el.videoPlayer.requestPictureInPicture();
  }
}

function toggleFullscreen() {
  const target = document.querySelector(".tube-tv");
  if (document.fullscreenElement) {
    document.exitFullscreen();
  } else {
    target.requestFullscreen?.();
  }
}

function destroyHls() {
  if (state.hls) {
    state.hls.destroy();
    state.hls = null;
  }
}

function mediaErrorMessage(error) {
  if (!error) return "The stream could not be played.";
  const messages = {
    1: "Playback was aborted.",
    2: "A network error stopped the stream.",
    3: "The stream could not be decoded.",
    4: "The stream format is not supported here.",
  };
  return messages[error.code] || "The stream could not be played.";
}

async function copyCurrentStream() {
  const stream = currentStream();
  if (!stream) return;
  await navigator.clipboard.writeText(stream.url);
  logEvent("Copied current stream link.");
}

async function copySourceLinks() {
  const lines = [
    ...(state.sources?.playlists || []).map((source) => `${source.label}: ${source.url}`),
    ...(state.sources?.epg || []).map((source) => `${source.label}: ${source.url}`),
    ...(state.sources?.apis || []).map((source) => `${source.label}: ${source.url}`),
  ];
  await navigator.clipboard.writeText(lines.join("\n"));
  logEvent("Copied curated source links.");
}

function exportSettings() {
  const payload = {
    exportedAt: new Date().toISOString(),
    favorites: [...state.favorites],
    displayNames: state.displayNames,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "hungary-tv-settings.json";
  link.click();
  URL.revokeObjectURL(url);
}

function logEvent(message) {
  const entry = `${new Date().toLocaleString()} - ${message}`;
  state.events.unshift(entry);
  state.events = state.events.slice(0, 25);
  localStorage.setItem("hungary-tv:events", JSON.stringify(state.events));
  renderEvents();
}

function renderEvents() {
  el.eventLog.innerHTML = state.events.map((event) => `<li>${escapeHtml(event)}</li>`).join("");
}

function clearEvents() {
  state.events = [];
  localStorage.removeItem("hungary-tv:events");
  renderEvents();
}

function normalizeGuideId(value) {
  return String(value || "").trim().toLowerCase();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, "&#96;");
}
