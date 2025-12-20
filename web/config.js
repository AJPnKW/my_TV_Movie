/* =========================================================================================
[FILE] web/config.js
[PROJECT] my_TV_Movie (My TV Hub)
[ROLE] Config loader + Config View renderer helpers (for SPA integration)
[VERSION] v4.6.0
[UPDATED] 2025-12-19_00-00-00
[BUILD] 00.00.00
[OWNER] Andrew & Brant (internal)

[PHASE 4.x MASTER OVERRIDE APPLIED]
- TRUE SPA: index.html is the ONLY entry point (this file is a module used by SPA).
- No multi-page routing / no hash routing / no external routing.
- No new files invented; this file must be usable when included.
- Canonical asset hierarchy ONLY (assets/...); never reference deprecated image/ folder.
- data.json load-once, read-only (not handled here).
- Errors must surface visually; no silent failures.
- Popups exist globally (not implemented here).

[EXPORT]
- window.MyTVHubConfig.load_config_once()
- window.MyTVHubConfig.get_config()
- window.MyTVHubConfig.validate_config(cfg)
- window.MyTVHubConfig.render_config_view(rootEl, cfg, opts)

[NOTES]
- web/config.json is the authoritative source of truth for streaming base URLs, sizing, cache layout.
- This file does not mutate config.json; it only reads + validates + renders.
========================================================================================= */

(function () {
  "use strict";

  // -----------------------------
  // Global namespace (stable)
  // -----------------------------
  const NS = (window.MyTVHubConfig = window.MyTVHubConfig || Object.create(null));

  // -----------------------------
  // Internal state (load-once)
  // -----------------------------
  let _config_loaded = false;
  let _config_frozen = null;

  // -----------------------------
  // Utilities
  // -----------------------------
  function _to_str(v) {
    return (typeof v === "string") ? v : "";
  }

  function _is_obj(v) {
    return !!v && typeof v === "object" && !Array.isArray(v);
  }

  function _clone_json_safe(obj) {
    // Deterministic, JSON-safe clone for display without mutation exposure
    try { return JSON.parse(JSON.stringify(obj)); } catch (_) { return null; }
  }

  function _escape_html(s) {
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function _surface_error(message) {
    // Error Handling rule: visible; no silent failures.
    // Try: global #error-surface (index.html pattern), else inline alert box.
    const msg = String(message || "Unknown error");

    const surf = document.getElementById("error-surface");
    const surfMsg = document.getElementById("error-msg");
    if (surf && surfMsg) {
      surfMsg.textContent = msg;
      surf.style.display = "inline-flex";
      return;
    }

    // Inline fallback (deterministic)
    const existing = document.getElementById("config-inline-error");
    if (existing) {
      existing.textContent = msg;
      existing.style.display = "block";
      return;
    }

    // Last resort: still visible
    // (No silent failures; but avoid blocking alerts unless unavoidable)
    console.error(msg);
  }

  function _clear_error_surface() {
    const surf = document.getElementById("error-surface");
    const surfMsg = document.getElementById("error-msg");
    if (surf && surfMsg) {
      surfMsg.textContent = "";
      surf.style.display = "none";
    }
    const existing = document.getElementById("config-inline-error");
    if (existing) {
      existing.textContent = "";
      existing.style.display = "none";
    }
  }

  async function _fetch_text(url) {
    const resp = await fetch(url, { cache: "no-store" });
    if (!resp.ok) {
      throw new Error(`Failed to load ${url} (${resp.status})`);
    }
    return await resp.text();
  }

  function _parse_json(text, label) {
    try { return JSON.parse(text); }
    catch (e) {
      throw new Error(`Invalid JSON in ${label}: ${e && e.message ? e.message : e}`);
    }
  }

  // -----------------------------
  // Canonical asset hierarchy (binding)
  // -----------------------------
  const CANON_ASSETS = Object.freeze({
    posters: Object.freeze({
      shows: "assets/posters/shows/",
      seasons: "assets/posters/seasons/",
      movies: "assets/posters/movies/",
      collections: "assets/posters/collections/"
    }),
    backdrops: Object.freeze({
      shows: "assets/backdrops/shows/",
      movies: "assets/backdrops/movies/"
    }),
    stills: Object.freeze({
      episodes: "assets/stills/episodes/"
    }),
    logos: Object.freeze({
      services: "assets/logos/services/",
      services_archive: "assets/logos/services/archive/",
      networks: "assets/logos/networks/",
      channels: "assets/logos/channels/"
    }),
    icons: Object.freeze({
      services: "assets/icons/services/",
      ui: "assets/icons/ui/"
    }),
    fallback: Object.freeze({
      posters: "assets/fallback/posters/",
      backdrops: "assets/fallback/backdrops/",
      stills: "assets/fallback/stills/",
      logos: "assets/fallback/logos/",
      icons: "assets/fallback/icons/"
    }),
    collections: "assets/collections/"
  });

  function _contains_deprecated_image_folder(obj) {
    // Detect any string value containing "image/" (deprecated, must not be referenced)
    const seen = new Set();
    function walk(v) {
      if (v === null || v === undefined) return false;
      if (typeof v === "string") return v.includes("image/");
      if (typeof v !== "object") return false;
      if (seen.has(v)) return false;
      seen.add(v);
      if (Array.isArray(v)) {
        for (const x of v) if (walk(x)) return true;
        return false;
      }
      for (const k of Object.keys(v)) {
        if (walk(v[k])) return true;
      }
      return false;
    }
    return walk(obj);
  }

  // -----------------------------
  // Validation (minimal + concrete)
  // -----------------------------
  function validate_config(cfg) {
    const errors = [];
    const warnings = [];

    if (!_is_obj(cfg)) {
      errors.push("config.json root must be an object.");
      return { ok: false, errors, warnings };
    }

    // Minimal structural expectations (non-rewrite; config.json is authoritative)
    // We validate presence/types when provably required for usability.
    // NOTE: Do not invent schema; only validate common-sense keys used by scripts/UI.
    if (!_is_obj(cfg.streaming)) {
      warnings.push("Missing or invalid 'streaming' object.");
    } else {
      // base URLs should be non-empty strings if present
      for (const k of Object.keys(cfg.streaming)) {
        const v = cfg.streaming[k];
        if (typeof v === "string") {
          const s = v.trim();
          if (!s) warnings.push(`streaming.${k} is an empty string.`);
        }
      }
    }

    if (!_is_obj(cfg.images)) {
      warnings.push("Missing or invalid 'images' object.");
    } else {
      // sizing should be coherent if present
      if (_is_obj(cfg.images.sizes)) {
        for (const k of Object.keys(cfg.images.sizes)) {
          const v = cfg.images.sizes[k];
          if (typeof v !== "number" || !Number.isFinite(v) || v <= 0) {
            warnings.push(`images.sizes.${k} should be a positive number.`);
          }
        }
      }
    }

    // image_cache.folders should align with canonical assets/ hierarchy when present
    if (_is_obj(cfg.image_cache)) {
      const folders = cfg.image_cache.folders;
      if (_is_obj(folders)) {
        for (const k of Object.keys(folders)) {
          const p = _to_str(folders[k]).trim();
          if (!p) {
            warnings.push(`image_cache.folders.${k} is empty.`);
            continue;
          }
          // Canonical rule: never "image/".
          if (p.includes("image/")) {
            errors.push(`Deprecated folder reference in image_cache.folders.${k}: "${p}"`);
          }
          // Strong preference: assets/ (binding for this project)
          if (!p.startsWith("assets/")) {
            warnings.push(`image_cache.folders.${k} does not start with "assets/": "${p}"`);
          }
        }
      } else if (folders !== undefined) {
        warnings.push("image_cache.folders exists but is not an object.");
      }
    } else {
      warnings.push("Missing or invalid 'image_cache' object.");
    }

    // Detect deprecated "image/" anywhere in config (binding)
    if (_contains_deprecated_image_folder(cfg)) {
      errors.push('config.json contains deprecated "image/" folder references.');
    }

    return { ok: errors.length === 0, errors, warnings };
  }

  // -----------------------------
  // Load-once
  // -----------------------------
  async function load_config_once() {
    if (_config_loaded && _config_frozen) return _config_frozen;

    _clear_error_surface();

    const text = await _fetch_text("./config.json");
    const parsed = _parse_json(text, "web/config.json");

    const result = validate_config(parsed);
    if (!result.ok) {
      // Visible error surfacing, but still freeze + return config (authoritative)
      _surface_error(`Config validation error(s): ${result.errors.join(" | ")}`);
    } else if (result.warnings.length > 0) {
      _surface_error(`Config warning(s): ${result.warnings.join(" | ")}`);
    }

    _config_frozen = Object.freeze(parsed);
    _config_loaded = true;
    return _config_frozen;
  }

  function get_config() {
    return _config_frozen;
  }

  // -----------------------------
  // Render Config View (SPA helper)
  // -----------------------------
  function render_config_view(rootEl, cfg, opts) {
    _clear_error_surface();

    const root = rootEl;
    const options = _is_obj(opts) ? opts : Object.create(null);

    if (!root || !(root instanceof Element)) {
      _surface_error("render_config_view: root element is missing/invalid.");
      return;
    }

    // Use provided cfg, else global loaded cfg
    const config = cfg || _config_frozen;

    // Clear root
    root.innerHTML = "";

    // Inline error box (fallback if global surface absent)
    const inlineErr = document.createElement("div");
    inlineErr.id = "config-inline-error";
    inlineErr.style.display = "none";
    inlineErr.style.border = "1px solid rgba(255, 91, 91, 0.35)";
    inlineErr.style.background = "rgba(255, 91, 91, 0.10)";
    inlineErr.style.color = "#ffd7d7";
    inlineErr.style.borderRadius = "12px";
    inlineErr.style.padding = "10px 12px";
    inlineErr.style.fontSize = "13px";
    inlineErr.style.marginTop = "10px";

    const header = document.createElement("div");
    header.className = "view-title";
    header.innerHTML = `<h1>Config</h1><div class="meta">web/config.json (authoritative)</div>`;

    const hint = document.createElement("div");
    hint.className = "hint";
    hint.textContent =
      "This view displays the authoritative configuration used by UI and scripts. " +
      'No manual edits to data.json. Canonical assets only (assets/...).';

    root.appendChild(header);
    root.appendChild(hint);
    root.appendChild(inlineErr);

    if (!config) {
      const msg = document.createElement("div");
      msg.className = "hint";
      msg.textContent = "Config not loaded yet.";
      root.appendChild(msg);
      _surface_error("Config not loaded. Call load_config_once() first.");
      return;
    }

    const val = validate_config(config);

    // Summary pills
    const pills = document.createElement("div");
    pills.style.display = "flex";
    pills.style.flexWrap = "wrap";
    pills.style.gap = "10px";
    pills.style.marginTop = "12px";

    const pillOk = document.createElement("div");
    pillOk.className = "pill";
    pillOk.textContent = val.ok ? "VALIDATION: OK" : "VALIDATION: ERRORS";
    if (val.ok) pillOk.classList.add("badge--ok");

    const pillWarn = document.createElement("div");
    pillWarn.className = "pill";
    pillWarn.textContent = `WARNINGS: ${val.warnings.length}`;

    const pillErr = document.createElement("div");
    pillErr.className = "pill";
    pillErr.textContent = `ERRORS: ${val.errors.length}`;

    pills.appendChild(pillOk);
    pills.appendChild(pillWarn);
    pills.appendChild(pillErr);

    root.appendChild(pills);

    // Errors/warnings (visible)
    if (!val.ok) {
      inlineErr.style.display = "block";
      inlineErr.textContent = `Config validation error(s): ${val.errors.join(" | ")}`;
    } else if (val.warnings.length > 0) {
      inlineErr.style.display = "block";
      inlineErr.textContent = `Config validation warning(s): ${val.warnings.join(" | ")}`;
    }

    // Canonical assets reference panel
    const canon = document.createElement("div");
    canon.className = "card";
    canon.style.marginTop = "12px";
    canon.innerHTML =
      `<div class="card-title">Canonical asset hierarchy (binding)</div>` +
      `<div class="card-sub">No deprecated "image/" folder. UI and scripts must use these paths.</div>`;

    const canonPre = document.createElement("pre");
    canonPre.style.margin = "10px 0 0 0";
    canonPre.style.whiteSpace = "pre";
    canonPre.style.overflow = "auto";
    canonPre.style.border = "1px solid rgba(255,255,255,0.10)";
    canonPre.style.background = "rgba(0,0,0,0.18)";
    canonPre.style.borderRadius = "12px";
    canonPre.style.padding = "10px 12px";
    canonPre.style.fontFamily = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace";
    canonPre.style.fontSize = "12px";
    canonPre.textContent =
      [
        CANON_ASSETS.posters.shows,
        CANON_ASSETS.posters.seasons,
        CANON_ASSETS.posters.movies,
        CANON_ASSETS.posters.collections,
        "",
        CANON_ASSETS.backdrops.shows,
        CANON_ASSETS.backdrops.movies,
        "",
        CANON_ASSETS.stills.episodes,
        "",
        CANON_ASSETS.logos.services,
        CANON_ASSETS.logos.services_archive,
        CANON_ASSETS.logos.networks,
        CANON_ASSETS.logos.channels,
        "",
        CANON_ASSETS.icons.services,
        CANON_ASSETS.icons.ui,
        "",
        CANON_ASSETS.fallback.posters,
        CANON_ASSETS.fallback.backdrops,
        CANON_ASSETS.fallback.stills,
        CANON_ASSETS.fallback.logos,
        CANON_ASSETS.fallback.icons,
        "",
        CANON_ASSETS.collections
      ].join("\n");

    canon.appendChild(canonPre);
    root.appendChild(canon);

    // Raw config view
    const raw = document.createElement("div");
    raw.className = "card";
    raw.style.marginTop = "12px";
    raw.innerHTML =
      `<div class="card-title">config.json (read-only)</div>` +
      `<div class="card-sub">Displayed for verification. This view does not mutate config.</div>`;

    const pre = document.createElement("pre");
    pre.style.margin = "10px 0 0 0";
    pre.style.whiteSpace = "pre";
    pre.style.overflow = "auto";
    pre.style.maxHeight = options.max_height ? String(options.max_height) : "360px";
    pre.style.border = "1px solid rgba(255,255,255,0.10)";
    pre.style.background = "rgba(0,0,0,0.18)";
    pre.style.borderRadius = "12px";
    pre.style.padding = "10px 12px";
    pre.style.fontFamily = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace";
    pre.style.fontSize = "12px";

    const safeClone = _clone_json_safe(config);
    pre.textContent = safeClone ? JSON.stringify(safeClone, null, 2) : _escape_html(String(config));

    raw.appendChild(pre);
    root.appendChild(raw);
  }

  // -----------------------------
  // Exports
  // -----------------------------
  NS.load_config_once = load_config_once;
  NS.get_config = get_config;
  NS.validate_config = validate_config;
  NS.render_config_view = render_config_view;

  // No auto-execution here (module helper only).
})();
