<!--
FILE: reports/ui_component_audit/ui_element_function_matrix.md
VERSION: 1.0.0
UPDATED: 2026-03-14T00:00:00Z
CHANGE NOTES:
- Added reusable element/function mapping layer for card and popup families
- Grouped shared, hybrid, and local element decisions by component family
-->
# UI Element Function Matrix

## Reading Guide
- `shared`: element should become part of the approved baseline contract
- `hybrid`: element is common enough to standardize conceptually, but layout or behavior should vary by page density
- `local`: element should stay page-specific or remain outside the first refactor pass

## Function Reuse Index

| helper_or_renderer | families using it | pages observed | reuse value | notes |
|---|---|---|---|---|
| `buildShowPopupHtml()` | show popup, popup episode card | `web/index.html`, `web/discover.html`, `web/calendar.html`, `web/shows.html`, `web/movies.html` | very high | Main structural source for standard show popup |
| `wireShowPopup()` | show popup, popup episode interactions | same app family | very high | Hard-coupled to modal DOM and `data-watch-*` hooks |
| `openMovieModal()` / `wireMoviePopup()` | movie popup | app family | very high | V1/V2 drift is behavioral, not conceptual |
| `showCardHtml()` | show card | app family | high | V1/V2 drift is mainly toggle/action regions |
| `movieCardHtml()` | movie card | app family | high | Direct provider action stack appears only in richer fork |
| `buildMediaLinks()` | show popup, movie popup, movie card, popup episode card, calendar cards | app family | very high | Baseline helper candidate |
| `renderWatchProvidersHtml()` | show popup, movie popup | app family | high | Provider modal contract should remain stable |
| `getLinksCascade()` | utility episode row | `web/tv_shows_listing.html` | high | Not reused yet, but should be centralized before refactor |
| `buildPills()` / `renderPillRow()` | watch detail show/movie | `web/watch.me.html` | medium | Good source for standard metadata/fact strip abstraction |
| `episodeCard()` | compact episode card | `web/watch_me/watch_me.html` | medium | Strong compact-density reference, not popup baseline |

## Show Popup Family

| variant_id | render_function | key shared elements | hybrid elements | local elements | selector/contracts to preserve |
|---|---|---|---|---|---|
| `SHOW_POPUP_APP_V1` | `buildShowPopupHtml()` | title block, poster, backdrop, metadata strip, overview, season list, season detail, episode list container, close button via modal shell | badges/status chips, provider/watch button group, watch-state band shell | none in markup, but toggle regions are blank | `.showwrap`, `.showtitle`, `.seasonopt`, `.carousel`, `#modalClose` |
| `SHOW_POPUP_APP_V2` | `buildShowPopupHtml()` + `wireShowPopup()` | same as V1 plus full watch-state controls | watch-state controls, badges/status chips, network logo block | none | `.switch.show`, `.switch.season`, `.switch.episode`, `[data-watch-show]`, `[data-watch-season]`, `[data-watch-episode]` |
| `WATCHME_DETAIL_SHOW_V1` | `renderShow()` + `renderSeasonDetail()` | title block, poster, backdrop, overview, season list, season detail, episode list container | metadata strip, fact strip, deep-link buttons | page-level layout shell, no modal close | `#seasonList`, `#episodesScroller`, `.infoCard`, `.sectionCard` |

## Movie Popup Family

| variant_id | render_function | key shared elements | hybrid elements | local elements | selector/contracts to preserve |
|---|---|---|---|---|---|
| `MOVIE_POPUP_APP_V1` | `openMovieModal()` | title block, poster, overview, provider/watch button group, production block, optional backdrop, close button via modal shell | production block, backdrop | missing popup watch band | `[data-where-watch='movie']`, `#modalClose` |
| `MOVIE_POPUP_APP_V2` | `openMovieModal()` + `wireMoviePopup()` | title block, poster, overview, provider/watch button group, production block, optional backdrop, close button | watch-state controls, watch-status band | none | `.popupwatch`, `.switch.movie`, `[data-watch-movie-popup]`, `[data-watch-status-choice]` |
| `WATCHME_DETAIL_MOVIE_V1` | `renderMovie()` | title block, poster, backdrop, overview, deep-link/provider-link logic | metadata/fact strip | page shell, no provider modal | `#movieVidsrcBtn`, `#movieVideasyBtn`, `#tmdbBtn` |

## Show Card Family

| variant_id | render_function | key shared elements | hybrid elements | local elements | selector/contracts to preserve |
|---|---|---|---|---|---|
| `SHOW_CARD_APP_V1` | `showCardHtml()` | title block, poster, metadata strip, icon/action footer | footer action bar | none | `.card`, `.imgbox`, `.cardmeta`, `data-show-open` |
| `SHOW_CARD_DISCOVER_V2` | `showCardHtml()` | title block, poster, metadata strip | inline watched toggle, actionbar/action menu row | none | `.cardtoggle`, `.actionbar[data-action-host='1']`, `data-watch-show` |
| `TREE_SHOW_CARD_V1` | `buildShowCard()` | title concept, metadata concept, provider link row | provider/watch button group | expandable children container, twisty utility flow | `.children`, `.pillbar`, twisty button state |

## Movie Card Family

| variant_id | render_function | key shared elements | hybrid elements | local elements | selector/contracts to preserve |
|---|---|---|---|---|---|
| `MOVIE_CARD_APP_V1` | `movieCardHtml()` | title block, poster, metadata strip, icon/action footer | footer action bar | none | `.card`, `.imgbox`, `data-movie-open` |
| `MOVIE_CARD_APP_V2` | `movieCardHtml()` | title block, poster, metadata strip | direct provider action stack, inline watched toggle in discover fork | none | `.actionstack`, `.cardtoggle`, `data-watch-movie` |
| `CAL_MOVIE_CARD_V1` | `renderCalendar()` | title concept, poster/thumb concept, provider actions concept | compact metadata, compact watched state | chip shell, calendar mini-actions | `.chip`, `.thumb`, calendar data attributes |
| `WATCHME_CAROUSEL_MOVIE_V1` | `movieCard()` | title concept, poster/media concept, provider actions concept | compact watched toggle, overlay metadata | keyboard-driven weekly carousel shell | `.media.mv`, `.watched-toggle`, `.links .iconbtn` |

## Episode Card/Row Family

| variant_id | render_function | key shared elements | hybrid elements | local elements | selector/contracts to preserve |
|---|---|---|---|---|---|
| `EPISODE_CARD_POPUP_V1` | `buildShowPopupHtml()` | episode card shell, image/media block, badge, title, metadata strip, overview, action row | fallback image logic | none | `.epcard`, `.epimg`, `.badge`, `.epactions` |
| `EPISODE_CARD_POPUP_V2` | `buildShowPopupHtml()` | same as V1 | inline watched toggle | none | `.switch.episode`, `[data-watch-episode]` |
| `CAL_EPISODE_CARD_V1` | `renderCalendar()` | episode identity, provider link logic, show badge/network block concept | provider logos, action row, compact metadata | dense history/list/remove/rate row, calendar chip shell | `.chip.cal-episode`, `.ep-side-actions`, `.ep-actions-row` |
| `WATCHME_DETAIL_EPISODE_V1` | `renderSeasonDetail()` | image block, badge, title, metadata strip, overview, action row | TMDB + provider mini-button layout | watch-detail page shell | `.epCard`, `.epBadge`, `.miniBtn` |
| `WATCHME_CAROUSEL_EPISODE_V1` | `episodeCard()` | title concept, provider link logic | compact watched switch, overlay copy stack | weekly carousel shell and keyboard behavior | `.media.ep`, `.watched-toggle`, `.ov` |
| `TREE_EPISODE_ROW_V1` | `buildEpisodeRow()` | title concept, metadata strip, provider link logic | thumb size/layout | utility row shell and cascade-first helper | `.ep-row`, `.pillbar`, `getLinksCascade()` |
| `HEATED_EPISODE_CARD_V1` | `renderEpisodeCards()` | badge/title/meta/action concept | hero still stack | campaign actions, download, active card behavior | `.episode-card`, `.episode-card-actions`, `.episode-num-pill` |

## Same Concept, Different Names

| concept | names/selectors observed | implication |
|---|---|---|
| title block | `.showtitle`, `.cardtitle`, `.epTitle`, `.ov .n`, `.primary.line1` | Shared conceptual element, not shared DOM contract |
| metadata strip | `.showmeta`, `.cardmeta`, `.epmeta`, pill row, utility line2 | Good candidate for `standard_metadata_row` helper |
| action row | `buildIconStripHtml()`, `.actionbar`, `.actionstack`, `.epactions`, `.pillbar`, `.links` | One concept, multiple implementations |
| watched toggle | `.switch.show`, `.switch.movie`, `.switch.episode`, `.watched-toggle`, blank placeholders | Standardize behavior first, selector contract second |
| badge | `.badge`, `.epBadge`, `.episode-num-pill` | Shared identity marker; exact shape can vary |

## Same Selector Name, Different DOM Contract

| selector | where it appears | contract difference |
|---|---|---|
| `.card` | app grids, `watch_me/watch_me`, utility tree | full poster card vs compact carousel card vs expandable utility row |
| `.meta` | `tv_shows_listing`, watch detail helpers, other local variants | container meaning varies between title/meta shell and subtext row |
| `.badge` | popup episode cards, utility episode rows, calendar cards | may mean S/E pill, action percent, or generic status |

## Centralization Priority From Element/Function Reuse

| priority | function_or_abstraction | why first |
|---|---|---|
| 1 | shared episode link helper with cascade support | prevents regressions while standardizing episode cards |
| 2 | `standard_action_bar` abstraction | action rows drift most across cards/popups |
| 3 | `standard_metadata_row` abstraction | same facts appear in different orders and wrappers |
| 4 | shared poster/backdrop block helper | show/movie detail surfaces already align strongly |
| 5 | unified watch-state control rendering helper | toggles exist in three incompatible forms |
