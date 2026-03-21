FILE: reports/ui_component_audit/full_scope_architecture_assessment.md
VERSION: v1.0
UPDATED: 2026-03-15T03:57:02Z
CHANGE NOTES:
- Created full-scope architecture assessment across all in-scope app surfaces, runtime files, editors, and docs.
- Classified each reviewed area against the current intended baseline.
- Captured keep/merge/retire/rewrite direction without broad refactor work.

# Full Scope Architecture Assessment

## Current Architectural State

The repository is not one coherent frontend. It is a split system with four overlapping layers:

1. A corrected main app trio:
   - `web/index.html`
   - `web/shows.html`
   - `web/movies.html`
2. A second cloned monolith family still on the older interaction/runtime path:
   - `web/calendar.html`
   - `web/discover.html`
   - `web/config.html`
3. Smaller standalone utility/user pages on separate architectures:
   - `web/watch.me.html`
   - `web/watch_me/watch_me.html`
   - `web/tv_shows_listing.html`
4. Competing editing/documentation workflows:
   - `web/inputs_editor.html`
   - `web/library_editor.html`
   - multiple contradictory READMEs/specs

The main trio is the only part aligned with the current locked UX contract direction. Even there, the implementation is still monolithic and duplicated. The corrected baseline exists, but it has not yet been extracted into shared runtime modules or shared browser-served CSS.

## Assessment By In-Scope File

| file | actual purpose | alignment | classification | direction |
|---|---|---:|---|---|
| `web/index.html` | Dashboard/main shell and baseline runtime | Mostly aligned | partial | keep as source baseline, later extract shared runtime |
| `web/shows.html` | Shows view using corrected dashboard-family runtime | Mostly aligned | partial | keep, normalize against shared runtime |
| `web/movies.html` | Movies view using corrected dashboard-family runtime | Mostly aligned | partial | keep, normalize against shared runtime |
| `web/calendar.html` | Calendar view on older cloned monolith | Misaligned | wrong, duplicated | replace after normalization, not patch-led redesign |
| `web/discover.html` | Discover view on older cloned monolith | Misaligned | wrong, duplicated | rebuild onto normalized blocks |
| `web/config.html` | Config surface but implemented as old app shell clone | Misaligned | wrong, duplicated | convert to thin config/runtime client later |
| `web/watch.me.html` | Legacy single-item watch page | Weak alignment | stale | retire after replacement path is confirmed |
| `web/watch_me/watch_me.html` | Newer watch-me standalone surface | Partial alignment | partial | keep as separate product surface, normalize shared utilities only |
| `web/tv_shows_listing.html` | Standalone listing utility over `data/data.json` | Weak alignment | stale, duplicated | retire or rewrite as admin/reporting utility |
| `web/inputs_editor.html` | Active catalog curation editor for `data/inputs.json` | Strong alignment | correct | keep as canonical editor |
| `web/library_editor.html` | Legacy editor around `data/inputs_parsed.json` export flow | Misaligned | wrong, stale, should retire | retire |
| `web/css/my_tv_hub.css` | Shared stylesheet used by side surfaces, not by main app family | Partial alignment | partial | keep, but either promote or replace with real shared bundle |
| `web/config.js` | Shared config loader/validator intent | Partial alignment | partial | keep and increase usage after runtime extraction |
| `web/config.json` | Central config/runtime constants | Partial alignment | partial | keep, clean stale icon metadata and path assumptions |
| `README.md` | Root project guide | Misaligned | stale | replace as canonical README |
| `README_my_TV_Movie.md` | Alternate product README | Misaligned | stale, redundant | merge useful content, archive remainder |
| `README.txt` | Minimal placeholder README | Misaligned | stale, redundant | retire/archive |
| `scripts.md` | Top-level script overview | Partial alignment | partial | merge into canonical docs with corrections |
| `scripts/scripts.md` | Script inventory and workflow notes | Partial alignment | partial | salvage operational content, remove old parser assumptions |
| `web/config.DOC.md` | Config documentation for `watch_me` tuning | Partial alignment | stale placement | move under `docs/` and narrow scope |
| `docs/spec/*` | Historical full-spec attempt | Misaligned | stale, contradictory | archive as non-authoritative |
| `docs/ui_standardization/baseline_contract_v3.md` | Current locked baseline contract | Strong alignment | correct | keep as UX source of truth |

## Family-Level Assessment

### Main App Family

The dashboard, shows, and movies pages are aligned enough to serve as the implementation seed for the intended end state:

- `show_card`
- `movie_card`
- `episode_card`
- unified `show_popup/show_detail`
- unified `movie_popup/movie_detail`
- `episode_row`

However, they are still implemented as three near-identical HTML monoliths with ~58 KB inline CSS and ~171 KB inline JS each. This means they are aligned in behavior but still architecturally unstable.

### Out-of-Sync Clone Family

`calendar.html`, `discover.html`, and `config.html` are not on the corrected baseline. They still carry the older interaction model:

- inline `watchstatusband`
- no shared corrected `action_bar` helper
- divergent script hashes and runtime behavior
- duplicated old rendering/event logic

These files are not good patch targets for ongoing incremental UX correction. They are evidence that the current architecture allows fixes to land in one family while other surfaces drift.

### Standalone Surfaces

`watch.me.html`, `watch_me/watch_me.html`, and `tv_shows_listing.html` are not part of the corrected card/popup baseline and should not be allowed to define baseline direction. They should consume shared data/config helpers later, but they should not drive the core UI contract.

## Purpose Alignment Conclusions

### Correct

- `web/inputs_editor.html`
- `tools/inputs_editor/inputs_editor_server.py`
- `docs/ui_standardization/baseline_contract_v3.md`

### Partial

- `web/index.html`
- `web/shows.html`
- `web/movies.html`
- `web/watch_me/watch_me.html`
- `web/css/my_tv_hub.css`
- `web/config.js`
- `web/config.json`
- `scripts.md`
- `scripts/scripts.md`

### Wrong

- `web/calendar.html`
- `web/discover.html`
- `web/config.html`
- `web/library_editor.html`

### Stale

- `web/watch.me.html`
- `web/tv_shows_listing.html`
- `README.md`
- `README_my_TV_Movie.md`
- `README.txt`
- much of `docs/spec/*`

### Duplicated

- main family inline CSS/JS
- out-of-sync clone family inline CSS/JS
- repeated data/config loading logic
- repeated popup/action/render helpers
- repeated README/script workflow descriptions

### Should Retire

- `season_card` as a primary baseline component
- `web/library_editor.html`
- `web/watch.me.html` after replacement path is confirmed
- `README.txt`
- `docs/spec/*` as architecture authority

## Corrective Architecture Direction

1. Preserve `baseline_contract_v3.md` as the UX contract.
2. Treat `web/index.html` corrected runtime as the current implementation reference, not the final architecture.
3. Extract a shared browser runtime for:
   - data/config loading
   - normalized card block rendering
   - unified `action_bar`
   - popup/detail state
   - provider logo fallback
   - show open routing
   - watch status popup behavior
4. Rebase `calendar`, `discover`, and `config` on that shared runtime instead of continuing isolated patching.
5. Keep only one canonical editing workflow around `data/inputs.json`.
6. Collapse documentation to one current README, one editor workflow doc, one config doc, one UX contract, and archival folders for stale specs.

## Intended End State Match

The intended end state is achievable without restarting the app, but only if the repo stops treating each HTML file as its own authoritative application. The corrective path is:

- normalize runtime first
- then re-platform the out-of-sync views
- then retire legacy editors/docs/surfaces

Patching cloned monoliths indefinitely will continue to produce UX drift, duplicated bugs, and slow fixes.
