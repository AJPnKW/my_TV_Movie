# Calendar Rebuild Dependencies

## Standardized Blocks Calendar Must Reuse Later

- `media_block`
- `action_bar`
- `title_block`
- `meta_row`
- `provider_group`
- `status_control`
- `context_block`

## Why Calendar Stays Deferred

- Calendar still carries older icon-strip and provider render assumptions.
- Core blocks needed a correction pass first so calendar can consume stable shared structures instead of inheriting mixed contracts.
- Calendar rebuild should happen after show/movie/episode surfaces are manually reviewed and approved.

