FILE: reports/ui_component_audit/dependency_interdependency_map.md
VERSION: v1.0
UPDATED: 2026-03-15T03:57:02Z
CHANGE NOTES:
- Created dependency and interdependency map across views, runtime files, editors, data, and docs.
- Identified duplication chains and drift sources.
- Flagged the dependency edges that block fast UX correction.

# Dependency and Interdependency Map

## High-Level Map

```text
data/inputs.json
  -> scripts/run_pipeline_full.py
  -> scripts/fetch_tmdb.py
  -> scripts/fetch_trakt_primary.py
  -> scripts/sync_local_watch_state.py
  -> data/data.json

data/data.json
  -> web/index.html
  -> web/shows.html
  -> web/movies.html
  -> web/calendar.html
  -> web/discover.html
  -> web/watch.me.html
  -> web/watch_me/watch_me.html
  -> web/tv_shows_listing.html

web/config.json
  -> web/config.js
  -> web/watch_me/watch_me.html
  -> main app monolith pages through duplicated inline logic

tools/inputs_editor/inputs_editor_server.py
  -> web/inputs_editor.html
  -> /api/inputs
  -> /api/config
  -> /api/tmdb/search
```

## Shared Runtime Dependencies

### Main App Trio

`web/index.html`, `web/shows.html`, and `web/movies.html` currently depend on nearly identical inline style/script payloads. They share:

- view shell structure
- card rendering helpers
- popup/detail behavior
- data loading
- config loading
- action bar rendering
- provider rendering
- show-open routing

This is a logical shared runtime implemented as file copies instead of modules.

### Divergent Clone Family

`web/calendar.html`, `web/discover.html`, and `web/config.html` depend on their own older copies of the same concepts:

- old card rendering
- old popup/action helpers
- old watch status strip model
- duplicated data/config loading
- duplicated event binding

This creates a forked runtime family rather than a single shared runtime.

## Data Dependencies

### Canonical Curation Source

The active curation source is `data/inputs.json`.

Evidence:

- `web/inputs_editor.html` loads and saves `/api/inputs`
- `tools/inputs_editor/inputs_editor_server.py` reads/writes `data/inputs.json`
- `scripts/run_pipeline_full.py` orchestrates from `data/inputs.json`
- `scripts/fetch_trakt_primary.py` builds catalog from `inputs.json`
- `scripts/sync_local_watch_state.py` syncs local watch state from `inputs.json` into `data/data.json`

### Derived Runtime Catalog

The active runtime catalog is `data/data.json`.

It is loaded by nearly every user-facing read surface.

### Drifted/Legacy Data Path

`data/inputs_parsed.json` is not present in the current repo state, but it still drives:

- `web/library_editor.html`
- `scripts/parse_txt_to_json.py`
- parts of `scripts/scripts.md`
- residual compatibility code in `scripts/fetch_tmdb.py`

This is a legacy dependency edge that now causes confusion and broken local behavior.

## Config Dependencies

### Shared Config Files

- `web/config.json` is the effective config source
- `web/config.js` is intended to validate/load that config

### Dependency Problems

- the main monolith pages still embed duplicated config-loading logic instead of consistently consuming `web/config.js`
- `web/config.html` is a full clone of the app shell rather than a thin config client
- `web/config.json` still contains stale icon metadata including the retired hot dog mapping

## Editor Dependencies

### Canonical Editor Path

```text
web/inputs_editor.html
  -> tools/inputs_editor/inputs_editor_server.py
  -> /api/inputs
  -> data/inputs.json
  -> pipeline scripts
  -> data/data.json
```

### Legacy Editor Path

```text
web/library_editor.html
  -> /data/inputs_parsed.json
  -> export-only JSON workflow
  -> no active canonical persistence path
```

The legacy path is disconnected from the actual active pipeline.

## Popup and Action Bar Dependencies

The corrected baseline requires normalized shared blocks:

- `media_block`
- `action_bar`
- `title_block`
- `meta_row`
- `provider_group`
- `source_chooser`
- `status_control`
- `tag_group`
- `context_block`

Current dependency state:

- corrected trio uses the newer `action_bar` direction and popup watch status control
- calendar/discover/config still depend on older inline `watchstatusband`
- some legacy docs still define popup stack + season popup + icon strip as requirements

This means UI behavior depends as much on which file copy a view inherited from as on any shared contract.

## Duplication Chains Causing Drift

### Duplicated Code

- inline CSS duplicated across major app surfaces
- inline JS duplicated across major app surfaces
- fetch patterns repeated per page
- event listener wiring repeated per page
- provider/logo rendering repeated per page
- docs repeating architecture in contradictory ways

### Drift Result

Fixes land in one HTML family and do not automatically propagate to the others. The recent baseline sync corrected `index`, `shows`, and `movies`, but calendar/discover/config remained behind because they are different clones.

## Dependencies That Slow Fixes

1. File-copy runtime instead of shared module runtime.
2. Large `data/data.json` dependency for many pages.
3. Residual split between `inputs.json` and `inputs_parsed.json` assumptions.
4. Config handled partly by `config.js`, partly by inline copies.
5. Stale specs/docs still defining old UX targets.

## Corrective Dependency Strategy

1. Declare `data/inputs.json` as the only catalog curation source of truth.
2. Declare `data/data.json` as the only runtime catalog payload.
3. Extract one shared browser runtime for the main app family.
4. Make `calendar`, `discover`, and `config` consume that runtime rather than maintaining cloned copies.
5. Retire dependencies on `inputs_parsed.json` for active user workflows.
6. Reduce docs to one authoritative UX contract and one current architecture/workflow set.
