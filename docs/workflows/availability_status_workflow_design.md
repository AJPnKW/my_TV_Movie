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
- CI validation: `.github/workflows/validate.yml`

## Phase 2 workflow note
- Local production workflow now includes `fetch_tmdb_assets.py` before runtime asset validation so rebuilt `*_local` refs are fetched before validation.
- CI still validates the tracked repo state without downloading assets.
- Runtime validation now also includes:
  - `scripts/qa_availability_phase2.py`
  - `scripts/validate_runtime_assets.py`
  - `scripts/validate_runtime_catalog_integrity.py`
