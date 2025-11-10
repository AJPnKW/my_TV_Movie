# my_TV_Movie

Static personal TV & Movies hub.  
Data from simple text files → built by GitHub Actions → served via GitHub Pages.  
Designed to work well on TV browsers (Chromecast, Shield, Android TV, etc).

---

## Live URLs

- Hub (SPA): <https://ajpnkw.github.io/my_TV_Movie/web/index.html>
- Root (redirect/entry): <https://ajpnkw.github.io/my_TV_Movie/>
- Config page: <https://ajpnkw.github.io/my_TV_Movie/web/config.html>
- Built data (for debugging): <https://ajpnkw.github.io/my_TV_Movie/data/data.json>

Open the **Hub** URL on your TV. Everything else hangs off that.

---

## How It Works

1. You maintain text lists in the repo:
   - `tv_list.txt`
   - `movies_list.txt`
   - (optional) `live_tv_list.txt` for future Live TV

2. GitHub Actions workflow  
   `.github/workflows/build-data.yml`:

   - Runs every **4 hours** and on **manual trigger**.
   - Calls `scripts/fetch_tmdb.py`:
     - Fetches show, season & episode data from TMDB.
     - Fetches movie data from TMDB.
     - Writes `data/data.json`.
     - Fails the build if:
       - `API_TMDB_KEY` missing, or
       - `tv_list.txt` has entries but 0 shows built, or
       - `movies_list.txt` has entries but 0 movies built.
   - If build passes, deploys the site to GitHub Pages.

3. `web/index.html` (SPA):

   - Loads `data/data.json`.
   - Renders:
     - **Calendar** (episodes + movie releases).
     - **Shows** grid.
     - **Movies** grid.
     - **Live TV** (skeleton using your channel/logo list).
     - **Config** (display + shortcuts + helpers).
   - All views share the same overlay system (show / season / episode / movie popups).

If `data.json` is broken or missing, the page shows a clear warning instead of silently lying.

---

## Input File Formats

### 1. TV Shows — `tv_list.txt`

One show per line:

```text
# name | tmdb_show_id | season_spec | tvmaze_id(optional)

Abbott Elementary|125935|5
Abbott Elementary|125935|5|43354
Only Murders in the Building|107113|5
Stranger Things|66732|5
```

**Rules:**

- `tmdb_show_id` — numeric TMDB TV ID (required).
- `season_spec`:
  - `*` → all seasons
  - `5` → only season 5
  - `1,2,5` → seasons 1, 2, and 5
- `tvmaze_id` — optional, reserved for future enrichment.
- Lines starting with `#` are comments.
- Empty / malformed lines are ignored (with warnings in workflow logs).

### 2. Movies — `movies_list.txt`

One movie per line:

```text
# name | tmdb_movie_id

28 Years Later|1100988
Argylle|848538
The Black Phone 2|1197137
The Hunger Games: Sunrise on the Reaping|1300968
```

**Rules:**

- `tmdb_movie_id` — numeric TMDB movie ID (required).
- Lines starting with `#` are comments.
- Non-numeric IDs are ignored (warned in logs).
- If this file has valid entries but `data.json` ends up with 0 movies, the workflow fails.

### 3. Live TV (future) — `live_tv_list.txt` (optional)

Reserved skeleton; not required yet.  
Intended format (subject to refinement):

```text
# name | country | group | logo_file(optional) | location/notes

CBC|CA|General|cbc.png|Eastern
TSN|CA|Sports|tsn.png|
```

Logos are expected under: `image/services_logos/`.

---

## Secrets / API Keys

Set these as **Repository secrets**  
(`Settings → Secrets and variables → Actions`):

Required:

- `API_TMDB_KEY` — TMDB API key.

Optional / future use (safe to set now):

- `API_TMDB_TOKEN`
- `API_TVMAZE_KEY`
- `API_OMDB_KEY`
- `API_TRAKT_CLIENT_ID`
- `API_TRAKT_CLIENT_SECRET`
- `API_TRAKT_TV_USER` (or similar)

The workflow and scripts are written to **fail loudly** if critical pieces are missing,
instead of deploying half-broken data.

---

## GitHub Actions

### Workflow file

`/.github/workflows/build-data.yml`

Key points:

- **Triggers**
  - `workflow_dispatch` (manual)
  - `schedule: "0 */4 * * *"` (every 4 hours)

- **Steps**
  - Checkout repo
  - Setup Python
  - `pip install -r requirements.txt` (if present)
  - Run:
    - `python scripts/fetch_tmdb.py`
    - Validate `data/data.json`:
      - Must exist
      - Must have at least some shows or some movies (if inputs provided)
  - Upload as Pages artifact
  - Deploy to GitHub Pages

- **Permissions**
  - `contents: read`
  - `pages: write`
  - `id-token: write`
  - `deploy` job uses `environment: github-pages`

If something is wrong (bad IDs, missing API key, parsing errors),
the job fails with a clear message in the logs.

---

## UI Overview

All in `web/index.html` (SPA).

### Tabs

- **Calendar**
- **Shows**
- **Movies**
- **Live TV**
- **Config**

### Calendar

- Sticky month header (`Prev`, `Today`, `Next`).
- Classic month grid.
- Each day:
  - TV episodes (with poster, show, `SxxEyy · title`, runtime, logos, TMDB/VidSrc/Videasy icons).
  - Movies by release date (poster, title, genres, runtime, icons).
- Click:
  - Show name → Show popup (all seasons).
  - Episode → Episode popup.
  - Movie → Movie popup.

### Shows

- Sticky filters:
  - Genre row.
  - Sort (A–Z / Z–A), Status, (Watched/When hooks reserved).
- Show cards:
  - Poster
  - Name `[tmdb_id]`
  - Current season summary
  - Genres, status
  - TMDB / VidSrc / Videasy icons
- Click:
  - Poster / title → Show popup.
  - Current season line → Season episodes popup.

### Movies

- Sticky filters:
  - Genre
  - Status:
    - In Theatres / Released / In Production / Announced
  - Sort:
    - Title / Release date
- Movie cards:
  - Poster
  - Title `[tmdb_id]`
  - Genres
  - `YYYY-MM-DD • Status • Runtime`
  - Icons row (TMDB / VidSrc / Videasy)
- Click:
  - Poster / title → Movie popup.

### Live TV (v1 skeleton)

- Grid of channels (from future `live_tv_list.txt`).
- Channel logo, name, country, group.
- Reserved space for future EPG.

### Popups (Overlays)

Shared logic for all views:

- **Show popup**
  - Title `[tmdb_id]`, TMDB icon.
  - Current season summary.
  - Network logos.
  - Overview.
  - Seasons list → click → Season popup.

- **Season popup**
  - Show + season header.
  - Season overview.
  - All episodes (incl. TBA):
    - `SxxEyy · title`
    - Air date
    - Runtime (when available)
    - Icons row (TMDB / VidSrc / Videasy).
  - Click episode → Episode popup.

- **Episode popup**
  - Show + `SxxEyy` + title.
  - Air date, runtime.
  - Overview.
  - Icons row.

- **Movie popup**
  - Title `[tmdb_id]`.
  - Release date, status, runtime.
  - Overview.
  - Icons row.
  - Related collection name (if any).

All popups have a large, high-contrast `✕` close button.

---

## Maintenance Shortcuts

For quick access (also shown on Config page):

- Hub: <https://ajpnkw.github.io/my_TV_Movie/web/index.html>
- Config: <https://ajpnkw.github.io/my_TV_Movie/web/config.html>
- Workflow: <https://github.com/AJPnKW/my_TV_Movie/actions/workflows/build-data.yml>
- Secrets: <https://github.com/AJPnKW/my_TV_Movie/settings/secrets/actions>
- Repo: <https://github.com/AJPnKW/my_TV_Movie>

---

## Troubleshooting

1. **Movies tab empty**
   - Check `movies_list.txt` for proper format & numeric IDs.
   - Check Actions → `Build TV Data and Deploy` logs:
     - If it says `movies_list.txt has entries but 0 movies were built`:
       - IDs wrong, TMDB unreachable, or rate-limited.

2. **Calendar shows old data**
   - Confirm newest run of `Build TV Data and Deploy` is green.
   - Open `/data/data.json` and check `"generated_at"` + `"meta"` counters.
   - Hard refresh on TV (or clear cache).

3. **Shows present but no episodes**
   - Check `season_spec` in `tv_list.txt`.
   - Check TMDB data (show actually has those seasons/episodes).

Everything critical is designed to:
- Fail hard in CI if data is clearly wrong.
- Show clear hints in UI if `data.json` is missing or empty.

---
