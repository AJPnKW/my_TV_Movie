# Visual Gap Analysis

Date: 2026-04-28

## Viewports

Validated through `scripts/qa_browser_layout_check.mjs` after starting `python -m http.server 8000`. Result: passed, with no console errors, 404s, or page-level horizontal overflow.

| Viewport | Size | Purpose |
|---|---:|---|
| Android/Chromecast TV | 1920x1080 | TV density and 7-column calendar |
| Laptop | 1366x768 | primary desktop/laptop density |
| Tablet landscape | 1024x768 | constrained desktop-like layout |
| Tablet portrait | 768x1024 | tablet wrapping and no overflow |
| Phone large | 430x932 | modern tall phone |
| Phone | 390x844 | narrow phone baseline |

## Findings And Fixes

| Area | Finding | Fix |
|---|---|---|
| Nested frames | Panels and dashboard wrappers still carried borders/shadows around framed cards. | `web/css/ui_contract_fix.css` now removes borders/shadows from app shell, panels, dashboard wrappers, and section wrappers while retaining borders on date/day columns and media cards. |
| Action boxes | Coarse-pointer and legacy CSS could enlarge action controls inconsistently. | Action controls now use one clamped square size, fixed aspect ratio, hidden overflow, and consistent active/inactive colors. |
| Action overlap | Action groups could compress into each other on small cards. | Action bar groups use fixed icon slots, clipped overflow, and compact rating width. |
| Card density | Recommendations and browse cards still rendered large posters on dashboard and mobile/TV. | Card grid max width, recommendation height, and image max height were reduced in the compatibility CSS. |
| State bleed | Item state used only a shared id key, which could affect multiple episode/season cards. | `web/js/watch_state_manager.js` now keys local state by kind/show/season/episode context. |
| Responsive QA | Existing layout QA did not cover all requested sizes. | `scripts/qa_browser_layout_check.mjs` now tests 1920x1080, 1366x768, 1024x768, 768x1024, 430x932, and 390x844. |

## Browser QA Results

| Check | Result |
|---|---|
| `scripts/qa_browser_layout_check.mjs` | passed |
| `scripts/qa_browser_popup_check.mjs` | passed |
| HTTP shell smoke for seven app pages | passed |
| D-pad smoke | passed; active focus stayed onscreen and Escape produced no runtime errors |
| Local watch-state toggle scope | passed; one clicked action updated only its own scoped state key |

## Residual Risk

Browser-font emoji rendering can vary by Android TV device. The canonical ticket and double-heart icons are still emitted by `web/js/action_bar.js`; validation checks that the source contract remains unchanged.
