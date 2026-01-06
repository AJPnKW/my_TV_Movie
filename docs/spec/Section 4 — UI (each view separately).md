/* =========================================================================================
[SECTION] 4.0 — UI (Each View Separately)
[PROJECT] my_TV_Movie (My TV Hub)
[ROLE] Global UI rules for all SPA views (parent section for 4.1–4.8)
[VERSION] v4.5.0
[UPDATED] 2025‑12‑19_00‑00‑00
[OWNER] Andrew & Brant (internal)

[PHASE 4.x CONTEXT]
- This section defines the global UI rules for **SPA views only**.
- SPA views are rendered inside `index.html` and follow the SPA navigation model.
- The new `watchlist.html` is a **standalone, non‑SPA page** and is documented
  separately in Section 4.9. It does NOT follow the rules in this section.
- The deprecated `show.html` (v3.3.5 single‑show page) is removed and replaced
  by Section 4.9.

[NOTES]
- This section defines the invariants that all SPA views must follow.
- Individual SPA views are defined in Sections 4.1–4.8.
- Standalone pages (currently only watchlist.html) are explicitly excluded.
========================================================================================= */

# Section 4.0 — UI (Each View Separately)

## Purpose
This section defines the **global UI requirements for all SPA views** in My TV Hub.
It serves as the parent document for the SPA view specifications in Sections 4.1–4.8.

SPA views are rendered **inside `index.html`**, use the shared navigation model,
and must comply with the global rules and invariants defined here.

**Important Architectural Note (Phase 4.x):**  
`watchlist.html` is a **standalone, non‑SPA page** and is therefore documented
separately in **Section 4.9**. It does not follow the SPA navigation model,
popup system, or rendering pipeline described in this section.

---

## Global UI Principles (SPA Views Only)

### 1. Local‑Only Rendering
SPA views must render exclusively from the canonical `data.json` file produced by
the build pipeline. No SPA view may fetch remote data at runtime.

### 2. Deterministic Layout
SPA layouts must not shift, animate, or reflow unpredictably. All UI elements
must have fixed, spec‑defined positions and sizes.

### 3. Consistent Navigation Model
All SPA views must support:
- DPAD navigation (Up/Down/Left/Right)
- Deterministic focus order
- Escape/back behavior
- No scroll‑jank or focus loss

### 4. Shared Styling and Components
All SPA views must use:
- the global stylesheet (`my_tv_hub.css`)
- the shared header bar
- the shared footer/status area
- the shared iconography and asset rules (Section 7)

### 5. Popup Compatibility
All SPA views must support the popup chain defined in Section 5:
- Show Popup (P1)
- Season Popup (P2)
- Episode Popup (P3)
- Movie Popup (P4)
- Collection Popup (future phase)
- Person Popup (Removed; see Section 5.6)

### 6. Error Visibility
SPA views must surface errors from the `errors[]` array in `data.json` using the
global error viewer defined in Section 6.

### 7. Accessibility and Appearance Controls
SPA views must respect the global appearance and accessibility settings defined
in the Config View (Section 4.5).

---

## View Subsections

### SPA Views (inside index.html)
- **4.1 — Calendar View**  
- **4.2 — Shows View**  
- **4.3 — Movies View**  
- **4.4 — Live TV View**  
- **4.5 — Config View**  
- **4.6 — Explore View (future phase)**  
- **4.7 — Profiles View (future phase)**  
- **4.8 — Watchlist — Watched Filters (future phase)**  

### Standalone (non‑SPA) View
- **4.9 — Watchlist (Standalone Page)**  
  *(Replaces the deprecated `show.html` and uses the v3.3.5 Show Details UI.)*

Each subsection defines:
- required layout  
- required components  
- required navigation behavior (SPA views only)  
- required data bindings  
- required popup triggers (SPA views only)  
- required invariants  

---

## Implementation Notes

### SPA Views
- Implemented as static HTML fragments rendered inside `index.html`.
- All dynamic behavior must be implemented in deterministic JavaScript modules.
- SPA views must **not** include inline scripts or inline styles.
- SPA views must load the same core UI framework and rendering pipeline.

### Standalone Exception — Section 4.9
`watchlist.html` is intentionally allowed to use:
- inline CSS  
- inline JavaScript  
- standalone rendering  
- non‑SPA expand/collapse logic  

This exception is documented fully in Section 4.9.

---

## Deprecated legacy view: show.html

### Status
The legacy file `web/show.html` from the v3.3.5 architecture is deprecated and must no longer be used as a UI entry point.

### Replacement
`show.html` is replaced by the standalone Watchlist Page defined in Section 4.9.  
All show‑level detail rendering is now provided by the show/season/episode accordion structure in watchlist.html.

### Requirements
- The file `web/show.html` must remain present in the repository.
- It must contain a redirect to `watchlist.html`.
- No SPA view may reference `show.html`.
- No documentation may reference `show.html` except this deprecation notice.

### Redirect behavior
The file `web/show.html` must implement an immediate redirect to `watchlist.html`.

Redirect rules:
- Must work offline  
- Must work in file:// mode  
- Must not rely on SPA routing  
- Must not create back‑button history entries  
- Must not use external libraries  

The redirect file must include both:
- a `<meta http-equiv="refresh">` redirect  
- a `window.location.replace()` redirect  

This ensures compatibility across all browsers and hosting environments.
