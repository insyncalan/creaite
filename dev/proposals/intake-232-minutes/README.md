# Proposal #232 E1 on Process's route: Find work items as `"as": "minutes"` (a guarded-file change: Alan's to approve)

**This is a proposal, not an edit.** `system/scripts/reach.py` and `system/scripts/live_server.py` are guarded: nothing on this
branch changes them. The two diffs here do, once Alan (or Jarvis, on his say) applies them. They are made against
`v26-232-next-2` (2.5.3's guarded files, unchanged since `v253-release`; `origin/main` cfe9b56c holds the same two files).

Why: Team Cap's review of `v26-232-next` bea9de16 (HIGH 1). Find work items sent `process <file> as minutes by someone else`
through `askLive` as a **confirmed** chat, so a third party's minutes were read in a run that may apply, undo and approve. On this
branch the page sends it through Process's own run kind instead: `processLive([{path, as: "minutes"}])`, `POST
/api/intake/process`, the guard hook's mode `process` (no record command, no apply, Stop on the row, the panel stays closed).

## What is on the branch already (no guarded file)

- `intake_process.py`: a file may carry `"as": "minutes"` (no other value, never a `.vtt`); the prompt marks that file and says it
  is read with `minutes.py transcript <file> --minutes` and staged with `"as": "minutes"` and `"file"`, no draft; the label says
  Find work items; `staged_paths` and `_waiting` also count `meeting.source_file` of a `"minutes by others"` proposal.
- The page: `irProcess` sends `{path, as: "minutes"}` through `processLive`; `askLive` has left the Intake page; Stop on every
  running row.

**Without these diffs** the route accepts the request, but the hook's `_process_stage_problem` refuses a spec with no
`"transcript"`, so nothing is staged and the row says "Not staged" (fail closed; nothing is applied).

## What the diffs do

- `live_server.diff`: `intake_process` passes the files Alan pressed Find work items on to `Run(..., as_minutes=...)`, which
  passes them through `guard_args` to `reach.start_run`.
- `reach.diff`:
  - `start_run(..., as_minutes=None)` writes `"files_as_minutes"` into `system/guard/run.json` (only the server writes it).
  - `process_minutes_files()`: those paths, each also one of the run's `files`; none when the record isn't this hook's Process run.
  - `_process_stage_problem`: a spec with `"as"` goes to `_process_minutes_stage_problem`: `"as"` must be `"minutes"`, `"file"` one
    of the Find work items files exactly as listed, and none of `draft`, `minutes`, `transcript`, `note`. A spec whose
    `"transcript"` is a Find work items file is refused (it is staged only as minutes); a transcript file (pressed with Make
    minutes or Process) is never staged as minutes (BL-260 holds: it still needs its draft).
  - Team Cap's review, MEDIUM 1: `_process_stage_problem` is split so no function passes check.py's complexity limit (15):
    `_process_stage_spec` (read the spec in drafts), `_process_minutes_stage_problem` (an `"as"` spec),
    `_process_transcript_stage_problem` (a transcript spec) and `_process_draft_problem` (its Word draft). The refusals and
    their words are unchanged.
  - `_runs_proposals`: a `"minutes by others"` proposal is the run's by its `source_file`, only for a Find work items file (so
    `tracker.py validate` and `search.py enrich` work on it as on a transcript's).

## Apply, check, undo

From the repo root:

```
git apply --check dev/proposals/intake-232-minutes/reach.diff dev/proposals/intake-232-minutes/live_server.diff
git apply dev/proposals/intake-232-minutes/reach.diff dev/proposals/intake-232-minutes/live_server.diff
```

Checked on `v26-232-next-2`: `git apply --check` is clean, the result is byte for byte the tested copy, and
`git apply -R --check` is clean. Undo: `git apply -R` with the same two files.

## Tests

`dev/tests/test_intake_process_minutes.py` (quick tier, no Chrome): 4 plain-code tests pass now; 7 are expected failures until
the diffs are applied, and pass with them (checked: 11 OK):
- 5 guard tests on `reach.decide` (the spec rules above, the run record, `_runs_proposals`);
- 2 route tests (Team Cap's review, MEDIUM 2) through the real live server, the real hook and a stand-in Claude: `POST
  /api/intake/process` with `{path, as: "minutes"}` writes `files_as_minutes` into `system/guard/run.json` (the stand-in copies
  the record as the server wrote it) and the stand-in's real `minutes.py stage` of an `"as": "minutes"` spec passes the hook and
  reaches Review as someone else's minutes; the same file sent without `"as"` leaves `files_as_minutes` empty and is not staged.

With the diffs applied, `check.py` prints `check: OK` (complexity included), and `test_intake_process` (29),
`test_intake_process_round2` (8) and `test_reach` (18) stay green.

The apply itself (copying the file to the minutes folder, removing it from the inbox) is E1's `tracker.py` diff, separate from
this one: `dev/proposals/intake-232/E1-tracker.rebased-on-guard-small.diff`, on top of `dev/proposals/guard-small/` (taken onto
this branch from Team Cap's `v26-e1-rebased` 56f16b34, READY WITH NOTES; the original `E1-tracker.diff` is removed: never apply
it). The two proposals touch different files (`tracker.py` there; `reach.py` and `live_server.py` here, which guard-small's
`reach-post-claim.diff` and `live-server-*.diff` also change: checked: after guard-small's four diffs these two still pass `git apply --check` and `-R --check`, and E1's diff still applies).
