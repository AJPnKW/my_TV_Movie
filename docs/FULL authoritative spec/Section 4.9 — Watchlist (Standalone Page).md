# ⭐ **Section 4.9 — Watchlist (Standalone Page).md**  
*(Full file contents — ready to save)*
```markdown
# =========================================================================================
# Section 4.9 — Watchlist (Standalone Page)
# [PROJECT] my_TV_Movie (My TV Hub)
# [ROLE] Standalone Watchlist Page (non‑SPA)
# [VERSION] v4.5.0
# [UPDATED] 2025‑12‑19_00‑00‑00
# [OWNER] Andrew & Brant (internal)
# =========================================================================================
## 4.9.1 — Purpose & Scope
The Watchlist Page (`web/watchlist.html`) is a **standalone, non‑SPA view** that renders a
multi‑show watchlist using the **v3.3.5 Show Details UI** as its visual foundation.
This page:
- Loads data from `data/data.json`
- Filters to shows where `is_watchlisted === true`
- Renders each show as a collapsed card
- Expands into a full hero‑header view with seasons, episodes, and streaming links
- Implements sorting + filtering client‑side
- Uses **local assets only** (no TMDB URLs)
- Is **not** part of the SPA shell (`index.html`)
This page **replaces the deprecated `show.html`** from v3.3.5.
The SPA “Shows View” (Section 4.2) remains active and is not affected.
---
## 4.9.2 — Phase 4.x Master Override Context
- This file is intentionally **outside** the SPA shell.
- `index.html` remains the **only SPA entry point**.
- No SPA routing, no popups, no overlays, no router hooks.
- Deterministic rendering using `data/data.json`.
- Canonical asset hierarchy ONLY (`assets/...`).
- No references to deprecated `image/` folder.
- No external image URLs (TMDB or otherwise).
- No dynamic imports, no module bundlers.
---
## 4.9.3 — High‑Level Behavior
1. Load `data/data.json` (no caching assumptions).
2. Filter to shows with `is_watchlisted: true`.
3. Render each show as a **collapsed card**.
4. Expand/collapse behavior:
   - Show → Season → Episode (three‑level accordion)
   - Expanded show displays a **full hero header** with local backdrop
   - Hero header is **sticky** on scroll (v3.3.5 behavior)
5. Sorting options:
   - A → Z (title)
   - Z → A (title)
   - Last season air date (asc/desc)
   - Last episode air date (asc/desc)
6. Filtering options:
   - ALL, ACTIVE, HIATUS, UPCOMING, ENDED
7. All images must be **local assets**.
8. All streaming links must use **local icons** + external URLs.
9. No SPA popups, overlays, or router interactions.
---
## 4.9.4 — Data Model Requirements
### Show Object (required fields)
```
id: number|string
title OR name: string
is_watchlisted: boolean
status: "ACTIVE" | "HIATUS" | "UPCOMING" | "ENDED"
poster_path_local: string
backdrop_path_local: string
network_logo_local: string
first_air_date: string (YYYY‑MM‑DD)
last_episode_air_date: string (YYYY‑MM‑DD)
last_season_air_date: string (YYYY‑MM‑DD)
overview: string
genres: string[]
seasons: Season[]
episodes: Episode[]
streaming_links: StreamingLink[]
```
### Season Object
```
season_number: number (>0)
name: string
overview: string
air_date: string
last_air_date: string
episode_count: number
```
### Episode Object
```
season_number: number
episode_number: number
name: string
overview: string
air_date: string
runtime?: number
vote_average?: number
streaming_links?: StreamingLink[]
```
### StreamingLink Object
```
service: string
type: string
url: string
icon_local: string
```
---
## 4.9.5 — Rendering Rules
### Collapsed Show Card
Must include:
- Poster thumbnail (local)
- Title
- Network logo (local)
- Status badge
- Compact metadata:
  - Last episode air date
  - Last season air date
  - Start year
  - Season count
- Expand button (▾)
- Entire header is clickable
Classes:
```
.show-card.collapsed
.show-card.expanded
```
---
### Expanded Show View
#### 1. Hero Header (sticky)
- Full‑width backdrop (local)
- Dark gradient overlay
- Poster (local)
- Title
- Status badge
- Network logo
- Meta pills:
  - Run years
  - Season count
  - Episode count
- Sticky behavior identical to v3.3.5
#### 2. Overview
- Show overview text
- Genre chips
- Country chip
- Network chip
#### 3. Streaming Links (show‑level)
- Buttons with:
  - icon_local
  - service name
  - type label
- External URLs open in new tab
#### 4. Seasons Panel
- Accordion list of seasons
- Season card includes:
  - S# + name
  - First air date
  - Episode count
  - Overview
  - Inline metadata
- Clicking a season:
  - Expands season card
  - Populates episodes panel
#### 5. Episodes Panel
- Initially empty
- Populated when a season is expanded
- Episode card includes:
  - S#E# + name
  - Air date
  - Runtime
  - Rating
  - Overview
  - Episode‑level streaming links
---
## 4.9.6 — Interaction Rules
- Clicking collapsed show → expands
- Clicking expanded show → collapses
- Clicking season header → toggles season
- Clicking season header → populates episodes panel
- Clicking episode header → toggles episode
- Sorting triggers full re-render
- Filtering triggers full re-render
- No animations beyond CSS transitions
- No SPA navigation
- No popups, overlays, modals, or router hooks
---
## 4.9.7 — Asset Requirements
### Required asset paths
```
assets/posters/shows/<slug>.jpg
assets/backdrops/shows/<slug>.jpg
assets/networks/<network>.png
assets/streaming/<service>.png
```
### Fallbacks
```
assets/posters/placeholder_poster.jpg
assets/backdrops/shows/placeholder_backdrop.jpg
```
### Forbidden
- TMDB URLs
- External image URLs
- Deprecated `image/` folder
---
## 4.9.8 — File Structure Requirements
### watchlist.html MUST contain:
1. Full HTML document:
   - `<!DOCTYPE html>`
   - `<html>`, `<head>`, `<body>`
2. Inline CSS block:
   - v3.3.5 visual parity
   - hero header
   - sticky behavior
   - accordions
   - gradients
   - shadows
3. Inline JS block:
   - load data.json
   - filter watchlisted shows
   - sorting + filtering
   - expand/collapse logic
   - season → episode population
   - streaming link rendering
4. No external JS frameworks  
5. No SPA router  
6. No popups or overlays  
---
## 4.9.9 — Validation Rules
ChatGPT MUST:
- Never invent fields not in this SPEC.
- Never reference TMDB URLs.
- Never reference deprecated folders.
- Always use canonical asset paths.
- Always implement expand/collapse exactly as defined.
- Always implement sticky hero header.
- Always filter by `is_watchlisted`.
- Always include sorting + filtering UI.
- Always match v3.3.5 visual style.
---
## 4.9.10 — Notes
- This page intentionally preserves the v3.3.5 Show Details UI.
- This page is the **only** active standalone page.
- The SPA “Shows View” (Section 4.2) remains active and separate.
- The deprecated `show.html` is fully replaced by this page.
# =========================================================================================
```
---
# ⭐ Your Section 4.9 SPEC file is now complete  
This is fully aligned with:
- your SPEC architecture  
- Phase‑4.x rules  
- the rebuilt watchlist.html  
- your asset hierarchy  
- your data model  
- your UI conventions  
