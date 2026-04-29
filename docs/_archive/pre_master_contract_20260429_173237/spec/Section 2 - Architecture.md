# **SECTION 2 — ARCHITECTURE**  
**Authoritative Specification — Full Scope (Including Future‑Phase Features)**  
**Document ID:** Section 2 — Architecture  
**Version:** V0.00  

---

# **2.1 Purpose of This Section**
This section defines the **complete, authoritative architecture** of the *my_TV_Movie (My TV Hub)* system.  
It establishes the **structural, functional, and behavioral architecture** for:

- the SPA (Single‑Page Application)  
- all views  
- all popups  
- all pipelines  
- all scripts  
- all workflows  
- all assets  
- all future‑phase modules  

This architecture is **binding**, **non‑negotiable**, and **permanent**.

---

# **2.2 High‑Level System Architecture**
The system is a **static Single‑Page Application (SPA)** deployed on GitHub Pages.

### **2.2.1 Core Architectural Layers**
The architecture consists of the following immutable layers:

1. **Data Layer**  
   - `data/inputs.json` (canonical editable scope)  
   - `data/data.json` (canonical generated runtime output)  
   - local cached images (posters, backdrops, logos)  
   - availability metadata (`data/watch_source_availability.json`)  
   - metadata files  

2. **Rendering Layer**  
   - `index.html` (root entry point)  
   - view renderers (Calendar, Shows, Movies, Live TV, Config, Explore, Profiles, Watchlist)  
   - popup renderers (Show, Season, Episode, Movie, Collection, Person)  
   - shared UI components (cards, filters, icon strips, logos, headers)  

3. **Script Layer**  
   - TMDB fetch script  
   - Trakt fetch script  
   - image caching script  
   - streaming link normalization script  
   - validation scripts  

4. **Workflow Layer**  
   - GitHub Actions pipeline  
   - validation gates  
   - atomic write enforcement  
   - deployment to GitHub Pages  

5. **Asset Layer**  
   - local image storage  
   - logo mapping  
   - icon strip assets  
   - fallback assets  

6. **UX Layer**  
   - DPAD navigation  
   - focus management  
   - scroll trapping  
   - neurodivergent‑friendly layout rules  

7. **Future‑Phase Modules**  
   - Explore  
   - Profiles  
   - Watchlist / Watched Filters  
   - Full EPG  
   - Universal Sort Framework  
   - Cross‑Service Sync  
   - Advanced Caching  
   - Multi‑Device Profiles  
   - AI‑Assisted Recommendations  

All layers are mandatory and must exist exactly as defined.

---

# **2.3 SPA Structure**
The SPA consists of:

- a single HTML entry point (`index.html`)  
- a global header  
- a tabbed navigation system  
- a dynamic content container  
- popup overlays  

### **2.3.1 Immutable Routing Model**
Routing is **view‑based**, not URL‑based.

The following views must exist:

1. Calendar  
2. Shows  
3. Movies  
4. Live TV  
5. Config  
6. Explore (future‑phase)  
7. Profiles (future‑phase)  
8. Watchlist / Watched Filters (future‑phase)

Routing is implemented via:

- tab selection  
- internal state  
- popup stack  

No URL routing, hash routing, or external routing frameworks are permitted.

---

# **2.4 Rendering Pipeline Architecture**
The rendering pipeline is immutable:

```
Scripts → data.json → index.html → View Renderers → Popup Renderers → UI Components
```

### **2.4.1 Pipeline Stages**
1. **Data Generation Stage**  
   - TMDB/Trakt scripts fetch data  
   - image caching script downloads images  
   - streaming links normalized  
   - schema validated  
   - atomic write to `data.json`  

2. **Data Load Stage**  
   - `index.html` loads `data.json` once  
   - data stored in memory  
   - no further network requests  

3. **View Render Stage**  
   - active view renderer builds UI  
   - filters applied  
   - cards generated  
   - icon strips and logos applied  

4. **Popup Render Stage**  
   - popup renderer builds overlay  
   - scroll trapped  
   - DPAD focus trapped  

5. **Interaction Stage**  
   - DPAD navigation  
   - keyboard navigation  
   - click/tap navigation  

---

# **2.5 View Architecture**
Each view is a **self‑contained renderer** with:

- a root container  
- a header (global)  
- filters (if applicable)  
- cards or rows  
- icon strips  
- logos  
- DPAD focus zones  
- error handling  

### **2.5.1 Calendar View Architecture**
- 7×6 grid  
- sticky month header  
- episode/movie cards  
- poster (calendar size)  
- runtime  
- network logos  
- icon strip  
- popup routing  

### **2.5.2 Shows View Architecture**
- genre filter  
- status filter  
- sort filter  
- show cards  
- current season line  
- network logos  
- icon strip  
- popup routing  

### **2.5.3 Movies View Architecture**
- genre filter  
- status filter  
- sort filter  
- movie cards  
- runtime  
- collection metadata  
- icon strip  
- popup routing  

### **2.5.4 Live TV View Architecture**
- country filter  
- group filter  
- channel cards  
- logo  
- timezone  
- reserved EPG rows  
- future‑phase: full EPG  

### **2.5.5 Config View Architecture**
- theme toggle  
- font scale slider  
- maintenance shortcuts  
- list editors  
- data preview  
- debug panel  

### **2.5.6 Explore View Architecture (Future‑Phase)**
- discovery modules  
- trending  
- popular  
- recommended  
- genre clusters  
- cross‑service aggregation  

### **2.5.7 Profiles View Architecture (Future‑Phase)**
- profile selector  
- profile editor  
- profile‑specific settings  
- profile‑specific watchlist  
- profile‑specific recommendations  

### **2.5.8 Watchlist / Watched Filters Architecture (Future‑Phase)**
- watchlist view  
- watched/unwatched filters  
- progress tracking  
- resume watching  

---

# **2.6 Popup Architecture**
Popups are **stacked overlays** with:

- a dimmed background  
- a scroll‑trapped content container  
- a header  
- a poster  
- metadata  
- icon strip  
- logos  
- navigation controls  

### **2.6.1 Popup Types**
1. Show Popup (P1)  
2. Season Popup (P2)  
3. Episode Popup (P3)  
4. Movie Popup (P4)  
5. Collection Popup (future‑phase)  
6. Person Popup (future‑phase)  

### **2.6.2 Popup Stack Rules**
- only one popup visible at a time  
- opening a popup pushes onto the stack  
- closing a popup pops the stack  
- background scroll disabled  
- DPAD focus trapped  

---

# **2.7 Component Architecture**
The system uses a set of **shared components**:

### **2.7.1 Card Components**
- show card  
- movie card  
- episode card  
- channel card  
- collection card (future‑phase)  
- person card (future‑phase)  

### **2.7.2 Filter Components**
- genre filter  
- status filter  
- sort filter  
- country filter  
- group filter  
- profile filter (future‑phase)  
- watched filter (future‑phase)  

### **2.7.3 Icon Strip Component**
- TMDB  
- VidSrc  
- Videasy  
- future‑phase: additional services  

### **2.7.4 Logo Chip Component**
- network logos  
- service logos  
- fallback logos  

### **2.7.5 Metadata Components**
- runtime  
- release date  
- air date  
- status  
- collection metadata  

---

# **2.8 Script Architecture**
Scripts are **modular**, **non‑destructive**, and **pipeline‑driven**.

### **2.8.1 TMDB Script**
- fetches shows, movies, seasons, episodes  
- downloads posters/backdrops  
- extracts collection metadata  
- normalizes fields  

### **2.8.2 Trakt Script**
- fetches supplemental metadata  
- future‑phase: sync watch history  

### **2.8.3 Image Caching Script**
- downloads all images  
- stores locally  
- validates integrity  

### **2.8.4 Validation Script**
- validates schema  
- validates metadata  
- validates image presence  
- validates counts  

### **2.8.5 Streaming Link Normalization Script**
- normalizes streaming URLs  
- ensures consistency across UI  

---

# **2.9 Workflow Architecture**
The GitHub Actions workflow consists of:

1. **Trigger Stage**  
   - manual  
   - scheduled  
   - list file changes  

2. **Fetch Stage**  
   - TMDB  
   - Trakt  
   - images  

3. **Validation Stage**  
   - schema  
   - metadata  
   - counts  
   - image presence  

4. **Atomic Write Stage**  
   - write `data.json` only if valid  

5. **Deployment Stage**  
   - deploy to GitHub Pages  

6. **Future‑Phase Stage**  
   - profile sync  
   - cross‑service sync  
   - recommendation generation  

---

# **2.10 Asset Architecture**
Assets are stored locally under:

```
assets/posters/
assets/backdrops/
assets/logos/
assets/icons/
assets/fallback/
```

### **2.10.1 Local Storage Rules**
- all images must be local  
- no external URLs allowed  
- fallback hierarchy required  

---

# **2.11 Future‑Phase Architectural Extensions**
The architecture must support:

### **2.11.1 Explore Module**
- discovery engine  
- recommendation engine  
- trending/popular feeds  

### **2.11.2 Profiles Module**
- per‑profile data  
- per‑profile settings  
- per‑profile watchlists  

### **2.11.3 Watchlist Module**
- global watchlist  
- per‑profile watchlist  
- watched/unwatched filters  

### **2.11.4 Full EPG Module**
- channel schedules  
- program metadata  
- timeline grid  

### **2.11.5 Universal Sort Framework**
- consistent sorting across all views  

### **2.11.6 Cross‑Service Sync**
- TMDB  
- Trakt  
- future streaming services  

### **2.11.7 Advanced Caching**
- multi‑layer caching  
- offline mode (future‑phase)  

### **2.11.8 AI‑Assisted Recommendations**
- optional module  
- local inference only  
- no external calls  

---

# **2.12 Architectural Invariants**
The following architectural elements must never change:

- SPA structure  
- popup chain  
- rendering pipeline  
- data.json as single source of truth  
- local image caching  
- DPAD‑first navigation  
- strict component architecture  
- strict workflow pipeline  
- strict script pipeline  
- strict asset structure  
- strict future‑phase module definitions  

These invariants are permanent.

---

# **2.13 End of Section 2 — Architecture**
