FILE: reports/ui_component_audit/calendar_salvage_vs_rebuild_assessment.md
VERSION: v1.0
UPDATED: 2026-03-15T03:57:02Z
CHANGE NOTES:
- Created calendar salvage vs rebuild assessment.
- Defined which normalized blocks and logic the future calendar must consume.
- Determined whether current implementation is worth patch-led salvage.

# Calendar Salvage vs Rebuild Assessment

## Current State

`web/calendar.html` is a large cloned monolith on the older runtime path. It still contains:

- legacy inline `watchstatusband`
- older action/status assumptions
- duplicated render/load/event logic separate from the corrected trio

It is not aligned with the corrected main family baseline.

## Salvage Assessment

### What Is Salvageable

- high-level page purpose
- calendar-specific filtering and scheduling intent
- any view-specific date grouping logic that is independent of card rendering

### What Is Not Worth Preserving As-Is

- current card/action implementation
- current watch status interaction model
- current monolithic inline runtime structure
- current duplicated event/data/config loading structure

## Decision

The calendar should be rebuilt after core normalization, not continuously patched in place.

This is not a "throw everything away" decision. It is a "do not continue salvaging the wrong runtime shell" decision.

## Required Shared Blocks For Future Calendar

The rebuilt calendar should consume the same normalized shared blocks as the corrected app family:

- `media_block`
- `action_bar`
- `title_block`
- `meta_row`
- `provider_group`
- `status_control`
- `tag_group`
- `context_block`

## Required Shared Logic

The rebuilt calendar should also share:

- data/config loading
- provider fallback logic
- watch status popup logic
- watched toggle logic
- rating display guards
- show/movie open routing helpers
- popup/detail state handling

## Why Rebuild After Normalization

If calendar is patched before the shared runtime is extracted, the repo will produce a fourth partial implementation of:

- cards
- action bar
- provider rendering
- popup behavior
- watch status logic

That would increase divergence, not reduce it.

## Recommended Calendar Path

1. Finish shared runtime normalization from corrected trio.
2. Reuse normalized card/detail/action logic.
3. Rebuild calendar-specific layout and date logic on top of that shared runtime.
4. Validate calendar only after it consumes the same corrected blocks as dashboard/shows/movies.
