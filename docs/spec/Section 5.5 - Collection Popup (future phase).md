SECTION 5.5 — COLLECTION POPUP (FUTURE‑PHASE)
Authoritative Specification — Full Scope (Including Future‑Phase Features) Document ID: Section 5.5 — Collection Popup Version: V0.00
5.5.1 Purpose of This Popup
The Collection Popup provides a complete, detailed, scrollable metadata view for a movie collection. It must support:
collection metadata
collection poster and backdrop
list of movies in the collection
streaming links for each movie
icon strip
profile relevance
watch progress
routing to Movie Popup (P4)
This popup is future‑phase but binding immediately.
5.5.2 Structural Layout Requirements
The Collection Popup must include:
5.5.2.1 Header
collection name
close button
5.5.2.2 Poster Section
collection poster (local path)
fallback poster if missing
5.5.2.3 Metadata Section
Must include:
overview
number of movies
keywords
profile_relevance (future‑phase)
5.5.2.4 Movie List
Each movie entry must include:
poster (local path)
title
release_date
runtime
streaming_links[]
icon_strip[]
progress indicator (future‑phase)
Selecting a movie opens Movie Popup (P4).
5.5.2.5 Related Collections (Future‑Phase)
similar collections
trending collections
5.5.3 Data Requirements
The Collection Popup must use:
collections[*]
collections[*].movies[]
movies[*]
streaming_links[]
icon_strip[]
profile_relevance
watch_progress
Required fields:
id
name
overview
poster (local path)
backdrop (local path)
movies[]
5.5.4 Interaction Requirements
DPAD up/down scrolls
DPAD left/right moves between movies
Enter opens Movie Popup
Back closes popup
5.5.5 Routing Requirements
selecting a movie → Movie Popup (P4)
selecting related collection → Collection Popup
Routing must be deterministic.
5.5.6 Visual Requirements
consistent poster aspect ratio
high contrast
no layout shifts
neurodivergent‑friendly spacing
5.5.7 Error Handling
Missing fields must:
use fallbacks
log errors
5.5.8 Future‑Phase Requirements
profile relevance weighting
watch progress indicators
cross‑service sync
AI‑assisted recommendations
collection‑level resume behavior
5.5.9 Invariants
movie list must always appear
icon strip must always appear
routing must always be deterministic
5.5.10 End of Section 5.5 — Collection Popup