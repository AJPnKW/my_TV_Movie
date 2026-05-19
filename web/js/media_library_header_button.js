/*
FILE: web/js/media_library_header_button.js
VERSION: v0.7.0
UPDATED: 2026-05-18
CHANGE NOTES:
- Places the Media Library icon only inside the primary .nav view-icon row.
- Removes broad fallback placement that could append the icon into the logo/header/body area.
- Clears inline styles so the icon inherits the same nav styling as the other view icons.
*/
(function(){
  'use strict';
  if (window.__myTvMediaLibraryHeaderButtonLoaded) return;
  window.__myTvMediaLibraryHeaderButtonLoaded = true;

  function install(){
    const nav = document.querySelector('.top .nav, .nav[role="tablist"], .nav');
    if (!nav) return;

    let link = document.getElementById('mediaLibraryHeaderButton');
    if (!link) {
      link = document.createElement('a');
      link.id = 'mediaLibraryHeaderButton';
      link.textContent = '📚';
    }

    link.className = 'tab media-library-view-icon';
    link.href = './Media_Library.html';
    link.target = '_blank';
    link.rel = 'noopener';
    link.title = 'Media Library';
    link.setAttribute('aria-label', 'Media Library');
    link.setAttribute('data-label', 'Media Library');
    link.setAttribute('data-tab', 'media-library');
    link.setAttribute('role', 'tab');
    link.setAttribute('aria-selected', 'false');
    link.removeAttribute('style');

    const configTab = nav.querySelector('[data-tab="config"]');
    if (link.parentElement !== nav) {
      nav.insertBefore(link, configTab || null);
    } else if (configTab && link.nextElementSibling !== configTab) {
      nav.insertBefore(link, configTab);
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true });
  else install();
})();
