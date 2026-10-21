# guard-small: three small guarded changes for 2.6 (a guarded-file change: Alan's to approve)

Four unified diffs, from the LOW notes of Team Cap's independent reviews of #269 (round 2 delta, 21-10-2026 01:08) and #264
(round 2 delta, the M2 leftover). They change `tracker.py`, `live_server.py`, `permissions.py` (one refusal, in the prompt diff) and `reach.py`, which are guarded files: nothing here
edits them. Each diff is written against `origin/v253-release` (23a9db25), which already holds the earlier guarded proposals
(guard-174 with reach-r7, minutes-stage-spec, intake-process round 2 and the rest).

## Apply

From the repo root, each with `-p0` (the headers read `--- system/scripts/<file>`). Check first with `--dry-run` or
`git apply --check -p0`.

```
patch -p0 < dev/proposals/guard-small/tracker-copy-source.diff     # (1) tracker.py
patch -p0 < dev/proposals/guard-small/live-server-prompt.diff      # (2) live_server.py, the prompt; permissions.py
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

**(1) `tracker-copy-source.diff`: a copy's source is a plain file in the right place, and what is checked is what is filed
(#269 delta LOW 1, and round 2 of its review).** `tracker.py apply` filed a copy's `from` from outside the vault: an absolute
path, a `../` path, a source under a symlinked folder and a hard link to an outside file were all filed into the project (the
link check looked only at the last part of the path). New `CopySource` (`open_copy_source`, used by `check_file_op` and
`_op_copy`):
- refuses an empty path or one with a NUL ("source not found", as for a missing file), an absolute path, a drive letter and any
  `..` part;
- **allowed places:** a source must be under `inbox/`, `system/staging/drafts/`, `system/staging/uploads/` (a Current state
  image, BL-63; never `uploads/ask/`, ask creaite's chat images) or `projects/` (the projects folder: in the vault, or the
  projects root outside it, BL-85, including `_portfolio` and the template skeleton). Everything else in the vault
  (`system/tracker.db`, `system/config/`, `.claude/`, `system/staging/applied/`...) is refused;
- opens the source one folder at a time from the real vault folder, or from the projects root when the path is under it (the
  longest base first), each step with `O_NOFOLLOW` (and `O_NONBLOCK` for the file), and keeps the file's folder open;
- requires a regular file, and (`check_name`, on opening and again after every read) that the name, looked up again in the folder
  held open (`os.stat(name, dir_fd=…, follow_symlinks=False)`), is the very file opened (same device and inode), that both the
  name and the descriptor count exactly one link, and that its size and mtime haven't changed. So a hard link to an outside file
  whose vault name is swapped away right after the open (its count drops back to 1: the round 2 MEDIUM) is refused: the name is
  then another file, or none;
- errors say what they are: "not found", "is a link, or is under one", "not a regular file" (a FIFO, a socket, a device, a
  folder), "a name in the source's path is too long";
- `_op_copy` reads in 1 MB chunks from the checked descriptor (never the whole file in memory, never the path again) into a
  temporary file beside the destination (`mkstemp`, `O_EXCL`), sets mode and times on that file's descriptor (`fchmod`,
  `os.utime(fd)`), checks the source's name again, and then puts it in place with a hard link (`EEXIST`: never over a file that
  appeared meanwhile; a rename after one more look where links aren't possible) and removes the temporary name. Any failure
  (a full disk, a refusal) removes the temporary file, so nothing partial is left and a retry works.
- `in_notes_folder` returns False for a path with a NUL (one line): before, a NUL source crashed `tracker.py apply` in
  `card_op_problem` (ValueError), and every later apply with it, until that proposal was removed.

Unchanged: a plain `inbox/`, `system/staging/drafts/` or project file is filed; identical content onto an existing file is a
no-op; differing content is refused and the file kept; the `#269 round 2 (L-B)` marker stays, so `test_copy_source_link` runs.
`import stat` is no longer added at the top of tracker.py (local imports), so E1's own `import stat` hunk applies.

**(2) `live-server-prompt.diff`: a usable PERMISSION example (#269 delta LOW 2).** ask creaite's prompt gave
`PERMISSION: Write(system/search/**) | to save summaries` as its example. Since #269 M-B `system/search` is on reach's never list
for writes, and the panel refuses every Edit or Write rule anyway (`_permission`: ask creaite changes files through
`filechange.py`), so the example only produced a useless card. The example is now only the script form
(`Bash(python3 system/scripts/<name>.py <subcommand> *) | <why>`), with "never an Edit or Write rule: files change through
filechange.py", and the next sentence now says "only a rule for a creaite script is accepted" (it said "or a path inside one
project's folder", which the panel never accepts). The same diff adds one refusal to `permissions.check`: a Bash rule naming
`reach.py` other than its `classify` and `never` commands (so `reach.py hook`, `wrap` or `reach.py *`) is never offered as
addable on the card (the hook refuses those commands in every mode anyway).

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
- `pending` keeps only the newest 64 calls (`PENDING_MAX`); an older call that never returned is dropped and its files stay
  not the run's. The dead `_HOOK["seen"]` loop in `_commit_claims` is gone (nothing fills it since this change).

## Tests

New, each a PROPOSAL test that copies the whole of `system/scripts/` (and `system/templates/`) into a throwaway vault, applies
its diffs there with `patch -p0`, and reads the decisions from the copy (shared set-up: `dev/tests/guard_small_support.py`).
Once a diff is applied to the repo its marker is found and the copy is made with `patch -R` for the unpatched runs, so the same
tests keep guarding the real files.

| Test | Diffs | Tests | Red without the diff |
|------|-------|-------|----------------------|
| `test_guard_small_copy_source.py` | (1) | 12 + mutants | 20 failures and 1 error (every refusal above, the swaps, the NUL crash, the partial write, mode by path; the race hangs on the FIFO) |
| `test_guard_small_prompt.py` | (2) | 5 + mutants | 7 failures (never-list path, Write rule, the path-rule sentence, reach.py rules addable x4) |
| `test_guard_small_post_claim.py` | (3) both | 7 + mutants | 5 failures (failed fill, swapped values, stray Post, settings, pending cap) |

`GUARD_SMALL_UNPATCHED=1 python3 dev/tests/<test>.py` runs them against the copy without the diffs (they must go red).
`GUARD_SMALL_MUTATE=<name>` runs one mutation; each file's `Mutants` test runs them all and fails if one is not caught.
`GUARD_SMALL_RACE=<n>` sets the race's rounds (3,000).

- (1): a source refused in every form: absolute (outside and inside the vault), `../`, `inbox/../…`, a symlinked parent, a hard
  link, a FIFO and a socket ("not a regular file"), a folder, missing, a NUL ("not found"), a 300-character name ("too long"),
  empty, `system/tracker.db`, `system/config/settings.json`, `.claude/settings.json`, `inbox` itself, `system/staging/applied/`,
  an ask creaite chat image; a symlinked `system/staging/drafts` refused. A plain inbox, drafts, upload, `./` and project source
  passes, and so does a file in a
  projects root outside the vault (a link there is refused). A whole apply still files a meeting, keeps the identical-content
  no-op and refuses differing content; a NUL source is refused at apply with no traceback and the next apply runs.
  Deterministic: the name (or the folder above it) swapped for a link right after the open and check: never the outside file;
  a hard link to an outside file whose vault name is replaced by a plain file right after the open (the review's race, made
  exact by wrapping `os.open`): refused; the file growing while it is read: refused; a full disk after the first chunk: refused,
  no destination and no temporary file left, and a retry files it; mode (0640) and mtime kept, set with no `chmod` or `utime` on
  a path. The race: 3,000 rounds, a thread cycling the name between a plain file, a hard link to the outside file, a FIFO and a
  link (atomic renames), and a folder above a second source between a folder and a link: 0 leaks in 2,247 copies; with the first guard-small diff (e7435aaa) the same race leaked 27 times in 2,452 copies. Mutants (10): `..` let
  through, folders followed, the link count ignored, the same-inode check dropped, no check after the read, the copy read by
  path, any vault file a source, a NUL let through, the temporary file left on failure, the mode set by path after placing: all
  caught.
- (2): every PERMISSION example in `ASK_PROMPT` (from the scratch copy) has its paths put through `reach.classify` (none
  "never") and none is an Edit or Write rule; at least one Bash example remains; the prompt never says a path rule is accepted;
  `permissions.check_full` never calls `reach.py hook`, `wrap` or `reach.py *` addable (python3 and the `run` wrapper). Mutants
  (5): the old Write example back, a `Read(~/.ssh/**)` example, an `Edit(projects/…)` example, the path-rule sentence back, the
  reach.py refusal dropped: all caught.
- (3): every call goes through the real hook commands from `live_server.guard_settings`, as Claude Code runs them (PreToolUse,
  the tool itself, then PostToolUse only when the tool succeeded). The PostToolUse is in process mode only (not ask, confirmed
  or sweep); the normal Process flow end to end, for real: Write values, `docx_tools.py fill`, Write the spec, `propose.py people
  map`, `minutes.py stage`: all allowed, the meeting reaches staging with its Word draft; a refused fill claims nothing; an
  allowed fill whose tool fails: another flow's file of that name is neither staged as the draft nor filled over; a values file
  swapped by another flow before its first use is refused, and a failed Write leaves the name unclaimed; a stray PostToolUse
  (another call's `tool_use_id`, another run's `--run`) records nothing; 300 Writes that never return leave 64 pending calls,
  the newest still recorded by its PostToolUse and a dropped one never the run's. Mutants (5): the first-sight trust back, a
  PostToolUse matching every pending call, one for another run, no cap on pending, no PostToolUse in the settings: all caught.

**Changed tests (fixtures only, they pass with and without the diffs):** `test_intake_process.py` and
`test_intake_process_round2.py` seed the run record with the files the run made earlier, so they now also record those files'
prints (as their PostToolUse would have), and a step where the run's own tool makes a file now also runs `reach.post_tool`
when the copy has it (`test_r1_what_the_run_creates_becomes_its_own` gains that step between the fill and the stage).

**Run on a copy of the release with all four diffs applied, one at a time, all OK (round 2):** guard_small_copy_source 13, guard_small_prompt 6, guard_small_post_claim 8 (each with its Mutants test), intake_process 29, intake_process_round2 8, minutes_stage_spec 38, minutes_stage_spec_hook 6, enrich_guard 10, copy_source_link 3, reach 18, guard_pinned 2, ask_reports_refused 6, held_bash_arg_forms 7, record_commands 10, permission_panel 14, script_policy 11, tracker 23, guard_174 25, guard_steerco_adhoc 14, archive_99 44, and the other tests with copy operations: onedrive_projects 44, notes_card_only_ops 18, minutes_draft 18, minutes_record 15, minutes_review 19, propose 20, review_project 11, dashboard_data_pinned 1, writer_pinned 19; `check.py --no-js` OK there and on the repo tree; no_real_names 2 on the repo tree (it needs git). On the repo tree without the diffs the two changed intake tests stay 29 and 8.

## Known limits

- (1) A hard-linked source is refused even when both names are inside the vault (a link count can't tell where the other name
  is). creaite never makes hard links, and macOS doesn't for ordinary files, so nothing legitimate is expected to hit it. A
  file that had a hard link outside whose *outside* name was deleted (so its content now lives only in the vault) is filed: it
  is a vault file by then. A source the user put under a symlinked *vault* or projects root is fine (the walk starts at the real
  folder); a symlinked folder *inside* them is refused. A same-size rewrite in place during the read with the mtime put back is
  not seen (a hostile local writer of a vault file, which is copied as it reads). The destination's folder is still taken by
  path (`safe_path`, as before). `open_copy_source` is now the `CopySource` class (a context manager), and a source from anywhere but `inbox/`, `system/staging/drafts/` or `projects/` is refused at apply.
- (2) The test reads the prompt's examples by the `PERMISSION: <rule> |` shape; a future example written another way is not
  checked.
- (3) The print is taken when the PostToolUse runs, just after the tool returns; another flow that writes that exact drafts name
  in the moment between the tool's end and its PostToolUse is still taken as the run's (a much narrower window than before, the
  whole run; it still needs a predictable name and another creaite flow writing it). A same-size in-place overwrite with the
  mtime put back still matches the print (hostile local writer only; noted in #264 round 2 as INFO). Claude Code runs
  PostToolUse only for a tool that succeeded: a tool that fails half way (a partial file) leaves no print, so the run can't use
  that file or write the name again until it is gone (fails closed; the run writes a new name). The names a run claims
  (`made`, with their prints) are not capped; only `pending` is.

## Composition with E1 (#232 E1, `dev/proposals/intake-232/E1-tracker.diff` on p260-e)

E1 is not changed here. It does not apply to `origin/v253-release` as it is (it was written against tracker.py 2baac5f7, before
#269 L-B): hunks 2 (`@@ -1404,17` `check_file_op` → `_check_copy`) and 4 (`@@ -1598,23` `_op_copy`, `_copy_checked`,
`_op_remove`, `_open_inbox_folder`, `_remove_checked`) fail there. After guard-small the same two hunks fail and nothing else
(hunk 1, `import stat`, applies: guard-small no longer adds that import; checked with `patch -p0` on release + guard-small, 2 of
12 hunks rejected). For the 2.6 assembly, re-base those two hunks on guard-small's tracker.py:
- **hunk 2 (`_check_copy`):** keep E1's `dst.is_dir()` refusal, its "already exists and differs" check and the by_others checks,
  but take the source from guard-small: `with open_copy_source(src) as s:` in place of `paths.resolve(src).is_file()` and the
  `#269 L-B` link check (the source checks are guard-small's), and compare an existing destination with the bytes of
  `s.chunks()`;
- **hunk 4 (`_op_copy`):** keep `dst.is_dir()`; E1's by_others copy should read from guard-small's descriptor and check
  `src_sha256` on those bytes: hash `src.chunks()` as `_copy_into` writes them and refuse before placing the file if the hash
  is not `src_sha256` (a `sha` argument to `_copy_into`, checked after `src.check_name()` and before the link). `_copy_checked`'s
  own path read (`_read_regular(src)`) and its `shutil.copystat` become redundant (guard-small sets mode and times by
  descriptor); `_op_remove`, `_open_inbox_folder` and `_remove_checked` apply unchanged once moved past guard-small's
  `_copy_into`. The assembly's scratch rebase of hunk 2 (asm26-scratch b12e86a8) was against an older E1 diff and is a reference
  only.
