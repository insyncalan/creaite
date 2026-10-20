# Proposal #264 round 2: Team Cap's notes on Process's R1 (guarded files: Jarvis applies on Alan's say)

**This is a proposal, not an edit.** `system/scripts/reach.py`, `system/scripts/live_server.py` and `system/creaite-rules.md` are
guarded: nothing on this branch changes them. Three diffs here do, once applied. Team Cap's review of `origin/v253-release`
aae1fe79 (the #264 diffs plus R1) was READY WITH NOTES with no HIGH; this round is its M2 and L1 to L4, and the rules part of L5.

## Apply, check, undo

From the repo root, on `origin/v253-release` bdbc9aec (with #265's diffs applied):

```
git apply --check dev/proposals/intake-process-round2/reach.diff dev/proposals/intake-process-round2/live_server.diff \
  dev/proposals/intake-process-round2/rules.diff
git apply dev/proposals/intake-process-round2/reach.diff dev/proposals/intake-process-round2/live_server.diff \
  dev/proposals/intake-process-round2/rules.diff
```

`git apply --check` is clean for all three, and `git apply -R --check` is clean once applied. Undo: `git apply -R` with the same
files. Verify (one at a time):

```
python3 dev/tests/test_intake_process_round2.py   # 7 tests: 6 expected failures before the diffs, all OK after
python3 dev/tests/test_intake_process.py          # 29, unchanged
python3 dev/tools/check.py                        # check: OK
```

Also run with the diffs applied, all OK: test_reach (18), test_guard_pinned (2, the pinned decisions unchanged), test_record_commands,
test_held_bash_arg_forms, test_ask_reports_refused, test_calendar_refresh (22), test_script_policy, test_closed_runs_no_writers,
test_run_read_pinned, test_permission_panel, test_ask_queue (5, Chrome), test_intake_process_ui, test_transcripts_ui (16),
test_calendar_refresh_ui.

## What Alan will notice

Nothing on the screen. Process stages the same files the same way; it just can't be led into treating another flow's file as
its own, and it can't read his home folder.

## The fixes (`reach.py` unless said)

| Finding | Fix | Test (`dev/tests/test_intake_process_round2.py`) |
|---|---|---|
| **M2** `_may_make` wrote a claim into `"made"` while the hook was still checking, so a refused call (a fill refused for its pictures, a report-named Write, an enrich refused on a later `--path`) left a name the run could later use as "its own" after another flow wrote it | Nothing is written while checking: `_may_make` and `_runs_own` note the claim, the write and what they saw in `_HOOK`, and `decide()` records them (`_commit_claims`) only when the whole call is allowed. The record also keeps each own file's `[inode, size, mtime_ns]` as first seen after the run's own last write (`"prints"`); a file changed or replaced since then is not the run's | `test_m2_a_refused_call_claims_nothing` (Cap's repro, plus the write and enrich cases); `test_m2_a_file_put_in_place_of_the_runs_own_is_not_its_own` |
| **L1** hooks at the same moment could lose each other's claims (read, change, write of `run.json`) | `_RunLock`: an exclusive `flock` on `system/guard/.run.lock` around every read-change-write of the record (`start_run`, `mark`, `end_run`, `_commit_claims`) | `test_l1_hooks_at_the_same_moment_keep_every_claim` (12 hooks at once, 60 claims) |
| **L2** (`live_server.py`) the BL-257 queue started an ask run under `QLOCK` only | `queue_start` makes the busy check and the start one step under `START_LOCK`; a run already going (other than the one ending) holds the queue (Run now starts it) | `Queue.test_l2_a_queued_message_starts_under_start_lock_and_never_beside_a_run` |
| **L3** the README said the run never reaches the home folder, but Read, Grep and Glob were unscoped | Scoped in the hook: in mode `process`, Read, Grep, Glob, LS and a script's path arguments must be in the vault or the projects folder (`process_reach_problem`); a plain chat is unchanged | `test_l3_a_process_run_reads_only_the_vault_and_the_projects` |
| **L4** the record was read without its run ID | `_process_record()`: `run.json` counts only when its `"run"` is the hook's `--run` (set by `decide`); `process_files`, `_made`, `_runs_proposals` and the write check all use it | `test_l4_the_record_counts_only_for_the_hooks_own_run` |
| N10 kept | a record that can't be written refuses the call (the claim now waits for `_commit_claims`, which fails closed) | `test_n10_when_the_record_cant_be_written_a_new_file_is_refused` (passes before and after) |
| **L5** the rules paragraph | `rules.diff`: the read commands, reading only the vault and the projects, `tracker.py validate` on its own proposal, and what "its own" means | (docs) |

L5's other two parts are on this branch already (not guarded): `dev/proposals/intake-process/README.md` now has R1's text (from
`v253-intake-process` 2df2a018) with its by-time lines marked superseded, and `dev/BUILD.md` has a #264 entry.

## Residual

- **Between an allowed write and the next use.** A file the run writes is seen afresh at its next use, so another flow writing
  the same name in that window (it has to guess the name and write while the run is going) would be taken as the run's. Closing it
  fully needs a PostToolUse hook that records the file just after the run's own tool writes it; not done here. The worst case stays
  a pending proposal, in Review, that Alan sees before it is anything.
- **Windows:** no `flock`, so L1's lock is skipped there (untested platform, as the rules say).
