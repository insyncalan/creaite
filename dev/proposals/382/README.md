# #382 (G1): check and load start context-less; the load search is bounded

Guarded file: `system/scripts/live_server.py`. Patch: `live_server-382.diff`, sha256 `d04410c0aa4f3447613ba7d549110ff957797d850722e0a90999f393b63b6ea3`.
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

## Functions touched
`launch_context`, `run_dirs` (one condition each), the constant `TRANSCRIPT_PROMPT`, the new constant `CONTEXTLESS_JOBS`.

## How verified
In a throwaway worktree on origin/main: `git apply --check` clean; `dev/tests/test_job_followup_365.py` (3 tests, ordinary commit,
skipped until this lands) passes with it; the neighbouring suites and `check.py` run with both G1 and G2 applied (results in the
report). Never applied in the committed branch.
