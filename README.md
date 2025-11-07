# my_TV_Movie

A static, GitHub-Pages-hosted TV & Movie hub designed to be used on your TV
(Chromecast, built-in browser, etc).

## Live site

- Home: [https://ajpnkw.github.io/my_TV_Movie/](https://ajpnkw.github.io/my_TV_Movie/)
- Direct index: [https://ajpnkw.github.io/my_TV_Movie/web/index.html](https://ajpnkw.github.io/my_TV_Movie/web/index.html)
- Config page: [https://ajpnkw.github.io/my_TV_Movie/web/config.html](https://ajpnkw.github.io/my_TV_Movie/web/config.html)

Open those on your TV and you’re in.

## How it works (for Future You)

1. You edit simple text files in the repo:
   - `tv_list.txt`
   - `movies_list.txt` (or `movies.txt`)
2. A GitHub Actions workflow runs `scripts/fetch_tmdb.py`:
   - Calls TMDB (and optionally TVMaze),
   - Writes `data/data.json` + `data/last_refresh.txt`.
3. The web UI (`web/index.html`) is 100% static and reads `data/data.json` on load.

Whenever you change `tv_list.txt` or `movies_list.txt`, you must run the
**Build TV Data** workflow so the site picks up your changes.

You can run it manually, or schedule it (see below).

## Input formats

### TV (`tv_list.txt`)

```text
# name | tmdb_show_id | season_spec | tvmaze_id (optional)
Abbott Elementary|125935|5
Abbott Elementary|125935|5|43354
Only Murders in the Building|107113|5
Stranger Things|66732|5
