
You’re asking for:
✔️ A design for the FULL authoritative spec,
✔️ Including all future‑phase features,
✔️ Broken into clean, logical sections,
✔️ So we can work through each section independently,
✔️ Without overwhelming a single prompt or losing context.
This is the right approach. This is how large systems are documented professionally. And this will give us the clean, complete, authoritative spec you want to attach to the new thread.
Below is the section architecture for the FULL spec — the exact structure we will use to build it piece by piece.
⭐ How we will work through this
We will build the spec section by section, in this order:
Section 1 — Global Rules
Section 2 — Architecture
Section 3 — Data Model
Section 4 — UI (each view separately)
Section 5 — Popups
Section 6 — UX
Section 7 — Assets
Section 8 — Scripts
Section 9 — Workflow
Section 10 — Versioning
Section 11 — Errors
Section 12 — Future‑Phase
Section 13 — Invariants
Each section will be:
complete
authoritative
non‑contradictory
aligned with all rules
aligned with all extracted details
aligned with your expectations
You can store each section as a separate .md file in your GitHub folder.
⭐ Your next step
Tell me which section you want to start with:
Section 1 — Global Rules
Section 2 — Architecture
Section 3 — Data Model
or any other section
Once you choose, I’ll generate that section in full.
-
-
-
✅ THE MASTER PROMPT (copy/paste this for every section)
Use this exact template. Replace {SECTION_NUMBER} and {SECTION_NAME} with the section you want.

You will now generate the FULL AUTHORITATIVE SPECIFICATION for:

SECTION {SECTION_NUMBER} — {SECTION_NAME}

This section must be:

• complete  
• authoritative  
• non‑contradictory  
• aligned with ALL rules in this project  
• aligned with ALL extracted details (Q1–Q5)  
• aligned with ALL global constraints  
• aligned with the strict development protocol  
• aligned with the rendering pipeline  
• aligned with the popup chain  
• aligned with the UX rules  
• aligned with the data model  
• aligned with the workflow  
• aligned with the versioning/metadata rules  
• aligned with the file integrity rules  
• aligned with the “no feature drops / no invention / no renaming” rules  
• aligned with the intended FINAL design (FULL scope, including future‑phase features)

REQUIREMENTS FOR THIS OUTPUT:

1. This section must stand alone as a complete document.
2. It must NOT reference other sections implicitly; restate anything needed.
3. It must NOT simplify or summarize.
4. It must NOT omit any requirement, rule, constraint, or behavior.
5. It must NOT invent architecture or features.
6. It must include ALL future‑phase features relevant to this section.
7. It must be structured, deterministic, and unambiguous.
8. It must be formatted in clean Markdown.
9. It must be suitable for saving as:
   “Section {SECTION_NUMBER} — {SECTION_NAME}_V0.00.md”
10. It must be long enough to be authoritative, but not padded with filler.

OUTPUT ONLY THE SPECIFICATION.
Do NOT generate code.
Do NOT generate commentary.
Do NOT generate instructions.
Do NOT generate summaries.

-
-
-
✅ SECTION INVOCATION LINES (copy/paste these into the template)
You simply replace the placeholders in the master prompt with these.

Section 0 — Index
Code
SECTION_NUMBER = 0
SECTION_NAME = Index
Section 1 — Global Rules
Code
SECTION_NUMBER = 1
SECTION_NAME = Global Rules
Section 2 — Architecture
Code
SECTION_NUMBER = 2
SECTION_NAME = Architecture
Section 3 — Data Model
Code
SECTION_NUMBER = 3
SECTION_NAME = Data Model
Section 4 — UI (each view separately)
You will run this prompt once per view:

Calendar View

Shows View

Movies View

Live TV View

Config View

Explore View (future phase)

Profiles View (future phase)

Watchlist / Watched Filters (future phase)

Example:

Code
SECTION_NUMBER = 4.1
SECTION_NAME = Calendar View
Section 5 — Popups
Run once per popup:

Show Popup (P1)

Season Popup (P2)

Episode Popup (P3)

Movie Popup (P4)

Collection Popup (future phase)

Person Popup (future phase)

Example:

Code
SECTION_NUMBER = 5.1
SECTION_NAME = Show Popup (P1)
Section 6 — UX
Code
SECTION_NUMBER = 6
SECTION_NAME = UX & Accessibility
Section 7 — Assets
Code
SECTION_NUMBER = 7
SECTION_NAME = Assets & Media
Section 8 — Scripts
Code
SECTION_NUMBER = 8
SECTION_NAME = Scripts (TMDB, Trakt, Image Caching)
Section 9 — Workflow
Code
SECTION_NUMBER = 9
SECTION_NAME = Workflow (GitHub Actions)
Section 10 — Versioning
Code
SECTION_NUMBER = 10
SECTION_NAME = Versioning & Metadata
Section 11 — Errors
Code
SECTION_NUMBER = 11
SECTION_NAME = Error Handling & Diagnostics
Section 12 — Future‑Phase
Code
SECTION_NUMBER = 12
SECTION_NAME = Future‑Phase Features
Section 13 — Invariants
Code
SECTION_NUMBER = 13
SECTION_NAME = Invariants (Must Never Change)
✅ HOW YOU USE THIS
Step 1
Pick a section folder (e.g., “Section 1 — Global Rules”).

Step 2
Copy the master prompt.

Step 3
Insert the section number and name.

Step 4
Paste into ChatGPT.

Step 5
Save the output as:

Code
Section {NUMBER} — {NAME}_V0.00.md
Step 6
Run your versioning script to create V0.01, V0.02, etc.

⭐ You now have a deterministic, repeatable, zero‑ambiguity workflow
This is exactly the kind of structured, modular, neurodivergent‑friendly system you’ve been trying to build for months.

You’ve already set up:

the folder structure

the versioning script

the inventory system

the governance rules

Now you have the ultimate prompt to generate each section cleanly.

If you want, I can also generate:

a README.md for the FULL authoritative spec folder

a governance document describing the spec workflow

a script to auto‑assemble all sections into a single master spec

Just say the word.


a tweak as 
4.5.6 List File Editors
This section allows editing of:
tv_list.txt
movies_list.txt
live_tv_list.txt
watchlist.txt formerly show_pages.txt
