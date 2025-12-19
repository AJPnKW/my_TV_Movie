# **SECTION 3 — DATA MODEL**  
**Authoritative Specification — Full Scope (Including Future‑Phase Features)**  
**Document ID:** Section 3 — Data Model  
**Version:** V0.00  

---

# **3.1 Purpose of This Section**
This section defines the **complete, authoritative, immutable schema** for the `data.json` file and all related data structures used by the *my_TV_Movie (My TV Hub)* system.

This schema is:

- the **single source of truth** for all UI rendering  
- the **foundation** for all scripts and workflows  
- the **binding contract** for all future‑phase features  
- **immutable**, except for additive future‑phase extensions  

No field may be renamed, removed, repurposed, or simplified.

---

# **3.2 Global Data Model Rules**
The following rules apply to the entire data model:

### **3.2.1 Single Source of Truth**
`data.json` is the only authoritative data file used by the UI.

### **3.2.2 Mandatory Fields**
All required fields must always exist, even if empty or null.

### **3.2.3 No Empty Arrays**
Empty arrays are forbidden unless explicitly allowed.

### **3.2.4 Local Image Paths Only**
All posters, backdrops, and logos must reference **local paths**, never remote URLs.

### **3.2.5 Normalized Streaming Links**
All streaming links must follow strict normalization rules.

### **3.2.6 Deterministic Ordering**
All arrays must be sorted deterministically:

- shows sorted alphabetically  
- movies sorted alphabetically  
- episodes sorted by episode number  
- seasons sorted by season number  
- channels sorted alphabetically  

### **3.2.7 Metadata Block Required**
The metadata block must always exist and include:

- build timestamp  
- version triple  
- counts  
- script metadata  

### **3.2.8 No Dynamic Schema**
The schema must never change at runtime.

### **3.2.9 Future‑Phase Fields Are Binding**
All future‑phase fields must exist now, even if empty.

---

# **3.3 Top‑Level Structure of `data.json`**
The root of `data.json` contains the following top‑level keys:

```
{
  "shows": [],
  "movies": [],
  "live_tv": [],
  "collections": [],
  "people": [],
  "profiles": [],
  "watchlist": [],
  "metadata": {},
  "errors": []
}
```

All keys are mandatory.

---

# **3.4 Shows Schema**
Each show object has the following structure:

```
{
  "id": <number>,
  "title": <string>,
  "original_title": <string>,
  "overview": <string>,
  "status": <string>,
  "genres": [<string>],
  "network": <string>,
  "network_logo": <string>,        // local path
  "poster": <string>,              // local path
  "backdrop": <string>,            // local path
  "first_air_date": <string>,
  "last_air_date": <string>,
  "next_episode_to_air": <object|null>,
  "seasons": [<season>],
  "streaming_links": [<streaming_link>],
  "icon_strip": [<icon>],
  "popularity": <number>,
  "vote_average": <number>,
  "vote_count": <number>,
  "runtime": <number|null>,
  "origin_country": [<string>],
  "keywords": [<string>],
  "profile_relevance": <number>,   // future-phase
  "watch_progress": <object>,      // future-phase
  "collections": [<collection_ref>]
}
```

### **3.4.1 Season Reference Schema**
Each season object:

```
{
  "season_number": <number>,
  "episode_count": <number>,
  "poster": <string>,              // local path
  "air_date": <string|null>,
  "episodes": [<episode>]
}
```

### **3.4.2 Episode Schema**
Each episode object:

```
{
  "episode_number": <number>,
  "title": <string>,
  "overview": <string>,
  "air_date": <string|null>,
  "runtime": <number|null>,
  "still": <string>,               // local path
  "streaming_links": [<streaming_link>],
  "icon_strip": [<icon>],
  "tba": <boolean>,                // required for TBA episodes
  "profile_relevance": <number>,   // future-phase
  "watch_progress": <object>       // future-phase
}
```

---

# **3.5 Movies Schema**
Each movie object:

```
{
  "id": <number>,
  "title": <string>,
  "original_title": <string>,
  "overview": <string>,
  "genres": [<string>],
  "runtime": <number|null>,
  "release_date": <string>,
  "poster": <string>,              // local path
  "backdrop": <string>,            // local path
  "collection": <collection_ref|null>,
  "streaming_links": [<streaming_link>],
  "icon_strip": [<icon>],
  "popularity": <number>,
  "vote_average": <number>,
  "vote_count": <number>,
  "keywords": [<string>],
  "profile_relevance": <number>,   // future-phase
  "watch_progress": <object>       // future-phase
}
```

---

# **3.6 Live TV Schema**
Each live TV channel object:

```
{
  "id": <string>,
  "name": <string>,
  "country": <string>,
  "group": <string>,
  "logo": <string>,                // local path
  "stream_url": <string>,
  "timezone": <string>,
  "epg": [<epg_entry>],            // future-phase
  "profile_relevance": <number>    // future-phase
}
```

### **3.6.1 EPG Entry Schema (Future‑Phase)**
```
{
  "start": <string>,
  "end": <string>,
  "title": <string>,
  "description": <string>,
  "season": <number|null>,
  "episode": <number|null>,
  "poster": <string>               // local path
}
```

---

# **3.7 Collections Schema**
Each collection object:

```
{
  "id": <number>,
  "name": <string>,
  "overview": <string>,
  "poster": <string>,              // local path
  "backdrop": <string>,            // local path
  "movies": [<movie_ref>],
  "icon_strip": [<icon>],
  "profile_relevance": <number>    // future-phase
}
```

---

# **3.8 People Schema (Future‑Phase)**
Each person object:

```
{
  "id": <number>,
  "name": <string>,
  "profile": <string>,             // local path
  "known_for": [<movie_or_show_ref>],
  "biography": <string>,
  "birthday": <string|null>,
  "deathday": <string|null>,
  "popularity": <number>,
  "icon_strip": [<icon>]
}
```

---

# **3.9 Profiles Schema (Future‑Phase)**
Each profile object:

```
{
  "id": <string>,
  "name": <string>,
  "avatar": <string>,              // local path
  "settings": {
    "theme": <string>,
    "font_scale": <number>,
    "language": <string>
  },
  "watchlist": [<movie_or_show_ref>],
  "watch_progress": {
    "<content_id>": {
      "progress": <number>,
      "timestamp": <string>
    }
  }
}
```

---

# **3.10 Watchlist Schema (Global Watchlist)**
```
{
  "items": [<movie_or_show_ref>]
}
```

---

# **3.11 Streaming Link Schema**
```
{
  "service": <string>,             // normalized name
  "url": <string>,                 // normalized URL
  "quality": <string|null>,
  "type": <string>,                // e.g., "stream", "trailer"
  "icon": <string>                 // local path
}
```

---

# **3.12 Icon Schema**
```
{
  "type": <string>,                // e.g., "tmdb", "vidsrc", "videasy"
  "icon": <string>,                // local path
  "label": <string>
}
```

---

# **3.13 Metadata Schema**
```
{
  "built_at": <string>,
  "version": <string>,             // version triple
  "script_versions": {
    "tmdb": <string>,
    "trakt": <string>,
    "images": <string>,
    "validator": <string>
  },
  "counts": {
    "shows": <number>,
    "movies": <number>,
    "episodes": <number>,
    "seasons": <number>,
    "live_tv": <number>,
    "collections": <number>,
    "people": <number>
  }
}
```

---

# **3.14 Error Schema**
```
{
  "type": <string>,
  "message": <string>,
  "context": <object>
}
```

---

# **3.15 Data Model Invariants**
The following invariants must never change:

- all fields are mandatory unless explicitly optional  
- no renaming of fields  
- no removal of fields  
- no repurposing of fields  
- no dynamic schema  
- all images must be local  
- all streaming links normalized  
- all arrays sorted deterministically  
- metadata block always present  
- future‑phase fields always present  

These invariants are permanent.

---

# **3.16 End of Section 3 — Data Model**
