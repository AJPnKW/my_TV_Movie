# Docs Cleanup Phase 2 Overlay — 2026-03-21

## Outcome
This overlay is based on the **live repo inventory** from the completed cleanup run.

## What changed from phase 1
- rename logic now matches the **actual filenames in your repo**
- uses the real unicode dash filenames found in `docs/spec/`
- archives the actual `archived,Section 5.6 — Person Popup (future phase).md`
- keeps existing availability-status docs in place
- does not guess or rebuild docs that already exist

## Apply
Run from repo root:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\apply_docs_cleanup_phase2.ps1
```
