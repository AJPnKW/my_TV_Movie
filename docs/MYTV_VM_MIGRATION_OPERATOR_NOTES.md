# MYTV VM MIGRATION OPERATOR NOTES

This records how the user narrative was interpreted.

- ChatGPT manages design, prompts, docs, and coordination.
- Medium Green PowerShell runs commands only.
- Lime Green Codex handles VM/deployment/infrastructure.
- Forest Green Codex handles app/API/database/state logic.
- GitHub stores persistent project memory.
- X1 Lab VM comes first.
- HP production VM comes later.
- PostgreSQL becomes primary write store.
- JSON remains import/export/static fallback.
- Images remain filesystem/assets by default; PostgreSQL stores metadata and paths.
