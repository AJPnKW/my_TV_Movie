# Docs Information Architecture

## Outcome
This is the target structure for the repo documentation tree.

## Target structure
| Path | Keep | Notes |
|---|---:|---|
| `docs/` root | Yes | only indexes, status, cross-cutting contracts |
| `docs/architecture/` | Yes | architecture baselines per feature/system |
| `docs/data/` | Yes | data contracts and schemas |
| `docs/design/` | Yes | solution design docs |
| `docs/impact/` | Yes | impact analysis |
| `docs/implementation/` | Yes | implementation plans |
| `docs/testing/` | Yes | QA and validation docs |
| `docs/ui/` | Yes | UI integration notes |
| `docs/workflows/` | Yes | workflow notes |
| `docs/spec/` | Yes | authoritative spec source set |
| `docs/spec/archive/` | Yes | spec items no longer active |
| `docs/ui_standardization/` | Yes | contracts, mockups, preserved UI baseline |
| `docs/ai/` | Yes | Codex / AI handoff docs |
| `docs/config/` | Yes | config-specific docs |
| `docs/_patch_notes/` | Yes | patch QA notes |
| `docs/_archive/` | Yes | exported noise, chat dumps, source drops, misplaced binaries |

## Root doc rules
| Rule | Decision |
|---|---|
| root docs should be few | Yes |
| feature docs belong in functional folders | Yes |
| exports, zips, and chat dumps do not belong in active root | Yes |
| filename normalization should remove leading punctuation and broken encoded separators where safe | Yes |

## Naming rules
| Pattern | Use |
|---|---|
| `README.md` | folder index |
| `*_design.md` | solution design |
| `*_architecture.md` | architecture baseline |
| `*_data_contract.md` | data contract |
| `*_impact_matrix.md` | impact analysis |
| `*_delivery_plan.md` | implementation plan |
| `*_qa_and_validation.md` | QA contract |
