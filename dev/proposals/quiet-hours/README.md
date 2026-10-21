# #97 step 1: quiet hours for the alert check (guarded file: live_server.py)

**What.** `live_server.diff` is a unified diff against `system/scripts/live_server.py` on `main` (4e564fcf). Apply from the repo root with
`git apply dev/proposals/quiet-hours/live_server.diff` (`git apply --check` passes). Four small hunks, no other guarded file:

1. **`vip_check`**: after the "no one followed" skip, `vip_schedule.paused()` returns `"skipped: quiet hours"` inside quiet time, so no
   `claude -p` call is made and `vip.json`'s `last_check` is not moved.
2. **`vip_check`**: the look-back line calls `vip_schedule.look_back(last_check, last_sweep, now)`. Same result as the line it replaces
   (the last successful check, else the last sweep, else now); it is in plain code now so it is tested in one place.
3. **`vip_timer`**: `wait = vip_schedule.timer_wait(wait)`. Outside quiet time the wait is unchanged. Inside it, the timer wakes when quiet
   time ends (plus 5 seconds), never later than `vip.check_minutes`, so the first check is at 07:00, not up to 30 minutes later, and a
   setting changed during quiet time takes effect at the next tick. It is inside the existing `try`, so a fault still means 30 minutes.
4. **`SAFE_SETTINGS`**: `"vip.quiet_"` joins the Copy diagnostics allow-list (times and switches only).

**Why.** Alan (20-10-2026) wants the alert check's cost halved. The decision is all in `system/scripts/vip_schedule.py` (plain code, not
guarded, no command line, writes nothing): `quiet_now(settings, now)`, `quiet_ends`, `next_due`, `timer_wait`, `look_back`, `paused`.
Settings: `vip.quiet_overnight` (on), `vip.quiet_from` (19:00), `vip.quiet_to` (07:00), `vip.quiet_weekend` (on; uses `work.weekend_days`).
Times are 24-hour HH:MM; a bad value falls back to its default; from equal to to means no overnight pause.

**Nothing is missed.** `last_check` is moved only by a finished check (`sweep.vip_record`), so the first check after quiet time reads
from the last one before it (Friday 18:30 to Monday 07:00, say). Messages are noticed later, never lost.

**Saving.** At 30 minutes: 336 checks a week without quiet time, 120 with it (24 a day on five days): 108 of 168 hours are quiet, about
64% fewer checks.

**Without the diff** the settings, the page and the module all work; the check simply runs as today.

**Tests.** `dev/tests/test_vip_quiet_hours.py`: the pure function over a table of times (weekday boundaries, weekends, windows across
midnight, from equal to to, bad values, each switch off, a clock change), and the `Wiring` class, which applies this diff to a throwaway
vault's own copy of `live_server.py` (never committed) and runs the real `vip_check` with a stand-in claude on a pinned clock: no call in
quiet time, the first call after it reads from the last check, the settings off restore today's behaviour, nothing says VIP.
`dev/tests/test_quiet_hours_page.py`: the two rows in Settings › Essentials › People I follow, their defaults and saves.

**Risk.** Low. The skip is before the lock and the call; a quiet tick writes nothing. The look-back is unchanged. The one behaviour change
is the default: alerts stop overnight and at weekends unless Alan turns the switches off.

**Other tests after the diff.** Every test that runs the real check or the server's timer pins a weekday daytime clock (08-10, 09-10 13:00,
12-10 09:30), so none falls into quiet time; the source-text checks on `vip_check` (one `prompt_last`, one `subprocess.run`) still hold.

## Also for Jarvis

- `creaite-rules.md`, folder map, `system/scripts/` row: add `` `vip_schedule.py` (#97: the alert check's quiet hours, `vip.quiet_*`; when the
  live server's check may run and where it reads back from; plain code, writes nothing) ``.
- `whats-new.md` / help: one line for Settings › Essentials › People I follow, when the release is cut.
