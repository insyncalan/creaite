"""creaite Close the day, a guided shutdown (BL-295): the plain code behind the card's steps. Standard library only.

The live server's routes (/api/day/card, /api/day/catchup, /api/day/close, /api/day/prep; dev/sprints/BL-295-server.md) call
this. Nothing here starts a run, approves, rejects or applies anything, and nothing is sent. The one file written is
system/staging/day-closed.json (`record`): each closed day's time ({"days": {YYYY-MM-DD: "HH:MM"}}, BL-206) and the plan made
in the card ({"plans": {YYYY-MM-DD: {"first", "review", "left", "prep", "swept"}}}), references only, never text:

  p:<proposal file>#<item n | meeting | report | file_changes>   a pending proposal's item or block
  i:<tracker ID>                                                  an action, RAID item or decision (ABC-A-003, ABC-002)
  t:<calendar event ID>                                           a meeting whose transcript is ready
  f:<12 hex>                                                      a file waiting in inbox/, by a fingerprint of its path

"First thing tomorrow" is the newest plan before today (`first_thing`), read by Today (build_dashboard.day_close) and the
session start; closing a day keeps only that day's plan, so the earlier list is cleared when its tomorrow is closed.
"""
import hashlib
import json
import re
import sqlite3
from contextlib import closing
from datetime import timedelta

import paths
import invite_clean  # noqa: E402  (2.6.8: a saved calendar is cleaned again when it is read)

MODES = ("offer", "start", "off")                 # day.catchup_sweep: ask first, start at once (the default), or never
PLACES = ("review", "first", "leave")             # Loose ends: Review now, First thing tomorrow, Leave
REF = re.compile(r"p:proposed-[A-Za-z0-9._-]{1,140}\.json#(?:\d{1,4}|meeting|report|file_changes)"
                 r"|i:[A-Z][A-Z0-9]{1,6}-(?:[A-Z]-)?\d{1,5}|t:[A-Za-z0-9+/=_.-]{1,300}|f:[0-9a-f]{12}")
LIST_MAX = 200                                     # the most references one plan keeps
TYPES = {"actions": "Action", "decisions": "Decision", "milestones": "Milestone", "promises": "Promise", "update": "Update",
         "files": "File change", "projects": "Project", "workstreams": "Workstream"}


# ── Settings ─────────────────────────────────────────────────────────────────

def catchup_settings(settings):
    """(mode, minutes): day.catchup_sweep (offer, start or off; start when missing or odd) and day.catchup_after_minutes (30)."""
    day = (settings or {}).get("day") or {}
    mode = day.get("catchup_sweep", "start")
    if isinstance(mode, bool) or mode is None:
        mode = "start" if mode else "off"
    try:
        after = max(0, int(day.get("catchup_after_minutes", 30)))
    except (TypeError, ValueError):                # an odd value: the default
        after = 30
    return (mode if mode in MODES else "start"), after


def when_shown(at, now):
    """A time as Alan reads it: "17:41" today, "12-10-2026 17:41" on another day; None stays None."""
    if not at:
        return None
    return at.strftime("%H:%M") if at.date() == now.date() else at.strftime("%d-%m-%Y %H:%M")


# ── Catch up ─────────────────────────────────────────────────────────────────

def catchup_decision(now, last, mode, minutes, busy=False, sweeping=False, dev=False, force=False):
    """Whether the catch-up sweep starts when the card opens: {status, message, last, last_shown}. status is start, offer (stale,
    but day.catchup_sweep asks first), recent, off, busy (another run: the server waits for it), sweeping (a sweep is already
    running) or cant (the development repository never reads Microsoft 365). `force` is Sweep again: it passes recent, off and
    offer, never busy, sweeping or cant."""
    out = {"last": last.strftime("%Y-%m-%d %H:%M") if last else None, "last_shown": when_shown(last, now)}
    status = catchup_status(now, last, mode, minutes, busy, sweeping, dev, force)
    return {"status": status, "message": CATCHUP_SAYS[status].format(last=out["last_shown"] or "never"), **out}


def catchup_status(now, last, mode, minutes, busy, sweeping, dev, force):
    """The status word for catchup_decision."""
    if dev:
        return "cant"
    if sweeping:
        return "sweeping"
    if not force and mode == "off":
        return "off"
    if not force and last and now - last < timedelta(minutes=minutes):
        return "recent"
    if busy:
        return "busy"
    return "offer" if mode == "offer" and not force else "start"


CATCHUP_SAYS = {"start": "Catching up: reading your Inbox, Sent Items and Teams since {last}.",
                "offer": "Mail and Teams last checked {last}. Catch up before you close?",
                "recent": "Caught up at {last}.",
                "off": "The last check of mail and Teams is off (Settings › General).",
                "busy": "Waiting for ask creaite to finish; the check starts after it (one run at a time).",
                "sweeping": "A check of mail and Teams is already running; this follows it.",
                "cant": "The development repository never reads Microsoft 365, so there is no check of mail and Teams here."}


# ── Loose ends ───────────────────────────────────────────────────────────────

def fingerprint(rel):
    """An inbox file's reference: the first 12 hex of the SHA-256 of its stored path (never the name itself)."""
    return hashlib.sha256(str(rel).encode("utf-8")).hexdigest()[:12]


def loose_ends(d, today, new_files=()):
    """Everything still open, each to be given a place: the catch-up sweep's new proposals first, then the other pending
    proposals, Intake (files waiting, transcripts ready) and open items due today or overdue. Each {ref, kind, type, t, p,
    project, new, place} (an item also has `due`) with place "first" (the card's default)."""
    names = {p["code"]: p["name"] for p in d.get("projects") or []}
    rows = proposal_rows(d.get("review") or [], set(new_files)) + intake_rows(d) + due_rows(d, today.isoformat())
    for r in rows:
        r.update(project=names.get(r["p"]), place="first")
    return sorted(rows, key=lambda r: not r["new"])


def proposal_rows(review_rows, new_files):
    """Review's pending rows as loose ends (one per item or block)."""
    out = []
    for r in review_rows:
        rec = r.get("rec") or {}
        kind = r.get("kind")
        word = rec.get("type") if kind == "raid" else "Minutes" if r.get("ref") == "meeting" else \
            "Report" if r.get("ref") == "report" else TYPES.get(kind, str(kind or "Item").capitalize())
        out.append({"ref": f"p:{r['file']}#{r['ref']}", "kind": "proposal", "type": word, "t": rec.get("t") or "",
                    "p": r.get("p"), "new": r["file"] in new_files})
    return out


def plain_file_name(name):
    """#291: an inbox file as a person names it: no extension, no leading 'Recording - ' (never the file name itself)."""
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(name or "")).strip()
    return re.sub(r"^Recording\s*-\s+", "", stem) or stem


def intake_rows(d):
    """Files waiting in inbox/ (not processed, not a chat) and meetings whose transcript is ready but not loaded or processed."""
    out = [{"ref": f"f:{fingerprint(f['path'])}", "kind": "intake", "type": "File in Intake", "t": plain_file_name(f.get("name") or ""),
            "p": f.get("p"), "new": False} for f in d.get("inbox") or [] if f.get("state") == "new"]
    for m in (d.get("meetings") or {}).get("rows") or []:
        if m.get("id") and m.get("transcript") == "available" and not (m.get("processed") or m.get("draft") or m.get("loaded")):
            out.append({"ref": f"t:{m['id']}", "kind": "intake", "type": "Transcript ready", "t": m.get("title") or "",
                        "p": m.get("p"), "new": False})
    return out


def due_rows(d, iso):
    """Open actions and RAID items due today, then those overdue (Alan, 13-10-2026: overdue items are loose ends too), oldest
    first."""
    out = []
    for table, word in (("actions", "Action"), ("raid", None)):
        for it in d.get(table) or []:
            due = it.get("due") or ""
            if due and due <= iso and it.get("st") not in ("Closed", "Cancelled"):
                when = "due today" if due == iso else "overdue"
                out.append({"ref": f"i:{it['id']}", "kind": "item", "type": f"{word or it.get('type') or 'RAID item'} {when}",
                            "t": it.get("t") or "", "p": it.get("p"), "new": False, "due": due})
    return sorted(out, key=lambda r: (r["due"] != iso, r["due"]))


def new_proposals(d, new_files):
    """What the catch-up sweep found, for step 1: {type, t, p, project} for each item it staged."""
    names = {p["code"]: p["name"] for p in d.get("projects") or []}
    return [{"ref": r["ref"], "type": r["type"], "t": r["t"], "p": r["p"], "project": names.get(r["p"])}
            for r in proposal_rows(d.get("review") or [], set(new_files)) if r["new"]]


# ── Tomorrow ─────────────────────────────────────────────────────────────────

def tomorrow(d, settings, today):
    """The next working day's meetings with their prep state (BL-293's day data): {day, day_shown, long, in_calendar, friday,
    meetings: [{start, end, title, confidential, p, project, key, page, plan, make}]}. A private meeting is left out; a
    confidential one keeps only its title and times (and its Prep key and page, as the day line has them)."""
    import build_dashboard
    nxt = build_dashboard.next_working_day(today, settings).isoformat()
    rec = next((x for x in (d.get("days") or {}).get("days") or [] if x.get("date") == nxt), None)
    names = {p["code"]: p["name"] for p in d.get("projects") or []}
    meets = [tomorrow_meeting(m, names) for m in (rec or {}).get("meetings") or [] if not m.get("private")]
    return {"day": nxt, "day_shown": build_dashboard.shown(nxt), "long": (rec or {}).get("long"), "in_calendar": rec is not None,
            "friday": today.weekday() == 4, "meetings": meets, "weekend": weekend_days(d, settings, today, nxt, names)}


def weekend_days(d, settings, today, nxt, names):
    """#187: the weekend days between today and the next working day that have something planned (the day band's rule, #138: a
    timed meeting, or an open or delayed action, an open RAID item or a milestone not done or cancelled due that day; an all-day
    note doesn't count): [{day, day_shown, long, meetings, due: [{type, t, p, project}]}]. Empty on a normal weekday. A private
    meeting shows as Busy with its times; a confidential one keeps only its title and times."""
    import build_dashboard
    import tracker
    off, out = tracker.weekend_days(settings), []
    day = today + timedelta(days=1)
    while day.isoformat() < nxt and day.weekday() in off:
        iso = day.isoformat()
        rec = next((x for x in (d.get("days") or {}).get("days") or [] if x.get("date") == iso), None)
        meets = [tomorrow_meeting(m, names) if not m.get("private") else
                 {"start": m.get("start") or "", "end": m.get("end") or "", "title": "Busy", "confidential": False, "key": None,
                  "page": None, "plan": False, "make": False} for m in (rec or {}).get("meetings") or []]
        due = weekend_due(d, iso, names)
        if meets or due:
            out.append({"day": iso, "day_shown": build_dashboard.shown(iso), "long": (rec or {}).get("long"), "meetings": meets,
                        "due": due})
        day += timedelta(days=1)
    return out


def weekend_due(d, iso, names):
    """Open work due on one day: [{type, t, p, project}] (actions and RAID items; milestones as Milestone)."""
    out = []
    for table, word, live in (("actions", "Action", ("Open", "Delayed")), ("raid", None, ("Open",))):
        for it in d.get(table) or []:
            if it.get("due") == iso and it.get("st") in live:
                out.append({"type": word or it.get("type") or "RAID item", "t": it.get("t") or "", "p": it.get("p"),
                            "project": names.get(it.get("p"))})
    return out + [{"type": "Milestone", "t": m[0] or "", "p": code, "project": names.get(code)}
                  for code, m in due_milestones(d, iso)]


def due_milestones(d, iso):
    """[(project code, milestone)] due on `iso` and not done or cancelled."""
    return [(pr.get("code"), m) for pr in d.get("projects") or [] for m in pr.get("ms") or []
            if m[1] == iso and m[2] != "done" and (len(m) < 7 or m[6] not in ("Done", "Cancelled"))]


def tomorrow_meeting(m, names):
    """One of tomorrow's meetings for the card: Make prep page when it has a Prep key and no page yet."""
    prep = m.get("prep") or {}
    out = {"start": m.get("start") or "", "end": m.get("end") or "", "title": m.get("title") or "",
           "confidential": bool(m.get("confidential")), "key": prep.get("key"), "page": prep.get("page"),
           "plan": bool(m.get("plan")), "make": bool(prep.get("key")) and not prep.get("page")}
    if not out["confidential"]:
        out.update(p=m.get("p"), project=names.get(m.get("p")))
    return out


# ── The day's record (system/staging/day-closed.json) ────────────────────────

def load():
    """day-closed.json as {"days": {day: "HH:MM"}, "plans": {day: plan}}; empty parts when it is missing or unreadable."""
    try:
        data = json.loads(paths.DAY_CLOSED.read_text(encoding="utf-8"))
    except (OSError, ValueError):                  # none yet, or unreadable: nothing closed
        data = {}
    data = data if isinstance(data, dict) else {}
    return {"days": data["days"] if isinstance(data.get("days"), dict) else {},
            "plans": data["plans"] if isinstance(data.get("plans"), dict) else {}}


def clean_refs(refs):
    """Only well-formed references, each once, in order, at most LIST_MAX."""
    return list(dict.fromkeys(r for r in refs or [] if isinstance(r, str) and REF.fullmatch(r)))[:LIST_MAX]


def make_plan(choices, prep=0, swept=None):
    """The plan kept with the day: references for First thing tomorrow and Review now, and counts. `choices` is {ref: place}."""
    first = clean_refs([r for r, w in choices.items() if w == "first"])
    review = clean_refs([r for r, w in choices.items() if w == "review"])
    return {"first": first, "review": review, "left": sum(1 for w in choices.values() if w == "leave"), "prep": int(prep or 0),
            "swept": swept}


def record(day, at, plan=None):
    """Write the closed day (the one write): its time, the last 30 days kept, and its plan, which replaces every earlier one
    (First thing tomorrow is cleared when its tomorrow is closed). Returns the record."""
    data = load()
    data["days"][day] = at
    data["days"] = dict(sorted(data["days"].items())[-30:])
    data["plans"] = {day: plan} if plan else {}
    paths.DAY_CLOSED.parent.mkdir(parents=True, exist_ok=True)
    tmp = paths.DAY_CLOSED.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    tmp.replace(paths.DAY_CLOSED)
    return data


def counts(plan):
    """The end line's numbers: {review, first, left, prep}."""
    plan = plan or {}
    return {"review": len(plan.get("review") or []), "first": len(plan.get("first") or []), "left": plan.get("left") or 0,
            "prep": plan.get("prep") or 0}


# ── First thing tomorrow, read the next day ──────────────────────────────────

def first_thing(today):
    """The newest plan before today, its references read afresh: {day, day_shown, items: [{ref, kind, type, t, p, open}]}, or
    None. An item already dealt with (decided, closed, processed, gone) has open false."""
    plans = load()["plans"]
    before = sorted(d for d in plans if d < today.isoformat() and isinstance(plans[d], dict))
    if not before:
        return None
    day = before[-1]
    look = Lookup()
    return {"day": day, "day_shown": f"{day[8:10]}-{day[5:7]}-{day[:4]}",
            "items": [look.resolve(r) for r in clean_refs(plans[day].get("first"))]}


def proposal_item(it):
    """A proposal's item as First thing tomorrow lists it: open while it is pending."""
    import review
    if not it:
        return {"kind": "proposal", "type": "Item", "t": "", "p": None, "open": False}
    what, text = review.describe(it)[:2]
    return {"kind": "proposal", "type": what, "t": text, "p": review.project_of(it),
            "open": it.get("decision") == "pending" and not it.get("applied")}


class Lookup:
    """Reads a reference's current state from the proposals, the tracker, the saved calendar and inbox/ (read only)."""

    def __init__(self):
        self._props = self._inbox = self._cal = None

    def resolve(self, ref):
        """{ref, kind, type, t, p, open} for one reference."""
        kind, _, rest = ref.partition(":")
        fn = {"p": self.proposal, "i": self.item, "t": self.meeting, "f": self.inbox_file}[kind]
        return {"ref": ref, **fn(rest)}

    def proposal(self, rest):
        """A proposal's item or block: open while it is still pending."""
        import review
        if self._props is None:
            self._props = {p.name: data for p, data in review.proposals()}
        name, _, part = rest.partition("#")
        data = self._props.get(name) or {}
        if part.isdigit():
            return proposal_item(next((i for i in data.get("items") or [] if str(i.get("n")) == part), None))
        block = data.get(part) or {}
        field = {"meeting": "minutes_decision", "report": "report_decision"}.get(part, "file_changes_decision")
        return {"kind": "proposal", "type": {"meeting": "Minutes", "report": "Report"}.get(part, "File change"),
                "t": block.get("title") or "", "p": block.get("project") or (block.get("projects") or [None])[0],
                "open": bool(block) and not block.get("applied") and block.get(field, "pending") == "pending"}

    def item(self, rest):
        """A tracker item: open until it is closed."""
        found = None
        if paths.DB.exists():
            with closing(sqlite3.connect(f"file:{paths.DB}?mode=ro", uri=True)) as con:
                for table, text in (("actions", "description"), ("raid", "description"), ("decisions", "decision")):
                    row = con.execute(f"SELECT {text}, project, status, '{table}' FROM {table} WHERE id = ?", (rest,)).fetchone()
                    found = found or row
        if not found:
            return {"kind": "item", "type": "Item", "t": rest, "p": None, "open": False}
        word = {"actions": "Action", "raid": "RAID item", "decisions": "Decision"}[found[3]]
        return {"kind": "item", "type": word, "t": f"{rest} {found[0] or ''}".strip(), "p": found[1],
                "open": found[2] not in ("Closed", "Cancelled", "Made", "Withdrawn")}

    def meeting(self, rest):
        """A meeting with a transcript ready: open until its minutes are processed."""
        import minutes
        if self._cal is None:
            try:
                cal = invite_clean.read_calendar(paths.CALENDAR)
            except (OSError, ValueError):          # no saved calendar: the meeting has no title to show
                cal = {}
            self._cal = {str(e.get("id")): (day, e) for day, evs in (cal.get("days") or {}).items() if isinstance(evs, list)
                         for e in evs if isinstance(e, dict) and e.get("id")}
        day, ev = self._cal.get(rest, (None, {}))
        done = minutes.processed_on(f"calendar:{rest}")
        return {"kind": "intake", "type": "Transcript ready", "t": "Busy" if ev.get("private") else ev.get("title") or "",
                "p": None, "day": day, "open": not done}

    def inbox_file(self, rest):
        """A file in inbox/: open while it is still there."""
        if self._inbox is None:
            files = sorted(paths.INBOX.iterdir()) if paths.INBOX.is_dir() else []
            self._inbox = {fingerprint(paths.rel(f)): f.name for f in files if f.is_file()}
        name = self._inbox.get(rest)
        return {"kind": "intake", "type": "File in Intake", "t": plain_file_name(name or ""), "p": None, "open": name is not None}


def pending_refs(files):
    """The references of everything still pending in these proposal files (the catch-up sweep's own), for a close that waited
    for the sweep: what it found and Alan never placed goes to First thing tomorrow."""
    import review
    out, wanted = [], set(files)
    for p, data in review.proposals():
        if p.name not in wanted:
            continue
        out += [f"p:{p.name}#{key}" for key, field, _ in review.BLOCKS
                if data.get(key) and not data[key].get("applied") and data[key].get(field, "pending") == "pending"]
        out += [f"p:{p.name}#{i.get('n')}" for i in data.get("items") or []
                if i.get("decision") == "pending" and not i.get("applied") and str(i.get("n", "")).isdigit()]
    return clean_refs(out)


def open_lists(plan):
    """What opens after closing, from Review now's references: Review filtered to {file, ref} pairs, Work to item IDs, Intake."""
    review = [r[2:] for r in (plan or {}).get("review") or [] if r.startswith("p:")]
    return {"review": [{"file": r.partition("#")[0], "ref": int(r.partition("#")[2]) if r.partition("#")[2].isdigit()
                        else r.partition("#")[2]} for r in review],
            "work": [r[2:] for r in (plan or {}).get("review") or [] if r.startswith("i:")],
            "intake": any(r[:2] in ("t:", "f:") for r in (plan or {}).get("review") or [])}
