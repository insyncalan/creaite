# Sprint: Debug log, part 1 (BL-102)

**Status (09-10-2026): merged into `main` (`c37c1f7`, 00:58); worktree removed. Part 2 is in `debug-log-2.md`.**

Branch `sprint-debug-log`, worktree `../creaite-debug-log`, made from `main` on 2026-10-09. Runs beside `sprint-permissions`, `sprint-sweep-alerts`, `sprint-pages`, `sprint-4a` and `sprint-5`. Read BL-102 in `dev/BACKLOG.md` first; it holds Alan's decisions.

## Goal

A log that keeps the last 7 days, written through one small helper that can never break a script, with the pieces that need no wiring into other sprints' files: the helper, its settings and path, the `doctor.py` check, the session-start status line, and tests. **Part 2** (after the other sprints merge) adds the calls in `tracker.py`, `sweep.py`, `minutes.py`, `review.py`, `report.py`, `excel_sync.py`, `build_dashboard.py`, `update.py` and `live_server.py`, the browser error route, the read allow list, Settings › Diagnostics, Copy diagnostics, and the rules text.

## Alan's decisions (BL-102, 2026-10-09)

- **One file per day** (`system/logs/debug-YYYY-MM-DD.log`), keeping today and the six days before it (seven files); the oldest goes when the first entry of a new day is written. No background job.
- **One plain-text line per entry:** time, level, area, message. A traceback adds indented continuation lines.
- **Levels:** `logging.level` in settings (`info` by default, `debug` when chasing a fault); `warn` and `error` are always written.
- **Size cap:** about 5 MB per day's file, then one line saying so and nothing more that day.
- **A write never raises.** If the log can't be written, the script carries on.
- **Never in the log:** the text of mail, Teams messages, transcripts, minutes, invites, notes or chats; Current state; images. Item IDs, file paths, project names and counts are fine.
- **Local only:** not in git, not in the daily backup, not in the OneDrive copy, not replaced by an update.

## Items

Commit each separately, in this order.

### 1. The helper, `system/scripts/log.py`

Standard library only. It takes its location and its setting from `paths.py`.

- `log.debug / info / warn / error(area, message)` and `log.exception(area, message)` (the message plus the current traceback).
- A message is one line: newlines and control characters become spaces and it is cut at 500 characters. Callers pass a short description, never content.
- `log.run(script, command)`: a context manager that logs the start, the time taken and the exit status, and an error with its traceback if the block raises (it re-raises). This is what part 2 puts around each script's `main`.
- Timestamps use the local clock, and honour `CREAITE_NOW` (as `sweep.now()` does) so tests are predictable.
- **Pruning:** when the first entry of a day creates that day's file, files dated before (today − 6 days) are deleted. `log.prune()` does the same on request.
- **Size cap:** at 5 MB the day's file gets one line, "log full for today: later entries are not kept", then nothing more.
- **Several processes at once:** each line is one append, written in a single call.
- **Reading:** `log.files()`, `log.tail(n)`, `log.errors_since(hours)` (the ERROR lines newer than that), `log.repeated(days, minimum)` (errors with the same area and message, digits ignored, seen at least `minimum` times).
- **Never raises:** every public function catches its own errors (a read-only folder, a full disk, a bad setting) and carries on.

### 2. Where and how it is set

- `paths.py`: one added line, `LOGS = SYSTEM / "logs"`.
- `settings.json` and `system/templates/settings-defaults.json`: a `logging` block with `level` (`info`), `max_mb` (5) and `keep_days` (7), so an update adds it and keeps any value Alan sets.
- `.gitignore`: `system/logs/*`.
- The rules text (folder map, Retention) and `help.md` are left for part 2, so this sprint doesn't touch `creaite-rules.md`.

### 3. `doctor.py` and the session-start status line

- **doctor:** "Debug log": the logs folder can be created and written (a probe file, as the other write checks do), the level is valid, and repeated errors in the last 7 days are listed as a warning (never a failure): "BL: 3 × tracker apply failed".
- **session.py:** `status()` gains `log_errors` (the ERROR lines in the last 24 hours), and the status line adds "2 errors in the last 24 hours (system/logs/)" when there are any. The sweep failures from `run-log.txt` stay as they are.

### 4. Tests, and a short note in `dev/BUILD.md`

`dev/tests/test_debug_log.py` (see Done when), and a "Debug log, part 1 (BL-102; sprint-debug-log)" section in `BUILD.md` saying what is built and what part 2 wires in.

## Boundaries

- **Owns:** `system/scripts/log.py` (new), `dev/tests/test_debug_log.py` (new), `dev/archive/sprints/debug-log.md`, and small additions to `paths.py` (one line), `doctor.py` (a new check and one `check(...)` line), `session.py` (the status field and line), `settings.json`, `settings-defaults.json`, `.gitignore` and `dev/BUILD.md`.
- **Don't edit:** `tracker.py` (Sprint 5), `sweep.py` and `minutes.py` (`sprint-sweep-alerts`, `sprint-4a`), `live_server.py` (`sprint-permissions` and others), `dashboard.html`, `report.py`, `docx_tools.py`, `creaite-rules.md`, `help.md`, `BACKLOG.md` and `BRD.md` (updated at merge).
- **Shared files** (`paths.py`, `doctor.py`, `session.py`, `settings.json`): add, never reformat or move existing lines, so the merge stays readable. Put new code in its own marked section.
- **Development guard:** sample data and temporary vaults only; never connect to Microsoft 365.

## Done when

**Tests (`dev/tests/test_debug_log.py`, temporary vaults, fixed clock):**
- a line has the time, level, area and message on one line; a message with newlines becomes one line; a long message is cut;
- a traceback is written as indented continuation lines under its entry;
- entries on different days go to different files; the first entry of a new day deletes a file dated 7 days before and keeps one dated 6 days before; `prune()` does the same;
- the size cap stops a flood with one notice line;
- a read-only logs folder, a bad setting and an unwritable disk do not stop the caller;
- `info` hides debug lines and `debug` shows them; warn and error are always written;
- `run()` logs the start, the duration and the exit, an exception with its traceback, and re-raises;
- two processes writing at once lose no lines;
- `errors_since` and `repeated` count correctly across days;
- `doctor.py` reports the log as writable, and warns (not fails) on repeated errors;
- `session.py start --json` shows `log_errors`, and the status line mentions them only when there are some;
- an update (`update.py`) keeps `system/logs/` and the `logging` setting, and adds `logging` to an older `settings.json`.

The full suite passes: `python3 dev/tools/run_tests.py`.

**Docs:** a short section in `dev/BUILD.md`.

**Commits:** each item committed separately on `sprint-debug-log`, with the attribution lines from the session's instructions. Never push or merge.

## Hand-offs

(Changes needed in files another sprint owns. Part 2 is the main one: the calls in `tracker.py`, `sweep.py`, `minutes.py`, `review.py`, `report.py`, `excel_sync.py`, `build_dashboard.py`, `update.py` and `live_server.py`; the browser error route and Settings › Diagnostics in `live_server.py` and `dashboard.html`; the read allow list; `creaite-rules.md` and `help.md`.)
