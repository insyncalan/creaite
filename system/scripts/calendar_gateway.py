"""#375 E1, slice S3: the one read path for the saved calendar (system/staging/calendar.json).

    read(purpose, path=None) -> {"fetched", "to", "days"}   same shape as invite_clean.read_calendar returns today, rows limited to
                                                          what `purpose` may see (a reader switches by changing one call)
    view(ev, purpose)        -> dict                       one event row limited to the purpose (new dicts, never the caller's)
    purpose_names()          -> tuple of the closed set of purposes (an unknown one raises UnknownPurpose, a LookupError: the readers
                                                          catch OSError and ValueError, so a typo is not swallowed as "no calendar")
    clean_row(row), stamp_row(row), stamp_rows(days), stamp_calendar(cal), lock()   for the writers (sweep), later

THE STAMP. A row written by today's sweep carries "clean": CLEAN (an int) and "clean_v": fingerprint() (a hash of the filter's two
source files). A row
with no stamp, a lower one, another filter version, or a stamp but a wrong shape (_well_formed) is filtered IN MEMORY when the file is
read (once per file version, the cache) and served filtered; only a trusted row is served as stored. A bare confidential flag is
turned into "sensitivity" before a trusted row is trimmed (keep_row). Re-filtering every row on every cache fill was measured and
rejected: the body filter costs about 8 ms a row, so a 3,000-row calendar would take tens of seconds. read() never writes: only the
sweep's save and the start-up
rescrub write, and they stamp (clean_row / stamp_rows). Nothing unfiltered is ever served: when the filter cannot be loaded, the body
of an unstamped row is dropped (fails closed).

THE FILTER. FILTER is a module-level hook, callable(text) -> text. None means invite_filter.filter_text_with_scrub (option c),
imported lazily on first use (called with html=None: HTML detected). Tests inject a stand-in.
SHORT is the same kind of hook for an unstamped row's short fields (title, place, organiser, names):
callable(row) -> row without a body; None means invite_clean.clean_row, imported lazily (the short
fields keep the label rule, plan section 1 rule 7); without it the row is cut to a bare "Meeting".

THE CACHE. Per path, keyed (mtime_ns, size, inode, CLEAN, id(FILTER), id(SHORT)) and checked again after the file is read: a file that
changed meanwhile is not cached. What is cached is the filtered calendar of that exact content; every call builds fresh views.

FIELDS PER PURPOSE (a field not listed is absent; "body" is whole lines only, in order, never above its length). A private or
confidential event gets only HEAD (title "Busy" when private) whatever the purpose, as invite_clean.sensitivity fails closed.

    HEAD  = id, start, end, all_day, title, private, sensitivity
    DAY   = HEAD + where, teams, organiser, recurrence, attendees (name, type, response only)

    purpose      fields                                                         body
    meta         id only (rows exist so days and meetings can be counted)       none
    day          DAY                                                            none
    intake       DAY, attendees with email (Intake's project match)             none
    prep_rank    DAY + attachments                                              1,500
    prep_panel   DAY (attendees with email) + attachments + organiser_email     1,500
    prep_page    DAY + attachments                                              1,500
    agenda       DAY (attendees with email: the follow-up's To list)           1,500 (the draft shows 400 of it)
    shape        HEAD                                                           600

(attendees are in DAY by name; a reader that needs an address uses intake, prep_panel or agenda. A private or confidential event
gets HEAD only, so no attendee or address.)
"""
import contextlib
import json
import os
import re
import time
import unicodedata
from pathlib import Path

import paths

CLEAN = 1                  # the stamp: bump to make every older row filtered again on read
BODY_MAX = 20000           # a saved body is cut here before the filter, as invite_clean does
BODY_CAP = 1500            # plan: the cap on a stored body, whole lines
FILTER = None              # hook: callable(text) -> text; None = invite_filter.filter_text (lazy)
SHORT = None               # hook: callable(row) -> row without a body; None = invite_clean.clean_row (lazy)
LOCK = paths.STAGING / "calendar.lock"

HEAD = ("id", "start", "end", "all_day", "title", "private", "sensitivity")
DAY = HEAD + ("where", "teams", "organiser", "recurrence", "attendees")
# "attendees_addr" is the attendees field with each person's address too (output key "attendees"). Only the readers that match or
# write to people need it: Intake's project match (email domains, #328), the Prep entry's match, the follow-up email's recipients.
DAY_ADDR = tuple("attendees_addr" if f == "attendees" else f for f in DAY)
# purpose -> (fields, body length or 0)
PURPOSES = {
    "meta": (("id",), 0),
    "day": (DAY, 0),
    "prep_rank": (DAY + ("attachments",), BODY_CAP),
    "intake": (DAY_ADDR, 0),
    "prep_panel": (DAY_ADDR + ("attachments", "organiser_email"), BODY_CAP),
    "prep_page": (DAY + ("attachments",), BODY_CAP),
    "agenda": (DAY_ADDR, BODY_CAP),
    "shape": (HEAD, 600),
}
# exactly what sweep.calendar_row writes (invite_clean.ROW_KEYS); anything else in a saved row is dropped
ROW_KEYS = ("id", "start", "end", "all_day", "title", "where", "teams", "private", "organiser", "sensitivity", "organiser_email",
            "recurrence", "body", "attendees", "attachments")
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CACHE = {}


class UnknownPurpose(LookupError):
    """A purpose that is not in PURPOSES."""


def purpose_names():
    """The closed set of purposes."""
    return tuple(PURPOSES)


def _spec(purpose):
    try:
        return PURPOSES[purpose]
    except (KeyError, TypeError):
        raise UnknownPurpose(f"unknown calendar purpose {purpose!r}; one of {', '.join(PURPOSES)}") from None


# ---- the filter and the short-field hooks -------------------------------------------------------------------------------------

def _filter_fn():
    """The body filter, or None when it cannot be had (then no body is served)."""
    if FILTER is not None:
        return FILTER
    try:
        import invite_filter
        fn = invite_filter.filter_text_with_scrub
    except (ImportError, AttributeError):
        return None
    return lambda text: fn(text, html=None)


def filter_body(body):
    """A body (text or HTML) through the filter, whole lines, at most BODY_CAP characters; "" for anything else or when the filter fails."""
    if not isinstance(body, str) or not body.strip():
        return ""
    fn = _filter_fn()
    if fn is None:
        return ""
    try:
        out = fn(body[:BODY_MAX])
    except Exception:  # noqa: BLE001  (a filter fault must never serve the raw body)
        return ""
    return _cap(out if isinstance(out, str) else "", BODY_CAP)


def _cap(text, limit):
    """Whole lines, in order, until `limit` characters; a line that would cross is dropped and the rest too. Never edits a line."""
    if not isinstance(text, str) or limit <= 0:
        return ""
    out, size = [], 0
    for line in text.split("\n"):
        size += len(line) + (1 if out else 0)
        if size > limit:
            break
        out.append(line)
    return "\n".join(out).strip("\n")


def _short_fields(row):
    """An unstamped row's short fields cleaned (no body)."""
    fn = SHORT
    if fn is None:
        try:
            import invite_clean
            fn = invite_clean.clean_row
        except ImportError:
            fn = None
    if fn is not None:
        try:
            return {k: v for k, v in fn({**row, "body": ""}).items() if k != "body"}
        except Exception:  # noqa: BLE001  (a faulty cleaner falls through to the bare row below: never the raw one)
            fn = None
    return {"id": str(row.get("id", ""))[:512], "start": str(row.get("start", ""))[:12], "end": str(row.get("end", ""))[:12],
            "title": "Meeting", "private": False, "sensitivity": "confidential"}


# ---- sensitivity (fails closed, as invite_clean.sensitivity) --------------------------------------------------------------------

def _flag(value):
    if isinstance(value, str):
        return unicodedata.normalize("NFKC", value).strip().lower() not in ("", "false", "0", "no", "none", "null", "off")
    return bool(value)


def _sens(ev):
    """"private", "confidential" or "normal"; anything unexpected is confidential."""
    if _flag(ev.get("private")):
        return "private"
    raw = ev.get("sensitivity")
    text = raw if isinstance(raw, str) else ("" if raw is None else str(raw))
    v = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip().lower()
    if v in ("", "normal", "none"):
        return "confidential" if _flag(ev.get("confidential")) else "normal"
    return "private" if ("private" in v or "personal" in v) else "confidential"


# ---- rows: clean (writer side) and normalise (reader side) --------------------------------------------------------------------

_FP = []                # the fingerprint, worked out once per process (a one-item list: empty means not yet)


def fingerprint():
    """What a stamp must say besides CLEAN: a hash (sha256 of the bytes, 16 hex digits) of the two files that decide what a saved row may
    keep, invite_filter.py and invite_clean.py. A row stamped by an earlier version of either is filtered again on its next read, and the
    rescrub writes it back stamped, so a fix to either file reaches saved rows without anyone bumping a number (saved calendars are
    cleaned again at the first start-up after an update). Worked out once per process. None when either file cannot be read: then no row
    is trusted as stored (fails closed)."""
    if _FP:
        return _FP[0]
    try:
        import hashlib
        import invite_clean
        import invite_filter
        h = hashlib.sha256()
        for mod in (invite_filter, invite_clean):
            h.update(Path(mod.__file__).read_bytes())
        fp = h.hexdigest()[:16]
    except (ImportError, AttributeError, TypeError, OSError):
        return None             # not remembered: tried again next time
    _FP.append(fp)
    return fp


def file_stamp():
    """The top-level stamp of a saved calendar: {"clean": CLEAN, "clean_v": fingerprint()} (no clean_v when the files cannot be read)."""
    fp = fingerprint()
    return {"clean": CLEAN, **({"clean_v": fp} if fp is not None else {})}


def is_stamped(row):
    """Whether a row carries the current stamp: "clean" >= CLEAN and "clean_v" equal to fingerprint(). A bare "clean": 1 (or any number)
    is not enough, so a stamp added by hand, an import or an older filter does not skip the filter."""
    if not isinstance(row, dict):
        return False
    c, fp = row.get("clean"), fingerprint()
    return fp is not None and row.get("clean_v") == fp and isinstance(c, int) and not isinstance(c, bool) and c >= CLEAN


def trusted(row):
    """A stamped row of the shape the sweep writes: the only kind that is served or kept as stored."""
    return is_stamped(row) and _well_formed(row)


def keep_row(row):
    """A trusted row as it is kept: ROW_KEYS and the stamp only, the body cut to BODY_CAP, and its sensitivity worked out BEFORE the
    trim (a bare "confidential": true is not a ROW_KEY, so it must be turned into "sensitivity" first). A private or confidential row
    keeps no body."""
    sens = _sens(row)
    out = {k: row[k] for k in ROW_KEYS if k in row}
    out["clean"], out["clean_v"] = CLEAN, row.get("clean_v")
    if sens != "normal":
        out["sensitivity"], out["private"] = sens, sens == "private"
        out.pop("body", None)
    elif "body" in out:
        out["body"] = _cap(out["body"], BODY_CAP) if isinstance(out["body"], str) else ""
    return out


def clean_row(row):
    """A row as the sweep should save it: short fields cleaned, the body filtered (whole lines, at most BODY_CAP), only ROW_KEYS kept,
    stamped "clean": CLEAN. A confidential or private row keeps no body. Cleaning a cleaned row gives the same row."""
    row = row if isinstance(row, dict) else {}
    out = _short_fields(row)
    if _sens(row) == "normal" and _sens(out) == "normal":
        body = filter_body(row.get("body"))
        if body:
            out["body"] = body
    sens = _sens(out) if _sens(row) == "normal" else _sens(row)
    out = {k: out[k] for k in ROW_KEYS if k in out}
    if sens != "normal":                                 # as keep_row writes it, so a cleaned row is kept as it is (one pass, then stable)
        out["sensitivity"], out["private"] = sens, sens == "private"
    out["clean"] = CLEAN
    fp = fingerprint()
    if fp is not None:
        out["clean_v"] = fp
    return out


def stamp_row(row):
    """A trusted row (current stamp, well formed) is returned as it is kept (keep_row, a copy); any other is cleaned and stamped."""
    return keep_row(row) if trusted(row) else clean_row(row)


def stamp_rows(days):
    """`days` ({day: [row]}) with every row stamped (see stamp_row); keys and order kept, non-list days and non-dict rows dropped."""
    return {d: [stamp_row(r) for r in rows if isinstance(r, dict)] for d, rows in (days if isinstance(days, dict) else {}).items()
            if isinstance(rows, list)}


def stamp_calendar(cal):
    """A calendar dict ready to save: every row stamped and the top level stamped too (a file stamp alone would lie after a merge)."""
    cal = cal if isinstance(cal, dict) else {}
    out = {k: cal[k] for k in ("fetched", "to") if isinstance(cal.get(k), str)}
    out["days"] = stamp_rows(cal.get("days"))
    out["clean"] = CLEAN
    fp = fingerprint()
    if fp is not None:
        out["clean_v"] = fp
    return out


@contextlib.contextmanager
def lock(wait=20.0):
    """The calendar's write lock (flock on system/staging/calendar.lock, the same file the sweep uses). Yields True when held, False when
    it could not be taken within `wait` seconds. Readers never take it."""
    fd, got = None, False
    try:
        import fcntl
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        fresh = not LOCK.exists()
        fd = os.open(str(LOCK), os.O_RDWR | os.O_CREAT, 0o644)
        if fresh:
            try:                            # the lock holds nothing: a new one must not look like a newer input to the live page's cache
                os.utime(str(LOCK), (0, 0))
            except OSError:         # harmless: the page cache just rebuilds once
                pass
        end = time.monotonic() + wait
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                got = True
                break
            except OSError:
                if time.monotonic() >= end:
                    break
                time.sleep(0.02)
    except (ImportError, OSError):
        got = False
    try:
        yield got
    finally:
        if fd is not None:
            os.close(fd)


_STR_KEYS = ("id", "start", "end", "title", "where", "sensitivity", "organiser_email", "recurrence")
_BOOL_KEYS = ("all_day", "teams", "private")
# "organiser" is True (you organised it), False, or the organiser's name (sweep.organiser_of): a bool or a string


def _well_formed(row):
    """Is a (stamped) row of the shape the sweep writes: text where text is expected, flags that are booleans, lists of the right
    things? A row that is not is re-filtered like an unstamped one (a hand edit or an import can add the stamp, finding 12)."""
    checks = [(_STR_KEYS + ("body",), lambda v: isinstance(v, str)), (_BOOL_KEYS, lambda v: isinstance(v, bool)),
              (("attendees",), lambda v: isinstance(v, list) and all(isinstance(a, dict) for a in v)),
              (("attachments",), lambda v: isinstance(v, list) and all(isinstance(f, str) for f in v)),
              (("organiser",), lambda v: isinstance(v, (bool, str)))]
    return all(ok(row[k]) for keys, ok in checks for k in keys if k in row)


def _safe_clean(row):
    """clean_row, and when a cleaner faults on a strange row, the row cut to a bare head (never the raw row)."""
    try:
        return clean_row(row)
    except Exception:  # noqa: BLE001
        sens = "private" if _flag(row.get("private")) else "confidential"
        return {"id": str(row.get("id", ""))[:512], "title": "Busy" if sens == "private" else "Meeting",
                "private": sens == "private", "sensitivity": sens, "clean": CLEAN}


def _normal_row(row):
    """A saved row as the cache holds it: a trusted row (current stamp, well formed) as stored, any other filtered in memory."""
    return keep_row(row) if trusted(row) else _safe_clean(row)


def _normal_calendar(cal):
    if not isinstance(cal, dict):
        return {"days": {}}
    days = cal.get("days")
    out = {k: cal[k] for k in ("fetched", "to") if isinstance(cal.get(k), str)}
    out["days"] = {d: [_normal_row(r) for r in rows if isinstance(r, dict)]
                   for d, rows in (days if isinstance(days, dict) else {}).items()
                   if isinstance(d, str) and _DAY.match(d) and isinstance(rows, list)}
    return out


# ---- views ---------------------------------------------------------------------------------------------------------------------

def _people(att, addr=False):
    """Attendees limited to name, type and response, plus email when `addr` (the 2.6.8 read kept the address)."""
    if not isinstance(att, list):
        return []
    keys = ("name", "type", "response") + (("email",) if addr else ())
    return [{k: a[k] for k in keys if isinstance(a.get(k), str)} for a in att if isinstance(a, dict)]


def _typed(k, v):
    """(True, value) when `v` is a legal value for field `k`, else (False, None): a view never carries a wrongly typed field."""
    if k == "id":
        if isinstance(v, bool):
            return False, None
        return (True, v) if isinstance(v, str) else ((True, str(v)) if isinstance(v, int) else (False, None))
    if k in _STR_KEYS:
        return (True, v) if isinstance(v, str) else (False, None)
    if k in _BOOL_KEYS:
        return (True, v) if isinstance(v, bool) else (False, None)
    if k == "organiser":
        return (True, v) if isinstance(v, (bool, str)) else (False, None)
    if k in ("attendees", "attendees_addr"):
        return True, _people(v, k == "attendees_addr")
    if k == "attachments":
        return (True, [f for f in v if isinstance(f, str)]) if isinstance(v, list) else (False, None)
    return False, None


def _limited(ev, fields, sens):
    """The fields of `fields` that `ev` holds, copied; a private or confidential event gets its flags forced."""
    out = {}
    for k in fields:
        src = "attendees" if k == "attendees_addr" else k
        if src in ev:
            ok, v = _typed(k, ev[src])
            if ok:
                out[src] = v
    if sens != "normal":
        if "sensitivity" in fields:
            out["sensitivity"] = sens
        if "private" in fields:
            out["private"] = sens == "private"
        if sens == "private" and "title" in fields:
            out["title"] = "Busy"
    return out


def view(ev, purpose):
    """One event row limited to `purpose` (see the table above). New dicts and lists: the caller may change the result freely."""
    fields, limit = _spec(purpose)
    if not isinstance(ev, dict):
        return {}
    sens = _sens(ev)
    if sens != "normal":
        fields, limit = tuple(f for f in fields if f in HEAD), 0
    out = _limited(ev, fields, sens)
    if limit and isinstance(ev.get("body"), str):
        body = _cap(ev["body"], limit)
        if body:
            out["body"] = body
    return out


def read(purpose, path=None):
    """The saved calendar for `purpose`: {"fetched", "to", "days"} with every row through view(). Unstamped rows are filtered in memory,
    stamped rows are served as stored; the file is never written. Raises OSError (missing) or ValueError (not JSON), as read_calendar."""
    _spec(purpose)
    path = path if path is not None else paths.CALENDAR
    key = str(path)
    st = path.stat()
    sig = (st.st_mtime_ns, st.st_size, st.st_ino, CLEAN, id(FILTER), id(SHORT), fingerprint())
    hit = _CACHE.get(key)
    if hit and hit[0] == sig:
        cal = hit[1]
    else:
        try:
            cal = _normal_calendar(json.loads(path.read_text(encoding="utf-8")))
        except RecursionError:
            raise ValueError("calendar file is nested too deeply") from None
        st2 = path.stat()
        if (st2.st_mtime_ns, st2.st_size, st2.st_ino, CLEAN, id(FILTER), id(SHORT), fingerprint()) == sig:
            _CACHE[key] = (sig, cal)
    out = {k: cal[k] for k in ("fetched", "to") if k in cal}
    out["days"] = {d: [view(r, purpose) for r in rows] for d, rows in cal["days"].items()}
    return out


def read_raw(path=None):
    """The saved calendar exactly as stored (json.loads of the file), for the WRITERS only (the sweep's held-day merge and the rescrub),
    which must see the stamps and the unfiltered rows they are about to stamp. Never serve this to a reader: use read(purpose).
    Raises OSError or ValueError as the plain read did."""
    return json.loads((path if path is not None else paths.CALENDAR).read_text(encoding="utf-8"))


def clear_cache():
    """Forget every cached calendar (tests)."""
    _CACHE.clear()
