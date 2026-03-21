FILE: reports/ui_component_audit/editor_canonical_decision.md
VERSION: v1.0
UPDATED: 2026-03-15T03:57:02Z
CHANGE NOTES:
- Created canonical editor decision for current local workflow.
- Determined surviving editor, retired editor, and true curation source of truth.
- Documented why the current alternate editor appears broken.

# Canonical Editor Decision

## Decision

The canonical editor is:

- `web/inputs_editor.html`

The canonical persistence and curation source of truth is:

- `data/inputs.json`

The server/runtime that supports the canonical editor is:

- `tools/inputs_editor/inputs_editor_server.py`

## Surviving Path

The surviving editor workflow is:

```text
web/inputs_editor.html
  -> /api/inputs
  -> tools/inputs_editor/inputs_editor_server.py
  -> data/inputs.json
  -> pipeline scripts
  -> data/data.json
```

This matches the active pipeline and the current local editing workflow.

## Retired Path

The editor that should retire is:

- `web/library_editor.html`

Reasons:

- it is built around `data/inputs_parsed.json`
- it advertises `inputs_parsed.json` as the only persisted target
- it exports JSON rather than updating the active canonical file
- `data/inputs_parsed.json` is not present in the current repo state
- its model no longer matches the pipeline source of truth

## Why Local Behavior Appears Broken

The repo still carries two historical editing models:

1. older text-list/parsed-json workflow
2. current direct `inputs.json` workflow

Breakage/confusion comes from the overlap:

- `web/library_editor.html` loads `/data/inputs_parsed.json`, which does not currently exist
- `scripts/parse_txt_to_json.py` still outputs `data/inputs_parsed.json`
- several script docs still reference parsed-json and text-list flows
- active runtime/pipeline scripts now start from `data/inputs.json`

This makes the library editor feel broken even when the actual pipeline is functioning, because it targets a retired intermediate artifact instead of the current source of truth.

## Required Direction

1. Keep `web/inputs_editor.html` as the only active editor.
2. Document `tools/inputs_editor/inputs_editor_server.py` as the required local editor server.
3. Mark `web/library_editor.html` as legacy/retired.
4. Remove `inputs_parsed.json` from active user-facing workflow documentation.
5. Keep any remaining parsed-json tooling only if it still serves an internal migration/audit role.
