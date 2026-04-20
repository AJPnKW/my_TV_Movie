# Codex Operating Rules — my_TV_Movie

Always append ARCHITECTURE_LOG.md when architecture or page shells change.

Read these first before any change:
- docs/ARCHITECTURE.md
- docs/AI_AGENT_RULES.md
- docs/UI_COMPONENTS.md
- docs/UI_GAP_ANALYSIS.md
- docs/ARCHITECTURE_LOG.md

Execution rules:
- Do not do rediscovery or broad analysis passes.
- Do not restate repo history.
- Do not propose options.
- Do not stop for approval.
- Implement in one grouped pass where possible.
- Fix live UI defects, validate, update docs only if architecture changed, commit, and push.
- Prefer correcting existing shared runtime/modules over adding new parallel systems.
- Treat the following as locked decisions:
  - data/inputs.json is canonical input
  - data/data.json is generated runtime output
  - web/inputs_editor.html is the canonical editor
  - web/library_editor.html stays retired/redirect-only
  - assets/ is the canonical asset root
  - calendar is full-width and has no left sidebar
  - shows/movies use left sidebar filters
  - watch_me keeps its own page but must share the card/action system
  - icon strip order is:
    - movies/episodes: popcorn, watch-status, favorites, bookmark, rating
    - shows/seasons: watch-status, favorites, bookmark, rating

Delivery rules:
- Implementation first.
- Validate with code checks and browser/runtime checks.
- Update docs/ARCHITECTURE_LOG.md with commit id and summary.
- Commit and push when complete.
