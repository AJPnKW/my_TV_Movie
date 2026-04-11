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

  class WatchPartyPlayer {
    constructor(options) {
      this.options = options || {};
      this.mount = document.querySelector(this.options.mountSelector);
      this.title = this.options.title || "Watch Party Player";
      this.role = "";
      this.step = "setup";
      this.ws = null;
      this.clientId = "";
      this.isApplyingRemote = false;
      this.lastBroadcastAt = 0;
      this.videos = [];
    }

    render() {
      if (!this.mount) return;
      this.mount.innerHTML = "";
      this.root = createElement("section", "watch-party-player");
      this.root.setAttribute("aria-label", "Local watch party player");

      const header = createElement("div", "watch-party-player-header");
      const heading = createElement("div");
      heading.appendChild(createElement("div", "watch-party-player-kicker", "Local Prototype"));
      heading.appendChild(createElement("div", "watch-party-player-title", this.title));
      this.status = createElement("div", "watch-party-player-status", "Setup");
      header.appendChild(heading);
      header.appendChild(this.status);

      this.steps = createElement("div", "watch-party-player-steps");
      this.steps.appendChild(createElement("div", "watch-party-player-step", "1. Set room"));
      this.steps.appendChild(createElement("div", "watch-party-player-step", "2. Connect"));
      this.steps.appendChild(createElement("div", "watch-party-player-step", "3. Play together"));

      const grid = createElement("div", "watch-party-player-grid");
      grid.appendChild(this.renderControls());
      grid.appendChild(this.renderStage());

      this.root.appendChild(header);
      this.root.appendChild(this.steps);
      this.root.appendChild(grid);
      this.mount.appendChild(this.root);
      this.bindVideoEvents();
      this.refreshVideos();
      this.updateStep("setup");
    }

    renderControls() {
      const wrap = createElement("div", "watch-party-player-controls");
      const fields = createElement("div", "watch-party-player-fields");

      const videoField = createElement("label", "watch-party-player-field");
      videoField.appendChild(createElement("span", "watch-party-player-label", "Local video"));
      this.videoSelect = createElement("select", "watch-party-player-select");
      videoField.appendChild(this.videoSelect);

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

      fields.appendChild(videoField);
      fields.appendChild(roomField);
      fields.appendChild(nameField);

      this.clock = createElement("span", "watch-party-player-clock", "00:00");
      const actions = createElement("div", "watch-party-player-actions");
      this.hostButton = this.button("Start Watch Party", "primary", () => this.connect("host"));
      this.joinButton = this.button("Join Watch Party", "", () => this.connect("guest"));
      this.playButton = this.button("Play", "primary", () => this.hostPlay());
      this.pauseButton = this.button("Pause", "", () => this.hostPause());
      this.syncButton = this.button("Sync Now", "", () => this.broadcastState());
      actions.appendChild(this.hostButton);
      actions.appendChild(this.joinButton);
      actions.appendChild(this.clock);
      actions.appendChild(this.playButton);
      actions.appendChild(this.pauseButton);
      actions.appendChild(this.syncButton);

      this.note = createElement("div", "watch-party-player-note", "");
      this.warning = createElement("div", "watch-party-player-warning", "");
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
      wrap.appendChild(this.video);
      return wrap;
    }

    button(label, variant, handler) {
      const btn = createElement("button", `watch-party-player-button ${variant || ""}`.trim(), label);
      btn.type = "button";
      btn.addEventListener("click", handler);
      return btn;
    }

    async refreshVideos() {
      try {
        const res = await fetch("/api/watch-party/videos", { cache: "no-store" });
        if (!res.ok) throw new Error("No local server");
        const data = await res.json();
        this.videos = Array.isArray(data.videos) ? data.videos : [];
        this.videoSelect.innerHTML = "";
        if (!this.videos.length) {
          const opt = document.createElement("option");
          opt.value = "";
          opt.textContent = "No local videos found";
          this.videoSelect.appendChild(opt);
          this.warning.textContent = "Add MP4/WebM files to .videos_local, then run the local watch-party server.";
        } else {
          this.videos.forEach((video) => {
            const opt = document.createElement("option");
            opt.value = video.id;
            opt.textContent = video.name;
            this.videoSelect.appendChild(opt);
          });
          this.setVideo(this.videos[0].id);
          this.warning.textContent = "";
        }
      } catch (_) {
        this.warning.textContent = "Local watch-party server is offline. Run: node tools/watch_party_player_server.js";
      }
      this.updateButtons();
    }

    setVideo(id) {
      const video = this.videos.find((item) => item.id === id);
      if (!video) return;
      if (this.video.getAttribute("data-video-id") === video.id) return;
      this.video.src = video.url;
      this.video.setAttribute("data-video-id", video.id);
    }

    bindVideoEvents() {
      this.videoSelect.addEventListener("change", () => {
        this.setVideo(this.videoSelect.value);
        this.broadcastState();
      });
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

    formReady() {
      return Boolean(this.videoSelect.value && safeRoom(this.roomInput.value) && this.nameInput.value.trim());
    }

    updateStep(step) {
      this.step = step;
      const labels = ["setup", "connect", "play"];
      [...this.steps.children].forEach((el, idx) => el.classList.toggle("active", labels[idx] === step));
      this.status.textContent = step === "setup" ? "Setup" : step === "connect" ? "Connected" : this.role === "host" ? "Hosting" : "Joined";
      this.note.textContent = step === "setup"
        ? "Choose a local video, enter room and name, then start or join."
        : this.role === "host"
          ? "Host controls playback. Guests follow play, pause, seek, and sync."
          : "Guest playback follows the host. Keep this page open.";
      this.updateButtons();
    }

    updateButtons() {
      const ready = this.formReady();
      const isSetup = this.step === "setup";
      const isPlay = this.step === "play";
      const isHost = this.role === "host";
      this.hostButton.disabled = !isSetup || !ready;
      this.joinButton.disabled = !isSetup || !ready;
      this.playButton.disabled = !isPlay || !isHost;
      this.pauseButton.disabled = !isPlay || !isHost;
      this.syncButton.disabled = !isPlay || !isHost;
      this.video.controls = isHost || this.step === "setup";
    }

    connect(role) {
      if (!this.formReady()) return;
      this.role = role;
      this.setVideo(this.videoSelect.value);
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
        this.warning.textContent = "Disconnected from the local watch-party server.";
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
      if (state.videoId && this.videoSelect.value !== state.videoId) {
        this.videoSelect.value = state.videoId;
        this.setVideo(state.videoId);
      }
      if (Math.abs(this.video.currentTime - Number(state.currentTime || 0)) > 1.25) {
        this.video.currentTime = Number(state.currentTime || 0);
      }
      const playPromise = state.paused ? (this.video.pause(), null) : this.video.play();
      if (playPromise && typeof playPromise.catch === "function") playPromise.catch(() => {});
      window.setTimeout(() => { this.isApplyingRemote = false; }, 250);
    }

    hostPlay() {
      this.video.play().catch(() => {});
      this.broadcastState();
    }

    hostPause() {
      this.video.pause();
      this.broadcastState();
    }

    broadcastState() {
      if (this.role !== "host" || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;
      this.lastBroadcastAt = Date.now();
      this.ws.send(JSON.stringify({
        type: "state",
        videoId: this.videoSelect.value,
        paused: this.video.paused,
        currentTime: this.video.currentTime,
      }));
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
