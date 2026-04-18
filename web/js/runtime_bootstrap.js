/*
FILE: web/js/runtime_bootstrap.js
VERSION: v1.0.0
UPDATED: 2026-04-18T00:00:00Z
CHANGE NOTES:
- Stabilizes shared-module boot order before app_runtime.js executes.
- Prevents startup failures when runtime expects window.MyTVHubSharedModules.
*/

import * as configLoader from './config_loader.js';
import * as dataLoader from './data_loader.js';
import * as availabilityUi from './availability_ui.js';
import * as cardRenderer from './card_renderer.js';
import * as popupController from './popup_controller.js';
import * as actionBar from './action_bar.js';
import '../config.js';

const existing = window.MyTVHubSharedModules && typeof window.MyTVHubSharedModules === 'object'
  ? window.MyTVHubSharedModules
  : {};

window.MyTVHubSharedModules = Object.freeze({
  ...existing,
  configLoader,
  dataLoader,
  availabilityUi,
  cardRenderer,
  popupController,
  actionBar
});

cardRenderer.applyRuntimeContract(document);
actionBar.applyRuntimeContract(document);
popupController.applyRuntimeContract(document);
