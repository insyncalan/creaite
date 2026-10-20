# Log hygiene, item 2: log the cause of an unhandled error, never its words (board #253)

For Jarvis. `live_server.py` is guarded, so this half of #253 is a diff for you to apply. Item 1 (the sweep's done line logs counts only) is already on branch `v252-log-hygiene` as ordinary code.

This is the second version. An independent review of the first found that the result routes still logged `str(e)`, and that a background thread's error was not covered. Both are in `live_server.diff` now. The card-title line is a question for you, below, with its own optional diff.

## The fault

A route that raises is answered as a 500 by `fault()` (POST), `files_get` or `usage_get`, and the debug log gets only the request line, for example `POST /api/settings/catalogue 500 12ms`. The log has no exception class, no frame and no route detail, so a repeat can't be diagnosed. Where a cause was logged, it was logged with its words:

- The `timed` wrapper's `except Exception` used `debuglog.exception`, which writes `str(e)` and the traceback.
- **The result routes** (`RESULT_ROUTES`: `/api/apply`, `/api/undo`, `/api/review`). `logged_send` kept the body's `message` as `_log_msg`, and `log_request` wrote it at WARN as `not ok: <message>`. For a fault that message is `fault()`'s `Class: str(e)`. For a refused apply it is tracker.py's own output, which can quote an item. For example: `POST /api/apply 200 119ms not ok: Validation failed: ABC-A-999 description '…' is too long`.
- **Background threads** (the VIP timer, the apply worker, the backup timer, the prep queue and so on). An uncaught error went only to Python's own hook, so the debug log had nothing.

## The change (`live_server.diff`, 149 lines, one file)

- New `log_cause(key, e)` writes one ERROR line: `<key> raised <Class> at <file.py>:<line> in <function> < …`. That is up to three of the innermost frames, by file name only. It never writes `str(e)` or source text. It logs once per key per minute (`FAULT_EVERY = 60`, under a lock), so a loop can't flood the log. A failure inside it is swallowed.
- `log_fault(handler, e)` calls it with the key `METHOD route`. It is called from `fault()`, `files_get`, `usage_get` and the `timed` wrapper. That last one replaces `debuglog.exception`. `CLIENT_LEFT` is never a fault: it stays at INFO as `client left: BrokenPipeError` (BL-263, BL-284), unchanged.
- **Result routes.** `logged_send` no longer keeps the message: `_log_msg` is gone. `fault()` sets `_log_cls = type(e).__name__`. `log_request` writes `POST /api/apply 200 119ms not ok` for a refusal and `POST /api/apply 500 121ms not ok: JSONDecodeError` for a fault, which also gets the ERROR cause line above. The page still gets the full message, as now.
- **Background threads.** `install_thread_faults()` is called from `install_debug_log()`. It wraps `threading.excepthook` to log `thread <name> raised <Class> at …` through `log_cause`, once a minute per thread name, then hands the error to Python's own hook. A thread's name is Python's own (`Thread-3 (vip_timer)`) or the one it was given, reduced to `A-Za-z0-9_ ().-`. `SystemExit` is skipped.
- `import traceback` is added.

## Apply and check

```
git apply --check dev/proposals/log-hygiene/live_server.diff   # checked against origin/main 4e564fcf
git apply dev/proposals/log-hygiene/live_server.diff
python3 dev/tests/test_log_hygiene.py
python3 dev/tests/test_debug_log_wiring.py
```

`test_log_hygiene.py` has four live-server tests that are expected failures until the diff is applied. The test sees `def log_fault(` in `live_server.py` and then runs them as normal tests, so you don't need to edit the test. The four tests:

- `test_a_route_error_logs_its_class_and_route_once_a_minute`
- `test_a_failed_apply_logs_not_ok_and_never_its_message`: a stand-in tracker.py refuses with item words.
- `test_an_apply_that_raises_logs_its_class_and_route_only`: a stand-in tracker.py makes `/api/apply` raise `JSONDecodeError`.
- `test_a_background_thread_error_logs_its_class_and_thread_once`

I checked this in a scratch worktree at origin/main 4e564fcf with the diff applied. `test_log_hygiene.py` passed 11 of 11. `test_debug_log_wiring.py` passed 31 of 31, with `card_titles_test.diff` applied too (below). Without the diff, the new tests fail on the canaries. For example, the log held `not ok: Validation failed: … 'CANARY-APPLY-WORDS' …` and `not ok: JSONDecodeError: Expecting value: …`, and it had no thread line.

## Mutation proofs (run in the scratch copy)

| Mutation | Result |
|---|---|
| log `str(e)` in the cause line (first version) | red |
| drop the once-a-minute throttle (first version) | red (2 cause lines, not 1) |
| log a page that left as an ERROR fault (first version) | red |
| `_log_cls` set to `Class: str(e)` | red (`test_an_apply_that_raises…`) |
| `install_thread_faults()` not called | red (`test_a_background_thread…`) |

## Questions for you

1. **The card-title line, about line 8041.** When a run asks for changes, the "changes" log line lists each card item's `title` through `debuglog.clean`. A title is `{OP} {path} → {to}`, for example `Move projects/ABC Example/08 Notes/<a personal note's name>.md → …`, or a path under the home folder. That breaks the same rule. **Suggested fix:** log the count and the ops only, for example `card c-1a2b: 3 changes for approval, 0 refused: create 2, edit 1`. That fix is `card_titles.diff`. It applies on its own or after `live_server.diff`. Its test change is `card_titles_test.diff`, for `test_debug_log_wiring.py`, which now expects the title `Allow Read(projects/**)`. Apply both or neither:
   ```
   git apply dev/proposals/log-hygiene/card_titles.diff dev/proposals/log-hygiene/card_titles_test.diff
   ```
2. **The server's console log.** `system/staging/live-server.log` is the launcher's stdout and stderr, not the debug log. Python's own thread hook and `socketserver`'s error handler still write full tracebacks there, with `str(e)`. I left that alone, because it is how a crash is diagnosed in Terminal. Say if you want it quietened too.
3. `debuglog.exception` in `log.py` still writes `str(value)` for its other callers, which are scripts that fail. Those messages come from the scripts, not from requests, so I left it alone, as in the first version.
