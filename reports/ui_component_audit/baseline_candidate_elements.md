<!--
FILE: reports/ui_component_audit/baseline_candidate_elements.md
VERSION: 1.0.0
UPDATED: 2026-03-14T00:00:00Z
CHANGE NOTES:
- Added baseline candidate element recommendations from reuse mapping
-->
# Baseline Candidate Elements

## Must-Have Baseline Elements

| target_component | must-have elements | why baseline | main source variants | centralize first? |
|---|---|---|---|---|
| `standard_show_popup` | title block, poster, backdrop header, metadata strip, overview, season list container, season detail panel, episode list container, provider/watch button group, close button | present in both popup forks and reinforced by watch-detail page | `SHOW_POPUP_APP_V2`, `SHOW_POPUP_APP_V1`, `WATCHME_DETAIL_SHOW_V1` | yes |
| `standard_movie_popup` | title block, poster, overview, provider/watch button group, close button | stable across movie popup variants and watch-detail page | `MOVIE_POPUP_APP_V2`, `MOVIE_POPUP_APP_V1`, `WATCHME_DETAIL_MOVIE_V1` | yes |
| `standard_show_card` | title block, poster, metadata strip, primary open action | stable across browse variants even when layout differs | `SHOW_CARD_DISCOVER_V2`, `SHOW_CARD_APP_V1`, `TREE_SHOW_CARD_V1` | yes |
| `standard_movie_card` | title block, poster, metadata strip, primary open action, footer action bar concept | stable across main browse variants | `MOVIE_CARD_APP_V2`, `MOVIE_CARD_APP_V1` | yes |
| `standard_episode_card` | image/media block, S/E badge, title block, metadata strip, provider/deep-link action row, fallback image logic | appears across popup/detail/utility variants | `EPISODE_CARD_POPUP_V2`, `WATCHME_DETAIL_EPISODE_V1`, `TREE_EPISODE_ROW_V1` | yes |

## Optional Baseline Extensions

| target_component | optional elements | reason optional | best source variants |
|---|---|---|---|
| `standard_show_popup` | watch-state controls, network/studio block, production block, genre/tag chip group, rating block | useful but not uniformly rendered in all popup forks | `SHOW_POPUP_APP_V2`, `WATCHME_DETAIL_SHOW_V1` |
| `standard_movie_popup` | watch-state controls, watch-status band, production block, backdrop, genre/tag chip group, rating block | richer fork has them, poorer fork does not | `MOVIE_POPUP_APP_V2`, `WATCHME_DETAIL_MOVIE_V1` |
| `standard_show_card` | inline watched toggle, actionbar/action menu row, status chip | valuable in richer fork but not mandatory in every dense grid | `SHOW_CARD_DISCOVER_V2` |
| `standard_movie_card` | direct provider action stack, inline watched toggle | useful when space allows | `MOVIE_CARD_APP_V2`, `WATCHME_CAROUSEL_MOVIE_V1` |
| `standard_episode_card` | watched toggle, overview/snippet, network/provider logos, secondary action bar | high value, but should scale with context density | `EPISODE_CARD_POPUP_V2`, `CAL_EPISODE_CARD_V1`, `WATCHME_CAROUSEL_EPISODE_V1` |

## Elements That Should Remain Exceptions

| element | keep as exception because | source variants |
|---|---|---|
| calendar dense history/date/list/remove/rate row | too dense for standard popup/detail episode card | `CAL_EPISODE_CARD_V1` |
| weekly carousel shell and keyboard navigation | interaction model is page-specific, not a generic card concern | `WATCHME_CAROUSEL_EPISODE_V1`, `WATCHME_CAROUSEL_MOVIE_V1` |
| twisty expandable children containers | utility-tree behavior is not part of baseline browse/detail cards | `TREE_SHOW_CARD_V1`, `TREE_SEASON_CARD_V1`, `TREE_EPISODE_ROW_V1` |
| campaign playback/download actions | bespoke product experience | `HEATED_EPISODE_CARD_V1`, `HEATED_MODAL_PLAYER_V1` |

## Functions/Helpers To Centralize First

| priority | function_or_helper | reason | affected families |
|---|---|---|---|
| 1 | episode deep-link helper with cascade | current best rule only exists in utility tree variant | show popup episode card, calendar episode card, utility row |
| 2 | `standard_action_bar` renderer | provider, icon strip, mini buttons, and action rows are fragmented versions of the same job | show card, movie card, episode card, popups |
| 3 | `standard_metadata_row` renderer | dates/runtime/genres/ratings/network facts drift in order and wrappers | all five target components |
| 4 | poster/backdrop block helper | repeated in show/movie detail surfaces | show popup, movie popup |
| 5 | watched-toggle renderer | same behavior appears as label switches, buttons, and blanks | show popup, movie popup, show card, movie card, episode card |

## Direct Decisions From Reuse Map

| decision | rationale |
|---|---|
| Put title, poster, metadata, and overview into baseline contracts | these are the most stable elements across variants |
| Treat watch-state controls as baseline-capable but variation-friendly | behavior is broadly reused, markup is not |
| Centralize link and fallback-image logic before markup unification | data-contract drift is a bigger regression risk than visual drift |
| Keep calendar and utility-tree shells out of the first shared markup pass | they are valuable references, but not good direct DOM baselines |
