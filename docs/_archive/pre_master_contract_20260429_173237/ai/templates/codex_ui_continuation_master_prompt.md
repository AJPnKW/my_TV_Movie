# Codex UI Continuation Master Prompt

Reference these repo files before executing:
- .ai_rules.md
- docs\ai\codex_operating_rules.md
- docs\ai\codex_prompt_blocks\windows_large_write_guardrail.md
- docs\ai\codex_prompt_blocks\ui_audit_continuation_guardrail.md

Use this master prompt when a prior Codex task partially completed and needs safe continuation.

## Prompt Frame

Continue work in:
C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie

Do not restart the task.
Do not redo broad discovery.
Treat completed artifacts as source of truth unless empty or corrupted.

Required continuation behavior:
1. identify completed required artifacts
2. identify only missing required artifacts
3. write remaining outputs in small batches
4. validate all required outputs
5. return final handoff only after validation succeeds

Required recovery behavior:
- if a large write fails, keep completed work
- continue using smaller batched writes
- finish missing outputs only
- avoid restarting from scratch

Required output discipline:
- list completed preserved artifacts
- list created continuation artifacts
- list validated files
- log execution and summary
