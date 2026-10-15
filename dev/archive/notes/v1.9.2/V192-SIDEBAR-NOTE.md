# v1.9.2 sidebar (BL-319 part 6): note for Team 1

Branch `v192-sidebar`, from `origin/v19-base` (origin/main had no Preact yet). Not pushed.

## What it is

The sidebar is now Preact components (dev/COMPONENTS.md) reading one store:

- `src/stores/rail.js`: `RAIL_ITEMS`, `RAIL_DEF`, `railItem`, `railNorm`, and the signals `railCfg`, `railView`,
  `railCounts`, `railMoreOpen`, `railCustOpen`, `railNarrow`, `railCollapsed`, `railMoreWaiting`;
  `setRailView(key)` and `setRailCount(id, n, label)`.
- `src/components/sidebar/`: `RailToggle`, `RailNav`, `RailButton`, `RailMore`, `CustomiseSidebar`, `RailIcon`
  (the icons as element data).
- `src/rail.js` mounts them into `#railTogBox`, `#railMain`, `#railFoot` and `#railCustBox`, and keeps `railSave`,
  `railToggle`, `railCustomise`, `renderRail` (now just sets the current page) and `railPopOpen` (an alias of
  `railCustomise`, for ⌘K).

Default: top Today, Work, Review, Projects, People; More (at the bottom) Intake, Files, Activity, Settings.
`dashboard.rail` gains `more`; `hidden` stays in the shape, always `[]` (an old hidden page goes into More).
Expanded 212px, collapsed 56px (`--rail-w`). **Under 1200px the sidebar is always collapsed** (toggle hidden, nothing
saved; `railNarrow`): with 212px the side peek (BL-80/BL-176), the top bar (BL-81) and the chat-beside rules failed their
tests at 1000 to 1100px. This breakpoint is my call, not in BL-319: Alan may want a different one. At 1200px and wider,
expanded, the page is 140px narrower than beside the old 72px rail.

## What other code must do now

- **Never write into the sidebar's DOM.** To mark the page: `setRailView(key)`. To set a badge:
  `setRailCount(id, n, label)`. The badge elements keep their ids (`#revBadge`, `#inboxBadge`, `#vipBadge`), always
  exist (in More's closed menu when the page is there) and still show `display:none` at 0.
- `.rail button[data-v="…"]` still finds a page's button; a page in More is inside `#railMoreMenu` (hidden until More
  opens), so a real click on it needs More opened first. `go(id)` works for every page.
- **Today's sidebar badge:** only the VIP count is on Today (`vipBadge` → `setRailCount("today", …)`). If Team 1 wants
  the mockup's To decide count on Today, call `setRailCount("today", n, label)` from today.js; nothing else is needed.

## Files outside rail.js and the components that changed (each a call site)

- `src/core/nav.js`: the three `$$(".rail button[data-v]").forEach(…aria-current…)` lines became `setRailView(…)`
  (go, the milestones page, the meeting page), plus its import.
- `src/core/server.js` `renderBadge`: `setRailCount("review", n)` in place of writing `#revBadge`; the `railMoreUpd`
  import replaced.
- `src/intake.js` `inboxBadge`: `setRailCount("inbox", n, label)`; the `railMoreUpd` import replaced.
- `src/settings.js` `vipBadge`: `setRailCount("today", n, label)` in place of adding `#vipBadge` to the button, plus
  its import.
- `src/core/dom.js` `tipShow`: a tooltip on something in the sidebar sits to its right (one line).
- `shell.html`: the nav has `id="rail"`, the toggle's box and `.rhead` around the wordmark; the hint says "sidebar".
- `style.css`: the rail rules rewritten (BL-163 block and the 480px rule).
- `settings-defaults.json`: `dashboard.rail` gains `more`.

**Not changed (Team 1's modules):** `today.js`, `review.js`, `panel.js`, `ask.js`. ⌘K keeps ask.js's entry
"Customise the rail" (it calls `railPopOpen`, which now opens Customise sidebar). If Team 1 wants the words
"Customise sidebar" in ⌘K, or a "Collapse or expand the sidebar" (⌘\) entry calling `railToggle()`, that's a line each
in ask.js; the cmdk golden would change with it.

## Goldens

Only `settings-general` changed: the Appearance row is now "Sidebar" with "Choose what is in the sidebar and what is
in More, put them in your own order, or show icons only". The snapshots capture each page's main region, not the
sidebar, so no other golden moved.

## Tests

- `dev/tests/test_rail_customise.py` rewritten for the sidebar (14 tests: default, toggle in place, ⌘\, remembered,
  collapsed names/tooltips/badges/accent bar, the narrow window, More upwards and sideways, its keys, empty More,
  Customise by buttons, Alt+arrows, drag across lists, Cancel/Esc/Reset/Icons only, right-click/Settings/⌘K, railNorm,
  a failed write put back).
- Adjusted: `test_today_brief.py` (Intake's name now its label; the foot holds More and Customise sidebar…),
  `test_ui_sweep.py` (the narrow rail is 56px), `work_board_case.py` (1640px wide, so the board keeps its old width).
- Failing, not caused here (also fail on `origin/v19-base` today): `test_dashboard` (Preact's namespace URLs, known),
  `test_meeting_hub` (its fixture's 2026-10-14 clashes with today's date), `test_settings_page` week-ahead ticks and
  `test_work_item_peek` "+3d" (date-dependent).
- **Exposed, not fixed:** `test_ui_sweep` Reflow at 640px, Work: Sara's person link sits under the title cell. The 56px
  rail gives the page 16px more than the old 72px one, and the base fails the same way at 656px, so it's a latent Work
  table overlap at that width (Work's code, not the sidebar's).

## Not done here

- `Menu`, `Dialog`, `IconButton` and `Icon` are not built as shared blocks; the sidebar has its own (menu and dialog
  behaviour inside `RailMore` and `CustomiseSidebar`, icons in `RailIcon`) to avoid clashing with Team 1's blocks.
  When those land, the sidebar should move onto them.
- Settings' "2 to fix" (BL-320, Health inside Settings) isn't on this base; when it lands, `setRailCount("settings",
  n, "2 to fix")` puts it on Settings and on More.
- The sidebar's styles are in `style.css`, not a per-area stylesheet: the build has no component stylesheet step yet.
