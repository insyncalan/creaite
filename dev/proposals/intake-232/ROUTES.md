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

## Left: someone else's minutes (Find work items) still go through ask creaite

`irProcess` still sends `process <file> as minutes by someone else` through `askLive` for a file whose kind is minutes. Process's
route cannot take it today:

1. `intake_process.validate_request` accepts only `{path, project}` and `build_prompt` asks for draft minutes.
2. `reach.py` mode `process` (`_process_stage_problem`) refuses a spec without `"transcript"`; someone else's minutes are staged
   with `"as": "minutes"` and `"file"` (minutes.py E1), so the stage step would be refused. `_runs_proposals` and
   `intake_process.staged_paths` also look only at `meeting.transcript` (E1 stages `meeting.source_file`).
3. The guard must know which of the run's files Alan pressed **Find work items** on, or a transcript `.txt` pressed with
   **Make minutes** could be staged as minutes with no draft (BL-260). The server would record it in `run.json`
   (`files_as_minutes`), which only `live_server.py` writes.

Proposed (for Jarvis; guarded: `reach.py`, `live_server.py`):

- `intake_process`: a file may carry `"as": "minutes"`; the prompt says, for that file, "someone else's minutes: read it with
  `minutes.py transcript <file> --minutes` and stage with `"as": "minutes"` and `"file"`, no draft"; `staged_paths` also counts
  `meeting.source_file`.
- `live_server.intake_process`: pass the minutes files to `Run(...)` so `run.json` holds them.
- `reach._process_stage_problem`: when `data.get("as") == "minutes"`, require `data["file"]` in the run's minutes files and none of
  `draft`, `minutes`, `transcript`, `note`; otherwise as today. `_runs_proposals`: accept `meeting.source_file` in the run's files.
- Then `irProcess` sends `{path, as: "minutes"}` through `processLive` and `askLive` leaves the Intake page.

Until then the Find work items row has no Stop of its own (ask creaite's panel has it), and the test
`test_find_work_items_still_goes_through_ask_creaite_until_the_guard_takes_it` keeps that visible.
