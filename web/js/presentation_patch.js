/*
FILE: web/js/presentation_patch.js
PURPOSE: Fix layout, episode images, dashboard truncation, focus issues.
*/

async function fetchJson(path){
  const r = await fetch(path,{cache:'no-store'});
  if(!r.ok) return null;
  return r.json();
}

function parseSE(text){
  const m = String(text||'').match(/S(\d+)E(\d+)/i);
  if(!m) return null;
  return {s:+m[1],e:+m[2]};
}

async function getEpisodeStill(showId,s,e){
  const d = await fetchJson(`../data/catalog_detail/${showId}.json`);
  if(!d) return null;
  const season = (d.seasons||[]).find(x=>x.season_number==s);
  const ep = (season?.episodes||[]).find(x=>x.episode_number==e);
  return ep?.still_local || ep?.still_path || null;
}

async function fixEpisodeImages(){
  const cards = document.querySelectorAll('[data-kind="episode"], .media-card--episode');
  for(const c of cards){
    const showId = c.getAttribute('data-show');
    let se = c.getAttribute('data-season');
    let ep = c.getAttribute('data-episode');
    if(!se || !ep){
      const txt = c.innerText;
      const parsed = parseSE(txt);
      if(parsed){se=parsed.s;ep=parsed.e;}
    }
    if(showId && se && ep){
      const img = c.querySelector('img');
      if(img){
        const still = await getEpisodeStill(showId,se,ep);
        if(still) img.src = still;
      }
    }
  }
}

function fixDashboardHeader(){
  const meta = document.getElementById('dashLastWeekMeta');
  if(meta){
    meta.style.marginLeft = '0';
  }
}

function trapModalFocus(){
  document.addEventListener('keydown',e=>{
    const modal = document.querySelector('#modalBack[style*="flex"]');
    if(!modal) return;
    if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key)){
      e.stopPropagation();
    }
  },true);
}

function removeDeadSpace(){
  document.body.classList.add('presentation-fixed');
}

async function run(){
  fixDashboardHeader();
  removeDeadSpace();
  trapModalFocus();
  await fixEpisodeImages();
}

window.addEventListener('load',run);
window.addEventListener('hashchange',run);
