# #232 on 2.5.3's routes: what is wired, and the one guarded step left

Branch `v26-232-next` (2.6 Intake line `p260-r-fix` + `v253-release`).

## Wired (no guarded file)

- **Process** on the one Intake page (List, Board, Two panes, Enter, Process all ready, Today's day line through
  `irProcessById`) runs Process's own run kind: `processLive` (moved from the retired `intake.js` to `core/intakeApi.js`),
  `POST /api/intake/process`. No ask creaite message, the panel stays closed. A calendar meeting's project goes with the file only
  when Alan chose it (`mtgProcessFile`, #264 S6). The running row shows the run's step and **Stop** (`/api/ask/stop` with the run's
  ID). A file the run could not finish comes back on its row as "Needs you: <question>" (or "Not staged") with **Ask creaite about
  this**, which fills the panel's box and sends nothing. The closure line is the snack.
- **Refresh** (the icon beside "Calendar read", and Today's Refresh calendar through `irRefreshCalendar`) runs the calendar's own run
  kind: `calendarLive`, `POST /api/calendar/refresh`. The line says "Refreshing… <step>", the icon is **Stop** while it runs, the
  closure is the snack.
- `askLive` is no longer imported by `core/intakeApi.js`. Tests: `test_intake_review_routes.py` (7, red first on `p260-r-fix`).

## Find work items (someone else's minutes): on Process's route too

`irProcess` sends `{path, as: "minutes"}` through `processLive` (no `askLive` on the Intake page any more; Stop on the row).
`intake_process.py` takes `"as": "minutes"` (plain code, on the branch). The guard's half (`run.json` `files_as_minutes`,
`_process_stage_problem` and `_runs_proposals` for `meeting.source_file`) is the guarded proposal in
`dev/proposals/intake-232-minutes/`; until it is applied the run stages nothing for such a file (fail closed: "Not staged").
