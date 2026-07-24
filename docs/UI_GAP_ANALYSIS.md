# UI Gap Analysis

This file tracks active gaps only. Historical discussion belongs in archived docs or commit history. `docs/00_master_contract.html` is the source of truth.

## Closed in MC-2026-05-20.1

- Media Library link no longer relies on deferred injection for visible placement; it is present in the primary nav shell.
- Stale `Where to watch` fallback title text was removed from active Watch Source modal shells.
- Retired provider row and watch-option CSS selectors were removed from active CSS.
- Retired runtime popup/render shims were moved out of `web/js/` to the archive.
- Validation now fails if old provider row classes, stale popup titles, active shim files, or misplaced/occluded Media Library nav links return.

## Active Watch Items

- `web/js/app_runtime.js` remains broad and should only be split through existing owner modules when a concrete defect or scoped refactor requires it.
- Script lifecycle ownership should remain visible in the master contract and validators so old scripts do not become untracked active behavior.
- Feature-parity regressions in Shows/Movies browse controls are release blockers: Search, Current, filters, sorting, cards, and actions must stay available on phone, tablet, desktop, and TV-style viewports through the single canonical runtime path.

