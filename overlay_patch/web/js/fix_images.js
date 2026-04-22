(function(){
  async function fetchJson(path){try{const r=await fetch(path,{cache:'no-store'});if(!r.ok)return null;return await r.json();}catch{return null;}}
  function parseDateKey(text){
    const m=String(text||'').match(/([A-Z]{3})\s+(\d{1,2}),\s+(\d{4})/i);
    if(!m) return null;
    const map={JAN:1,FEB:2,MAR:3,APR:4,MAY:5,JUN:6,JUL:7,AUG:8,SEP:9,OCT:10,NOV:11,DEC:12};
    return `${m[3]}-${String(map[m[1].toUpperCase()]||0).padStart(2,'0')}-${String(m[2]).padStart(2,'0')}`;
  }
  function removeLastWeekHeading(){
    document.querySelectorAll('.dashhead h2').forEach(h=>{ if(/last week/i.test(h.textContent||'')) h.remove(); });
  }
  function hardenImages(){
    document.querySelectorAll('img').forEach(img=>{
      img.loading='lazy';
      img.onerror=function(){ this.style.visibility='hidden'; };
    });
  }
  async function expandDashboardFromCalendar(){
    const wrap=document.querySelector('#dashLastWeekCols');
    if(!wrap) return;
    const data=await fetchJson('../data/calendar.json');
    if(!data||!data.days) return;
    const cols=wrap.querySelectorAll('.dashcol');
    cols.forEach(col=>{
      const head=col.querySelector('.dashcolhead');
      const stack=col.querySelector('.dashcolstack');
      if(!head||!stack) return;
      const key=parseDateKey(head.textContent);
      if(!key||!Array.isArray(data.days[key])) return;
      const expected=data.days[key];
      const existing=stack.querySelectorAll('.media-card,.dashcard').length;
      if(expected.length<=existing) return;
      expected.slice(existing).forEach(item=>{
        const card=document.createElement('div');
        card.className='dashcard dashcard--injected';
        const img=(item.still_local||item.still_path||item.thumb||item.image||item.poster_local||item.poster_path||'');
        const title=(item.title||item.name||'').replace(/</g,'&lt;');
        const meta=(item.show_title||item.series||item.subtitle||item.air_time||'').replace(/</g,'&lt;');
        card.innerHTML=`<div class="media-card media-card--episode"><div class="media-card__poster">${img?`<img src="${img}">`:''}</div><div class="media-card__overlay"><div class="media-card__overlay-title">${title}</div><div class="media-card__overlay-meta">${meta}</div></div></div>`;
        stack.appendChild(card);
      });
    });
  }
  function fixEpisodeStillPriority(){
    document.querySelectorAll('[data-kind="episode"], .media-card--episode, .epcard, .calendar-item').forEach(card=>{
      const still=card.getAttribute('data-still')||card.getAttribute('data-still-local')||card.dataset?.still||card.dataset?.stillLocal;
      const img=card.querySelector('img');
      if(still&&img&&img.src!==still) img.src=still;
    });
  }
  async function run(){
    removeLastWeekHeading();
    hardenImages();
    fixEpisodeStillPriority();
    await expandDashboardFromCalendar();
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', run, {once:true}); else run();
  window.addEventListener('load', run, {once:true});
})();
