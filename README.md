README.md

Cut/paste:

# my_TV_Movie

Static TV + Movies + Live TV hub, built from text lists and deployed on GitHub Pages.  
Optimized for TV browsers (Chromecast, Android TV, Shield, etc).

## Live URLs

- Home: <https://ajpnkw.github.io/my_TV_Movie/>
- App: <https://ajpnkw.github.io/my_TV_Movie/web/index.html>
- Config: <https://ajpnkw.github.io/my_TV_Movie/web/config.html>

Open those on your TV and you’re in.

---

## How it works

1. You edit plain text lists:

   - `tv_list.txt`
   - `movies_list.txt`
   - `live_tv_list.txt` (channels stub, for future full EPG)

2. GitHub Actions workflow `Build TV Data and Deploy`:

   - Runs `python scripts/fetch_tmdb.py`
   - Runs `python scripts/fetch_tvmaze.py` (if configured)
   - Runs `python scripts/fetch_omdb.py` (if configured)
   - Runs `python scripts/sync_trakt.py`
   - Writes `data/data.json` (shows, movies, live_tv, meta)
   - Deploys `/web` to GitHub Pages

3. `web/index.html` reads `data/data.json` at runtime.

### Triggers

- Manual: from Actions → **Build TV Data and Deploy**
- Scheduled: every 4 hours via cron (`0 */4 * * *`) if enabled and actions allowed.

Whenever you change `tv_list.txt`, `movies_list.txt`, or `live_tv_list.txt`,
run the workflow so the site picks up your changes.

---

## Input formats

### TV (`tv_list.txt`)

```text
# name | tmdb_show_id | season_spec | tvmaze_id(optional)
Abbott Elementary|125935|5
Abbott Elementary|125935|5|43354
Only Murders in the Building|107113|5
Stranger Things|66732|5

Notes:

    season_spec:

        * → all seasons

        5 → only season 5

        1,2,5 → seasons 1, 2, 5

Movies (movies_list.txt)

# name | tmdb_movie_id
Inception|27205
The Matrix|603

Notes:

    Non-numeric or missing TMDB IDs are ignored.

Live TV (live_tv_list.txt)

# name | country | group | logo(optional) | epg_hint(optional)
CTV Kitchener|CA|Local|ctv.png|ctv_kitchener
BBC One|UK|BBC|bbc_one.png|bbc1

Notes:

    Used to build the Live TV tab.

    logo should match a file in image/services_logos/ or a full URL.

    epg_hint is for mapping to future EPG sources.

Secrets / environment

Set as Repository secrets:

Required:

    API_TMDB_KEY

Recommended / optional:

    API_TMDB_TOKEN

    API_TVMAZE_KEY

    API_OMDB_KEY

    API_TRAKT_CLIENT_ID

    TRAKT_PROFILES (e.g. Andrew:trakt_user1;Brant:trakt_user2)

No secrets are exposed to the browser; everything is used at build time.
Shortcuts

    GitHub Pages: https://ajpnkw.github.io/my_TV_Movie/

Config UI: https://ajpnkw.github.io/my_TV_Movie/web/config.html

Secrets: Settings → Secrets and variables → Actions

Workflow: https://github.com/AJPnKW/my_TV_Movie/actions/workflows/build-data.yml

UI Overview
Calendar

    Monthly grid (7×6), sticky header + Today / Prev / Next.

    Shows:

        Show name → Show popup (seasons list).

        Episode line → Episode popup (details) if available, else season overview.

        Icons: TMDB / VidSrc / Videasy (with season+episode).

    Movies:

        Title → Movie popup.

    Highlight:

        Today clearly shaded.

    Profile-aware (Trakt): can omit episodes already watched for a profile.

Shows

    Grid of shows.

    Filters:

        Genre, Status, When (All/Past/Future/30d/90d).

    Sort:

        Title A–Z/Z–A, Latest, Upcoming.

    Click:

        Show title → Show popup (P1).

        Current season line → same popup focused on that season.

    Popup:

        Seasons (P1) + inline episodes (P2) + episode popup (P3).

Movies

    Grid of movies.

    Filters:

        Genre, Status, When.

    Sort:

        Title, Release date, Upcoming.

    Popup:

        Movie details (P4) + icons.

Live TV (framework)

    Grid of channels from live_tv_list.txt.

    Filters:

        Country, Group.

    Uses logos from image/services_logos/ (via reports mapping).

    Future:

        Map epg_hint to one or more EPG sources for actual schedule.

Config

    Theme (dark / light).

    Font size.

    Quick links to Pages, Secrets, Workflow.

    Inline editors for:

        tv_list.txt

        movies_list.txt

        live_tv_list.txt

    Download buttons to save edited files for commit.
