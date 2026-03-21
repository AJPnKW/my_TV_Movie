# Asset Path Normalization Report

- Date: 2026-03-15

## Findings

- `web/assets` was drift, not a required runtime dependency, for the in-scope normalized surfaces.
- Nested tree contents were limited to `web/assets/logos/services/*`.
- Duplicate check result:
- `web/assets/logos/services`: 74 files
- `assets/logos/services`: 211 files
- Missing-from-root count for nested files: 0

## Action Taken

- Removed `web/assets/logos/services/*` after confirming all 74 files already exist in `assets/logos/services/*`.
- Kept canonical runtime references on `assets/...` at repo root.
- Updated provider logo resolution in `web/js/app_runtime.js` to prefer canonical local logo files by TMDB filename before remote fallback.

## Post-Normalization State

- Canonical asset root remains `assets/...`.
- No in-scope `web/assets` dependency remains.
- Provider chips now degrade to TMDB fallback or text-only chip fallback instead of persisting broken local-logo references.
