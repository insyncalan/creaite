# Proposal: tracker.suggested_state follows CREAITE_NOW (guarded file: tracker.py)

**What.** One line in `system/scripts/tracker.py`, `suggested_state(row, on=None)`: `on = on or today()` becomes
`on = on or clock_day().isoformat()`. `clock_day()` already exists in the file (CREAITE_NOW's day, else `date.today()`).
Apply with `git apply dev/proposals/clock-tracker/tracker.diff`.

**Why.** `milestone_state(m)` and `suggested_state(m)` called without a date read the real clock, so every test whose fixture holds
absolute dates around 19-10-2026 failed once the real date passed it (a milestone due 19-10 is "Overdue", not "Slipped"; "Late", not
"Expected later"). The dashboard build already passes its own day (`build_dashboard.clock()`); this fixes the callers that do not.

**Why not change `tracker.today()` itself.** It also stamps `created`, `closed`, `actual_date` and the processed.txt line. Making it
follow CREAITE_NOW would change those in every test that sets the clock, and `test_dashboard_data_pinned` and `test_clock_guard`
document that the real day is used there on purpose. The narrow change touches only the state reading.

**Risk.** None outside tests: nothing in `system/scripts` sets CREAITE_NOW (grep: no assignment anywhere), so in production `clock_day()`
is `date.today()` and the result is identical. Call sites that rely on the default `on`: `report.milestones` (fixed in code on this
branch by passing `on`), `propose.milestone_notes` (same), and `tracker.norm_milestone` line ~1121 (`suggested_state(row)`), which
only this diff covers. `build_dashboard` and `sneak_peek` pass `on` already.

**Tests.** With the diff applied alone (without the `report.py` and `propose.py` changes on this branch) test_report_builders_pinned,
test_steerco and test_snapshots pass. The branch's non-guarded changes make them pass without the diff; the diff makes the default
safe for any future caller.
