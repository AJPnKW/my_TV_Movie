<!--
FILE: reports/ui_component_audit/local_smoke_test_report.md
VERSION: 1.0.2
UPDATED: 2026-03-14T00:00:00Z
CHANGE NOTES:
- Document the one-command local smoke-test launcher for the main repo pages.
- Record the exact URLs opened for local validation.
- Lock the launcher documentation to Chrome only.
- Remove Edge entirely and allow Firefox only as the backup browser.
-->

# Local Smoke Test Report

## Purpose

Provide one repeatable command that starts the local servers needed for smoke testing and opens the main pages for this repo in one browser session.

## Command

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_smoke_test.ps1 -Browser chrome
```

Firefox backup:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_smoke_test.ps1 -Browser firefox
```

## Opened Pages

- `http://127.0.0.1:8000/web/index.html`
- `http://127.0.0.1:8000/web/watch.me.html`
- `http://127.0.0.1:8000/web/tv_shows_listing.html`
- `http://127.0.0.1:8000/web/heated-rivalry.html`
- `http://127.0.0.1:8000/web/watch_me/watch_me.html`
- `http://127.0.0.1:8787/web/inputs_editor.html`

## Notes

- Port `8000` is used for the standard static site pages.
- Port `8787` is used for `inputs_editor.html` because save/config APIs require the dedicated local server.
- The launcher reuses a running server when one is already responding on the expected port.
- Edge is intentionally unsupported.
