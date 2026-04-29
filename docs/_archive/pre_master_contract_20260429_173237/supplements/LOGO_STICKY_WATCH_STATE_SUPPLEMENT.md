# Documentation Supplement — Logo, Sticky Sections, Watch-State Management

## Purpose
This supplement records missing requirements discovered after the post-stabilization screenshots. It is authoritative until merged into `docs/UI_COMPONENTS.md` and `docs/ARCHITECTURE.md`.

## Screenshot-Based Gaps

| Gap | Required Correction |
|---|---|
| Logo renders huge/wide and consumes header | Logo must be small, height-bound, aspect-ratio preserved, no stretching. |
| Logo background appears checker/opaque | Preferred asset should be transparent PNG. If current file is not transparent, create optimized transparent/runtime version or use correct existing transparent version. |
| Section headers are not sticky | Dashboard section headers must use reusable sticky-section behavior. |
| Action icons still visually inconsistent | Icons must fit, not overlap, not sit behind text, and must be validated from rendered DOM/screenshot QA. |
| Watch Me still active as full view | Watch Me is deprecated as a standalone destination unless explicitly preserved as compatibility route. |
| No manage state view | A view is required to manage `watch_list`, `watched_status`, `favourite`, Trakt matching, and sync queue. |

## Header Logo Contract

Use:

```text
assets/custom/the_boys_hub_logo2.png
```

Rules:
- Render as an image, not as a background stretch.
- Preserve aspect ratio.
- Fit inside header height.
- Logo height target: same visual height as the compact nav row.
- Logo must not force header height larger.
- Do not crop logo.
- Do not stretch logo horizontally.
- If the image has a checkerboard/opaque background, create/use a transparent corrected runtime asset and document it.
- Add validation to fail if logo renders larger than the header height budget.

Suggested CSS contract:

```css
.logo,
.brand-logo {
  height: clamp(32px, 4vw, 48px);
  width: auto;
  max-width: 140px;
  object-fit: contain;
}
```

## Sticky Section Header Contract

Dashboard sections:
1. current week
2. watchlist
3. upcoming schedule
4. recommendations

Requirement:
- Each section has a sticky header.
- Current section header remains visible while section content scrolls.
- Next section header replaces prior header naturally.
- Sticky header must account for sticky top nav height.
- Sticky header must not cover card content.
- Behavior must be implemented as reusable section pattern for future views.

Suggested structure:

```text
<section class="section-block">
  <header class="section-sticky-header">...</header>
  <div class="section-body">...</div>
</section>
```

Suggested CSS principle:

```css
.section-sticky-header {
  position: sticky;
  top: var(--app-sticky-top);
  z-index: 40;
}
```

## Watch Me Deprecation Contract

Watch Me is now deprecated as a standalone primary navigation destination unless Codex documents a current unique purpose.

Preferred path:
- Preserve `/web/watch_me.html` as compatibility.
- Redirect or render a lightweight compatibility page pointing to Dashboard / Manage Watch State.
- Remove Watch Me from primary nav if it is redundant.
- Do not break existing links.

Documentation must state one of:
- deprecated compatibility route, or
- retained with unique purpose.

## Required Manage Watch State View

A management view is required for:
- `watched_status`
- `watch_list`
- `favourite`
- Trakt match status
- unmatched TMDB IDs
- pending offline sync queue
- sync actions: pull, compare, push, reconcile

Preferred location:
- Config sub-view or dedicated `/web/manage_watch_state.html`

Required functions:
- view current local state
- filter by shows/movies/episodes
- toggle watched_status/watch_list/favourite
- show Trakt mapping status
- show local-only changes waiting to sync
- run pull/compare/push/reconcile workflows when backend/API support exists
- never match by title alone

## Trakt Workflow Contract

Design flow:

```text
Trakt pull -> normalize -> compare -> local queue -> push -> pull confirmation -> reconcile -> report
```

Required pipeline modes:
- pull only
- compare only
- push queued local changes
- reconcile after push
- report unmatched/ambiguous items

Matching:
- primary: `tmdb_id`
- secondary only if documented and user-approved
- never title-only

Favourite:
- Evaluate whether Trakt can support favourite-like or recommendation input.
- If no exact Trakt mapping exists, keep favourite local and document it as recommendation input.

## Icon Acceptance Contract

Required row:

```text
🍿 ⌚ 🎫 💕 76%
```

Rendered acceptance:
- all icons same row
- no icon overlaps another icon
- no icon overlaps image/text
- popcorn/watch/ticket use visible square or rounded-square boxes
- action row is below image/text zone
- rating includes `%`
- row remains readable at laptop, tablet, phone, Android TV viewports

## Validation Additions

`scripts/validate_runtime.ps1` should validate:
- logo file exists
- logo dimensions/render CSS do not exceed header budget
- Watch Me deprecation documented
- manage watch-state view or documented pending route exists
- sticky section header CSS/classes exist
- action icon row rendered with correct order
- no availability badge overlays in active card renderers
- no stale primary nav to Watch Me if deprecated
