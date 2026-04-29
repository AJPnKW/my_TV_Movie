# Visual Gap Analysis

Date: 2026-04-29

## Viewports

Validated through repo runtime checks after starting `python -m http.server 8000`.

| Viewport | Size | Purpose |
|---|---:|---|
| Android/Chromecast TV | 1920x1080 | TV density and D-pad readability |
| Laptop | 1366x768 | primary desktop/laptop density |
| Tablet landscape | 1024x768 | constrained desktop-like layout |
| Tablet portrait | 768x1024 | tablet wrapping and no overflow |
| Phone large | 430x932 | modern tall phone |
| Phone | 390x844 | narrow phone baseline |

## Findings And Fixes

| Area | Finding | Fix |
|---|---|---|
| Action overlap | Fixed action boxes could exceed the available card width and overlap. | `web/css/ui_contract_fix.css` now uses adaptive square action boxes and visible overflow on action groups. |
| Popcorn clipping | Action containers could clip the rounded popcorn box. | Removed action-row `overflow: clip` behavior and normalized square box sizing. |
| Image/action overlap | Some card paths could visually place card controls over the media area. | `web/js/card_renderer.js` keeps the action row below media and preserves a visible text row outside the image. |
| Availability badge overlay | Availability badges sat over posters/stills and hid content. | Card render paths no longer pass availability badges; availability is represented by popcorn state only. |
| State bleed | Cards with shared local ids could toggle together. | `web/js/watch_state_manager.js` now keys state by item context, including episode show/season/episode identity. |
| Card drift | Dashboard, discover, watch-me, shows, and movies used visibly different card/action rules. | Shared card/action CSS now controls density, action sizing, image/action separation, and compact rating output across pages. |
| Header size | The text logo block consumed too much vertical space. | Page shells now use `assets/custom/the_boys_hub_logo2.png` with compact sticky header styling. |
| Section behavior | Dashboard sections lacked a consistent sticky section header pattern. | Dashboard, watch-me day groups, and calendar summaries use the shared sticky section header treatment. |
| Overflow behavior | Dashboard/calendar overflow behavior was inconsistent. | Shared `+X more` expansion is active for dashboard and calendar visible sets. |
| Runtime assets | Runtime images previously retained original-sized downloads. | `scripts/optimize_runtime_assets.py` generated poster, still, and backdrop runtime targets and refreshed the asset report. |

## Browser QA Results

| Check | Result |
|---|---|
| Repo validation entry point | passed |
| HTTP shell smoke for seven app pages plus Inputs Editor shell | passed |
| Responsive viewport inspection | passed at 1920x1080, 1366x768, 1024x768, 768x1024, 430x932, and 390x844 |
| Popup/modal focus smoke | passed; focus stayed inside the active modal and Escape closed it |
| Watch-state scope smoke | passed; visible action buttons all had context-specific keys |
| Action geometry smoke | passed; no visible action overlap, clipping, non-square buttons, or page overflow |

## Residual Risk

Browser-font emoji rendering can vary by Android TV device. The canonical ticket and double-heart icons are emitted by `web/js/action_bar.js`; validation checks that the source contract remains unchanged.
