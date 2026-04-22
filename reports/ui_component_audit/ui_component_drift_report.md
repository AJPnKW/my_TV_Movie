<!--
FILE: reports/ui_component_audit/ui_component_drift_report.md
VERSION: 1.0.0
UPDATED: 2026-03-13T00:00:00Z
CHANGE NOTES:
- Initial drift categorization across page families
- Linked component variants to regression risks
-->
# UI Component Drift Report

## Executive Read
The repo does not have one popup/card system with small view wrappers. It has one large inline-app renderer family that forked across `index`, `shows`, `movies`, `discover`, and `calendar`, plus three other independently evolved surfaces (`watch.me`, `watch_me`, `tv_shows_listing`). The biggest risk is not CSS mismatch. It is behavior drift hidden inside duplicated template literals and per-page event wiring.

## Drift Categories

### D1. Markup Drift
- `SHOW_POPUP_APP_V1` and `SHOW_POPUP_APP_V2` share the same hero/season/episode structure, but only some pages inject `.switch.show`, `.switch.season`, and `.switch.episode`.
- `MOVIE_CARD_APP_V1` and `MOVIE_CARD_APP_V2` differ by the presence of `.actionstack` provider buttons even when the rest of the card shell is the same.
- Calendar episode cards use `.chip.cal-episode` wrapping `.epcard`, while show popup episodes use bare `.epcard`; same concept, different wrapper semantics.

### D2. Behavior Drift
- `wireShowPopup()` exists across the app family, but pages with `SHOW_POPUP_APP_V1` still re-render the popup after actions that are impossible to trigger because the matching toggles are not rendered.
- Movie popups drift in watch-state behavior: `shows.html` movie popup lacks popup watch controls while `discover.html`, `calendar.html`, and `index.html` include them.
- Some grids rely on icon-strip actions only; others expose direct provider buttons on the card body.

### D3. Data-Contract Drift
- Episode links are direct in app popups/cards, but `tv_shows_listing` explicitly cascades `episode.links -> season.links -> show.links`. Standardization that assumes episode links always exist will regress that utility surface and possibly some data states elsewhere.
- Air date selection drifts between `pickAirDate(ep)` and direct `ep.air_date`; the family is conceptually aligned but implemented inconsistently.
- Image selection order differs between popup/show/movie/detail variants. Some prefer local poster first, some still/backdrop fallback more aggressively.

### D4. Styling Drift
- Main app family mostly uses inline CSS inside each HTML file rather than a shared component stylesheet.
- `watch_me/watch_me.html` depends on `web/css/my_tv_hub.css` plus local compact styles; the main app family duplicates card/popup styles inline instead of consuming the shared stylesheet.
- The same class names (`.card`, `.meta`, `.badge`) mean different density/layout rules across page families.

### D5. Terminology Drift
- “popup”, “modal”, “details”, “show”, “watch”, and “open info” are used interchangeably for the same conceptual detail surface.
- `watch.me` is a page-level detail view but structurally solves the same “show popup” problem.
- Calendar uses “chip” for what is functionally an episode/movie card.

### D6. Interaction Drift
- Focus/keyboard handling is most explicit in modal shells and `watch_me/watch_me.html`; other card families are mouse-first.
- Calendar cards expose history/date/list/rate actions that are absent from standard show-popup episode cards.
- `heated-rivalry` uses active-card selection plus player modal instead of generic detail navigation.

## Repeated Problems
- Large duplicated template literals copied between page variants.
- Parallel copies of the same event wiring with small behavioral differences.
- Partial upgrades landed in one page but not sibling pages.
- Styling hooks are coupled to exact DOM nesting; shared classes alone are not enough to unify safely.

## Near-Duplicates
- `index.html` and `calendar.html` show popup family are near-duplicates.
- `discover.html`, `shows.html`, and likely `movies.html` are near-duplicate enhanced show popup variants.
- `discover.html` and `calendar.html` movie popup family are near-duplicates with popup watch controls.
- `showCardHtml()` implementations across app-family pages differ mostly in optional toggle/action regions.

## Accidental Forks
- Show popup controls fork: layout stayed aligned while toggle rendering split.
- Movie popup controls fork: some pages received `popupwatch` band, some did not.
- Movie card body fork: some pages received `actionstack`, some did not.

## Cosmetic-Only Drift
- Minor spacing and line-order differences in metadata strings.
- Different line labels such as `Since` vs `Released`.
- Presence or absence of backdrop block when data is missing.

## Structural Drift
- Popup shells are shared in concept but not in componentization.
- Episode cards exist in at least four materially different structures: show popup carousel, calendar chip, watch detail scroller, weekly compact card.
- Tree utility view encodes expansion and link-cascade rules not represented anywhere else.

## Likely Regression Risks If Standardized Badly
- Breaking `wireShowPopup()` by changing markup names without updating event selectors.
- Losing calendar-only action affordances by forcing calendar chips into generic popup episode markup.
- Assuming link availability instead of preserving cascade/fallback behavior.
- Collapsing focus behavior in modal shells or weekly keyboard navigation.
- Reusing generic `.card` classes across page families without isolating scope, causing CSS bleed.

## Severity Findings
- `F01` High: Show popup behavior and markup are split across two incompatible forks.
- `F02` High: Movie popup richness is inconsistent across main app pages.
- `F03` High: Episode link and image fallback expectations are not centralized.
- `F04` Medium: Shared class names hide incompatible DOM shapes.
- `F05` Medium: Calendar episode cards contain actions not represented in the proposed “standard episode card” yet.
- `F06` Medium: `watch.me` and `watch_me` solve detail/action density more cleanly than parts of the main app, but are disconnected from the main renderer family.
