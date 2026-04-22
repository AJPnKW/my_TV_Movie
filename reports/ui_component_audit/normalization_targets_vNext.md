FILE: reports/ui_component_audit/normalization_targets_vNext.md
VERSION: v1.0
UPDATED: 2026-03-15T03:57:02Z
CHANGE NOTES:
- Created normalization targets for the next implementation phase.
- Defined which contracts should become shared runtime primitives.
- Scoped the next corrective work away from unrelated redesigns.

# Normalization Targets vNext

## Primary Objective

Normalize the corrected baseline into shared runtime primitives so all active core views consume the same behavior instead of cloned file copies.

## Shared UI Primitives To Standardize

### Core Blocks

- `media_block`
- `action_bar`
- `title_block`
- `meta_row`
- `provider_group`
- `source_chooser`
- `status_control`
- `tag_group`
- `context_block`

### Core Entity Surfaces

- `show_card`
- `movie_card`
- `episode_card`
- unified `show_popup/show_detail`
- unified `movie_popup/movie_detail`
- `episode_row`

### Retired Baseline Surface

- `season_card`

Season remains inside show detail.

## Shared Behavior To Standardize

- action bar ordering and entity gating
- popcorn only on movie/episode contexts
- favourites availability
- popup bullet-selection watch status control
- watched toggle behavior
- heart icon and rating display
- provider logo fallback
- show-open click routing
- guarded rating display for episode contexts

## Shared Runtime To Extract

1. data loading
2. config loading/validation
3. provider lookup/fallback
4. card rendering helpers
5. detail/popup rendering helpers
6. event delegation/state updates
7. local watch-state and compatibility hooks

## View Migration Targets

### First Wave

- `web/calendar.html`
- `web/discover.html`
- `web/config.html`

### Second Wave

- `web/watch_me/watch_me.html` for shared utility adoption where safe
- utility/admin surfaces only if still needed

### Retirement Targets

- `web/library_editor.html`
- `web/watch.me.html`
- stale documentation that conflicts with baseline v3

## Non-Targets In vNext

- full calendar redesign before normalization
- watch_me redesign
- tv_shows_listing redesign
- heated-rivalry redesign
- backend API and Trakt sync implementation

## Success Markers For vNext

- one shared runtime path for dashboard/shows/movies/calendar/discover/config
- no active `watchstatusband` in core family
- no hot dog in active UX/runtime/config paths
- one canonical editor path
- one canonical README and current workflow docs
