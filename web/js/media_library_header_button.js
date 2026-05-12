/*
FILE: web/js/media_library_header_button.js
VERSION: v0.6.8
UPDATED: 2026-05-11
CHANGE NOTES:
- Adds a Media Library view icon to the app header without rebuilding the shell.
*/
(function(){
  'use strict';
  if (window.__myTvMediaLibraryHeaderButtonLoaded) return;
  window.__myTvMediaLibraryHeaderButtonLoaded = true;
  function install(){
    if (document.getElementById('mediaLibraryHeaderButton')) return;
    const host = document.querySelector('.view-icons,.view-icon-set,.header-actions,.topbar-actions,.app-header,.site-header,header') || document.body;
    const link = document.createElement('a');
    link.id = 'mediaLibraryHeaderButton';
    link.className = 'view-icon media-library-view-icon';
    link.href = './Media_Library.html';
    link.target = '_blank';
    link.rel = 'noopener';
    link.title = 'Recorded Media Library';
    link.setAttribute('aria-label','Recorded Media Library');
    link.textContent = '📚';
    Object.assign(link.style, {
      display:'inline-flex',alignItems:'center',justifyContent:'center',width:'34px',height:'34px',borderRadius:'10px',
      textDecoration:'none',fontSize:'18px',marginLeft:'6px',background:'rgba(20,40,76,.85)',border:'1px solid rgba(120,232,255,.35)'
    });
    host.appendChild(link);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once:true});
  else install();
})();
