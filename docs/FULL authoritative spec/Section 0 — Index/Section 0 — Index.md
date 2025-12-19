# FULL Authoritative Specification — Index

## Section 0 — Index

## Section 1 — Global Rules

## Section 2 — Architecture

## Section 3 — Data Model

## Section 4 — UI (each view separately)
- 4.1 — Calendar View
- 4.2 — Shows View
- 4.3 — Movies View
- 4.4 — Live TV View
- 4.5 — Config View
- 4.6 — Explore View *(future phase)*
- 4.7 — Profiles View *(future phase)*
- 4.8 — Watchlist / Watched Filters *(future phase)*

## Section 5 — Popups
- 5.1 — Show Popup (P1)
- 5.2 — Season Popup (P2)
- 5.3 — Episode Popup (P3)
- 5.4 — Movie Popup (P4)
- 5.5 — Collection Popup *(future phase)*
- 5.6 — Person Popup *(future phase)*

## Section 6 — UX

## Section 7 — Assets

## Section 8 — Scripts

## Section 9 — Workflow

## Section 10 — Versioning

## Section 11 — Errors

## Section 12 — Future‑Phase

## Section 13 — Invariants

---

# Appendix A — Functional Details

This appendix provides functional descriptions for all user‑facing components, including UI views, popups, workflows, and interaction patterns. Each subsection corresponds directly to a numbered section in the main specification.

---

## A.1 — UI Views (Section 4)

### 4.1 — Calendar View
- Primary purpose: Display scheduled content (episodes, movies, live events) in a calendar layout.
- Core interactions:
  - Navigate by day/week/month.
  - Select an item to open its corresponding popup.
  - Filter by profile, service, or content type.
- Functional constraints:
  - Must support both grid and list modes.
  - Must show indicators for watched/unwatched.

### 4.2 — Shows View
- Purpose: Browse all TV shows.
- Interactions:
  - Search, filter, sort.
  - Open Show Popup (P1).
  - Navigate to Seasons/Episodes.

### 4.3 — Movies View
- Purpose: Browse all movies.
- Interactions:
  - Search, filter, sort.
  - Open Movie Popup (P4).

### 4.4 — Live TV View
- Purpose: Display live channels and current programming.
- Interactions:
  - Channel list navigation.
  - Program details popup.
  - Quick‑tune actions.

### 4.5 — Config View
- Purpose: User and system configuration.
- Interactions:
  - Profile management.
  - Service integration.
  - UI/UX preferences.

### 4.6 — Explore View *(future phase)*
- Purpose: Discovery‑focused browsing.
- Interactions:
  - Trending, recommended, curated lists.

### 4.7 — Profiles View *(future phase)*
- Purpose: Dedicated profile management UI.

### 4.8 — Watchlist / Watched Filters *(future phase)*
- Purpose: Manage watchlist and watched‑status filters.

---

## A.2 — Popups (Section 5)

### 5.1 — Show Popup (P1)
- Displays show metadata, seasons, and actions.
- Interactions:
  - Add/remove from watchlist.
  - Navigate to Season Popup (P2).

### 5.2 — Season Popup (P2)
- Displays season‑level metadata.
- Interactions:
  - Episode list.
  - Navigate to Episode Popup (P3).

### 5.3 — Episode Popup (P3)
- Displays episode metadata.
- Interactions:
  - Mark watched/unwatched.
  - Play episode.

### 5.4 — Movie Popup (P4)
- Displays movie metadata.
- Interactions:
  - Play movie.
  - Add/remove from watchlist.

### 5.5 — Collection Popup *(future phase)*
- Displays grouped content (collections, bundles).

### 5.6 — Person Popup *(future phase)*
- Displays actor/crew metadata.

---

## A.3 — Workflows (Section 9)

### Example workflows:
- Content discovery → popup → playback.
- Calendar navigation → item selection → popup.
- Profile switching → UI refresh.
- Watchlist management → filtering → playback.

---

## A.4 — User Interaction Patterns (Global)

- Consistent popup behavior across all content types.
- Unified search and filtering model.
- Predictable navigation hierarchy.
- Accessibility requirements (keyboard, screen reader, contrast).


# Appendix B — Technical Details

This appendix contains the technical underpinnings of the system, including architecture, data models, API contracts, and implementation constraints.

---

## B.1 — Architecture (Section 2)

### System Architecture Overview
- Modular, component‑based UI.
- Data layer abstracted behind unified API gateway.
- Caching layer for performance and offline tolerance.
- Event‑driven updates for UI refresh.

### Key Architectural Constraints
- All UI components must be stateless where possible.
- Popups must be lazy‑loaded.
- Views must support incremental rendering.

---

## B.2 — Data Model (Section 3)

### Core Entities
- Show
- Season
- Episode
- Movie
- Person
- Collection
- Profile
- Service

### Relationships
- Show → Seasons → Episodes
- Movie → Standalone
- Person → Appears in (shows, movies)
- Profile → Watch history, preferences

### Data Integrity Rules
- IDs must be globally unique.
- Timestamps must be UTC.
- Watch status must be atomic.

---

## B.3 — API Contracts

### Required Endpoints
- `/shows`, `/shows/{id}`
- `/movies`, `/movies/{id}`
- `/episodes/{id}`
- `/calendar`
- `/profiles`
- `/search?q=`

### Response Requirements
- JSON only.
- All responses must include:
  - `id`
  - `type`
  - `attributes`
  - `relationships`

---

## B.4 — Implementation Constraints

- UI must remain responsive under high data volume.
- All popups must load in < 200ms (cached).
- Views must support pagination or infinite scroll.
- Versioning must be applied to all spec files.
- Inventory tracking must remain consistent across updates.

