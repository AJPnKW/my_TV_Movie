# Episode Card Contract

- Shared across dashboard, calendar, watch_me carousel, and show popup episode carousel.
- 16:9 still image with 10% side trim applied on dashboard/calendar to reduce overly wide framing.
- Overlay hierarchy:
  1. show title (eyebrow)
  2. episode title
  3. `SxxExx • runtime` meta line when runtime exists
  4. contextual submeta such as date where the view needs it
- Icon strip must be single row: `🍿   ⌚ 💕 🔖   ★76%`
- In Watch Me date-grouped rows, the date is not repeated inside the card.
