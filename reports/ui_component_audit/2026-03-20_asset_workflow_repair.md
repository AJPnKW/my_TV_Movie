# 2026-03-20 Asset Workflow Repair

## Scope

- Replaced the placeholder `scripts/fetch_tmdb_assets.py` implementation with a real TMDB asset downloader.
- Generated missing local assets referenced by `data/data.json`.
- Re-ran the asset QA audit to verify local asset coverage against runtime data.

## Root Cause

- The previous `scripts/fetch_tmdb_assets.py` script did not walk the real `shows` / `movies` / `seasons` / `episodes` structures in `data/data.json`.
- It wrote placeholder values against a nonexistent `data["items"]` collection and did not download TMDB-hosted assets to the canonical `assets/` tree.
- As a result, newly added titles and episodes could retain valid remote TMDB paths in `data.json` while their required local assets were never fetched.

## Implementation

- Enumerate asset references from:
  - `show.poster_local` / `show.backdrop_local`
  - `movie.poster_local` / `movie.backdrop_local`
  - `season.poster_local` / `season.backdrop_local`
  - `episode.still_local`
- Pair each local asset target with its TMDB remote path.
- De-duplicate by local asset destination so repeated references do not redownload.
- Download missing assets concurrently from the TMDB image base and preserve already-present files.
- Emit machine-readable logs under `logs/asset_fetch_<timestamp>/`.

## Validation

- Syntax:
  - `python -m py_compile scripts/fetch_tmdb_assets.py`
- Download pass:
  - `python scripts/fetch_tmdb_assets.py --max-workers 16`
  - Result:
    - total unique referenced assets with remote paths: `6400`
    - matched existing local assets: `4467`
    - newly downloaded local assets: `1933`
    - failed downloads: `0`
  - log folder: `logs/asset_fetch_20260320_231025`
- QA audit:
  - `python scripts/qa_assets_against_data_json.py --no-pause`
  - Result:
    - referenced local assets: `17670`
    - matched local assets: `17670`
    - missing local assets: `0`
    - orphan local assets: `2914`
    - movies with missing local assets: `0`
    - shows with missing show/season/episode assets: `0`
  - log folder: `logs/asset_qa_20260320_231036`

## Remaining Non-Blocking Items

- The canonical asset set now covers all file paths referenced by `data/data.json`.
- `2914` orphan local assets remain under `assets/`; these are cleanup candidates, not runtime blockers.
