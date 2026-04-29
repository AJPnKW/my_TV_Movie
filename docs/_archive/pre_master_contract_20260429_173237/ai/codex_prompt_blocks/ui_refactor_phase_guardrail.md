# Prompt Block - UI Refactor Phase Guardrail

Use this when moving from approved UI audit and mockup work into implementation.

## Windows Write Constraint

This repo runs in Windows shells where command and patch payload size limits can break large writes.

Assume:
- single large writes are unsafe
- safe write size per operation is approximately 2 KB to 4 KB
- files larger than approximately 3 KB should be written in small batches
- validation must confirm files are non-empty and readable

## Implementation Rules

1. Do not redesign from scratch.
2. Use approved baseline artifacts and mockups as implementation source of truth.
3. Preserve existing modal IDs, data-* hooks, selector contracts, and event wiring in the first pass.
4. Standardize popup behavior before grid cards.
5. Centralize fallback logic before broad card swaps.
6. Keep page-specific dense or bespoke variants out of first-pass shared refactor unless explicitly approved.
7. Group interdependent changes into coherent batches.
8. Validate both structure and behavior after each grouped pass.

## Preferred Implementation Order

1. shared helpers
2. popup unification
3. fallback logic centralization
4. show and movie card unification
5. page-specific exception review
6. final validation

## Recovery Rule

If a write fails due to Windows command or patch size limits:
1. keep completed artifacts
2. continue with smaller batched writes
3. finish remaining outputs
4. validate before declaring completion
