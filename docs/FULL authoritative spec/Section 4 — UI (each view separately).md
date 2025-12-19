# Section 4.0 — UI (Each View Separately)

## Purpose
This section defines the global UI requirements for My TV Hub and serves as the
parent document for all individual UI view specifications. Each view is defined
in its own subsection (4.1–4.8), but all views must comply with the global rules
and invariants described here.

The UI is a deterministic, non‑reactive, non‑fetching interface that renders
exclusively from the locally‑built `data.json` file. All views must follow the
same rendering pipeline, navigation model, and interaction rules.

## Global UI Principles
All UI views must adhere to the following principles:

1. **Local‑Only Rendering**  
   No view may fetch remote data at runtime. All content must come from the
   canonical `data.json` file produced by the build pipeline.

2. **Deterministic Layout**  
   Layouts must not shift, animate, or reflow unpredictably. All UI elements
   must have fixed, spec‑defined positions and sizes.

3. **Consistent Navigation Model**  
   All views must support:
   - DPAD navigation (Up/Down/Left/Right)
   - Deterministic focus order
   - Escape/back behavior
   - No scroll‑jank or focus loss

4. **Shared Styling and Components**  
   All views must use:
   - the global stylesheet (`my_tv_hub.css`)
   - the shared header bar
   - the shared footer/status area
   - the shared iconography and asset rules (Section 7)

5. **Popup Compatibility**  
   All views must support the popup chain defined in Section 5:
   - Show Popup (P1)
   - Season Popup (P2)
   - Episode Popup (P3)
   - Movie Popup (P4)
   - Collection Popup (future phase)
   - Person Popup (Removed; see Section 5.6)

6. **Error Visibility**  
   All views must surface errors from the `errors[]` array in `data.json` using
   the global error viewer defined in Section 6.

7. **Accessibility and Appearance Controls**  
   All views must respect the global appearance and accessibility settings
   defined in the Config View (Section 4.5).

## View Subsections
Each view has its own dedicated specification:

- **4.1 — Calendar View**  
- **4.2 — Shows View**  
- **4.3 — Movies View**  
- **4.4 — Live TV View**  
- **4.5 — Config View**  
- **4.6 — Explore View (future phase)**  
- **4.7 — Profiles View (future phase)**  
- **4.8 — Watchlist — Watched Filters (future phase)**

Each subsection defines:
- required layout
- required components
- required navigation behavior
- required data bindings
- required popup triggers
- required invariants

## Implementation Notes
- All views must be implemented as static HTML files.
- All dynamic behavior must be implemented in deterministic JavaScript modules.
- No view may include inline scripts or inline styles.
- All views must load the same core UI framework and rendering pipeline.

## Versioning
This section is versioned according to the global rules in Section 10. Any
changes to UI structure, navigation, or rendering must increment the appropriate
version fields.

