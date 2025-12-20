# ⭐ **Section 7 — Assets.md**  
*(Full file contents — ready to save)*

```markdown
/* =========================================================================================
[SECTION] 7.0 — Assets
[PROJECT] my_TV_Movie (My TV Hub)
[ROLE] Canonical asset hierarchy, naming rules, and required asset sets
[VERSION] v4.5.0
[UPDATED] 2025‑12‑19_00‑00‑00
[OWNER] Andrew & Brant (internal)

[PHASE 4.x CONTEXT]
- All assets must be local.
- No external URLs (TMDB, CDN, remote images).
- No deprecated folders (e.g., /image/).
- All views (SPA and standalone) must use the canonical hierarchy defined here.
- watchlist.html (Section 4.9) introduces additional asset requirements for
  posters, backdrops, network logos, and streaming service icons.

========================================================================================= */

# Section 7 — Assets

## 7.1 — Purpose
This section defines the **canonical asset hierarchy** for My TV Hub.  
All UI views, scripts, and pipelines must reference assets **exclusively** through
the paths and naming rules defined here.

No view may introduce its own asset folders or naming conventions.

---

## 7.2 — Canonical Asset Hierarchy

```
assets/
    posters/
        shows/
            <slug>.jpg
            placeholder_poster.jpg

    backdrops/
        shows/
            <slug>.jpg
            placeholder_backdrop.jpg

    networks/
        <network>.png

    streaming/
        <service>.png

    icons/
        <global UI icons>

    ui/
        <shared UI elements>

    fonts/
        <font files>

    misc/
        <miscellaneous static assets>
```

All folders listed above are required.  
No additional folders may be created without SPEC approval.

---

## 7.3 — Naming Rules

### 7.3.1 — Show Slugs
Show assets must use a **slug** derived from the show title:

- lowercase  
- alphanumeric  
- hyphens instead of spaces  
- no special characters  

Example:
```
"The Expanse" → the-expanse.jpg
```

### 7.3.2 — Network Logos
Network logos must use the network identifier:

```
assets/networks/netflix.png
assets/networks/hbo.png
assets/networks/amazon.png
```

### 7.3.3 — Streaming Service Icons
Streaming icons must match the service name:

```
assets/streaming/netflix.png
assets/streaming/prime-video.png
assets/streaming/disney-plus.png
```

### 7.3.4 — File Format
All posters, backdrops, and icons must be **.jpg** or **.png** only.

No SVGs for posters/backdrops.  
No WebP.  
No GIFs.

---

## 7.4 — Required Asset Sets

### 7.4.1 — Posters (Shows)
Required for:
- Shows View (4.2)
- Popups (P1–P3)
- watchlist.html (4.9)

Path:
```
assets/posters/shows/<slug>.jpg
```

Fallback:
```
assets/posters/placeholder_poster.jpg
```

### 7.4.2 — Backdrops (Shows)
Required for:
- Show Popup (P1)
- watchlist.html (4.9)

Path:
```
assets/backdrops/shows/<slug>.jpg
```

Fallback:
```
assets/backdrops/shows/placeholder_backdrop.jpg
```

### 7.4.3 — Network Logos
Required for:
- Shows View (4.2)
- Popups (P1–P3)
- watchlist.html (4.9)

Path:
```
assets/networks/<network>.png
```

### 7.4.4 — Streaming Service Icons
Required for:
- watchlist.html (4.9)
- Episode‑level streaming links (future phase)

Path:
```
assets/streaming/<service>.png
```

---

## 7.5 — Forbidden Assets

### 7.5.1 — External URLs
The following are strictly forbidden:
- TMDB image URLs  
- CDN image URLs  
- Remote icons  
- Any non‑local asset references  

### 7.5.2 — Deprecated Folders
The following must not be used:
- `/image/`
- `/img/`
- `/pictures/`
- `/static/` (unless approved)

### 7.5.3 — Inline Base64 Assets
Inline base64 images are not allowed in:
- SPA views  
- popups  
- shared components  

Exception:  
`watchlist.html` may embed small inline SVGs if required for layout.

---

## 7.6 — Asset Validation Rules
All assets must satisfy:

- Correct folder  
- Correct filename  
- Correct slug  
- Correct format  
- No missing posters/backdrops for watchlisted shows  
- No broken paths  
- No unused assets in the repo  

The build pipeline (Section 9) must include an asset validation step.

---

## 7.7 — watchlist.html (Section 4.9) Asset Requirements
The standalone watchlist page requires:

```
assets/posters/shows/<slug>.jpg
assets/backdrops/shows/<slug>.jpg
assets/networks/<network>.png
assets/streaming/<service>.png
```

Fallbacks must be used when assets are missing.

watchlist.html must not reference:
- TMDB URLs  
- deprecated folders  
- external icons  

---

# End of Section 7 — Assets
