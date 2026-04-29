# Prompt Block - UI Audit Continuation Guardrail

Use this when an audit or mockup task was partially completed.

## Windows Write Constraint

This repo runs in Windows shells where command and patch payload size limits can break large writes.

Assume:
- single large writes are unsafe
- safe write size per operation is approximately 2 KB to 4 KB
- files larger than approximately 3 KB should be written in small batches
- validation must confirm files are non-empty and readable

## Continuation Rules

1. Treat existing completed artifacts as source of truth unless empty or corrupted.
2. Do not restart the audit.
3. Do not redo broad repo discovery.
4. Complete only the missing required artifacts.
5. Write large files in small batches.
6. Validate all required outputs at the end.
7. Return final handoff only after validation succeeds.

## Required Output Discipline

- preserve completed analysis
- complete missing docs, mockups, and logs
- do not refactor production pages in continuation mode
- explicitly list created files and validated files

## Recovery Rule

If a write fails due to Windows command or patch size limits:
1. keep completed artifacts
2. continue with smaller batched writes
3. finish only missing outputs
4. run final validation
