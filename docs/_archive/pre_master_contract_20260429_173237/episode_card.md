# Episode Card Contract

- Shared across dashboard upcoming schedule, dashboard last week, calendar, watch_me rows, and show popup episode carousel.
- The visual baseline comes from the calendar episode card:
  - 16:9 still image
  - centered trim on the still image
  - upper-right availability badge on the image surface
  - overlay hierarchy on the image, not in a separate text block
- The action row baseline comes from the corrected dashboard last-week episode card:
  - left `🍿`
  - center `⌚ 🎫 💕`
  - right compact rating, for example `76`
  - one row only, no wrap, no floating
- Overlay hierarchy:
  1. show title (eyebrow)
  2. episode title
  3. `SxxExx • runtime` meta line when runtime exists
  4. contextual submeta such as date where the view needs it
- Icon strip must be single row: `🍿 ⌚ 🎫 💕 76`
- In Watch Me date-grouped rows, the date is not repeated inside the card.
- Dashboard `Up Next` is retired. Dashboard episode browsing now flows through `Upcoming Schedule` and `Last Week`.
