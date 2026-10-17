# #175 guarded proposal r3 (engineers)

**Proposal only; nothing applied.** Base: `origin/notes-136-gate` 94117e79 (contains `origin/v220-int-gate`). Design:
`notes-175-design-r3` a1040bd5 (`design-r3.md`), agreed by Alan 17-10-2026. Supersedes r2 (`notes-175-proposal` 0c7ed984,
against `notes-119-own` 629c599e). Plain-English version for Alan: `README-plain.md`.

## Alan's answers (17-10-2026) and what they mean here

| Answer | In the diff |
|---|---|
| Keep the 30-minute cap | `filechange.SESSION_MAX_AGE = 1800`, `_age`, `_session_first`, `session_backup` (as r2) |
| Confidential leftover drafts stay in place | `retire_note_drafts` skips anything `reach.confidential_places()` holds; no unlink-without-copy path exists |
| "Restore", not "Undo" | Comments and the route docstring only; the button label is page work (`ask.js`, unguarded) |
| Activity on a notes row = file-level restore to the session's start | `changes_list_route` fold (M1); the row's id is the latest save, and `filechange.py undo <id>` (unchanged) restores the session's backup |
| One Activity row per editing session | The fold, keyed `(path, session, backup)`; adds `saves`, `first_at` |

## Changes against r2

- Rebased: the r2 diffs applied with a 1-line offset in `live_server.py`; regenerated, now exact (`git apply --check` clean).
- Comments and the `changes_list_route` docstring reworded to Restore and to Alan's decisions; no logic change.
- Tests: `test_the_row_undo_undoes_the_whole_session` renamed `test_the_row_restore_puts_back_the_file_as_before_the_session`;
  the confidential test now also asserts the draft is byte-identical in place; new
  `test_a_failed_clean_up_is_logged_and_never_stops_the_server` (wrapper returns 0, drafts stay, debug log has the warning).

## Guarded surface

- `filechange.py`: `SESSION_MAX_AGE`, `_age`, `_session_first`, `session_backup`, `NOTE_DRAFT`, `retire_note_drafts`.
- `live_server.py`: `changes_list_route`, `retire_note_drafts` (wrapper, catches `Exception`), `main` (one call after the stale
  change requests are cleared, before any thread or `serve_forever`).
- Unchanged: `perform`, `_same_session`, `session_saves`, `_undo_edit`, `cmd_undo`, `changes_undo_route`, `reach.py`,
  `permissions.py`, `tracker.py`, `backup.py`, `update.py`. `"cleanup"` stays out of `CHANGE_OPS`.

## Tests (run one module at a time, `CREAITE_NOW="2026-10-16 09:30"`)

With the code removed (tests applied, guarded files at base): `test_notes_175` 9 of 9 fail; `test_notes_autosave_backups`
3 of 16 fail (the cap, the restore chain, a first save missing from the log; the 2 L3 tests cover existing code).

With the code: `test_notes_175` 9, `test_notes_autosave_backups` 16, `test_notes_server` 25, `test_notes_guard` 5,
`test_file_access` 25, `test_backups` 21, `test_notes_own_save` 5, `test_admin_card` 26, `test_open_write` 15: all OK.
`dev/tools/check.py`: OK.

```
git apply dev/proposals/notes-175/filechange-175.diff dev/proposals/notes-175/live_server-175.diff dev/proposals/notes-175/tests-175.diff
```

## Not in this proposal

Page work from design r3 (`cxUndoSteps`, depth 500, the editor-state cache, the Restore label and "12 saves, 14:02 to 14:31"
in `askChangesHtml`, reopening the note after a Restore) and its real-Chrome tests. L2 (whole log parsed on every save).
