# Asset Gap Follow-up — 2026-03-19

This patch adds a targeted repair script for missing local assets referenced by `data/data.json`.

## Why
The QA run showed:

- 12,655 referenced local assets
- 1,657 missing local assets
- 2,926 orphan local assets

The biggest gap is episode stills.

## What this patch adds
- `scripts/refresh_missing_assets_from_data.py`

## What it does
- loads `data/data.json`
- checks every referenced local poster/backdrop/still
- if local file is missing and a TMDB `*_path` exists, downloads the file into the referenced local path
- produces:
  - `logs/asset_repair_YYYYMMDD_HHMMSS/summary.txt`
  - `logs/asset_repair_YYYYMMDD_HHMMSS/asset_repair_results.csv`
  - `logs/asset_repair_YYYYMMDD_HHMMSS/asset_repair_results.json`

## Notes
This repairs **downloadable** gaps only.
If a referenced local asset has no remote `poster_path`, `backdrop_path`, or `still_path`, it is reported as `missing_no_remote`.
