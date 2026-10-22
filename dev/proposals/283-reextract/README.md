# Proposal #283: Read again (Re-extract) as its own run kind (a guarded-file change: Alan's to approve)

**This is a proposal, not an edit.** `system/scripts/reach.py` and `system/scripts/live_server.py` are guarded files: nothing on
this branch changes them. The diffs here do, once Alan (or Jarvis, on his say) applies them after the independent review.
Everything else (`reextract.py`, the page, the usage kind, the skill line, the tests) is on the branch `v26-283-design` and does
nothing harmful without the diffs: Read again then says it couldn't start (the route isn't there: "It couldn't start: check the
live server."), and the tests that need the diffs are expected failures. The design, the fence and the open decisions are in
`DESIGN.md`.

## Files

| File | Against | What |
|---|---|---|
| `reach.diff` | the 2.6 line: `origin/v26-rc-fix` d7ce345e (#232 E1 and #264 round 3 already in; `reach.py` blob be8f4164) | the mode `reextract` (`PROCESS_MODES`, `_reextract_problem`, the hook's own mode in `_process_record`, round 3's PostToolUse for both modes) |
| `live_server.diff` | the same (`live_server.py` blob 5e5018d3) | the two routes, the run kind, the PostToolUse in its `--settings`, the end step (`Run._ended`), recovery at start, usage and plain labels |

**Rebased 22-10-2026 (Team Cap's review, H1).** The earlier pairs were written on `origin/v26-line-4` 7a900841, which had no
#264 round 3, and did not apply to the 2.6 line. Round 3 gives a Process run's file a print only once its PostToolUse hook has
recorded it, and that hook was registered for mode `process` only. A rebase of the old hunks alone would have left Read again
unable to edit its own spec or map its people (it fails closed: "Nothing new"). This pair also:
- registers the PostToolUse for both modes (`live_server.guard_settings`: `mode in reach.PROCESS_MODES`);
- runs `post_tool` for both modes in `hook_main`, passing the hook's mode, and `post_tool(..., mode)` sets and clears
  `_HOOK["mode"]`, so a Post records only on a run of its own mode;
- keeps round 3's `call` (tool_use_id) in `decide`'s `_HOOK.update`, beside the new `mode`;
- (review L1) puts the earlier draft back on any fault starting the run, not only `OSError`.
The old pairs (`reach.diff`/`live_server.diff` on 7a900841, and the `-after-232` pair) are replaced by this one.

## Apply, check, undo

Apply **both files together, in one command** (live_server alone would start the run under a plain chat's hook rules for an
unknown mode: no record command, but not the Read again fence; reach alone adds a mode nothing starts). Order within the
command: `reach.diff`, then `live_server.diff`.

```
git apply --check dev/proposals/283-reextract/reach.diff dev/proposals/283-reextract/live_server.diff
git apply dev/proposals/283-reextract/reach.diff dev/proposals/283-reextract/live_server.diff
```

Checked (22-10-2026) on `origin/v26-rc-fix` d7ce345e merged with this branch: `git apply --check` clean; once applied,
`git apply -R --check` clean and `git apply -R` gives both files back byte for byte. Undo: `git apply -R` with the same two
files. The server must be restarted after applying (the route table and the run kinds are read at start).

## Verify after applying (one at a time; check the load first)

```
python3 dev/tests/test_reextract.py            # 21 tests, all pass (6 are expected failures before the diffs)
python3 dev/tests/test_intake_process.py       # #264 unchanged (29)
python3 dev/tests/test_intake_process_round2.py
python3 dev/tests/test_intake_process_minutes.py
python3 dev/tests/test_calendar_refresh.py
python3 dev/tests/test_reach.py
python3 dev/tests/test_minutes_stage_spec_hook.py
python3 dev/tests/test_record_commands.py
python3 dev/tests/test_live_server.py
python3 dev/tests/test_guard_small_post_claim.py   # round 3 unchanged (its mutants follow the new lines)
python3 dev/tests/test_minutes_stage_client_flags.py   # review M2 (no diff needed)
python3 dev/tests/test_minutes_view_v2.py      # Chrome tier: the bar, the ask, Stop, Undo
python3 dev/tools/check.py                     # check: OK
```

All of these were run with the diffs applied in a throwaway worktree on the 2.6 line and passed; the diffs were then reversed.

## What changes, file by file

**`reach.py` (the guard hook):**
- `PROCESS_MODES = ("process", "reextract")`: every place Process's rules apply (`start_run`'s R1 record, `decide`'s claims,
  direct writes, the reach to the vault and projects only, `record_gate` → `process_gate`) now takes either mode.
- `_HOOK["mode"]`: `decide` keeps the hook's own mode for the call; `_process_record` gives a record only to a hook of the
  record's own mode (a `reextract` hook never treats a Process run's files as its own, and back). Outside a hook call (tests
  calling the helpers directly) the mode is not compared, as before.
- `_reextract_problem` (first in `process_step_problem`, mode `reextract` only): refuses `docx_tools.py fill`, any `search.py
  enrich`, and a `minutes.py stage` spec with a `"draft"` or without a `"minutes"` record. Process's own checks still run
  after it (its one file, no note, the R1 claims).
- Round 3 (#264): `hook_main --event post` runs `post_tool` for either mode, with the hook's mode; `post_tool(tool, inp, run,
  use_id=None, mode=None)` sets and clears `_HOOK["mode"]` (None, as the tests that call it directly, compares no mode).
- Docstrings: `start_run`, `hook_main`'s mode list.

**`live_server.py`:**
- `POST /api/minutes/reextract {proposal, run?}` (`minutes_reextract`): `foreign_origin` 403; `reextract.validate_request` 400;
  under `START_LOCK` a busy 409, then `reextract.hold` (the earlier proposal set aside) and `Run(kind="reextract",
  files=[transcript], label, closer, lines)`; a failed start puts it back. Streamed with `follow`.
- `POST /api/minutes/reextract/undo {run}` (`minutes_reextract_undo`): 403 / 409 while a run is going / `reextract.undo`.
- The run kind: `GUARDED_KINDS`, `KIND_TOOLS` (Process's minus fill and enrich), `KIND_DENIES` (Process's plus fill and
  enrich), `KIND_ARGS` (Process's built-ins, `--strict-mcp-config`), `KIND_PROMPTS`, `NO_CARD_KINDS`; `guard_mode`,
  `guard_args` (its one transcript in `run.json`) and `run_dirs` (the projects folder only) take it as Process.
- `guard_settings`: the PostToolUse (`--event post`) for `reextract` too (round 3: without it the run's own files never get a
  print, so Edit of its spec and `propose.py people map` on it are refused).
- `Run._ended(lines, failed)`: for a stopped or failed run, the kind's own `lines["ended"]` step (Read again puts the earlier
  minutes back) before the Stop or failure line; a fault there is logged and the closure goes on. Called from `_closing`; no
  other kind sets `ended`, so nothing else changes.
- `recover_reextract()` in `main()` after the stale `run.json` is removed: a Read again left `held` by a server that died is
  settled as failed (the earlier minutes back).
- `USAGE_KIND["reextract"]`, `PLAIN_ASK["reextract"] = "Read a meeting's transcript again"`.

**Not changed:** `permissions.py`, `filechange.py`, `tracker.py`, `schema.sql`, `client_leak.py`, the settings files, the rules,
`VERSION`, `.github`.

## Guard-test plan for the reviewer

1. **The fence, through the real hook** (`reach.py hook --mode reextract --run <id>` with a `run.json` written by
   `reach.start_run(..., files=[<transcript>])`): try every record command (apply, undo, approve, reject, bulk, propose stage,
   sweep stage, report, filechange, minutes refresh and carry), `docx_tools.py fill` from a values file the run wrote,
   `search.py enrich set|get`, a stage of another file's spec, of a spec with a `"draft"`, without `"minutes"`, with a `"note"`,
   or of a spec another flow wrote; Writes over the hold (`system/staging/reextract/**`), `run.json`, a proposal, the record in
   drafts, another flow's drafts `.json`, a symlink in drafts, `~/.zshrc`; Read/Grep/Glob of the home folder and `../`; all
   quoted, full-path and chained forms. Expect every one refused; the run's own spec Write and stage allowed.
2. **Mode mixing:** a `reextract` hook against a Process `run.json` and the reverse: nothing of the other's is the run's own.
3. **The route:** forged token, Host, Origin and `Sec-Fetch-Site: cross-site` (both routes) 403; a proposal name with `/`,
   `..`, a symlink, a hard link, a proposal of someone else's minutes, a quick note, a Word draft, one with an approved or applied
   item, a missing transcript: 400 and nothing moved; two clicks: one run (409); Undo during a run: 409.
4. **Settling:** Stop at every step (before the spec, after the spec, after stage), a Claude Code that exits non-zero, a server
   killed mid-run then restarted: in each case the earlier proposal and record are back byte for byte and anything the run
   staged is in `unused/`, nothing deleted. A run that stages twice: the newest takes the place, the other in `unused/`.
5. **Undo:** after an item of the new draft is approved (refused), after the earlier name is taken by another proposal
   (refused), twice (second refused).
6. **Mutants already tried (all caught by test_reextract):** the PostToolUse registered for `process` only
   (`guard_settings`), and `hook_main` running the Post for `process` only (both: Edit of its own spec refused); `_reextract_problem` not called (the no-record spec is let
   through); the hook's mode not compared in `_process_record` (a `reextract` hook takes a Process record). Equivalent mutant
   noted: dropping the `ended` step still puts the earlier minutes back on Stop (the Stop line settles too), but not on a
   failure; test 4 above covers that by hand.
