# #252: the archive folder is called "99 Archive" (proposal for the guarded files)

**Status: a proposal for Jarvis and Alan. Four guarded files change (`reach.py`, `tracker.py`, `live_server.py`, `permissions.py`); nothing guarded is edited on this branch.** The rest (`paths.py`, `archive.py`, `propose.py`, `update.py`, `locations.py`, `doctor.py`, `health.py`, `health_fixes.py`, the dashboard, the help, the tests) is ordinary and is already on branch `proposal-252`.

## What Alan decided (20-10-2026)

1. **No migration and no Health rename offer.** Alan renames his own existing archive folders by hand.
2. The old names (`_Archive`, `zz Archive`) are **still read and skipped for one release, then dropped**.
3. Stored paths stay `projects/<folder>/…`.
4. Archived projects (`<projects root>/99 Archive/<engagement folder>`) and each engagement's own archive folder use the same one name.

## What changes, in plain words

- **New archive moves go to `99 Archive`, and nowhere else**: archive a project, the monthly "archive old reports and minutes" move, Delete note.
- **For one release the two old names still work for reading.** A stored path under `_Archive` or `zz Archive` still opens; both are still skipped by search and extraction; ask creaite still cannot read or write them. If an old folder and `99 Archive` both exist, **both are read and `99 Archive` is looked at first**.
- **Moving something out of an old folder still works**: restore a project that an earlier release archived into `_Archive`; Move back for a report or a note an earlier release archived. Moving something *into* an old name does not.
- **The "rename zz Archive" offer is gone**: no Health problem, no Fix it, no `propose.py old-archives`, no `rename` kind of folder move, no doctor complaint about old names. A project made from a skeleton that still holds `_Archive` or `zz Archive` gets `99 Archive`.
- **Settings:** `locations.never_index` defaults to `99 Archive, _Archive, zz Archive, _Templates, 99 System`. An update **adds** `99 Archive` to a saved list (and no longer renames `zz Archive` there); nothing is removed.
- **A folder Alan renames by hand is followed.** An apply's record keeps the archive folder's name as it was (`projects/_Archive/…`), so after Alan renames it to `99 Archive` the stored path no longer exists. `paths.follow_stored` (used by `paths.resolve`) then looks for the same stored path under the other archive names (99 Archive first), so Restore project, Files › Archived, Move back and Undo keep working, whichever way round the record and the folder are named. `archive.archived_moves` returns its keys in that followed form; `tracker.check_move` looks the source up through it (one line in the guarded diff).
- Names are judged **whole and as macOS judges them**: `99 archive` is the archive; `99 Archivement` and `99 Archive ` (trailing space) are ordinary folders.

## What is in the guarded diff (`guarded.diff`, about 360 lines, `patch -p1`)

| File | Change |
|---|---|
| `reach.py` | `ARCHIVE_MOVES` loses `rename`; `_old_archive_rename` removed. New helper `_archive_part(name, old)`. `archive` and `reports` and `notes` moves must end in exactly `99 Archive`. `restore`, `reports_back` and `notes_back` may start in `99 Archive`, `_Archive` or `zz Archive`. A `SCRIPT_COMMANDS` entry (`old-archives`) is removed. Marker `ARCHIVE99 = True`. |
| `tracker.py` | `check_move` looks the move's source up through `paths.follow_stored` (a record that says `_Archive` for a folder now called `99 Archive`, or the reverse); the `move` refusal says "an archive or a restore"; comments. |
| `live_server.py` | `existing_project_folder` (the rule that stops `/api/fs` creating a `CLAUDE.md` in a made-up folder) used only the saved `never_index` list, so it would let `99 Archive` through (it has no leading underscore). It now asks `paths.is_skipped(name)` (also ignores case). The page-folder walk uses the same. Prompt text and comments. |
| `permissions.py` | The "never read or written" test uses `paths.is_skipped` (case-insensitive) and names `99 Archive`. Comment. |

`ask creaite`'s deny patterns come from `paths.never_index_patterns()` (ordinary): `99 Archive` and `_Archive` are denied; `zz Archive` is guarded by `reach.classify` but not named, as before.

The diff needs the ordinary branch (`paths.is_skipped`, `paths.OLD_ARCHIVES`): apply that first.

## How to apply, how to undo

```
git merge proposal-252                                   # or cherry-pick f74ce105 and its follow-ups
git apply dev/proposals/archive-99/guarded.diff          # or: patch -p1 < dev/proposals/archive-99/guarded.diff
python3 dev/proposals/archive-99/rules_edit.py system/creaite-rules.md --check   # 12 sentences; then again without --check
```

- **Checked:** `guarded.diff` applies cleanly (`git apply --check`) to `origin/main` (dcd8a7b6) **and** to `origin/v252-release` (fd60c7c0). `patch -p1 --dry-run` is clean on main.
- `rules.diff` is the same rules change as a diff against `origin/main` only (it does not apply to `v252-release`, whose rules text has moved on); `rules_edit.py` works on both because it replaces exact sentences and refuses unless each occurs once. The rules file is replaced by updates, so it is not part of `guarded.diff`.
- **Undo:** `git apply -R dev/proposals/archive-99/guarded.diff` (and revert the ordinary commits). Without the diff the branch still works for the new name (the guarded code reads `paths.ARCHIVE`), but an old-name restore or move back is refused and `rename` is still accepted until the diff lands.

## Which tests prove it

- `dev/tests/test_archive_99.py` (new): ordinary part always runs (names, resolve under all three names, both-present, look-alikes and case, new moves to `99 Archive`, a name taken in an old folder is numbered, skeleton, no migration and no offer). `HandRenamed`, `HandRenamedProject` (a folder renamed by hand after the archive: old record + new folder, new record + old folder, both; Files › Archived, Move back, Undo, Restore project, `check_move`) and `OldNamesAreStillSkipped` (a saved `never_index` without the old names still skips `zz Archive` and `_Archive` in indexing, documents and the guard) are in it too. The guarded part (`MoveRules`, `RestoreFromAnOldArchive`, the old-folder cases of `HandRenamed*`, `test_check_move_…`) **runs only when `reach.ARCHIVE99` is present** (the diff applied); with `ARCHIVE99_UNPATCHED=1`, or with the diff missing, it skips.
- Updated for the new name: `test_archive_projects`, `test_archive_reports`, `test_archive_move_back`, `test_card_only_moves`, `test_notes_delete`, `test_notes_card_only_ops`, `test_onedrive_projects`, `test_update`, `test_reach`, `test_file_access`, `test_health_fixes`, `test_health_dismiss`, `test_portability` (doctor has 36 checks), `test_fs_newfile`, `test_fast_save`, `test_pages`, `test_agendas_files`, `test_settings_calmer`, the two bash-form tests, `handchecks/test_v195`.
- The results are in the report that came with this proposal (head sha, counts, and the run on a scratch copy with the diff applied).

## Risks (for the Opus review)

1. **Client files moved into the wrong folder if a name is mis-compared.** The destination of every new move must be exactly `99 Archive` (`_archive_part(x, old=False)`); the old names are accepted only as the *source* of `restore`, `reports_back` and `notes_back`. Look-alikes (`99 Archivement`, `99 Archive.old`) are refused as a destination and as a restore source (tests). `99 Archive ` with a trailing space is a normal folder name, so a project folder called that could be archived like any other; it is not the archive.
2. **A user with both `_Archive` and `99 Archive`.** Both are read, `99 Archive` first, so a stored path resolves to the first folder holding it. An archived project's name is numbered if it is taken in any of the three, so one stored path never has two answers. A same-named report in both would resolve to `99 Archive`'s.
3. **`existing_project_folder` and `permissions` changed behaviour, not just text**: they now compare case-insensitively and include the old names whatever the saved list says. That is stricter (more folders refused), never looser.
4. **Removing `rename`** removes a guarded move kind. A proposal staged by an earlier release with `archive: "rename"` and still waiting is refused ("a folder is moved only by an archive or a restore").
5. **One release only.** After it, `OLD_ARCHIVES`, `paths.OLD_ARCHIVE` (kept as an alias so an unpatched `reach.py` still imports), the old-name arms of `_archive_part`, and the two names in `never_index` must be dropped, or restores from them stop working.

## Found while reviewing (not part of #252, not fixed here)

`Grep` is not blocked from the archive folders. The guard hook allows `Grep(path=<engagement folder>, output_mode=content)`, and `reach.never_inside` ignores project folders that are skipped by name, so a search from the engagement folder goes into `99 Archive` and `zz Archive` (there is no deny pattern for `zz Archive`; `99 Archive` and `_Archive` have one). It relies on Claude Code's own `Read` deny rules covering `Grep`. Worth a separate look; this proposal does not change it.

## Decisions Alan still has to make

- Which release drops the old names (Jarvis plans 2.6 for #252, so 2.7?). Until then Alan renames his own folders when he likes; nothing prompts him.
- Whether `zz Archive` should stay out of ask creaite's deny patterns (as now: guarded by `classify`, not named) or be named too (a one-line change in `paths.never_index_patterns`).
