"""#250 slice B: may a meeting's transcript be fetched, judged from the SAVED calendar? Plain code; calendar_hold and same_meeting do no
I/O, read no clock and change nothing they are given. The one reader (read_saved_calendar) is a separate function, so it can be pointed at
another reader later.

    held, reason = calendar_hold(event, saved_calendar, live=None, created=None, tz=None)

`event` is the meeting a transcript belongs to: a dict with id, day (YYYY-MM-DD), start, end (HH:MM local, or an ISO stamp; a stamp with
an offset or Z is turned into `tz`, default the machine's) and title; or just an event ID (a string, "calendar:" prefix allowed).
`saved_calendar` is calendar.json as loaded (a dict with "days": {day: [row, ...]}). `live` is the event as the run read it (a dict with
"sensitivity"), or None when the run did not read it. `created` is the transcript's created time, when known.

Fail closed. It holds when the saved calendar is unusable, when no saved row is this meeting, when the match is ambiguous, when the
matched row is anything but exactly "normal", and when a closed (confidential or private) meeting overlaps. The live event can only add a
hold. Reasons are fixed short words (REASONS), never a title, an ID or a time."""
import re
import unicodedata
from datetime import datetime, timedelta

NOT_HELD = "normal"
REASONS = ("confidential", "private", "unknown sensitivity", "no event", "calendar unreadable", "not in saved calendar", "ambiguous",
           "live event not normal", "overlaps closed meeting", "times unreadable", "outside its meeting")
PRIORITY = ("confidential", "private", "unknown sensitivity")           # the order a matched row's reasons are given in
LEAD = timedelta(minutes=15)                                            # a transcript starts a little before its meeting's start
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
_HHMM = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


def title_key(title):
    """A title for matching: NFKC, lower case, [tags] and punctuation removed, spaces squeezed. "" when nothing is left."""
    t = unicodedata.normalize("NFKC", str(title or "")).casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^\w ]|_", " ", re.sub(r"\[[^\]]*\]", "", t))).strip()


def id_text(value):
    """An event ID as text: stripped, "calendar:" removed, "" for anything not a string or number."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return ""
    t = str(value).strip()
    return t[len("calendar:"):].strip() if t.lower().startswith("calendar:") else t


def id_fold(value):
    """The ID with case, percent-encoding, padding and look-alike forms folded: two IDs that fold alike but are not equal are
    ambiguous, never the same."""
    from urllib.parse import unquote
    return unicodedata.normalize("NFKC", unquote(id_text(value))).casefold().rstrip("=")


def _clock(value, day, tz):
    """(day, "HH:MM") of a time given as "HH:MM" (on `day`) or as an ISO stamp, or (None, None)."""
    v = str(value or "").strip() if isinstance(value, str) else ""
    if _HHMM.fullmatch(v):
        return (day if isinstance(day, str) and _DAY.fullmatch(day) else None), v
    try:
        stamp = datetime.fromisoformat(v.replace("Z", "+00:00")) if v else None
    except ValueError:
        stamp = None
    if stamp is None:
        return None, None
    if stamp.tzinfo is not None:
        stamp = stamp.astimezone(tz) if tz is not None else stamp.astimezone()
    return stamp.strftime("%Y-%m-%d"), stamp.strftime("%H:%M")


def _event(event, tz):
    """The event as {id, day, start, end, title} (empty strings for what is missing), or None for nothing usable."""
    if isinstance(event, (str, int)) and not isinstance(event, bool):
        eid = id_text(event)
        return {"id": eid, "day": "", "start": "", "end": "", "title": ""} if eid else None
    if not isinstance(event, dict):
        return None
    out = _event_times(event, tz)
    out.update(id=id_text(event.get("id")), title=title_key(event.get("title")))
    return out if out["id"] or out["title"] or out["start"] else None


def _event_times(event, tz):
    day = event.get("day") if isinstance(event.get("day"), str) and _DAY.fullmatch(event["day"]) else None
    d1, start = _clock(event.get("start"), day, tz)
    d2, end = _clock(event.get("end"), day or d1, tz)
    return {"day": d1 or d2 or day or "", "start": start or "", "end": end or ""}


def same_meeting(a, b):
    """Whether two meetings (dicts with id, day, start, end, title) are one: the IDs are equal, else the day, start and end are equal and
    the normalised titles are equal. Never a title alone and never a time overlap alone; anything missing is "no"."""
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    ia, ib = id_text(a.get("id")), id_text(b.get("id"))
    if ia and ib:
        return ia == ib
    ka, kb = title_key(a.get("title")), title_key(b.get("title"))
    keys = [(str(x.get("day") or ""), str(x.get("start") or ""), str(x.get("end") or "")) for x in (a, b)]
    return bool(ka) and ka == kb and keys[0] == keys[1] and all(keys[0])


def _verdict(row):
    """NOT_HELD or the reason a saved row is closed. Only exactly "normal" (and no private or confidential flag) is open."""
    if not isinstance(row, dict):
        return "unknown sensitivity"
    if row.get("private") not in (False, None, 0):
        return "private"
    if row.get("confidential") not in (False, None, 0):
        return "confidential"
    raw = row.get("sensitivity")
    if not isinstance(raw, str):
        return "unknown sensitivity"
    v = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", raw)).strip().casefold()
    if v == "normal":
        return NOT_HELD
    if v in ("private", "personal"):
        return "private"
    return "confidential" if v else "unknown sensitivity"


def _rows(saved, day):
    """(all (day, row) pairs, whether a row of `day` was not an object) from a saved calendar, or (None, True) when it is unusable."""
    days = saved.get("days") if isinstance(saved, dict) else None
    if not isinstance(days, dict):
        return None, True
    out, bad = [], False
    for d, rows in days.items():
        if not isinstance(rows, list):
            bad = bad or d == day or not day
            continue
        for r in rows:
            if isinstance(r, dict):
                out.append((str(d), r))
            else:
                bad = bad or d == day or not day
    return out, bad


def _as_meeting(day, row):
    return {"id": row.get("id"), "day": day, "start": str(row.get("start") or ""), "end": str(row.get("end") or ""),
            "title": row.get("title")}


def _minutes(hhmm):
    return int(hhmm[:2]) * 60 + int(hhmm[3:]) if isinstance(hhmm, str) and _HHMM.fullmatch(hhmm) else None


def _first(reasons):
    for r in PRIORITY:
        if r in reasons:
            return r
    return reasons[0]


def _touches(r, d, ev_span, made_day, made):
    """Whether one closed row (on day d) holds the meeting: its times can't be read, the event's times overlap it (only when
    `ev_span` is given), or the transcript's created time is in [start - 15 min, end)."""
    s, e = _minutes(r.get("start")), _minutes(r.get("end"))
    if s is None or e is None or e <= s:
        return "times unreadable"
    lo, hi = ev_span
    if lo is not None and hi is not None and lo < e and s < hi:
        return "overlaps closed meeting"
    if made is not None and made_day == d and s - 15 <= _minutes(made) < e:
        return "overlaps closed meeting"
    return None


def _own_window(rows, created, tz):
    """Whether the transcript's created time is inside the matched row's own window [start - 15 min, end) on its day (H1: a closed
    meeting the saved calendar never kept can't be seen, so a transcript the matched meeting can't claim is not opened). A row with no
    times (all day) has no window to test."""
    made_day, made = _clock(created, None, tz)
    if made is None:
        return False
    for d, r in rows:
        if r.get("all_day") is True:
            continue
        s, e = _minutes(r.get("start")), _minutes(r.get("end"))
        if s is None or e is None or e <= s or d != made_day or not (s - 15 <= _minutes(made) < e):
            return False
    return True


def _closed_overlap(ev, rows, created, tz, by_times):
    """A closed row on the event's day that the event's times or the transcript's created time touch, as a reason, or None. Hold-only: it
    never opens anything. A closed row with times that can't be read holds (an all-day row has none by design and holds nothing)."""
    made_day, made = _clock(created, None, tz) if created not in (None, "") else (None, None)
    if created not in (None, "") and made is None:
        return "times unreadable"
    day = ev["day"] or made_day
    span = (_minutes(ev["start"]), _minutes(ev["end"])) if by_times else (None, None)    # an ID match is exact: its times don't decide
    for d, r in rows:
        if d not in (day, made_day) or _verdict(r) == NOT_HELD:         # H2: the transcript's own day counts too (a series lists every day)
            continue
        if r.get("all_day") is True:
            if _verdict(r) != "private":            # M2: closed all-day holds its day, private nothing
                return "overlaps closed meeting"
            continue
        why = _touches(r, d, span if d == day else (None, None), made_day, made)
        if why:
            return why
    return None


def _live_hold(live):
    if live is None:
        return None
    if not isinstance(live, dict):
        return "live event not normal"
    return None if _verdict({"sensitivity": live.get("sensitivity"), "private": live.get("private"),
                             "confidential": live.get("confidential")}) == NOT_HELD else "live event not normal"


def _matched(ev, rows):
    """(verdicts of the distinct matching rows, whether a row's ID only looks like the event's, whether an ID matched exactly,
    the (day, row) pairs matched)."""
    ids = [(d, r) for d, r in rows if ev["id"] and id_text(r.get("id")) == ev["id"]]
    folded = [(d, r) for d, r in rows if ev["id"] and id_text(r.get("id")) != ev["id"] and id_fold(r.get("id")) == id_fold(ev["id"])]
    bare = {**ev, "id": ""}                                  # no ID match: the times and the title decide
    found = ids or [(d, r) for d, r in rows if same_meeting(bare, {**_as_meeting(d, r), "id": ""})]
    distinct = {}
    for d, r in found:
        distinct[(d, id_text(r.get("id")), str(r.get("start")), str(r.get("end")), title_key(r.get("title")), _verdict(r))] = _verdict(r)
    return list(distinct.values()), bool(folded), bool(ids), found


def calendar_hold(event, saved_calendar, live=None, created=None, tz=None):
    """(held, reason) for one meeting. See the module text. Reason is NOT_HELD ("normal") when it is not held."""
    ev = _event(event, tz)
    if ev is None:
        return True, "no event"
    rows, bad = _rows(saved_calendar, ev["day"])
    if rows is None or bad:
        return True, "calendar unreadable"
    verdicts, lookalike, by_id, found = _matched(ev, rows)
    closed = [v for v in verdicts if v != NOT_HELD]
    if closed:
        return True, _first(closed)
    if lookalike or len(verdicts) > 1:
        return True, "ambiguous"
    if not verdicts:
        return True, "not in saved calendar"
    no_time = created in (None, "")
    extra = _closed_overlap(ev, rows, created, tz, not by_id or no_time)    # M1: no created time: the event's own times decide
    if extra:
        return True, extra
    if not no_time and not _own_window(found, created, tz):
        return True, "outside its meeting"
    live_reason = _live_hold(live)
    return (True, live_reason) if live_reason else (False, NOT_HELD)


def read_saved_calendar(path=None):
    """The saved calendar for calendar_hold, or None when it can't be read (calendar_hold then holds). The one place this module reads a
    file; today it is invite_clean.read_calendar, so a reader that cleans rows is used and the gateway can replace it in one line."""
    try:
        import json
        import paths
        with open(path or paths.CALENDAR, encoding="utf-8") as f:     # raw, not invite_clean: it reads no sensitivity as normal (M3)
            return json.load(f)
    except Exception:                                                    # missing, unreadable, corrupt: all the same to the caller
        return None


def hold_for(event, live=None, created=None, tz=None):
    """calendar_hold with the saved calendar read now: the call a caller makes."""
    return calendar_hold(event, read_saved_calendar(), live=live, created=created, tz=tz)
