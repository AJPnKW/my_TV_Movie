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
| `docs/UI_GAP_ANALYSIS.md` | UI gaps and required fixes |
| `docs/PROJECT_STATUS_2026-03-16.md` | project snapshot |
| `docs/THREAD_RESTART_HANDOFF_2026-03-16.md` | thread restart context |
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
- fetches and prunes remotes without piping native git output into `Add-Content`
- records branch, head, remote URLs, working tree state, and ahead/behind status versus `origin/main` and `github/main` when present
- only runs `git pull --ff-only origin main` when the repo is on `main`, clean, and only behind `origin/main`
- writes per-repo logs under each repo's `logs\`
- writes a shared summary and zip bundle under `C:\Users\andrew\PROJECTS\GitHub\.ai_uploads`
