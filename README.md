<!-- Version: v1.2.0 (2025-11-09) -->

# my_TV_Movie

Static TV + Movies hub built from text lists and deployed via GitHub Pages.  
Designed to be simple, fast, and friendly on TV browsers (Chromecast, Android TV, Shield, etc).

---

## Live URLs

Open these directly on your TV / browser:

- **Home:** <https://ajpnkw.github.io/my_TV_Movie/>
- **App:** <https://ajpnkw.github.io/my_TV_Movie/web/index.html>
- **Config:** <https://ajpnkw.github.io/my_TV_Movie/web/config.html>

All views (Calendar / Shows / Movies) live in `web/index.html` as a single-page app.

---

## How It Works

1. You maintain **input lists**:
   - `tv_list.txt`
   - `movies_list.txt`
2. A workflow (or local script) runs:
   - Calls `scripts/fetch_tmdb.py` (+ optional helpers)
   - Fetches show / season / episode / movie metadata
   - Writes:
     - `data/data.json`
     - `data/last_refresh.txt`
3. `web/index.html` reads `data/data.json` at runtime and renders:
   - Calendar of episodes + movie releases
   - Shows view
   - Movies view

Whenever you change `tv_list.txt` or `movies_list.txt`, you must **rebuild** so the site picks up changes.

---

## Input Formats

### TV (`tv_list.txt`)

```text
# File: tv_list.txt
# Project: my_TV_Movie
# Version: v1.0.0 (2025-11-09)
# format:
#   name | tmdb_show_id | season_spec | tvmaze_id (optional)
#
# season_spec:
#   5       = only season 5
#   1,2,5   = seasons 1, 2 and 5
#   *       = all seasons

Abbott Elementary|125935|5
Only Murders in the Building|107113|5
Stranger Things|66732|5
