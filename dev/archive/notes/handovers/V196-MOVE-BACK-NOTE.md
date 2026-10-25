# BL-331 · Move back one archived report (after v1.9.5, Team 2)

Branch `v196-move-back`, from `origin/v195-archiving` (ce7340a). Not pushed. No schema change; `schema.sql` untouched.

## Where it stands

**Done:** built and tested, with Alan's three answers (14-10-2026) below built in.

## What was built

- **Files › Archived.** A new **Archived** chip in Files. It shows only while there are archived files. It lists the reports, minutes and Steerco one-pagers that BL-03's archive moved and that are still in an `_Archive`, either an engagement's or the portfolio's.
  - Each row is tagged **Archived** and has **Move back** in place of Open folder. No other row in Files has Move back.
  - The name still opens the file, through its stored path.
- **Where the list comes from:** the apply records only (`archive.archived_moves`).
  - A file counts when an apply that hasn't been undone made a `move` of kind `reports` for it, and no later apply that hasn't been undone made a `move` of kind `reports_back` for it.
  - The list holds names, sizes and dates. Nothing in `_Archive` is read.
  - It is in the dashboard data as `files_archived`, and `/api/files` returns it as `archived`.
- **Move back:** `POST /api/files/move-back {path}`.
  - It needs the token and takes `path` (the stored path) and nothing else.
  - `archive.back_spec` builds one `move`, from `<…>/_Archive/<folder>/<file>` to `<…>/<folder>/<file>`, in a file block with `archive: "reports_back"`.
  - The server puts it on the existing change card (`server_edit_card`), which shows "Move file A → B". **Approve** applies it through `tracker.py apply`.
- **Refused:**
  - when the original place is taken: nothing is overwritten (see "One difference from the backlog" below);
  - when the file isn't one an archive moved. `back_spec` says so, and `tracker.check_move` checks the apply records again at apply.
- **Undo** (`tracker.py undo`) moves the file back into `_Archive`. If its `_Archive` folder has gone, undo makes it again.
- **Stored paths** never change. Once the file is back, `paths.resolve` finds it in place. After an undo, it finds it in `_Archive` again.
- **Search:** the apply's search refresh indexes the file again once it is back, and `search.py query` finds it. After an undo it is no longer indexed.

## Security changes for Alan/Team 1

1. **`reach.ARCHIVE_MOVES` gains `"reports_back"`, the exact reverse of the approved `reports` shape.**
   - **The code:** `_move_shape("reports_back", pa, pb)` is `_report_archive(pb, pa)`, BL-03's own check with its two ends swapped. So it allows exactly:
     - `<projects root>/<engagement>/_Archive/<minutes, weekly, client or Steerco folder>/<file>` → `<projects root>/<engagement>/<that folder>/<file>`;
     - `<projects root>/<portfolio folder>/_Archive/<its minutes folder>/<file>` → `<projects root>/<portfolio folder>/<minutes folder>/<file>`.
   - **What it refuses (tested):**
     - another engagement, another folder, a deeper place or the engagement root;
     - transcripts, and the portfolio's transcripts;
     - a folder, `..`, a symlink, or a hidden or `~$` file;
     - anything outside the projects root;
     - a destination that already exists;
     - the other direction.
   - **Small refactors, no change in behaviour:**
     - `reach.FILE_MOVES = ("reports", "reports_back")` names the one-file kinds.
     - The refusal wording moved into `_not_the_shape()`, to keep `archive_move_problem` under the complexity limit.
   - **What doesn't change:**
     - `classify()` is unchanged: anything in `_Archive` is still `never` for ask creaite, for every operation (tested).
     - Only tracker.py's `move` calls `archive_move_problem`.
2. **`tracker.check_move` adds a check for `reports_back`:** the file must be one an archive moved. In the apply records, the latest `reports` move that hasn't been undone must have moved this file's original path to this exact `_Archive` path, and no later move back may have undone it. A file put in `_Archive` by hand, or a path that only looks right, is refused.
3. **ask creaite can't do a move back** (stricter than BL-03's "a spec ask creaite writes could reach the card"):
   - `live_server.build_edit_card` refuses a model's `CHANGE:` spec with `archive: "reports_back"`: "an archived file is moved back from Files (Move back), never from ask creaite".
   - `propose.py stage` refuses a `reports_back` spec unless the spec file is in `system/guard/`, where only the live server writes its card snapshot. This closes the confirmed-run path (BL-306), where ask creaite stages through `propose.py stage` from `system/staging/drafts/`.
   - No new script command, so `reach.SCRIPT_COMMANDS` is unchanged. No permission rule was added, and the deny lists are unchanged.
4. **New route `/api/files/move-back`,** in `ADMIN_ROUTES` beside `/api/project/archive`. It is token-checked, takes only `path`, and only puts the move on the card.

## One difference from the backlog (Alan: refuse, as built)

BL-331 says a taken name "gets a number". Following the build brief, a taken place is **refused** instead, and nothing is overwritten. The card says to rename or move that file first. Adding a number would also need a third shape in the guard, a renamed move back, so I didn't widen it.

Alan confirmed refusing (14-10-2026).

## Question for Alan (answered: never offered again, built)

A moved-back report is still older than 12 months, so the monthly line would have offered it again. Alan's answer is point 3 below.

## Tests

- **`dev/tests/test_archive_move_back.py` (new), 10 tests:**
  - Files lists only the archived files, marked archived, with the right project, folder and sub. The ordinary list never has them.
  - Move back through apply: the card's "Move file" line, the stored path resolves in place, the file is indexed and found by `search.py query`, it leaves the archived list, and undo puts it back in `_Archive`, unindexed and `never`.
  - A moved-back file is never offered again: `archive.py reports` offers only a new old file, then nothing, and the due count is 0; undoing the move back clears it from `moved_back()`.
  - Portfolio minutes move back into the portfolio.
  - Refused when the place is taken, at `back_spec`, at stage and at apply. The existing file is unchanged.
  - Refused for a file the archive didn't move, at `back_spec` and at apply. Also refused: a path with `..`.
  - `reports_back` accepts only the exact reverse shape (nine refusals).
  - ask creaite: `classify()` gives `never` for read, change, move, delete and create. `propose.py stage` from drafts is refused. A `CHANGE:` card is refused.
  - The route: 403 without the token, and 400 with an extra field or a path that isn't text. A transcript is refused. Nothing moves before Approve. The card's title and line are as expected, and Approve moves the file.
  - In Chrome: the Archived chip, Move back on every archived row and on no other row, the card, and Approve.
- **Updated:** `test_pages`, whose two exact key lists for `/api/files` and `files_view()` gain `archived`.
- **Pass:**
  - test_archive_move_back, test_archive_reports, test_archive_projects;
  - test_guard_pinned, test_reach, test_record_commands, test_script_policy, test_run_read_pinned, test_permission_panel;
  - test_file_access, test_snapshots, test_help, test_pages, test_live_server, test_portability;
  - test_dashboard_data_pinned, test_tracker, test_propose, test_writer_pinned, test_dashboard_split, test_search, test_ask_change_card, test_agendas_files, test_health_fixes, test_onedrive_projects.
- **Goldens:** none re-recorded. The chip only shows when there are archived files, and the sample data has none.
- **`check.py`:** OK.

## Docs

- **Help:** the Archiving bullet gains how to move one back.
- **`dev/dashboard-spec.md`:** "Move back one (BL-331)" under Archiving items and reports.
- **`archive.py`'s description:** a BL-331 paragraph.

## Alan's answers (14-10-2026), built on top

1. **The guard change is approved as built:**
   - `reports_back`, BL-03's shape reversed;
   - `check_move`'s origin check;
   - ask creaite refused;
   - the route, which only puts the move on the card.
2. **A taken place: refuse, as built.** No number is added.
3. **Moved-back files are never offered again.**
   - `archive.moved_back()` reads the stored paths moved back from the apply records: the `reports_back` moves of applies that haven't been undone.
   - `archive.due_reports` leaves those paths out, so Health's monthly "Archive N reports and minutes" line never counts or offers them again.
   - Undoing the move back puts the file in `_Archive` again, and its path leaves `moved_back()`.
   - Tested by `test_a_moved_back_file_is_never_offered_again`.

