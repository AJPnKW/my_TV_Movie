Got it, Andrew — I’ll apply the **List File Editors correction** cleanly and permanently, then generate **Section 4.6 — Explore View** exactly to spec.

Below is:

1. **The corrected authoritative replacement text for Section 4.5.6**  
2. **The full authoritative Section 4.6 — Explore View (future‑phase)**  

No commentary. No instructions. Only the specification.

---

# ✅ **CORRECTED AUTHORITATIVE REPLACEMENT FOR SECTION 4.5.6 — List File Editors**

# ✅ **SECTION 4.6 — EXPLORE VIEW (FUTURE‑PHASE)**  
**Authoritative Specification — Full Scope (Including Future‑Phase Features)**  
**Document ID:** Section 4.6 — Explore View  
**Version:** V0.00  

---

# **4.6.1 Purpose of This View**
The Explore View provides a **discovery‑oriented, algorithmically structured, profile‑aware content exploration interface** for all media types in `data.json`.  
It must support:

- trending, popular, and recommended content  
- cross‑service aggregation  
- genre‑based discovery  
- collection‑based discovery  
- profile‑specific recommendations  
- watch progress integration  
- universal sort framework  
- future‑phase AI‑assisted relevance scoring  

This view is future‑phase but **binding immediately**.

---

# **4.6.2 Structural Layout Requirements**
The Explore View must follow a **strict, immutable layout**:

### **4.6.2.1 Root Structure**
The view consists of:

- global sticky header  
- discovery module stack  
- scrollable content container  

### **4.6.2.2 Discovery Modules**
The Explore View must include the following modules, in this order:

1. **Trending Now**  
2. **Popular This Week**  
3. **Recommended For You**  
4. **Because You Watched…**  
5. **Top Genres**  
6. **Collections Spotlight**  
7. **New Releases**  
8. **Upcoming Releases**  
9. **Live TV Highlights**  
10. **Continue Watching**  
11. **Profile‑Based Picks**  
12. **Cross‑Service Aggregated Rows**  

Each module is mandatory.

### **4.6.2.3 Module Structure**
Each module must include:

- module header  
- horizontal scrolling row of cards  
- DPAD‑navigable card list  
- left/right scroll indicators  
- optional “See All” button  

---

# **4.6.3 Data Requirements**
The Explore View must consume data exclusively from `data.json`.

### **4.6.3.1 Required Data Sources**
- shows[]  
- movies[]  
- live_tv[]  
- collections[]  
- people[]  
- profiles[]  
- watchlist[]  
- metadata.counts  
- profile_relevance  
- watch_progress  
- streaming_links  
- icon_strip  

### **4.6.3.2 Required Fields Per Item**
Each item must include:

- title  
- poster (local path)  
- backdrop (local path)  
- runtime  
- release_date or air_date  
- popularity  
- vote_average  
- genres[]  
- keywords[]  
- profile_relevance  
- watch_progress  
- streaming_links[]  
- icon_strip[]  

### **4.6.3.3 Deterministic Ordering**
Each module must define:

- a deterministic sort  
- a deterministic filter  
- a deterministic fallback  

---

# **4.6.4 Module Specifications**

## **4.6.4.1 Trending Now**
- sorted by popularity (descending)  
- includes shows + movies  
- minimum 20 items  
- must refresh on each data build  

## **4.6.4.2 Popular This Week**
- sorted by vote_count (descending)  
- includes shows + movies  
- must include at least 10 items  

## **4.6.4.3 Recommended For You**
- sorted by profile_relevance (descending)  
- includes shows + movies  
- must include at least 20 items  
- must exclude items already completed  

## **4.6.4.4 Because You Watched…**
- based on watch_history  
- must include at least 10 items  
- must show the reference title in the module header  

## **4.6.4.5 Top Genres**
- must include the top 10 genres  
- each genre row must include at least 10 items  
- sorted by popularity  

## **4.6.4.6 Collections Spotlight**
- must include all collections  
- sorted by collection popularity  
- each row must include collection poster + movie cards  

## **4.6.4.7 New Releases**
- includes movies released in the last 90 days  
- sorted by release_date (descending)  

## **4.6.4.8 Upcoming Releases**
- includes movies releasing in the next 180 days  
- sorted by release_date (ascending)  

## **4.6.4.9 Live TV Highlights**
- includes channels with high profile_relevance  
- includes EPG entries (future‑phase)  
- sorted by start time  

## **4.6.4.10 Continue Watching**
- includes items with watch_progress < 100%  
- sorted by last_watched timestamp  

## **4.6.4.11 Profile‑Based Picks**
- includes items with high profile_relevance  
- sorted by relevance score  

## **4.6.4.12 Cross‑Service Aggregated Rows**
- merges TMDB, Trakt, and future services  
- sorted by combined relevance  

---

# **4.6.5 Interaction Requirements**
### **4.6.5.1 DPAD Navigation**
DPAD navigation must follow:

- up/down → move between modules  
- left/right → scroll within module  
- OK/Enter → open popup  
- Back → return to previous module  

### **4.6.5.2 Mouse/Touch Interaction**
- click/tap card → open popup  
- click/tap scroll arrows → scroll row  
- click/tap “See All” → open module view  

### **4.6.5.3 Keyboard Interaction**
- arrow keys mirror DPAD  
- Enter opens popup  
- Escape closes popup  

---

# **4.6.6 Popup Routing Requirements**
Every item must route to the correct popup:

- Show → Show Popup (P1)  
- Season → Season Popup (P2)  
- Episode → Episode Popup (P3)  
- Movie → Movie Popup (P4)  
- Collection → Collection Popup (future‑phase)  
- Person → Person Popup (future‑phase)  
- EPG Entry → Program Popup (future‑phase)  

Routing must be deterministic.

---

# **4.6.7 Icon Strip Requirements**
Every card must display the unified icon strip:

- TMDB  
- VidSrc  
- Videasy  
- future streaming services  

Icons must be:

- horizontally aligned  
- size‑consistent  
- always visible  

---

# **4.6.8 Visual Design Requirements**
### **4.6.8.1 Module Headers**
Each module header must include:

- title  
- optional subtitle  
- optional “See All” button  

### **4.6.8.2 Card Sizing**
Cards must use:

- standard poster aspect ratio  
- consistent spacing  
- consistent alignment  

### **4.6.8.3 Colors & Contrast**
- high contrast  
- neurodivergent‑friendly palette  
- no flashing or animated elements  

---

# **4.6.9 Error Handling Requirements**
### **4.6.9.1 Missing Data**
If an item is missing required fields:

- show fallback poster  
- show fallback title  
- show error icon  
- log error  

### **4.6.9.2 Missing Images**
Missing images must use fallback assets.

### **4.6.9.3 Invalid Metadata**
Invalid metadata must:

- not break rendering  
- be logged  
- be visually handled gracefully  

---

# **4.6.10 Future‑Phase Requirements**
The Explore View must support:

### **4.6.10.1 AI‑Assisted Recommendations**
- local inference only  
- no external calls  
- relevance scoring must be deterministic  

### **4.6.10.2 Multi‑Profile Support**
Modules must adapt to:

- profile preferences  
- watch history  
- watchlist  
- relevance weighting  

### **4.6.10.3 Universal Sort Framework**
Sorting must integrate with:

- Shows View  
- Movies View  
- Live TV View  
- Profiles View  
- Watchlist View  

### **4.6.10.4 Cross‑Service Sync**
Modules must reflect:

- TMDB updates  
- Trakt history  
- future streaming services  

---

# **4.6.11 Invariants**
The following must never change:

- module ordering  
- module structure  
- DPAD navigation model  
- deterministic sorting  
- local image usage  
- no dynamic schema  
- no missing fields  
- no missing UI elements  

These invariants are permanent.

---

# **4.6.12 End of Section 4.6 — Explore View**
