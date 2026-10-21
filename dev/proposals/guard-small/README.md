# guard-small: three small guarded changes for 2.6 (a guarded-file change: Alan's to approve)

Four unified diffs, from the LOW notes of Team Cap's independent reviews of #269 (round 2 delta, 21-10-2026 01:08) and #264
(round 2 delta, the M2 leftover). They change `tracker.py`, `live_server.py` and `reach.py`, which are guarded files: nothing here
edits them. Each diff is written against `origin/v253-release` (23a9db25), which already holds the earlier guarded proposals
(guard-174 with reach-r7, minutes-stage-spec, intake-process round 2 and the rest).

## Apply

From the repo root, each with `-p0` (the headers read `--- system/scripts/<file>`). Check first with `--dry-run` or
`git apply --check -p0`.

```
patch -p0 < dev/proposals/guard-small/tracker-copy-source.diff     # (1) tracker.py
patch -p0 < dev/proposals/guard-small/live-server-prompt.diff      # (2) live_server.py, the prompt
patch -p0 < dev/proposals/guard-small/reach-post-claim.diff        # (3) reach.py
patch -p0 < dev/proposals/guard-small/live-server-post-hook.diff   # (3) live_server.py, the run's --settings
```

The diffs are independent of each other: any order applies cleanly (the two `live_server.py` diffs touch lines about 80 apart).
(3) is two diffs that belong together: apply both or neither. `reach-post-claim.diff` without `live-server-post-hook.diff`
fails closed (a Process run's own files are never recorded, so its fill and its staging of a Word draft are refused: Process
stops working, nothing opens); the hook diff without the reach diff makes the old hook (which doesn't know `--event`) decide
each call a second time after it ran (nothing more is allowed; a refusal there only shows Claude a message).

**Undo:** `patch -p0 -R` in the opposite order, or `git revert` the commit that applied them.

## What each does

**(1) `tracker-copy-source.diff`: a copy's source stays in the vault (#269 delta LOW 1).** `tracker.py apply` filed a copy's
`from` from outside the vault: an absolute path, a `../` path, a source under a symlinked folder and a hard link to an outside
file were all filed into the project (the link check looked only at the last part of the path). New `open_copy_source` (used
by `check_file_op` and `_op_copy`):
- refuses an empty or absolute path, a drive letter and any `..` part;
- opens the source one folder at a time from the real vault folder, or from the projects root when the path is under it
  (BL-85, `paths.resolve`; the longest base first), each step with `O_NOFOLLOW` (and `O_NONBLOCK` for the file), so a link
  anywhere on the way fails, whenever it was put there;
- refuses anything but a regular file with exactly one link (`st_nlink == 1`);
- `_op_copy` copies from the very descriptor it checked (never by its path again), creates the copy with `"xb"` (never over a
  file that appeared meanwhile) and keeps the mode and times, as `shutil.copy2` did.

Unchanged: a plain `inbox/`, `system/staging/drafts/` or project file is filed; identical content onto an existing file is a
no-op; differing content is refused and the file kept; the `#269 round 2 (L-B)` marker stays, so `test_copy_source_link` runs.

**(2) `live-server-prompt.diff`: a usable PERMISSION example (#269 delta LOW 2).** ask creaite's prompt gave
`PERMISSION: Write(system/search/**) | to save summaries` as its example. Since #269 M-B `system/search` is on reach's never list
for writes, and the panel refuses every Edit or Write rule anyway (`_permission`: ask creaite changes files through
`filechange.py`), so the example only produced a useless card. The example is now only the script form
(`Bash(python3 system/scripts/<name>.py <subcommand> *) | <why>`), with "never an Edit or Write rule: files change through
filechange.py".

**(3) `reach-post-claim.diff` + `live-server-post-hook.diff`: a Process run's file is its own only once its tool has returned
(#264 round 2 LOW leftover).** Before, the PreToolUse hook claimed a drafts name (`made`) and the file's fingerprint was taken at
first sight, the next time the hook looked; so if an allowed `fill` then failed to make its file, or another flow put a file in
place of the run's values file between the run's Write and its first use, that other file was the run's at first sight
(`minutes.py stage` with it as the Word draft, or a fill from it, was allowed). Now:
- `live_server.guard_settings` adds, for mode `process` only, a PostToolUse hook: the same command plus `--event post`.
- The PreToolUse (`decide`, `_commit_claims`) still claims only after every check has passed (round 2) and sets the call's files
  to "no print", and records them in run.json `pending` with the call's `tool_use_id` (or, when Claude Code gives none, a
  SHA-256 of the tool and its input).
- `reach.py hook ... --event post` (`post_tool`) runs when the tool has returned: under the record's lock, for this hook's own
  run only (the `--run` check, L4), it finds the pending call (by `tool_use_id`, else by the call's fingerprint) and records the
  print (inode, size, mtime) of each of its files as they are now, then drops the entry. A PostToolUse that matches no pending
  call records nothing; it always exits 0 (a PostToolUse can't block anyway).
- `_runs_own` trusts a file only when its recorded print is a real print that matches now. No PostToolUse (the tool failed,
  the hook didn't run, an old server without the hook diff): no print, never the run's (fail closed). The run can then only
  claim the name again while no file has it.

## Tests

New, each a PROPOSAL test that copies the whole of `system/scripts/` (and `system/templates/`) into a throwaway vault, applies
its diffs there with `patch -p0`, and reads the decisions from the copy (shared set-up: `dev/tests/guard_small_support.py`).
Once a diff is applied to the repo its marker is found and the copy is made with `patch -R` for the unpatched runs, so the same
tests keep guarding the real files.

| Test | Diffs | Tests | Red without the diff |
|------|-------|-------|----------------------|
| `test_guard_small_copy_source.py` | (1) | 6 + mutants | 10 failures (absolute, `..` x3, linked parent, hard link, linked drafts folder, swap, race: 135 leaks in 4,004 copies) |
| `test_guard_small_prompt.py` | (2) | 3 + mutants | 2 failures (never-list path, Write rule) |
| `test_guard_small_post_claim.py` | (3) both | 6 + mutants | 4 failures (failed fill, swapped values, stray Post, settings) |

`GUARD_SMALL_UNPATCHED=1 python3 dev/tests/<test>.py` runs them against the copy without the diffs (they must go red).
`GUARD_SMALL_MUTATE=<name>` runs one mutation; each file's `Mutants` test runs them all and fails if one is not caught.

- (1): a source outside the vault refused in every form (absolute, absolute inside the vault, `../`, `inbox/../…`, a symlinked
  parent, a hard link, a FIFO, a folder, missing, empty); a symlinked `system/staging/drafts` refused; a plain inbox, drafts and
  `./` source passes; a whole apply still files a meeting, keeps the identical-content no-op and refuses differing content;
  a deterministic swap of the file, and of the folder above it, right after the check files the plain content; and the
  3,000-round race (a thread flipping the source between file and link, and a folder above another source between folder and
  link): 0 leaks, with copies made in between. Mutants: `..` let through, folders followed, a second hard link let through, the
  copy read again by its path: all caught.
- (2): every PERMISSION example in `ASK_PROMPT` (from the scratch copy) has its paths put through `reach.classify` (none
  "never") and none is an Edit or Write rule; at least one Bash example remains. Mutants: the old Write example back, a
  `Read(~/.ssh/**)` example, an `Edit(projects/…)` example: all caught.
- (3): every call goes through the real hook commands from `live_server.guard_settings`, as Claude Code runs them (PreToolUse,
  the tool itself, then PostToolUse only when the tool succeeded). The PostToolUse is in process mode only (not ask, confirmed
  or sweep); the normal Process flow end to end, for real: Write values, `docx_tools.py fill`, Write the spec, `propose.py people
  map`, `minutes.py stage`: all allowed, the meeting reaches staging with its Word draft; a refused fill claims nothing; an
  allowed fill whose tool fails: another flow's file of that name is neither staged as the draft nor filled over; a values file
  swapped by another flow before its first use is refused, and a failed Write leaves the name unclaimed; a stray PostToolUse
  (another call's `tool_use_id`, another run's `--run`) records nothing. Mutants: the first-sight trust back, a PostToolUse
  matching every pending call, one for another run, no PostToolUse in the settings: all caught.

**Changed tests (fixtures only, they pass with and without the diffs):** `test_intake_process.py` and
`test_intake_process_round2.py` seed the run record with the files the run made earlier, so they now also record those files'
prints (as their PostToolUse would have), and a step where the run's own tool makes a file now also runs `reach.post_tool`
when the copy has it (`test_r1_what_the_run_creates_becomes_its_own` gains that step between the fill and the stage).

**Run on a copy of the release with all four diffs applied, one at a time, all OK:** guard_small_copy_source 7, guard_small_prompt 4, guard_small_post_claim 7 (each with its mutants), intake_process 29, intake_process_round2 8, minutes_stage_spec 38, minutes_stage_spec_hook 6, enrich_guard 10, copy_source_link 3, reach 18, guard_pinned 2, ask_reports_refused 6, held_bash_arg_forms 7, record_commands 10, permission_panel 14, script_policy 11, tracker 23, guard_174 25, guard_steerco_adhoc 14, archive_99 44; `check.py --no-js` OK there and on the repo tree; no_real_names 2 on the repo tree (it needs git). On the repo tree without the diffs the two changed intake tests stay 29 and 8.

## Known limits

- (1) A hard-linked source is refused even when both names are inside the vault (`st_nlink > 1` can't tell where the other
  name is). creaite never makes hard links, and macOS doesn't for ordinary files, so nothing legitimate is expected to hit it.
  A source the user put under a symlinked *vault* or projects root is fine (the walk starts at the real folder); a symlinked
  folder *inside* them is refused. A file whose content another process rewrites in place while it is copied is copied as it
  reads (same as before).
- (2) The test reads the prompt's examples by the `PERMISSION: <rule> |` shape; a future example written another way is not
  checked.
- (3) The print is taken when the PostToolUse runs, just after the tool returns; another flow that writes that exact drafts name
  in the moment between the tool's end and its PostToolUse is still taken as the run's (a much narrower window than before, the
  whole run; it still needs a predictable name and another creaite flow writing it). A same-size in-place overwrite with the
  mtime put back still matches the print (hostile local writer only; noted in #264 round 2 as INFO). Claude Code runs
  PostToolUse only for a tool that succeeded: a tool that fails half way (a partial file) leaves no print, so the run can't use
  that file or write the name again until it is gone (fails closed; the run writes a new name). Pending entries of failed calls
  stay in run.json until the run ends (a few names; never trusted).
