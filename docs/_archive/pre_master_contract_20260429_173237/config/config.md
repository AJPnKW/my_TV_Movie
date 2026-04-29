FILE: docs/config/config.md
VERSION: v1.0
UPDATED: 2026-03-15T04:28:23Z
CHANGE NOTES:
- Moved config documentation out of web/ to the docs tree.
- Preserved the existing watch_me-specific tuning reference.

# ui_tuning.watch_me

This section documents `web/config.json > ui_tuning.watch_me`. It is Watch Me page specific and does not change other pages.

Template used for every setting:
- Purpose
- Affects
- Default value
- Suggested min/max (with rationale)
- Failure modes outside range
- Safe examples
- Relationship to other settings

## `sidebar_width_px`
- Purpose: Fixed width of Watch Me left filter menu.
- Affects: `.layout` first grid column and `.side` width.
- Default value: `220`.
- Suggested min/max: `180` to `320`.
Because below 180 labels/selects clip, above 320 content pane loses useful width on TV.
- Failure modes outside range:
Below min causes cramped controls and truncated text.
Above max compresses carousel viewport and increases scroll churn.
- Safe examples: `200`, `220`, `260`.
- Relationship to other settings:
Interacts with `card_width_px` and `carousel_rows`; wider sidebar leaves less horizontal space for cards.

## `card_width_px`
- Purpose: Base card width used by TV and movie tracks on Watch Me.
- Affects: CSS vars `--w` and `--card-w`, day segment card widths, track density.
- Default value: `160`.
- Suggested min/max: `130` to `220`.
Because too narrow hurts readability, too wide reduces cards per viewport and increases long-distance scrolling.
- Failure modes outside range:
Low values make titles/network chips hard to read.
High values can cause oversized cards and sparse rows.
- Safe examples: `150`, `160`, `180`.
- Relationship to other settings:
Coupled with `card_gap_px`, `sidebar_width_px`, and `carousel_rows`.

## `card_height_px`
- Purpose: Minimum card height target to keep card blocks visually consistent.
- Affects: `min-height` for card items inside day segments.
- Default value: `152`.
- Suggested min/max: `130` to `260`.
Because very short cards can crowd overlays/buttons; very tall cards reduce visible card count.
- Failure modes outside range:
Too short may clip visual hierarchy.
Too tall may push controls and create excessive vertical mass.
- Safe examples: `150`, `152`, `180`.
- Relationship to other settings:
Works with `card_width_px`; unusual aspect pairings can feel distorted.

## `card_gap_px`
- Purpose: Horizontal spacing between cards in tracks and day segments.
- Affects: `gap` in `.track` and `.day-cards`.
- Default value: `10`.
- Suggested min/max: `6` to `20`.
Because too tight reduces item separation; too wide wastes track width.
- Failure modes outside range:
Low values can make focus transitions feel merged.
High values reduce card density and increase scroll steps.
- Safe examples: `8`, `10`, `14`.
- Relationship to other settings:
Interacts with `card_width_px` and effective viewport width.

## `section_gap_px`
- Purpose: Vertical gap between major Watch Me rows.
- Affects: `.main` flex column spacing.
- Default value: `12`.
- Suggested min/max: `8` to `24`.
Because too small compresses sections; too large causes unnecessary scrolling.
- Failure modes outside range:
Tiny values blur row boundaries.
Large values make navigation feel disjointed.
- Safe examples: `10`, `12`, `16`.
- Relationship to other settings:
Independent of card sizing but impacts perceived page density.

## `carousel_btn_size_px`
- Purpose: Visual diameter of left/right carousel overlay buttons.
- Affects: `.carousel-btn` width/height.
