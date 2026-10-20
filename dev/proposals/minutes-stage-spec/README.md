# Proposal #269: the hook checks `minutes.py stage`'s spec too (a guarded-file change: Alan's to approve)

**This is a proposal, not an edit.** `system/scripts/reach.py` is a guarded file: nothing on this branch changes it. The fix
itself is already on the branch and needs no guarded change: `minutes.py stage` checks its own spec (`minutes_spec.py`) before
it reads anything, so the protection holds in every mode, with or without this diff. The diff adds the same check at the ask
creaite hook, so a refused spec never reaches the script (defence in depth).

## Apply, check, undo

From the repo root:

```
git apply --check dev/proposals/minutes-stage-spec/reach.diff
git apply dev/proposals/minutes-stage-spec/reach.diff
```

Checked on `origin/v253-release` (df417f7d): clean. It also applies cleanly with #264's `dev/proposals/intake-process/reach.diff`,
in either order (the two touch different lines). Undo: `git apply -R dev/proposals/minutes-stage-spec/reach.diff`.

Verify after applying (one at a time):

```
python3 dev/tests/test_minutes_stage_spec_hook.py   # 3 tests: skipped until the diff is applied, then all pass
python3 dev/tests/test_minutes_stage_spec.py        # 31 tests: the command's own check (passes with or without the diff)
python3 dev/tests/test_record_commands.py
python3 dev/tools/check.py                          # check: OK
```

## What Alan will notice (plain words)

Nothing in normal use. If ask creaite (a plain chat, a confirmed request, the catch-up sweep or Intake's Process) tries to stage a
meeting whose spec names a file from outside Intake or the project's meeting folders, or a Word file from outside
`system/staging/drafts/`, the step is refused before it runs, with the reason in one plain sentence ("minutes.py stage: ...").
The command refuses the same spec on its own anyway.

## What changes

`reach.py`, `bash_refusal`: after the record gate, `stage_spec_gate(command)`. For `minutes.py stage` only, it calls
`minutes_spec.validate_spec(<spec>, paths.ROOT)`, the check the command makes, and refuses with its reason; `minutes.py stage`
with anything but one spec path is refused; any error refuses (fail closed). A spec that doesn't exist yet is let through: there
is nothing to read, and the command refuses it itself ("the spec not found", nothing staged); the classification tests
(`test_record_commands.py`) name such a spec. Every other command is unchanged. Held runs still refuse the command earlier, in the
record gate.

## With #264 (Intake's Process)

Checked in a scratch copy of `origin/v253-release` with this branch and `origin/v253-intake-process` (a8eba516) merged and all three
diffs applied (#264's `reach.diff` and `live_server.diff`, and this one): `test_intake_process.py` (25), `test_intake_process_ui.py`,
`test_record_commands.py`, `test_minutes_stage_spec*.py`, `test_enrich_guard.py`, `test_search.py`, `test_stage_pinned.py`,
`test_held_run_bash_writes.py`, `test_panel_sweep.py`, `test_ask_shell_shapes.py`, `test_ask_confirmed_apply.py`,
`test_minutes_record.py`, `test_minutes_review.py`, `test_guard_backslash.py` all pass, and `check.py` is OK, with two fixture lines
changed in #264's test: its specs `pilot.json` and `newdraft.json` had no date or projects, which stage needs anyway
(`intake-process-test-fixture.diff`, against `v253-intake-process`):

```
git apply dev/proposals/minutes-stage-spec/intake-process-test-fixture.diff     # on v253-intake-process, or at the merge
```

Without it, `Fence.test_it_may_read_draft_and_stage_its_own_files` (`stage`, `stage_own_word_draft`) fails once both reach diffs
are in: the hook now refuses those half-specs, as the command itself always would have.

## Search summaries (`search.py enrich set`, the scope addition)

No guarded change: the rule is in `search.py` itself, so it holds in every mode, Process included (#264's mode lets `enrich set`
through; the command then applies this rule). A summary is written for a meeting or report that has none; an existing one is
replaced only for a file that a proposal waiting in Review files (the `to` of a copy or move: a re-extract, a redrafted report),
never a client report's; a path whose file leads outside the vault and the projects folder is refused; every path is checked
before any is written. Tests: `dev/tests/test_enrich_guard.py`.
