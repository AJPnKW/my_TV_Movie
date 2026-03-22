# Docs Cleanup Plan — 2026-03-21

## Execution model
| Step | Action |
|---|---|
| 1 | backup current `docs` folder |
| 2 | write pre-clean inventory |
| 3 | archive noisy/non-active artifacts |
| 4 | normalize selected spec filenames |
| 5 | add / replace index docs |
| 6 | write post-clean inventory |
| 7 | zip cleanup run outputs |

## This cleanup intentionally does not do
| Item | Decision |
|---|---|
| delete files permanently | No |
| rewrite content of the active spec sections | No |
| merge spec notes automatically | No |
| move availability-status docs out of their current functional folders | No |

## Script scope
The included PowerShell script performs only safe archival and rename operations based on the reviewed bundle.
