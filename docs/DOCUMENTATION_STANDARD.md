# Documentation Standard

## Purpose
This file defines how documentation is maintained for `my_TV_Movie` so ChatGPT, Codex, and future work do not create conflicting instructions.

## Source-of-Truth Rules

| Domain | Owner |
|---|---|
| UI layout, card behavior, icons, header, modal focus | `docs/UI_COMPONENTS.md` |
| Data model, runtime architecture, asset pipeline, Trakt architecture | `docs/ARCHITECTURE.md` |
| Documentation governance and ownership | `docs/DOCUMENTATION_STANDARD.md` |
| Historical change log | `docs/ARCHITECTURE_LOG.md` |

## Prohibited Patterns

- Current UI rules duplicated in architecture docs.
- Current architecture rules duplicated in reports.
- Patch reports treated as source of truth.
- New docs created for the same concept without linking to the canonical owner.
- Placeholder docs or scripts.

## Required Change Flow

1. Documentation contract is updated first.
2. Codex implements code against that contract.
3. Validation is run.
4. Reports record evidence.
5. Commit only intentional files.

## Source-of-Truth Matrix

| Design / Function Area | Canonical File | Supporting Docs | Compatibility Shim | Validation |
|---|---|---|---|---|
| Action icons | `web/js/action_bar.js` | `docs/UI_COMPONENTS.md` | `web/js/ui_contract_fix.js` only if still needed | `scripts/validate_runtime.ps1` |
| Card layout | `web/css/main_app.css` and shared card renderer | `docs/UI_COMPONENTS.md` | `web/css/ui_contract_fix.css` only temporary | Visual + validator |
| Watch state | `web/js/watch_state_manager.js` | `docs/ARCHITECTURE.md` | none expected | state key audit |
| Popup/watch sources | `web/js/trailer_watch_popup_fix.js` | `docs/ARCHITECTURE.md` | none expected | popup smoke test |
| Calendar/dashboard data | `web/js/data_loader.js`, `web/js/app_runtime.js` | `docs/ARCHITECTURE.md` | none expected | no silent truncation |
| Asset optimization | `scripts/optimize_runtime_assets.py` | `docs/ARCHITECTURE.md` | none | asset report |
| Header/navigation | `web/css/main_app.css`, page shell | `docs/UI_COMPONENTS.md` | none expected | responsive QA |
| Modal/D-pad focus | `web/js/chrometv_focus.js` | `docs/UI_COMPONENTS.md` | none expected | keyboard/D-pad test |
| Documentation process | `docs/DOCUMENTATION_STANDARD.md` | `docs/README.md` | none | docs consistency check |

## Cleanup Rules

| Item Type | Decision |
|---|---|
| Overlay patch folders | Delete if obsolete; archive only when evidence is needed |
| One-off apply scripts | Delete when superseded |
| Duplicate validators | Consolidate into `scripts/validate_runtime.ps1` |
| Logs | Keep latest evidence; do not treat as design |
| Backups | Do not commit unless needed for reproducibility |
| Original assets | Preserve `assets/original_downloads/` |

## Forbidden Active Drift Markers

The active repo must not use these as current behavior:

```text
▶
🎬
📏
💛
⭐ rating icon
.slice(0,3)
placeholder
Apply overlay
```

Historical/archive references are allowed only when clearly historical.
