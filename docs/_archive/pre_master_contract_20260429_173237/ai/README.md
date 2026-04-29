# Codex Support Files

Repository root:
C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie

This folder contains the reusable Codex operating guidance for this repo.

## Files and Purpose

| File | Purpose |
|---|---|
| `.ai_rules.md` | repo-level hard AI and Codex operating rules |
| `docs\ai\codex_operating_rules.md` | detailed Codex execution rules for this repo |
| `docs\ai\codex_prompt_blocks\windows_large_write_guardrail.md` | reusable write-size guardrail block |
| `docs\ai\codex_prompt_blocks\ui_audit_continuation_guardrail.md` | continuation guidance for partial audit and mockup tasks |
| `docs\ai\codex_prompt_blocks\ui_refactor_phase_guardrail.md` | implementation-phase guardrail block |
| `docs\ai\templates\codex_task_launch_template.md` | generic master task launch frame |
| `docs\ai\templates\codex_ui_implementation_master_prompt.md` | implementation-phase master prompt |
| `docs\ai\templates\codex_ui_continuation_master_prompt.md` | continuation-phase master prompt |

## Which file to use when

| Situation | File(s) to reference |
|---|---|
| any major Codex task | `.ai_rules.md`, `docs\ai\codex_operating_rules.md`, `docs\ai\templates\codex_task_launch_template.md` |
| large docs, reports, mockups, or matrices | add `docs\ai\codex_prompt_blocks\windows_large_write_guardrail.md` |
| partial audit or stalled mockup task | add `docs\ai\codex_prompt_blocks\ui_audit_continuation_guardrail.md` or `docs\ai\templates\codex_ui_continuation_master_prompt.md` |
| implementation phase for approved UI baseline work | add `docs\ai\codex_prompt_blocks\ui_refactor_phase_guardrail.md` or `docs\ai\templates\codex_ui_implementation_master_prompt.md` |

## Minimum recommended prompt references

For most future Codex sessions in this repo, reference:
1. `.ai_rules.md`
2. `docs\ai\codex_operating_rules.md`
3. one relevant prompt block or template for the task type

## Validation Rule

These files only have value if they are actually referenced in future Codex prompts.
