/*
FILE: web/js/provider_popup_guard.js
VERSION: v1.1.0
UPDATED: 2026-05-18
CHANGE NOTES:
- Converts the provider popup guard from an active popup replacement into a passive DOM cleaner.
- Restores popup ownership to app_runtime.js / canonical runtime renderer.
- Does not intercept popcorn/watch-source clicks.
- Does not stop propagation.
- Does not generate fallback provider-only popup HTML.
- Removes only forbidden admin/status text and blocked/archived provider links from an already-rendered popup.
*/
(function(){
  'use strict';

  if (window.__myTvMovieProviderPopupGuardLoaded) return;
  window.__myTvMovieProviderPopupGuardLoaded = true;

  const PROVIDER_REGISTRY_URL = '../data/provider_registry.json';
  const BLOCKED_STATUSES = new Set(['blocked', 'archived']);
  const FORBIDDEN_TEXTS = new Set([
    'active candidate from user findings',
    'active',
    'degraded',
    'blocked',
    'archived'
  ]);
  const ADMIN_SELECTOR = [
    '.trailer-watch-source__note',
    '.provider-note',
    '.provider-status',
    '.watch-provider-note',
    '.watch-provider-status',
    '[data-provider-note]',
    '[data-provider-status]',
    '[data-admin-note]',
    '[data-health-note]'
  ].join(',');

  let providerRegistry = null;

  function text(value){
    return value == null ? '' : String(value).trim();
  }

  function lower(value){
    return text(value).toLowerCase();
  }

  function normalizeDomain(value){
    const raw = text(value);
    if (!raw) return '';
    try {
      const url = raw.includes('://') ? new URL(raw) : new URL('https://' + raw);
      return url.hostname.replace(/^www\./i, '').toLowerCase();
    } catch (_) {
      return raw.replace(/^https?:\/\//i, '').replace(/^www\./i, '').split('/')[0].toLowerCase();
    }
  }

  function registryItems(registry){
    if (!registry) return [];
    if (Array.isArray(registry)) return registry;
    if (Array.isArray(registry.providers)) return registry.providers;
    if (Array.isArray(registry.items)) return registry.items;
    if (registry.providers && typeof registry.providers === 'object') return Object.values(registry.providers);
    return [];
  }

  function providerStatusForUrl(href){
    const domain = normalizeDomain(href);
    if (!domain) return '';
    const item = registryItems(providerRegistry).find(candidate => {
      const candidateDomain = normalizeDomain(
        candidate.domain ||
        candidate.provider_domain ||
        candidate.url ||
        candidate.href ||
        candidate.url_pattern ||
        candidate.provider_id
      );
      return candidateDomain && (domain === candidateDomain || domain.endsWith('.' + candidateDomain));
    });
    return lower(item && item.status);
  }

  function removeAdminText(root){
    root.querySelectorAll(ADMIN_SELECTOR).forEach(node => node.remove());

    Array.from(root.querySelectorAll('span,div,p,small,em,strong')).forEach(node => {
      if (node.children.length > 0) return;
      const value = lower(node.textContent);
      if (FORBIDDEN_TEXTS.has(value)) node.remove();
    });
  }

  function removeBlockedProviders(root){
    root.querySelectorAll('a[href],button[data-href],[data-provider-url]').forEach(node => {
      const href = node.getAttribute('href') || node.getAttribute('data-href') || node.getAttribute('data-provider-url') || '';
      const status = providerStatusForUrl(href);
      if (BLOCKED_STATUSES.has(status)) {
        const row = node.closest('.trailer-watch-source,.watch-provider,.provider-row,.provider-card,li') || node;
        row.remove();
      }
    });
  }

  function cleanProviderPopup(){
    const roots = [
      document.getElementById('providerBody'),
      document.getElementById('providerBack'),
      document.querySelector('[data-popup="watch-source"]'),
      document.querySelector('.watch-source-popup'),
      document.querySelector('.app-modal-card--provider')
    ].filter(Boolean);

    roots.forEach(root => {
      removeAdminText(root);
      removeBlockedProviders(root);
    });
  }

  function installObserver(){
    const observer = new MutationObserver(cleanProviderPopup);
    observer.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
  }

  function loadRegistry(){
    return fetch(PROVIDER_REGISTRY_URL, { cache: 'no-cache' })
      .then(response => response.ok ? response.json() : null)
      .then(payload => { providerRegistry = payload; })
      .catch(() => { providerRegistry = null; });
  }

  function install(){
    loadRegistry().finally(cleanProviderPopup);
    installObserver();
    document.addEventListener('click', () => setTimeout(cleanProviderPopup, 0), false);
    document.addEventListener('keyup', event => {
      if (event.key === 'Escape') setTimeout(cleanProviderPopup, 0);
    }, false);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, { once: true });
  } else {
    install();
  }
})();
