/*
FILE: web/js/data_loader.js
VERSION: v1.0.0
UPDATED: 2026-03-15T04:28:23Z
CHANGE NOTES:
- Centralized shared catalog and inputs loading for the normalized main app runtime.
- Added in-memory caching to reduce repeated parse/load work across rebased views.
*/

import { loadJsonFirst } from './config_loader.js';

let catalogPromise = null;
let inputsPromise = null;

export async function loadCatalogFirst(urls = ['../data/data.json']){
  if (!catalogPromise) catalogPromise = loadJsonFirst(urls);
  return catalogPromise;
}

export async function loadInputsFirst(urls = ['../data/inputs.json', '../inputs.json']){
  if (!inputsPromise) inputsPromise = loadJsonFirst(urls);
  return inputsPromise;
}

export function clearDataLoaderCache(){
  catalogPromise = null;
  inputsPromise = null;
}