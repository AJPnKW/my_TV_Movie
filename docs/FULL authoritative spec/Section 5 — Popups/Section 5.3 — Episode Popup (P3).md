SECTION 5.3 — EPISODE POPUP (P3)
Authoritative Specification — Full Scope (Including Future‑Phase Features) Document ID: Section 5.3 — Episode Popup (P3) Version: V0.00

5.3.1 Purpose of This Popup
The Episode Popup (P3) provides a complete, detailed, scrollable metadata view for a specific episode of a TV show. It must support:

episode metadata

still image

streaming links

icon strip

TBA handling

profile relevance

watch progress

routing to Season Popup (P2) and Show Popup (P1)

This popup is mandatory.

5.3.2 Structural Layout Requirements
The Episode Popup must include:

5.3.2.1 Header
show title

season + episode number

close button

5.3.2.2 Still Image Section
still image (local path)

fallback still if missing

aspect ratio must be consistent across all episodes

5.3.2.3 Metadata Section
Must include:

episode title

overview

air_date

runtime

TBA indicator

vote_average

vote_count

profile_relevance (future‑phase)

watch_progress (future‑phase)

5.3.2.4 Streaming Links
normalized streaming links

clickable/tappable

icon strip

5.3.2.5 Navigation Links
Must include:

“View Season” → Season Popup (P2)

“View Show” → Show Popup (P1)

5.3.2.6 Related Episodes (Future‑Phase)
previous episode

next episode

recommended episodes

5.3.3 Data Requirements
The Episode Popup must use:

shows[].seasons[].episodes[*]

streaming_links[]

icon_strip[]

profile_relevance

watch_progress

Required fields:

episode_number

title

overview

air_date

runtime

still (local path)

tba

streaming_links[]

icon_strip[]

5.3.4 Interaction Requirements
DPAD up/down scrolls

DPAD left/right moves between streaming links or related episodes

Enter activates

Back closes popup

5.3.5 Routing Requirements
“View Season” → Season Popup (P2)

“View Show” → Show Popup (P1)

selecting related episode → Episode Popup (P3)

Routing must be deterministic.

5.3.6 Visual Requirements
consistent still image aspect ratio

high contrast

no layout shifts

neurodivergent‑friendly spacing

5.3.7 Error Handling
Missing fields must:

use fallbacks

log errors

5.3.8 Future‑Phase Requirements
profile relevance weighting

watch progress indicators

cross‑service sync

AI‑assisted recommendations

episode‑level resume behavior

5.3.9 Invariants
still image must always appear

streaming links must always appear

icon strip must always appear

routing must always be deterministic