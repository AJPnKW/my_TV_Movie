FILE: reports/ui_component_audit/editor_transition_report.md
VERSION: v1.0
UPDATED: 2026-03-15T04:34:43Z
CHANGE NOTES:
- Documented the editor transition to the canonical inputs editor workflow.
- Recorded the deprecation state of the legacy library editor.

# Editor Transition Report

## Canonical Editor

The canonical editor remains:

- `web/inputs_editor.html`

Canonical source of truth remains:

- `data/inputs.json`

## Legacy Editor Transition

`web/library_editor.html` was converted from an active legacy editor into a deprecation/redirect surface.

New behavior:

- informs the user that the page is deprecated
- explains that `inputs_parsed.json` is no longer the active persisted workflow target
- links to `/web/inputs_editor.html`
- auto-redirects to `/web/inputs_editor.html`

## Supporting Cleanup

- `web/config.DOC.md` was moved to `docs/config/config.md`
- active workflow documentation no longer needs to remain under `web/`
- `web/config.json` icon metadata no longer includes the hot dog marker for `media_videasy`
