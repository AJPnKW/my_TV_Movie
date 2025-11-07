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
	2. Workflow `Build TV Data and Deploy Pages` runs:
	   - `python scripts/fetch_tmdb.py`
	   - Writes `data/data.json` + `data/last_refresh.txt`
	   - Deploys site to GitHub Pages.
	3. `web/index.html` reads `data/data.json` at runtime.

After updating lists, either wait for the schedule (every 4 hours) or run
the workflow manually.
Whenever you change `tv_list.txt` or `movies_list.txt`, you must run the
**Build TV Data** workflow so the site picks up your changes.

## Input formats

### TV (`tv_list.txt`)

	```text
	# name | tmdb_show_id | season_spec | tvmaze_id
	Abbott Elementary|125935|5
	Abbott Elementary|125935|5|43354
	Only Murders in the Building|107113|5
	Stranger Things|66732|5
	
    note: 	season_spec:
		5 → only season 5
		1,2,5 → seasons 1, 2, 5
		* → all seasons

### Movies (`movies_list.txt`)

	# name | tmdb_movie_id | tvmaze_id
	40 Acres | 1319951 |
	Argylle | 848538 |
	Avatar: Fire and Ash | 83533 |
	Avengers: Doomsday | 1003596 |

    note: 	Non-numeric IDs like TBD are ignored.

## Secrets

Set as Repository secrets:
    API_TMDB_KEY
    API_TMDB_TOKEN (optional)
    API_TVMAZE_KEY (optional)
    API_OMDB_KEY (optional helper only)

## Shortcuts:

    Secrets: https://github.com/AJPnKW/my_TV_Movie/settings/secrets/actions

Workflow: https://github.com/AJPnKW/my_TV_Movie/actions/workflows/build-data.yml

## Workflow

.github/workflows/build-data.yml:

    ### Triggers:
        Manual (workflow_dispatch)
        Scheduled (0 */4 * * * = every 4 hours)

    Steps:
        Checkout
        Python + deps
        Run scripts/fetch_tmdb.py
        Upload + deploy via GitHub Pages actions
    Note: Make sure Settings → Pages is configured to use GitHub Actions.

## UI

    ### Calendar
        Month view, sticky header.
        TV episodes + movie releases.
        Episode links: TMDB / VidSrc / Videasy with season+episode.
        Click show/episode → overlay (seasons + episodes).

    ### Shows
        Grid, posters, status, genres.
        Sticky filters:
            Line 1: Genre
            Line 2: Sort (A–Z/Z–A), Status
        Click show → overlay.

    ### Movies
        Grid, posters, genres, release date.
        Genre + Status filters, title/date sort.

    ### Config
        Dark / Light
        Font size
        Shows last refresh
        Links to secrets + workflow

That’s the whole loop.
