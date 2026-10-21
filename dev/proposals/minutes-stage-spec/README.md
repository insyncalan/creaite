# Proposal #269: the hook checks `minutes.py stage`'s spec too (a guarded-file change: Alan's to approve)

**This is a proposal, not an edit.** `system/scripts/reach.py` is a guarded file: nothing on this branch changes it. The fix
itself is already on the branch and needs no guarded change: `minutes.py stage` checks its own spec (`minutes_spec.py`) before
it reads anything, so the protection holds in every mode, with or without this diff. The diff adds the same check at the ask
creaite hook, so a refused spec never reaches the script (defence in depth), and (round 2, M-B) puts `system/search/` on the never
list for writes, so a search summary can't be replaced by `filechange.py edit`. A second, separate diff (`tracker-copy-link.diff`,
round 2, L-B) makes `tracker.py apply` file a copy only from a plain file.

## Apply, check, undo

From the repo root:

```
git apply --check dev/proposals/minutes-stage-spec/reach.diff
git apply dev/proposals/minutes-stage-spec/reach.diff
```

Checked on `origin/v253-release` (830359dd, with #264's round 1 and round 2 and #265's guarded diffs already applied): clean, and
`git apply -R --check` is clean once applied. Undo: `git apply -R dev/proposals/minutes-stage-spec/reach.diff`.

The second diff is independent (either order, either alone):

```
git apply --check dev/proposals/minutes-stage-spec/tracker-copy-link.diff
git apply dev/proposals/minutes-stage-spec/tracker-copy-link.diff
```

Verify after applying (one at a time):

```
python3 dev/tests/test_minutes_stage_spec_hook.py   # 6 tests: skipped until reach.diff is applied, then all pass
python3 dev/tests/test_copy_source_link.py          # 3 tests: skipped until tracker-copy-link.diff is applied, then all pass
python3 dev/tests/test_minutes_stage_spec.py        # 38 tests: the command's own check (passes with or without the diffs)
python3 dev/tests/test_intake_process.py            # 29 tests (with the fixture diff below)
python3 dev/tests/test_intake_process_round2.py     # 8 tests (with the fixture diff below)
python3 dev/tests/test_record_commands.py
python3 dev/tools/check.py                          # check: OK
```

## What Alan will notice (plain words)

Nothing in normal use. If ask creaite (a plain chat, a confirmed request, the catch-up sweep or Intake's Process) tries to stage a
meeting whose spec names a file from outside Intake or the project's meeting folders, or a Word file from outside
`system/staging/drafts/`, the step is refused before it runs, with the reason in one plain sentence ("minutes.py stage: ...").
The command refuses the same spec on its own anyway.

## What changes

`reach.py`, `NEVER` (round 2, M-B): `("vault", "system/search", "write", RECORD)`. Writing, changing or deleting a search summary
is refused to ask creaite in every mode (before, with a summary present, `filechange.py edit system/search/<sha256>.json --from
system/staging/drafts/x.json` was ordinary: done at once, no card, defeating "a summary is written once"). Reading is unchanged.
`search.py enrich set` and `tracker.py` write there themselves, not through `filechange.py`, so they are unaffected (tested).

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
changed in #264's tests: specs with no date or projects, which stage needs anyway (`intake-process-test-fixture.diff`, now on
the release): `pilot.json`, `newdraft.json` and (round 2, M-A) `chain.json` in `test_intake_process.py`, and `own.json` and
`pilot.json` in `test_intake_process_round2.py`:

```
git apply dev/proposals/minutes-stage-spec/intake-process-test-fixture.diff     # with reach.diff
```

Without it, once `reach.diff` is in, `test_intake_process.py` fails 3 of 29 (`stage`, `stage_own_word_draft`, `stage_chain`) and
`test_intake_process_round2.py` 2 of 8: the hook now refuses those half-specs, as the command itself always would have. With it:
29 of 29 and 8 of 8. The two test files aren't guarded; the change is kept as a diff because it only matters with `reach.diff`.

## Search summaries (`search.py enrich set`, the scope addition)

No guarded change: the rule is in `search.py` itself, so it holds in every mode, Process included (#264's mode lets `enrich set`
through; the command then applies this rule). A summary is written for a meeting or report that has none; an existing one is
replaced only for a file that a proposal waiting in Review files (the `to` of a copy or move: a re-extract, a redrafted report),
never a client report's; a path whose file leads outside the vault and the projects folder is refused; every path is checked
before any is written. Tests: `dev/tests/test_enrich_guard.py`.

## Round 2 (Cap's review of 757f544c)

- **M-B**, a summary replaced by `filechange.py edit`: the `NEVER` entry above, in `reach.diff`. Tests:
  `test_minutes_stage_spec_hook.py`, `SearchSummariesAreOnTheNeverList` (fail without the entry, pass with it).
- **M-A**, the fixture diff missed `chain.json`: fixed above, and `test_intake_process_round2.py` (new on the release) added.
- **L-A**, a named pipe swapped in after the check hung the command: `minutes_spec._read_once` opens with `O_NONBLOCK`, so the
  plain-file check refuses it at once (unguarded, on the branch). Test: `test_a_spec_swapped_for_a_named_pipe_...` (hung before).
- **L-B**, a transcript swapped for a link after the check was still filed: `tracker-copy-link.diff` refuses a copy whose source is
  a link, in `check_file_op` and again in `_op_copy` just before copying. Only the last part of the path is checked, so a
  projects folder reached through a link (`~/OneDrive` on a Mac) still works. Tests: `test_copy_source_link.py`.
- **L-C**, docs: cx-minutes now says a chat doesn't write into `inbox/` without Alan's Approve on the card, and to use Intake; the
  enrich step says a summary is written once and replaced only for what a proposal waiting in Review files.

## Residuals

- **L-B, before `tracker-copy-link.diff` is applied:** only the spec is pinned; a transcript swapped for a link between `stage`
  and apply is filed (needs a writer in `inbox/`; pre-existing). A hard link can't be told from a plain file at apply.
- **L-D:** a report `.docx` in `system/staging/drafts/` that no proposal names yet can be given as a meeting's draft and stages as
  minutes. Alan sees it in Review, where it is rejected; nothing is filed without his approval.
- **"Refused at apply":** a copy onto a file that is already there with identical content is a no-op (the file is already filed),
  so "never overwritten, refused at apply" holds for differing content only. Nothing is changed either way.
