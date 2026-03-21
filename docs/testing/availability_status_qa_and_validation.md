# Availability Status QA and Validation

## Required validation categories
| Category | Required |
|---|---:|
| Python syntax compile | Yes |
| JSON parse validation | Yes |
| Source file duplicate-key validation | Yes |
| Enum validation | Yes |
| End-to-end enrichment run | Yes |
| Post-enrichment field presence validation | Yes |
| UI render validation on real pages | Yes |
| Workflow validation | Yes |

## Test cases
| Case | Expected result |
|---|---|
| Future-dated movie | `not_yet_released` |
| Released movie with passing URL | `available` |
| Released movie with failing URL | `unavailable` |
| Released item with missing required URL | `unavailable` |
| Missing release date and no override | `unknown` |
| Unmatched record | `unknown` |
| Duplicate source keys | validator fail |
| Invalid enum | validator fail |

## Live repo QA commands
- `python -m compileall scripts`
- `python scripts/validate_availability_overlay.py --write-normalized`
- `python scripts/enrich_data_with_availability.py`
- `python scripts/qa_availability_status.py`
- `python scripts/qa_pipeline_integrity.py`

## Live repo QA artifact paths
- `reports/availability_status/availability_status_*.json`
- `reports/_qa_pipeline_integrity_*.json`
- `logs/qa_pipeline_integrity_*.log.txt`

## Required QA artifacts Codex must produce
| Artifact | Purpose |
|---|---|
| implementation summary | what changed |
| file inventory | exact files changed |
| validation summary | what passed |
| logs or report files | evidence |
| known gaps | if any remain |
