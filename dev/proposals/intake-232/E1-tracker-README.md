# Proposal E1-tracker: someone else's minutes are filed only with an approved item

`system/scripts/tracker.py` is guarded, so this is a proposal for Jarvis: `dev/proposals/intake-232/E1-tracker.diff`
(a minimal patch against origin/main's tracker.py, `patch -p0` from the vault root; 22 lines added, 6 changed).

## Why
Find work items (#232 E1) stages someone else's minutes with `meeting.kind = "minutes by others"` and
`minutes_decision = "approved"` from the start (there are no minutes to approve, as for a quick note), and `meeting.note` set so
BL-260 point 4 does not refuse it. Apply runs a block's file operations whenever its decision is approved, so:

1. any later full `tracker.py apply`, even for an unrelated proposal, copies the file into the project's minutes folder, removes
   the inbox copy and writes a `processed.txt` line with 0 items, while the proposal's items are still pending;
2. rejecting every item still files the copy (and removes the inbox file);
3. a different file already at the destination is only found halfway through the apply (`_op_copy`), after the backup.

## What the patch does (five hunks)
- `by_others_waiting(data, blk)`: true for a `minutes by others` block, not yet applied, while no item of its proposal is `approved`.
- `decided()` leaves such a block out; `_file_op_problems` and `_apply_blocks` skip it (no copy, no remove, no `processed.txt`
  line, `applied` not set); `finished()` treats it as finished so a proposal whose items were all rejected moves to `applied/`.
  With at least one approved item the behaviour is exactly today's (copy, remove, line with the count).
- `check_file_op` (copy): refuses, at validation, a destination that already exists as a different file ("already exists; it is
  never overwritten"). The same file already there is still fine. This also moves the existing `_op_copy` refusal earlier for every
  copy (minutes, transcripts), before the backup.

## Repro (today)
In a scratch vault: stage a spec with `"as": "minutes", "file": "inbox/m.txt"` (two items), add any other approved proposal, run
`tracker.py apply`: `m.txt` is copied to `.../minutes/`, removed from `inbox/`, and `processed.txt` has `... | 0`. Or mark both items
`rejected` and apply: the same.

## How to test
    python3 dev/tests/test_minutes_by_others_filing.py                       # the fixed behaviour, on a patched scratch copy
    E1_TRACKER_UNPATCHED=1 python3 dev/tests/test_minutes_by_others_filing.py # fail-first: the scratch copy has no patch
The scratch copy is a throwaway vault whose `tracker.py` is the repo's with the diff applied (`patch -p0`); after Jarvis applies the
diff to the repo the same file keeps guarding it (the marker `def by_others_waiting` is found, and the "defect" tests reverse the
patch with `patch -R`). The repo's tracker.py is not touched by this branch.

Unpatched (`E1_TRACKER_UNPATCHED=1`) three `Fixed` tests go red: an unrelated apply leaves the proposal and the inbox file alone;
rejecting every item files nothing and the proposal finishes; validation names a different file at the destination before any
apply. The rest of `Fixed` (one approved item files and the other stays pending, no double filing, undo, the apply-time refusal
of a different file, the same file there is fine) is the behaviour today and stays green both ways. The two `DefectToday` tests
run on the unpatched copy in both modes: they document today's behaviour.

Also checked with the diff applied to the worktree's tracker.py (then reverted): test_tracker, test_minutes_by_others,
test_minutes_draft, _record, _approve, _review, _editor, test_refused_apply_words, test_activity_undo, test_shared_undo,
test_stage_pinned all pass.

## Until it is applied
`dev/tests/test_minutes_by_others.py` (the stage side, no tracker.py change) is complete without it. The dashboard should not
describe the file as "filed on approval" with more than "when you approve the items" until the patch is in; SKILL.md and
`dev/staging-format.md` say precisely what is true today.
