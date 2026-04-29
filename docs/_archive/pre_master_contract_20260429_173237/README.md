# My_TV_Movie — Documentation Index

## Purpose
This repository uses a single-source-of-truth documentation model.

- ChatGPT project thread defines documentation contracts.
- Codex implements code strictly against the documented contracts.
- Reports and archived material are evidence only, not active source of truth.

## Active Documentation

| Area | File | Status |
|---|---|---|
| UI contract | `docs/UI_COMPONENTS.md` | Primary |
| System architecture | `docs/ARCHITECTURE.md` | Primary |
| Documentation rules | `docs/DOCUMENTATION_STANDARD.md` | Primary |
| Architecture history | `docs/ARCHITECTURE_LOG.md` | Historical log |

## Historical / Evidence Only

| Location | Role |
|---|---|
| `docs/_archive/` | Superseded historical material |
| `docs/_patch_notes/` | Prior patch notes and QA notes |
| `reports/` | Run evidence, validation, generated reports |

## Rules

1. Every behavior has one documentation owner.
2. UI behavior lives in `docs/UI_COMPONENTS.md`.
3. Architecture and data flow live in `docs/ARCHITECTURE.md`.
4. Documentation governance lives in `docs/DOCUMENTATION_STANDARD.md`.
5. Reports/logs do not define current behavior.

## Validation

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/validate_runtime.ps1
```
