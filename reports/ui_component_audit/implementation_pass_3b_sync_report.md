# Implementation Pass 3b Sync Report

## Purpose

Finish the family sync by aligning `web/shows.html` and `web/movies.html` to the corrected baseline already implemented in `web/index.html`.

## Source Of Truth

- `web/index.html`
- `docs/ui_standardization/baseline_contract_v3.md`

## Sync Applied

- Replaced the shared style and script blocks in `web/shows.html` and `web/movies.html` from the corrected `web/index.html` baseline.
- Preserved page-local title and shell markup outside the shared blocks.

## Baseline Elements Confirmed In Family

- Shared ordered action bar
- Popup bullet-selection watch-status control
- Provider logo fallback chips
- Corrected show-open wiring
- Guarded episode rating display
- No inline `watchstatusband` path
- Popcorn in the action bar where applicable

## Validation Summary

- `web/index.html`, `web/shows.html`, and `web/movies.html` all contain `action_bar`
- `web/shows.html` and `web/movies.html` no longer contain `watchstatusband`
- `status_set` popup status control wiring exists in all three
- `providerchip.fallback-only` fallback styling exists in all three
- No deferred surfaces were modified in this sync pass

