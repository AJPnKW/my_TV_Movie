(function () {
  "use strict";

  const DEFAULT_JITSI_DOMAIN = "meet.jit.si";
  const STORAGE_PREFIX = "my-tv-movie-watch-party:";

  function slugify(value) {
    return String(value || "watch-party")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 56) || "watch-party";
  }

  function sanitizeRoom(value, fallback) {
    return slugify(value || fallback).replace(/-/g, "");
  }

  function encodeRoomState(state) {
    return btoa(unescape(encodeURIComponent(JSON.stringify(state))));
  }

  function decodeRoomState(value) {
    try {
      return JSON.parse(decodeURIComponent(escape(atob(value))));
    } catch (_) {
      return null;
    }
  }

  function getHashState() {
    const params = new URLSearchParams((window.location.hash || "").replace(/^#/, ""));
    const encoded = params.get("party");
    return encoded ? decodeRoomState(encoded) : null;
  }

  function formatSeconds(seconds) {
    const safe = Math.max(0, Math.floor(Number(seconds) || 0));
    const h = Math.floor(safe / 3600);
    const m = Math.floor((safe % 3600) / 60);
    const s = safe % 60;
    return h > 0
      ? `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
      : `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  function createElement(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  }

  class WatchPartyService {
    constructor(options) {
      this.options = options || {};
      this.mount = document.querySelector(this.options.mountSelector);
      this.episodes = Array.isArray(this.options.episodes) ? this.options.episodes : [];
      this.title = this.options.title || document.title || "Watch Party";
      this.storageKey = `${STORAGE_PREFIX}${slugify(this.title)}`;
      this.tickTimer = null;
      this.syncStartedAt = null;
      this.syncSeconds = 0;

      const hashState = getHashState();
      const savedState = this.readSavedState();
      this.state = {
        room: sanitizeRoom(hashState?.room || savedState?.room, this.title),
        displayName: hashState?.name || savedState?.displayName || "",
        episodeKey: hashState?.episodeKey || savedState?.episodeKey || this.defaultEpisodeKey(),
      };
    }

    defaultEpisodeKey() {
      const first = this.episodes[0];
      return first ? this.episodeKey(first) : "";
    }

    episodeKey(ep) {
      return `s${Number(ep.season) || 0}e${Number(ep.number) || 0}`;
    }

    selectedEpisode() {
      return this.episodes.find((ep) => this.episodeKey(ep) === this.state.episodeKey) || this.episodes[0] || null;
    }

    readSavedState() {
      try {
        return JSON.parse(window.localStorage.getItem(this.storageKey) || "{}");
      } catch (_) {
        return {};
      }
    }

    saveState() {
      try {
        window.localStorage.setItem(this.storageKey, JSON.stringify(this.state));
      } catch (_) {
        // Private browsing and strict storage settings can block localStorage.
      }
    }

    inviteUrl() {
      const base = `${window.location.origin}${window.location.pathname}`;
      const state = {
        room: this.state.room,
        episodeKey: this.state.episodeKey,
      };
      return `${base}#party=${encodeURIComponent(encodeRoomState(state))}`;
    }

    render() {
      if (!this.mount) return;

      this.mount.innerHTML = "";
      this.root = createElement("section", "watch-party-panel");
      this.root.setAttribute("aria-label", "Watch party");

      const header = createElement("div", "watch-party-header");
      const heading = createElement("div");
      heading.appendChild(createElement("div", "watch-party-kicker", "Private Room"));
      heading.appendChild(createElement("div", "watch-party-title", "Watch Party"));
      this.status = createElement("div", "watch-party-status", "Room ready");
      header.appendChild(heading);
      header.appendChild(this.status);

      const layout = createElement("div", "watch-party-layout");
      layout.appendChild(this.renderControls());
      layout.appendChild(this.renderConference());

      this.root.appendChild(header);
      this.root.appendChild(layout);
      this.mount.appendChild(this.root);
      this.updateEpisodeSummary();
    }

    renderControls() {
      const wrap = createElement("div", "watch-party-controls");
      const setupWrap = createElement("div", "watch-party-setup-grid");

      const episodeField = createElement("label", "watch-party-field watch-party-episode-field");
      episodeField.appendChild(createElement("span", "watch-party-label", "Episode"));
      this.episodeSelect = createElement("select", "watch-party-select");
      this.episodes.forEach((ep) => {
        const option = document.createElement("option");
        option.value = this.episodeKey(ep);
        option.textContent = `S${ep.season} E${ep.number} - ${ep.title}`;
        option.selected = option.value === this.state.episodeKey;
        this.episodeSelect.appendChild(option);
      });
      this.episodeSelect.addEventListener("change", () => {
        this.state.episodeKey = this.episodeSelect.value;
        this.saveState();
        this.updateEpisodeSummary();
      });
      episodeField.appendChild(this.episodeSelect);
      this.now = createElement("div", "watch-party-now");

      const roomField = createElement("label", "watch-party-field");
      roomField.appendChild(createElement("span", "watch-party-label", "Room Name"));
      this.roomInput = createElement("input", "watch-party-input");
      this.roomInput.value = this.state.room;
      this.roomInput.autocomplete = "off";
      this.roomInput.addEventListener("input", () => {
        this.state.room = sanitizeRoom(this.roomInput.value, this.title);
        this.saveState();
      });
      roomField.appendChild(this.roomInput);

      const nameField = createElement("label", "watch-party-field");
      nameField.appendChild(createElement("span", "watch-party-label", "Your Name"));
      this.nameInput = createElement("input", "watch-party-input");
      this.nameInput.value = this.state.displayName;
      this.nameInput.placeholder = "Name shown in the room";
      this.nameInput.autocomplete = "name";
      this.nameInput.addEventListener("input", () => {
        this.state.displayName = this.nameInput.value.trim();
        this.saveState();
      });
      nameField.appendChild(this.nameInput);

      this.syncTime = createElement("span", "watch-party-sync-time", "00:00");
      this.syncTime.setAttribute("aria-label", "Sync timer");

      const actions = createElement("div", "watch-party-actions");
      actions.appendChild(this.button("Host Watch Party", "primary", () => this.hostParty()));
      actions.appendChild(this.button("Join Watch Party", "", () => this.joinParty()));
      actions.appendChild(this.button("Open Episode", "", () => this.openEpisode()));
      actions.appendChild(this.button("Copy Invite", "", () => this.copyInvite()));
      actions.appendChild(this.syncTime);
      actions.appendChild(this.button("Start Timer", "", () => this.startTimer()));
      actions.appendChild(this.button("Pause", "", () => this.pauseTimer()));
      actions.appendChild(this.button("Reset", "", () => this.resetTimer()));

      const episodeRow = createElement("div", "watch-party-episode-row");
      episodeRow.appendChild(this.now);
      episodeRow.appendChild(episodeField);

      setupWrap.appendChild(roomField);
      setupWrap.appendChild(nameField);

      wrap.appendChild(episodeRow);
      wrap.appendChild(setupWrap);
      wrap.appendChild(actions);
      return wrap;
    }

    renderConference() {
      const wrap = createElement("div", "watch-party-conference");
      const guidance = createElement(
        "div",
        "watch-party-guidance",
        "Host starts the Jitsi room first and signs in if prompted. Everyone opens the same episode separately, then uses the timer to stay together."
      );
      this.error = createElement("div", "watch-party-error");
      wrap.appendChild(guidance);
      wrap.appendChild(this.error);
      return wrap;
    }

    button(label, variant, handler) {
      const btn = createElement("button", `watch-party-button ${variant || ""}`.trim(), label);
      btn.type = "button";
      btn.addEventListener("click", handler);
      return btn;
    }

    updateEpisodeSummary() {
      const ep = this.selectedEpisode();
      if (!ep || !this.now) return;
      this.now.innerHTML = "";
      this.now.appendChild(createElement("div", "watch-party-episode-title", ep.title));
      this.now.appendChild(
        createElement("div", "watch-party-episode-meta", `Season ${ep.season}, Episode ${ep.number} | ${ep.runtime} min | ${ep.airdate}`)
      );
    }

    openEpisode() {
      const ep = this.selectedEpisode();
      if (!ep || !this.options.watchUrlBuilder) return;
      window.open(this.options.watchUrlBuilder(ep), "_blank", "noopener,noreferrer");
    }

    async copyInvite() {
      this.state.room = sanitizeRoom(this.roomInput?.value, this.title);
      this.state.displayName = this.nameInput?.value.trim() || "";
      this.saveState();
      const url = this.inviteUrl();

      try {
        await navigator.clipboard.writeText(url);
        this.setStatus("Invite copied");
      } catch (_) {
        window.prompt("Invite link", url);
        this.setStatus("Invite ready");
      }
    }

    setStatus(message) {
      if (!this.status) return;
      this.status.textContent = message;
      window.clearTimeout(this.statusTimer);
      this.statusTimer = window.setTimeout(() => {
        if (this.status) this.status.textContent = "Room ready";
      }, 2200);
    }

    startTimer() {
      if (this.tickTimer) return;
      this.syncStartedAt = Date.now() - this.syncSeconds * 1000;
      this.tickTimer = window.setInterval(() => {
        this.syncSeconds = Math.floor((Date.now() - this.syncStartedAt) / 1000);
        this.syncTime.textContent = formatSeconds(this.syncSeconds);
      }, 250);
      this.setStatus("Timer running");
    }

    pauseTimer() {
      window.clearInterval(this.tickTimer);
      this.tickTimer = null;
      this.setStatus("Timer paused");
    }

    resetTimer() {
      this.pauseTimer();
      this.syncSeconds = 0;
      this.syncTime.textContent = "00:00";
      this.setStatus("Timer reset");
    }

    roomUrl() {
      return `https://${DEFAULT_JITSI_DOMAIN}/${encodeURIComponent(this.state.room)}`;
    }

    persistRoomState() {
      this.state.room = sanitizeRoom(this.roomInput?.value, this.title);
      this.state.displayName = this.nameInput?.value.trim() || "";
      this.saveState();
    }

    hostParty() {
      this.persistRoomState();
      window.open(this.roomUrl(), "_blank", "noopener,noreferrer");
      this.setStatus("Host room opened");
      if (this.error) {
        this.error.textContent = "Host signs in to start the Jitsi room. After the room is live, open the episode and start the timer.";
      }
    }

    joinParty() {
      this.persistRoomState();
      window.open(this.roomUrl(), "_blank", "noopener,noreferrer");
      this.setStatus("Join room opened");
      if (this.error) {
        this.error.textContent = "If Jitsi says no moderator has arrived, wait for the host to sign in and start the room.";
      }
    }
  }

  window.MyTvMovieWatchParty = {
    init(options) {
      const service = new WatchPartyService(options);
      service.render();
      return service;
    },
  };
})();
