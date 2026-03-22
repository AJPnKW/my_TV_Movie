# Focus And Navigation TV Contract

## Purpose

Defines first-class Android TV and D-pad behavior for the shared runtime. TV behavior is not a fallback mode; it is a core interaction contract for browse surfaces and popups.

## Global Rules

- every actionable control must be reachable without a pointer
- visible focus is mandatory
- hidden or offscreen controls must not receive focus
- focus order must follow spatial layout, not DOM accidents

## D-Pad Navigation

- left/right move horizontally to the nearest visible actionable target
- up/down move vertically to the nearest visible actionable target
- if no candidate exists in that direction inside an active popup, the popup scrolls for up/down
- Enter and Space activate the focused control

## Popup Focus Trap

- opening a popup stores the previously focused element
- focus moves into the popup header exit button immediately
- Tab and Shift+Tab loop inside the topmost popup only
- provider popup above a show or movie popup becomes the active focus layer
- closing the top popup restores focus to the last element in the layer below, or the original invoker if no deeper popup remains

## Scroll Lock

- background document must not scroll while any popup is open
- modal scroll happens inside the popup card only
- wheel, touch, and key-driven scroll all remain inside the top popup

## Active Layer Rules

- provider modal supersedes movie/show popup
- show/movie popup supersedes page content
- page content cannot reclaim focus while a popup is open
- launching a watch source from the provider popup closes the provider layer so return focus goes back to the underlying page or popup

## Browse Surface Rules

- cards are focusable as a whole surface
- action-strip icons are separately focusable
- action-strip navigation must not wrap into a second row
- season carousel buttons and cards participate in the same spatial navigation map

## Android TV Specific Implications

- minimum focus target size should remain usable from a couch distance
- sticky headers must not cover the focused control when it scrolls into view
- side drawers on phones are optional, but TV relies on predictable left-right travel and stable control placement

## Must Never Happen

- focus escaping behind an open popup
- background scroll while modal is active
- focus landing on hidden items
- action-strip wrapping that changes D-pad geometry
