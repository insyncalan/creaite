# macOS UI (#152): the Stop race in `live_server.py` (guarded; Jarvis applies)

`test_ask_queue.AskQueue.test_stop_clears_the_queue_and_says_so` fails on the macOS runner (also alone, run 39048796680) and can fail on any OS under load. It is a real race in the product, not the test.

**Cause.** `ask_stop` builds `{"deferred": run.request_stop(), "cleared": queue_clear()}`. Python evaluates `request_stop()` first. It ends the child process and waits; meanwhile the run's reader thread reaches `_done()`, which calls `queue_after(run)`. Because `run.stop` is set, `queue_after` empties the queue itself. By the time `queue_clear()` runs it finds nothing and returns 0, so the page never says "1 queued message was removed". The queue is still cleared; only the count Alan is told is wrong.

**Fix (two lines, `ask-stop.diff`).** Count and clear the queue first (`cleared = queue_clear()`), then call `run.request_stop()`. If the run happens to end by itself in between, `queue_after` finds an empty queue and starts nothing, so nothing new can start. `git apply dev/proposals/macos-ui-152/ask-stop.diff` applies cleanly to `origin/main` dcd8a7b6.

**Proof so far.** The mechanism (clear after `queue_after` gives 0, clear before gives 1) and the symptom (delaying the handler's return by 0.4 s fails the test with the CI message) were shown in the first #152 round. This diff has not been run end to end, because the guarded file was not edited. Once applied, run `dev/tests/test_ask_queue.py` five times as the stress gate says.

No test change is needed: the test already asserts the right behaviour.
