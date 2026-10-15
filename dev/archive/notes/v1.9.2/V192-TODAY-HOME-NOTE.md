# v192-today-home: BL-319 parts 1 to 5, Today as one home (Team 2, for Team 1)

Branch `v192-today-home`, from `origin/release-191`, with `origin/v192-sidebar` (BL-319 part 6, kept as built) and
`origin/v192-reject-reasons` (BL-315 server) merged in. Built from `dev/mockups/today-one-home-mockup.html`, tab "Today, one
home". Not pushed.

## Merge order

1. `release-191` (main and every v1.9.0 and v1.9.1 branch).
2. `v192-sidebar`, then `v192-reject-reasons` (both already merged here; the conflicts are resolved in this branch's merge
   commits: `core/server.js` and `settings.js` take the sidebar's `setRailCount` with release-191's code around it, and the
   Today badge and window title stay BL-288's plain "(n)" and "n messages to see first"; `quality.py` keeps both promises
   and the seven reasons; help.md keeps both "Or say" additions).
3. This branch, then `v192-reject-ui` (merged in here too).

## What was built

- **Header (part 1).** BL-293's band, unchanged (day line, headline, the day-line graphic, the meetings with follow-up and
  prep, Close the day, swipe and `[` `]` `T`, BL-321's fixed arrows). Its inner column is now full width (`.bandin`, was
  `.col80`).
- **To decide (part 2).** New first section (`#tdSec`), drawn by `components/today/ToDecide.jsx` from `today.js`
  `toDecideRows()`: pending proposals, transcripts ready in Intake (`mtgHasTx`), and messages from people Alan follows
  (tag "Message", never labelled), newest first, top five, "+n more", then "Open Review (n)". Icons: Approve and save,
  Reject with a reason, Open in Review, Process the transcript, Make a work item, Dismiss.
  - **Bulk rule:** Approve and save only for `tdApprovable` rows (`routineKid` and not a draft or file change). Minutes,
    reports, file changes, new decisions, new risks and every other one-at-a-time item, or one needing a project or with a
    conflict, get Open in Review instead (highlighted there).
  - The old "Messages to see first" block in Needs attention is gone: those rows are now To decide's (same
    `data-alertdo` buttons, same Undo).
  - **Needs attention has no proposal groups (Alan, 14-10-2026):** the per-meeting groups ("Review the … minutes", "Review the
    proposals from …") and their "Approve n routine" are gone; proposals are To decide's alone, and minutes and the other
    one-at-a-time items reach Review through "Open in Review". Nothing on Today shows a staging file name
    (`test_today_home.NoFileNames`). Needs attention now holds the pending decisions' line, the report reminders and the
    missing owner or due date line.
- **Sections (part 3), in order and unboxed:** To decide, First thing, Decisions needed, Needs attention, Your commitments
  (You owe and Waiting on now inside it), Week ahead, Resolved (a closed `<details>`, one line with the count) and
  Portfolio (unchanged, BL-285's hover kept).
  - **Week ahead** (`components/today/WeekAhead.jsx`, `weekGroups()`; server `build_dashboard.week_ahead`): day by day
    **to next Monday** (`week_window` changed); pending decisions needed in the window (decisions have no priority, so all
    of them); late work of the listed priorities and late decisions lead the first day (`week_late`, `od`); milestones carry
    `slip`. Each row: tag, title, who and project, why (due, due over the weekend, n days overdue, needed by, n days late,
    due · at risk / on track, worth preparing), icon action.
- **Icons (part 4).** `components/IconButton.jsx` (new building block, `test_block_icon_button.py`); `tib()` for the rows still
  drawn as text (Your commitments, Decisions needed on Today, reminders). Named on hover (`data-tip`) and to screen readers
  (`aria-label` with the row's words); 55% until the row is hovered or focused, full strength without hover; nothing
  moves. Mark done and Move the date are staged through `pkCommit` with Undo (`pkUndoLast`). The reminders' "…" menu stays.
  New icons in `core/dom.js`: play, calmove, done, dismiss, chasemail.
- **Spacing (part 5).** 28px between sections, rows ≥44px, one 13px uppercase heading style, content at 980px centred,
  header full width; under 480px a row's icons go under its words.

## Alan's decisions applied

- **(a) Week ahead priorities:** the Week ahead follows `dashboard.week_ahead_priorities`; nothing is hard-coded. A line
  under the heading says what the setting lists ("Urgent work, every milestone and decision, and meetings"). I did **not**
  change the default. It is already `["Urgent"]` on this branch, at `system/templates/settings-defaults.json` line 101-103
  (`"week_ahead_priorities": [ "Urgent" ]`); per the coordinator (Urgent only, 14-10-2026) that line stays as it is, and
  v192-settings-server owns any change. No Help text or test here says the default is Urgent and High (Help: "Urgent
  unless you change it").
- **(b)** The sidebar stays always collapsed below 1200px, as built on v192-sidebar (untouched).

## The BL-315 hook (wired)

`origin/v192-reject-ui` (eb5374a, BL-315's screens) is merged in (it contains v192-reject-reasons). To decide's **Reject,
with a reason** now opens the same menu as Review: `today.js` `tdAct` calls `rjLoadGuesses()` then `rjMenuFor([r], btn, …)`:
the seven reasons on 1 to 7, Use each guess, No reason, Duplicate's item, through `/api/review/reject`, with its one message
and Undo. Merge conflicts resolved keeping both: `review.js` (BL-288's comment and BL-315's `rjLoadGuesses`), `keys.js` and
`panel.js` imports (both sides' names), `style.css` (`.rtline` and the `.rj…` rules), help.md (Review steps renumbered 11 to
14: Update an existing item instead, Reject with a reason, Every reject can be changed, Looks done; Approve routine keeps the
promise sentence, the bar says Reject with a reason (R)). `RailMore.jsx`'s `menuItems` became `railMenuItems` (JSDUP with
`RejectMenu.jsx`). No golden changed with the combination.

## Tests

- New: `dev/tests/test_today_home.py` (Header, ToDecide, Sections, Icons, Rhythm, Narrow: one class per Done-when point),
  `dev/tests/test_block_icon_button.py`.
- Changed: `test_today_brief.py` (window to next Monday; order; 980px column; Week ahead rows and why; a new data test for
  decisions, late work and milestones at risk), `test_vip_screens.py` and `test_sweep_alerts.py` (messages are To decide
  rows), `test_dashboard_editing.py` (8 sections), `test_ui_sweep.py` (the closed Resolved list is skipped, like
  Settings' Advanced rows).
- `test_ui_sweep.py`'s Work at 640px failure (`#workTbl .ce a.plink2[data-person]` covered) was already failing on the base
  before this work; not touched.

## Goldens

Re-recorded, for Alan to agree: `dev/tests/snapshots/today.html` (only that one changed).
