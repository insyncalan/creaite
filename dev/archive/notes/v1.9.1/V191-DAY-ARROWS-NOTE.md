# v1.9.1 — BL-321, the day arrows never move

Taken over from Team 1 (paused 14-10-2026, Alan approved the hand-over).

## What Team 1 built (ce528cf, on BL-293's 63ff7a0)

The ‹ › arrows sit at a fixed place at the top right of Today's band on every day, whatever the headline, meetings or the day line's wrapping; at an end the arrow stays, disabled and dimmed. `test_today_days_ui` clicks › through every day without moving the mouse and checks both arrows' boxes are identical, with reduced motion, with motion on and at 320 px. ce528cf also carried a merge of an earlier main.

## The merge (sprint-today-days-ui, with today's main, into fix-day-arrows)

Merge order for Team 1: `sprint-today-days-ui` first (see `dev/archive/notes/v1.9.0/V190-TODAY-DAYS-NOTE.md`), then `fix-day-arrows`.

Three conflicts:

- `dev/BACKLOG.md`, `dev/archive/sprints/STATUS.md` — the older main ce528cf carried against today's; resolved to origin/main's version exactly (no edit of our own; BL-321's entry is already in main).
- `src/today.js` — two comment-only hunks (BL-256 StatusDot comments); took main's wording. BL-321's own changes merged cleanly.
- `dashboard.html` rebuilt with `split_dashboard.py build`.

## Tests

`check.py`: OK. All passed: test_today_days_ui (arrows fixed at reduced motion, motion on and 320 px), test_today_days, test_today_brief, test_snapshots, test_dashboard_split, test_block_tabs, test_portfolio_table.

## Goldens

None changed.

## CI fixes carried over

The two CI fixes on `sprint-today-days-ui` (218076e) came in by a merge with no conflicts. One is the single reduced-motion rule; the other updates the Prep label test to expect the day written out. See `dev/archive/notes/v1.9.0/V190-TODAY-DAYS-NOTE.md`. BL-321 adds no reduced-motion block of its own. Passed afterwards: test_motion, test_sweep_alerts, test_today_days_ui, test_today_brief, test_snapshots, check.py.
