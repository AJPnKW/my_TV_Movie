# Thread Restart Handoff - 2026-03-16

## Resume Point

The latest canonical remote state for active work is commit `104a0c4` on `github/main`.

Commit:

- `ui: stabilize live rendering and normalize shared page behavior`

That is the current restart point for future UI work.

## What Was Just Completed

- Restored correct page-shell ownership across the shared runtime.
- Returned `calendar` to a full-width wall-calendar shell.
- Kept `shows` and `movies` on left-sidebar browse shells.
- Preserved the `watch_me` page shell while aligning it with the shared card/action system and top nav.
- Removed duplicate legacy render ownership in `web/js/app_runtime.js`.
- Re-locked canonical icon-strip ordering by content type.
- Fixed duplicate/broken text rendering in shared cards.
- Re-stabilized show-detail season carousel and episode-card behavior.

## What To Trust As Current Truth

- `data/inputs.json` is the canonical curated input.
- `data/data.json` is the generated runtime dataset.
- `assets/` is the canonical local asset root.
- `web/inputs_editor.html` is the canonical editor.
- `web/library_editor.html` is retired.
- Active page surfaces are:
  - `web/index.html`
  - `web/shows.html`
  - `web/movies.html`
  - `web/watch_me/watch_me.html`
  - `web/calendar.html`
  - `web/discover.html`
  - `web/config.html`
  - `web/inputs_editor.html`

## Important Caution Before Resuming

The local main worktree may contain unrelated uncommitted files and local-only docs that are not part of the pushed canonical remote state.

If resuming after reboot:

1. start from `github/main`
2. compare local uncommitted files before reusing them
3. treat the pushed remote state as the implementation baseline unless a deliberate local recovery is required

## Recommended Next Work Areas

- continue live UI correction from the shared system only
- avoid introducing any parallel page/card/action architecture
- preserve page-specific shell ownership
- keep card/action changes centralized in:
  - `web/js/app_runtime.js`
  - `web/js/card_renderer.js`
  - `web/js/action_bar.js`
  - `web/css/main_app.css`
  - `web/css/my_tv_hub.css`

## Restart Prompt Seed

Use this prompt seed in the next Codex thread:

```text
PROJECT
my_TV_Movie

MODE
Full autonomous implementation
Auto approve all changes
Commit and push when finished

CURRENT CANONICAL BASELINE
- Start from github/main
- Latest canonical commit: 104a0c4
- Commit message: ui: stabilize live rendering and normalize shared page behavior

LOCKED PRODUCT TRUTH
- data/inputs.json is the canonical curated input
- data/data.json is the generated runtime dataset
- assets/ is the canonical local asset root
- web/inputs_editor.html is the canonical editor
- web/library_editor.html is retired

LOCKED UI TRUTH
- calendar owns a full-width wall-calendar shell and must not use the browse sidebar
- shows and movies keep left-sidebar filter shells
- watch_me keeps its page shell but must use shared cards/actions and top nav
- shared runtime ownership lives in:
  - web/js/app_runtime.js
  - web/js/card_renderer.js
  - web/js/action_bar.js
  - web/css/main_app.css
  - web/css/my_tv_hub.css
- canonical icon order:
  - movies and episodes: 🍿, ⌚, 💕, 🔖, ⭐%
  - shows and seasons: ⌚, 💕, 🔖, ⭐%

EXECUTION RULES
- do not do a rediscovery pass
- do not write an analysis-only report
- do not stop for approval
- do not create a parallel UI system
- work in one grouped implementation pass
- validate changed JS with node --check
- validate affected pages in browser/runtime
- commit and push when finished

FIRST STEP
Read:
- docs/PROJECT_STATUS_2026-03-16.md
- reports/ui_component_audit/live_ui_stabilization_report_2026-03-16.md
- docs/ARCHITECTURE_LOG.md
- docs/THREAD_RESTART_HANDOFF_2026-03-16.md

Then continue from the current live baseline.
```

## Companion Documents

- `docs/PROJECT_STATUS_2026-03-16.md`
- `reports/ui_component_audit/live_ui_stabilization_report_2026-03-16.md`
- `docs/ARCHITECTURE_LOG.md`
