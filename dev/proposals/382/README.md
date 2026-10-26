# #382 (G1): check and load start context-less; the load search is bounded

Guarded file: `system/scripts/live_server.py`. Patch: `live_server-382.diff`, sha256 `be27770da2b4dfcc95d66e7c1d605820f596525bbf2af78142c45b976273c9e3`.
It is the #365 follow-up (`live_server-365-followup.diff`, 5687339225f38235, Cap's three MEDIUMs) rebased on current main: only the
`run_dirs` hunk changed (#339 A added "sweep" and extended its docstring). Needs Alan's word on these bytes. Not pinned; see
`dev/proposals/GUARDED-2.6.9-extra.chain`.

## What it does
- `CONTEXTLESS_JOBS = ("check", "load")` (new, after the #365 KIND_TOOLS lines): these two start like #183's draft run: an empty folder
  outside the vault, `NO_CONTEXT_ARGS` (`--setting-sources ""`, no session saved), `NO_CONTEXT_ENV`, and no `--add-dir`. The Microsoft
  365 connector is account-level so it stays; held mode's hook is still passed with `--settings`.
- `launch_context`: `policy in TOOLLESS_KINDS or policy in CONTEXTLESS_JOBS` takes the context-less branch.
- `run_dirs`: the same condition returns `[]`.
- `TRANSCRIPT_PROMPT` step 1: search one hour either side of the meeting, then the whole day, then the exact start and end; never
  more than three searches, then stop and say so; take only the event whose id is exactly the asked one.

## Revision 2 (after the independent review)
- Model (revision 3): check and load stay on Sonnet. `NO_CONTEXT_ARGS` names `--model sonnet` and they take it with the rest of
  the context-less start, like the tool-less kinds and #183's draft run. With no settings files the model must be named, and a
  transcript load must not move silently to the account's default model (probed 26-10-2026: `claude-opus-5-5`, probably dearer).
  Cost and quality: a lookup of one event and one transcript is a few cheap calls, so Sonnet's cost is low; the load reads and saves
  what the calls return and does no writing, so quality is not affected. Before this change they ran on the model in Alan's settings.
- KIND_PROMPTS for check and load now says "headless in an empty folder outside the vault" (same hunk).
- The three-search bound is a prompt rule. Server side, with no guarded code: `transcripts.Job.searches()` counts the calendar searches
  and `Job.diagnosis()` (debug log, counts only) says "calendar searches: 4 (over the bound of 3)". No hard stop: one needs a
  per-tool counter in the guarded run engine; LOW because a fourth search only costs one call and the run is already narrowed to two tools.
- Tests: `test_job_followup_365` gains the M1 test (a non-empty `extra_dirs()` still gives these kinds no `--add-dir`), the Sonnet test and
  the wording test; mutants dropping the `run_dirs` clause, is killed.

## Functions touched
`launch_context`, `run_dirs` (one condition each), the constant `TRANSCRIPT_PROMPT`, the new constant `CONTEXTLESS_JOBS`.

## How verified
In a throwaway worktree on origin/main: `git apply --check` clean; `dev/tests/test_job_followup_365.py` (3 tests, ordinary commit,
skipped until this lands) passes with it; the neighbouring suites and `check.py` run with both G1 and G2 applied (results in the
report). Never applied in the committed branch.
