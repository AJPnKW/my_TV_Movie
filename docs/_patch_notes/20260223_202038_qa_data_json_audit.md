# QA Data JSON Audit + Dedup Fix

- Timestamp local: `2026-02-23T20:20:38`
- Timestamp UTC: `2026-02-24T01:20:38Z`

## Evidence
- `inputs.tv` duplicate TMDB groups before: `0`
- `data.shows` duplicate TMDB groups before: `0`
- `watch_me` TV path had no show-level dedupe by TMDB/season/episode keys.

## Changes
- Deduped `data/inputs.json` TV rows by `tmdb_id` (removed `0` duplicate rows).
- Applied requested show entries idempotently:
  - 155431 `*`
  - 245927 `*`
  - 276241 `2+`
  - 84910 `14+`
  - 40936 `3+`
  - 247723 `*`
- Deduped `data/data.json` shows by `tmdb_id` (removed `0` duplicate show rows).
- Deduped within merged shows: removed `0` duplicate season rows and `0` duplicate episode rows.

## Rule Validation (After)
- Show uniqueness (TMDB): `0` duplicate groups.
- Season uniqueness within show: `0` duplicate rows.
- Episode uniqueness within season: `0` duplicate rows.

## Artifacts
- `out/qa_data_json_audit/20260223_202038/inputs_data_duplicate_report.json`
- `out/qa_data_json_audit/20260223_202038/inputs_data_duplicate_report.txt`
- `out/qa_data_json_audit/20260223_202038/inputs_data_duplicate_report.log.txt`
