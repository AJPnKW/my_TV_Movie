# AI Agent Rules

`docs/00_master_contract.html` is the source of truth. Do not simplify, collapse, or generalize user examples when updating docs or code.

## Required Workflow

- Fix existing canonical files before adding new owners.
- Do not create replacement frameworks.
- Archive the master contract before editing it.
- Update contract sections additively with `Added`, `Updated`, `Origin`, `Owner`, and `Validation`.
- Append `docs/ARCHITECTURE_LOG.md` when architecture or page shells change.
- Run the relevant validators before committing.

## Drift Controls

- Public UI must not expose provider admin notes or status words.
- Watch Source Providers use compact country rows with provider hyperlink anchors.
- Provider URLs belong in `href` only, never visible text.
- Media Library belongs inside the primary nav icon row only.
- Retired compatibility shims must stay archived, not active.

