# Architecture Log

## 2026-05-04

- Fixed dashboard duplicate rendering guards with shared card render keys, scoped dashboard dedupe, and non-accumulating dashboard navigation handlers.
- Restored the top app nav as a true sticky header and compacted dashboard recommendation card sizing.
- Extended runtime validation to cover duplicate dashboard render keys, sticky top nav pinning, compact recommendation dimensions, and local rendered performance thresholds against `docs/00_master_contract.html`.
- Commit: `7e5c6fe5` fix dashboard rendering and sticky nav validation.

## 2026-04-30

- Updated page shells to add Discover to the primary icon nav across active pages.
- Wired Discover to a separate discover registry source and config-needed empty state.
- Rebuilt Manage Watch State display rules so show/season rows derive watched status from released children.
- Aligned validation and rendered QA checks with the current master contract.
- Commit: `5f1af1c9` implement master contract compliance batch.
