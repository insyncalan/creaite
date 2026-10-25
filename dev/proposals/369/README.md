# #369: the live server cleans the saved calendar again (guarded diff)

`live_server-rescrub.diff` (git apply clean on origin/main) changes `system/scripts/live_server.py`, which is on the guarded list:

1. New `calendar_rescrub_job()`: calls `sweep.rescrub_calendar()` (v2.6.8, in `sweep.py`), logs counts only, and never raises (an exception goes to `swallowed("calendar-rescrub", e)`).
2. `backup_timer()` calls it once before its first wait (start-up; it runs in the timer thread, so start-up is not slowed) and on every hourly pass of the daily job.

Why: `session.py start` already cleans the calendar, but the live server's own readers can see an entry an earlier version saved with a value (a password or PIN word with no digit) until the next sweep save. `rescrub_calendar` rewrites the file only if something changed and only if the file was not saved meanwhile.

Test: `dev/tests/test_live_rescrub_369.py` applies the diff to a throwaway vault's copy, never to the checkout. Three mutants.
Not on any chain list.
