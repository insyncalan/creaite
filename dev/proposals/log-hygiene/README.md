# Log hygiene, item 2: log the cause of an unhandled 500 (board #253)

For Jarvis. `live_server.py` is guarded, so this half of #253 is a diff for you to apply. Item 1 (the sweep's done line logs counts only) is already on branch `v252-log-hygiene` as ordinary code.

## The fault

A route that raises is answered as a 500 by `fault()` (POST), `files_get` or `usage_get`, and the debug log gets only the request line, for example `POST /api/settings/catalogue 500 12ms`. The log has no exception class, no frame and no route detail, so a repeat can't be diagnosed. In the one path that did log a cause (an exception escaping `do_GET`/`do_POST` in the `timed` wrapper), `debuglog.exception` wrote `str(e)` and the full traceback. An exception's message can carry the request's own text.

## The change (`live_server.diff`, 83 lines, one file)

- New `log_fault(handler, e)` writes one ERROR line: `POST /api/settings/catalogue raised RuntimeError at settings_catalogue.py:9 in catalogue < live_server.py:5521 in settings_catalogue_route < …`. That is the route, the class name and up to three of the innermost frames (file name only, line and function). It never writes `str(e)` and never writes source text.
- It logs once per route per minute (`FAULT_EVERY = 60`, keyed by method and route, under a lock), so a loop can't flood the log. The request line itself is still logged for each request, as now.
- `CLIENT_LEFT` (`BrokenPipeError`, `ConnectionResetError`) is never a fault. It stays at INFO as `client left: BrokenPipeError` (BL-263, BL-284), with no change.
- It is called from `fault()`, `files_get`, `usage_get` and the `timed` wrapper's `except Exception`. That last one replaces `debuglog.exception`, which wrote `str(e)`.
- `import traceback` is added. A failure inside `log_fault` is swallowed, so the answer is always sent.

## Apply and check

```
git apply --check dev/proposals/log-hygiene/live_server.diff   # checked against v252-release d3a9d706 + cf51de8e
git apply dev/proposals/log-hygiene/live_server.diff
python3 dev/tests/test_log_hygiene.py
```

`LiveServerFault.test_a_route_error_logs_its_class_and_route_once_a_minute` is an expected failure until the diff is applied. The test sees `def log_fault(` in `live_server.py` and then runs as a normal test, so you don't need to edit the test. With the diff applied in a scratch copy, all 8 tests pass. `test_debug_log_wiring.py` gave 30 of 31: the one failure is `test_a_script_that_works_logs_an_exit_zero`, which was already failing on the base commit (doctor flags `system/scripts/confusables.py` for not importing `paths`).

## Mutation proofs (run in the scratch copy)

| Mutation | Result |
|---|---|
| log `str(e)` in the cause line | red (the cause line no longer matches, and "secret words" reaches the log) |
| drop the once-a-minute throttle | red (2 cause lines, not 1) |
| log a page that left as an ERROR fault | red (`test_a_page_that_left_stays_at_info`) |

## Not in this diff (for you to judge)

- `debuglog.exception` in `log.py` still writes `str(value)` and the last traceback lines for every other caller, such as a script that fails. Those messages come from the scripts, not from requests, so I left it alone. Changing it would also break `test_debug_log_wiring`'s check for "ValueError: it broke".
- At about line 8042 of `live_server.py`, the run's card line logs each card item's `title` through `debuglog.clean`, for example `Allow Read(projects/**)`. These are change titles, not message text, and a test expects them. Worth a look under the same rule.
