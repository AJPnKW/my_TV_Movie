<!--
FILE: reports/ui_component_audit/shared_vs_page_specific_map.md
VERSION: 1.0.0
UPDATED: 2026-03-14T00:00:00Z
CHANGE NOTES:
- Added shared vs page-specific element/function buckets for first refactor planning
-->
# Shared vs Page-Specific Map

## 1. Must Be Shared In Baseline

| item_type | item | current names/selectors/functions | target components | why shared |
|---|---|---|---|---|
| element | title block | `.showtitle`, `.cardtitle`, `.epTitle`, `.ov .n`, `.primary.line1` | all five targets | universally present identity element |
| element | poster/media block | `.poster`, `.imgbox`, `.media.mv`, `.media.ep`, `.thumb` | show popup, movie popup, show card, movie card, episode card | stable visual anchor across all families |
| element | metadata strip | `.showmeta`, `.cardmeta`, `.epmeta`, pill row, utility line2 | all five targets | same data facts recur everywhere |
| element | description/overview | `.overview`, `.epov`, `.epOverview`, inline overview div | show popup, movie popup, episode card | repeated detail content |
| element | provider/deep-link logic | `buildMediaLinks()`, `linkOrDisabled()`, `getLinksCascade()`, `.actionstack`, `.pillbar`, `.epactions` | movie popup, standard episode card, movie card | high regression risk if left fragmented |
| function | watch/provider modal opener | `renderWatchProvidersHtml()` + provider modal wiring | show popup, movie popup | already shared conceptually |
| function | fallback image selection | `pickImage()`, detail-page image resolvers, utility thumb selection | all visual targets | same problem solved repeatedly |

## 2. Shared With Variation

| item_type | item | current names/selectors/functions | target components | variation rule |
|---|---|---|---|---|
| element | watch-state controls | `.switch.show`, `.switch.movie`, `.switch.episode`, `.watched-toggle` | show popup, movie popup, show card, movie card, episode card | shared behavior, variant-specific density and control shape |
| element | genre/tag chip group | `.pills .pill`, watch detail pill row, status chips | show popup, movie popup, show card, movie card | compact on cards, fuller on popups |
| element | rating block | pill summary, metadata row, utility line item | show popup, movie popup, cards | can collapse into metadata strip on dense views |
| element | badges/status chips | `.statuspill`, `.badge`, `.epBadge`, `.episode-num-pill` | show popup, episode card, show/movie card | semantics shared, visuals can vary |
| element | provider/watch button group | `.showactions`, `.actionstack`, `.epactions`, `.links`, `.pillbar` | popups, movie card, episode card | same concept, different density/layout |
| element | episode list container | `.carousel`, `#episodesScroller`, `.children` | show popup, detail show page | shared concept, page-specific container mechanics |
| function | action-row renderer | `buildIconStripHtml()`, card actionbar rows, calendar action rows | cards and episodes | shared abstraction with context-specific button sets |

## 3. Keep Page-Specific

| item_type | item | source variants | keep local because |
|---|---|---|---|
| element | calendar dense episode action row | `CAL_EPISODE_CARD_V1` | optimized for calendar workflow, too dense for baseline |
| element | weekly carousel shell and keyboard navigation | `WATCHME_CAROUSEL_EPISODE_V1`, `WATCHME_CAROUSEL_MOVIE_V1` | page-level interaction model, not component-level baseline |
| element | twisty expandable containers | `TREE_SHOW_CARD_V1`, `TREE_SEASON_CARD_V1`, `TREE_EPISODE_ROW_V1` | utility explorer behavior |
| element | campaign download/play row | `HEATED_EPISODE_CARD_V1` | bespoke feature set |
| function | player modal logic | `HEATED_MODAL_PLAYER_V1` | different purpose from detail popup |

## 4. Out Of Scope For First Refactor Pass

| item | source | reason out of scope |
|---|---|---|
| `heated-rivalry` episode cards and modal player | `web/heated-rivalry.html` | bespoke campaign experience |
| weekly watch carousel card shells | `web/watch_me/watch_me.html` | separate interaction surface with API-backed watched state |
| utility tree layout markup | `web/tv_shows_listing.html` | not part of the browse/detail visual baseline migration |
| admin editor cards | `web/inputs_editor.html`, `web/library_editor.html` | not user-facing product baseline |

## Naming and Contract Warnings

| warning_type | item | impact |
|---|---|---|
| same selector, different contract | `.card` | cannot be globalized safely across app, carousel, and utility tree |
| same concept, different names | title block | helper should be semantic, not selector-driven |
| same behavior, different control type | watched toggle | implementation must normalize event/data contract before markup |
| hidden helper gap | episode link cascade | must be added before standardizing episode action rows |
