# Codex UI Implementation Master Prompt

Reference these repo files before executing:
- .ai_rules.md
- docs\ai\codex_operating_rules.md
- docs\ai\codex_prompt_blocks\windows_large_write_guardrail.md
- docs\ai\codex_prompt_blocks\ui_refactor_phase_guardrail.md

Use this master prompt when beginning implementation work after audit, mockups, and reuse mapping are approved.

## Prompt Frame

Continue work in:
C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie

Do not restart discovery.
Do not redo approved audit outputs.
Do not redesign from scratch.

Use these as source of truth:
- reports\ui_component_audit\ui_component_inventory.md
- reports\ui_component_audit\ui_component_matrix.csv
- reports\ui_component_audit\ui_component_drift_report.md
- reports\ui_component_audit\ui_component_dependency_map.md
- reports\ui_component_audit\ui_component_recommendations.md
- docs\ui_standardization\proposed_standard_components.md
- docs\ui_standardization\mockup_show_popup.html
- docs\ui_standardization\mockup_movie_popup.html
- docs\ui_standardization\mockup_show_card.html
- docs\ui_standardization\mockup_movie_card.html
- docs\ui_standardization\mockup_episode_card.html
- docs\ui_standardization\mockup_notes.md
- reports\ui_component_audit\ui_element_function_matrix.csv
- reports\ui_component_audit\baseline_candidate_elements.md
- reports\ui_component_audit\shared_vs_page_specific_map.md

Implementation objective:
- build shared internal helpers for approved baseline components
- unify popup behavior first
- centralize fallback logic next
- unify grid cards after popup stabilization
- preserve current IDs, selectors, data-* hooks, and event wiring in the first pass

Required execution order:
1. shared helpers
2. show popup unification
3. movie popup unification
4. fallback logic centralization
5. show card unification
6. movie card unification
7. validation

Required output discipline:
- group interdependent changes in coherent batches
- write large files in small batches
- log created and modified files
- validate all required outputs
- do not claim completion if validation is incomplete
