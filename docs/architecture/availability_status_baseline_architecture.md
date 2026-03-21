# Availability Status Baseline Architecture

## Current-state-safe target

```text
inputs.json
   │
   ├── existing build scripts
   ▼
data.json
   │
   ├── availability enrichment script
   │      ├── reads availability source file
   │      ├── resolves per-entity availability
   │      └── writes additive fields into data.json
   ▼
enriched data.json
   │
   ├── index/listing/detail pages
   ├── cards
   ├── popups/details
   └── episode rows
```

## Architectural boundary decisions
| Layer | Owner | Change |
|---|---|---|
| `inputs.json` | Existing editorial input | No structural change |
| Existing build scripts | Existing data assembly | Minimal or no change |
| Availability source file | New canonical availability source | New |
| Enrichment script | New post-build layer | New |
| Web pages/components | Read from `data.json` | Small additive change |

## Source-of-truth file
Recommended path:
`data/watch_source_availability.json`

Live implementation:
- top-level `defaults` block defines validation mode and source preference per entity type
- top-level `records` block remains the manual override surface
- enrichment writes only additive availability fields back into `data/data.json`

Actual post-build runner:
`scripts/run_pipeline_tmdb_trakt.py`

Actual implementation files:
- `scripts/availability_status_lib.py`
- `scripts/validate_availability_overlay.py`
- `scripts/enrich_data_with_availability.py`
- `scripts/qa_availability_status.py`

## Why a separate post-build layer
| Concern | Architectural answer |
|---|---|
| Avoid rework in baseline input model | Keep `inputs.json` intact |
| Avoid merge-loss in `data.json` | Recompute from external source each run |
| Support episode granularity | External file supports any depth |
| Keep pages simple | Pages only read final fields from `data.json` |
