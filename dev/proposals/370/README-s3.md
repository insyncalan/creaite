# #370 slice 3: guarded patch for live_server.py (2.6.10)

Base: eb32046b (2.6.9 candidate). To be REBASED on the released 2.6.9 before review. Touches `system/scripts/live_server.py` only.
Patch: `live_server-370s3.diff`, sha256 `38802fdb7bd5ae52b7ba7bef54b40f670b2dd9764788c79d0d4eb574a13dfcf3`. Marker: `RUN_LIMITS_370`.

## What and why
| Change | Where | Why |
|---|---|---|
| B2 `RUN_LIMITS_370`, `run_limits(kind)`; `Run._start` appends it to the prompt | after `run_prompt` (~2617); `_start` prompt line (~2799) | The model reached for grep, date, tail and scripts the kind may not run. Each of sweep, process, calendar, reextract, check, load now gets today's date (`build_dashboard.clock()`, honours CREAITE_NOW) and its own script commands, derived from `KIND_TOOLS` (not in `READ_TOOLS`), or "no shell". `run_prompt` and `KIND_PROMPTS` are unchanged, so test_job_prompts_365 stays green. No allow list or hook changes. |
| B1 `Run._count_refusal`, call in `_on_tool_result`, one line in `_done` | ~2990, ~3208 | Counts the guard hook's refusals (error results containing "creaite refused this") per run; logs `<id> <kind> refusals: N` at info. Counts only. No new branch in `_on_tool_result`; `Run.__init__` untouched. |
| D1 `settings_catalogue_route` | ~6242 | `OSError`/`ValueError` from `catalogue()` gives 503 `{ok:false, retry:true, message}` with `Retry-After: 1` and an info log (class only), not a 500. |
| D3 `LocalServer.handle_error` | ~3950 | `BrokenPipeError`/`ConnectionResetError` (CLIENT_LEFT) logged at info "client left", no traceback; any other error goes to the standard handler. |

Functions touched: `run_prompt` neighbour (new `run_limits`), `Run._start` (one line), `Run._on_tool_result` (one call), new `Run._count_refusal`, `Run._done` (3 lines), `LocalServer.handle_error` (new), `settings_catalogue_route`.

## Verified (throwaway worktree on eb32046b)
`git apply --check`, apply, `py_compile`, `dev/tools/check.py` OK (no complexity or long-line change; longest added line 134, limit 140). Tests: test_job_prompts_370, test_handle_error_370, test_catalogue_503_370 (skip when unpatched), test_job_prompts_365, test_job_tools_365, test_run_tools_explicit, test_held_edit_deny, test_guard_pinned, test_fresh_ask_327, test_lighter_runs_339, test_live_* (7), test_no_real_names: all green. test_guarded_chain not run (its 2.6.9 pin is in v269-main only); the diff touches only live_server.py. Mutants (each change removed) each fail a test.

## Rebase anchors
Context lines that change on the released 2.6.9 (it carries the G1/G2 hunks): the `@@` hunks at `run_prompt`/`guard_mode` (insert before `def guard_mode`), `_start`'s `prompt = PANEL_SWEEP_PROMPT if sweep else run_prompt(kind, confirmed)` line, `def _on_tool_result(self, part):`, `def _done(self):` followed by `self._usage_record()`, `def server_bind(self):` in `LocalServer`, and `settings_catalogue_route`'s body. Re-run the diff with `git apply --3way` or regenerate from the anchors above.
