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
- Default value: `56`.
- Suggested min/max: `28` to `72`.
Because too small hurts remote/touch targeting; too large can obscure track content.
- Failure modes outside range:
Small buttons reduce discoverability.
Large buttons block edge content and can crowd day labels.
- Safe examples: `40`, `56`, `64`.
- Relationship to other settings:
Pair with `carousel_btn_hitbox_px` and `carousel_btn_border_px`.

## `carousel_btn_hitbox_px`
- Purpose: Reserved edge space/hit area for carousel controls.
- Affects: `.carousel-wrap` side padding.
- Default value: `64`.
- Suggested min/max: `32` to `88`.
Because too low may overlap content, too high consumes usable track width.
- Failure modes outside range:
Low values can cover day-pill/card edges.
High values reduce visible cards per row.
- Safe examples: `48`, `64`, `72`.
- Relationship to other settings:
Should generally be >= `carousel_btn_size_px`.

## `carousel_btn_border_px`
- Purpose: Button border thickness for contrast and focus affordance.
- Affects: `.carousel-btn` border width.
- Default value: `2`.
- Suggested min/max: `1` to `4`.
Because thin borders can disappear on bright scenes; thick borders can look heavy.
- Failure modes outside range:
Too thin can hurt visibility.
Too thick can make controls visually noisy.
- Safe examples: `1`, `2`, `3`.
- Relationship to other settings:
Works with `carousel_btn_shadow` and palette contrast.

## `carousel_btn_shadow`
- Purpose: Toggle button drop shadow for depth/contrast.
- Affects: `--carousel-btn-shadow`.
- Default value: `true`.
- Suggested min/max: Boolean (`true`/`false`) only.
Because this is a binary visual affordance.
- Failure modes outside range:
Invalid values are coerced; unexpected coercion can cause inconsistent appearance.
- Safe examples: `true`, `false`.
- Relationship to other settings:
Most useful when `carousel_btn_size_px` is small or backgrounds are busy.

## `day_pill_height_px`
- Purpose: Minimum height of day pills so date labels remain legible at distance.
- Affects: `.day-pill` min-height.
- Default value: `26`.
- Suggested min/max: `20` to `40`.
Because too short compresses text; too tall increases vertical row density.
- Failure modes outside range:
Low values reduce readability.
High values can bloat segment headers.
- Safe examples: `24`, `26`, `32`.
- Relationship to other settings:
Pairs with `day_segment_gap_px` for header-to-card spacing feel.

## `day_segment_gap_px`
- Purpose: Vertical gap between each day pill and its card strip.
- Affects: `.day-seg` gap.
- Default value: `10`.
- Suggested min/max: `6` to `18`.
Because too tight crowds pill and cards; too loose adds visual drift.
- Failure modes outside range:
Low values can feel cramped.
High values create disconnected segments.
- Safe examples: `8`, `10`, `14`.
- Relationship to other settings:
Combined effect with `day_pill_height_px` controls day-segment rhythm.

## `carousel_rows`
- Purpose: Reserved tuning hook for row density profiles.
- Affects: Exposed as CSS var `--carousel-rows` for future guarded use.
- Default value: `2`.
- Suggested min/max: `1` to `3`.
Because beyond 3 usually creates visual complexity on TV layouts.
- Failure modes outside range:
Current implementation does not switch row templates from this value, but extreme values can mislead operators expecting behavior change.
- Safe examples: `1`, `2`, `3`.
- Relationship to other settings:
Conceptually linked to `card_width_px` and viewport width planning.

## Validation checklist
- `config.json` parses with strict JSON parser (no comments/trailing commas).
- Watch Me page still renders with tuning fallback if config fetch fails.
- Carousel buttons remain visibly high-contrast and focus-visible.
- DPAD behavior still works:
Arrow left/right changes focus within row.
Enter on card activates primary provider.
Enter on day pill moves focus to first card in segment.
