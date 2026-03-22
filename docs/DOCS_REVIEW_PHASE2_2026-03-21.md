# Docs Review Phase 2 — Live Repo Based

## Bottom line
The first cleanup run succeeded, but the rename map did not match the real filenames in `docs/spec/`.

## Live repo findings
| Area | Result |
|---|---|
| Existing availability-status docs | already present and correctly placed |
| Root `docs/README.md` | already replaced and valid |
| `docs/spec/README.md` | already added and valid |
| Noisy artifacts | mostly archived successfully |
| Active spec section filenames | use real unicode dash `—`, not `#U2014` |
| Archived popup file | still present at live path and should be moved |

## Keep
| File group | Decision |
|---|---|
| `docs/architecture/availability_status_baseline_architecture.md` | keep |
| `docs/data/availability_status_data_contract.md` | keep |
| `docs/design/availability_status_solution_design.md` | keep |
| `docs/impact/availability_status_system_impact_matrix.md` | keep |
| `docs/implementation/availability_status_end_to_end_delivery_plan.md` | keep |
| `docs/testing/availability_status_qa_and_validation.md` | keep |
| `docs/ui/availability_status_ui_integration.md` | keep |
| `docs/workflows/availability_status_workflow_design.md` | keep |
| `docs/ai/*` | keep |
| `docs/ui_standardization/*` | keep |
| `docs/spec/Section *` | keep |

## Move to archive now
| Current path | Target path |
|---|---|
| `docs/spec/archived,Section 5.6 — Person Popup (future phase).md` | `docs/spec/archive/Section 5.6 - Person Popup (future phase).md` |

## Normalize now
| Current | Target |
|---|---|
| `docs/spec/Section 0 — Index.md` | `docs/spec/Section 0 - Index.md` |
| `docs/spec/Section 1 — Global Rules.md` | `docs/spec/Section 1 - Global Rules.md` |
| `docs/spec/Section 2 — Architecture.md` | `docs/spec/Section 2 - Architecture.md` |
| `docs/spec/Section 3 — Data Model.md` | `docs/spec/Section 3 - Data Model.md` |
| `docs/spec/Section 4 — UI (each view separately).md` | `docs/spec/Section 4 - UI (each view separately).md` |
| `docs/spec/Section 4.1 — Calendar View.md` | `docs/spec/Section 4.1 - Calendar View.md` |
| `docs/spec/Section 4.2 — Shows View.md` | `docs/spec/Section 4.2 - Shows View.md` |
| `docs/spec/Section 4.3 — Movies View.md` | `docs/spec/Section 4.3 - Movies View.md` |
| `docs/spec/Section 4.4 — Live TV View.md` | `docs/spec/Section 4.4 - Live TV View.md` |
| `docs/spec/Section 4.5 — Config View.md` | `docs/spec/Section 4.5 - Config View.md` |
| `docs/spec/Section 4.6 — Explore View (future phase).md` | `docs/spec/Section 4.6 - Explore View (future phase).md` |
| `docs/spec/Section 4.7 — Profiles View (future phase).md` | `docs/spec/Section 4.7 - Profiles View (future phase).md` |
| `docs/spec/Section 4.8 — Watchlist - Watched Filters (future phase).md` | `docs/spec/Section 4.8 - Watchlist - Watched Filters (future phase).md` |
| `docs/spec/Section 4.9 — Watchlist (Standalone Page).md` | `docs/spec/Section 4.9 - Watchlist (Standalone Page).md` |
| `docs/spec/Section 5 — Popups.md` | `docs/spec/Section 5 - Popups.md` |
| `docs/spec/Section 5.1 — Show Popup (P1).md` | `docs/spec/Section 5.1 - Show Popup (P1).md` |
| `docs/spec/Section 5.2 — Season Popup (P2).md` | `docs/spec/Section 5.2 - Season Popup (P2).md` |
| `docs/spec/Section 5.3 — Episode Popup (P3).md` | `docs/spec/Section 5.3 - Episode Popup (P3).md` |
| `docs/spec/Section 5.4 — Movie Popup (P4).md` | `docs/spec/Section 5.4 - Movie Popup (P4).md` |
| `docs/spec/Section 5.5 — Collection Popup (future phase).md` | `docs/spec/Section 5.5 - Collection Popup (future phase).md` |
| `docs/spec/Section 6 — UX.md` | `docs/spec/Section 6 - UX.md` |
| `docs/spec/Section 7 — Assets.md` | `docs/spec/Section 7 - Assets.md` |
| `docs/spec/Section 8 — Scripts.md` | `docs/spec/Section 8 - Scripts.md` |
| `docs/spec/Section 9 — Workflow.md` | `docs/spec/Section 9 - Workflow.md` |
| `docs/spec/Section 10 — Versioning.md` | `docs/spec/Section 10 - Versioning.md` |
| `docs/spec/Section 11 — Errors.md` | `docs/spec/Section 11 - Errors.md` |
| `docs/spec/Section 12 — Future‑Phase.md` | `docs/spec/Section 12 - Future-Phase.md` |
| `docs/spec/Section 13 — Invariants.md` | `docs/spec/Section 13 - Invariants.md` |

## Review later, do not auto-move
| File | Reason |
|---|---|
| `docs/calendar_view.md` | may still map to a real page contract |
| `docs/show_card.md` | tiny but may be intentionally direct |
| `docs/movie_card.md` | tiny but may be intentionally direct |
| `docs/episode_card.md` | tiny but may be intentionally direct |
| `docs/show_popup.md` | tiny but may be intentionally direct |
| `docs/movie_popup.md` | may still be referenced |
| `docs/focus_navigation_tv.md` | real UX concern doc |
| `docs/TMDB_fields.txt` | useful data reference |
| `docs/Network + Service Logo Spec.md` | asset/design reference |
| `docs/Web Icon Image Inventory (usable formats & variants).txt` | asset inventory |
| `docs/spec/Section 99 — WIP, Change, enhancement and SEC changes and consideration and updates needed.txt` | keep until spec convergence is complete |
