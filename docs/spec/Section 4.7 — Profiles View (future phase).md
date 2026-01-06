# **SECTION 4.7 — PROFILES VIEW (FUTURE‑PHASE)**  
**Authoritative Specification — Full Scope (Including Future‑Phase Features)**  
**Document ID:** Section 4.7 — Profiles View  
**Version:** V0.00  
---
# **4.7.1 Purpose of This View**
The Profiles View provides a **centralized, deterministic interface** for managing user profiles within the *my_TV_Movie (My TV Hub)* system.  
It must support:
- profile selection  
- profile creation  
- profile deletion  
- profile editing  
- profile‑specific settings  
- profile‑specific watchlists  
- profile‑specific watch progress  
- profile‑specific recommendations  
- profile‑specific preferences  
- cross‑service sync per profile  
- future‑phase multi‑device profile support  
This view is future‑phase but **binding immediately**.
---
# **4.7.2 Structural Layout Requirements**
The Profiles View must follow a **strict, immutable layout**:
### **4.7.2.1 Root Structure**
The view consists of:
- global sticky header  
- profile selector grid  
- profile management panel  
- scrollable content container  
### **4.7.2.2 Profile Selector Grid**
The grid must include:
- one card per profile  
- one “Add Profile” card  
- DPAD‑navigable layout  
- consistent spacing and alignment  
### **4.7.2.3 Profile Management Panel**
When a profile is selected, the panel must display:
- profile avatar  
- profile name  
- profile settings  
- watchlist  
- watch progress  
- recommendation tuning  
- cross‑service sync settings  
---
# **4.7.3 Profile Card Requirements**
Each profile must be represented by a **Profile Card**, which includes:
### **4.7.3.1 Required Visual Elements**
- avatar (local path)  
- profile name  
- profile badge (if applicable)  
- active profile indicator  
### **4.7.3.2 Required Metadata Elements**
- id  
- name  
- avatar  
- settings.theme  
- settings.font_scale  
- settings.language  
### **4.7.3.3 Interaction Behavior**
- selecting a profile activates it  
- long‑press or options button opens profile management  
- DPAD focus must be visible and predictable  
---
# **4.7.4 Data Requirements**
The Profiles View must consume data exclusively from `data.json`.
### **4.7.4.1 Required Data Fields**
Each profile must include:
- id  
- name  
- avatar (local path)  
- settings:  
  - theme  
  - font_scale  
  - language  
- watchlist[]  
- watch_progress{}  
- profile_relevance  
- cross_service_sync settings (future‑phase)  
### **4.7.4.2 Watchlist Requirements**
Each profile must maintain its own:
- watchlist  
- watchlist ordering  
- watchlist metadata  
### **4.7.4.3 Watch Progress Requirements**
Each profile must maintain:
- per‑item progress  
- last watched timestamp  
- completion percentage  
### **4.7.4.4 Recommendation Data Requirements**
Must include:
- profile_relevance  
- watch_history  
- genre preferences  
- keyword preferences  
---
# **4.7.5 Interaction Requirements**
### **4.7.5.1 DPAD Navigation**
DPAD navigation must follow:
- left/right → adjacent profile cards  
- up/down → move between grid and management panel  
- OK/Enter → select profile  
- Back → return to previous view  
### **4.7.5.2 Mouse/Touch Interaction**
- click/tap profile → activate  
- click/tap settings → open management panel  
### **4.7.5.3 Keyboard Interaction**
- arrow keys mirror DPAD  
- Enter activates  
- Escape closes dialogs  
---
# **4.7.6 Profile Management Requirements**
The profile management panel must include:
### **4.7.6.1 Profile Editing**
- change avatar  
- change name  
- change theme  
- change font scale  
- change language  
### **4.7.6.2 Watchlist Management**
- add/remove items  
- reorder items  
- clear watchlist  
### **4.7.6.3 Watch Progress Management**
- reset progress  
- sync progress  
- import/export progress  
### **4.7.6.4 Recommendation Controls**
- adjust relevance weighting  
- adjust genre weighting  
- reset recommendation model  
### **4.7.6.5 Cross‑Service Sync Controls**
- connect/disconnect  
- sync now  
- sync schedule  
- conflict resolution rules  
---
# **4.7.7 Visual Design Requirements**
### **4.7.7.1 Profile Card Layout**
Profile cards must include:
- centered avatar  
- name below avatar  
- consistent spacing  
- consistent sizing  
### **4.7.7.2 Avatar Requirements**
Avatars must:
- be local images  
- use a square aspect ratio  
- support fallback avatars  
### **4.7.7.3 Colors & Contrast**
- high contrast  
- neurodivergent‑friendly palette  
- no flashing or animated elements  
---
# **4.7.8 Popup Routing Requirements**
Profile actions must route to:
- avatar picker popup  
- profile editor popup  
- watchlist popup  
- watch progress popup  
- recommendation tuning popup  
- cross‑service sync popup  
All popups must follow:
- scroll trapping  
- DPAD trapping  
- deterministic routing  
---
# **4.7.9 Error Handling Requirements**
### **4.7.9.1 Missing Data**
If a profile is missing required fields:
- show fallback avatar  
- show fallback name  
- show error icon  
- log error  
### **4.7.9.2 Invalid Settings**
Invalid settings must:
- be rejected  
- show error message  
- not break the UI  
### **4.7.9.3 Sync Failures**
Sync failures must:
- show error dialog  
- log error  
- not corrupt profile data  
---
# **4.7.10 Future‑Phase Requirements**
The Profiles View must support:
### **4.7.10.1 Multi‑Device Profiles**
Profiles must support:
- cloud sync  
- device‑specific overrides  
- conflict resolution  
### **4.7.10.2 AI‑Assisted Recommendations**
Recommendations must:
- use local inference  
- never call external services  
- be deterministic  
### **4.7.10.3 Cross‑Service Sync**
Profiles must support:
- TMDB sync  
- Trakt sync  
- future streaming services  
### **4.7.10.4 Universal Sort Framework**
Profile preferences must influence:
- Shows View  
- Movies View  
- Live TV View  
- Explore View  
- Watchlist View  
---
# **4.7.11 Invariants**
The following must never change:
- profile card layout  
- profile management structure  
- DPAD navigation model  
- deterministic behavior  
- local image usage  
- no dynamic schema  
- no missing fields  
- no missing UI elements  
- no destructive actions without confirmation  
These invariants are permanent.
---
# **4.7.12 End of Section 4.7 — Profiles View**
