# #370 slice 3: guarded patch for live_server.py (2.6.10)

Revision 2. Base: v269-release 0b637e92 (released 2.6.9; the first draft was on eb32046b). Applies with plain `git apply`, no 3-way needed. Touches `system/scripts/live_server.py` only.
Patch: `live_server-370s3.diff`, sha256 `b4d4c7a5193e0fedf6c1adf3dc03034369e24beb551c535a4024b3bbdf9bc867`. Marker: `RUN_LIMITS_370`.

## What and why
| Change | Where | Why |
|---|---|---|
| B2 `RUN_LIMITS_370`, `run_limits(kind)`; `Run._start` appends it to the prompt | after `run_prompt` (~2617); `_start` prompt line (~2799) | The model reached for grep, date, tail and scripts the kind may not run. Each of sweep, process, calendar, reextract, check, load now gets today's date (`build_dashboard.clock()`, honours CREAITE_NOW) and its own script commands, derived from `KIND_TOOLS` (not in `READ_TOOLS`), or "no shell". `run_prompt` and `KIND_PROMPTS` are unchanged, so test_job_prompts_365 stays green. No allow list or hook changes. |
| B1 `Run._count_refusal`, call in `_on_tool_result`, one line in `_done` | ~2990, ~3208 | Counts the guard hook's refusals (error results containing "creaite refused this") per run; logs `<id> <kind> refusals: N` at info. Counts only. No new branch in `_on_tool_result`; `Run.__init__` untouched. |
| D1 `settings_catalogue_route`, `CATALOGUE_FAILS`, `catalogue_lasting` | ~6242 | A transient `OSError` gives 503 `{ok:false, retry:true, message}` with `Retry-After: 1` and a WARN (class only). A `ValueError` (corrupt settings.json) or the third failure within 60 s gives a 500 "Settings can't be read. See Settings > Health." and an ERROR (class only). Success clears the counter. Module-level list, no thread. |
| D3 `LocalServer.handle_error` | ~3950 | `BrokenPipeError`/`ConnectionResetError` (CLIENT_LEFT) logged at info "client left", no traceback; any other error goes to the standard handler. |

Functions touched: `run_prompt` neighbour (new `run_limits`), `Run._start` (one line), `Run._on_tool_result` (one call), new `Run._count_refusal`, `Run._done` (3 lines), `LocalServer.handle_error` (new), `settings_catalogue_route`.

## Verified (throwaway worktree on eb32046b)
`git apply --check`, apply, `py_compile`, `dev/tools/check.py` OK (no complexity or long-line change; longest added line 134, limit 140). The prompt sentence reads "Do not run grep, tail or date, and never read a file that neither the message nor your own skill's read list names." (the skills' read-first registers stay allowed; a test checks the skills still carry them). Tests: test_job_prompts_370, test_handle_error_370, test_catalogue_503_370 (skip when unpatched), test_job_prompts_365, test_job_tools_365, test_run_tools_explicit, test_held_edit_deny, test_guard_pinned, test_fresh_ask_327, test_lighter_runs_339, test_live_* (7), test_no_real_names: all green. test_guarded_chain not run (its 2.6.9 pin is in v269-main only); the diff touches only live_server.py. Mutants (each change removed) each fail a test.

## Rebase notes
Rebased on 0b637e92 (released 2.6.9): the revision-1 diff applied with `git apply --3way` without conflict, and the final diff was regenerated on 0b637e92 and checks cleanly in reverse. Hunk anchors: before `def guard_mode`; `_start`'s prompt line; `_on_tool_result`; `_done`; `LocalServer.server_bind`; `settings_catalogue_route`. On the full re-run test_guarded_chain (185 tests) passes with the patch applied; check.py OK, no new long lines.
