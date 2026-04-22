/*
FILE: web/js/data_loader.js
VERSION: v1.0.0
UPDATED: 2026-03-15T04:28:23Z
CHANGE NOTES:
- Centralized shared catalog and inputs loading for the normalized main app runtime.
- Added in-memory caching to reduce repeated parse/load work across rebased views.
*/

import { loadJsonFirst } from './config_loader.js';

let catalogIndexPromise = null;
let calendarPromise = null;
let inputsPromise = null;
const detailPromises = new Map();

export async function loadCatalogIndexFirst(urls = ['../data/catalog_index.json']){
  if (!catalogIndexPromise) catalogIndexPromise = loadJsonFirst(urls);
  return catalogIndexPromise;
}

export async function loadCalendarFirst(urls = ['../data/calendar.json']){
  if (!calendarPromise) calendarPromise = loadJsonFirst(urls);
  return calendarPromise;
}

export async function loadCatalogDetailFirst(id, urls){
  const key = String(id ?? '').trim();
  if (!key) throw new Error('Catalog detail id is required');
  if (!detailPromises.has(key)){
    detailPromises.set(key, loadJsonFirst(Array.isArray(urls) && urls.length ? urls : [`../data/catalog_detail/${key}.json`]));
  }
  return detailPromises.get(key);
}

export async function loadInputsFirst(urls = ['../data/inputs.json', '../inputs.json']){
  if (!inputsPromise) inputsPromise = loadJsonFirst(urls);
  return inputsPromise;
}

export function clearDataLoaderCache(){
  catalogIndexPromise = null;
  calendarPromise = null;
  inputsPromise = null;
  detailPromises.clear();
}
