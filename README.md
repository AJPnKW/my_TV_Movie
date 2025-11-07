Here’s the complete `README.md` as clean pasteable text (no extra chatter, formatting fixed, movies format corrected to what the code expects):

````markdown
# my_TV_Movie

Static TV + Movies hub, built from text lists and deployed on GitHub Pages.  
Optimized for TV browsers (Chromecast, Android TV, Shield, etc).

## Live

- Home: <https://ajpnkw.github.io/my_TV_Movie/>
- Index: <https://ajpnkw.github.io/my_TV_Movie/web/index.html>
- Config: <https://ajpnkw.github.io/my_TV_Movie/web/config.html>

Open those on your TV and you’re in.

## How it works

1. Edit:
   - `tv_list.txt`
   - `movies_list.txt` (or `movies.txt`)
2. Workflow **Build TV Data and Deploy Pages** runs:
   - `python scripts/fetch_tmdb.py`
   - Writes `data/data.json` + `data/last_refresh.txt`
   - Deploys site to GitHub Pages.
3. `web/index.html` reads `data/data.json` at runtime.

After updating lists, either wait for the schedule (every 4 hours) or run
the workflow manually so the site picks up your changes.

## Input formats

### TV (`tv_list.txt`)

```text
# name | tmdb_show_id | season_spec | tvmaze_id (optional)
Abbott Elementary|125935|5
Abbott Elementary|125935|5|43354
Only Murders in the Building|107113|5
Stranger Things|66732|5
````

Notes:

* `season_spec`:

  * `5`       → only season 5
  * `1,2,5`   → seasons 1, 2, and 5
  * `*`       → all seasons from TMDB
* `tvmaze_id` (optional) is used (if `API_TVMAZE_KEY` is set) to improve episode
  titles, air dates, and descriptions.

### Movies (`movies_list.txt`)

```text
# name | tmdb_movie_id
Dune: Part Two|693134
Tenet|577922
The Fall Guy|746036
```

Notes:

* One movie per line.
* First field is the display name, second is the TMDB movie ID.
* Non-numeric IDs like `TBD` are ignored.

## Secrets

Set these as **Repository secrets**:

* `API_TMDB_KEY`
* `API_TMDB_TOKEN` (optional)
* `API_TVMAZE_KEY` (optional)
* `API_OMDB_KEY` (optional helper only)

## Shortcuts

* Secrets: [https://github.com/AJPnKW/my_TV_Movie/settings/secrets/actions](https://github.com/AJPnKW/my_TV_Movie/settings/secrets/actions)
* Workflow: [https://github.com/AJPnKW/my_TV_Movie/actions/workflows/build-data.yml](https://github.com/AJPnKW/my_TV_Movie/actions/workflows/build-data.yml)

## Workflow

File: `.github/workflows/build-data.yml`

Triggers:

* Manual: `workflow_dispatch`
* Scheduled: `0 */4 * * *` (every 4 hours, UTC)

Steps (summary):

* Checkout
* Setup Python + deps
* Run `scripts/fetch_tmdb.py`
* Upload + deploy via GitHub Pages actions

Make sure **Settings → Pages** is configured to use **GitHub Actions**.

## UI

### Calendar

* Month view with sticky header.
* TV episodes + movie releases.
* Episode links:

  * TMDB / VidSrc / Videasy with correct season + episode.
* Click show/episode → overlay with seasons and episodes.

### Shows

* Grid with posters, status, and genres.
* Sticky filters:

  * Line 1: Genre
  * Line 2: Sort (A–Z / Z–A), Status
* Click show → overlay with season/episode details.

### Movies

* Grid with posters, genres, status, and release date.
* Genre + Status filters.
* Sort by title or release date.

### Config

* Dark / Light theme.
* Font size.
* Shows last refresh timestamp.
* Links to secrets + workflow.

That’s the whole loop.

```
::contentReference[oaicite:0]{index=0}
```


# my_TV_Movie

Static TV + Movies hub, built from text lists and deployed on GitHub Pages.  
Optimized for TV browsers (Chromecast, Android TV, Shield, etc).

## Live

- Home: <https://ajpnkw.github.io/my_TV_Movie/>
- Index: <https://ajpnkw.github.io/my_TV_Movie/web/index.html>
- Config: <https://ajpnkw.github.io/my_TV_Movie/web/config.html>

Open those on your TV and you’re in.

## How it works

1. Edit:
   - `tv_list.txt`
   - `movies_list.txt` (or `movies.txt`)
2. Workflow **Build TV Data and Deploy Pages** runs:
   - `python scripts/fetch_tmdb.py`
   - Writes `data/data.json` + `data/last_refresh.txt`
   - Deploys site to GitHub Pages.
3. `web/index.html` reads `data/data.json` at runtime.

After updating lists, either wait for the schedule (every 4 hours) or run
the workflow manually so the site picks up your changes.

## Input formats

### TV (`tv_list.txt`)

```text
# name | tmdb_show_id | season_spec | tvmaze_id (optional)
Abbott Elementary|125935|5
Abbott Elementary|125935|5|43354
Only Murders in the Building|107113|5
Stranger Things|66732|5

Notes:

    season_spec:

        5 → only season 5

        1,2,5 → seasons 1, 2, and 5

        * → all seasons from TMDB

    tvmaze_id (optional) is used (if API_TVMAZE_KEY is set) to improve episode
    titles, air dates, and descriptions.

Movies (movies_list.txt)

# name | tmdb_movie_id
Dune: Part Two|693134
Tenet|577922
The Fall Guy|746036

Notes:

    One movie per line.

    First field is the display name, second is the TMDB movie ID.

    Non-numeric IDs like TBD are ignored.

Secrets

Set these as Repository secrets:

    API_TMDB_KEY

    API_TMDB_TOKEN (optional)

    API_TVMAZE_KEY (optional)

    API_OMDB_KEY (optional helper only)

Shortcuts

    Secrets: https://github.com/AJPnKW/my_TV_Movie/settings/secrets/actions

Workflow: https://github.com/AJPnKW/my_TV_Movie/actions/workflows/build-data.yml
Workflow

File: .github/workflows/build-data.yml

Triggers:

    Manual: workflow_dispatch

    Scheduled: 0 */4 * * * (every 4 hours, UTC)

Steps (summary):

    Checkout

    Setup Python + deps

    Run scripts/fetch_tmdb.py

    Upload + deploy via GitHub Pages actions

Make sure Settings → Pages is configured to use GitHub Actions.
UI
Calendar

    Month view with sticky header.

    TV episodes + movie releases.

    Episode links:

        TMDB / VidSrc / Videasy with correct season + episode.

    Click show/episode → overlay with seasons and episodes.

Shows

    Grid with posters, status, and genres.

    Sticky filters:

        Line 1: Genre

        Line 2: Sort (A–Z / Z–A), Status

    Click show → overlay with season/episode details.

Movies

    Grid with posters, genres, status, and release date.

    Genre + Status filters.

    Sort by title or release date.

Config

    Dark / Light theme.

    Font size.

    Shows last refresh timestamp.

    Links to secrets + workflow.

That’s the whole loop.







