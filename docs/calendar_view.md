# Calendar View UI Contract

## Purpose

Full-width wall-calendar for release tracking. This page is distinct from dashboard browse layouts and must not inherit a left rail.

## Page Layout

1. Sticky top app header
2. Sticky calendar control bar
3. Sticky weekday row
4. Seven-column month grid on desktop
5. Compact release cards inside each day cell

## Page-Level Rules

- full-width main content
- no left sidebar
- previous, next, and today controls live inline with the month label
- controls must not consume an entire separate row
- weekday row remains sticky under the page header

## Day Cell Contract

- date number at top-left
- weekday label visible in the cell
- up to 3 visible items by default
- `+X more` appears when more than 3 items exist
- expanding swaps the button label to `Show less`
- collapsing hides extra items and restores the original count

## Card Contract Inside Calendar

- compact episode and movie cards only
- same canonical icon strip grouping as their parent card models
- summary text hidden
- hierarchy, title, meta, and action strip preserved

## Data Mapping

Calendar events are derived from runtime release data in `data/data.json`:

- episode date: `episode.air_date`
- episode title: `episode.name` or `episode.title`
- episode hierarchy: parent show `title` or `name`
- movie date: `movie.release_date`
- movie title: `movie.title`
- rating percent: normalized vote average
- action availability: links and local watch state derived from runtime helpers

## Sticky Rules

- top header is sticky
- calendar controls are sticky below the header
- weekday row is sticky below the controls
- sticky offsets must be computed so rows never overlap

## Responsive Behavior

- desktop: seven columns
- tablet: reduced columns but still wall-calendar behavior before single-column collapse
- phone: one column stacked days is allowed, but sticky controls remain usable
- Android TV: control buttons and day cards must remain focusable without hidden overflow traps

## Must Never Appear

- left sidebar
- dashboard blocks reused as calendar layout
- `+X more` after the fourth item instead of the third
- expanded items that fail to collapse on `Show less`
