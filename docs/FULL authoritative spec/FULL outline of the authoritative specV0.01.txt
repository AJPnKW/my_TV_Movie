SECTION 0 — Executive Summary (Optional)
A short overview of:
purpose of the system
high‑level architecture
major components
future‑phase scope
(We can skip this if you prefer.)
SECTION 1 — Global Rules & Non‑Negotiable Constraints
This section defines the laws of the system, including:
no feature drops
no architectural invention
no renaming
no partial files
no destructive writes
no cross‑contamination
strict metadata headers
strict versioning
strict rendering pipeline
strict popup chain
strict UX rules
strict DPAD rules
strict neurodivergent‑friendly rules
strict file integrity rules
strict workflow guardrails
This becomes the foundation for all other sections.
SECTION 2 — System Architecture
Defines the entire system, including:
SPA structure
Views
Popups
Components
Data flow
Rendering pipeline
Script pipeline
Workflow pipeline
Asset pipeline
Future‑phase modules
This section is the “map” of the whole project.
SECTION 3 — Data Model (data.json)
Full schema for:
shows
seasons
episodes
movies
live TV
collections
streaming links
local image paths
metadata
error blocks
future‑phase fields
This section is critical because everything depends on data.json.
SECTION 4 — UI Specification (Views)
Each view gets its own subsection:
4.1 Calendar View
4.2 Shows View
4.3 Movies View
4.4 Live TV View
4.5 Config View
4.6 Explore View (future phase)
4.7 Profiles View (future phase)
4.8 Watchlist / Watched Filters (future phase)
Each subsection includes:
layout
components
filters
sorting
card structure
icon strip
logos
poster rules
DPAD behavior
error handling
future‑phase extensions
SECTION 5 — Popup Specification
Each popup gets its own subsection:
5.1 Show Popup (P1)
5.2 Season Popup (P2)
5.3 Episode Popup (P3)
5.4 Movie Popup (P4)
5.5 Collection Popup (future phase)
5.6 Person Popup (future phase)
Each includes:
required fields
layout
navigation
DPAD behavior
scroll trapping
icon strip
logos
streaming links
future‑phase enhancements
SECTION 6 — UX & Accessibility
Includes:
DPAD navigation rules
focus zones
scroll behavior
sticky header rules
neurodivergent‑friendly spacing
color contrast
predictable layout rules
animation constraints
future‑phase UX extensions
SECTION 7 — Assets & Media
Includes:
poster/backdrop rules
local caching rules
fallback hierarchy
network/service logo mapping
icon strip rules
future‑phase asset types
SECTION 8 — Scripts (TMDB, Trakt, Image Caching)
Includes:
fetch_tmdb.py
fetch_trakt.py
image caching scripts
streaming link normalization
atomic writes
schema validation
non‑destructive rules
future‑phase script extensions
SECTION 9 — Workflow (GitHub Actions)
Includes:
build-data.yml
validation gates
fail‑fast rules
file naming rules
deployment rules
future‑phase workflow extensions
SECTION 10 — Versioning & Metadata
Includes:
file header rules
version triple rules
build metadata rules
monotonic versioning
future‑phase versioning extensions
SECTION 11 — Error Handling & Diagnostics
Includes:
UI error messages
script error messages
workflow error messages
config debug panel
future‑phase diagnostics
SECTION 12 — Future‑Phase Features (Full Scope)
Includes:
profiles
watched filters
explore tab
full EPG
universal sort framework
cross‑service sync
advanced caching
offline mode
multi‑device profiles
AI‑powered recommendations (if desired)
This section defines the long‑term roadmap.
SECTION 13 — Invariants (Things That Must NEVER Change)
This is the “constitution” of the project.
Includes:
popup chain
rendering pipeline
data.json schema
icon strip
logo mapping
DPAD rules
metadata rules
versioning rules
file integrity rules
no feature drops
no architectural invention
This section protects the system from future regressions.
