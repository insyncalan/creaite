# #175: Notes autosave follow-up (proposal only)

Session cap, fewer Activity rows, old-draft clean-up. Follow-up to #119 (Alan, 17-10-2026). **This is a proposal. Nothing here is
applied to a code branch.** The diffs are against `origin/notes-119-own` 629c599e, and they apply cleanly there (checked in a
fresh worktree; the files come out byte-identical to the tested ones).

| File | What it is |
|------|------------|
| `filechange-175.diff` | Guarded: the session cap (M2) and `retire_note_drafts` (L1) |
| `live_server-175.diff` | Guarded: Activity folding (M1) and the start-up call (L1) |
| `tests-175.diff` | New `dev/tests/test_notes_175.py` (8 tests), plus 5 tests added to `dev/tests/test_notes_autosave_backups.py` |

Team Cap's findings (#119, round-1 server review): **M1, M2 and L1 are closed. L3 is closed by tests only. L2 is not done.**

## filechange.py

**Hunk 1: `SESSION_MAX_AGE = 1800` (M2).** Decision: an editing session ends 30 minutes after its **first** save, as Cap
recommended. It still also ends after 5 minutes without a save (`SESSION_IDLE`, unchanged). Why: one Undo can now put back at
most about 30 minutes of typing, not hours.

**Hunk 2: `_age`, `_session_first` and `session_backup` (M2).**
- The session's first save is the log entry whose `id` is the number of the shared backup folder (`changes/<n>/`). It must be
  an edit of the same path, in the same session, with the same backup.
- A save joins the session only if two things hold: the last save was under 300 s ago (as before), and that first entry is in
  the log and under 1800 s old.
- If the first entry is missing or can't be read, the save gets a new backup. That is the safe direction: an extra backup,
  never a wrong join.
- The other checks are unchanged, in the same order: the file still matches `after`, and the backup still matches `before`.
- `_age` takes out the timestamp parsing that already existed, unchanged.

**Hunk 3: `NOTE_DRAFT` and `retire_note_drafts` (L1).**
- **What is moved:** only files whose name is exactly `<16 lowercase hex>.json` or `<16 lowercase hex>.json.tmp`. That is the
  old `notes.draft_file` name, plus a leftover from an interrupted write. They must be regular files, not symlinks, directly
  in `system/staging/drafts/notes/`.
- **What is never touched:**
  - `capture-*.json` (the Capture drawer keeps its draft; Alan, 17-10-2026);
  - any other name;
  - subfolders;
  - symlinks, and what they point to;
  - a draft that `reach.confidential_places()` holds. That is a draft marked confidential, a draft of a confidential note, or
    one that is unreadable or whose note is gone, which fail closed. These are found with reach's own test; nothing is copied.
- **How:**
  - each file is copied into one new `system/backups/files/changes/<n>/` and then removed;
  - the files log gets **one** line: `op: "cleanup"`, `path: system/staging/drafts/notes`, `files: [names]`, `backup`,
    `via: "server"`, `tier: "ordinary"` and `why`. It never holds the text;
  - one debug line.
- **When:** each time the server starts. If nothing matches, nothing is written, so in practice it runs once.
- **Retention:** Tidy up's existing rule removes the backup folder after 90 days (`backups.file_change_days`). It dates the
  folder from the log line.
- `"cleanup"` is not in `CHANGE_OPS`, so `filechange.changes()`, `list`, Activity and Undo never see it. `next_id` and
  Tidy up's `change_dates` still count it.

## live_server.py

**Hunk 1: `main()` calls `retire_note_drafts()`.** It runs after the stale change requests are cleared and before any thread
starts or anything is served. So no save from the page can race it.

**Hunk 2: `changes_list_route` folds sessions (M1).**
- **The files log keeps exactly what it has today: one line per save.** Nothing about logging changes.
- **What Activity shows:**
  - one row per editing session, grouped by `(path, session key, backup)`. A capped session and the one after it have
    different backups, so they are two rows;
  - each row is the session's **latest** save: its `id`, `at` and `undone`, plus two new fields, `saves` (how many) and
    `first_at` (when the session began);
  - edits without a session (cli, ask creaite, card approvals), creates, moves and deletes keep their own rows, as before.
- The row's Undo button sends the latest save's id. `filechange.py undo <id>` undoes the whole session, which is #119's
  existing behaviour.
- After the fold: about 1,800 rows for an hour of typing become 2 to 12, depending on pauses and the cap.

**Hunk 3: `retire_note_drafts()` wrapper.**
- If the clean-up fails, the server writes a warning to the debug log and carries on starting. The drafts stay until the next
  start.
- After a clean-up it logs one info line with the count.

**Page wording (not in these diffs).** `ask.js` is not guarded and isn't changed here, so the row shows the latest save's time
and nothing more. A one-line change in `askChangesHtml` would show the count:
`${c.saves>1?html` <span class="sub">${c.saves} saves, ${c.first_at.slice(11,16)} to ${c.at.slice(11,16)}</span>`:""}`.
That needs a `dashboard.html` rebuild and can go in with the apply as ordinary page work.

## How Undo behaves across a capped session

- Session 1 runs 14:00 to 14:30. The save at 14:31 starts session 2, whose backup is the text as session 1 left it.
- Undo session 2 (Activity's top row): the text goes back to 14:30.
- Then Undo session 1: the file now matches that session's last `after`, so it is allowed, and the text goes back to before
  14:00.
- Each step undoes at most about 30 minutes. Undoing the older session first still refuses ("changed since"), as today.
- An Undo still can't itself be undone. That has not changed (Cap's M2 alternative, keeping the current text first, is not
  built).

## Not changed

- `reach.py` and the never list. The tiers, approvals and the ten-file limit.
- `own=True` and `_is_own`.
- The 5-minute idle rule. The token rules and `SESSION_MAX`.
- `_undo_edit`, `cmd_undo` and `session_saves`.
- The Capture drawer and its route. The dead `/api/notes/draft` route.
- `entries()` still parses the whole log on every save (**L2 not done**: it is outside #175's three points; a separate small
  item if wanted).
- The stale docstrings in the non-own run tests, and the HTTP test of the 14 saves (Cap's `notes-119-own` notes 1 and 2).

## Safety

- **What ask creaite or a client-safe place can see:**
  - nothing widens. The fold only drops rows from an existing read-only list;
  - the clean-up only removes files from staging, which also takes them out of the daily offsite zip;
  - the copies land in `system/backups/`, which the zip leaves out;
  - confidential drafts are left where they are. If they were moved into the backups, a held run could read them once no
    note is confidential, so they are not moved;
  - client reports never read staging or backups.
- **Approvals:**
  - no path to `perform` changes;
  - `retire_note_drafts` takes no argument from a request. Only `main()` calls it, and an ask creaite run can't run it (it is
    not a CLI command, and the hook allows only bare creaite scripts);
  - it deletes only creaite's own staging files, by an exact name pattern.
- **Undo:** as above. Sessions are never joined more widely than before; the cap only makes them shorter.

## Tests

The new tests fail when the code part is taken back out. Run from the throwaway worktree with the tests applied and the two
guarded files reset to 629c599e:
- `test_notes_175`: all 8 fail;
- `test_notes_autosave_backups`: 3 of the 5 new tests fail (the cap, the undo chain, a first save missing from the log).

The two L3 tests cover code that already exists, so they pass without the change. Mutation runs show they work:
- dropping the `sha(backup) != before` check makes `test_a_session_backup_changed_since_is_never_reused` fail;
- dropping `not is_settings_file(target)` in `_backup` makes
  `test_backup_never_joins_a_settings_file_even_when_called_as_joinable` fail;
- dropping the confidential filter makes 3 `OldDrafts` tests fail.

Each mutation was restored byte-identical afterwards.

On the applied proposal, run one at a time with `CREAITE_NOW="2026-10-16 09:30"`, every test passed:

| Test file | Tests |
|-----------|-------|
| `test_notes_autosave_backups` | 16 |
| `test_notes_175` | 8 |
| `test_notes_server` | 25 |
| `test_notes_guard` | 5 |
| `test_file_access` | 25 |
| `test_backups` | 21 |
| `test_notes_own_save` | 5 |
| `test_admin_card` | 26 |
| `test_ask_tiers` | 20 |
| `test_permission_file` | 20 |
| `test_open_write` | 15 |
| `test_guard_pinned` | 2 |

`check.py`: OK.

```
git apply dev/proposals/notes-175/filechange-175.diff dev/proposals/notes-175/live_server-175.diff dev/proposals/notes-175/tests-175.diff
for t in test_notes_autosave_backups test_notes_175 test_notes_server test_notes_guard test_file_access test_backups \
         test_notes_own_save test_admin_card test_ask_tiers test_permission_file test_open_write test_guard_pinned; do
  CREAITE_NOW="2026-10-16 09:30" python3 dev/tests/$t.py; done
python3 dev/tools/check.py
```

## For Alan to decide

1. **The cap: 30 minutes from the first save** (Cap's recommendation)? Yes, or another length.
2. **Confidential leftover drafts** (marked confidential, of a confidential note, or of a note that is gone): leave them in
   place (as proposed), or delete them with **no** copy? Deleting closes L1 fully; to do it, a confidential draft is unlinked
   instead of skipped (about 3 lines).
3. The page's "12 saves, 14:02 to 14:31" wording (unguarded, above): with the apply, or later?
