# **SECTION 1 — GLOBAL RULES**  
**Authoritative Specification — Full Scope (Including Future‑Phase Features)**  
**Document ID:** Section 1 — Global Rules  
**Version:** V0.00  
---
# **1.1 Purpose of This Section**
This section defines the **non‑negotiable, system‑wide rules** that govern the entire *my_TV_Movie (My TV Hub)* project.  
These rules apply to **all components**, **all files**, **all scripts**, **all workflows**, **all UI**, **all popups**, **all data**, and **all future‑phase features**.
These rules are **binding**, **permanent**, and **cannot be overridden** by any other section.
---
# **1.2 System‑Wide Non‑Negotiable Constraints**
The following constraints apply universally:
### **1.2.1 No Feature Drops**  
No feature that has ever existed, been specified, or been required may be removed, omitted, simplified, or replaced.
### **1.2.2 No Architectural Invention**  
No new architecture, routing model, framework, or structural pattern may be introduced beyond what is explicitly defined in the authoritative specification.
### **1.2.3 No Renaming**  
No renaming of files, fields, folders, functions, variables, components, or UI elements is permitted unless explicitly defined in the authoritative specification.
### **1.2.4 No Partial Files**  
All files must be complete, valid, and fully populated.  
No placeholder files, partial implementations, or incomplete structures are allowed.
### **1.2.5 No Destructive Writes**  
No script, workflow, or process may overwrite valid data with empty, partial, or invalid data.  
Atomic writes and validation gates are mandatory.
### **1.2.6 No Cross‑Contamination**  
Files must not contain logic, data, or responsibilities belonging to other files.  
Each file has a strict, isolated purpose.
### **1.2.7 No Simplification**  
No rule, behavior, or requirement may be simplified, approximated, or reduced.  
All requirements must be implemented exactly as specified.
### **1.2.8 No Missing Fields**  
All required fields in the data model must always be present, even if empty or null.
### **1.2.9 No Missing UI Elements**  
All required UI elements must always be rendered, even if data is missing.
### **1.2.10 No Missing Popups**  
All popups (Show, Season, Episode, Movie, Collection, Person) must always exist and be fully functional.
### **1.2.11 No Missing Filters**  
All filters must always exist and be fully functional.
### **1.2.12 No Missing Icon Strips**  
All icon strips must always be present and consistent across all views and popups.
### **1.2.13 No Missing Sizing Rules**  
Poster, backdrop, logo, and icon sizing rules must always be applied.
### **1.2.14 No Missing Metadata**  
All metadata fields must always be populated and displayed.
### **1.2.15 No Missing Workflow Guardrails**  
All workflows must enforce validation, fail‑fast behavior, and non‑destructive writes.
### **1.2.16 No Missing Script Validation**  
All scripts must validate schema, enforce invariants, and prevent invalid output.
### **1.2.17 No Missing Local Image Paths**  
All posters, backdrops, and logos must have valid local paths.
### **1.2.18 No Missing Streaming Link Rules**  
All streaming links must follow normalization rules and appear in all required locations.
---
# **1.3 Rendering Pipeline Rules**
The rendering pipeline is immutable:
```
Scripts → data.json → index.html → view renderers → popup renderers
```
### **1.3.1 No Runtime Fetching**  
All data must be precomputed.  
No live API calls are permitted in the UI.
### **1.3.2 No Dynamic Schema**  
The schema of `data.json` is fixed and must never change at runtime.
### **1.3.3 No Missing Data Guards**  
Views must not break when data is missing.  
Graceful fallback is mandatory.
### **1.3.4 No Silent Failures**  
All errors must be surfaced in the UI or logs.
---
# **1.4 Popup Chain Rules**
The popup chain is permanent and must never change:
```
Show → Season → Episode → Movie → (Collection, Person)
```
### **1.4.1 Mandatory Existence**  
All popups must exist and be fully functional.
### **1.4.2 Mandatory Navigation**  
Navigation between popups must always work in both directions.
### **1.4.3 Mandatory Scroll Trapping**  
Scroll must be trapped inside the popup.  
Background scrolling is forbidden.
### **1.4.4 Mandatory DPAD Behavior**  
DPAD focus must remain inside the popup until closed.
### **1.4.5 Mandatory Icon Strip**  
All popups must include the unified icon strip.
### **1.4.6 Mandatory Logos**  
All popups must include network/service logos when applicable.
---
# **1.5 UX & Accessibility Rules**
These rules apply universally:
### **1.5.1 DPAD‑First Navigation**  
The entire system must be fully navigable with a TV remote.
### **1.5.2 Predictable Focus Zones**  
Focus must move predictably and consistently.
### **1.5.3 Sticky Header Behavior**  
The global header must remain visible at all times.
### **1.5.4 Neurodivergent‑Friendly Layout**  
Spacing, contrast, and layout must follow neurodivergent‑friendly principles:
- no sudden layout shifts  
- no unpredictable animations  
- consistent spacing  
- consistent alignment  
- consistent sizing  
### **1.5.5 No Hidden Interactions**  
All interactions must be visible and discoverable.
---
# **1.6 Data Model Rules**
These rules apply to all data:
### **1.6.1 Mandatory Fields**  
All required fields must always exist.
### **1.6.2 Local Image Paths**  
All posters, backdrops, and logos must be stored locally.
### **1.6.3 Streaming Link Normalization**  
All streaming links must follow strict normalization rules.
### **1.6.4 Collection Metadata**  
Movies must include collection metadata when applicable.
### **1.6.5 TBA Episodes**  
TBA episodes must always be included.
### **1.6.6 No Empty Arrays**  
Empty arrays are forbidden unless explicitly allowed.
### **1.6.7 Metadata Block**  
`built_at`, counts, and version metadata must always be present.
---
# **1.7 Workflow Rules**
These rules apply to GitHub Actions:
### **1.7.1 Fail‑Fast Behavior**  
The workflow must fail if:
- shows == 0  
- movies == 0  
- schema invalid  
- metadata missing  
- images missing  
- scripts error  
### **1.7.2 No Silent Success**  
Workflows must never pass with invalid data.
### **1.7.3 Canonical File Naming**  
Canonical production files must follow these names:
- `data/inputs.json`
- `data/data.json`
- `data/watch_source_availability.json`
- `watchlist.txt` (local watch-state legacy helper only)
### **1.7.4 Atomic Writes**  
Workflows must write data atomically.
---
# **1.8 Script Rules**
These rules apply to all scripts:
### **1.8.1 Non‑Destructive Writes**  
Scripts must never overwrite valid data with empty or partial data.
### **1.8.2 Schema Validation**  
Scripts must validate schema before writing.
### **1.8.3 Local Image Caching**  
Scripts must download and store all images locally.
### **1.8.4 Streaming Link Normalization**  
Scripts must normalize all streaming links.
### **1.8.5 Collection Extraction**  
Scripts must extract collection metadata.
### **1.8.6 TBA Episode Handling**  
Scripts must include TBA episodes.
---
# **1.9 Versioning & Metadata Rules**
These rules apply to all files:
### **1.9.1 Mandatory File Headers**
Every file must include:
```
[VERSION]
[UPDATED]
[BUILD]
```
### **1.9.2 Monotonic Versioning**  
Version numbers must always increase.
### **1.9.3 No Reuse of Version Triples**  
Each version triple must be unique.
### **1.9.4 Inventory Tracking**  
All files must be tracked in the inventory.
---
# **1.10 File Integrity Rules**
### **1.10.1 No Corruption**  
Files must never be corrupted or partially written.
### **1.10.2 No Missing Files**  
All required files must always exist.
### **1.10.3 No Duplicate Files**  
Duplicate files are forbidden unless versioned.
### **1.10.4 No Orphan Files**  
All files must belong to a defined section.
---
# **1.11 Future‑Phase Binding Rules**
All future‑phase features are **binding immediately**:
- Explore tab  
- Profiles  
- Watched filters  
- Full EPG  
- Universal sort framework  
- Cross‑service sync  
- Advanced caching  
- Multi‑device profiles  
- Collection popup  
- Person popup  
- AI‑powered recommendations (if included)  
These features must be included in:
- architecture  
- data model  
- UI  
- popups  
- scripts  
- workflows  
- assets  
- UX  
- invariants  
They are not optional and not deferred.
---
# **1.12 Global Invariants**
The following rules must never change:
- SPA architecture  
- popup chain  
- rendering pipeline  
- data.json schema  
- icon strip  
- logo mapping  
- DPAD rules  
- metadata rules  
- versioning rules  
- file integrity rules  
- no feature drops  
- no architectural invention  
- no renaming  
- no partial files  
These invariants are permanent.
---
# **1.13 End of Section 1 — Global Rules**
