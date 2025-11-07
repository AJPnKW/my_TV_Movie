# my_TV_Movie

A static, GitHub-Pages-hosted TV & Movie hub designed to be friendly on a TV (Chromecast, etc.).

## Live site

Home:

- `https://ajpnkw.github.io/my_TV_Movie/`

Config:

- `https://ajpnkw.github.io/my_TV_Movie/config.html`

## How it works

1. You maintain simple text lists:
   - `tv_list.txt`
   - `movies_list.txt` **or** `movies.txt`
2. GitHub Actions runs `scripts/fetch_tmdb.py` to:
   - Call TMDB (and optionally TVMaze),
   - Generate `data/data.json`.
3. The static web UI (`web/index.html`) reads `data/data.json` and renders:
   - Calendar (TV + Movies),
   - Shows library,
   - Movies library.

Everything runs fully on GitHub Pages — no local server needed for normal use.

## Input formats

### `tv_list.txt`

```text
# name | tmdb_show_id | season_spec | tvmaze_id (optional)
Abbott Elementary|125935|5
Abbott Elementary|125935|5|43354
Only Murders in the Building|107113|5
Stranger Things|66732|5
