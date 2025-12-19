SECTION 5.2 — SEASON POPUP (P2)
Authoritative Specification — Full Scope (Including Future‑Phase Features) Document ID: Section 5.2 — Season Popup (P2) Version: V0.00
5.2.1 Purpose of This Popup
The Season Popup (P2) provides a complete, scrollable list of episodes for a specific season of a show. It must support:
season metadata
episode list
streaming links
icon strip
routing to Episode Popup (P3)
profile relevance
watch progress
This popup is mandatory.
5.2.2 Structural Layout Requirements
The Season Popup must include:
5.2.2.1 Header
show title
season number
close button
5.2.2.2 Poster Section
season poster (local path)
fallback poster if missing
5.2.2.3 Metadata Section
Must include:
overview
air_date
episode_count
5.2.2.4 Episode List
Each episode entry must include:
episode number
title
overview
air_date
runtime
still image (local path)
streaming links
icon strip
TBA indicator
progress indicator (future‑phase)
Selecting an episode opens Episode Popup (P3).
5.2.3 Data Requirements
The Season Popup must use:
shows[].seasons[]
shows[].seasons[].episodes[*]
streaming_links[]
icon_strip[]
profile_relevance
watch_progress
5.2.4 Interaction Requirements
DPAD up/down scrolls
DPAD left/right moves between episodes
Enter opens Episode Popup
Back closes popup
5.2.5 Routing Requirements
Episode selection → Episode Popup (P3)
Show title selection (future‑phase) → Show Popup (P1)
5.2.6 Visual Requirements
consistent still image aspect ratio
high contrast
no layout shifts
neurodivergent‑friendly spacing
5.2.7 Error Handling
Missing fields must:
use fallbacks
log errors
5.2.8 Future‑Phase Requirements
profile relevance weighting
watch progress indicators
cross‑service sync
AI‑assisted recommendations
5.2.9 Invariants
episode list must always appear
icon strip must always appear
routing must always be deterministic
5.2.10 End of Section 5.2 — Season Popup (P2)