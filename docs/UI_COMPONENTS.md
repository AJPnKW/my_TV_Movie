# UI Component Contract

## Purpose
This document is the active UI source of truth for cards, action icons, image sizing, section headers, modal focus, responsive behavior, and layout rules.

## Universal Card Layout

All media cards use this structure:

```text
[ image ]
[ title + metadata ]
[ action row ]
```

Never allowed:
- action icons on top of the image
- media text hidden behind icons
- availability badges covering poster/still artwork
- different show-card layout on Dashboard vs Shows page
- different movie-card layout on Dashboard vs Movies page

## Card Types

| Type | Image | Runtime/Display Target |
|---|---|---|
| Show | poster | `poster_card_171x257` |
| Movie | poster | `poster_card_171x257` |
| Episode | cropped still | `episode_still_narrow_256x180` |

## Episode Still Rule

Start from:

```text
episode_still_source_320x180
```

Crop 10% from left and 10% from right:

```text
320x180 -> 256x180
```

Do not distort by non-proportional scaling.

## Action Row

Required order:

```text
🍿 ⌚ 🎫 💕 76%
```

| Function | Icon | Meaning |
|---|---:|---|
| Watch sources | 🍿 | Open watch-source popup |
| Watched status | ⌚ | Toggle watched/unwatched |
| Watch list | 🎫 | Toggle queued to watch later |
| Favourite | 💕 | Toggle favourite/recommendation signal |
| Rating | `76%` | Compact rating percentage |

Forbidden active icons:
- play triangle for watched status
- clapperboard for watched status
- ruler for watch list
- yellow single-heart for favourite
- star for rating

## Action Icon Layout

- Popcorn/watch/ticket must use solid rounded-square boxes.
- Icon box width and height must match.
- Icon and box must scale to available card width.
- If space is tight, rating text shrinks before icons overlap.
- Do not clip overflow or hide overflow in a way that cuts rounded corners.
- Action row sits below card media/text, never over the image.

## Availability

Availability must be represented primarily through popcorn color.

| State | Popcorn Color |
|---|---|
| available | green |
| not_yet_released | orange |
| unavailable | red |

Remove overlay availability badges from cards when they cover image artwork.

## Watch-State Identity

State keys must be kind-specific:

```text
watched_status:episode:<show_id>:<season_number>:<episode_number>
watched_status:movie:<tmdb_id>
watched_status:show:<tmdb_id>
watch_list:episode:<show_id>:<season_number>:<episode_number>
watch_list:movie:<tmdb_id>
watch_list:show:<tmdb_id>
favourite:episode:<show_id>:<season_number>:<episode_number>
favourite:movie:<tmdb_id>
favourite:show:<tmdb_id>
```

Toggling one item may update duplicate representations of the same item, but must not update unrelated cards.

## Header / Navigation

- Use `assets/custom/the_boys_hub_logo2.png` as the upper-left logo.
- Replace the old `MY TV HUB` text block.
- Header must be sticky.
- Navigation should be compact, icon-first, accessible, and D-pad friendly.
- Each nav item must expose hover/title/aria label text.
- Inputs Editor must remain reachable.

## Dashboard Section Headers

Dashboard sections:
1. current week
2. watchlist
3. upcoming schedule
4. recommendations

Each section uses the same sticky-section-header behavior:
- active section header remains visible while the section is in view
- next section header replaces it
- sticky header must not cover cards

## Calendar / Dashboard More Behavior

No silent truncation.

If a day has more items than visible space:
- show first visible items cleanly
- show `+X more`
- click/Enter expands or opens a day detail view
- Dashboard and Calendar must share this behavior

## Modal / Popup Focus

When a modal or provider popup is open:
- arrow keys/D-pad navigate only inside the popup
- Escape/Back closes the popup
- background page does not scroll or receive focus
- focus returns to launching control where practical

## Frame Rules

Keep visible frames only around:
- date/day column
- show card
- movie card
- episode card

Avoid visible frames around:
- app shell
- page panel wrappers
- redundant nested dashboard sections
- action row

## Discover and Watch Me Decisions

Discover and Watch Me must not duplicate Dashboard behavior without a documented reason.

Required future decision:
- keep as distinct surfaces,
- merge into Dashboard,
- or preserve route as compatibility/redirect.
