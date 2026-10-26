"""Meeting transcripts from Microsoft 365 (BL-42 phase 3): everything that needs no connection to Microsoft 365.

The route to a transcript is three calls (dev/reference/spike-transcripts-2026-10-08.md), made by a Claude Code run:
  1. outlook_calendar_search finds the event;
  2. read_resource on calendar:///events/<id> gives onlineMeeting.joinUrl and meetingTranscriptUrl;
  3. read_resource on that meeting-transcript:/// URL, exactly as returned (it carries the occurrence's start and end),
     gives transcripts[].content as WebVTT.
SharePoint and OneDrive search are not a fallback. The chat is read from teams:///chats/<thread id>/messages.

This module classifies what those calls returned, keeps the statuses (system/staging/transcripts.json: never a body, a
passcode, a PIN or transcript text), and tidies and writes the files. A script writes them, from the run's own tool results:
Claude never re-types a transcript.

Commands (the daily sweep, cx-sweep, uses them through sweep.py):
  todo                    the meetings in the Calendar import window still to look up, as JSON; meetings that aren't
                          online are recorded as "No transcript" at once
  record <facts.json>     classify what the sweep read for each meeting and keep the statuses
  show                    the statuses kept so far
Set CREAITE_NOW="YYYY-MM-DD HH:MM" to fix the clock (tests).
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import calendar_gateway  # noqa: E402  (#375 E1: the one read path for the saved calendar)
try:
    import log as debuglog  # BL-102: the debug log (not `log`: some scripts have a function of that name); optional
except ImportError:
    class debuglog:  # the helper is missing: every call does nothing and the script runs as before
        info = debug = warn = error = exception = staticmethod(lambda *a, **k: None)
        rule = staticmethod(lambda text, *a: "")
        main = staticmethod(lambda script, fn, *a: fn(*a))

STATUSES = {"available": "Transcript available", "not_transcribed": "Not transcribed", "none": "No transcript",
            "no_access": "No access"}
M365 = "mcp__claude_ai_Microsoft_365__"
KEEP = ("status", "uri", "start", "end", "count", "checked", "thread")     # the only fields ever stored


def now():
    """The time now to the minute, or CREAITE_NOW in tests."""
    fixed = os.environ.get("CREAITE_NOW")
    return datetime.strptime(fixed, "%Y-%m-%d %H:%M") if fixed else datetime.now().replace(second=0, microsecond=0)


# ── what is kept ──
def load_state():
    """The transcript statuses kept so far (system/staging/transcripts.json), {'checked': {}} if none."""
    try:
        data = json.loads(paths.TRANSCRIPTS.read_text(encoding="utf-8"))
        return data if isinstance(data.get("checked"), dict) else {"checked": {}}
    except (OSError, ValueError, AttributeError):
        return {"checked": {}}


def save_state(state):
    """Write the transcript statuses to system/staging/transcripts.json, atomically; never any text (BL-42)."""
    paths.TRANSCRIPTS.parent.mkdir(parents=True, exist_ok=True)
    tmp = paths.TRANSCRIPTS.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(paths.TRANSCRIPTS)


def keep(entry_id, record):
    """Store one meeting's status, only the fields in KEEP (nothing else can reach the file)."""
    if not str(entry_id).strip() or record.get("status") not in STATUSES:
        return False
    state = load_state()
    state["checked"][str(entry_id)] = {k: record[k] for k in KEEP if record.get(k) not in (None, "")}
    state["version"] = 1
    save_state(state)
    return True


# ── reading what Microsoft 365 returned ──
def result_text(content):
    """A tool result's text: a string, or a list of {type: text, text}."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return ""


SPOOL = re.compile(r"(?:saved|written|stored)\s+(?:in|to|at)?:?\s*(?:file\s*)?:?\s*[\"'`]?((?:/|~)[^\s\"'`<>]+)", re.I)


def spool_roots():
    """Where Claude Code spools a result that is too big to return inline (tests add their own folder)."""
    roots = [Path.home() / ".claude"]
    extra = os.environ.get("CREAITE_TOOL_RESULTS")
    if extra:
        roots.append(Path(extra))
    return roots


def read_spooled(text):
    """If a tool result says it was saved to a file, that file's text (only from Claude Code's own folders); else None."""
    m = SPOOL.search(text or "")
    if not m:
        return None
    for cand in (m.group(1), m.group(1).rstrip(".,;:)")):
        try:
            full = Path(cand).expanduser().resolve()
            if full.is_file() and any(root.resolve() in full.parents for root in spool_roots()):
                raw = full.read_text(encoding="utf-8")
                if raw.lstrip().startswith("[") and "\"type\"" in raw[:200]:       # a list of text blocks, as the tool returned it
                    try:
                        return result_text(json.loads(raw))
                    except ValueError:  # BL-228: not JSON after all: the file is read as plain text below
                        pass
                return raw
        except (OSError, ValueError):
            continue
    return None


def as_json(text):
    """The JSON object in a tool result: inline, or a list of text blocks holding it, or spooled to a file."""
    spooled = read_spooled(text) if text and not text.lstrip().startswith(("{", "[")) else None
    for t in (spooled, text):
        if not t:
            continue
        try:
            data = json.loads(t)
        except ValueError:
            continue
        if isinstance(data, list) and data and all(isinstance(p, dict) and p.get("type") == "text" for p in data):
            try:
                return json.loads("".join(p.get("text", "") for p in data))
            except ValueError:
                return None
        return data
    return None


def error_kind(text):
    """permission, notfound or other, for a tool result that is an error."""
    t = (text or "").lower()
    if re.search(r"403|forbidden|permission|access denied|not allowed|unauthori[sz]ed|insufficient", t):
        return "permission"
    if re.search(r"404|not ?found|doesn.t exist|does not exist|no such", t):
        return "notfound"
    return "other"


def thread_id(join_url):
    """19:meeting_…@thread.v2 inside a Teams join URL (also the meeting chat's ID)."""
    m = re.search(r"(19(?::|%3a)meeting_[A-Za-z0-9_\-]+(?:@|%40)thread\.v2)", join_url or "", re.I)
    return unquote(m.group(1)) if m else None


def uri_window(uri):
    """(start, end) from a meeting-transcript URL's query, ISO text or None."""
    q = parse_qs(urlsplit(uri or "").query)
    return (q.get("start") or [None])[0], (q.get("end") or [None])[0]


def names(people):
    """The distinct display names in a list of people, whether given as names or Microsoft 365 records."""
    out = []
    for p in people or []:
        n = p.get("name") if isinstance(p, dict) else p
        if isinstance(p, dict) and not n:
            n = (p.get("emailAddress") or {}).get("name")
        if n and str(n).strip() and str(n).strip() not in out:
            out.append(str(n).strip())
    return out


def event_facts(event):
    """What a calendar event (read_resource on calendar:///events/<id>) tells us. Never the body, passcode or PIN."""
    if not isinstance(event, dict):
        return {}
    online = event.get("onlineMeeting") if isinstance(event.get("onlineMeeting"), dict) else {}
    org = event.get("organizer") or {}
    org = (org.get("emailAddress") or org) if isinstance(org, dict) else {}
    return {"id": event.get("id"), "title": event.get("subject") or event.get("title"),
            "join_url": online.get("joinUrl"), "uri": event.get("meetingTranscriptUrl"),
            "organiser_me": event.get("isOrganizer"), "organiser": org.get("name") if isinstance(org, dict) else None,
            "attendees": names(event.get("attendees")), "cancelled": bool(event.get("isCancelled")),
            "start": ((event.get("start") or {}).get("dateTime") if isinstance(event.get("start"), dict) else None),
            "end": ((event.get("end") or {}).get("dateTime") if isinstance(event.get("end"), dict) else None)}


def transcripts_in(data):
    """The transcripts a meeting-transcript read returned: [{id, created, end, content}], or None if it isn't that shape."""
    if not isinstance(data, dict) or not isinstance(data.get("transcripts"), list):
        return None
    return [{"id": t.get("id"), "created": t.get("createdDateTime"), "end": t.get("endDateTime"), "content": t.get("content") or ""}
            for t in data["transcripts"] if isinstance(t, dict)]


def classify(*, online, uri, count, error, past):
    """The status of one meeting, or None when it can't be told yet (a future meeting, a dropped connection).
    available: at least one transcript for the occurrence. not_transcribed: an online meeting in the past, with a transcript URL
    and an empty list. none: no online meeting, or no transcript URL. no_access: a permission or not-found error for an online
    meeting in the past."""
    if not online or not uri:
        return "none" if (not online or past) else None
    if not past:
        return None
    if error in ("permission", "notfound"):
        return "no_access"
    if error:
        return None
    if count is None:
        return None
    return "available" if count >= 1 else "not_transcribed"


# ── the meetings still to look up (the sweep) ──
def calendar_rows():
    """The timed meetings in system/staging/calendar.json, each with its day."""
    try:
        cal = calendar_gateway.read("day")
    except (OSError, ValueError):
        return []
    out = []
    for day, events in (cal.get("days") or {}).items():
        for ev in events if isinstance(events, list) else []:
            if ev.get("id") and not ev.get("all_day"):
                out.append({**ev, "day": day})
    return out


def ended(row, at=None):
    """Whether a calendar meeting had ended by `at` (default now)."""
    at = at or now()
    try:
        return datetime.strptime(f"{row['day']} {row.get('end') or '23:59'}", "%Y-%m-%d %H:%M") <= at
    except ValueError:
        return False


def todo(at=None):
    """Meetings in the Calendar import window that are new, or still 'Not transcribed' or unchecked: the sweep looks them up.
    Meetings that aren't online are recorded at once as 'No transcript'. Cleared, private and processed ones are left alone."""
    import build_dashboard
    import minutes
    at = at or now()
    start = build_dashboard.meetings_start(paths.load_settings(), at.date()).isoformat()
    state, cleared = load_state()["checked"], {e["key"] for e in build_dashboard.cleared_load(today=at.date())}
    look, auto = [], []
    for row in calendar_rows():
        eid = str(row["id"])
        if not (start <= row["day"] <= at.date().isoformat()) or row.get("private") or eid in cleared:
            continue
        if minutes.processed_on(f"calendar:{eid}") or not ended(row, at):
            continue
        if not row.get("teams"):
            if (state.get(eid) or {}).get("status") != "none":
                keep(eid, {"status": "none", "checked": at.strftime("%Y-%m-%d %H:%M")})
                auto.append(eid)
            continue
        if (state.get(eid) or {}).get("status") in (None, "not_transcribed"):
            look.append({"id": eid, "title": row.get("title"), "day": row["day"], "start": row.get("start"), "end": row.get("end")})
    return {"look_up": look, "recorded_without_lookup": auto}


FACT_KEYS = ("id", "online", "uri", "count", "error", "start", "end", "thread")      # the only keys a fact may carry
FACT_ERRORS = (None, "permission", "notfound", "other")
URI_MAX, THREAD_MAX, ID_MAX, STAMP_MAX = 2048, 512, 512, 40
KEYED = re.compile(r"[?&;](pwd|passcode|pass|password|pin|tk|token)=", re.I)


def _text_field(v, most, spaces=False):
    """True when v is None, or a string of at most `most` characters with no control character (and no space unless
    `spaces`)."""
    if v is None:
        return True
    if not isinstance(v, str) or len(v) > most or re.search(r"[\x00-\x1f\x7f]", v):
        return False
    return spaces or not re.search(r"\s", v)


STAMP = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,9})?)?(?:Z|[+-]\d{2}:?\d{2})?)?|\d{2}:\d{2}")


def _stamp(v):
    """True when v is None or a date or time as the sweep writes it (v2.6 review): ISO from the transcript URL or the event
    ("2026-10-15T08:00:00Z", "…T08:00:00.0000000"), "YYYY-MM-DD HH:MM" with a space, or "HH:MM"; never other text."""
    return v is None or (_text_field(v, STAMP_MAX, spaces=True) and bool(STAMP.fullmatch(v)))


def _shape_problem(f):
    """Why a fact's shape is wrong (not an object, another field, no ID), or None."""
    if not isinstance(f, dict):
        return "not an object"
    extra = sorted(str(k) for k in f if k not in FACT_KEYS)
    if extra:
        return "fields not allowed: " + ", ".join(extra)[:120]
    eid = f.get("id")
    if not isinstance(eid, str) or not eid.strip() or not _text_field(eid, ID_MAX):
        return "no event ID"
    return None


def _link_problem(f):
    """Why a fact's uri or thread isn't a short link or ID (too long, a space, a key in it), or None."""
    if not _text_field(f.get("uri"), URI_MAX) or KEYED.search(f.get("uri") or ""):
        return "the uri isn't a short link"
    if not _text_field(f.get("thread"), THREAD_MAX) or KEYED.search(f.get("thread") or ""):
        return "the thread isn't a short ID"
    return None


def _value_problem(f):
    """Why a fact's online, count, error, start or end has the wrong type or value, or None."""
    if not isinstance(f.get("online", False), bool):
        return "online isn't true or false"
    c = f.get("count")
    if c is not None and (isinstance(c, bool) or not isinstance(c, int) or not 0 <= c <= 1000):
        return "count isn't a whole number"
    if f.get("error") not in FACT_ERRORS:
        return "error isn't one of permission, notfound or other"
    if not (_stamp(f.get("start")) and _stamp(f.get("end"))):
        return "start or end isn't a short time"
    return None


def fact_problem(f):
    """Why one fact can't be recorded, or None (#265 review L5): a JSON object of FACT_KEYS only (never a body, a passcode, a
    PIN or any text), an ID, `online` true or false, a uri and a thread as short strings with no spaces and no key in them,
    `count` a whole number or null, `error` one of FACT_ERRORS, `start` and `end` dates or times (_stamp) or null."""
    return _shape_problem(f) or _link_problem(f) or _value_problem(f)


def _refuse(f, n, why, refused):
    """Note a refused fact: in the debug log (its place and the reason's kind, never a value) and in `refused` (its ID when it
    has a usable one, else its place in the list)."""
    eid = f.get("id") if isinstance(f, dict) else None
    if refused is not None:
        refused.append(eid if isinstance(eid, str) and eid.strip() and _text_field(eid, 80) else f"#{n + 1}")
    debuglog.warn("transcripts", f"record: fact {n + 1} refused ({why.split(':')[0]})")


def record(facts_list, at=None, refused=None):
    """Classify what the sweep (or a run) read for each meeting and keep it. facts: {id, online, uri, count, error, start, end,
    thread}. A fact that fact_problem refuses is left out (its ID, when it has a usable one, or its place in the list, goes in
    `refused`). Returns {id: status or None}."""
    at = at or now()
    rows = {str(r["id"]): r for r in calendar_rows()}
    out = {}
    for n, f in enumerate(facts_list if isinstance(facts_list, list) else []):
        why = fact_problem(f)
        if why:
            _refuse(f, n, why, refused)
            continue
        eid = str(f.get("id") or "")
        row = rows.get(eid)
        past = ended(row, at) if row else True
        status = classify(online=bool(f.get("online")), uri=f.get("uri"), count=f.get("count"), error=f.get("error"), past=past)
        out[eid] = status
        if status:
            keep(eid, {"status": status, "uri": f.get("uri"), "start": f.get("start"), "end": f.get("end"), "count": f.get("count"),
                       "thread": f.get("thread"), "checked": at.strftime("%Y-%m-%d %H:%M")})
    tally = {}
    for s in out.values():
        tally[s or "undecided"] = tally.get(s or "undecided", 0) + 1
    debuglog.info("transcripts", f"looked up {len(out)} meeting(s): " + (", ".join(f"{k} {v}" for k, v in sorted(tally.items())) or "none"))
    return out


# ── tidying and writing ──
TIME = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})(?:[.,](\d{1,3}))?$")


def seconds(stamp):
    """A WebVTT timestamp (HH:MM:SS.mmm or MM:SS.mmm) in seconds; 0 if it can't be read."""
    m = TIME.match(stamp.strip())
    if not m:
        return 0.0
    h, mi, s, ms = int(m.group(1) or 0), int(m.group(2)), int(m.group(3)), (m.group(4) or "0").ljust(3, "0")
    return h * 3600 + mi * 60 + s + int(ms) / 1000


def tidy_vtt(content, meta=None):
    """The transcript as a clean WebVTT file: LF line ends, cues in start-time order (Teams lists short back-channel cues after
    the longer ones they overlap), cue IDs dropped, every word and speaker name exactly as given, and a NOTE header from the event
    (title, date, start time, organiser, attendees, event ID). Several transcripts for one meeting are kept in order as parts."""
    meta = meta or {}
    parts = content if isinstance(content, (list, tuple)) else [content]
    out = ["WEBVTT", ""]
    head = []
    for key, label in (("title", "Meeting"), ("day", "Date"), ("start", "Start"), ("organiser", "Organiser"), ("id", "Event ID")):
        if meta.get(key):
            head.append(f"{label}: {one_line(meta[key])}")
    if meta.get("attendees"):
        head.append("Attendees: " + one_line(", ".join(meta["attendees"][:60])))
    if head:
        out += ["NOTE"] + head + [""]
    for n, part in enumerate(parts, 1):
        cues = []
        text = str(part or "").replace("\r\n", "\n").replace("\r", "\n")
        for block in re.split(r"\n{2,}", text.strip("\n")):
            lines = block.split("\n")
            i = next((k for k, ln in enumerate(lines) if "-->" in ln), None)
            if i is None:
                continue
            timing = lines[i].strip()
            cues.append((seconds(timing.split("-->")[0]), timing, [ln for ln in lines[i + 1:] if ln != ""]))
        if len(parts) > 1:
            out += ["NOTE", f"Part {n} of {len(parts)}", ""]
        for _, timing, body in sorted(cues, key=lambda c: c[0]):            # stable: equal starts keep their order
            out += [timing] + body + [""]
    return "\n".join(out).rstrip("\n") + "\n"


def one_line(text):
    """Text on one line, with any WebVTT arrow made harmless."""
    return re.sub(r"\s+", " ", str(text).replace("-->", "->")).strip()


def html_to_text(body):
    """An HTML message body as plain text: line breaks kept, tags and common entities removed."""
    t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", "\n", body or "")
    t = re.sub(r"(?s)<[^>]+>", "", t)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        t = t.replace(a, b)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def when(value):
    """An ISO date-time (UTC if it has no zone) as a timezone-aware datetime, or None."""
    if not value:
        return None
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def sender(msg):
    """A Teams message's sender display name, or None when it is unknown."""
    f = msg.get("from")
    if isinstance(f, dict):
        f = (f.get("user") or {}).get("displayName") or f.get("name") or f.get("displayName") or (f.get("emailAddress") or {}).get("name")
    return f if f and str(f).strip().lower() != "unknown" else None


def message_body(msg):
    """A Teams message's text, as plain text."""
    b = msg.get("body")
    if isinstance(b, dict):
        text = b.get("content") or ""
        return html_to_text(text) if str(b.get("contentType", "")).lower() == "html" or "<" in text else text.strip()
    if isinstance(b, str):
        return html_to_text(b)
    return html_to_text(msg.get("bodyPreview") or "")


def chat_messages(listing):
    """The message records in a Teams chat listing, whatever shape it came in."""
    data = listing
    if isinstance(data, dict):
        data = data.get("messages") or data.get("value") or []
    return [m for m in data if isinstance(m, dict)] if isinstance(data, list) else []


def chat_text(listing, full, window, meta):
    """The meeting chat, only messages sent during the meeting, each with its full body (`full`: {message id: message}), without
    system events or joins and leaves. Times are shown in the local time zone."""
    start, end = (when(window[0]), when(window[1])) if window else (None, None)
    rows = []
    for m in chat_messages(listing):
        if str(m.get("messageType") or "message").lower() != "message" or m.get("eventDetail"):
            continue                                                       # call started or ended, recording, members joined or left
        sent = when(m.get("createdDateTime") or m.get("sentDateTime") or m.get("lastModifiedDateTime"))
        if sent is None or (start and sent < start) or (end and sent > end):
            continue
        body = message_body(full.get(m.get("id")) or m)
        if body:
            rows.append((sent, sender(m) or "Teams (automatic)", body))
    rows.sort(key=lambda r: r[0])
    head = [f"Chat during {one_line(meta.get('title') or 'the meeting')}, {meta.get('day', '')}", f"Event ID: {meta.get('id', '')}", ""]
    lines = []
    for sent, who, body in rows:
        lines.append(f"[{sent.astimezone().strftime('%H:%M')}] {who}: " + body.replace("\n", "\n    "))
    return "\n".join(head + (lines or ["(no messages during the meeting)"])) + "\n", len(rows)


def file_stem(day, title):
    """The file name stem for a meeting, as minutes.py names it: 'YYYY-MM-DD Title'."""
    import minutes
    return minutes.stem(day, title)


def unique(folder, stem, suffix):
    """A free path in `folder` for `stem` + `suffix`, numbered ' (2)', ' (3)'... when taken."""
    p, n = folder / f"{stem}{suffix}", 2
    while p.exists():
        p, n = folder / f"{stem} ({n}){suffix}", n + 1
    return p


def inbox_event_ids():
    """{event ID: file} for the transcripts and chats already in inbox/, read from their header."""
    found = {}
    if paths.INBOX.is_dir():
        for p in sorted(paths.INBOX.iterdir()):
            if p.suffix.lower() in (".vtt", ".txt") and p.is_file():
                eid = file_event_id(p)
                if eid and (eid not in found or p.suffix.lower() == ".vtt"):
                    found[eid] = paths.rel(p)
    return found


def file_event_id(path):
    """The calendar event ID a loaded transcript or chat carries in its header, or None."""
    try:
        with open(paths.resolve(str(path)) if not Path(str(path)).is_absolute() else path, encoding="utf-8", errors="ignore") as f:
            head = f.read(4000)
    except OSError:
        return None
    m = re.search(r"^Event ID:[ \t]*(\S+)", head, re.M)
    return m.group(1) if m else None


# ── one lookup, as the live server runs it ──
SEARCH_BOUND = 3        # #382: the load prompt's "never more than three searches"; a fourth is logged in the diagnosis
class Job:
    """What one transcript run (a check, or a load) reads. The live server hands it every tool call and result of the run;
    finish() then writes the status and the files. Nothing here comes from what Claude says."""

    def __init__(self, event_id, title="", day="", start="", end="", mode="load", row=None):
        self.id, self.title, self.day, self.start_hm, self.end_hm = str(event_id), title, day, start, end
        self.mode, self.event, self.error, self.transcripts, self.uri_used = mode, None, None, None, None
        self.chat_listing, self.chat_full, self.chat_thread, self.wrong = None, {}, None, False
        self.cancel_note = ""
        self.calls, self.event_read = [], None     # #365: each tool result (name, error, length); how the event read went

    def observe(self, name, tool_input, text, is_error=False):
        """Take one tool call and its result from the run: the event, the transcript or the meeting chat it read.
        Other tools are only counted (#365: names, errors and lengths, never text), so a load that read nothing says so.
        """
        self.calls.append((str(name).split("__")[-1][:40], bool(is_error), len(text or "")))
        if not str(name).endswith("__read_resource"):
            return
        uri = str((tool_input or {}).get("uri") or "")
        if uri.startswith("calendar:///events/"):
            self.take_event(text, is_error)
        elif uri.startswith("meeting-transcript:///"):
            self.uri_used = uri
            if is_error:
                self.error = error_kind(text)
                return
            found = transcripts_in(as_json(text))
            if found is None:
                self.error = error_kind(text) if re.search(r"error|denied|forbidden|not found", text or "", re.I) else "other"
            else:
                self.transcripts, self.error = found, None
        elif uri.startswith("teams:///chats/"):
            rest = uri[len("teams:///chats/"):]
            thread, _, tail = rest.partition("/messages")
            self.chat_thread = unquote(thread)
            if is_error:
                return
            data = as_json(text)
            if tail.startswith("/") and len(tail) > 1:                      # one message, in full
                if isinstance(data, dict):
                    self.chat_full[data.get("id") or unquote(tail[1:])] = data
            elif data is not None:
                self.chat_listing = data

    # the facts the sweep also records
    def take_event(self, text, is_error):
        """The calendar event a read_resource returned: kept if it is this meeting's, `wrong` if it is another's."""
        facts = event_facts(as_json(text) if not is_error else None)
        self.event_read = "error" if is_error else ("unreadable" if not facts else "ok")
        if facts.get("id") == self.id or (facts.get("id") and unquote(facts["id"]) == self.id):
            self.event, self.wrong = facts, False       # M1: a read of the asked event wins over a neighbour read before it
        elif facts and self.event is None:              # ... and a neighbour read after it changes nothing
            self.wrong = True

    def diagnosis(self):
        """Counts only, for the debug log (#365): the tool results the run returned (name, error or ok, length) and how the
        event read went (none, error, unreadable, ok). Never any text."""
        calls = ", ".join(f"{n} {'error' if e else 'ok'} {ln}" for n, e, ln in self.calls[:12]) or "none"
        n = self.searches()
        over = f" (over the bound of {SEARCH_BOUND})" if n > SEARCH_BOUND else ""
        return f"{len(self.calls)} tool results ({calls}); calendar searches: {n}{over}; event read: {self.event_read or 'none'}"

    def searches(self):
        """#382: how many calendar searches the run made (the prompt allows three); the server only counts and logs it."""
        return sum(1 for n, _, _ in self.calls if n == "outlook_calendar_search")

    def no_event(self):
        """The plain line when the event was not read, saying which way it failed; the debug log gets the counts (#365)."""
        debuglog.warn("transcripts", f"{self.mode} {self.id[-8:]}: no calendar event: {self.diagnosis()}")
        if not self.calls:
            return ("Claude Code did not reach Microsoft 365, so it never looked for the meeting's calendar event "
                    "and nothing was loaded. Press Process to try again.")
        if self.event_read is None:
            return ("Claude Code searched Microsoft 365 but never opened the meeting's calendar event, "
                    "so nothing was loaded. Press Process to try again.")
        return ("The meeting's calendar event was found but could not be read, so nothing was loaded. "
                "Press Process to try again.")

    def facts(self):
        """What the run found for this meeting: online or not, the transcript URL and window, count, error, chat thread."""
        ev = self.event or {}
        uri = ev.get("uri") or self.uri_used
        s, e = uri_window(uri)
        return {"id": self.id, "online": bool(ev.get("join_url") or uri), "uri": uri, "count": None if self.transcripts is None else len(self.transcripts),
                "error": self.error, "start": s or ev.get("start"), "end": e or ev.get("end"), "thread": thread_id(ev.get("join_url"))}

    def finish(self, at=None):
        """Keep the status; for a load, write the transcript and the chat into inbox/. Returns {status, files, message}."""
        at = at or now()
        if self.wrong:
            return {"status": None, "files": [], "message": "The calendar event that came back wasn't the one asked for, so nothing was loaded."}
        if self.event is None:
            return {"status": None, "files": [], "message": self.no_event()}
        if self.event.get("cancelled"):
            return {"status": None, "files": [], "message": "That meeting was cancelled."}
        f = self.facts()
        past = ended({"day": self.day, "end": self.end_hm}, at) if self.day else True
        status = classify(online=f["online"], uri=f["uri"], count=f["count"], error=f["error"], past=past)
        if status:
            keep(self.id, {"status": status, "uri": f["uri"], "start": f["start"], "end": f["end"], "count": f["count"],
                           "thread": f["thread"], "checked": at.strftime("%Y-%m-%d %H:%M")})
        label = STATUSES.get(status)
        if self.mode == "check" or status != "available":
            return {"status": status, "files": [], "message": f"{label}." if label else "Couldn't tell yet: try again later."}
        return self.write(at, label)

    def write(self, at, label):
        """Write the meeting's transcript (and its chat, if read) to inbox/ as a tidied .vtt and .txt, unless it has
        been processed or is already in the inbox. Returns {status, files, message}.
        """
        import minutes
        done = minutes.processed_on(f"calendar:{self.id}")
        if done:
            return {"status": "available", "files": [], "message": f"Already processed on {done[8:10]}-{done[5:7]}-{done[:4]}."}
        existing = inbox_event_ids().get(self.id)
        if existing:
            return {"status": "available", "files": [existing], "message": "Already in the inbox.", "already": True}
        ev = self.event
        day = self.day or (when(ev.get("start")) or at).astimezone().strftime("%Y-%m-%d")
        meta = {"title": self.title or ev.get("title") or "Meeting", "day": day, "start": self.start_hm, "organiser": ev.get("organiser"),
                "attendees": ev.get("attendees"), "id": self.id}
        stem = file_stem(day, meta["title"])
        paths.INBOX.mkdir(parents=True, exist_ok=True)
        vtt = unique(paths.INBOX, stem, ".vtt")
        with open(vtt, "w", encoding="utf-8", newline="\n") as fh:    # write_text(newline=) needs Python 3.10; creaite runs on 3.9
            fh.write(tidy_vtt([t["content"] for t in self.transcripts], meta))
        files = [paths.rel(vtt)]
        msg = f"Loaded {vtt.name}."
        if self.chat_listing is not None:
            window = (self.facts()["start"], self.facts()["end"])
            text, n = chat_text(self.chat_listing, self.chat_full, window, meta)
            if n:
                chat = paths.INBOX / f"{vtt.stem} - chat.txt"
                with open(chat, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(text)
                files.append(paths.rel(chat))
                msg += f" And the meeting chat ({n} message{'s' if n != 1 else ''})."
        return {"status": "available", "files": files, "message": msg}


# ── command line ──
def main(argv):
    """Run the todo, record or show command in `argv`; record writes system/staging/transcripts.json."""
    if not argv:
        print(__doc__)
        return 1
    cmd = argv[0]
    if cmd == "todo":
        print(json.dumps(todo(), indent=1, ensure_ascii=False))
        return 0
    if cmd == "record" and len(argv) == 2:
        try:
            spec = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"Can't read {argv[1]}: {e}")
            return 1
        refused = []
        out = record((spec.get("results") if isinstance(spec, dict) else None) or [], refused=refused)
        kept = {k: v for k, v in out.items() if v}
        print(json.dumps({"recorded": kept, "not_yet": [k for k, v in out.items() if not v],
                          **({"refused": refused} if refused else {})}, indent=1))
        return 0
    if cmd == "show":
        print(json.dumps(load_state(), indent=1, ensure_ascii=False))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
