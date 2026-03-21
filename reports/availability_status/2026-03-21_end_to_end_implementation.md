# 2026-03-21 Availability Status End-to-End Implementation

## Inspection Summary
- Runtime dataset path: `data/data.json`
- Canonical input path remained unchanged: `data/inputs.json`
- Actual post-build runner for refreshed catalog data: `scripts/run_pipeline_tmdb_trakt.py`
- Actual enrichment/QA pattern already in repo: atomic JSON writes plus report/log output under `reports/` and `logs/`
- Stable live keys:
  - movie: `tmdb_id`, `id`
  - show: `tmdb_id`, `id`
  - season: `id`, `season_number`, parent show `tmdb_id`
  - episode: `id`, `show_id`, `season_number`, `episode_number`
- Live UI/runtime surfaces:
  - main runtime: `web/js/app_runtime.js`
  - shared cards: `web/js/card_renderer.js`
  - shared action bar: `web/js/action_bar.js`
  - watch_me runtime: `web/js/watch_me_runtime.js`
  - shared styles: `web/css/main_app.css`
- Existing availability implementation state before this pass:
  - `data/watch_source_availability.json` existed but was empty
  - `scripts/validate_availability_overlay.py` was a placeholder
  - `scripts/enrich_data_with_availability.py` was a placeholder
  - UI relied on coarse release-date helpers instead of normalized availability fields

## Implementation
- Added `scripts/availability_status_lib.py` as the shared resolver for entity keys, source normalization, primary watch URL derivation, and status resolution.
- Replaced placeholder availability scripts with real validator and enrichment passes.
- Added `scripts/qa_availability_status.py` to produce deterministic status QA reports under `reports/availability_status/`.
- Updated `data/watch_source_availability.json` to the live defaults-plus-overrides shape.
- Enriched `data/data.json` with:
  - `availability_status`
  - `availability_checked_at`
  - `availability_source`
  - `availability_reason`
  - `primary_watch_url_tested` when resolved
- Integrated availability into:
  - dashboard cards
  - shows cards
  - movies cards
  - calendar cards
  - watch_me cards
  - show popup detail
  - movie popup detail
  - show season detail
  - show popup episode cards
- Updated `.github/workflows/validate.yml` to run the availability validator, enricher, and QA summary.

## Validation
- `python -m compileall scripts`
- `node --check web/js/app_runtime.js`
- `node --check web/js/card_renderer.js`
- `node --check web/js/watch_me_runtime.js`
- `node --check web/js/availability_ui.js`
- `python scripts/validate_availability_overlay.py --write-normalized`
- `python scripts/enrich_data_with_availability.py`
- `python scripts/qa_availability_status.py`
- `python scripts/qa_pipeline_integrity.py`
- Live browser validation with headless Edge against:
  - `web/index.html`
  - `web/shows.html`
  - `web/movies.html`
  - `web/calendar.html`
  - `web/watch_me/watch_me.html`
  - show popup
  - movie popup

## Validation Results
- Availability source validation: `OK`
- Enrichment counts:
  - movies: `96`
  - shows: `185`
  - seasons: `592`
  - episodes: `9493`
- Status distribution after enrichment:
  - movie: `77 available`, `19 not_yet_released`
  - show: `173 available`, `9 not_yet_released`, `3 unknown`
  - season: `544 available`, `17 not_yet_released`, `31 unknown`
  - episode: `8876 available`, `213 not_yet_released`, `404 unknown`
- Availability QA report: `OK`
- Browser validation confirmed shared availability badges on dashboard, shows, movies, calendar, and watch_me, plus availability detail in movie/show popups and season/episode rendering inside the show popup.

## Known Non-Blocking Items
- `scripts/qa_pipeline_integrity.py` still fails the pre-existing `missing_trakt_id_movies_zero` check because the live repo currently has `3` movies without `trakt_id`. Availability integration itself passed all new checks.

## Changed Files
- `data/watch_source_availability.json`
- `data/data.json`
- `scripts/availability_status_lib.py`
- `scripts/validate_availability_overlay.py`
- `scripts/enrich_data_with_availability.py`
- `scripts/qa_availability_status.py`
- `scripts/qa_pipeline_integrity.py`
- `scripts/run_pipeline_tmdb_trakt.py`
- `.github/workflows/validate.yml`
- `web/js/availability_ui.js`
- `web/js/card_renderer.js`
- `web/js/app_runtime.js`
- `web/js/watch_me_runtime.js`
- `web/css/main_app.css`
- `docs/design/availability_status_solution_design.md`
- `docs/architecture/availability_status_baseline_architecture.md`
- `docs/data/availability_status_data_contract.md`
- `docs/impact/availability_status_system_impact_matrix.md`
- `docs/implementation/availability_status_end_to_end_delivery_plan.md`
- `docs/testing/availability_status_qa_and_validation.md`
- `docs/ui/availability_status_ui_integration.md`
- `docs/workflows/availability_status_workflow_design.md`
- `docs/ARCHITECTURE_LOG.md`
