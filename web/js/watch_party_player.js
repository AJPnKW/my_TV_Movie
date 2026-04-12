(function () {
  "use strict";

  function createElement(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  }

  function safeRoom(value) {
    return String(value || "").trim().toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "");
  }

  function formatSeconds(value) {
    const total = Math.max(0, Math.floor(Number(value) || 0));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    return h > 0
      ? `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
      : `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  function normalizeSource(source) {
    if (!source || !source.id) return null;
    return {
      id: String(source.id),
      label: source.label || source.title || String(source.id),
      meta: source.meta || "",
      sourceType: source.sourceType || "external",
      sourceUrl: source.sourceUrl || source.url || "",
      videoUrl: source.videoUrl || source.url || source.sourceUrl || "",
      canControl: Boolean(source.canControl),
    };
  }

  function toWebSocketUrl(value, baseUrl) {
    const url = new URL(value, baseUrl || window.location.href);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    return url.toString();
  }

  class WatchPartyPlayer {
    constructor(options) {
      this.options = options || {};
      this.mount = document.querySelector(this.options.mountSelector);
      this.title = this.options.title || "Watch Party Player";
      this.serverUrl = String(this.options.serverUrl || window.MyTvMovieWatchPartyServerUrl || "").replace(/\/+$/, "");
      this.sources = (this.options.items || this.options.sources || []).map(normalizeSource).filter(Boolean);
      this.currentSource = this.sources.find((item) => item.id === this.options.initialItemId) || this.sources[0] || null;
      this.role = "";
      this.step = "setup";
      this.ws = null;
      this.clientId = "";
      this.isApplyingRemote = false;
      this.lastBroadcastAt = 0;
      this.timerPaused = true;
      this.timerBase = 0;
      this.timerStartedAt = 0;
      this.serverReady = false;
      this.serverChecked = false;
      this.initialParams = new URLSearchParams(window.location.search);
    }

    render() {
      if (!this.mount) return;
      this.mount.innerHTML = "";
      this.root = createElement("section", "watch-party-player");
      this.root.setAttribute("aria-label", "Watch party player");

      const header = createElement("div", "watch-party-player-header");
      const heading = createElement("div");
      heading.appendChild(createElement("div", "watch-party-player-kicker", "Watch Together"));
      heading.appendChild(createElement("div", "watch-party-player-title", this.title));
      header.appendChild(heading);

      this.steps = createElement("div", "watch-party-player-steps");
      this.steps.appendChild(createElement("div", "watch-party-player-step", "1. Pick episode"));
      this.steps.appendChild(createElement("div", "watch-party-player-step", "2. Start or join"));
      this.steps.appendChild(createElement("div", "watch-party-player-step", "3. Watch together"));

      const grid = createElement("div", "watch-party-player-grid");
      grid.appendChild(this.renderControls());
      grid.appendChild(this.renderStage());

      this.root.appendChild(header);
      this.root.appendChild(this.steps);
      this.root.appendChild(grid);
      this.mount.appendChild(this.root);
      this.bindEvents();
      this.applyInitialParams();
      this.setCurrentItem(this.currentSource?.id || "");
      this.updateStep("setup");
      this.checkServer();
      window.setInterval(() => this.refreshClock(), 500);
    }

    renderControls() {
      const wrap = createElement("div", "watch-party-player-controls");

      this.sourceSummary = createElement("div", "watch-party-player-source");
      this.sourceLabel = createElement("div", "watch-party-player-source-title", "Select an episode");
      this.sourceMeta = createElement("div", "watch-party-player-source-meta", "Use an episode card Watch Party button.");
      this.sourceSummary.appendChild(createElement("div", "watch-party-player-label", "Selected episode"));
      this.sourceSummary.appendChild(this.sourceLabel);
      this.sourceSummary.appendChild(this.sourceMeta);

      const fields = createElement("div", "watch-party-player-fields three");
      const episodeField = createElement("label", "watch-party-player-field");
      episodeField.appendChild(createElement("span", "watch-party-player-label", "Season / episode"));
      this.sourceSelect = createElement("select", "watch-party-player-input");
      this.sources.forEach((source) => {
        const option = document.createElement("option");
        option.value = source.id;
        option.textContent = source.label;
        this.sourceSelect.appendChild(option);
      });
      episodeField.appendChild(this.sourceSelect);

      const roomField = createElement("label", "watch-party-player-field");
      roomField.appendChild(createElement("span", "watch-party-player-label", "Room"));
      this.roomInput = createElement("input", "watch-party-player-input");
      this.roomInput.placeholder = "heated-rivalry-test";
      this.roomInput.autocomplete = "off";
      roomField.appendChild(this.roomInput);

      const nameField = createElement("label", "watch-party-player-field");
      nameField.appendChild(createElement("span", "watch-party-player-label", "Name"));
      this.nameInput = createElement("input", "watch-party-player-input");
      this.nameInput.placeholder = "Your name";
      this.nameInput.autocomplete = "name";
      nameField.appendChild(this.nameInput);

      fields.appendChild(episodeField);
      fields.appendChild(roomField);
      fields.appendChild(nameField);

      this.clock = createElement("span", "watch-party-player-clock", "00:00");
      const actions = createElement("div", "watch-party-player-actions");
      this.hostButton = this.button("Start Watch Party", "primary", () => this.connect("host"));
      this.joinButton = this.button("Join Watch Party", "", () => this.connect("guest"));
      this.openButton = this.button("Open Episode", "primary", () => this.openSource());
      this.inviteButton = this.button("Copy Invite", "", () => this.copyInvite());
      this.playButton = this.button("Start Timer", "", () => this.hostPlay());
      this.pauseButton = this.button("Pause Timer", "", () => this.hostPause());
      this.syncButton = this.button("Sync Now", "", () => this.broadcastState());
      actions.appendChild(this.hostButton);
      actions.appendChild(this.joinButton);
      actions.appendChild(this.openButton);
      actions.appendChild(this.inviteButton);
      actions.appendChild(this.clock);
      actions.appendChild(this.playButton);
      actions.appendChild(this.pauseButton);
      actions.appendChild(this.syncButton);

      this.note = createElement("div", "watch-party-player-note", "");
      this.warning = createElement("div", "watch-party-player-warning", "");
      wrap.appendChild(this.sourceSummary);
      wrap.appendChild(fields);
      wrap.appendChild(actions);
      wrap.appendChild(this.note);
      wrap.appendChild(this.warning);
      return wrap;
    }

    renderStage() {
      const wrap = createElement("div", "watch-party-player-stage");
      this.video = document.createElement("video");
      this.video.className = "watch-party-player-video";
      this.video.controls = true;
      this.video.playsInline = true;

      this.placeholder = createElement("div", "watch-party-player-placeholder");
      this.placeholderTitle = createElement("div", "watch-party-player-placeholder-title", "External episode source");
      this.placeholderText = createElement("div", "watch-party-player-placeholder-text", "");
      this.placeholder.appendChild(this.placeholderTitle);
      this.placeholder.appendChild(this.placeholderText);

      wrap.appendChild(this.video);
      wrap.appendChild(this.placeholder);
      return wrap;
    }

    button(label, variant, handler) {
      const btn = createElement("button", `watch-party-player-button ${variant || ""}`.trim(), label);
      btn.type = "button";
      btn.addEventListener("click", handler);
      return btn;
    }

    bindEvents() {
      this.sourceSelect.addEventListener("change", () => this.setCurrentItem(this.sourceSelect.value));
      this.roomInput.addEventListener("input", () => this.updateButtons());
      this.nameInput.addEventListener("input", () => this.updateButtons());
      this.video.addEventListener("timeupdate", () => {
        this.clock.textContent = formatSeconds(this.video.currentTime);
        if (this.role === "host" && Date.now() - this.lastBroadcastAt > 3000) this.broadcastState();
      });
      this.video.addEventListener("play", () => {
        if (this.role === "host" && !this.isApplyingRemote) this.broadcastState();
      });
      this.video.addEventListener("pause", () => {
        if (this.role === "host" && !this.isApplyingRemote) this.broadcastState();
      });
      this.video.addEventListener("seeked", () => {
        if (this.role === "host" && !this.isApplyingRemote) this.broadcastState();
      });
    }

    applyInitialParams() {
      const sourceId = this.initialParams.get("partySource");
      const room = this.initialParams.get("partyRoom");
      if (sourceId && this.sources.some((item) => item.id === sourceId)) this.currentSource = this.sources.find((item) => item.id === sourceId);
      if (room) this.roomInput.value = safeRoom(room);
    }

    setCurrentItem(itemOrId) {
      const source = typeof itemOrId === "object"
        ? normalizeSource(itemOrId)
        : this.sources.find((item) => item.id === String(itemOrId));
      if (!source) {
        this.updateButtons();
        return;
      }
      if (!this.sources.some((item) => item.id === source.id)) {
        this.sources.push(source);
        if (this.sourceSelect) {
          const option = document.createElement("option");
          option.value = source.id;
          option.textContent = source.label;
          this.sourceSelect.appendChild(option);
        }
      }
      this.currentSource = source;
      if (this.sourceSelect && this.sourceSelect.value !== source.id) {
        this.sourceSelect.value = source.id;
      }
      this.sourceLabel.textContent = source.label;
      this.sourceMeta.textContent = source.meta || (source.canControl ? "Controlled playback source" : "External playback source");

      if (source.canControl && source.videoUrl) {
        this.placeholder.hidden = true;
        this.video.hidden = false;
        if (this.video.getAttribute("data-source-id") !== source.id) {
          this.video.src = source.videoUrl;
          this.video.setAttribute("data-source-id", source.id);
        }
        this.playButton.textContent = "Play";
        this.pauseButton.textContent = "Pause";
      } else {
        this.video.pause();
        this.video.removeAttribute("src");
        this.video.removeAttribute("data-source-id");
        this.video.hidden = true;
        this.placeholder.hidden = false;
        this.placeholderTitle.textContent = source.label;
        this.placeholderText.textContent = "Google Drive playback opens in its own tab. This room keeps the selected episode, shared timer, and sync state together.";
        this.playButton.textContent = "Start Timer";
        this.pauseButton.textContent = "Pause Timer";
      }

      if (this.role === "host") this.broadcastState();
      this.updateButtons();
    }

    formReady() {
      return Boolean(this.currentSource && safeRoom(this.roomInput.value) && this.nameInput.value.trim());
    }

    async checkServer() {
      this.serverChecked = false;
      this.serverReady = false;
      this.warning.textContent = "Checking watch-party room server...";
      this.updateButtons();
      try {
        const res = await fetch(`${this.serverUrl}/api/watch-party/health`, { cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!data?.ok) throw new Error("Health check failed");
        if (data.websocket) this.websocketUrl = toWebSocketUrl(data.websocket, this.serverUrl || window.location.origin);
        this.serverReady = true;
        this.warning.textContent = "";
      } catch (_) {
        this.serverReady = false;
        this.warning.textContent = "Room sync is offline here. A public party needs the hosted watch-party server to be running.";
      } finally {
        this.serverChecked = true;
        this.updateButtons();
      }
    }

    sourceIsControllable() {
      return Boolean(this.currentSource?.canControl && this.currentSource?.videoUrl);
    }

    currentTime() {
      if (this.sourceIsControllable()) return this.video.currentTime;
      if (this.timerPaused) return this.timerBase;
      return this.timerBase + ((Date.now() - this.timerStartedAt) / 1000);
    }

    refreshClock() {
      this.clock.textContent = formatSeconds(this.currentTime());
    }

    updateStep(step) {
      this.step = step;
      const labels = ["setup", "connect", "play"];
      [...this.steps.children].forEach((el, idx) => el.classList.toggle("active", labels[idx] === step));
      if (step === "setup") {
        this.note.textContent = "Choose the episode, enter room and name, then start or join. Open Episode works without room sync.";
      } else if (this.sourceIsControllable()) {
        this.note.textContent = this.role === "host"
          ? "Host controls playback. Guests follow play, pause, seek, and sync."
          : "Guest playback follows the host. Keep this page open.";
      } else {
        this.note.textContent = this.role === "host"
          ? "Open the episode in Google Drive, then use the timer so everyone can line up playback."
          : "Open the episode in Google Drive and follow the host timer.";
      }
      this.updateButtons();
    }

    updateButtons() {
      const ready = this.formReady();
      const isSetup = this.step === "setup";
      const isPlay = this.step === "play";
      const isHost = this.role === "host";
      this.hostButton.disabled = !isSetup || !ready || !this.serverReady;
      this.joinButton.disabled = !isSetup || !ready || !this.serverReady;
      this.openButton.disabled = !this.currentSource?.sourceUrl;
      this.inviteButton.disabled = !this.currentSource || !safeRoom(this.roomInput.value) || !this.serverReady;
      this.playButton.disabled = !isPlay || !isHost;
      this.pauseButton.disabled = !isPlay || !isHost;
      this.syncButton.disabled = !isPlay || !isHost;
      this.video.controls = this.sourceIsControllable() && (isHost || this.step === "setup");
      if (!this.currentSource) {
        this.warning.textContent = "Select an episode from the show page before starting the room.";
      } else if (this.serverChecked && this.serverReady && this.step === "setup") {
        this.warning.textContent = "";
      }
    }

    connect(role) {
      if (!this.formReady()) return;
      this.role = role;
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const fallbackWsUrl = this.serverUrl
        ? toWebSocketUrl("/watch-party-ws", this.serverUrl)
        : `${protocol}//${window.location.host}/watch-party-ws`;
      this.ws = new WebSocket(this.websocketUrl || fallbackWsUrl);
      this.updateStep("connect");
      this.ws.addEventListener("open", () => {
        this.ws.send(JSON.stringify({
          type: "hello",
          room: safeRoom(this.roomInput.value),
          name: this.nameInput.value.trim(),
          role,
        }));
      });
      this.ws.addEventListener("message", (event) => this.handleMessage(event));
      this.ws.addEventListener("error", () => {
        this.warning.textContent = "Watch-party server is not reachable. Start it with npm run watch-party and open the local server page, or host the server where every participant can reach it.";
      });
      this.ws.addEventListener("close", () => {
        this.role = "";
        this.updateStep("setup");
        this.serverReady = false;
        this.warning.textContent = "Room sync disconnected. Restart the watch-party server and reload this page.";
      });
    }

    handleMessage(event) {
      let message = null;
      try {
        message = JSON.parse(event.data);
      } catch (_) {
        return;
      }
      if (message.type === "joined") {
        this.clientId = message.clientId;
        if (message.state) this.applyRemoteState(message.state);
        this.updateStep("play");
      }
      if (message.type === "state" && this.role !== "host") this.applyRemoteState(message.state);
    }

    applyRemoteState(state) {
      if (!state) return;
      this.isApplyingRemote = true;
      if (state.sourceId && this.currentSource?.id !== state.sourceId) this.setCurrentItem(state.sourceId);
      const nextTime = Number(state.currentTime || 0);
      if (this.sourceIsControllable()) {
        if (Math.abs(this.video.currentTime - nextTime) > 1.25) this.video.currentTime = nextTime;
        const playPromise = state.paused ? (this.video.pause(), null) : this.video.play();
        if (playPromise && typeof playPromise.catch === "function") playPromise.catch(() => {});
      } else {
        this.timerPaused = Boolean(state.paused);
        this.timerBase = nextTime;
        this.timerStartedAt = Date.now();
      }
      this.refreshClock();
      window.setTimeout(() => { this.isApplyingRemote = false; }, 250);
    }

    openSource() {
      if (!this.currentSource?.sourceUrl) return;
      window.open(this.currentSource.sourceUrl, "_blank", "noopener,noreferrer");
    }

    copyInvite() {
      if (!this.currentSource || !safeRoom(this.roomInput.value)) return;
      const url = new URL(window.location.href);
      url.searchParams.set("partySource", this.currentSource.id);
      url.searchParams.set("partyRoom", safeRoom(this.roomInput.value));
      navigator.clipboard?.writeText(url.toString()).then(() => {
        this.warning.textContent = "Invite copied. Send it to your guest, then start the watch party room.";
      }).catch(() => {
        this.warning.textContent = url.toString();
      });
    }

    hostPlay() {
      if (this.sourceIsControllable()) {
        this.video.play().catch(() => {});
      } else if (this.timerPaused) {
        this.timerPaused = false;
        this.timerStartedAt = Date.now();
      }
      this.broadcastState();
    }

    hostPause() {
      if (this.sourceIsControllable()) {
        this.video.pause();
      } else if (!this.timerPaused) {
        this.timerBase = this.currentTime();
        this.timerPaused = true;
      }
      this.broadcastState();
    }

    broadcastState() {
      if (this.role !== "host" || !this.ws || this.ws.readyState !== WebSocket.OPEN || !this.currentSource) return;
      this.lastBroadcastAt = Date.now();
      this.ws.send(JSON.stringify({
        type: "state",
        sourceId: this.currentSource.id,
        paused: this.sourceIsControllable() ? this.video.paused : this.timerPaused,
        currentTime: this.currentTime(),
      }));
      this.refreshClock();
    }
  }

  window.MyTvMovieWatchPartyPlayer = {
    init(options) {
      const player = new WatchPartyPlayer(options);
      player.render();
      return player;
    },
  };
})();
