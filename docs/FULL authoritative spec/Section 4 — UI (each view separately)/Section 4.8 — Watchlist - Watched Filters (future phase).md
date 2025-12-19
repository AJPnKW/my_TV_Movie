# **SECTION 4.8 — WATCHLIST / WATCHED FILTERS (FUTURE‑PHASE)**  
**Authoritative Specification — Full Scope (Including Future‑Phase Features)**  
**Document ID:** Section 4.8 — Watchlist / Watched Filters  
**Version:** V0.00  

---

# **4.8.1 Purpose of This View**
The Watchlist / Watched Filters View provides a **centralized, profile‑aware, deterministic interface** for managing and browsing:

- the user’s global watchlist  
- the user’s profile‑specific watchlist  
- watched/unwatched filtering  
- progress‑based filtering  
- resume‑watching functionality  
- cross‑service watch history integration  
- future‑phase recommendation weighting  

This view is future‑phase but **binding immediately**.

---

# **4.8.2 Structural Layout Requirements**
The Watchlist / Watched Filters View must follow a **strict, immutable layout**:

### **4.8.2.1 Root Structure**
The view consists of:

- global sticky header  
- filter bar  
- sort bar  
- card grid  
- scrollable content container  

### **4.8.2.2 Filter Bar**
The filter bar must include:

- **Watchlist Filter**  
- **Watched Filter**  
- **Unwatched Filter**  
- **In‑Progress Filter**  
- **Completed Filter**  
- **Profile Filter** (future‑phase)  
- **Service Filter** (future‑phase)  
- **Relevance Filter** (future‑phase)  

Filters must be:

- horizontally aligned  
- DPAD‑navigable  
- keyboard‑navigable  
- touch‑friendly  

### **4.8.2.3 Sort Bar**
The sort bar must include:

- Alphabetical (A→Z, Z→A)  
- Recently Added  
- Recently Watched  
- Progress (ascending/descending)  
- Profile Relevance (future‑phase)  
- Universal Sort Framework (future‑phase)  

Sorting must be deterministic.

### **4.8.2.4 Card Grid**
The card grid must:

- be responsive  
- support mixed media types (shows + movies)  
- maintain consistent poster aspect ratio  
- support DPAD navigation  
- support keyboard navigation  
- support mouse/touch interaction  
- maintain consistent spacing and alignment  

---

# **4.8.3 Card Requirements**
Each item in the Watchlist View must be represented by a **Watchlist Card**, which includes:

### **4.8.3.1 Required Visual Elements**
- poster (local path)  
- title  
- media type badge (Show / Movie)  
- progress bar  
- resume marker  
- service logo  
- icon strip  
- watchlist badge  

### **4.8.3.2 Required Metadata Elements**
- id  
- title  
- runtime  
- release_date or air_date  
- streaming_links[]  
- icon_strip[]  
- profile_relevance  
- watch_progress  
- watchlist membership  

### **4.8.3.3 Interaction Behavior**
- clicking/tapping/DPAD‑selecting a card opens the correct popup  
- long‑press or options button opens watchlist actions  
- card must be fully focusable  
- card must show focus outline when selected  

---

# **4.8.4 Data Requirements**
The Watchlist / Watched Filters View must consume data exclusively from `data.json`.

### **4.8.4.1 Required Data Sources**
- profiles[*].watchlist[]  
- profiles[*].watch_progress{}  
- global watchlist.items[]  
- shows[]  
- movies[]  
- streaming_links[]  
- icon_strip[]  
- profile_relevance  

### **4.8.4.2 Watch Progress Requirements**
Each item must include:

- progress percentage  
- last watched timestamp  
- completion status  
- resume position  

### **4.8.4.3 Watchlist Requirements**
Each item must include:

- global watchlist membership  
- profile watchlist membership  
- watchlist ordering  

---

# **4.8.5 Interaction Requirements**
### **4.8.5.1 DPAD Navigation**
DPAD navigation must follow:

- left/right → adjacent cards  
- up/down → previous/next row  
- OK/Enter → open popup  
- Back → return to previous focus zone  

Focus must always remain within the view.

### **4.8.5.2 Mouse/Touch Interaction**
- click/tap card → open popup  
- click/tap filter → toggle filter  
- click/tap sort → apply sort  
- click/tap watchlist badge → toggle watchlist  

### **4.8.5.3 Keyboard Interaction**
- arrow keys mirror DPAD  
- Enter opens popup  
- Escape closes popup  

---

# **4.8.6 Popup Routing Requirements**
Every card must route to the correct popup:

- Show → Show Popup (P1)  
- Season → Season Popup (P2)  
- Episode → Episode Popup (P3)  
- Movie → Movie Popup (P4)  
- Collection → Collection Popup (future‑phase)  
- Person → Person Popup (future‑phase)  

Routing must be deterministic and must never fail.

---

# **4.8.7 Filtering Requirements**
Filters must:

- be multi‑select where applicable  
- update results instantly  
- never hide the filter bar  
- never break DPAD navigation  
- always show at least one filter option  

### **4.8.7.1 Watchlist Filter**
Shows only items in:

- global watchlist  
- profile watchlist  

### **4.8.7.2 Watched Filter**
Shows only items with:

- watch_progress == 100%  

### **4.8.7.3 Unwatched Filter**
Shows only items with:

- watch_progress == 0%  

### **4.8.7.4 In‑Progress Filter**
Shows only items with:

- 0% < watch_progress < 100%  

### **4.8.7.5 Completed Filter**
Shows only items with:

- watch_progress == 100%  
- AND last_watched timestamp exists  

### **4.8.7.6 Profile Filter (Future‑Phase)**
Filters items based on:

- active profile  
- profile preferences  
- profile watch history  

### **4.8.7.7 Service Filter (Future‑Phase)**
Filters items based on:

- streaming_links.service  

### **4.8.7.8 Relevance Filter (Future‑Phase)**
Filters items based on:

- profile_relevance score  

---

# **4.8.8 Sorting Requirements**
Sorting must be deterministic and must include:

- Alphabetical (A→Z, Z→A)  
- Recently Added  
- Recently Watched  
- Progress (ascending/descending)  
- Profile Relevance (future‑phase)  
- Universal Sort Framework (future‑phase)  

Sorting must never produce inconsistent ordering.

---

# **4.8.9 Watchlist Management Requirements**
### **4.8.9.1 Add/Remove Behavior**
Users must be able to:

- add items to watchlist  
- remove items from watchlist  
- reorder watchlist (future‑phase)  

### **4.8.9.2 Watchlist Indicators**
Cards must display:

- watchlist badge  
- add/remove icon  

### **4.8.9.3 Watchlist Persistence**
Changes must update:

- profile watchlist  
- global watchlist  
- metadata  

---

# **4.8.10 Watch Progress Requirements**
### **4.8.10.1 Progress Bar**
Each card must display:

- progress bar  
- resume marker  

### **4.8.10.2 Resume Behavior**
Selecting a partially watched item must:

- open the popup  
- highlight resume option  

### **4.8.10.3 Completion Behavior**
Completed items must:

- show completion badge  
- move to “Completed” filter  

---

# **4.8.11 Visual Design Requirements**
### **4.8.11.1 Poster Sizing**
Posters must use a **standard portrait aspect ratio**.

### **4.8.11.2 Spacing**
- consistent vertical spacing  
- consistent horizontal spacing  
- no layout shifts  

### **4.8.11.3 Colors & Contrast**
- high contrast  
- neurodivergent‑friendly palette  
- no flashing or animated elements  

---

# **4.8.12 Error Handling Requirements**
### **4.8.12.1 Missing Data**
If an item is missing required fields:

- show fallback poster  
- show fallback title  
- show error icon  
- log error  

### **4.8.12.2 Missing Images**
Missing images must use fallback assets.

### **4.8.12.3 Invalid Metadata**
Invalid metadata must:

- not break rendering  
- be logged  
- be visually handled gracefully  

---

# **4.8.13 Future‑Phase Requirements**
The Watchlist / Watched Filters View must support:

### **4.8.13.1 Multi‑Profile Watchlists**
Each profile must maintain:

- its own watchlist  
- its own ordering  
- its own metadata  

### **4.8.13.2 Cross‑Service Sync**
Watchlist and watch progress must sync with:

- TMDB  
- Trakt  
- future streaming services  

### **4.8.13.3 AI‑Assisted Recommendations**
Recommendations must:

- use local inference  
- never call external services  
- be deterministic  

### **4.8.13.4 Universal Sort Framework**
Sorting must integrate with:

- Shows View  
- Movies View  
- Live TV View  
- Explore View  
- Profiles View  

---

# **4.8.14 Invariants**
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

# **4.8.15 End of Section 4.8 — Watchlist / Watched Filters**
