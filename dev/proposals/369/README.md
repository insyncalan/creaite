# #369: the live server cleans the saved calendar again (guarded diff)

`live_server-rescrub.diff` (git apply clean on origin/main) changes `system/scripts/live_server.py`, which is on the guarded list:

1. New `calendar_rescrub_job()`: returns at once in the development repository (`.creaite-dev`, so the sample calendar is never rewritten); otherwise calls `sweep.rescrub_calendar()` (v2.6.8, in `sweep.py`), logs counts only, and never raises (an exception goes to `swallowed("calendar-rescrub", e)`).
2. `backup_timer()` calls it once before its first wait (start-up; it runs in the timer thread, so start-up is not slowed) and on every hourly pass of the daily job.

Why: `session.py start` already cleans the calendar, but the live server's own readers can see an entry an earlier version saved with a value (a password or PIN word with no digit) until the next sweep save. `rescrub_calendar` rewrites the file only if something changed, and does it under the calendar lock (`sweep.calendar_lock`) that a sweep's own save also takes, so neither loses the other's write.

Test: `dev/tests/test_live_rescrub_369.py` applies the diff to a throwaway vault's copy, never to the checkout. Four mutants, including the development-repository guard (the marker present: the calendar stays byte for byte).
Not on any chain list.

## v2 (live_server-rescrub-v2.diff)

`live_server-rescrub.diff` (sha256 6cdba005...) stays as it was. The review found that its job ran outside the server's job lock (`LOCK`), where a restore could overlap it. `live_server-rescrub-v2.diff` makes `calendar_rescrub_job()` take `LOCK` without waiting and skip until the next hourly pass when it is held. It applies cleanly on origin/main, and `test_live_rescrub_369.py` uses it (and also works when either diff is already applied: it takes the applied diff off before it tries the changed copies).

## v3 (live_server-rescrub-v3.diff): show Alan this one

v1 (6cdba005...) and v2 (ecb0f097...) stay as they were. v3 fixes the two notes on v2: the job no longer holds the server's job lock (`LOCK`) while it cleans (it only checks that the lock is free, so a restore in progress is not overlapped; the calendar's own file lock, `sweep.calendar_lock`, guards the file against a sweep's save), and a skipped job is tried again after five minutes (`CALENDAR_RETRY`, one daemon timer) instead of after the hour, so an early daily zip does not hold the raw file. It applies cleanly on origin/main; `test_live_rescrub_369.py` uses it and takes any applied diff off before it tries the changed copies.

## v4 (live_server-rescrub-v4.diff): show Alan this one instead of v3

v3 retried only once: `calendar_rescrub_retry` returns when the timer is alive, and when it is called from the timer's own callback that timer is alive. v4 adds `and timer is not threading.current_thread()`. Applies cleanly on origin/main (`git apply --check`); `test_live_rescrub_369.py` uses it, with a held-lock test of several retries (0.3 s delay, lock held 2 s) and a mutant that fails if only one retry happens.
