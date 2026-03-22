# View Navigation Tree

## Primary Navigation

- Dashboard
  - Up Next
  - Upcoming Schedule
  - Last Week
  - Watchlist
  - Recommended Shows
  - Recommended Movies
- Shows
  - Left filter rail
  - Show grid
  - Show detail popup
    - Series hero
    - Where to watch
    - Season navigator rail
    - Season detail surface
    - Episode carousel
- Movies
  - Left filter rail
  - Movie grid
  - Movie detail popup
    - Movie hero
    - Fact rows
    - Where to watch
    - Backdrop surface
- Watch Me
  - Left filter rail
  - Upcoming Episodes group rows
  - Upcoming Movies group rows
- Calendar
  - Month toolbar
  - 7-column month grid
  - Day cells
    - Episode cards
    - Movie cards
    - `+X more` / `Show less`
- Discover
  - Intro surface
  - Featured show
  - Featured movie
  - Show picks
  - Movie picks
- Config
  - Runtime overview
  - Quick links
  - Config renderer surface
- Inputs Editor
  - In-app launcher surface
  - Local editor route

## Shared Modal Layers

- Detail popup
  - Exit button
  - Shared action bar
  - Shared availability badge
- Provider popup
  - Exit button
  - Direct watch source chooser
  - Provider chips

## Shared Card Families

- `show_card`
- `movie_card`
- `episode_card`
- `season summary surface`

## Shared Interaction Rules

- D-pad first
- Focus enters `Exit` first on modals
- Action strip stays one row
- Provider popup auto-closes after launching a source
