# Availability Status End-to-End Delivery Plan

## Delivery goal
Implement the feature across data, workflows, validation, and UI without breaking existing repo behavior.

## Required grouped delivery phases
| Phase | Required outcome |
|---|---|
| 1. Repo inspection | Confirm current source-of-truth files, `data.json` location, entity keys, current page/component structure, current workflows |
| 2. Design alignment | Update any repo docs that still reflect legacy assumptions |
| 3. Data implementation | Add source file model, validator, enrichment script |
| 4. Workflow integration | Add manual and/or chained workflow support |
| 5. UI integration | Show status in index/list/detail/card/episode views |
| 6. QA pass | Validate syntax, JSON, merge results, UI visibility |
| 7. Final reporting | Output exact changed files, validations, and remaining risks |

## Live implementation mapping
- Source file: `data/watch_source_availability.json`
- Shared logic: `scripts/availability_status_lib.py`
- Validator: `scripts/validate_availability_overlay.py`
- Enricher: `scripts/enrich_data_with_availability.py`
- QA summary: `scripts/qa_availability_status.py`
- Manual chained runner: `scripts/run_pipeline_tmdb_trakt.py`
- CI validation hook: `.github/workflows/validate.yml`
- Shared UI helper: `web/js/availability_ui.js`

## Hard implementation rules
| Rule | Required |
|---|---:|
| Do not guess repo paths | Yes |
| Do not assume legacy docs are current | Yes |
| Update stale docs first if needed | Yes |
| Reuse existing helpers/components where possible | Yes |
| Preserve repo structure | Yes |
| No rewrite-from-scratch | Yes |
| Provide complete changed files | Yes |
| Produce grouped implementation pass, grouped fix pass, grouped QA pass | Yes |

## Phase 2 completion additions
- Provider-aware validation is now the default model.
- Optional cached network verification support exists but is not enabled in default workflow runs.
- Runtime asset-contract validation is now handled by `scripts/validate_runtime_assets.py`.
- Runtime JSON/integrity validation is now handled by `scripts/validate_runtime_catalog_integrity.py`.
- Deterministic phase-2 QA coverage is now handled by `scripts/qa_availability_phase2.py`.
- Local runner integration now includes `scripts/fetch_tmdb_assets.py` before final asset validation.

## Metadata hardening additions
- `scripts/self_heal_asset_metadata.py` now performs deterministic asset-metadata repair before final validation.
- Repair logic backfills:
  - missing `*_path` from existing local asset filenames when safe
  - missing `*_local` from existing remote metadata using canonical config folders
- The local runner now executes secret-drift validation and asset self-heal before availability validation/enrichment.
