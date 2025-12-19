SECTION 5.6 — PERSON POPUP (FUTURE‑PHASE)
Authoritative Specification — Full Scope (Including Future‑Phase Features) Document ID: Section 5.6 — Person Popup Version: V0.00
5.6.1 Purpose of This Popup
The Person Popup provides a complete, detailed, scrollable metadata view for a person (actor, director, writer, etc.). It must support:
person metadata
profile image
biography
filmography
related people
profile relevance
routing to Show Popup (P1) and Movie Popup (P4)
This popup is future‑phase but binding immediately.
5.6.2 Structural Layout Requirements
The Person Popup must include:
5.6.2.1 Header
person name
close button
5.6.2.2 Profile Image Section
profile image (local path)
fallback image if missing
5.6.2.3 Metadata Section
Must include:
biography
birthday
deathday (if applicable)
popularity
known_for[]
profile_relevance (future‑phase)
5.6.2.4 Filmography
Filmography must be grouped into:
Movies
TV Shows
Each entry must include:
poster (local path)
title
release_date or first_air_date
role (if available)
streaming_links[]
icon_strip[]
Selecting an entry opens the appropriate popup:
Show → Show Popup (P1)
Movie → Movie Popup (P4)
5.6.2.5 Related People (Future‑Phase)
collaborators
co‑stars
similar profiles
5.6.3 Data Requirements
The Person Popup must use:
people[*]
people[*].known_for[]
shows[]
movies[]
streaming_links[]
icon_strip[]
profile_relevance
Required fields:
id
name
profile (local path)
biography
birthday
popularity
known_for[]
5.6.4 Interaction Requirements
DPAD up/down scrolls
DPAD left/right moves between filmography items
Enter opens Show or Movie Popup
Back closes popup
5.6.5 Routing Requirements
selecting a movie → Movie Popup (P4)
selecting a show → Show Popup (P1)
selecting related person → Person Popup
Routing must be deterministic.
5.6.6 Visual Requirements
consistent profile image aspect ratio
high contrast
no layout shifts
neurodivergent‑friendly spacing
5.6.7 Error Handling
Missing fields must:
use fallbacks
log errors
5.6.8 Future‑Phase Requirements
profile relevance weighting
cross‑service sync
AI‑assisted recommendations
filmography‑based discovery
5.6.9 Invariants
filmography must always appear
icon strip must always appear
routing must always be deterministic
5.6.10 End of Section 5.6 — Person Popup