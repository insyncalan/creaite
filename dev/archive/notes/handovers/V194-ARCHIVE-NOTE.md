# BL-09 · Archive and restore whole projects (v1.9.4)

Branch `v194-archive` (renamed from `v193-archive`). It is built on `origin/main`, with these merged in:
- `dev-bl09-skeleton-archive` (the docs);
- `origin/v192-settings-ui` (BL-320's Health and Fix it).

## Where it stands

**Done:** both parts are built and tested.

**Schema:** Alan committed it himself (5bbfbab, his two-flag design):
- `archived` on `projects`, with `archived = 0 OR active = 0`;
- `archived` on `milestones`, `workstreams`, `actions`, `raid`, `decisions` and `promises`.

I didn't edit `schema.sql`.

**Migration:** `tracker.py migrate` rebuilds the changed tables and keeps every row; the existing code does this. `test_archive_projects.Migration` tests it:
- It builds a database with origin/main's schema, which has no `archived`, and puts sample rows in all 14 tables.
- It runs migrate.
- Every row and every value is kept, and every flagged table has `archived` at 0. The other tables are unchanged.
- The CHECK refuses `archived = 1` while `active = 1`, and allows it with `active = 0`.
- A second migrate does nothing.

## What part 2 built

**tracker.py: the archive and restore items.**
- **The items:**
  - `{"op": "archive" | "restore", "table": "projects", "id": CODE}` goes through `archive_project`.
  - **Archive:**
    - It refuses while any item is open: actions Open or Delayed, RAID Open, decisions Pending, promises Open, milestones Planned.
    - It sets `active = 0` and `archived = 1`.
    - It flags every milestone, workstream, action, RAID item, decision and promise of the project.
  - **Restore:** it clears the flags and puts `active` back to its value before the archive.
  - **History:** each field change is logged in change_log; `updated_at` is never touched. The register row and the folder move are also logged as history-only fields (`register_row`, `folder`), so a restore can put them back.
- **Undo:** it reverses everything through the generic undo.
- **Refusals:**
  - `archive_problems` refuses an archive or restore item without its approved file block (`archive: archive | restore`) and exactly its own folder move.
  - Setting `archived` in an ordinary new item or update is refused.
  - A new item, or a change to an item, in an archived project is refused: "archived: restore it first".
- **Inserts:** a new row's `archived = 0` isn't logged, so inserts log exactly what they did before.
- **`hide_archived(con)`:**
  - Temporary views named like the tables leave archived projects out, with their items, links, item labels and updates.
  - They work on read-only connections too, for that connection only.
  - `dashboard.show_archived` turns the hiding off.

**propose.py: archive and restore.**
- `archive CODE [--open | --cancel-open] [--out]`:
  - With open items it stops and lists them, saying "Cancel them all and archive (--cancel-open), or stop".
  - `--open` prints the open items as JSON.
  - `--cancel-open` cancels them in the same proposal: actions, RAID and promises are cancelled, a decision is Withdrawn and a milestone Cancelled. Each carries the note "Cancelled to archive the project".
  - The folder moves to `projects/_Archive/<folder>`, numbered if that name is taken.
  - The register row moves to Retired codes as `| ABC | Name | DD-MM-YYYY (archived) |`.
- `restore CODE [--out]`:
  - It reads the latest archive that hasn't been undone, from change_log.
  - The folder moves back. If the name is taken it gets a number, and the register's folder cell says so.
  - The row returns to Projects, in code order, so a sorted register round-trips exactly.
- Both are classified as READ in `reach.SCRIPT_COMMANDS`, like `close-project`: they print or save a spec, and staging it is still RECORD.

**The views.**
- The dashboard's connections (`build_dashboard.ro_db`) and the Excel export (`excel_sync.db`) go through `hide_archived`.
- The dashboard data adds `project_states` and `settings.showArchived`.
- Reminders, the sweep and matching already skip inactive projects, and the register row is gone from Projects.

**Search.** Items are found in the tables themselves. An archived one carries `archived: true` and "Archived" in its meta. Opening one with Show archived off says so. The files in `_Archive/` aren't indexed; part 1's `project_folders` already skips them.

**Settings › People and projects › Projects and register.**
- A Show archived projects switch, then one row per project with **Archive**. An archived project is listed only with the switch on, and has **Restore**.
- `POST /api/project/archive {code, action, cancel_open}`:
  - The token is checked, and only an upper-case code and archive or restore are accepted.
  - With open items it answers with the list. The page's dialog (`#parchDlg`) offers **Cancel them all and archive** or **Stop**.
  - Otherwise propose.py builds the change and the server puts it on the BL-258 change card (`server_edit_card`). The page opens that card (`pendingEdit`). Approve applies it through `tracker.py apply`, and Undo reverses it.

**cx-edit:** the skill has "archive project ABC" and "restore project ABC".

**Docs:** creaite-rules.md (the skills table), Help (Settings › People and projects) and the dashboard spec ("Archive and restore a project").

**Settings catalogue:** `dashboard.show_archived` is in the defaults and the catalogue (Work and views).

## What part 1 built

**The rename, zz Archive to `_Archive`:**
- **Scope:** code, templates, the Help, creaite-rules.md, BUILD, the dashboard spec, the tests and the settings snapshot.
- **Count:** 44 mentions in 17 files.
- **Kept on purpose:**
  - `paths.OLD_ARCHIVE` and its uses, so the old name is still skipped for one release;
  - BACKLOG, BRD, STATUS, the release notes and the history in `dev/sprints/`, as instructed.

**paths.py:**
- `ARCHIVE` and `OLD_ARCHIVE`.
- `ALWAYS_NEVER_INDEX` now holds both names, `_Templates` and `99 System`.
- The `never_index` default is `_Archive`, `_Templates`, `99 System`.
- `project_folders()` never treats `projects/_Archive` as a project.
- `resolve(stored, archived=True)` maps `projects/<folder>/…` to `_Archive/<folder>/…` when the folder has been archived. A stored path never changes. `archived=False` gives the raw place, which the apply's own moves use.
- `old_archive_folders()` lists the folders still called zz Archive, in the projects root and in each engagement.
- `skeleton_old_archive()` lists the skeleton's zz Archive folders (a folder listing only).

**update.py:**
- `rename_archive_folder()` replaces `zz Archive` with `_Archive` in a saved `locations.never_index`, in its place, and keeps every other value. This is the only saved value an update changes.
- It runs both in `merged_changes` (an install) and in `tidy`.
- The settings log keeps the old value, and the update's preview says what it does.
- It does nothing the second time.

**reach.py:** `archive_move_problem(src, dst, kind)` is the agreed guard exception (see the security section below).

**tracker.py:**
- **The `move` file operation:**
  - It needs a block marked `archive: "archive" | "restore" | "rename"`, and it asks reach.
  - It makes `_Archive` if needed and moves the whole folder.
  - Undo moves the folder back, and removes `_Archive` if this move made it and it is empty again.
- **Other file operations** (copy, write, remove, mkdir) are now refused inside `_Archive`, `zz Archive`, `_Templates` or `99 System` below the projects root. The one exception is a mkdir of the folder itself, which a new project's empty `_Archive` from the skeleton needs.

**propose.py:**
- `old-archives [--out]` prints the spec that renames each zz Archive folder (exit 1 when there is none). A folder that already has an `_Archive` beside it is left alone, and the command says so.
- `folder_ops` names any `zz Archive` copied from the skeleton `_Archive`.
- The preview shows "Move folder A/ → B/".

**Health:**
- **Two new doctor checks:**
  - `old_archive_folders` warns and names the folders still called zz Archive.
  - `skeleton_archive` warns while the skeleton still holds a zz Archive. The fix is manual: rename it in Finder, because creaite never writes in `_Templates`.
- **The Fix it:** `health_fixes.FIXES["old_archive"]` has `card: True`. `POST /api/health/fix/old_archive`, with an empty body, runs `propose.py old-archives`. That command only prints the change. The live server puts it on the BL-258 change card (`server_edit_card`). Health.jsx then opens that card in ask creaite (`pendingEdit`). **Approve** stages and applies it through `tracker.py apply`.

**Docs:** creaite-rules.md (a `projects/_Archive/` row and a never_index note), Help (Settings › Health), the dashboard spec (an "Archive folders and Health" section) and BUILD.

## Security changes for Alan/Team 1

1. **`reach.archive_move_problem` (new) is the one exception Alan agreed.**
   - **What it allows:** whole-folder moves in three shapes, and nothing else:
     - archive: `<root>/<project folder>` → `<root>/_Archive/<name>`;
     - restore: the reverse;
     - rename: `<root>[/<engagement>]/zz Archive` → `_Archive` in the same place.
   - **What it refuses:** symlinks, `..`, `_` and hidden folders, anything outside the projects root, a destination that already exists, and any file.
   - **Who calls it:** only tracker.py's `move` operation.
   - **What doesn't change:** `classify()`, so `_Archive` and `zz Archive` are still `never` for every operation, and filechange.py and the hook are refused as before.
   - **Reason:** BL-09's guard decision (Alan, 14-10-2026).
2. **`SCRIPT_COMMANDS["propose.py"]["old-archives"] = READ`.** It only prints or saves a spec, like `close-project`. Staging the spec is still `propose.py stage` (RECORD).
3. **`health_fixes.FIXES["old_archive"]` (new).** It runs a READ command, and the change then waits on the approval card. `test_health_fixes` now allows a fix marked `card` to run a READ command. The fix map gains `old_archive_folders → old_archive`.
4. **`tracker.safe_path` is stricter.** Copy, write, remove and mkdir into `_Archive`, `zz Archive`, `_Templates` or `99 System` below the projects root are now refused. Before, `safe_path` didn't check these names at all. The reason is so a stale proposal can't file into an archived project's folder through `resolve`'s mapping.
5. **The deny lists name `_Archive` only (Alan, 14-10-2026: `_Archive` only; `zz Archive` still never via `classify()`).**
   - `paths.never_index()` and `never_index_patterns()` (ask creaite's deny tools, the permission patterns) name `_Archive`, `_Templates` and `99 System`, as before with `_Archive` in place of `zz Archive`.
   - `paths.skipped_names()` (new) adds `zz Archive` for one release. Listing, indexing, documents, `reach.classify()`, `tracker.safe_path` and the permission panel's path check use it, so a `zz Archive` folder stays `never` for ask creaite until it is renamed.
   - `test_file_access` and `test_onedrive_projects` keep their `_Archive`-only exact lists; `test_archive_projects` checks both functions and that no deny pattern names `zz Archive`.
6. **Approval-card wording.** BL-09 says the rename "goes on the approval card". filechange.py moves single files only, and `_Archive` is `never` for it, so the rename uses the BL-258 change card instead. It is approved there and applied by `tracker.py apply`, which keeps to the guard decision that only the apply moves folders into `_Archive`.

All the guard tests pass unchanged: test_guard_pinned, test_reach, test_record_commands, test_script_policy and test_run_read_pinned.

7. **Part 2 adds no new guard exception.** Archive and restore use part 1's `move` and `archive_move_problem`. `POST /api/project/archive` is a dashboard-only route: it checks the token and the code pattern, and runs only `propose.py archive|restore` (READ). Its change waits on the approval card.

## Tests

- **`dev/tests/test_archive_projects.py`: 23 tests, all passing.**
  - **Part 1 (14):** as before.
  - **Part 2 (9):**
    - open items are listed, and nothing is archived with one open; an archive without its folder move is refused;
    - archive, then undo, round-trips exactly: rows, register, files and search;
    - archived items leave the dashboard data and the Excel export, stay in search marked Archived, have their files left out of the index and can't be read by ask creaite; their links still resolve; Show archived brings them back;
    - no new items in an archived project; the code is never reused; `archived` can't be set by hand;
    - restore reverses each step and round-trips exactly, and an undo of the restore archives again;
    - a restore never overwrites: a taken name gets a number and the register says so;
    - the OneDrive layout round-trips: an engagement goes into `<root>/_Archive` and back, with the register restored exactly;
    - the migration test (above);
    - the live route: a bad code is refused, open items come first, then the card; nothing changes before Approve; Approve archives; Restore by the card brings it back.
- **`test_health_fixes`:** the old_archive Fix it routes.
- **Passing:**
  - test_tracker, test_schema_sprint5, test_writer_pinned;
  - the guard tests: test_guard_pinned, test_reach, test_record_commands, test_script_policy and test_run_read_pinned;
  - test_search, test_search_eml, test_search_live and test_search_dashboard;
  - test_settings_calmer, test_update, test_onedrive_projects, test_file_access, test_health_fixes;
  - test_excel, test_propose, test_recode, test_ask_change_card, test_dashboard_data_pinned;
  - test_new_vault, test_agendas_files, test_people (with test_people_dashboard and test_people_filters);
  - test_snapshots, test_help and test_help_loop.
- **Pinned records updated:**
  - **Writer:** 18 of `dev/tests/pinned/*.json` were re-recorded. A script compared them with the old records: every difference is the new `"archived": 0` in a row, nothing else.
  - **Kept:** `old-code.sql` and `old-code-undo.json` stay as they were. Undo on a database written by the code before BL-09 still gives the old result.
- **Snapshots:**
  - `settings-advanced`: the `never_index` default (part 1).
  - `settings-people`: the Show archived switch and the Archive buttons.
- **Not covered:** no Chrome test clicks Archive or the open-items dialog. The route and the card are tested through the live server.
- **`check.py`:** OK.
