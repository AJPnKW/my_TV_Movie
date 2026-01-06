### **Section 4.1 — Calendar View**

I will now generate the **FULL AUTHORITATIVE SPECIFICATION** for:

```
SECTION_NUMBER = 4.1
SECTION_NAME = Calendar View
```

Exactly following your rules:

- complete  
- authoritative  
- non‑contradictory  
- aligned with all global rules  
- aligned with Q1–Q5  
- aligned with the rendering pipeline  
- aligned with the popup chain  
- aligned with UX rules  
- aligned with the data model  
- aligned with workflow rules  
- aligned with versioning rules  
- aligned with file integrity rules  
- aligned with the FULL final design  
- formatted in clean Markdown  
- suitable for saving as “Section 4.1 — Calendar View_V0.00.md”  
- no commentary, no instructions, no summaries  

Here it is.

---

# **SECTION 4.1 — CALENDAR VIEW**  
**Authoritative Specification — Full Scope (Including Future‑Phase Features)**  
**Document ID:** Section 4.1 — Calendar View  
**Version:** V0.00  

---

# **4.1.1 Purpose of This View**
The Calendar View provides a **month‑based, grid‑structured visual schedule** of all upcoming and past episodes, movies, and live TV programs.  
It is a **primary navigation surface** for date‑driven discovery and must support:

- daily content visibility  
- popup routing  
- DPAD navigation  
- icon strip display  
- network/service logos  
- future‑phase EPG integration  
- future‑phase profile relevance  
- future‑phase watch progress  

This view is mandatory and must always be present.

---

# **4.1.2 Structural Layout Requirements**
The Calendar View must follow a **strict, immutable layout**:

### **4.1.2.1 Grid Structure**
- 7 columns (Monday → Sunday)  
- 5–6 rows depending on month  
- Each cell represents a single calendar day  
- Each cell must support multiple content items  

### **4.1.2.2 Sticky Month Header**
A persistent header must display:

- month name  
- year  
- left/right month navigation arrows  
- today indicator  

The header must remain visible during scrolling.

### **4.1.2.3 Day Cell Structure**
Each day cell must include:

- date number (top‑left)  
- list of content items (episodes, movies, EPG entries)  
- overflow indicator if >3 items  
- DPAD focus zone  
- click/tap zone  

### **4.1.2.4 Content Item Structure**
Each content item must include:

- poster (calendar size)  
- title  
- episode number (if applicable)  
- runtime  
- network logo  
- icon strip  
- streaming availability indicator  
- TBA indicator (if applicable)  

---

# **4.1.3 Data Requirements**
The Calendar View must consume data exclusively from `data.json`.

### **4.1.3.1 Required Data Sources**
- `shows[*].seasons[*].episodes[*]`  
- `movies[*]`  
- `live_tv[*].epg[*]` (future‑phase)  
- `profiles[*].watch_progress` (future‑phase)  
- `watchlist.items` (future‑phase)  

### **4.1.3.2 Required Fields Per Item**
Each calendar item must include:

- title  
- poster (local path)  
- backdrop (optional)  
- runtime  
- air_date or release_date  
- network_logo (if applicable)  
- streaming_links  
- icon_strip  
- tba flag (episodes only)  
- profile_relevance (future‑phase)  
- watch_progress (future‑phase)  

### **4.1.3.3 Sorting Rules**
Within each day:

1. Episodes sorted by air time  
2. Movies sorted by release time  
3. EPG entries sorted by start time  
4. TBA episodes appear last  

Sorting must be deterministic.

---

# **4.1.4 Interaction Requirements**
### **4.1.4.1 DPAD Navigation**
DPAD navigation must follow:

- left/right → adjacent days  
- up/down → same weekday in previous/next week  
- OK/Enter → open popup  
- Back → close popup or return to previous month  

Focus must always remain within the grid.

### **4.1.4.2 Mouse/Touch Interaction**
- click/tap on a day → focus the day  
- click/tap on an item → open popup  
- scroll → vertical movement only  

### **4.1.4.3 Keyboard Interaction**
- arrow keys mirror DPAD  
- Enter opens popup  
- Escape closes popup  

---

# **4.1.5 Popup Routing Requirements**
Every item in the Calendar View must route to the correct popup:

- Episode → Episode Popup (P3)  
- Season (if clicked via episode grouping) → Season Popup (P2)  
- Show (if clicked via show header) → Show Popup (P1)  
- Movie → Movie Popup (P4)  
- EPG entry (future‑phase) → Program Popup (future‑phase)  

Routing must be deterministic and must never fail.

---

# **4.1.6 Icon Strip Requirements**
Every calendar item must display the unified icon strip:

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

# **4.1.7 Logo Requirements**
Each item must display:

- network logo (for episodes)  
- service logo (for movies)  
- channel logo (for live TV)  

Logos must be:

- local images  
- size‑normalized  
- aligned to the right of the item  

---

# **4.1.8 Visual Design Requirements**
### **4.1.8.1 Poster Sizing**
Calendar posters must use a **small, square or near‑square** variant.

### **4.1.8.2 Spacing**
- consistent vertical spacing  
- consistent horizontal spacing  
- no layout shifts  

### **4.1.8.3 Colors & Contrast**
- high contrast  
- neurodivergent‑friendly palette  
- no flashing or animated elements  

### **4.1.8.4 Overflow Handling**
If a day contains more than 3 items:

- show first 3  
- show “+X more” indicator  
- clicking indicator opens a popup listing all items  

---

# **4.1.9 Error Handling Requirements**
### **4.1.9.1 Missing Data**
If an item is missing required fields:

- show fallback poster  
- show fallback title  
- show error icon  
- log error to `errors[]`  

### **4.1.9.2 Invalid Dates**
Invalid dates must be:

- logged  
- excluded from rendering  
- never break the grid  

### **4.1.9.3 Missing Images**
Missing images must use fallback assets.

---

# **4.1.10 Future‑Phase Requirements**
The Calendar View must support:

### **4.1.10.1 Full EPG Integration**
Live TV channels must display:

- program blocks  
- start/end times  
- program posters  
- program metadata  

### **4.1.10.2 Profile Relevance**
Items must be visually weighted based on:

- watch progress  
- profile preferences  
- profile watchlist  

### **4.1.10.3 Watch Progress Indicators**
Episodes and movies must show:

- progress bar  
- resume marker  

### **4.1.10.4 Cross‑Service Sync**
Calendar must reflect:

- Trakt watch history  
- TMDB updates  
- future streaming services  

---

# **4.1.11 Invariants**
The following must never change:

- 7×5/6 grid  
- sticky month header  
- poster sizing rules  
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

# **4.1.12 End of Section 4.1 — Calendar View**
