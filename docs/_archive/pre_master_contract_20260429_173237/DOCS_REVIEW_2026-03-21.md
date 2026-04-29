# Docs Review — 2026-03-21

## Scope reviewed
Uploaded docs bundle containing 88 files.

## Bottom line
| Finding | Result |
|---|---|
| The docs tree has useful content | Yes |
| The docs tree also has noise and misfiled artifacts | Yes |
| Existing availability-status docs already exist and should be kept | Yes |
| New availability docs should not be re-added at different paths | Yes |
| Root `docs/README.md` is invalid and needed replacement | Yes |

## Keep as-is
| File / Area | Reason |
|---|---|
| `docs/ARCHITECTURE.md` | valid architecture contract |
| `docs/ARCHITECTURE_LOG.md` | valid historical/supporting log |
| `docs/PROJECT_STATUS_2026-03-16.md` | useful point-in-time status |
| `docs/THREAD_RESTART_HANDOFF_2026-03-16.md` | useful restart context |
| `docs/UI_COMPONENTS.md` | small but valid contract |
| `docs/UI_GAP_ANALYSIS.md` | small but valid gap list |
| `docs/ai/` | valid AI/Codex support materials |
| `docs/config/config.md` | valid feature doc |
| `docs/ui_standardization/` | valid UI standardization set |
| `docs/spec/Section *` files | keep; they are the active structured spec body |
| `docs/design/data/impact/implementation/testing/ui/workflows/availability_*` | keep; already aligned |

## Keep but index better
| File / Area | Action |
|---|---|
| `docs/spec/` | add `docs/spec/README.md` |
| `docs/` root | replace broken `README.md` with a real index |

## Move to archive
| File | Why |
|---|---|
| `docs/doc_folder-.md-files.zip` | source-drop artifact, not active documentation |
| `docs/actual text of the ChatGPT responsesQ1-Q5.txt` | conversation export, not active spec/design |
| `docs/spec/..NOTES for the FULL authoritative spec+plan.md` | duplicate-style working-note filename with leading punctuation |
| `docs/spec/my_TV_Movies- authoritative spec.tws` | binary workspace artifact, not primary active markdown spec |

## Rename / normalize
| Current | Target |
|---|---|
| `docs/spec/archived,Section 5.6 #U2014 Person Popup (future phase).md` | `docs/spec/archive/Section 5.6 - Person Popup (future phase).md` |
| `docs/spec/Section 0 #U2014 Index.md` | `docs/spec/Section 0 - Index.md` |
| `docs/spec/Section 1 #U2014 Global Rules.md` | `docs/spec/Section 1 - Global Rules.md` |
| `docs/spec/Section 2 #U2014 Architecture.md` | `docs/spec/Section 2 - Architecture.md` |
| `docs/spec/Section 3 #U2014 Data Model.md` | `docs/spec/Section 3 - Data Model.md` |
| `docs/spec/Section 4 #U2014 UI (each view separately).md` | `docs/spec/Section 4 - UI (each view separately).md` |
| `docs/spec/Section 5 #U2014 Popups.md` | `docs/spec/Section 5 - Popups.md` |
| `docs/spec/Section 6 #U2014 UX.md` | `docs/spec/Section 6 - UX.md` |
| `docs/spec/Section 7 #U2014 Assets.md` | `docs/spec/Section 7 - Assets.md` |
| `docs/spec/Section 8 #U2014 Scripts.md` | `docs/spec/Section 8 - Scripts.md` |
| `docs/spec/Section 9 #U2014 Workflow.md` | `docs/spec/Section 9 - Workflow.md` |
| `docs/spec/Section 10 #U2014 Versioning.md` | `docs/spec/Section 10 - Versioning.md` |
| `docs/spec/Section 11 #U2014 Errors.md` | `docs/spec/Section 11 - Errors.md` |
| `docs/spec/Section 12 #U2014 Future#U2011Phase.md` | `docs/spec/Section 12 - Future-Phase.md` |
| `docs/spec/Section 13 #U2014 Invariants.md` | `docs/spec/Section 13 - Invariants.md` |

## Review later, do not auto-delete
| File | Reason |
|---|---|
| `docs/spec/NOTES for the FULL authoritative spec+plan.md` | may still contain useful working notes |
| `docs/spec/FULL outline of the authoritative specV0.01.md` | likely superseded but may still be useful |
| `docs/spec/SPEC Overide-Notes.txt` | likely useful during spec convergence |
| `docs/spec/Mandatory-PIPELINE SOLUTION.txt` | likely useful for pipeline constraints |
| `docs/Network + Service Logo Spec.md` | keep pending broader asset review |
| `docs/TMDB_fields.txt` | keep pending data-contract merge |
| `docs/Web Icon Image Inventory (usable formats & variants).txt` | keep pending asset merge |
