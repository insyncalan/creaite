# #252 design: one archive folder name, 99 Archive

## Every place that names the folder

- **paths.py** (ordinary): `ARCHIVE = "99 Archive"`, `LEGACY_ARCHIVE = "_Archive"`, `OLD_ARCHIVES`, `ARCHIVE_NAMES`; `ALWAYS_NEVER_INDEX` holds 99 Archive and `_Archive`; `archive_name(base)` (the folder in use at a place), `is_archive_name`, `archive_alias` (a path under a renamed old folder follows into 99 Archive; the folder itself is never mapped, so undo works); `resolve`, `archived_path`, `archived_file`, `archive_dir`, `old_archive_folders` (now also the portfolio), `skeleton_old_archive`, `skipped_names`, `never_index_patterns` (never `zz Archive`, as BL-09 agreed), the notes shapes.
- **Ordinary callers**: `archive.py` (12-month reports move, Delete note), `propose.py` (project archive, `old-archives` rename spec, a skeleton's old name made as 99 Archive), `doctor.py`, `health.py`, `health_fixes.py` (Rename to 99 Archive, on the card), `update.py` (renames the saved `never_index` value only), `locations.py`, `build_dashboard.py`, the dashboard's `files.js`, `settings.js`, `notes.js`, `ask.js`, `DeleteNote.jsx`, `help.md`, `settings-defaults.json`, cx-edit's skill.
- **Guarded** (this folder's diffs): `reach.py` (`archive_move_problem` shapes), `live_server.py` (`existing_project_folder`, ask creaite's prompt), `permissions.py` and `tracker.py` (wording), `creaite-rules.md`.

## The migration

1. The update renames `_Archive` and `zz Archive` in the saved `locations.never_index` to `99 Archive`. No folder is moved at update time.
2. Until a place is renamed, `archive_name` keeps using its `_Archive`, so one place never gets two archive folders. `zz Archive` is never a destination.
3. Health names every old folder (root, engagements, portfolio) and offers **Rename to 99 Archive**: a `move` of kind `rename` on the approval card, applied by `tracker.py apply`, undoable. Two old folders in one place are never merged (the second is left and named).
4. All three names are skipped, resolved and on ask creaite's never list for one release; then `_Archive` and `zz Archive` are dropped.

## Risks

- **Client files moved**: the rename moves whole OneDrive folders that may hold other people's files. Mitigation: only on Alan's approval, shown first, undoable, never merged, never at update time.
- **Broken links after the rename**: mitigated by `archive_alias`; tested for an archived project, a report and a deleted note.
- **Landing order**: `reach.py` today names `paths.OLD_ARCHIVE`, which the branch removes; the branch and `reach.diff` land together.
- **Guard widening**: a move out may now start in any old name, which is wider than before only by the names that existed; a move in is narrower (the folder in use only). Classify and the never list are unchanged.
- **#255**: textual conflicts in comments and rules only (README).

## Test plan

- `dev/tests/test_archive_folder_99.py` (20 tests, fail first on e8ee48dc): names and defaults, never for ask creaite, the name in use, stored paths under each name and after the rename, the moves, Health's offer and the card, never merging, the update, the guarded shapes (`GuardedMoves`, needs `reach.diff`) and `existing_project_folder` (needs `live_server.diff`).
- Regression, one at a time: the archive, reach, card-only, notes delete, Health, OneDrive, update and portability tests.
- Release hand check: rename a fictional vault's `_Archive` from Health, open an archived report and a deleted note, undo, and restore an archived project.
