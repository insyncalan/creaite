# #371 (G2): the run's startup, in the debug log, counts only

Guarded file: `system/scripts/live_server.py`. Patch: `live_server-371.diff`, sha256 `3145004945ec7ae613629b42ad54ed50ad488a64ed70d54ba5037e324fbb37e2`.
Independent of #382 (G1): separate hunks, `git apply --check` clean alone on main and in both orders with G1. Needs Alan's word.
Not pinned; see `dev/proposals/GUARDED-2.6.9-extra.chain`.

## What the real binary shows (probed 26-10-2026)
Run with a check or load's arguments (`--setting-sources "" --no-session-persistence --tools ToolSearch`, an empty folder), the first
`system` init event has `mcp_servers: []` and `tools: ["ToolSearch"]`: the Microsoft 365 connector is NOT listed at start (its tools are
deferred). So the first version's "microsoft365: absent" would always have misled. This version says only what the event lists.

## What it does
- On each run's init event, one debug-log line (area `run`): `<run id> start: mcp servers listed at start: none; tools at start: 1
  (connector tools load on the first ToolSearch)` (`init_summary`, pure; servers counted by status, no names).
- For a transcript job (`job_observe`), after a ToolSearch result: `<id> <kind> tool search: N Microsoft 365 tool names in the result`
  (`m365_names_seen`, a count of distinct names; the result text itself is never logged). If a result does not list names, it reads 0:
  the existing #365 per-result lines still show the calendar and read calls that did run.

## Privacy
Counts and fixed words only: no server name, tool name, title or text. A fault is swallowed.

## Functions touched
New module functions `init_summary`, `m365_names_seen`; new `Run._init_log`; `Run.read` gains a two-line call
(`if kind == "system": self._init_log(ev)`); `Run.job_observe` gains one guarded log line. check.py clean.

## How verified
Throwaway worktree on origin/main: `dev/tests/test_job_init_log_371.py` (6 tests, ordinary, skipped until this lands), including a real
`Run.read` through a stand-in process (the call is made for the init event only; killed when the call is removed).
