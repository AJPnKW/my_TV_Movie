# **SECTION 7 — ASSETS & MEDIA**  
**Authoritative Specification — Full Scope (Including Future‑Phase Features)**  
**Document ID:** Section 7 — Assets & Media  
**Version:** V0.00  
---
# **7.1 Purpose of This Section**
This section defines the **complete, authoritative, immutable rules** for all assets and media used in the *my_TV_Movie (My TV Hub)* system, including:
- posters  
- backdrops  
- still images  
- logos  
- icons  
- fallback assets  
- local storage rules  
- naming conventions  
- integrity rules  
- caching rules  
- future‑phase asset types  
All assets must be **local**, never remote.
---
# **7.2 Asset Categories**
The system must support the following asset categories:
- posters  
- backdrops  
- still images  
- network logos  
- service logos  
- channel logos  
- icon strip icons  
- fallback assets  
- collection posters  
- profile avatars (future‑phase)  
- EPG images (future‑phase)  
---
# **7.3 Directory Structure**
Assets must be stored in:
```
assets/posters/
assets/backdrops/
assets/stills/
assets/logos/
assets/icons/
assets/fallback/
assets/collections/
assets/avatars/        (future‑phase)
assets/epg/            (future‑phase)
```
This structure is immutable.
---
# **7.4 Naming Conventions**
### **7.4.1 Posters**
```
poster_<id>.jpg
```
### **7.4.2 Backdrops**
```
backdrop_<id>.jpg
```
### **7.4.3 Stills**
```
still_<showid>_<season>_<episode>.jpg
```
### **7.4.4 Logos**
```
logo_<network>.png
```
### **7.4.5 Icons**
```
icon_<service>.png
```
### **7.4.6 Collections**
```
collection_<id>.jpg
```
### **7.4.7 Avatars (Future‑Phase)**
```
avatar_<profileid>.png
```
### **7.4.8 EPG Images (Future‑Phase)**
```
epg_<channelid>_<timestamp>.jpg
```
---
# **7.5 Local Storage Rules**
### **7.5.1 No Remote URLs**
All images must be:
- downloaded  
- stored locally  
- referenced via relative paths  
### **7.5.2 Integrity Requirements**
Each asset must:
- exist  
- be readable  
- be valid image format  
- match expected dimensions  
### **7.5.3 Fallback Rules**
If an asset is missing:
- use fallback poster  
- use fallback logo  
- use fallback icon  
Fallbacks must always exist.
---
# **7.6 Image Dimensions**
### **7.6.1 Posters**
- portrait aspect ratio  
- consistent across all views  
### **7.6.2 Backdrops**
- landscape aspect ratio  
- consistent across all popups  
### **7.6.3 Stills**
- 16:9 aspect ratio  
### **7.6.4 Logos**
- normalized height  
- variable width  
### **7.6.5 Icons**
- square  
- consistent size  
---
# **7.7 Icon Strip Requirements**
Icon strip icons must:
- be local  
- be consistent size  
- be horizontally aligned  
- be deterministic in order  
---
# **7.8 Logo Requirements**
Logos must:
- be local  
- be normalized  
- never distort  
- never stretch  
---
# **7.9 Asset Validation**
The system must validate:
- file existence  
- file size  
- file format  
- file readability  
- naming conventions  
Invalid assets must be logged.
---
# **7.10 Caching Rules**
### **7.10.1 Image Caching Script**
Must:
- download all images  
- validate integrity  
- store locally  
- never overwrite valid images unless updated  
### **7.10.2 Cache Invalidation**
Cache must be invalidated when:
- poster changes  
- backdrop changes  
- logo changes  
- icon changes  
---
# **7.11 Future‑Phase Asset Requirements**
Future‑phase assets include:
- profile avatars  
- EPG images  
- AI‑generated thumbnails (local only)  
- offline mode asset bundles  
---
# **7.12 Invariants**
The following must never change:
- directory structure  
- naming conventions  
- local‑only rule  
- fallback hierarchy  
- icon strip rules  
- logo normalization rules  
These invariants are permanent.
---
# **7.13 End of Section 7 — Assets & Media**
