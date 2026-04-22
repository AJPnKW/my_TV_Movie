SECTION 5.4 — MOVIE POPUP (P4)
Authoritative Specification — Full Scope (Including Future‑Phase Features) Document ID: Section 5.4 — Movie Popup (P4) Version: V0.00
5.4.1 Purpose of This Popup
The Movie Popup (P4) provides a complete, detailed, scrollable metadata view for a movie. It must support:
movie metadata
poster
streaming links
icon strip
collection metadata
profile relevance
watch progress
routing to Collection Popup (future‑phase)
This popup is mandatory.
5.4.2 Structural Layout Requirements
The Movie Popup must include:
5.4.2.1 Header
movie title
release year
close button
5.4.2.2 Poster Section
poster (local path)
fallback poster if missing
5.4.2.3 Metadata Section
Must include:
overview
genres
keywords
release_date
runtime
popularity
vote_average
vote_count
profile_relevance (future‑phase)
watch_progress (future‑phase)
5.4.2.4 Streaming Links
normalized streaming links
clickable/tappable
icon strip
5.4.2.5 Collection Metadata
If the movie belongs to a collection:
collection name
collection poster
collection overview
“View Collection” button → Collection Popup (future‑phase)
5.4.2.6 Related Movies (Future‑Phase)
recommended movies
similar movies
trending movies
5.4.3 Data Requirements
The Movie Popup must use:
movies[*]
movies[*].collection
streaming_links[]
icon_strip[]
profile_relevance
watch_progress
Required fields:
id
title
overview
genres[]
runtime
release_date
poster (local path)
backdrop (local path)
streaming_links[]
icon_strip[]
5.4.4 Interaction Requirements
DPAD up/down scrolls
DPAD left/right moves between streaming links or related movies
Enter activates
Back closes popup
5.4.5 Routing Requirements
“View Collection” → Collection Popup (future‑phase)
selecting related movie → Movie Popup (P4)
Routing must be deterministic.
5.4.6 Visual Requirements
consistent poster aspect ratio
high contrast
no layout shifts
neurodivergent‑friendly spacing
5.4.7 Error Handling
Missing fields must:
use fallbacks
log errors
5.4.8 Future‑Phase Requirements
profile relevance weighting
watch progress indicators
cross‑service sync
AI‑assisted recommendations
collection‑level navigation
5.4.9 Invariants
poster must always appear
streaming links must always appear
icon strip must always appear
routing must always be deterministic
5.4.10 End of Section 5.4 — Movie Popup (P4)