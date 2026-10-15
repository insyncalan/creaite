# v1.9.0 — BL-293, Today moves between the calendar's days (the screens)

Taken over from Team 1 (paused 14-10-2026, Alan approved the hand-over).

## What Team 1 built (63ff7a0)

- The date at the top of Today's band becomes a day line (`DayTabs`, a `Tabs` block): every day the saved calendar holds, the chosen one written out, today in the accent colour, a "Next week" divider.
- Click, hover chevrons, a two-finger swipe (one day per gesture), a touch drag, `[` `]` and `T` move it; arrows, Home and End inside it. The chosen day is in memory only (`stores/today.js`): a reload opens on today.
- Only the band follows the day: `dayShape`, `DayCurve` (no sun or Now off today), `DayMeetings`. Past days show the follow-up state (Minutes made, Draft in Review, Transcript ready / Process, No transcript, Not checked yet / Check); today and later show one pill per meeting (Prepare or Prep). Confidential meetings show only title and times. The Prep popup opens for any day.
- New blocks `Tabs` and `Chip` (dev/COMPONENTS.md) with their own Chrome tests; `test_today_days_ui.py`; `test_insight` expects "Prepare for …".
- 951ef60 was only a rebuilt guide (`guide-how-to.html`).

## The merge with main (37 commits behind)

`git merge origin/main`; three conflicts:

- `src/projects.js` — import line from `today.js`: BL-293 added `longDay`, main (BL-285) added `pfResize`. Kept both.
- `src/today.js` — imports: BL-293 added `SA` from settings.js, main (BL-285) added `colResizer` from work.js. Kept both.
- `dashboard.html` — took main's side, then rebuilt with `split_dashboard.py build`.

Everything else (BL-285 portfolio table, Preact StatusDot, BL-308, tests and notes) merged cleanly.

## Tests (after the merge)

`check.py`: OK. All passed: test_today_days_ui, test_today_days, test_today_brief, test_snapshots, test_dashboard_split, test_help, test_help_loop, test_ui_sweep, test_block_tabs, test_block_chip, test_insight; also test_portfolio_table, test_meetings, test_clear_day, test_dashboard*.

## Goldens

None changed (the sample vault has no calendar, so the day line does not appear in the snapshots).

## CI fixes after the merge (Actions run 38530386542)

- **test_motion** (one reduced-motion rule): BL-293 added its own `@media (prefers-reduced-motion:reduce){ .dayedge{transition:none} }`. It was redundant: the single existing block already collapses every transition, and leaves motion on when the in-app Motion setting is Full. I removed it, so `style.css` has one block again.
- **test_sweep_alerts** › `test_the_brief_in_chrome`: this was BL-293's intended wording, not a regression and not a date problem. `openPrep` now labels a later day with the day written out (`longDay`, e.g. "Thursday 15th October, 10:00 – …") instead of "Tomorrow". The test now expects tomorrow's weekday name and ", 10:00".
- Passed afterwards: test_motion, test_sweep_alerts, test_today_days_ui, test_today_brief, test_snapshots, check.py.
