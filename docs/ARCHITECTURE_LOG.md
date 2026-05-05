# Architecture Log

## 2026-05-04

- Updated GitHub workflow actions to Node-24-native major versions for checkout, setup-python, and setup-node to remove the Node 20 deprecation warning.
- Commit: `adf6cc48` update github actions to node24-native versions.

- Restored GitHub validation workflow integrity by adding the missing availability source validator, aligning the validate workflow with the asset fetch precondition used by build-data, fixing the self-heal asset downloader call signature/base URL, and replacing the retired `watch_me_runtime.js` syntax check with the active shared watch-state runtime module.
- Commit: `f3f3948f` fix github validation workflow availability checks.

- Implemented MC-2026-05-05.1 Trakt two-way watch-state sync: file-backed `data/watch_state_queue.json`, local click queue records, inputs-editor queue/sync APIs, Trakt dry-run/live sync engine, exact watchlist/history endpoint payload generation, and validation/browser QA coverage for queue records and payload proof.
- Commit: `5d62716f` implement trakt two way watch state sync.

- Implemented MC-2026-04-30.4 contract updates for shared calendar column alignment, tri-state local-first watch-state records, queued Trakt workflow scaffolding, computed Manage Watch State statuses, popup media-detail rendering, Android TV popup focus trapping, and extended rendered validation.
- Commit: `0105895e` fix calendar trakt watch state popup and dpad contract compliance.

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
