# Availability Asset Metadata Hardening and Secret Drift Cleanup

Date: 2026-03-21

## Scope
- Normalized Trakt redirect secret naming to `API_TRAKT_REDIRECT_URL`.
- Added explicit secret drift detection and runtime warnings.
- Added deterministic asset metadata self-heal and grouped repair reporting.
- Updated the local production runner order so repair happens before final validation.

## Secret drift findings
- Canonical secret name: `API_TRAKT_REDIRECT_URL`
- Deprecated typo secret name detected only in guarded validation/runtime-warning code:
  - `scripts/trakt_device_auth.py`
  - `scripts/trakt_test_tokens.py`
  - `scripts/validate_secret_name_drift.py`
- No unexpected repo drift references remained after this pass.
- Local environment still exposes the deprecated typo variable in addition to the canonical one, but values do not conflict; the new warning/validation path now surfaces that state explicitly.

## Self-heal rules
- If `*_path` is missing but a valid local asset exists, backfill the path from the local filename.
- If `*_local` is missing but `*_path` exists, backfill the local path using canonical folders from `web/config.json`.
- If the local asset is still missing and the remote metadata exists, fetch the asset before final validation in the local runner.
- If both metadata and local asset are absent, classify as unrecoverable upstream metadata absence and keep as warning/reporting, not false success.

## Current classified gap state
- Before warning counts:
  - `movie.poster = 3`
  - `movie.backdrop = 8`
  - `show.poster = 3`
  - `show.backdrop = 8`
  - `season.poster = 109`
  - `episode.still = 4094`
- Current recoverable drift found in the live catalog during this pass:
  - `repaired_from_local_asset = 0`
  - `repaired_from_metadata = 0`
  - `fetched_missing_asset = 0`
  - `repair_failed = 0`
- Current irrecoverable upstream gaps:
  - `unrecoverable_upstream_gap = 4225`

## Why no repairs were applied in this run
- The current live metadata warnings are not path-backfill or fetch-order defects.
- They are upstream metadata absences: the affected entities have neither usable TMDB metadata paths nor matching local assets to derive from.
- The new self-heal path is therefore preventive and future-proofing, not a cosmetic rewrite of current upstream limitations.

## Workflow result
- `scripts/run_pipeline_tmdb_trakt.py` now runs:
  - `validate_secret_name_drift.py`
  - `self_heal_asset_metadata.py --fetch-missing`
  - availability validate/enrich/QA
  - runtime asset validation
  - runtime catalog validation
- The local runner completed successfully with this order.

## Implementation commit
- Metadata hardening implementation commit: `pending grouped commit`
