/*
FILE: web/js/availability_ui.js
VERSION: v1.0.0
UPDATED: 2026-03-21T00:00:00Z
CHANGE NOTES:
- Centralized shared availability badge rendering for the normalized UI runtime.
*/

const STATUS_LABELS = Object.freeze({
  available: 'Available',
  unavailable: 'Unavailable',
  not_yet_released: 'Not Yet Released',
  unknown: 'Unknown'
});

export function normalizeAvailabilityStatus(value){
  const text = String(value || '').trim().toLowerCase();
  return STATUS_LABELS[text] ? text : 'unknown';
}

export function availabilityLabel(status){
  return STATUS_LABELS[normalizeAvailabilityStatus(status)];
}

export function availabilityBadgeHtml(status, options = {}){
  const normalized = normalizeAvailabilityStatus(status);
  const label = availabilityLabel(normalized);
  const classes = ['availability-badge', `availability-badge--${normalized}`];
  if (options.compact) classes.push('availability-badge--compact');
  if (options.extraClass) classes.push(String(options.extraClass));
  return `<span class="${classes.join(' ')}" data-availability-status="${normalized}">${label}</span>`;
}

if (typeof window !== 'undefined'){
  window.MyTVHubAvailabilityUi = Object.assign(window.MyTVHubAvailabilityUi || {}, {
    normalizeAvailabilityStatus,
    availabilityLabel,
    availabilityBadgeHtml
  });
}
