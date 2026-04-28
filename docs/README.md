# my_TV_Movie — Documentation Index

## Purpose
This `docs` tree holds the current design, architecture, implementation, UI, workflow, AI-operating, and cleanup documentation for the repo.

## Current top-level doc groups
| Path | Purpose |
|---|---|
| `docs/architecture/` | feature or system architecture baselines |
| `docs/data/` | data contracts and schemas |
| `docs/design/` | feature solution design docs |
| `docs/impact/` | system impact analysis |
| `docs/implementation/` | delivery and implementation plans |
| `docs/testing/` | QA and validation contracts |
| `docs/ui/` | UI integration notes |
| `docs/workflows/` | workflow design notes |
| `docs/spec/` | authoritative spec workstream |
| `docs/ui_standardization/` | component standardization and mockups |
| `docs/ai/` | Codex / AI operating docs and prompt blocks |
| `docs/config/` | config-page reference docs |
| `docs/_patch_notes/` | prior patch/QA notes |
| `docs/_archive/` | archived noise, exports, and superseded working notes |

## Current high-value docs
| File | Role |
|---|---|
| `docs/ARCHITECTURE.md` | current architecture contract |
| `docs/ARCHITECTURE_LOG.md` | architecture change/history log |
| `docs/UI_COMPONENTS.md` | UI component contract |
| `docs/DOCUMENTATION_STANDARD.md` | documentation ownership and source-of-truth matrix |
| `docs/UI_GAP_ANALYSIS.md` | UI gaps and required fixes |
| `docs/PROJECT_STATUS_2026-03-16.md` | historical project snapshot |
| `docs/THREAD_RESTART_HANDOFF_2026-03-16.md` | historical thread restart context |
| `docs/spec/README.md` | authoritative spec index |
| `docs/DOCS_INFORMATION_ARCHITECTURE.md` | docs structure baseline |
| `docs/DOCS_REVIEW_2026-03-21.md` | review and disposition report |
| `docs/DOCS_CLEANUP_PLAN_2026-03-21.md` | cleanup actions and script scope |

## Availability-status docs already present
These are already in the correct functional folders and should stay there:
- `docs/design/availability_status_solution_design.md`
- `docs/architecture/availability_status_baseline_architecture.md`
- `docs/data/availability_status_data_contract.md`
- `docs/impact/availability_status_system_impact_matrix.md`
- `docs/implementation/availability_status_end_to_end_delivery_plan.md`
- `docs/testing/availability_status_qa_and_validation.md`
- `docs/ui/availability_status_ui_integration.md`
- `docs/workflows/availability_status_workflow_design.md`

## Rule
Do not add new docs at root unless they are repo-wide index, governance, status, or cross-cutting contracts.

## Repo sync preflight
Use `scripts/repo_sync_pre_codex_v2.ps1` before multi-tab Codex work that depends on trusted repo state.

The script:
- validates both configured repo roots and `.git` presence
- verifies `git` is available, then fetches and prunes remotes without piping native git output into `Add-Content`
- records branch, head, remote fetch/push URLs, working tree state, fetch result, and ahead/behind status versus `origin/main` and `github/main` when present
- only runs `git pull --ff-only origin main` when the repo is on `main`, clean, and only behind `origin/main`
- preserves dirty or diverged repos as-is and writes an explicit recommendation instead of failing early
- writes per-repo logs under each repo's `logs\`
- writes a shared summary and zip bundle under `C:\Users\andrew\PROJECTS\GitHub\.ai_uploads`

## Current UI/runtime note
- `web/js/app_runtime.js` keeps the Inputs Editor route visible, removes dashboard silent per-day truncation, keeps dashboard/calendar episode completeness aligned, and locks focus to the active popup.
- `web/css/main_app.css` is the live styling surface for the repaired calendar month/list layouts, card overlay spacing, and modal readability changes.
- Canonical UI/runtime owners are `web/js/action_bar.js`, `web/js/watch_state_manager.js`, `web/js/data_loader.js`, `web/js/trailer_watch_popup_fix.js`, and `web/css/main_app.css`.
- Compatibility shims still loaded by the focus bootstrap are `web/js/runtime_render_fix.js`, `web/js/ui_contract_fix.js`, `web/css/runtime_layout_fix.css`, and `web/css/ui_contract_fix.css`.
- Current action icon order is popcorn, watch, ticket, double-heart, compact numeric rating.
- Historical docs may mention old bookmark, single-heart, star, play, ruler, or percent-rating treatments; current docs must use `docs/UI_COMPONENTS.md` and `docs/DOCUMENTATION_STANDARD.md`.
- Removed drift artifacts include root overlay apply docs, `overlay/`, `overlay_patch/`, old apply scripts, overlay validation, and abandoned overlay reports.
- Canonical local launcher: `tools/run_local_servers.bat`. It starts/reuses the static app server on `8000` and the Inputs Editor API server on `8787`; root `run_server.bat` delegates to it for compatibility.
- Standard validation command: `powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1`.
