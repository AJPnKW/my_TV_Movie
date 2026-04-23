# Availability Status UI Integration

## Outcome
Every applicable movie/show/season/episode display surface should be able to render one normalized availability indicator based on `availability_status`.

## Target surfaces
| Surface | Required |
|---|---:|
| index/list pages | Yes |
| show cards | Yes |
| movie cards | Yes |
| season displays if present | Yes |
| episode rows | Yes |
| popups/details | Yes |

## Rendering rule
Pages must read `availability_status` from `data.json` and render one shared status pattern.

Live implementation path:
- shared badge helper: `web/js/availability_ui.js`
- shared card renderer support: `web/js/card_renderer.js`
- main app integration: `web/js/app_runtime.js`
- watch_me integration: `web/js/watch_me_runtime.js`
- badge and ring styling: `web/css/main_app.css`

## Shared mapping
| `availability_status` | UI label |
|---|---|
| `available` | Available |
| `unavailable` | Unavailable |
| `not_yet_released` | Not Yet Released |
| `unknown` | Unknown |

## UI implementation rule
Codex must inspect the current component/helper/page architecture and integrate into the existing rendering pattern instead of inventing a parallel UI system.

## Live surfaces now wired
- dashboard cards
- shows cards
- movies cards
- calendar cards
- watch_me cards
- show popup detail grid
- movie popup detail grid
- season detail block inside show popup
- episode cards inside show popup

## Placement rule
- Show and season surfaces keep the shared availability badge treatment.
- Movie and episode surfaces use the popcorn watch icon as the primary availability indicator with a tight square outline.
- `available` = green outline, `unavailable` = orange outline, `not_yet_released` = red outline.
- Movie and episode cards do not place availability badges over poster or still copy.
