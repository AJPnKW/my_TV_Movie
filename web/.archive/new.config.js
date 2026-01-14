// =========================================================================================
// [FILE] web/config.js
// [PROJECT] my_TV_Movie (My TV Hub)
// [ROLE] Lightweight client config (no data schema dependencies)
// [UPDATED] 2025-12-22
// =========================================================================================

(function () {
  "use strict";

  // Optional runtime config.json (if present). Safe to omit.
  const DEFAULTS = {
    fallback_poster: "assets/fallback/poster_fallback.jpg",
    fallback_backdrop: "assets/fallback/backdrop_fallback.jpg",
    link_label_overrides: {
      vidsrc: "VidSrc",
      videasy: "VidEasy"
    }
  };

  function isObject(o) {
    return !!o && typeof o === "object" && !Array.isArray(o);
  }

  async function tryLoadConfigJson() {
    try {
      const res = await fetch("config.json", { cache: "no-cache" });
      if (!res.ok) return null;
      const cfg = await res.json();
      return isObject(cfg) ? cfg : null;
    } catch {
      return null;
    }
  }

  function merge(a, b) {
    const out = Object.assign({}, a);
    if (!isObject(b)) return out;

    for (const k of Object.keys(b)) {
      const v = b[k];
      if (isObject(v) && isObject(out[k])) out[k] = merge(out[k], v);
      else out[k] = v;
    }
    return out;
  }

  function safeStr(v, fallback = "") {
    return (typeof v === "string" && v.trim() !== "") ? v.trim() : fallback;
  }

  function getLinkLabel(key, cfg) {
    const k = safeStr(key, "");
    if (!k) return "Link";
    const map = isObject(cfg?.link_label_overrides) ? cfg.link_label_overrides : {};
    return safeStr(map[k.toLowerCase()], k);
  }

  function getFallbackPoster(cfg) {
    return safeStr(cfg?.fallback_poster, DEFAULTS.fallback_poster);
  }

  function getFallbackBackdrop(cfg) {
    return safeStr(cfg?.fallback_backdrop, DEFAULTS.fallback_backdrop);
  }

  // Expose to window for pages that want it (optional).
  async function init() {
    const cfgJson = await tryLoadConfigJson();
    const cfg = merge(DEFAULTS, cfgJson || {});
    window.MyTVHubConfig = {
      cfg,
      getLinkLabel: (k) => getLinkLabel(k, cfg),
      getFallbackPoster: () => getFallbackPoster(cfg),
      getFallbackBackdrop: () => getFallbackBackdrop(cfg)
    };
  }

  init();
})();
