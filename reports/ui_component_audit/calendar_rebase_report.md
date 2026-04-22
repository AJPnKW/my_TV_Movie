FILE: reports/ui_component_audit/calendar_rebase_report.md
VERSION: v1.0
UPDATED: 2026-03-15T04:34:43Z
CHANGE NOTES:
- Documented the calendar rebase onto the shared main-app runtime.
- Recorded what was corrected now versus what remains for later calendar-specific UX refinement.

# Calendar Rebase Report

## Rebased Now

`web/calendar.html` now:

- loads `./js/app_runtime.js`
- uses shared CSS instead of a page-local inline style block
- uses the same runtime path as dashboard, shows, movies, discover, and config
- no longer carries its own inline `watchstatusband` path inside the page shell

## Structural Correction Achieved

Calendar is no longer a separate old runtime fork. That was the core requirement for this pass.

The page now inherits:

- shared data/config loading path
- shared popup/detail contract markers
- shared normalized block contract markers
- shared action-bar contract markers
- shared event/runtime boot path

## Remaining Gap

Calendar still needs later view-specific polish and deeper calendar-specific cleanup, but those remaining items are now on top of the normalized runtime instead of inside a separate cloned app shell.

## Validation

- `web/calendar.html` references `./js/app_runtime.js`
- `web/calendar.html` references `./css/my_tv_hub.css`
- `web/calendar.html` references `./css/main_app.css`
- `web/calendar.html` contains no inline `<style>` block
- `web/calendar.html` contains no inline `<script>` block
