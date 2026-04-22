FILE: reports/ui_component_audit/documentation_consolidation_plan.md
VERSION: v1.0
UPDATED: 2026-03-15T03:57:02Z
CHANGE NOTES:
- Created documentation consolidation plan for current repo state.
- Chose canonical README direction and archive/merge actions.
- Identified misplaced and contradictory docs.

# Documentation Consolidation Plan

## Canonical Documentation Set

The repo should converge to this minimal current documentation set:

1. `README.md`
   - canonical project entry point
2. `docs/ui_standardization/baseline_contract_v3.md`
   - canonical UX contract
3. one editor workflow document under `docs/`
   - canonical editing and pipeline instructions for `data/inputs.json`
4. one config document under `docs/`
   - current config/runtime behavior
5. one scripts/workflow document under `docs/` or root
   - current operational scripts only

## README Decision

### Canonical README

Use `README.md` as the single canonical README, but rewrite it to reflect current reality.

### Merge Inputs

Merge useful current content from:

- `README_my_TV_Movie.md`
- `scripts.md`
- `scripts/scripts.md`

### Archive/Retire

- `README_my_TV_Movie.md`: archive after merge
- `README.txt`: retire/archive

## Config Documentation Decision

`web/config.DOC.md` should not live under `web/` because it is documentation, not a browser-served asset.

Direction:

- move it to `docs/`
- narrow it to current config/runtime behavior
- clearly separate general app config from `watch_me`-specific tuning

## Current Stale or Contradictory Documentation

### Strongly Stale

- `README.md`
- `README_my_TV_Movie.md`
- `README.txt`

### Partially Current, Needs Cleanup

- `scripts.md`
- `scripts/scripts.md`
- `web/config.DOC.md`

### Historical, Not Authoritative

- `docs/spec/*`
- `docs/actual text of the ChatGPT responsesQ1-Q5.txt`
- older standardization drafts such as `baseline_contract_v2.md` and mockup notes where they conflict with baseline v3

These files may remain for archive/reference, but they must no longer be treated as architecture truth.

## Why Consolidation Is Required

The current docs create false requirements that directly fight the intended end state:

- season popup as mandatory
- icon strip as mandatory
- popup chain as immutable
- old text-list/parsed-json editing workflow

Those contradictions slow implementation because they make the repo appear to require behaviors that the locked baseline has already retired.

## Recommended Documentation Actions

1. Rewrite `README.md` as canonical entry point.
2. Move `web/config.DOC.md` to `docs/`.
3. Merge script workflow docs into one corrected operational guide.
4. Add a short archival note to `docs/spec/` declaring it historical/non-authoritative.
5. Keep `baseline_contract_v3.md` as the highest-priority UX contract reference.
