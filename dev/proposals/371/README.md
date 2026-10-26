# #371 (G2): the run's startup, in the debug log, counts only

Guarded file: `system/scripts/live_server.py`. Patch: `live_server-371.diff`, sha256 `6a761e1cfb8f53bd2aaaae4a0eb8e926d207348a322c85b5c63b92fca4ecdd0a`.
Independent of #382 (G1): separate hunks, `git apply --check` clean alone on main and in both orders with G1. Needs Alan's word.
Not pinned; see `dev/proposals/GUARDED-2.6.9-extra.chain`.

## What it does
For each run, on Claude's `system` event with subtype `init`, one debug-log line (area `run`):
`<run id> start: mcp servers: connected 2, needs-auth 1; microsoft365: connected; m365 tools: 12 of 30 tools`.
It is the diagnostic for the failed transcript loads (the cause is unproven; this names it on the next failure).

## Privacy
Counts and fixed words only: server counts by status, the Microsoft 365 connector's status (its name is never logged, nor any
other server's), the number of Microsoft 365 tools and the total. No title, text, tool name or user data. A fault is swallowed.

## Functions touched
New module function `init_summary(ev)` (pure); new `Run._init_log(self, ev)`; `Run.read` gains a two-line call
(`if kind == "system": self._init_log(ev)`), so `read` grows by one branch (check.py complexity checked).

## How verified
Throwaway worktree on origin/main: `dev/tests/test_job_init_log_371.py` (3 tests, ordinary commit, skipped until this lands) passes
with it; both orders of G1/G2 apply cleanly; `check.py` and the neighbouring suites with both applied (see the report).
