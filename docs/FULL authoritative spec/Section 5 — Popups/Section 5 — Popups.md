SECTION 5.0 — POPUPS (MASTER SECTION)
Authoritative Specification — Full Scope (Including Future‑Phase Features) Document ID: Section 5.0 — Popups Version: V0.00
5.0.1 Purpose of This Section
This section defines the complete, authoritative, immutable architecture for all popup overlays used in the my_TV_Movie (My TV Hub) system. Popups are stacked overlays that provide detailed metadata, navigation, and actions for:
shows
seasons
episodes
movies
collections (future‑phase)
people (future‑phase)
Popups are a core subsystem and must follow strict rules for:
layout
metadata
DPAD navigation
scroll trapping
routing
icon strip usage
logo usage
future‑phase extensibility
5.0.2 Global Popup Architecture
All popups must follow the same structural model:
5.0.2.1 Popup Structure
Each popup must include:
dimmed background overlay
centered popup container
scroll‑trapped content area
header section
poster section
metadata section
icon strip
action buttons
related content rows (if applicable)
5.0.2.2 Popup Stack Rules
only one popup visible at a time
opening a popup pushes onto the stack
closing a popup pops the stack
background scroll disabled
DPAD focus trapped inside popup
Escape/Back closes the topmost popup
5.0.2.3 Popup Routing Rules
Popups must route deterministically:
Show → Season → Episode
Movie → Collection (future‑phase)
Person → Filmography (future‑phase)
EPG Entry → Program Popup (future‑phase)
Routing must never fail.
5.0.3 Global Data Requirements
All popups must use data exclusively from data.json.
Required fields include:
title
poster (local path)
backdrop (local path)
runtime
release/air date
genres
keywords
streaming_links[]
icon_strip[]
profile_relevance
watch_progress
collection metadata (if applicable)
season/episode metadata (if applicable)
5.0.4 Global Interaction Requirements
5.0.4.1 DPAD Navigation
up/down → scroll content
left/right → move between buttons or related items
OK/Enter → activate
Back → close popup
5.0.4.2 Mouse/Touch Interaction
click/tap outside popup → close
click/tap poster → enlarge (future‑phase)
click/tap streaming link → open
5.0.4.3 Keyboard Interaction
arrow keys mirror DPAD
Enter activates
Escape closes popup
5.0.5 Global Visual Requirements
high contrast
neurodivergent‑friendly palette
no flashing or animated elements
consistent poster sizing
consistent spacing
consistent metadata layout
5.0.6 Global Error Handling
If required fields are missing:
show fallback poster
show fallback title
show error icon
log error to errors[]
5.0.7 Future‑Phase Extensions
All popups must support:
profile relevance
watch progress
cross‑service sync
AI‑assisted recommendations
multi‑profile support
universal sort framework integration
5.0.8 End of Section 5.0 — Popups (Master Section)
