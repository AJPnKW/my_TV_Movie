# **SECTION 4.2 — SHOWS VIEW**  
**Authoritative Specification — Full Scope (Including Future‑Phase Features)**  
**Document ID:** Section 4.2 — Shows View  
**Version:** V0.00  

---

# **4.2.1 Purpose of This View**
The Shows View provides a **complete, filterable, sortable, DPAD‑navigable catalog of all TV shows** defined in `data.json`.  
It must support:

- browsing all shows  
- filtering by genre, status, and other attributes  
- sorting by multiple deterministic criteria  
- displaying show cards with full metadata  
- routing to the Show Popup (P1)  
- routing to Season Popup (P2) and Episode Popup (P3) via Show Popup  
- displaying network logos and icon strips  
- supporting future‑phase profile relevance and watch progress  
- supporting future‑phase universal sort framework  

This view is mandatory and must always be present.

---

# **4.2.2 Structural Layout Requirements**
The Shows View must follow a **strict, immutable layout**:

### **4.2.2.1 Root Structure**
The view consists of:

- global sticky header  
- filter bar  
- sort bar  
- card grid  
- scrollable content container  

### **4.2.2.2 Filter Bar**
The filter bar must include:

- **Genre Filter** (multi‑select)  
- **Status Filter** (Running, Ended, Canceled, Upcoming)  
- **Origin Country Filter**  
- **Profile Relevance Filter** (future‑phase)  
- **Watchlist Filter** (future‑phase)  
- **Watched/Unwatched Filter** (future‑phase)  

Filters must be:

- horizontally aligned  
- DPAD‑navigable  
- keyboard‑navigable  
- touch‑friendly  

### **4.2.2.3 Sort Bar**
The sort bar must include:

- Alphabetical (A→Z, Z→A)  
- Popularity  
- Vote Average  
- First Air Date  
- Last Air Date  
- Profile Relevance (future‑phase)  
- Universal Sort Framework (future‑phase)  

Sorting must be deterministic.

### **4.2.2.4 Card Grid**
The card grid must:

- be responsive  
- maintain consistent poster aspect ratio  
- support DPAD navigation  
- support keyboard navigation  
- support mouse/touch interaction  
- maintain consistent spacing and alignment  

---

# **4.2.3 Show Card Requirements**
Each show must be represented by a **Show Card**, which includes:

### **4.2.3.1 Required Visual Elements**
- poster (local path)  
- show title  
- current season indicator  
- next episode indicator (if applicable)  
- network logo  
- icon strip  
- status badge (Running, Ended, etc.)  
- origin country chip  
- genre chips  

### **4.2.3.2 Required Metadata Elements**
- first_air_date  
- last_air_date  
- runtime (if available)  
- popularity  
- vote_average  
- vote_count  

### **4.2.3.3 Future‑Phase Metadata**
- profile_relevance  
- watch_progress  
- watchlist indicator  

### **4.2.3.4 Interaction Behavior**
- clicking/tapping/DPAD‑selecting a card opens the **Show Popup (P1)**  
- card must be fully focusable  
- card must show focus outline when selected  

---

# **4.2.4 Data Requirements**
The Shows View must consume data exclusively from `data.json`.

### **4.2.4.1 Required Data Fields**
Each show must include:

- id  
- title  
- original_title  
- overview  
- status  
- genres  
- network  
- network_logo (local path)  
- poster (local path)  
- backdrop (local path)  
- first_air_date  
- last_air_date  
- seasons[]  
- streaming_links[]  
- icon_strip[]  
- popularity  
- vote_average  
- vote_count  
- runtime  
- origin_country[]  
- keywords[]  
- profile_relevance (future‑phase)  
- watch_progress (future‑phase)  
- collections[]  

### **4.2.4.2 Season Data Requirements**
The Shows View must extract:

- number of seasons  
- number of episodes  
- next episode to air  
- last episode to air  

### **4.2.4.3 Filtering Data Requirements**
Filters must use:

- genres[]  
- status  
- origin_country[]  
- profile_relevance (future‑phase)  
- watch_progress (future‑phase)  
- watchlist (future‑phase)  

---

# **4.2.5 Interaction Requirements**
### **4.2.5.1 DPAD Navigation**
DPAD navigation must follow:

- left/right → adjacent cards  
- up/down → previous/next row  
- OK/Enter → open Show Popup  
- Back → return to previous focus zone  

Focus must always remain within the view.

### **4.2.5.2 Mouse/Touch Interaction**
- click/tap card → open Show Popup  
- click/tap filter → toggle filter  
- click/tap sort → apply sort  

### **4.2.5.3 Keyboard Interaction**
- arrow keys mirror DPAD  
- Enter opens popup  
- Escape closes popup  

---

# **4.2.6 Popup Routing Requirements**
Every show card must route to:

- **Show Popup (P1)**  
  - which routes to Season Popup (P2)  
  - which routes to Episode Popup (P3)  

Routing must be deterministic and must never fail.

---

# **4.2.7 Icon Strip Requirements**
Every show card must display the unified icon strip:

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

# **4.2.8 Logo Requirements**
Each show card must display:

- network logo (local path)  

Logos must be:

- size‑normalized  
- aligned to the right of the card header  

---

# **4.2.9 Visual Design Requirements**
### **4.2.9.1 Poster Sizing**
Show posters must use a **standard portrait aspect ratio**.

### **4.2.9.2 Spacing**
- consistent vertical spacing  
- consistent horizontal spacing  
- no layout shifts  

### **4.2.9.3 Colors & Contrast**
- high contrast  
- neurodivergent‑friendly palette  
- no flashing or animated elements  

### **4.2.9.4 Status Badges**
Status badges must be:

- color‑coded  
- consistently positioned  
- readable at TV distance  

---

# **4.2.10 Filtering Requirements**
Filters must:

- be multi‑select where applicable  
- update results instantly  
- never hide the filter bar  
- never break DPAD navigation  
- always show at least one filter option  

### **4.2.10.1 Genre Filter**
Must include all genres present in `data.json`.

### **4.2.10.2 Status Filter**
Must include:

- Running  
- Ended  
- Canceled  
- Upcoming  

### **4.2.10.3 Origin Country Filter**
Must include all origin countries present in `data.json`.

### **4.2.10.4 Profile Relevance Filter (Future‑Phase)**
Must filter shows based on:

- profile preferences  
- watch history  
- relevance score  

### **4.2.10.5 Watchlist Filter (Future‑Phase)**
Must show only shows in the user’s watchlist.

### **4.2.10.6 Watched/Unwatched Filter (Future‑Phase)**
Must filter based on:

- watch_progress  
- episode completion  

---

# **4.2.11 Sorting Requirements**
Sorting must be deterministic and must include:

- Alphabetical (A→Z, Z→A)  
- Popularity  
- Vote Average  
- First Air Date  
- Last Air Date  
- Profile Relevance (future‑phase)  
- Universal Sort Framework (future‑phase)  

Sorting must never produce inconsistent ordering.

---

# **4.2.12 Error Handling Requirements**
### **4.2.12.1 Missing Data**
If a show is missing required fields:

- show fallback poster  
- show fallback title  
- show error icon  
- log error to `errors[]`  

### **4.2.12.2 Missing Images**
Missing images must use fallback assets.

### **4.2.12.3 Invalid Metadata**
Invalid metadata must:

- not break rendering  
- be logged  
- be visually handled gracefully  

---

# **4.2.13 Future‑Phase Requirements**
The Shows View must support:

### **4.2.13.1 Profile Relevance**
Cards must visually weight:

- relevance score  
- watch history  
- profile preferences  

### **4.2.13.2 Watch Progress Indicators**
Shows must display:

- progress bar  
- resume marker  

### **4.2.13.3 Watchlist Integration**
Shows must display:

- watchlist badge  
- add/remove watchlist action  

### **4.2.13.4 Universal Sort Framework**
Sorting must integrate with:

- Explore View  
- Profiles View  
- Watchlist View  

### **4.2.13.5 Cross‑Service Sync**
Shows must reflect:

- Trakt watch history  
- TMDB updates  
- future streaming services  

---

# **4.2.14 Invariants**
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

# **4.2.15 End of Section 4.2 — Shows View**
