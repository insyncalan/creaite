# BL-10 and BL-03 · Archiving items, reports and minutes (v1.9.5, Team 2)

Branch `v195-archiving`, from `origin/v194-archive` (BL-09 complete) with `origin/dev-week-ahead-urgent` (the BL-10 and BL-03 write-ups) merged in. Not pushed.

## Where it stands

**Done:** both items are built and tested.

**Schema:** no change needed. BL-09's `archived` flag on the item tables and the existing `closed` dates are enough. I didn't touch `schema.sql`.

## The daily slot (BL-10)

BL-323's Tidy up isn't on this base (it is on `v193-backups`, not merged into `v194-archive`). So the daily archiving runs in the daily slot that session start and the live server already use:
- **Session start:** `session.py start` runs `archive.py daily` straight after the daily backup.
- **The live server:** a new `archive_timer` runs a minute after start-up, then hourly. It runs under the job lock and is skipped while an ask creaite run is in progress.

Either way it runs at most once a day (`system/staging/archive-state.json`). It never runs in the development repository, and never from an ask creaite run: `archive.ask_run()` checks `system/guard/run.json` and `CREAITE_HEADLESS_RUN` (BL-323's flag), and fails closed.

**When BL-323 merges,** the live server's `backup_timer` can call `archive.daily()` after Tidy up, and `archive_timer` can then go. Session start already has it in the right place, after the backup.

## What was built

**BL-10: items archived for their age, automatically.**
- **`archive.py daily | items [--dry-run]`** (new) picks the items with `tracker.due_for_age_archive`:
  - closed or cancelled actions and RAID items, and done or dropped promises;
  - with a `closed` date `archive.after_months.<table>` months ago or more (6 by default; exactly 6 months counts);
  - not archived already, and not in an archived project.
  It writes one proposal (`source_run: "archive"`, items `{"op": "archive_item"}`, approved) and applies it with `tracker.cmd_apply`. So the change is backed up, logged in change_log and undoable.
- **`tracker.archive_item` checks the rule again.** A hand-made proposal can't archive an open item, a decision, a milestone or a recent one. `archived` still can't be set by an ordinary update.
- **Undo** reverses the flags. The proposal is marked undone and not returned to Review (`_kept_out_of_review`, beside BL-289's card mark).
- **Editing un-archives.** `_update_row` clears the flag when an archived item's fields or labels change, and logs it.
  - **Agreed by Alan (14-10-2026):** the daily run then leaves that item live for a full period from the edit (`unarchived_since`, read from change_log), so it doesn't disappear again the next morning.
- **Client reports:** client-visible items follow the same rule, as Alan decided.
- **The views:** BL-09's `hide_archived` views already filter `archived = 0` on each item table. So archived items leave Work, Today and the Excel export, and search still finds them, marked Archived.
- **Show archived:** the setting's label is now "Show archived projects and items", and it brings the items back.
- **Health:** a new doctor check, `archive_items`, always passes. Its detail is "Archived 5 items on 14-10-2026 …", and Health lists it under a new **Archiving** heading (`health()["archiving"]`, `#healthArchiving`).

**BL-03: reports, minutes and Steerco one-pagers moved into the engagement's own `_Archive` after 12 months, on a yes.**
- **`archive.py reports [--out]`** prints the spec, with one `move` per file and the file block `archive: "reports"`.
  - **What it takes:** weekly reports, client reports, minutes and Steerco one-pagers, dated `archive.reports_after_months` (12) months ago or more by the date in the file name. It looks only directly inside the mapped folders. With the projects in the vault, `reports/` is shared, so files are matched by name and ad hoc documents are left alone.
  - **What it leaves:** transcripts, agendas, documents, undated files, archived projects, and any file whose place in `_Archive` is already taken. The portfolio's minutes are included (Alan's answer 3, below).
- **Health's monthly line.** The doctor check `archive_reports` warns, and Health's title reads "Archive 14 reports and minutes older than 12 months".
  - **Fix it:** **Archive them** (`health_fixes.FIXES["archive_reports"]`, `card: True`). It goes through the existing token-checked `POST /api/health/fix/<id>`, which refuses any body or query string. That runs `archive.py reports` (READ), and the server puts the moves on the BL-258 change card.
  - **Approve** stages the change and applies it through `tracker.py apply`.
  - **Monthly:** once an archive has been applied this calendar month, the check passes ("Archived 14 reports and minutes on …") until the next month.
- **tracker.py:**
  - `_op_move` records `kind`, and the highest folder it made (for example `_Archive/04 Reporting/Weekly`).
  - Undo moves a file back and removes the folders that move made, once they are empty.
- **paths.py:**
  - `archived_file`: `resolve` maps a stored `projects/<folder>/<sub>/<file>` that is no longer there to `<folder>/_Archive/<sub>/<file>`. Stored paths never change.
  - New: `ARCHIVED_FILE_KINDS` and `archivable_folders()`.
- **The card preview** says "Move file A → B" for a file (propose.py `file_op_lines`).

**Settings** (in the defaults and the catalogue, a new Advanced group "Archiving"):
- `archive.after_months.actions`, `.raid` and `.promises`: 6 each;
- `archive.reports_after_months`: 12.
0 turns a kind off. They are also in `system/config/settings.json`.

**Docs:**
- Help: a new "Archiving (Settings › Health)" bullet.
- `dev/dashboard-spec.md`: "Archiving items and reports".
- `creaite-rules.md`: session step 1, the `_Archive` row, `archive.py` in the folder map, and Retention.

## Security changes for Alan/Team 1

1. **`reach.ARCHIVE_MOVES` gains `"reports"`, a new shape in BL-09's one `_Archive` exception (`archive_move_problem`).**
   - **What it allows:** one file, `<root>/<engagement>/<a minutes, weekly, client or Steerco folder>/<file>`, moved to `<root>/<engagement>/_Archive/<same folder>/<file>`.
   - **What it refuses:**
     - a folder, or a file in any other folder (transcripts, documents, agendas);
     - a deeper or different place, or another engagement's `_Archive`;
     - the projects-level `_Archive`;
     - a hidden or `~$` file, a symlink, `..`;
     - anything outside the projects root;
     - a destination that already exists.
   - **What doesn't change:**
     - Only tracker.py's `move` calls it.
     - `classify()` is unchanged, so every `_Archive` is still `never` for ask creaite, for every operation.
     - Archived files resolve into `_Archive` and so classify as `never` (tested).
   - **One shared consequence:** as with BL-09's archive and restore, a spec that ask creaite writes could carry such moves onto the approval card; only Alan's Approve applies them.
2. **`reach.SCRIPT_COMMANDS["archive.py"]`:**
   - `daily`: RECORD;
   - `items`: RECORD, read-only with `--dry-run`;
   - `reports` and `status`: READ.
   `dev/tests/test_record_commands.py`'s list of record commands gains `archive.py daily` and `archive.py items` (a security decision, as that test says).
3. **`session.py start` stays DERIVED but now writes the record once a day** (the archiving, through `tracker.py apply`). An ask creaite run can't trigger it: `archive.daily` returns at once while `system/guard/run.json` exists or `CREAITE_HEADLESS_RUN=1`.
4. **`health_fixes.FIXES["archive_reports"]` (new).** It runs a READ command, and the change waits on the approval card. The map gains `CHECK_FIXES["archive_reports"]`.
5. **The live server's `archive_timer` (new):** a daemon thread that runs only `archive.py daily` through the server's own `run()`, under `LOCK`. No new route.
6. **No permission rule added** to `.claude/settings.json`, and no change to the deny lists.

## Tests

- **`dev/tests/test_archive_items.py` (new), 9 tests**, with the clock pinned:
  - each type and status at the boundary: 14-04 is archived on 14-10, 15-04 the next day, and open items, decisions and milestones never are, even a year on;
  - a period is a setting, and 0 turns a kind off;
  - the run goes through apply, is logged, and undo is exact with nothing in Review;
  - a hand-made proposal can't archive an open, recent, decision or milestone item, and `archived` can't be set directly;
  - an edit un-archives the item for a full period;
  - archived items leave the dashboard data and stay searchable, marked Archived;
  - it runs once a day, never with run.json or `CREAITE_HEADLESS_RUN`, and Health's line and `archiving` show the run;
  - session start runs it;
  - it never runs in the development repository (`--dry-run` still lists).
- **`dev/tests/test_archive_reports.py` (new), 5 tests:**
  - the due set: kinds, the boundary date, the ad hoc, transcript, agenda and document files left alone, and the setting;
  - the Health line and title, and its built Fix it;
  - the move through apply: stored paths resolve, ask creaite can't read the files, they aren't indexed, the line is quiet for the month, and undo restores the files and removes the folders it made;
  - `archive_move_problem`'s refusals, and an apply refusing a transcript move;
  - the live route: 403 without the token, 400 with a body or a query, nothing moves before Approve, the card shows "Move file", and Approve moves the files;
  - the OneDrive layout with mapped folders, with undo.
- **Updated:**
  - `test_record_commands`: the two new record commands.
  - `test_health_fixes`: the fix list, its commands and the check map gain `archive_reports`.
  - `test_portability`: doctor now has 34 checks. It said 30, so it was already stale on `v194-archive` (BL-09's two checks); BL-10 and BL-03 add two more.
  - `test_tracker`: its vault copies `archive.py`.
- **Golden:** `settings-advanced` was re-recorded. The differences are the new Archiving group and the Show archived row's new label and wording, nothing else.
- **Pass:**
  - test_archive_items, test_archive_reports, test_archive_projects;
  - test_guard_pinned, test_reach, test_record_commands, test_script_policy, test_run_read_pinned;
  - test_tracker, test_writer_pinned (no pinned record changed), test_health_fixes;
  - test_settings_catalogue, test_settings_calmer, test_snapshots, test_help, test_portability;
  - test_session_sweep, test_onedrive_projects, test_debug_log_wiring, test_project_names, test_update, test_new_vault, test_file_access, test_search, test_excel, test_propose.
- **`check.py`:** OK.

## Alan's answers (14-10-2026), built on top

Alan approved all six security points above.

1. **Editing an archived item:** my choice stands. The item comes back and stays live for a full period from the edit. Tested by `test_editing_an_archived_item_unarchives_it_for_a_full_period`.
2. **Restoring one archived report:** deferred, a follow-up after v1.9.5. The Product Manager logs it. Not built; undo is the only way back for now.
3. **Portfolio minutes** are archived on the same 12-month rule, into `<portfolio folder>/_Archive/<its minutes folder>/`. Only minutes; never the portfolio's transcripts or anything else.
   - **The new shape** (in `reach._report_archive`, the approved `reports` move):
     - `<projects root>/<portfolio folder>/<its minutes folder>/<file>` → `<projects root>/<portfolio folder>/_Archive/<minutes folder>/<file>`.
     - "The portfolio folder" is `paths.portfolio_dir()`, directly in the projects root: `_Portfolio`, or `projects/_portfolio` in the vault. Its realpath is checked, so a look-alike name elsewhere doesn't qualify.
   - **The code:**
     ```python
     portfolio = _portfolio_folder(pa[0]) if pa else False
     if len(pa) < 3 or len(pb) != len(pa) + 1 or not (_top_folder(pa[0]) or portfolio) or pb[0] != pa[0] or pb[1] != paths.ARCHIVE:
         return False
     if pb[2:] != pa[1:] or pa[-1].startswith((".", "~$")):
         return False
     if portfolio:                                    # the portfolio: its minutes only
         return "/".join(pa[1:-1]) == paths.folder_name("minutes").strip("/")
     return "/".join(pa[1:-1]) in paths.archivable_folders()

     def _portfolio_folder(name):
         pf = Path(os.path.realpath(paths.portfolio_dir()))
         return pf.name == name and pf.parent == Path(os.path.realpath(paths.projects_root()))
     ```
   - **Stored paths:** `paths.resolve` maps `projects/_portfolio/<minutes>/<file>` into the portfolio's `_Archive` once the file has moved, in both layouts. `classify()` is unchanged: anything below `_Archive` is still `never` for ask creaite.
   - **Tests:**
     - `test_portfolio_minutes_move_into_the_portfolios_own_archive` (vault layout): the portfolio's transcripts are refused, and so is another engagement's `_Archive`; the file resolves, ask creaite can't read it, it isn't indexed, and undo puts it back.
     - The OneDrive case gains a `_Portfolio/02 Meetings/Minutes` file.
4. **Restoring a whole project leaves items archived for their age alone.** No column was needed and `schema.sql` is unchanged:
   - `tracker.age_archived_before(con, code)` reads the change log of the project's latest archive (not undone).
   - Of the project's archived items, it keeps those that archive didn't flag. Those were archived for their age before it, and they stay archived.
   - Only the archive's own flags are cleared. Without an archive record, nothing is kept back, as before.
   - Undo of the restore puts the project's flags back exactly.
   - Tested by `test_restoring_the_project_leaves_items_archived_for_their_age`.

## Deferred

- **Restoring one archived report** ("move back"): after v1.9.5 (Alan, 14-10-2026).
