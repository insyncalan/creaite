# v1.9.0 — BL-295, Close the day, a guided shutdown (the screens)

Taken over from Team 1 (paused 14-10-2026 00:15, Alan approved the hand-over). Branch `sprint-close-day-ui`. The server side
(`close_day.py`, the `/api/day/*` routes, the `sweep` guard mode) was already on main (`dev/sprints/BL-295-server.md`).

## What Team 1 had (9baeb15, "not tested")

- `components/closeday/CloseDay.jsx`: the four-step card (Catch up, Today, Loose ends, Tomorrow) and the end line, on a new
  `Dialog` building block (`components/Dialog.jsx`, its own test `test_block_dialog.py`) and `components/mount.js`.
- `components/closeday/FirstThing.jsx`: First thing at the head of Today's brief (`#ftSec`).
- BL-206's string-built card removed from `ask.js`; `openClose()` now opens the component.
- Settings › General › Close the day (`day.catchup_sweep`, `day.catchup_after_minutes`).
- `close_day.py`: overdue items in Loose ends (Alan's decision). `session.py`: the First thing line at session start (Alan's
  decision); `creaite-rules.md` says so.
- Help, release note, `test_close_day_card.py` (three tests), updates to `test_close_day`, `test_close_day_guided`,
  `test_today_brief`, `test_settings_page`, `test_dashboard_editing`; goldens `today.html` and `settings-general.html`.

## What I did

1. `git merge origin/main` (16 behind): one conflict in `today.js` (a comment on the portfolio line; main's kept) and
   `dashboard.html` (rebuilt).
2. `git merge origin/sprint-today-days-ui` (BL-293, which merges before this in v1.9.0; both touch `today.js`): conflicts in
   `today.js` imports, `main.js` component exports and `core/globals.json`, all kept from both sides; `dashboard.html` rebuilt.
   **Merge order: BL-293 (`sprint-today-days-ui`) first, then this branch.**
3. Reviewed the WIP against every Done-when point and Alan's Decisions. All of it was there except:
   - a close waiting for the sweep stopped following it once the card was hidden (the status poll ran only while the card was
     open), so the day closed on the server but the door and the card didn't know until reopened. The poll now also runs
     while a close is waiting.
   - most Done-when points had no test. Added one per point (below); fixed the Skip test, which expected Today to show on a
     quiet day (it is passed over, as the rule says).
4. Rebuilt the guides (`guide-how-to.html` was out of date with Help). `dev/dashboard-spec.md`: the card, First thing and the
   settings rows.

No server change was needed beyond Team 1's; the BL-141 guard tests are unchanged and pass.

## Done when, with the test for each

| Point | Test |
|---|---|
| An old sweep starts the catch-up as the card opens, with its progress | `test_close_day_card`: `test_the_four_steps…` (starts, ends, "Caught up at"), `test_stop_ends_the_sweep_and_shows_its_progress` (sources list, `aria-busy`); `test_close_day_guided` `CatchupDecision` |
| Skip works | `test_close_day_card`: `test_esc_keeps_the_step_skip_stops_a_running_sweep…` (nothing staged) |
| Stop works | `test_close_day_card`: `test_stop_ends_the_sweep_and_shows_its_progress` |
| The sweep's new items in Loose ends (first, tagged New) | `test_close_day_card`: `test_the_four_steps…` |
| Choices kept; Review now opens Review filtered | `test_close_day_card`: `test_the_four_steps…` (plan in `day-closed.json`, Review highlighted) |
| Review now opens Work for an item, Intake for a file; stages nothing | `test_close_day_card`: `test_ask_first_and_review_now_opens_work…` |
| First thing on tomorrow's brief | `test_close_day_card`: `test_first_thing_heads_the_next_mornings_today`; `test_close_day_guided` test_8 |
| First thing on the session-start line | `test_close_day_guided` test_8 |
| Prep pages made (through the run engine, after closing) | `test_close_day_card`: `test_the_four_steps…` (made); `test_close_day_guided` test_6 |
| Closing during a sweep closes when it ends | `test_close_day_card`: `test_closing_during_the_sweep_closes_when_it_ends`; `test_close_day_guided` test_7 |
| Nothing approved or applied | `test_close_day_card`: tracker and every earlier proposal unchanged (two tests); `test_close_day_guided` test_5 |
| A quiet day skips empty steps | `test_close_day_card`: `test_esc_keeps…` (Today passed over both ways, shown done); `test_close_day` (Catch up off) |
| Overdue items in Loose ends | `test_close_day_card`: `test_ask_first…`; `test_close_day_guided` `LooseEndsShape` |
| Ask first (`day.catchup_sweep` offer) | `test_close_day_card`: `test_ask_first…` (nothing started) |
| Keyboard; "Step 3 of 4, Loose ends" for a screen reader | `test_close_day_card`: `test_the_four_steps…` (← →, focus on Next, the group's name and the live region), `test_esc_keeps…` (Esc, ←); `test_block_dialog` |
| VIP never labelled | `test_close_day_card`: `test_the_four_steps…` |
| Debug log: counts only | `test_close_day_guided` test_9 |
| Help updated | `test_help` (guides rebuilt) |

## Tests

`check.py`: OK. Passed: test_close_day_card (6), test_close_day, test_close_day_guided, test_today_brief, test_today_days_ui,
test_snapshots, test_dashboard_split, test_help, test_help_loop, test_ui_sweep, test_block_dialog, test_dashboard_editing,
test_guard_pinned, test_reach, test_record_commands.

`test_settings_page`: one failure, `test_week_ahead_ticks_save_reload…` (the Week ahead has no items in the fixture). It fails
the same way on `origin/main` and on `origin/sprint-today-days-ui`, so it is not BL-295's; left for its owner.

## Goldens (BL-254)

Re-recorded by Team 1, checked here as BL-295's only:
- `today.html`: the hidden First thing section (`#ftSec`) at the head of the brief.
- `settings-general.html`: the Close the day section (two rows).

No golden for the card itself: opening it in the snapshot vault would start a catch-up sweep through the real `claude`
command. The card's markup is covered by `test_close_day_card`.
