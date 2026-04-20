# Codex Prompt — Availability Status Full Repo Implementation

You are working inside the live current repo for `my_TV_Movie`.

## Outcome
Implement a production-ready availability-status feature across the real current repo state.

## Critical execution rules
- Use the current repo as source of truth.
- Do not use legacy assumptions if the repo differs.
- Do not rebuild frameworks or create parallel systems if an existing one can be extended.
- Preserve paths, structures, naming, workflow patterns, and UI conventions already in the repo.
- Group interdependent changes into one coherent implementation pass, then one grouped fix pass if needed, then one grouped QA pass.
- Provide complete changed files, not snippets.
- Do not leave details unstated.
- Do not guess unknown paths or field names; inspect the repo and align to the actual current state.
- Update any stale design/baseline docs in the repo if they conflict with the implementation reality.

## Feature goal
Add a normalized `availability_status` capability for movies, shows, seasons, and episodes.

## Final status enum
- `not_yet_released`
- `available`
- `unavailable`
- `unknown`

## Design baseline to implement unless the repo has a stronger existing pattern
1. Keep `inputs.json` unchanged.
2. Keep source-of-truth outside `data.json`.
3. Add a separate availability source file.
4. Add a separate validator.
5. Add a separate enrichment pass after the current `data.json` build.
6. Write additive fields into `data.json`:
   - `availability_status`
   - `availability_checked_at`
   - `availability_source`
   - `availability_reason`
   - optional `primary_watch_url_tested`
7. Integrate rendering into the existing current page/component system for:
   - index/list pages
   - show cards
   - movie cards
   - season displays where applicable
   - episode rows
   - popups/details

## Mandatory repo inspection before implementation
Inspect and report:
- actual `data.json` path(s)
- actual build script(s) that create/update it
- actual entity key fields for movie/show/season/episode
- actual current page/component/helper files used by index/list/detail/card/episode rendering
- actual current workflow files that should chain or call this
- any existing availability/provider/watch-status related code that overlaps with this change
- any stale docs that would drift Codex if left unchanged

## Required file outcomes
Create or update the necessary real repo files for:
- availability source JSON
- validator script
- enrichment script
- workflow integration
- UI helper/render logic
- design/baseline/architecture docs
- QA/validation docs or reports if the repo pattern supports them

## Logic rules
- Future release date => `not_yet_released`
- Released + required primary URL passes validation => `available`
- Released + required primary URL fails or missing => `unavailable`
- Missing/indeterminate case => `unknown`
- Do not rely on broad inheritance alone; episode/season/show/movie may differ

## Validation rules
Must provide evidence for:
- Python compile success
- JSON parse success
- source file validation
- post-enrichment `data.json` validation
- UI visibility in the affected pages/views
- workflow compatibility
- changed file inventory

## Final required output from Codex
Provide:
1. exact files changed
2. exact docs added/updated
3. validation results
4. any follow-up gaps that remain
5. a downloadable patch/overlay bundle if supported by the environment
