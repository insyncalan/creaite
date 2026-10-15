"""Dates in plain words for the scripts (BL-147, v2.1.0 P4 BL-338). Standard library only. A library: no command line.

The one parser is the dashboard's system/templates/dashboard/src/core/datewords.js; this is its copy for the scripts, word for
word, and dev/tests/test_minutes_record.py runs both on the same words and checks they agree. Change both together.

parse(text, today, due, mode, weekend) gives YYYY-MM-DD or None. `weekend` holds the weekend's days numbered as JavaScript's
getDay() (Sunday 0), so both copies read the same list. deadline(text, meeting_day) is the minutes' deadline: the words worked
out from the meeting's date (minutes-style.md): "Friday", "next week" (that week's Friday), "next Wednesday", "end of month" (its
last working day), "in 2 weeks", "30-10".
"""
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
MON = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
MONTHS = "january february march april may june july august september sept october november december".split()
DAYNAMES = "sunday monday tuesday wednesday thursday friday saturday tues weds thur thurs".split()
SAT_SUN = (0, 6)
A = re.ASCII


def _day(s):
    """A YYYY-MM-DD string as a date."""
    return date.fromisoformat(s)


def _dow(s):
    """JavaScript's getDay() of a YYYY-MM-DD day (Sunday 0)."""
    return (_day(s).weekday() + 1) % 7


def _shift(today, n, unit):
    """today moved by n days, weeks or months (a month keeps the day, or the month's last day)."""
    d = _day(today)
    if unit == "m":
        y, m = divmod(d.month - 1 + n, 12)
        y, m = d.year + y, m + 1
        last = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)).day
        return date(y, m, min(d.day, last)).isoformat()
    return (d + timedelta(days=n * (7 if unit == "w" else 1))).isoformat()


def _real(y, m, d):
    """YYYY-MM-DD for a real date (a two-digit year is this century), else None."""
    y = y + 2000 if y < 100 else y
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def _month_of(w):
    """1 to 12 for a month's name or its start ("oct", "octo"), else 0."""
    i = MON.index(w[:3]) if w[:3] in MON else -1
    return i + 1 if i >= 0 and (any(n.startswith(w) for n in MONTHS) or len(w) == 3) else 0


def _weekday_of(w):
    """getDay() of a weekday's name or its start ("fri", "thurs"), else -1."""
    return next((i for i, d in enumerate(DAYS) if w.startswith(d) and any(n.startswith(w) for n in DAYNAMES)), -1)


def working_day(day, weekend=SAT_SUN):
    """The nearest working day to `day` (the earlier on a tie)."""
    if _dow(day) not in weekend:
        return day
    for n in range(1, 7):
        back, on = _shift(day, -n, "d"), _shift(day, n, "d")
        if _dow(back) not in weekend:
            return back
        if _dow(on) not in weekend:
            return on
    return day


def _last_working_day(day, weekend):
    """The last working day of the month `day` is in."""
    d = _day(day)
    s = (date(d.year + (d.month == 12), d.month % 12 + 1, 1) - timedelta(days=1)).isoformat()
    for _ in range(7):
        if _dow(s) not in weekend:
            break
        s = _shift(s, -1, "d")
    return s


def _deadline_only(s, today, weekend):
    """The deadline words only: None when the words aren't one of them."""
    dow = _dow(today)
    monday = (1 - dow + 7) % 7 or 7
    if s == "next week":
        return _shift(today, monday + 4, "d")                       # that week's Friday
    if s in ("end of month", "eom"):
        return _last_working_day(today, weekend)
    m = re.fullmatch(r"next ([a-z]{3,9})", s, A)
    w = _weekday_of(m.group(1)) if m else -1
    if w >= 0:
        return _shift(today, monday + (w + 6) % 7, "d")             # in the next week
    return None


def _day_month(s, today, due):
    """A date written with digits or a month's name."""
    def dm(d, m, y):
        """A day and month: the year given, or this one (next year for a due date that would be past)."""
        if y is not None:
            return _real(int(y), int(m), int(d))
        yr = int(today[:4])
        r = _real(yr, int(m), int(d))
        if r and due and r < today:
            r = _real(yr + 1, int(m), int(d))
        return r
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s, A)
    if m:
        return _real(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.fullmatch(r"(\d{1,2})[/\-. ](\d{1,2})(?:[/\-. ](\d{2}|\d{4}))?", s, A)
    if m:
        return dm(m.group(1), m.group(2), m.group(3))
    m = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)? ([a-z]{3,9})(?: (\d{4}))?", s, A)
    if m and _month_of(m.group(2)):
        return dm(m.group(1), _month_of(m.group(2)), m.group(3))
    m = re.fullmatch(r"([a-z]{3,9}) (\d{1,2})(?:st|nd|rd|th)?(?: (\d{4}))?", s, A)
    if m and _month_of(m.group(1)):
        return dm(m.group(2), _month_of(m.group(1)), m.group(3))
    return None


def _named(s, today):
    """today, tomorrow, yesterday, a weekday, next week, end of week or month: None for anything else."""
    dow = _dow(today)
    fixed = {"today": 0, "now": 0, "tomorrow": 1, "tmrw": 1, "tmr": 1, "yesterday": -1}
    if s in fixed:
        return _shift(today, fixed[s], "d")
    m = re.fullmatch(r"(next |this )?([a-z]{3,9})", s, A)
    w = _weekday_of(m.group(2)) if m else -1
    if w >= 0:
        return _shift(today, ((w - dow + 7) % 7 or 7) + (7 if m.group(1) == "next " else 0), "d")
    if s == "next week":
        return _shift(today, (1 - dow + 7) % 7 or 7, "d")           # Monday
    if s in ("end of week", "eow"):
        return _shift(today, (5 - dow + 7) % 7, "d")                # Friday: today on a Friday
    if s in ("end of month", "eom"):
        d = _day(today)
        return (date(d.year + (d.month == 12), d.month % 12 + 1, 1) - timedelta(days=1)).isoformat()
    if s == "end of next week":
        return _shift(today, (5 - dow + 7) % 7 + 7, "d")
    return None


def parse(text, today, due=False, mode="", weekend=SAT_SUN):
    """YYYY-MM-DD for a date in words, or None (core/datewords.js parseWords, word for word)."""
    s = re.sub(r"[.,]$", "", re.sub(r"\s+", " ", str(text or "").strip().lower()))
    if not s:
        return None
    deadline = mode == "deadline"
    if deadline:
        due = True
        s = re.sub(r"^(?:by|on) ", "", s)
        d = _deadline_only(s, today, weekend)
        if d:
            return d
    named = _named(s, today)
    if named:
        return named
    m = re.fullmatch(r"(?:\+|in )?\s*(\d{1,3}) ?(d|days?|w|wks?|weeks?|m|mos?|months?)", s, A) or \
        re.fullmatch(r"\+(\d{1,3})()", s, A)
    if m:
        r = _shift(today, int(m.group(1)), m.group(2)[:1] or "d")
        return working_day(r, weekend) if deadline else r
    return _day_month(s, today, due)


def weekend_days():
    """The weekend's days as getDay() numbers, from settings work.weekend_days (tracker.weekend_days counts Monday 0)."""
    import tracker
    try:
        settings = paths.load_settings()
    except (OSError, ValueError):     # no settings yet: Saturday and Sunday
        settings = {}
    return tuple(sorted((d + 1) % 7 for d in tracker.weekend_days(settings)))


def deadline(text, meeting_day, weekend=None):
    """A minutes deadline in words, worked out from the meeting's date (YYYY-MM-DD): YYYY-MM-DD, or None (Not set)."""
    return parse(text, meeting_day, True, "deadline", weekend_days() if weekend is None else weekend)


def said(day):
    """What a date was understood as: "Friday 16-10-2026"."""
    d = _day(day)
    return f"{d.strftime('%A')} {d:%d-%m-%Y}"
