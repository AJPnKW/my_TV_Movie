# Prompt Block - Windows Large Write Guardrail

Include this block in Codex prompts when artifacts may be large.

## Windows Write Constraint

This repo runs in Windows shells where command and patch payload size limits are restricted.

You must assume:
- single large writes are unsafe
- safe write size per operation is approximately 2 KB to 4 KB
- files larger than approximately 3 KB must be written in small batches
- files larger than approximately 20 KB require staged writes and validation

## Required Write Method

For large outputs:
1. create file
2. write first section
3. append remaining sections in small batches
4. validate file exists and is non-empty
5. log files created and validation results

## Do Not

- attempt a single large patch for a long file
- restart the whole task if a large write fails
- redo broad discovery when only writing failed

## Recovery Rule

If a write fails due to Windows command or patch size limits:
- keep completed work
- continue with smaller batched writes
- finish missing outputs only
- run final validation
