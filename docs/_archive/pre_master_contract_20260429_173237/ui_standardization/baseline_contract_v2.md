# Baseline Contract V2

Timestamp: `20260314T172445Z`

## Approved Component Set

| component | status | notes |
|---|---|---|
| `show_card` | approved primary baseline | watched toggle, watch status, icon strip |
| `movie_card` | approved primary baseline | watched toggle, watch status, icon strip, popcorn watch entry |
| `episode_card` | approved popup/detail baseline | watched toggle, metadata, popcorn watch entry |
| `show_popup/show_detail` | combined primary baseline | season-aware unified detail surface |
| `movie_popup/movie_detail` | combined primary baseline | unified movie detail surface |
| `episode_row` | approved as episode-card-compatible detail row | same action contract as popup episode card |
| `season_card` | retired from primary baseline | season lives inside unified show detail structures |

## Locked Decisions

| area | decision |
|---|---|
| show detail | `show_popup` and `show_detail` are one baseline contract |
| movie detail | `movie_popup` and `movie_detail` are one baseline contract |
| season representation | season remains inside show detail, not a separate primary baseline component |
| watched coverage | watched toggle contract applies to show, movie, season, and episode surfaces |
| watch status coverage | watch status is implemented now for show/movie and defined for season/episode frontend contract |
| action entry | popcorn-only watch-source entry is the baseline direction |
| providers | legal provider links stay allowed where data exists |
| stream targets | explicit watch-source chooser is required for movie and episode surfaces |
| backend boundary | tracking API integration remains deferred; frontend contract only in this pass |

## Required Controls Per Entity

| entity | watched toggle | watch status | icon strip | provider links | popcorn watch entry |
|---|---|---|---|---|---|
| show | required | required | required | required where data exists | optional |
| season | required | frontend contract defined | required through show detail context | required where data exists | optional |
| episode | required | frontend contract defined | required | required where data exists | required |
| movie | required | required | required | required where data exists | required |

## Popcorn-Only Watch Entry Model

- Primary watch-source entry is a single popcorn button.
- The popcorn button opens a chooser modal.
- Chooser sources may include:
  - local or owned URLs
  - existing embed URLs already present in repo data
  - legal provider deep links from `watch_providers`
  - future configured `watch_sources` or `source_options`
- No new questionable backup providers are introduced in this pass.

## Deferred Boundaries

- tracking API persistence for season and episode watch status
- backend write orchestration for watch history and source selection
- redesign of calendar dense rows, weekly carousel shell, and tree/twisty pages
