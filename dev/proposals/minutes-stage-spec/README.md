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
with anything but one spec path is refused; any error refuses (fail closed). Every other command is unchanged. Held runs still
refuse the command earlier, in the record gate.
