# AI Agent Operational Rules

All AI agents modifying this repository must follow these rules.

1.  Always read docs/ARCHITECTURE.md before making changes.
2.  Do not redesign architecture unless explicitly instructed.
3.  Normalize existing systems instead of creating new ones.
4.  When architectural changes occur:
    -   update ARCHITECTURE.md
    -   append entry to ARCHITECTURE_LOG.md
5.  Avoid UI drift by using shared modules:
    -   card_renderer.js
    -   action_bar.js
    -   app_runtime.js
6.  Do not introduce duplicate UI components.
