/*
FILE: web/js/presentation_fix_v2.js
VERSION: v1.0.0
UPDATED: 2026-04-18T00:00:00Z
CHANGE NOTES:
- Removes 'Last Week' label.
- Expands dashboard columns to include all episodes for each date.
- Uses episode stills for dashboard cards.
- Eliminates empty right-side gutter.
- Enforces modal focus ownership.
*/

async function fetchJson(path){
  try{
    const r = await fetch(path,{cache:'no-store'});
    if(!r.ok) return null;
    return await r.json();
  }catch{ return null; }
}

function parseDateKey(label){
  const m = String(label||'').match(/([A-Z]{3})\s+(\d{1,2}),\s+(\d{4})/i);
  if(!m) return null;
  const months = {JAN:1,FEB:2,MAR:3,APR:4,MAY:5,JUN:6,JUL:7,AUG:8,SEP:9,OCT:10,NOV:11,DEC:12};
  const mm = months[m[1].toUpperCase()];
  const dd = String(m[2]).padStart(2,'0');
  const yyyy = m[3];
  return `${yyyy}-${String(mm).padStart(2,'0')}-${dd}`;
}

function removeLastWeekLabel(){
  document.querySelectorAll('.dashhead h2').forEach(h=>{
    if(/last week/i.test(h.textContent||'')) h.remove();
  });
}

function fixHeaderLayout(){
  const head = document.querySelector('#panel-dashboard .dashhead');
  const meta = document.getElementById('dashLastWeekMeta');
  const nav = document.getElementById('dashLastWeekNav');
  if(head && meta && nav){
    const wrap = document.createElement('div');
    wrap.className = 'dashhead__range';
    wrap.appendChild(meta);
    wrap.appendChild(nav);
    head.innerHTML = '';
    head.appendChild(wrap);
  }
}

function fixGridWidth(){
  const colsWrap = document.getElementById('dashLastWeekCols');
  if(!colsWrap) return;
  const cols = colsWrap.querySelectorAll('.dashcol');
  if(cols.length){
    colsWrap.style.gridTemplateColumns = `repeat(${cols.length}, minmax(0,1fr))`;
  }
}

async function expandDashboard(){
  const cols = document.querySelectorAll('#dashLastWeekCols .dashcol');
  if(!cols.length) return;

  const cal = await fetchJson('../data/calendar.json');
  if(!cal || !cal.days) return;

  for(const col of cols){
    const head = col.querySelector('.dashcolhead');
    const stack = col.querySelector('.dashcolstack');
    if(!head || !stack) continue;

    const key = parseDateKey(head.textContent);
    if(!key) continue;

    const items = cal.days[key] || [];
    const existing = stack.querySelectorAll('.media-card').length;

    if(items.length > existing){
      const missing = items.slice(existing);
      for(const it of missing){
        const card = document.createElement('div');
        card.className = 'dashcard dashcard--injected';

        const img = (it.still_local || it.still_path || it.thumb || '') || '';
        const title = it.title || '';
        const meta = it.season && it.episode ? `S${String(it.season).padStart(2,'0')}E${String(it.episode).padStart(2,'0')}` : '';

        card.innerHTML = `
          <div class="media-card">
            <div class="media-card__poster">
              <img src="${img}" />
            </div>
            <div class="media-card__overlay">
              <div class="media-card__overlay-title">${title}</div>
              <div class="media-card__meta">${meta}</div>
            </div>
          </div>
        `;
        stack.appendChild(card);
      }
    }
  }
}

function trapFocus(){
  document.addEventListener('keydown',e=>{
    const modal = document.querySelector('.app-modal-backdrop[aria-hidden="false"]');
    if(!modal) return;
    if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key)){
      e.stopPropagation();
    }
  },true);
}

async function run(){
  removeLastWeekLabel();
  fixHeaderLayout();
  fixGridWidth();
  await expandDashboard();
  trapFocus();
}

window.addEventListener('load',run);
window.addEventListener('hashchange',run);
