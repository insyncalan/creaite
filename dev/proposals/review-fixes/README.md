# Proposal: v2.6 review fixes in guarded files (Jarvis applies on Alan's say)

**This is a proposal, not an edit.** `system/scripts/live_server.py` and `system/scripts/reach.py` are guarded: nothing on this
branch changes them. The two diffs here do, once applied. They are three of the nine `/code-review high` findings on
`origin/v253-release` (052100ea); the other six are plain edits on the same branch (`v26-review-fixes`).

## Apply, check, undo

From the repo root, on `v26-review-fixes`:

```
git apply --check dev/proposals/review-fixes/live_server.diff dev/proposals/review-fixes/reach.diff
git apply dev/proposals/review-fixes/live_server.diff dev/proposals/review-fixes/reach.diff
```

`git apply --check` is clean for both, and `git apply -R --check` is clean once applied. Undo: `git apply -R` with the same files.
Verify (one at a time):

```
python3 dev/tests/test_review_fixes_guarded.py    # 4 tests: all skip before the diffs, all OK after
python3 dev/tests/test_intake_process.py          # unchanged
python3 dev/tests/test_calendar_refresh.py        # unchanged (its route now uses the shared check)
python3 dev/tests/test_log_hygiene.py             # unchanged (the log line is the same)
python3 dev/tests/test_reach.py                   # unchanged
python3 dev/tools/check.py                        # check: OK
```

## What Alan will notice

Nothing on the screen.

## The fixes

| Finding | Fix | Test (`dev/tests/test_review_fixes_guarded.py`) |
|---|---|---|
| (4) `POST /api/intake/process` had no same-origin check: another site's page could start a Process run (it still needed the token, but every other run-starting route checks the Origin too) | `live_server.py`: the Calendar refresh check moved into one helper, `foreign_origin(headers)` (a cross-site fetch, or an Origin that isn't http on a loopback host), used by both routes, first, before the request is read | `IntakeProcessOrigin`: a foreign Origin, `null` and `Sec-Fetch-Site: cross-site` get 403; the page's own Origin, no Origin and same-origin reach the request's own checks |
| (6) `reach._RunLock` leaked its file descriptor when `flock` failed (an interrupt, a lock error): `__enter__` raised after `os.open`, so `__exit__` never ran | `reach.py`: the descriptor is closed and the error raised again; `__exit__` closes it once | `RunLockFd`: 40 failed locks leave no descriptor open; a good lock still holds and releases |
| (9) `FAULT_SEEN` was keyed by the thread label alone, so one thread's fault could keep a different fault of another thread with the same name (a name given twice, or cut at 60 characters) out of the log for a minute; the keys also grew without end (every `Thread-N` is a new name) | `live_server.py`: `log_cause(key, e, seen=None)` counts by `seen` when given; a thread's fault is counted by `thread_fault_key` (its name, the fault's class and innermost frame); the logged line is unchanged; at most `FAULT_KEEP` (500) keys are remembered, the oldest going first | `ThreadFaultKey`: two faults of one thread name are both logged, a repeat is not, another thread's is; 550 keys keep 500 |
