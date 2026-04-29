# Availability Status Workflow Design

## Execution model
| Step | Action |
|---|---|
| 1 | `scripts/run_pipeline_tmdb_trakt.py` runs `fetch_tmdb.py` |
| 2 | Same runner executes `fetch_omdb.py` and `fetch_trakt.py` |
| 3 | Availability validator checks `data/watch_source_availability.json` |
| 4 | Availability enrichment script updates `data/data.json` |
| 5 | QA summary verifies required fields and status counts |
| 6 | Pages consume enriched `data.json` |

## Recommended workflow strategy
| Strategy | Decision |
|---|---|
| Independent manual workflow | Yes |
| Chained post-build workflow | Yes |
| Replace current workflow | No |

## Required workflow outputs
| Output | Purpose |
|---|---|
| validation log | prove source file is valid |
| enrichment log | prove counts and decisions |
| JSON parse validation | prove output is not corrupted |
| changed entity counts | prove actual application |

## Live repo workflow files
- manual/local chain: `scripts/run_pipeline_tmdb_trakt.py`
- production data build: `.github/workflows/build-data.yml`
- CI validation: `.github/workflows/validate.yml`

## Current source hierarchy note
- The repo also contains `scripts/fetch_trakt_primary.py`, which reflects the Trakt-primary catalog intent.
- The active production rebuild chain restored in this phase mirrors the current live runner: `fetch_tmdb.py -> fetch_omdb.py -> fetch_trakt.py -> fetch_tmdb_assets.py -> self-heal/availability/runtime validation`.
- This means the repo currently has a real Trakt-primary builder available, but the active production workflow still uses the TMDB-first runner until that source-authority migration is completed explicitly.

## Phase 2 workflow note
- The production data-build workflow now runs the same end-to-end runner as local rebuilds and commits regenerated `data/data.json` plus changed `assets/**` back to `main`.
- The local production runner explicitly includes `fetch_tmdb_assets.py` before final self-heal and runtime validation so rebuilt `*_local` refs are fetched before validation.
- The validation workflow still validates the tracked repo state without rebuilding data artifacts.
- Runtime validation now also includes:
  - `scripts/qa_availability_phase2.py`
  - `scripts/validate_runtime_assets.py`
  - `scripts/validate_runtime_catalog_integrity.py`

## Metadata hardening workflow note
- The local runner now executes:
  - `scripts/validate_secret_name_drift.py`
  - `scripts/self_heal_asset_metadata.py --fetch-missing`
  - availability validation/enrichment
  - runtime asset/catalog validation
- This order ensures recoverable metadata gaps and missing fetched assets are addressed before the final runtime validator runs.
