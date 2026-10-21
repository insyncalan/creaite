"""Quiet hours for the alert check (#97 step 1; Alan, 20-10-2026: halve its cost).

The live server checks for messages from the people Alan follows every vip.check_minutes, each check a paid `claude -p` call. This
module decides, in plain code, whether a check may run now:
    vip.quiet_overnight   on by default: no checks from vip.quiet_from (19:00) to vip.quiet_to (07:00), across midnight when
                          from is later than to; from equal to to means no window
    vip.quiet_weekend     on by default: no checks on the weekend days (work.weekend_days, Saturday and Sunday by default), all day
Times are 24-hour HH:MM on the laptop's own clock (sweep.now(): CREAITE_NOW pins it in tests); a value that isn't one falls back
to its default. Quiet time is decided on wall-clock times, so 19:00 is 19:00 either side of a clock change; a wait in seconds is
the real time between two wall-clock times (seconds_between), so it is right across a change too.

Nothing is missed: the first check after quiet time looks back to the last successful check (vip.json's last_check, which only a
finished check moves on; look_back), not to "now minus the interval". Messages sent overnight are noticed at 07:00, not lost.

Plain code, no command line, writes nothing. The live server calls paused() in vip_check and timer_wait() in vip_timer
(dev/proposals/quiet-hours, a guarded change); the Settings page's People I follow card edits the four keys.
"""
import sys
from datetime import datetime, time as dtime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import paths  # noqa: E402,F401  (every script imports paths: doctor's "Scripts take locations from paths.py" check)

DEFAULTS = {"quiet_overnight": True, "quiet_from": "19:00", "quiet_to": "07:00", "quiet_weekend": True}   # = settings-defaults.json
OFF_WORDS = ("off", "false", "no", "0")
ON_WORDS = ("on", "true", "yes", "1")
SKIPPED = "skipped: quiet hours"
WAKE_AFTER = 5                      # seconds past the end of quiet time the timer wakes, so the clock is surely past it


def parse_hhmm(value):
    """Minutes after midnight for a 24-hour "HH:MM" (outer spaces allowed), else None."""
    if not isinstance(value, str):
        return None
    t = value.strip()
    if len(t) != 5 or t[2] != ":" or not (t[:2] + t[3:]).isdigit():
        return None
    h, m = int(t[:2]), int(t[3:])
    return h * 60 + m if h < 24 and m < 60 else None


def _switch(value, default):
    """A switch from settings.json, as a hand edit may write it: a bool, 0 or 1, or on/off words; anything else is the default."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        w = value.strip().lower()
        if w in OFF_WORDS:
            return False
        if w in ON_WORDS:
            return True
    return default


def quiet_settings(settings):
    """{"overnight", "from", "to", "weekend", "weekend_days"} from a settings dict (settings.json as read); from and to in
    minutes after midnight, weekend_days as weekday numbers (Monday 0)."""
    import tracker
    s = settings if isinstance(settings, dict) else {}
    vip = s.get("vip") if isinstance(s.get("vip"), dict) else {}
    start = parse_hhmm(vip.get("quiet_from"))
    end = parse_hhmm(vip.get("quiet_to"))
    return {"overnight": _switch(vip.get("quiet_overnight"), DEFAULTS["quiet_overnight"]),
            "from": parse_hhmm(DEFAULTS["quiet_from"]) if start is None else start,
            "to": parse_hhmm(DEFAULTS["quiet_to"]) if end is None else end,
            "weekend": _switch(vip.get("quiet_weekend"), DEFAULTS["quiet_weekend"]),
            "weekend_days": tracker.weekend_days(s)}


def _quiet(q, now):
    if q["weekend"] and now.weekday() in q["weekend_days"]:
        return True
    if not q["overnight"] or q["from"] == q["to"]:
        return False
    t = now.hour * 60 + now.minute
    if q["from"] < q["to"]:                                   # a window inside one day, such as 01:00 to 05:30
        return q["from"] <= t < q["to"]
    return t >= q["from"] or t < q["to"]                      # across midnight, such as 19:00 to 07:00


def quiet_now(settings, now):
    """True when the alert check must not run at `now` (a naive local datetime)."""
    return _quiet(quiet_settings(settings), now)


def quiet_ends(settings, now):
    """The first local time after `now` that is not quiet, when `now` is quiet; None when it isn't, or when it never ends (every
    day a weekend day). Quiet time can only end at a midnight or at quiet_to, so only those are tried, over the next eight days."""
    q = quiet_settings(settings)
    if not _quiet(q, now):
        return None
    to = dtime(q["to"] // 60, q["to"] % 60)
    tries = sorted(c for d in range(9) for day in [now.date() + timedelta(days=d)]
                   for c in (datetime.combine(day, dtime(0, 0)), datetime.combine(day, to)) if c > now)
    return next((c for c in tries if not _quiet(q, c)), None)


def next_due(settings, now, minutes):
    """When the next check runs after one at `now`, every `minutes`: the usual time, or the end of quiet time when that falls in it."""
    due = now + timedelta(minutes=minutes)
    if not quiet_now(settings, due):
        return due
    return quiet_ends(settings, due) or due


def seconds_between(a, b):
    """Real seconds from local wall-clock time a to b (naive datetimes read as the laptop's local time, clock changes included)."""
    return b.astimezone().timestamp() - a.astimezone().timestamp()


def look_back(last_check, last_sweep, now):
    """Where a check reads from ("YYYY-MM-DD HH:MM"): the last successful check, else the last sweep, else now. After quiet time
    this is the last check before it, so nothing sent while the checks were paused is missed."""
    return last_check or (last_sweep or now).strftime("%Y-%m-%d %H:%M")


def _load():
    try:
        import paths
        return paths.load_settings()
    except (OSError, ValueError, ImportError):
        return {}


def _now():
    import sweep
    return sweep.now()


def paused(settings=None, now=None):
    """SKIPPED when the live server's check must not run now (quiet time), else None."""
    settings = _load() if settings is None else settings
    return SKIPPED if quiet_now(settings, _now() if now is None else now) else None


def timer_wait(wait, settings=None, now=None, interval=None):
    """The check timer's sleep: `wait` (what the server worked out) outside quiet time; inside it, until quiet time ends (plus a
    few seconds), never longer than the usual interval, so a setting changed in quiet time takes effect at the next tick, and
    ignoring the shorter wait for a conversation still being waited for (no check could run sooner anyway)."""
    settings = _load() if settings is None else settings
    now = _now() if now is None else now
    if not quiet_now(settings, now):
        return wait
    if interval is None:
        import sweep
        interval = 60.0 * float(sweep.vip_settings().get("check_minutes") or 30)
    end = quiet_ends(settings, now)
    if end is None:
        return interval
    return max(1.0, min(interval, seconds_between(now, end) + WAKE_AFTER))


WEEK = datetime(2026, 10, 5)        # a Monday; wall-clock minutes only, so the week chosen doesn't matter


def weekly_quiet_hours(settings):
    """Hours of a week in which the check doesn't run (108 of 168 by default)."""
    q = quiet_settings(settings)
    return sum(_quiet(q, WEEK + timedelta(minutes=m)) for m in range(7 * 24 * 60)) / 60


def weekly_checks(settings, minutes):
    """How many checks a week at every `minutes`, from Monday 00:00 (336 at 30 minutes with no quiet time; 120 by default)."""
    q, step = quiet_settings(settings), max(1, int(minutes))
    return sum(not _quiet(q, WEEK + timedelta(minutes=m)) for m in range(0, 7 * 24 * 60, step))
