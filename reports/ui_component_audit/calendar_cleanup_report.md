FILE: reports/ui_component_audit/calendar_cleanup_report.md
VERSION: v1.0
UPDATED: 2026-03-15T17:58:07Z
CHANGE NOTES:
- Recorded the calendar cleanup implementation.
- Captured the move from stretched generic fragments to compact calendar-specific event composition.

# Calendar Cleanup Report

## What Changed

- Replaced the old partial-column calendar composition with a full 42-day month grid.
- Replaced stretched oversized event fragments with compact calendar event cards.
- Simplified event content to title, show/movie context, timing, and compact watch-now access where playable.
- Added expandable `+more` handling per day instead of permanently overflowing the cell.
- Kept episode clicks routed to show detail and movie clicks routed to movie detail.

## Outcome

- The calendar now behaves like a calendar surface instead of a recycled generic card rail.
- Day cells are readable at a glance and no longer depend on oversized image slabs.
- Popcorn watch-now is still available for episode/movie playable contexts without polluting show surfaces.
