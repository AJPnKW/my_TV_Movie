# Baseline Contract v3

## Locked Baseline

- Primary component set: `show_card`, `movie_card`, `episode_card`, unified `show_popup/show_detail`, unified `movie_popup/movie_detail`, `episode_row`.
- `season_card` is retired from the primary baseline. Seasons live only inside show detail.
- Hot dog action strips are removed from the main app family baseline.
- Inline watch-status bands/sliders are removed from the baseline.
- Popcorn watch-now belongs inside the shared action bar where direct playback makes sense.

## Shared Block Names

- `media_block`
- `action_bar`
- `title_block`
- `meta_row`
- `provider_group`
- `source_chooser`
- `status_control`
- `tag_group`
- `context_block`

## Action Bar Contract

Ordered baseline:

1. Popcorn watch-now chooser at far left when applicable.
2. Add to favourites.
3. Popup bullet-style watch-status selector.
4. Watched toggle.
5. Heart/rating control near the right edge.
6. Rating/love percent at far right when present.

Rules:

- Popcorn appears on movie and episode surfaces.
- Shows do not expose popcorn as the primary action.
- Show, season, episode, and movie status controls must share one frontend contract.

## Card Structures

### Show Card

- `media_block`
- `action_bar`
- `title_block`
- `meta_row` with release, status, and season/episode summary
- `provider_group`
- `context_block`
- `tag_group`

### Movie Card

- `media_block`
- `action_bar`
- `title_block` with movie title and runtime
- `meta_row` with release date
- `provider_group`
- `context_block`
- `tag_group`

### Episode Card / Row

- `media_block`
- `action_bar`
- `title_block` with episode title, `S##E##`, runtime
- secondary line with show name
- `meta_row` with air date
- `provider_group`
- `context_block`
- `tag_group` when available

## Show Detail Contract

- Show detail is the combined baseline for popup/detail.
- Season sections live inside show detail.
- Episode rows live inside season sections.
- Show poster, title, and details view areas open show detail unless already inside show detail.

