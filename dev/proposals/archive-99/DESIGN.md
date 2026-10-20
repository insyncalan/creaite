# #252 design: one archive folder name, 99 Archive

## Every place that names the folder

- **`paths.py`** (ordinary): `ARCHIVE = "99 Archive"`, `OLD_ARCHIVES = ("_Archive", "zz Archive")`, `archive_names()`, `is_archive_name` (whole name, any case), `is_skipped`, `archive_dirs(base)` (the archive folders in a place: 99 Archive first, never a symlink), `follow_stored` (a recorded path whose archive folder was renamed by hand is followed; never across engagements, never a symlink, never `..`), `canonical_archive`, `free_archive_path`, `archive_dir`, `archived_path`, `archived_file`, `resolve`, `skipped_names`, `never_index`, `never_index_patterns` (never `zz Archive`, as BL-09 agreed), `ALWAYS_NEVER_INDEX`, the notes shapes (`NOTES_SHAPES`, `notes_places`), `project_path_problem`.
- **Ordinary callers:** `archive.py` (12-month reports move, Delete note, Files › Archived, Move back), `propose.py` (project archive and restore, a skeleton's old name made as 99 Archive), `locations.py`, `doctor.py` and `health.py`/`health_fixes.py` (the two old-name checks and the Fix it removed), `update.py` (adds 99 Archive to a saved `never_index`), `build_dashboard.py`, `settings_catalogue.py`, the dashboard's `notes.js`, `ask.js`, `settings.js`, `DeleteNote.jsx`, `help.md`, `settings-defaults.json`, `settings.json`, cx-edit's skill.
- **Guarded** (`guarded.diff`): `reach.py` (`archive_move_problem` shapes, `ARCHIVE_MOVES`, `ARCHIVE99`), `tracker.py` (`check_move` through `follow_stored`; comments), `live_server.py` (`existing_project_folder`, the page-folder walk, ask creaite's prompt, comments), `permissions.py` (the refusal names the folder). And `creaite-rules.md` (`rules_edit.py`).

## No migration

Nothing is renamed or moved at update time or by a Health offer. An update adds `99 Archive` to a saved `never_index`; the two old names stay in it. Alan renames his own folders when he likes.

## Lookup order

New items go to `99 Archive` (decision A in the README). A stored path is looked up literally first; if nothing is there and it names an archive folder, the same path under the other names is tried, `99 Archive` first, then `_Archive`, then `zz Archive`. When two archive folders hold the same stored path the first wins.

## Risks

- A mis-compared name moves client files into the wrong folder: destinations must be exactly `99 Archive`; look-alikes are refused; tested.
- A hand-renamed folder breaks a record: followed (`follow_stored`), tested for restore, Files › Archived, Move back, Undo and `check_move`.
- A follow reaches another engagement, a symlink, or leaves through `..`: it cannot (tested).
- One release only: after it `OLD_ARCHIVES`, the `paths.OLD_ARCHIVE` alias and the old-name arms must go.

## Test plan

`dev/tests/test_archive_99.py` (the always-run part and the part that needs `guarded.diff`, marked by `reach.ARCHIVE99`), the updated older archive tests, `test_reach`, `test_file_access`, `test_permissions`, `test_fast_save`, `test_pages`, `test_notes_delete`, `test_no_real_names`, `check.py`.
