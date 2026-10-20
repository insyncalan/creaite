# #252: the archive folder is called "99 Archive" (proposal for the guarded files)

**Status: a proposal for Jarvis and Alan. Four guarded files change (`reach.py`, `tracker.py`, `live_server.py`, `permissions.py`); nothing guarded is edited on this branch.** The rest (`paths.py`, `archive.py`, `propose.py`, `update.py`, `locations.py`, `doctor.py`, `health.py`, `health_fixes.py`, the dashboard, the help, the tests) is ordinary and is already on branch `proposal-252`.

## What Alan decided (20-10-2026)

1. **No migration and no Health rename offer.** Alan renames his own existing archive folders by hand.
2. The old names (`_Archive`, `zz Archive`) are **still read and skipped for one release, then dropped**.
3. Stored paths stay `projects/<folder>/…`.
4. Archived projects (`<projects root>/99 Archive/<engagement folder>`) and each engagement's own archive folder use the same one name.

## What Alan will notice

1. **Nothing is renamed or moved for him.** His existing `_Archive` and `zz Archive` folders stay exactly as they are; no Health problem, no offer, no prompt.
2. **If he renames them to `99 Archive` himself, everything keeps working**: Restore project, Move back, Undo and Files > Archived follow the renamed folder (the apply records still say the old name; creaite looks for the folder under any of the three names).
3. **Old names are read for one release**: still skipped by search and extraction, still unreadable to ask creaite, still restorable. New archives, the monthly reports move and Delete note go to `99 Archive` only.
4. **Settings > Never read gains `99 Archive`** (nothing removed); a new project's folders come from his template with any old archive folder named `99 Archive`.
5. **For creaite-rules.md (one sentence, already in `rules_edit.py`):** "The archive folder is `99 Archive`; `_Archive` and `zz Archive` are still read and skipped for one release, then dropped, and nothing is renamed or migrated for Alan."

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
- `rules_edit.py` is the one set of `creaite-rules.md` sentences (12, the same places as the other proposal's `creaite-rules.diff`: folder map row, `locations` cell, scripts row, Project documents, Read, Retention, Archiving); it replaces exact sentences, so it applies on any base, with or without #255 (checked on main, v253-release and main + #255). Nothing in the result says `_Archive` alone.
- **Undo:** `git apply -R dev/proposals/archive-99/guarded.diff` (and revert the ordinary commits). Without the diff the branch still works for the new name (the guarded code reads `paths.ARCHIVE`), but an old-name restore or move back is refused and `rename` is still accepted until the diff lands.

## Which tests prove it

- `dev/tests/test_archive_99.py` (new): ordinary part always runs (names, resolve under all three names, both-present, look-alikes and case, new moves to `99 Archive`, a name taken in an old folder is numbered, skeleton, no migration and no offer). `HandRenamed`, `HandRenamedProject` (a folder renamed by hand after the archive: old record + new folder, new record + old folder, both; Files › Archived, Move back, Undo, Restore project, `check_move`) and `AlwaysTheNewName` (a new archive goes to `99 Archive` where an old folder exists: Delete note, the 12-month move, archive project, numbering across all three) and `OldNamesAreStillSkipped` (a saved `never_index` without the old names still skips `zz Archive` and `_Archive` in indexing, documents and the guard) are in it too. The guarded part (`MoveRules`, `RestoreFromAnOldArchive`, the old-folder cases of `HandRenamed*`, `test_check_move_…`) **runs only when `reach.ARCHIVE99` is present** (the diff applied); with `ARCHIVE99_UNPATCHED=1`, or with the diff missing, it skips.
- Updated for the new name: `test_archive_projects`, `test_archive_reports`, `test_archive_move_back`, `test_card_only_moves`, `test_notes_delete`, `test_notes_card_only_ops`, `test_onedrive_projects`, `test_update`, `test_reach`, `test_file_access`, `test_health_fixes`, `test_health_dismiss`, `test_portability` (doctor has 36 checks), `test_fs_newfile`, `test_fast_save`, `test_pages`, `test_agendas_files`, `test_settings_calmer`, the two bash-form tests, `handchecks/test_v195`.
- The results are in the report that came with this proposal (head sha, counts, and the run on a scratch copy with the diff applied).

## Risks (for the Opus review)

1. **Client files moved into the wrong folder if a name is mis-compared.** The destination of every new move must be exactly `99 Archive` (`_archive_part(x, old=False)`); the old names are accepted only as the *source* of `restore`, `reports_back` and `notes_back`. Look-alikes (`99 Archivement`, `99 Archive.old`) are refused as a destination and as a restore source (tests). `99 Archive ` with a trailing space is a normal folder name, so a project folder called that could be archived like any other; it is not the archive.
2. **A user with both `_Archive` and `99 Archive`.** Both are read, `99 Archive` first, so a stored path resolves to the first folder holding it. An archived project's name is numbered if it is taken in any of the three, so one stored path never has two answers. A same-named report in both would resolve to `99 Archive`'s.
3. **`existing_project_folder` and `permissions` changed behaviour, not just text**: they now compare case-insensitively and include the old names whatever the saved list says. That is stricter (more folders refused), never looser.
4. **Removing `rename`** removes a guarded move kind. A proposal staged by an earlier release with `archive: "rename"` and still waiting is refused ("a folder is moved only by an archive or a restore").
5. **One release only.** After it, `OLD_ARCHIVES`, `paths.OLD_ARCHIVE` (kept as an alias so an unpatched `reach.py` still imports), the old-name arms of `_archive_part`, and the two names in `never_index` must be dropped, or restores from them stop working.

## Left as they are (on purpose)

- Comments only, still saying `_Archive`: `tracker.py:1426` ("a whole folder into or out of _Archive") and `tracker.py:1996-2013` (the `in_notes_folder` and `_named_notes` docstrings). They are accurate for the old name and harmless; the next guarded pass can reword them.
- `paths.ALWAYS_NEVER_INDEX` names `99 Archive` and `_Archive` but not `zz Archive`: that name is added by `paths.skipped_names()` (and is in the new `never_index` default), so it is skipped whatever a saved list says (`OldNamesAreStillSkipped` proves it, and the mutation of dropping it from `skipped_names` fails that test). It stays out of `never_index_patterns()` as before (Alan, 14-10-2026).
- `handchecks/test_v195` (browser): it is red on clean `origin/main` too (12 failures, 5 errors); the branch, and the branch with the diff, show 13 failures and 9 errors. None of the extra ones is #252's: the Files › Archived checks c35-c40 compare original stored paths with the archived list's `at` names (since #124), c23 failing with c24-c29 erroring also happens on clean `origin/main` when the 21-30 group is run on its own, and c25 and c30 read Health's text while it still says "Checking…" (seen under heavy load).

## Found while reviewing (not part of #252, not fixed here)

`Grep` is not blocked from the archive folders. The guard hook allows `Grep(path=<engagement folder>, output_mode=content)`, and `reach.never_inside` ignores project folders that are skipped by name, so a search from the engagement folder goes into `99 Archive` and `zz Archive` (there is no deny pattern for `zz Archive`; `99 Archive` and `_Archive` have one). It relies on Claude Code's own `Read` deny rules covering `Grep`. Worth a separate look; this proposal does not change it.

## The rule (decided by Alan, 20-10-2026, via Jarvis)

**New archives always go into `99 Archive`, in every place** (the projects root, an engagement, the portfolio), even where an old `_Archive` still exists. **The old folders are read for one release**: nothing in them disappears, they are still skipped by search and extraction and unreadable to ask creaite, and a move OUT of them (restore, Move back, Undo) works from any of the three names. Alan renames his old folders by hand. A place with both an old folder and `99 Archive` reads both, `99 Archive` first (it wins on a stored path both hold); a name already taken in any of them is numbered, so a new item is never written over or followed into an old one (N1).

*For Alan, in one line:* new archives always go to `99 Archive`; old `_Archive` and `zz Archive` folders are read for one release, then dropped.

(The other proposal's rule, "into the folder already in use at that place", was considered and not adopted; Jarvis first chose it, then reversed it on Alan's word. Nothing of it, `paths.archive_name` included, is in this branch.)

## Merged from the other proposal (`origin/v26-archive-name-proposal`, ae8740c4)

| Piece | Taken? |
|---|---|
| 11 older tests expecting `99 Archive` | Done here for every file it names and more, **including** those where an engagement already holds the skeleton's old `_Archive` (a new archive there goes to `99 Archive`) |
| `creaite-rules.md` wording | One set: `rules_edit.py` (its `creaite-rules.diff` still talks about Health's rename, which Alan declined) |
| `live_server.py` `existing_project_folder` via `skipped_names` | Taken (here via `paths.is_skipped`, also case-blind); the ask-creaite prompt and comment edits too. New test with a hand-emptied `never_index` |
| `permissions.py` wording | Taken: the refusal names the folder that was hit (`99 Archive is never read or written…`, or `_Archive …`) |
| `reach.py` rule for moves INTO an archive | **Not taken**: his is "into the folder in use"; Alan's rule is always `99 Archive` (above) |
| `reach.py` `rename` shape, Health's "Rename to 99 Archive", `old-archives`, the update's `never_index` rename | Declined: Alan's decision 1 (no migration, no offer) |
| `tracker.py` comments | Taken (same changes) |
| `archive_alias` / `archive_name` | `archive_alias` is covered by `paths.follow_stored` (all four record/folder combinations, no cross-project follow, no symlink, no `..`); `archive_name` is not used (see the rule) |
| `test_archive_folder_99.py` | Its cases that fit this design are in `test_archive_99.py` (`AfterAHandRename`, the portfolio shapes, the emptied list); the Health, update-rename, folder-in-use and rename-apply tests are not (they test what Alan declined or the rule he reversed); its "new archive goes into the old `_Archive` where one exists" cases are replaced by `AlwaysTheNewName`, which expects `99 Archive` |
| `DESIGN.md` | `DESIGN.md` here lists every place that names the folder |

## With #255 (Delete note with no card, `origin/v26-delete-note-card` b73a31a4)

#255 lands first; this rebases onto it. Dry-run in both orders:
- **#255 first, then #252:** `guarded-on-255.diff` (this folder) applies on main + #255's `reach.diff`, `tracker.diff`, `live_server.diff` (checked with `git apply --check`); `rules_edit.py` applies. The ordinary branch conflicts in two places: `DeleteNote.jsx` (the header comment) and `help.md` (the Delete note bullet). Resolution: take #255's text and change its `_Archive` to `99 Archive`. #255's `tests.diff` then needs the same rename in `test_card_only_moves`, `test_notes_card_only_ops`, `test_notes_delete` and `test_notes_delete_browser` (apply it to main's versions, then `sed s/_Archive/99 Archive/`).
- **#252 first, then #255:** #255's `reach.diff` (1 hunk) and `live_server.diff` (2 of 4 hunks) fail against `guarded.diff` because both rewrite the same comments; `tracker.diff` and `creaite-rules.diff` apply; the two ordinary conflicts above are the same. Use the first order.
- A scratch copy of main + #255 + this branch + `guarded-on-255.diff` + #255's tests with the rename passed `test_delete_note_no_card`, `test_notes_delete`, `test_card_only_moves`, `test_notes_card_only_ops`, `test_archive_99` and `test_reach` (results in the report).

## Decisions Alan still has to make

- Which release drops the old names (Jarvis plans 2.6 for #252, so 2.7?). Until then Alan renames his own folders when he likes; nothing prompts him.
- Whether `zz Archive` should stay out of ask creaite's deny patterns (as now: guarded by `classify`, not named) or be named too (a one-line change in `paths.never_index_patterns`).
