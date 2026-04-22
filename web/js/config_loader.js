/*
FILE: web/js/config_loader.js
VERSION: v1.0.0
UPDATED: 2026-03-15T04:28:23Z
CHANGE NOTES:
- Centralized shared config loading for the normalized main app runtime.
- Added shared JSON fetch fallback handling for main app views.
*/

const configCache = new Map();

export async function loadJsonFirst(urls){
  let lastError = null;
  for (const url of urls){
    try {
      const response = await fetch(url, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      lastError = new Error(`${url}: ${error.message || error}`);
    }
  }
  throw lastError || new Error('No loadable JSON source found.');
}

export async function loadConfigFirst(urls = ['./config.json', '../web/config.json']){
  const cacheKey = urls.join('|');
  if (configCache.has(cacheKey)) return configCache.get(cacheKey);
  const cfg = await loadJsonFirst(urls);
  configCache.set(cacheKey, cfg);
  return cfg;
}
