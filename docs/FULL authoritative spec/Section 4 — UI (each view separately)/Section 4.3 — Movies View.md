# **SECTION 4.3 — MOVIES VIEW**  
**Authoritative Specification — Full Scope (Including Future‑Phase Features)**  
**Document ID:** Section 4.3 — Movies View  
**Version:** V0.00  

---

# **4.3.1 Purpose of This View**
The Movies View provides a **complete, filterable, sortable, DPAD‑navigable catalog of all movies** defined in `data.json`.  
It must support:

- browsing all movies  
- filtering by genre, release year, runtime, and other attributes  
- sorting by multiple deterministic criteria  
- displaying movie cards with full metadata  
- routing to the Movie Popup (P4)  
- displaying collection metadata  
- displaying service logos and icon strips  
- supporting future‑phase profile relevance and watch progress  
- supporting future‑phase universal sort framework  
- supporting future‑phase watchlist and watched filters  

This view is mandatory and must always be present.

---

# **4.3.2 Structural Layout Requirements**
The Movies View must follow a **strict, immutable layout**:

### **4.3.2.1 Root Structure**
The view consists of:

- global sticky header  
- filter bar  
- sort bar  
- card grid  
- scrollable content container  

### **4.3.2.2 Filter Bar**
The filter bar must include:

- **Genre Filter** (multi‑select)  
- **Release Year Filter**  
- **Runtime Filter** (short, medium, long)  
- **Collection Filter**  
- **Profile Relevance Filter** (future‑phase)  
- **Watchlist Filter** (future‑phase)  
- **Watched/Unwatched Filter** (future‑phase)  

Filters must be:

- horizontally aligned  
- DPAD‑navigable  
- keyboard‑navigable  
- touch‑friendly  

### **4.3.2.3 Sort Bar**
The sort bar must include:

- Alphabetical (A→Z, Z→A)  
- Popularity  
- Vote Average  
- Release Date  
- Runtime  
- Profile Relevance (future‑phase)  
- Universal Sort Framework (future‑phase)  

Sorting must be deterministic.

### **4.3.2.4 Card Grid**
The card grid must:

- be responsive  
- maintain consistent poster aspect ratio  
- support DPAD navigation  
- support keyboard navigation  
- support mouse/touch interaction  
- maintain consistent spacing and alignment  

---

# **4.3.3 Movie Card Requirements**
Each movie must be represented by a **Movie Card**, which includes:

### **4.3.3.1 Required Visual Elements**
- poster (local path)  
- movie title  
- release year  
- runtime  
- collection badge (if applicable)  
- service logo  
- icon strip  
- genre chips  

### **4.3.3.2 Required Metadata Elements**
- release_date  
- runtime  
- popularity  
- vote_average  
- vote_count  
- keywords  

### **4.3.3.3 Future‑Phase Metadata**
- profile_relevance  
- watch_progress  
- watchlist indicator  

### **4.3.3.4 Interaction Behavior**
- clicking/tapping/DPAD‑selecting a card opens the **Movie Popup (P4)**  
- card must be fully focusable  
- card must show focus outline when selected  

---

# **4.3.4 Data Requirements**
The Movies View must consume data exclusively from `data.json`.

### **4.3.4.1 Required Data Fields**
Each movie must include:

- id  
- title  
- original_title  
- overview  
- genres[]  
- runtime  
- release_date  
- poster (local path)  
- backdrop (local path)  
- collection (collection_ref or null)  
- streaming_links[]  
- icon_strip[]  
- popularity  
- vote_average  
- vote_count  
- keywords[]  
- profile_relevance (future‑phase)  
- watch_progress (future‑phase)  

### **4.3.4.2 Collection Data Requirements**
If a movie belongs to a collection:

- collection name  
- collection poster  
- collection backdrop  
- collection id  
- collection movies[]  

### **4.3.4.3 Filtering Data Requirements**
Filters must use:

- genres[]  
- release_date  
- runtime  
- collection  
- profile_relevance (future‑phase)  
- watch_progress (future‑phase)  
- watchlist (future‑phase)  

---

# **4.3.5 Interaction Requirements**
### **4.3.5.1 DPAD Navigation**
DPAD navigation must follow:

- left/right → adjacent cards  
- up/down → previous/next row  
- OK/Enter → open Movie Popup  
- Back → return to previous focus zone  

Focus must always remain within the view.

### **4.3.5.2 Mouse/Touch Interaction**
- click/tap card → open Movie Popup  
- click/tap filter → toggle filter  
- click/tap sort → apply sort  

### **4.3.5.3 Keyboard Interaction**
- arrow keys mirror DPAD  
- Enter opens popup  
- Escape closes popup  

---

# **4.3.6 Popup Routing Requirements**
Every movie card must route to:

- **Movie Popup (P4)**  
  - which routes to Collection Popup (future‑phase)  
  - which routes to Person Popup (future‑phase)  

Routing must be deterministic and must never fail.

---

# **4.3.7 Icon Strip Requirements**
Every movie card must display the unified icon strip:

- TMDB  
- VidSrc  
- Videasy  
- future streaming services  

Icons must be:

- horizontally aligned  
- size‑consistent  
- always visible  
- clickable/tappable  

---

# **4.3.8 Logo Requirements**
Each movie card must display:

- service logo (local path)  

Logos must be:

- size‑normalized  
- aligned to the right of the card header  

---

# **4.3.9 Visual Design Requirements**
### **4.3.9.1 Poster Sizing**
Movie posters must use a **standard portrait aspect ratio**.

### **4.3.9.2 Spacing**
- consistent vertical spacing  
- consistent horizontal spacing  
- no layout shifts  

### **4.3.9.3 Colors & Contrast**
- high contrast  
- neurodivergent‑friendly palette  
- no flashing or animated elements  

### **4.3.9.4 Collection Badges**
Collection badges must be:

- visually distinct  
- consistently positioned  
- readable at TV distance  

---

# **4.3.10 Filtering Requirements**
Filters must:

- be multi‑select where applicable  
- update results instantly  
- never hide the filter bar  
- never break DPAD navigation  
- always show at least one filter option  

### **4.3.10.1 Genre Filter**
Must include all genres present in `data.json`.

### **4.3.10.2 Release Year Filter**
Must include:

- all years present in movie data  
- decade groupings (future‑phase)  

### **4.3.10.3 Runtime Filter**
Must include:

- Short (0–60 min)  
- Medium (61–120 min)  
- Long (121+ min)  

### **4.3.10.4 Collection Filter**
Must include all collections present in `data.json`.

### **4.3.10.5 Profile Relevance Filter (Future‑Phase)**
Must filter movies based on:

- profile preferences  
- watch history  
- relevance score  

### **4.3.10.6 Watchlist Filter (Future‑Phase)**
Must show only movies in the user’s watchlist.

### **4.3.10.7 Watched/Unwatched Filter (Future‑Phase)**
Must filter based on:

- watch_progress  
- completion percentage  

---

# **4.3.11 Sorting Requirements**
Sorting must be deterministic and must include:

- Alphabetical (A→Z, Z→A)  
- Popularity  
- Vote Average  
- Release Date  
- Runtime  
- Profile Relevance (future‑phase)  
- Universal Sort Framework (future‑phase)  

Sorting must never produce inconsistent ordering.

---

# **4.3.12 Error Handling Requirements**
### **4.3.12.1 Missing Data**
If a movie is missing required fields:

- show fallback poster  
- show fallback title  
- show error icon  
- log error to `errors[]`  

### **4.3.12.2 Missing Images**
Missing images must use fallback assets.

### **4.3.12.3 Invalid Metadata**
Invalid metadata must:

- not break rendering  
- be logged  
- be visually handled gracefully  

---

# **4.3.13 Future‑Phase Requirements**
The Movies View must support:

### **4.3.13.1 Profile Relevance**
Cards must visually weight:

- relevance score  
- watch history  
- profile preferences  

### **4.3.13.2 Watch Progress Indicators**
Movies must display:

- progress bar  
- resume marker  

### **4.3.13.3 Watchlist Integration**
Movies must display:

- watchlist badge  
- add/remove watchlist action  

### **4.3.13.4 Universal Sort Framework**
Sorting must integrate with:

- Explore View  
- Profiles View  
- Watchlist View  

### **4.3.13.5 Cross‑Service Sync**
Movies must reflect:

- Trakt watch history  
- TMDB updates  
- future streaming services  

---

# **4.3.14 Invariants**
The following must never change:

- filter bar structure  
- sort bar structure  
- card grid layout  
- poster aspect ratio  
- icon strip  
- logo placement  
- DPAD navigation model  
- popup routing  
- deterministic sorting  
- local image usage  
- no dynamic schema  
- no missing fields  
- no missing UI elements  

These invariants are permanent.

---

# **4.3.15 End of Section 4.3 — Movies View**
