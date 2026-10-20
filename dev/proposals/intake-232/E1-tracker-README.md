# Proposal E1-tracker: someone else's minutes are filed safely, and only with a written item

`system/scripts/tracker.py` is guarded, so this is a proposal for Jarvis: `dev/proposals/intake-232/E1-tracker.diff` (a patch
against origin/main's tracker.py, `patch -p0` from the vault root; about 280 lines added, 11 changed). The stage side
(`minutes.py`, the skill, the docs) needs no tracker.py change and is already on the branch; this is what makes the apply safe.

## Why
Find work items (#232 E1) stages someone else's minutes with `meeting.kind = "minutes by others"` and `minutes_decision =
"approved"` from the start (there are no minutes to approve, as for a quick note), and `meeting.note` set so BL-260 point 4 does
not refuse it. Apply runs a block's file operations whenever its decision is approved, and `check_file_op` / `_op_copy` /
`_op_remove` trust the path. So today:

1. any later full `tracker.py apply`, even for an unrelated proposal, copies the file, removes the inbox copy and writes a
   `processed.txt` line with 0 items, while the proposal's items are still pending; rejecting every item still files it;
2. an approved item that is held (needs a project, or a conflict) still files the copy, with an item count of 0;
3. **swap (TOCTOU):** `check_file_op` only asks `is_file()`, which follows links, and `safe_path` resolves links, so after staging
   `rm inbox/m.txt; ln -s <vault>/projects/ABC.../documents/contract.txt inbox/m.txt` passes validation, files the contract's
   contents as the minutes and **deletes the contract** (the remove resolves to the target), leaving a dangling link in inbox/
   (undo restores it). A target outside the vault (`/etc/hosts`) is refused only by the remove, after the copy, rolling the whole
   apply back. A hard link or a different regular file put there after staging is filed as the minutes. The same hole exists
   today for an inbox transcript (`copy` from `transcript`, then `remove` of the inbox path): this patch closes it only for the
   `minutes by others` block, and the transcript path would need the same change (not made here: out of E1's scope);
4. a destination collision (a different file already there, or another proposal in the same apply copying a different file to the
   same name) is found halfway through the apply, which rolls back, and **every later apply fails the same way**: one proposal
   blocks the queue.

## What the patch does
- `by_others_waiting(data, blk)`: a `minutes by others` block, not yet applied, with no approved item. `decided()` leaves it out,
  `_file_op_problems` and `_apply_blocks` skip it, `finished()` treats it as finished (so a proposal whose items were all
  rejected moves to `applied/` and nothing is filed).
- `by_others_unwritten(data, blk)` (checked in `_apply_blocks`, after the items): the block is filed only if at least one approved
  item of the proposal has been written (is `applied`), in this apply or an earlier one. An approved item that is held (needs a
  project, conflict) files nothing; the file waits for the apply that writes one. (Counting only *this* apply's items left a
  proposal stuck for good after an undo that skipped an item as "changed since": the item stays approved and applied, the block
  goes back to approved, and the next apply wrote nothing new, so it never filed.) The processed line's count is of this apply's
  items, so it can read 0 in that case.
- `by_others_file_problem(rel, blk, sha)`, called from `check_file_op` for the block's `copy` source and its inbox `remove`, at
  validation and again before each operation at apply: the file must be a regular file by `lstat` (a link is refused, whatever it
  points at), have no other name (`st_nlink`), have a real path in inbox/ (itself not a link) or a matched project's minutes
  folder, and hash to the `src_sha256` staged by `minutes.py` ("the file changed since it was staged" otherwise; a missing
  checksum is refused).
- `_op_copy` for the block reads the bytes once through `O_NOFOLLOW`, compares them with `src_sha256`, then writes them (no
  window between check and copy). It opens with `O_NONBLOCK` and checks `S_ISREG` on the open file before reading, so a pipe
  (FIFO) put in place of the file after the check is refused instead of hanging the apply. A link that appears after the check (an `ELOOP`) is a clean `Invalid` naming the stored
  (relative) path, `from None`, so neither stdout nor the debug log carries the absolute path.
- **One way to read the file** (`_read_regular`): `O_NOFOLLOW | O_NONBLOCK`, `fstat`, `S_ISREG` on the open file, then read. The
  validation check (`by_others_file_problem`: it used `file_hash`, whose `read_bytes` blocks on a pipe and follows links), the
  copy (`_copy_checked`) and the remove (`_remove_checked`) all use it, so a pipe put in place of the file at any moment is
  refused ("is not a regular file") instead of hanging the apply, and a link is never followed. The comparison with a file already at
  the destination also hashes through it (`_dst_is_same`, by the staged checksum).
- `_op_copy` reads the bytes once through it, compares them with `src_sha256`, then writes them (no window between check and copy).
  A link that appears after the check (an `ELOOP`) is a clean `Invalid` naming the stored (relative) path, `from None`, so neither
  stdout nor the debug log carries the absolute path.
- `_op_remove` for the block works through the open folder (`_remove_checked`, `_open_inbox_folder`): the folder is reached from
  the vault root one level at a time, each opened with `O_NOFOLLOW | O_DIRECTORY` (so `inbox/`, or a folder in it, swapped for a
  link is refused, and a rename or link put on the path afterwards changes nothing: the descriptor is the folder that was
  opened); the entry is read through `_read_regular` from that folder, checked (regular file, one name, `src_sha256`), backed up
  from the bytes just read, **moved to a private name inside the open folder, compared by inode with the file that was read, and
  only then unlinked** (`_unlink_same`, all through `dir_fd`). The private name is `.creaite-removing-<pid>-<ns>`: it carries no
  part of the file's name, so a name near the 255-byte limit (240 bytes, or 78 CJK characters) still files. A different file
  put under the same name is never deleted: if the move caught it, it is put back **without replacing anything** (a hard link,
  then the private name is unlinked), and the apply stops ("a different file was put there; it is left alone"). If something
  has taken the name again (a file, or a folder), it is not touched: the different file stays in inbox/ under its private name
  and the error says which ("… is left in inbox/ as .creaite-removing-…"). Only a file in `inbox/` can be removed this way
  (minutes.py stages no other remove). (Inbox transcripts still have the old hole: `copy` from `transcript` then `remove` of the
  path; not touched here.)
- **Undo:** the existing undo resets every applied block to `pending`; for a `minutes by others` block it now sets it back to
  `approved` (it is approved from staging), so undo, approve, apply files the minutes again. Without this the re-apply wrote the
  items, filed nothing, left the file in inbox/ and the proposal in staging for good.
- **Hand-written or edited proposals:** the checks key on `by_others_op(fop, blk)`: the block's `kind` *or* the `src_sha256` on the
  operation, so a proposal edited to drop `kind` is still checked. A copy of such an operation must go to a matched project's
  minutes folder (`by_others_dest_problem`), not anywhere `safe_path` allows. **Known limit:** a proposal edited to drop both
  `kind` and `src_sha256` gets today's rules (a link swap is followed and its target removed, and `to` is confined only by
  `safe_path`), as every other block (transcripts, reports, notes) does today; proposals are written by the staging scripts into
  `system/staging/`, which only creaite's own commands and Alan write. Closing that for every block is a different, larger change.
- **A folder at the destination** is refused cleanly at validation and at apply ("… is a folder", relative path), not an
  `IsADirectoryError` naming the absolute path.
- `check_file_op` (every copy): refuses, at validation, a destination that already exists as a different file.
- **The queue is not blocked:** a full apply (`tracker.py apply` with no arguments) first drops, with a line "Left in staging,
  not applied: <proposal>: <reason>.", each `minutes by others` proposal whose file can't be filed now (destination taken by a
  different file, link or changed file, a different file already claimed for the same destination by an earlier proposal in this
  apply). Everything else in the queue applies. The dropped proposal stays in staging with its choices; the next apply tries it
  again, so putting the file right (or restaging) is enough. `tracker.py apply <proposal>` (named) still stops with the reason, as
  before. Other proposals (reports, ordinary minutes) keep today's behaviour.
- `minutes.py` (already on the branch) gives each copy and remove op `src_sha256`, numbers the destination against files on disk
  and against other staged proposals' destinations, and refuses to stage the same file twice.

## Known residuals
- If a different file takes the staged file's name *after* the move to the private name and before the unlink, nothing is lost (the
  private name is not guessable and nothing else looks there). The window between reading the file and moving it is closed by the
  inode comparison, not by the checksum alone: the swapped-in file is moved back untouched.
- The edited-proposal limit above.

## Repro (today)
Scratch vault: stage `"as": "minutes", "file": "inbox/m.txt"` (two items), then
1. add another approved proposal and run `tracker.py apply`: m.txt is filed and removed, `processed.txt` has `... | 0`;
2. or mark both items rejected and apply: the same;
3. or replace `inbox/m.txt` with a symlink to a vault file, approve, apply: the target is filed as the minutes and deleted;
4. or `tracker.py undo` after the first apply, approve both items and apply again: written 2, filed 0, the file stays in inbox/;
5. or create a different file at the destination and apply twice: the apply fails each time, and an unrelated proposal in the
   queue is never applied.

## How to test
    python3 dev/tests/test_minutes_by_others_filing.py                        # the fixed behaviour, on a patched scratch copy
    E1_TRACKER_UNPATCHED=1 python3 dev/tests/test_minutes_by_others_filing.py # fail-first: the scratch copy has no patch
    E1_TRACKER_MUTATE=<name> python3 dev/tests/test_minutes_by_others_filing.py   # one line of the patch broken: a test goes red
The scratch copy is a throwaway vault whose `tracker.py` is the repo's with the diff applied (`patch -p0`); after Jarvis applies the
diff to the repo the same file keeps guarding it (the marker `def by_others_waiting` is found, and the "defect" tests reverse the
patch with `patch -R`). The repo's tracker.py is not touched by this branch. Unpatched, 34 of the 44 tests go red (the swap, undo, race, hand-written proposal, folder destination,
held-item, collision, unrelated-apply and all-rejected tests, and the validation message); the `DefectToday` tests document today's
behaviour on the unpatched copy in both modes, and the rest (one approved item files, no double filing, undo, the same file at the
destination) is today's behaviour and stays green.

Also run with the diff applied to the worktree's tracker.py (then reverted), all passing: test_tracker, test_minutes_by_others,
test_minutes_draft, _record, _review, _approve, _editor, test_refused_apply_words, test_activity_undo, test_shared_undo,
test_stage_pinned, test_script_policy, test_no_real_names, check.py.

## Until it is applied
`dev/tests/test_minutes_by_others.py` (the stage side) is complete without it. The ops carry `src_sha256`, which today's tracker
ignores. Until the patch is in, the filing has the four defects above; SKILL.md and `dev/staging-format.md` say what is true today.
