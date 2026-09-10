/*
FILE: web/js/media_library_header_button.js
VERSION: v0.8.1
UPDATED: 2026-09-10
CHANGE NOTES:
- Keeps the Media Library icon inside the primary navigation row.
- Keeps the Release Calendar as a canonical primary-nav view immediately after Movies.
- Uses a distinct New Releases icon so Release Calendar is visually different from the schedule Calendar.
- Normalizes both links at runtime so active app shells stay navigation-consistent.
*/
(function(){
  'use strict';
  if (window.__myTvMediaLibraryHeaderButtonLoaded) return;
  window.__myTvMediaLibraryHeaderButtonLoaded = true;

  function install(){
    const nav = document.querySelector('.top > .nav[role="tablist"][aria-label="Primary"]');
    if (!nav) return;

    let releaseLink = nav.querySelector('[data-tab="release-calendar"]');
    if (!releaseLink) {
      releaseLink = document.createElement('a');
      const calendarTab = nav.querySelector('[data-tab="calendar"]');
      nav.insertBefore(releaseLink, calendarTab || null);
    }
    releaseLink.className = 'tab release-calendar-view-icon';
    releaseLink.textContent = '🆕';
    releaseLink.href = './release_calendar.html';
    releaseLink.title = 'Release Calendar';
    releaseLink.setAttribute('aria-label', 'Release Calendar');
    releaseLink.setAttribute('data-label', 'Release Calendar');
    releaseLink.setAttribute('data-tab', 'release-calendar');
    releaseLink.setAttribute('role', 'tab');
    const isReleaseCalendar = document.body?.dataset?.page === 'release-calendar';
    releaseLink.classList.toggle('active', isReleaseCalendar);
    releaseLink.setAttribute('aria-selected', isReleaseCalendar ? 'true' : 'false');
    releaseLink.removeAttribute('style');

    let link = document.getElementById('mediaLibraryHeaderButton');
    if (!link) {
      link = document.createElement('a');
      link.id = 'mediaLibraryHeaderButton';
    }

    link.className = 'tab media-library-view-icon';
    link.textContent = '📚';
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
