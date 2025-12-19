# **SECTION 4.4 — LIVE TV VIEW**  
**Authoritative Specification — Full Scope (Including Future‑Phase Features)**  
**Document ID:** Section 4.4 — Live TV View  
**Version:** V0.00  

---

# **4.4.1 Purpose of This View**
The Live TV View provides a **complete, filterable, sortable, DPAD‑navigable catalog of all live TV channels** defined in `data.json`.  
It must support:

- browsing all channels  
- filtering by country, group, and other attributes  
- sorting by multiple deterministic criteria  
- displaying channel cards with full metadata  
- routing to future‑phase EPG program popups  
- displaying channel logos  
- supporting future‑phase full EPG integration  
- supporting future‑phase profile relevance  
- supporting future‑phase watchlist and watched filters  
- supporting future‑phase universal sort framework  

This view is mandatory and must always be present.

---

# **4.4.2 Structural Layout Requirements**
The Live TV View must follow a **strict, immutable layout**:

### **4.4.2.1 Root Structure**
The view consists of:

- global sticky header  
- filter bar  
- sort bar  
- channel card grid  
- scrollable content container  

### **4.4.2.2 Filter Bar**
The filter bar must include:

- **Country Filter**  
- **Group Filter**  
- **Profile Relevance Filter** (future‑phase)  
- **Watchlist Filter** (future‑phase)  
- **Watched/Unwatched Filter** (future‑phase)  

Filters must be:

- horizontally aligned  
- DPAD‑navigable  
- keyboard‑navigable  
- touch‑friendly  

### **4.4.2.3 Sort Bar**
The sort bar must include:

- Alphabetical (A→Z, Z→A)  
- Country  
- Group  
- Profile Relevance (future‑phase)  
- Universal Sort Framework (future‑phase)  

Sorting must be deterministic.

### **4.4.2.4 Channel Card Grid**
The card grid must:

- be responsive  
- maintain consistent logo sizing  
- support DPAD navigation  
- support keyboard navigation  
- support mouse/touch interaction  
- maintain consistent spacing and alignment  

---

# **4.4.3 Channel Card Requirements**
Each channel must be represented by a **Channel Card**, which includes:

### **4.4.3.1 Required Visual Elements**
- channel logo (local path)  
- channel name  
- country chip  
- group chip  
- timezone indicator  
- live indicator (optional)  

### **4.4.3.2 Required Metadata Elements**
- id  
- name  
- country  
- group  
- timezone  
- stream_url  

### **4.4.3.3 Future‑Phase Metadata**
- EPG preview (next program)  
- profile_relevance  
- watch_progress  
- watchlist indicator  

### **4.4.3.4 Interaction Behavior**
- clicking/tapping/DPAD‑selecting a card opens the **EPG Program Popup** (future‑phase)  
- card must be fully focusable  
- card must show focus outline when selected  

---

# **4.4.4 Data Requirements**
The Live TV View must consume data exclusively from `data.json`.

### **4.4.4.1 Required Data Fields**
Each channel must include:

- id  
- name  
- country  
- group  
- logo (local path)  
- stream_url  
- timezone  
- epg[] (future‑phase)  
- profile_relevance (future‑phase)  

### **4.4.4.2 EPG Data Requirements (Future‑Phase)**
Each EPG entry must include:

- start  
- end  
- title  
- description  
- season (optional)  
- episode (optional)  
- poster (local path)  

### **4.4.4.3 Filtering Data Requirements**
Filters must use:

- country  
- group  
- profile_relevance (future‑phase)  
- watch_progress (future‑phase)  
- watchlist (future‑phase)  

---

# **4.4.5 Interaction Requirements**
### **4.4.5.1 DPAD Navigation**
DPAD navigation must follow:

- left/right → adjacent cards  
- up/down → previous/next row  
- OK/Enter → open EPG Program Popup (future‑phase)  
- Back → return to previous focus zone  

Focus must always remain within the view.

### **4.4.5.2 Mouse/Touch Interaction**
- click/tap card → open EPG Program Popup  
- click/tap filter → toggle filter  
- click/tap sort → apply sort  

### **4.4.5.3 Keyboard Interaction**
- arrow keys mirror DPAD  
- Enter opens popup  
- Escape closes popup  

---

# **4.4.6 Popup Routing Requirements**
Every channel card must route to:

- **EPG Program Popup (future‑phase)**  
  - which routes to Episode Popup (P3) if program metadata includes episode info  
  - which routes to Movie Popup (P4) if program is a movie  
  - which routes to Show Popup (P1) if program is part of a show  

Routing must be deterministic and must never fail.

---

# **4.4.7 Logo Requirements**
Each channel card must display:

- channel logo (local path)  

Logos must be:

- size‑normalized  
- aligned to the top of the card  
- visually consistent across all channels  

---

# **4.4.8 Visual Design Requirements**
### **4.4.8.1 Logo Sizing**
Channel logos must use a **standardized rectangular aspect ratio**.

### **4.4.8.2 Spacing**
- consistent vertical spacing  
- consistent horizontal spacing  
- no layout shifts  

### **4.4.8.3 Colors & Contrast**
- high contrast  
- neurodivergent‑friendly palette  
- no flashing or animated elements  

### **4.4.8.4 EPG Preview (Future‑Phase)**
If EPG data exists:

- show next program title  
- show start time  
- show small poster (local path)  

---

# **4.4.9 Filtering Requirements**
Filters must:

- be multi‑select where applicable  
- update results instantly  
- never hide the filter bar  
- never break DPAD navigation  
- always show at least one filter option  

### **4.4.9.1 Country Filter**
Must include all countries present in `data.json`.

### **4.4.9.2 Group Filter**
Must include all groups present in `data.json`.

### **4.4.9.3 Profile Relevance Filter (Future‑Phase)**
Must filter channels based on:

- profile preferences  
- watch history  
- relevance score  

### **4.4.9.4 Watchlist Filter (Future‑Phase)**
Must show only channels in the user’s watchlist.

### **4.4.9.5 Watched/Unwatched Filter (Future‑Phase)**
Must filter based on:

- watch_progress  
- program completion  

---

# **4.4.10 Sorting Requirements**
Sorting must be deterministic and must include:

- Alphabetical (A→Z, Z→A)  
- Country  
- Group  
- Profile Relevance (future‑phase)  
- Universal Sort Framework (future‑phase)  

Sorting must never produce inconsistent ordering.

---

# **4.4.11 Error Handling Requirements**
### **4.4.11.1 Missing Data**
If a channel is missing required fields:

- show fallback logo  
- show fallback name  
- show error icon  
- log error to `errors[]`  

### **4.4.11.2 Missing Images**
Missing images must use fallback assets.

### **4.4.11.3 Invalid Metadata**
Invalid metadata must:

- not break rendering  
- be logged  
- be visually handled gracefully  

---

# **4.4.12 Future‑Phase Requirements**
The Live TV View must support:

### **4.4.12.1 Full EPG Integration**
Channels must display:

- program blocks  
- start/end times  
- program posters  
- program metadata  

### **4.4.12.2 Profile Relevance**
Cards must visually weight:

- relevance score  
- watch history  
- profile preferences  

### **4.4.12.3 Watch Progress Indicators**
Channels must display:

- progress bar  
- resume marker  

### **4.4.12.4 Watchlist Integration**
Channels must display:

- watchlist badge  
- add/remove watchlist action  

### **4.4.12.5 Universal Sort Framework**
Sorting must integrate with:

- Explore View  
- Profiles View  
- Watchlist View  

### **4.4.12.6 Cross‑Service Sync**
Channels must reflect:

- Trakt watch history  
- TMDB updates  
- future streaming services  

---

# **4.4.13 Invariants**
The following must never change:

- filter bar structure  
- sort bar structure  
- card grid layout  
- logo aspect ratio  
- DPAD navigation model  
- popup routing  
- deterministic sorting  
- local image usage  
- no dynamic schema  
- no missing fields  
- no missing UI elements  

These invariants are permanent.

---

# **4.4.14 End of Section 4.4 — Live TV View**
