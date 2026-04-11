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

  class WatchPartyPlayer {
    constructor(options) {
      this.options = options || {};
      this.mount = document.querySelector(this.options.mountSelector);
      this.title = this.options.title || "Watch Party Player";
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
      this.status = createElement("div", "watch-party-player-status", "Setup");
      header.appendChild(heading);
      header.appendChild(this.status);

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
      this.setCurrentItem(this.currentSource?.id || "");
      this.updateStep("setup");
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

      const fields = createElement("div", "watch-party-player-fields two");
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

      fields.appendChild(roomField);
      fields.appendChild(nameField);

      this.clock = createElement("span", "watch-party-player-clock", "00:00");
      const actions = createElement("div", "watch-party-player-actions");
      this.hostButton = this.button("Start Watch Party", "primary", () => this.connect("host"));
      this.joinButton = this.button("Join Watch Party", "", () => this.connect("guest"));
      this.openButton = this.button("Open Episode", "primary", () => this.openSource());
      this.playButton = this.button("Start Timer", "", () => this.hostPlay());
      this.pauseButton = this.button("Pause Timer", "", () => this.hostPause());
      this.syncButton = this.button("Sync Now", "", () => this.broadcastState());
      actions.appendChild(this.hostButton);
      actions.appendChild(this.joinButton);
      actions.appendChild(this.openButton);
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

    setCurrentItem(itemOrId) {
      const source = typeof itemOrId === "object"
        ? normalizeSource(itemOrId)
        : this.sources.find((item) => item.id === String(itemOrId));
      if (!source) {
        this.updateButtons();
        return;
      }
      if (!this.sources.some((item) => item.id === source.id)) this.sources.push(source);
      this.currentSource = source;
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
      this.status.textContent = step === "setup" ? "Setup" : step === "connect" ? "Connected" : this.role === "host" ? "Hosting" : "Joined";
      if (step === "setup") {
        this.note.textContent = "Use the episode card to choose what to watch, enter room and name, then start or join.";
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
      this.hostButton.disabled = !isSetup || !ready;
      this.joinButton.disabled = !isSetup || !ready;
      this.openButton.disabled = !isPlay || !this.currentSource?.sourceUrl;
      this.playButton.disabled = !isPlay || !isHost;
      this.pauseButton.disabled = !isPlay || !isHost;
      this.syncButton.disabled = !isPlay || !isHost;
      this.video.controls = this.sourceIsControllable() && (isHost || this.step === "setup");
      this.warning.textContent = this.currentSource ? "" : "Select an episode from the show page before starting the room.";
    }

    connect(role) {
      if (!this.formReady()) return;
      this.role = role;
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      this.ws = new WebSocket(`${protocol}//${window.location.host}/watch-party-ws`);
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
      this.ws.addEventListener("close", () => {
        this.role = "";
        this.updateStep("setup");
        this.warning.textContent = "Disconnected from the watch-party server.";
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
