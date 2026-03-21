# Core Correction No Invalid Defers

Date: 2026-03-15

## Implemented

- Restored shared status-menu support to the canonical action bar and wired it through the shared runtime instead of page-local markup.
- Corrected calendar episode cards to use the canonical shared episode-card family with overlay title, `S##E##`, show title, shared action row, popcorn-first playable flow, watched toggle, status popup, like, and rating percent.
- Corrected movie calendar cards to use the shared compact card/action system with popcorn, favourite, status, watched, like, and rating.
- Removed the watched-to-`100%` shortcut from calendar progress so rating percent remains tied to real progress/rating data.
- Restored popup episode-row parity in show detail so popup episode rows now use the shared action bar with status and popcorn behavior instead of the reduced legacy subset.
- Added sticky calendar controls and sticky weekday row in the current full-width shell.
- Tightened calendar card spacing and top-edge image crop behavior with calendar-specific overrides rather than introducing a separate card family.
- Restored overlay submeta hierarchy for shared episode cards and propagated it into `watch_me`.

## Validation Summary

- Sticky calendar header and sticky weekday row verified in desktop browser validation.
- Calendar episode card overlay hierarchy verified: title, `S##E##`, show title.
- Calendar watch-source popup opened from the popcorn icon in playable episode context.
- Calendar status popup opened from the shared status icon.
- Calendar watched toggle no longer forced rating percent to `100%`.
- Popup episode rows now expose shared status and popcorn icons consistently.
- `watch_me` shared overlay episode cards now render title, `S##E##`, and show-title overlay hierarchy.
