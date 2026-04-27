(function(){
'use strict';
const KEY='mytv_watch_state_v1';
function load(){try{return JSON.parse(localStorage.getItem(KEY)||'{}')}catch{return {}}}
function save(data){localStorage.setItem(KEY,JSON.stringify(data))}
function toggle(id,type){const data=load();const key=type+':'+id;data[key]=!data[key];save(data);return data[key]}
document.addEventListener('click',function(e){
const btn=e.target.closest('[data-watch-state-action]');
if(!btn)return;
const id=btn.getAttribute('data-id');
const action=btn.getAttribute('data-watch-state-action');
if(!id)return;
if(action==='toggle-watch-list')toggle(id,'watch_list');
if(action==='toggle-watched-status')toggle(id,'watched_status');
});
})();