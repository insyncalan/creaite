# #252: the archive folder is called 99 Archive (guarded part)

**For Alan, in plain words.** The archive folder gets one name, **99 Archive**, so it sorts last in OneDrive beside 99 System. New archiving (a project, old reports and minutes, a deleted note) goes into 99 Archive. Nothing moves on its own: an update only changes the saved setting's name. Your existing `_Archive` and `zz Archive` folders stay where they are, keep working and stay hidden from ask creaite for one release; where a place still has only an old `_Archive`, creaite keeps using it so no place ever ends up with two archive folders. Settings › Health lists the folders still called `_Archive` or `zz Archive` and offers **Rename to 99 Archive**; it goes on the approval card, you see every folder, it is undoable, and it never runs without your yes, because these folders are in the company OneDrive and can hold other people's files. Stored paths do not change: every link, Files › Archived, Move back and a project restore still open after the rename. Not touched: the database, stored paths, the files inside the folders, `_Templates` (you rename the skeleton's folder yourself in Finder; a new project gets 99 Archive either way), `99 System`, and the client report rules.

## The four decisions (issue #252) and the recommended answers

| # | Decision | Recommended (what this proposal builds) |
|---|----------|-----------------------------------------|
| 1 | Existing vaults and OneDrive folders: Health offer or automatic migration at update time? | **Health offers it, on the card, on your say-so.** Never silent; the update renames only the saved `never_index` value |
| 2 | Keep skipping and resolving `_Archive` and `zz Archive` for one release, then drop them? | **Yes, one release** (as BL-09 did for `zz Archive`); drop in the release after 2.6 |
| 3 | Stored paths stay `projects/<folder>/…`? | **Yes, unchanged.** A path recorded under an old name is followed into the 99 Archive that replaced it |
| 4 | Archived projects and each engagement's own archive both use the one name? | **Yes, both** `<projects root>/99 Archive/<engagement>` and `<engagement>/99 Archive/…` |

## The diffs (guarded files; Jarvis to review, Alan to approve)

Each was checked with `git apply --check` against origin/main 4e564fcf.

| File | What changes |
|------|--------------|
| `reach.diff` | `archive_move_problem`: a move **into** an archive must use the folder in use at that place (`paths.archive_name`: 99 Archive, or a vault's old `_Archive` until renamed; never a new `_Archive`, never `zz Archive`); a move **out** (restore, reports_back, notes_back) may start in any of the three names; the rename is `_Archive` or `zz Archive` to the 99 Archive beside it, in the root, an engagement or now the portfolio. Fixes the `paths.OLD_ARCHIVE` reference the branch removed. Classify, the never list and `CARD_ONLY_MOVES` are unchanged |
| `tracker.diff` | Comments and the move block's header only; `safe_path` already refuses every archive name through `paths.skipped_names()` |
| `live_server.diff` | `existing_project_folder` uses `paths.skipped_names()` (so `99 Archive`, which has no underscore, is never taken for a project even with a hand-emptied list); ask creaite's prompt and comments name 99 Archive and the old names |
| `permissions.diff` | Wording only: the refusal and the help text name 99 Archive (the check already uses `skipped_names`) |
| `creaite-rules.diff` | Folder map (`locations`, `projects/99 Archive/`, scripts), documents, retention and archiving wording; the one-release overlap sentence in the `never_index` cell |

**Must land with the branch.** The branch's `paths.py` drops `paths.OLD_ARCHIVE`, which today's `reach.py` uses in the rename check, so the ordinary commits and `reach.diff` go together (or `OLD_ARCHIVE = "zz Archive"` is put back as an alias if the branch must land first).

## Verified in a scratch copy

All five diffs applied to the branch head in a scratch worktree, tests run one at a time: `test_archive_folder_99` 20/20; `test_reach`, `test_archive_items`, `test_archive_items_marks`, `test_archive_projects`, `test_archive_reports`, `test_archive_move_back`, `test_card_only_moves`, `test_notes_delete`, `test_notes_card_only_ops`, `test_file_access`, `test_fs_newfile`, `test_agendas_files`, `test_fast_save`, `test_pages`, `test_portability`, `test_onedrive_projects`, `test_update` and the `test_health*` tests all OK. The browser tests and the v1.9.5 hand check need Chrome and a live server slot and were not run.

Eleven older tests named `_Archive` as the place a new archive goes; they were changed deliberately to `99 Archive` (a vault engagement has no archive folder yet, so the new name is used), except where the test's engagement already holds the skeleton's old `_Archive`, which stays the folder in use. No guard was loosened in a test. `permissions.diff` now names the refused folder (`99 Archive is never read or written…`), so the existing `_Archive` refusal text still matches.

## With #255 (Delete note without the card, `dev/proposals/delete-note-no-card/`)

- `reach.diff` and `tracker.diff` compose with #255's in either order.
- `creaite-rules.diff` and `live_server.diff` conflict textually with #255's in either order: comments and rules prose only (`move_back_route`'s docstring, the #124 Delete note comment block, the Archiving paragraph). **Resolution:** take #255's text, then apply this proposal's renaming to it: every `_Archive` in #255's new lines becomes "its archive folder" or `99 Archive` (four places: the move-back docstring, the Delete note block twice, `notes_delete_now`'s docstring, and the Archiving paragraph). No code conflict: #255 builds the move with `archive.note_delete_spec`, which this branch already points at the folder in use.
- Tests: #255's `tests.diff` and this branch both change `test_card_only_moves.py` and `test_notes_delete.py`, so they conflict. Take #255's version of both files, then change `_Archive` to `99 Archive` where a note goes into a vault engagement or the portfolio, as this branch does.
- Order: land #255 first (it is the larger change), then rebase these two diffs onto it.
