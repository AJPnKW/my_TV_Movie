SECTION 5.1 — SHOW POPUP (P1)
Authoritative Specification — Full Scope (Including Future‑Phase Features) Document ID: Section 5.1 — Show Popup (P1) Version: V0.00

5.1.1 Purpose of This Popup
The Show Popup (P1) provides a complete, detailed, scrollable metadata view for a TV show. It must support:

show metadata

season list

streaming links

icon strip

network logos

related shows

profile relevance

watch progress

routing to Season Popup (P2)

This popup is mandatory.

5.1.2 Structural Layout Requirements
The Show Popup must include:

5.1.2.1 Header
show title

status badge

network logo

close button

5.1.2.2 Poster Section
poster (local path)

fallback poster if missing

5.1.2.3 Metadata Section
Must include:

overview

genres

keywords

first_air_date

last_air_date

origin_country

runtime

popularity

vote_average

vote_count

5.1.2.4 Streaming Links
normalized streaming links

clickable/tappable

icon strip

5.1.2.5 Seasons List
Each season entry must include:

season number

episode count

poster (local path)

air_date

progress indicator (future‑phase)

Selecting a season opens Season Popup (P2).

5.1.2.6 Related Shows (Future‑Phase)
recommended shows

similar shows

trending shows

5.1.3 Data Requirements
The Show Popup must use:

shows[*]

shows[].seasons[]

shows[*].streaming_links[]

shows[*].icon_strip[]

shows[*].network_logo

profile_relevance

watch_progress

5.1.4 Interaction Requirements
DPAD up/down scrolls

DPAD left/right moves between seasons

Enter opens Season Popup

Back closes popup

5.1.5 Routing Requirements
Season selection → Season Popup (P2)

Episode selection (via season) → Episode Popup (P3)

5.1.6 Visual Requirements
consistent poster aspect ratio

high contrast

no layout shifts

neurodivergent‑friendly spacing

5.1.7 Error Handling
Missing fields must:

use fallbacks

log errors

5.1.8 Future‑Phase Requirements
profile relevance weighting

watch progress indicators

cross‑service sync

AI‑assisted recommendations

5.1.9 Invariants
season list must always appear

streaming links must always appear

icon strip must always appear

5.1.10 End of Section 5.1 — Show Popup (P1)