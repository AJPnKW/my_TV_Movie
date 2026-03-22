# Availability Status Phase 2 Completion

Date: 2026-03-21

## Scope
- Hardened availability validation from structural-only to provider-aware deterministic validation.
- Added optional cached network-check support without making it a required pipeline dependency.
- Added runtime asset-contract and runtime catalog-integrity validators.
- Moved card availability badges onto the image surface upper-right corner and mirrored the same contract on popup visual surfaces.
- Fixed the local pipeline so rebuilt TMDB asset refs are fetched before runtime asset validation.

## Key changes
- `scripts/availability_status_lib.py`
  - provider-aware validation
  - optional cached network validation support
  - child-status fallback for shows/seasons with missing dates
- `scripts/enrich_data_with_availability.py`
  - nested resolution order for episode -> season -> show
  - network-cache persistence support
- `scripts/validate_runtime_assets.py`
  - validates `*_local` path conventions, local-file presence, and metadata/file separation
- `scripts/validate_runtime_catalog_integrity.py`
  - validates JSON structure and required availability fields after enrichment
- `scripts/qa_availability_phase2.py`
  - deterministic override-precedence and provider-validation checks
- `scripts/qa_availability_ui.py`
  - browser-level badge placement validation
- `scripts/run_pipeline_tmdb_trakt.py`
  - now runs `fetch_tmdb_assets.py` before runtime asset validation

## Validation model
- Default mode: `provider_structural`
- Network mode: optional cached HEAD/GET verification, disabled by default
- Reason for default: third-party stream hosts are not stable enough for required CI/local pipeline success criteria

## Override model
- Manual per-entity override support remains in `data/watch_source_availability.json`
- Live seeded overrides after phase 2: `0`
- Reason: no current catalog item required a justified manual override after provider-aware validation and child-status fallback were added

## Production validation evidence
- `python scripts/run_pipeline_tmdb_trakt.py` completed successfully after phase-2 workflow hardening.
- `python scripts/qa_availability_ui.py` passed with upper-right badge placement confirmed on:
  - dashboard
  - shows
  - movies
  - calendar
  - watch_me
  - movie popup
  - show popup
- `python scripts/validate_runtime_assets.py` passed after the pipeline asset-refresh step.
- Existing deep asset audit reported:
  - referenced local assets: `17685`
  - matched local assets: `17685`
  - missing local assets: `0`

## Remaining non-blocking limits
- Some titles remain metadata-gap warnings because TMDB does not provide poster/backdrop/still paths for them.
- Optional network validation support exists but is intentionally not enabled by default.

## Implementation commit
- Phase 2 implementation commit: `pending grouped commit`
