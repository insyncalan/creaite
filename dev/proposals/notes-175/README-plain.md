# #175 Notes: the protected part, in plain English

**For Alan. This is a proposal. Nothing has been changed in creaite yet.** It needs your yes before anyone puts it in.

## What changes for you

- **Activity gets shorter.** Today, an hour of typing in a note can make hundreds of rows in Activity › What ask creaite
  changed. After this, one stretch of typing is **one row**, for example "12 saves, 14:02 to 14:31".
- **The row's button says "Restore 14:02".** It puts the whole note back as it was when that stretch of typing began. Your
  everyday undo is still Cmd+Z in the note itself (that part is page work, not in this proposal).
- **A stretch of typing lasts at most 30 minutes** (as you agreed). After that, the next save starts a new row. So one Restore
  never takes back more than about 30 minutes of work. It still also ends after 5 minutes without typing, as today.
- **Old leftover copies of notes are tidied away once.** Before #119, the Notes tab kept a typed copy of each note in a
  staging folder. Nothing uses them now. When creaite starts, it moves them into the backups (kept for 90 days, then removed
  by the usual Tidy up). **Copies of confidential notes stay exactly where they are** (as you agreed). The Capture drawer's
  own copy is never touched.

## Which protected functions change

In `filechange.py` (the one place that changes files with a backup and a way back):

- `SESSION_MAX_AGE` (new setting in code): 30 minutes, the longest one stretch of typing can last.
- `_age` (new): works out how old a log line is. It is the existing time check, moved into its own function.
- `_session_first` (new): finds the first save of a stretch of typing, so the 30 minutes can be counted from it.
- `session_backup` (changed): decides whether a save joins the current stretch. It now also checks the 30-minute limit.
- `NOTE_DRAFT` and `retire_note_drafts` (new): find the old leftover copies by their exact name and move them into the
  backups, with one line in the files log.

In `live_server.py` (the local server the dashboard talks to):

- `changes_list_route` (changed): builds the Activity list. It now folds the saves of one stretch into one row.
- `retire_note_drafts` (new, a small wrapper): runs the tidy-up and, if it fails, notes it in the debug log and carries on.
- `main` (one line added): runs the tidy-up once when the server starts, before anything is served.

Nothing changes in the rules about what ask creaite may touch, the approval card, the database or backups' own code.

## What could go wrong, and the way back

| What could go wrong | How likely | The way back |
|---|---|---|
| A Restore takes back less than you expected, because the stretch was cut at 30 minutes | Expected by design | Restore the older row as well (newest first) |
| The Activity row count looks wrong | Low; tested | The files log still keeps every save; nothing is lost |
| The start-up tidy-up fails | Low | The server starts anyway; the copies stay until next time |
| An old copy you wanted is moved | Very low; only exact old names | It is in `system/backups/files/changes/` for 90 days |
| The code change itself misbehaves | Low; tests pass | Version control puts both files back in one step |

## Tests

9 new checks and 5 added to an existing set. With the change taken out, 12 of them fail (they really test it); with the
change in, every one passes, as do 8 neighbouring test sets and the code checker.

## Your yes or no

1. **Fold one stretch of typing into one Activity row.**
   Risk: none to your data; the full log is kept. **Recommend: YES.**
2. **Cap a stretch at 30 minutes from its first save.**
   Risk: a Restore may need two clicks for a long session. **Recommend: YES** (you already chose this).
3. **Activity's button on a note row is "Restore <time>", a restore to the start of that stretch.**
   Risk: two kinds of undo; the word "Restore" keeps them apart. **Recommend: YES** (you already chose this).
4. **Tidy away the old leftover note copies at start-up, into the backups for 90 days.**
   Risk: very low; exact names only, a copy is kept first. **Recommend: YES.**
5. **Leave confidential leftover copies where they are, never moved or deleted.**
   Risk: they stay in staging and in the daily backup zip until you remove them. **Recommend: YES** (you already chose this).
6. **Put these two protected files in with the next release, after Team Cap's review.**
   Risk: as the table above. **Recommend: YES.**
