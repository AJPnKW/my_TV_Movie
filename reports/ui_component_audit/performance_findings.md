FILE: reports/ui_component_audit/performance_findings.md
VERSION: v1.0
UPDATED: 2026-03-15T03:57:02Z
CHANGE NOTES:
- Created performance findings focused on repeated payloads, loads, and UI render costs.
- Captured the specific duplication patterns slowing stabilization.
- Separated immediate performance risks from later optimization work.

# Performance Findings

## Executive Summary

The current performance problem is architectural duplication before it is algorithmic inefficiency. The app repeatedly ships and executes large inline runtime copies, reloads large shared data payloads, and rebinds many listeners per page. This slows initial load, increases drift, and makes optimization expensive because it must be repeated in multiple files.

## Primary Findings

### 1. Repeated Large Inline CSS/JS Duplication

Observed page payload duplication:

- `web/index.html`: ~58 KB inline CSS, ~171 KB inline JS
- `web/shows.html`: ~58 KB inline CSS, ~171 KB inline JS
- `web/movies.html`: ~58 KB inline CSS, ~171 KB inline JS
- `web/calendar.html`: ~55 KB inline CSS, ~157 KB inline JS
- `web/discover.html`: ~55 KB inline CSS, ~164 KB inline JS
- `web/config.html`: ~54 KB inline CSS, ~156 KB inline JS

Impact:

- larger HTML transfer and parse cost
- repeated JS parse/compile cost
- repeated duplication of bugs and fixes
- no browser-level caching of shared runtime as a separate asset

Severity: high

### 2. Repeated Full Data Payload Loading

`data/data.json` is approximately 14.4 MB and is used across many user-facing views.

Impact:

- high initial JSON parse cost
- repeated page-by-page fetch/parse cost
- slower interaction on pages that do not need the full catalog

Severity: high

### 3. Repeated Config/Data Fetch Patterns

Major monolith pages repeatedly fetch:

- runtime health/inputs endpoints
- config
- catalog data

This logic is copied rather than centralized.

Impact:

- redundant network work
- redundant error handling code
- harder caching strategy

Severity: medium-high

### 4. Repeated Event Wiring

Observed listener counts:

- corrected trio: about 51 listeners per page
- calendar: about 55 listeners
- discover: about 52 listeners
- config: about 50 listeners

Impact:

- repeated binding/unbinding costs
- more failure points after rerenders
- harder reasoning about state ownership

Severity: medium

### 5. Large DOM/Card Render Cost

The app renders many card-heavy surfaces directly from large catalog payloads inside monolithic scripts.

Impact:

- slow first render on dense views
- render cost scales with catalog growth
- view-specific optimizations are hard because render logic is copied

Severity: medium-high

### 6. Missing Provider Logo / Asset Churn

The corrected trio now has provider fallback behavior, but the broader app family still relies on a fragmented asset/config model.

Impact:

- potential 404 churn for missing logos
- unnecessary image decode attempts
- inconsistent fallback rendering

Severity: medium

### 7. Config Path and Metadata Drift

`web/config.json` still contains stale metadata such as the retired hot dog icon mapping and path assumptions that do not fully match `web/config.js` validation expectations.

Impact:

- wasted runtime checks
- confusing asset fallback behavior
- harder cache correctness

Severity: medium

## Performance Root Causes

1. File-cloned frontend architecture.
2. No extracted shared runtime bundle.
3. Oversized all-purpose runtime payload (`data/data.json`) for many surfaces.
4. View logic duplication across separate HTML pages.
5. Residual legacy paths for editors/docs/config/assets.

## Low-Risk Corrective Plan

### Phase 1

- extract shared JS runtime from corrected trio
- extract shared CSS used by corrected trio
- centralize config and catalog loading helpers

### Phase 2

- move calendar/discover/config to shared runtime
- remove old `watchstatusband` code paths entirely

### Phase 3

- split large catalog consumption by view needs where possible
- add better asset existence/fallback normalization
- reduce rerender/listener duplication

## Not Recommended

- micro-optimizing old clone pages before runtime normalization
- continuing to patch large inline duplicates independently
- treating calendar performance separately from architecture drift
