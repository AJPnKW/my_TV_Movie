(function(){
  function hideBrokenImages(root){
    (root||document).querySelectorAll('img').forEach(function(img){
      var src=img.getAttribute('src')||'';
      if(!src||/undefined|null/i.test(src)){img.style.display='none';}
      img.onerror=function(){this.style.display='none';};
    });
  }
  function removeLastWeekLabels(root){
    (root||document).querySelectorAll('.dashhead h2,.dashhead .paneltitle,.dashcolhead,h2').forEach(function(el){
      if((el.textContent||'').trim().toLowerCase()==='last week'){el.textContent='';el.style.display='none';}
    });
  }
  function promoteEpisodeStills(root){
    (root||document).querySelectorAll('[data-kind="episode"],.media-card--episode,.calendar-item,.epcard').forEach(function(card){
      var still=card.getAttribute('data-still')||card.getAttribute('data-still-local')||card.getAttribute('data-still-path')||'';
      if(!still)return; var img=card.querySelector('img'); if(img&&img.getAttribute('src')!==still){img.setAttribute('src',still);}
    });
  }
  function cleanupBrokenLiteralNewline(){document.documentElement.innerHTML=document.documentElement.innerHTML.replace(/`r`n/g,'');}
  function run(){cleanupBrokenLiteralNewline();removeLastWeekLabels(document);promoteEpisodeStills(document);hideBrokenImages(document);}
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',run);}else{run();}
  window.addEventListener('load',run);
})();