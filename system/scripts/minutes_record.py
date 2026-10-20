"""The minutes record (v2.1.0 P4, BL-338). Standard library only. A library: no command line (minutes.py stage and the live server
call it from Python).

A meeting's minutes are a creaite document (creaite_doc.py, kind "minutes"), drafted by `minutes.py stage` into
system/staging/drafts/ and filed in each project's minutes folder when Alan approves them (tracker.py apply copies it, as it copied
the Word draft). The record holds:
- the sections of minutes-style.md: header, executive summary, updates by topic with flags, decisions, risks, issues, assumptions
  and dependencies, action items, open questions and escalations, what wasn't covered, and the source line;
- the proposed items as rows: decisions, RAID items and actions are the staged items themselves (row ref "@<n>", the item's
  number in the proposal, which tracker.py turns into the ID it gives when the minutes are approved);
- each line's transcript position for its time tag (section `tags` and row `at`: the VTT cue time, else the speaker turn), shown
  in creaite only and never exported;
- in `meta`: the proposal, the meeting key, the transcript, the start and end times, the source line, agenda coverage and what was
  done about each point, milestone notes (never a change: BL-186), and removed rows kept for Undo.

Every change here goes to the proposal (review.save, then tracker.py validate) and to the record (creaite_doc.save, a new version
through filechange.py). Nothing reaches the tracker until the minutes are approved (review.approve_minutes: one apply).
"""
import contextlib
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import creaite_doc  # noqa: E402
import date_words  # noqa: E402

FLAGS = ("PRIORITY", "ACTION", "FLAG", "BLOCKED", "SUPPORT NEEDED", "NEW SCOPE", "NEW", "ON TRACK", "HIGH RISK", "DONE")
HEADINGS = {"header": "Meeting", "summary": "Executive Summary", "updates": "Updates", "decisions": "Decisions",
            "raid": "Risks, Issues, Assumptions & Dependencies", "actions": "Action Items",
            "open_questions": "Open Questions / Escalations", "not_covered": "Not covered in this meeting", "source": "Source"}
COLUMNS = {"decisions": [{"key": "decision", "label": "Decision"}, {"key": "by", "label": "Made by"}],
           "raid": [{"key": "type", "label": "Type"}, {"key": "description", "label": "Description"},
                    {"key": "owner", "label": "Owner"}],
           "actions": [{"key": "owner", "label": "Owner"}, {"key": "action", "label": "Action"},
                       {"key": "due", "label": "Deadline"}]}
ROW_TABLES = {"actions": "actions", "decisions": "decisions", "raid": "raid"}
CLOSING = ("Closed", "Cancelled")
HHMM = re.compile(r"([01]\d|2[0-3]):[0-5]\d$")
TIME = re.compile(r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:[.,]\d+)?$")
CUE = re.compile(r"((?:\d{1,2}:)?\d{1,2}:\d{2}(?:[.,]\d+)?)\s*-->\s*((?:\d{1,2}:)?\d{1,2}:\d{2}(?:[.,]\d+)?)")
HOW = {"carry": "Carried to the next meeting", "session": "A separate session", "drop": "No longer needed",
       "enough": "Covered enough"}


class RecordError(ValueError):
    """Why a change to the minutes can't be made, as a plain sentence for Alan."""


# ── The transcript: speaker turns and their times ────────────────────────────

def seconds(t):
    """"00:12:34.500", "12:34" or "1:02:03" as whole seconds, or None."""
    m = TIME.match(str(t or "").strip())
    return int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) if m else None


def clock(s):
    """Seconds as HH:MM:SS."""
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def _vtt_cues(text):
    """[(start, end, who, said)] of a .vtt file's cues; NOTE blocks are left out."""
    cues, timing, note = [], None, False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            timing, note = None, False
            continue
        if note or line.startswith("NOTE") or line == "WEBVTT":
            note = note or line.startswith("NOTE")
            continue
        m = CUE.search(line)
        if m:
            timing = (seconds(m.group(1)), seconds(m.group(2)))
            continue
        if timing is None or line.isdigit():
            continue
        v = re.match(r"<v ([^>]+)>(.*?)(?:</v>)?$", line)
        who, said = (v.group(1).strip(), v.group(2)) if v else (None, line)
        cues.append((timing[0], timing[1], who, re.sub(r"<[^>]+>", "", said).strip()))
    return cues


def _merged(cues):
    """Consecutive cues by the same speaker as one turn."""
    turns = []
    for start, end, who, said in cues:
        if turns and turns[-1]["who"] == who:
            turns[-1]["end"] = end
            turns[-1]["text"] += " " + said
        else:
            turns.append({"who": who, "start": start, "end": end, "text": said})
    return turns


def _text_turns(text):
    """Speaker turns from minutes.transcript_text's lines: "Name (0:03): text" (timed) or "Name: text"."""
    turns = []
    for line in text.splitlines():
        m = re.match(r"(.{1,80}?) \(((?:\d{1,2}:)?\d{1,2}:\d{2})\): (.*)$", line) or re.match(r"([^:]{1,80}): (.*)$", line)
        if not m:
            continue
        timed = len(m.groups()) == 3
        turns.append({"who": m.group(1).strip(), "start": seconds(m.group(2)) if timed else None, "end": None,
                      "text": (m.group(3) if timed else m.group(2)).strip()})
    return turns


def turns(path):
    """{"timed": bool, "turns": [{n, who, start, end, text}]}: the transcript as speaker turns, numbered from 1, with VTT cue times
    (or Teams' Word export's times) as HH:MM:SS. Read only; [] when there is no transcript."""
    if not path:
        return {"timed": False, "turns": []}
    p = paths.resolve(path)
    if not p.is_file():
        return {"timed": False, "turns": []}
    if p.suffix.lower() == ".vtt":
        raw = _merged(_vtt_cues(p.read_text(encoding="utf-8", errors="ignore")))
    else:
        import minutes
        raw = _text_turns(minutes.transcript_text(p))
    out = [{"n": i, "who": t["who"], "start": clock(t["start"]) if t["start"] is not None else None,
            "end": clock(t["end"]) if t.get("end") is not None else None, "text": t["text"]} for i, t in enumerate(raw, 1)]
    return {"timed": any(t["start"] for t in out), "turns": out}


def position(line, tr):
    """A line's time tag from what cx-minutes gave ("at": a cue time, or "turn": a speaker turn's number): {turn, time} or None.
    A time is matched to the turn said then; a turn number to that turn and its time."""
    if not isinstance(line, dict):
        return None
    ts = tr["turns"]
    if line.get("at") not in (None, "") and tr["timed"]:
        s = seconds(line["at"])
        if s is None:
            return None
        hit = [t for t in ts if t["start"] and seconds(t["start"]) <= s]
        return {"turn": hit[-1]["n"], "time": clock(s)} if hit else None
    n = line.get("turn")
    if isinstance(n, int) and 1 <= n <= len(ts):
        return {"turn": n, "time": ts[n - 1]["start"]}
    return None


def tag(line, text, tr):
    """The source tag of one line drawn from the transcript, or None: {ref: "transcript", turn, time, text}."""
    at = position(line, tr)
    return {"ref": "transcript", **at, "text": str(text)[:200]} if at else None


# ── Deadlines in words ───────────────────────────────────────────────────────

def deadlines(spec):
    """Work each action's or promise's deadline in words (`due_words`) out from the meeting's date (date_words.deadline), into
    `due_date`; the reading is marked as guessed (BL-208). Returns notes for words it couldn't read (left Not set)."""
    notes, day = [], spec["date"]
    for raw in spec.get("items") or []:
        words = raw.pop("due_words", None) or (raw.get("values") or {}).pop("due_words", None)
        if not words or raw.get("op") == "update":
            continue
        values = raw.setdefault("values", {})
        got = date_words.deadline(words, day)
        if not got:
            notes.append(f"deadline \"{str(words)[:40]}\" isn't a date creaite can read; left Not set")
            continue
        values.setdefault("due_date", got)
        raw.setdefault("inferred", []).append({"field": "due_date", "why": f"said “{str(words)[:40]}”, from the meeting's date"})
    return notes


# ── The items as rows ────────────────────────────────────────────────────────

def _shown(day):
    """YYYY-MM-DD as DD-MM-YYYY; '' for none."""
    import tracker
    return tracker.shown(day) if day else ""


def _change_words(item):
    """An update's changes in words: "status Closed; due 16-10-2026"."""
    import review
    import tracker
    fmt = lambda f, x: tracker.shown(x) if f in tracker.DATE_FIELDS else str(x)  # noqa: E731
    return "; ".join(f"{review.UPDATE_LABELS.get(f, f.replace('_', ' '))} {fmt(f, c)}" for f, c in (item.get("changes") or {}).items())


def does(item):
    """What a row does, in words: "New action", "Closes ABC-A-003", "Records ABC-D-004 as made", "Looks like ABC-R-006"."""
    table, v, ch = item.get("table"), item.get("values") or {}, item.get("changes") or {}
    if item.get("op") == "update":
        status = ch.get("status")
        if table == "decisions" and status in ("Made", "Withdrawn"):
            return f"Records {item['id']} as {status.lower()}"
        return f"Closes {item['id']}" if status in CLOSING else f"Updates {item['id']}"
    if table == "decisions":
        return "Decision needed" if v.get("status") == "Pending" else "New decision"
    kind = {"actions": "action", "raid": (v.get("type") or "risk").lower()}.get(table, table)
    ll = item.get("looks_like") or {}
    looks = f" · Looks like {ll['id']}" if ll.get("id") and not (ll.get("kept") or ll.get("merged")) else ""
    return f"New {kind}{looks}"


def _update_cells(item):
    """An update's row: the item it changes and the changes in words."""
    ch = item.get("changes") or {}
    what = f"{item['id']}: {_change_words(item)}"
    return {"actions": {"owner": "", "action": what, "due": _shown(ch.get("due_date"))},
            "decisions": {"decision": what, "by": ch.get("made_by") or ""},
            "raid": {"type": "", "description": what, "owner": ""}}[item["table"]]


def _cells(item):
    """A row's cells for its table, from the staged item."""
    table, v = item["table"], item.get("values") or {}
    if item.get("op") == "update":
        return _update_cells(item)
    if table == "actions":
        return {"owner": v.get("owner") or "TBC", "action": v.get("description") or "",
                "due": _shown(v.get("due_date")) or "Not set"}
    if table == "decisions":
        by = v.get("made_by") or ""
        return {"decision": v.get("decision") or "", "by": f"Needed from {by}" if v.get("status") == "Pending" and by else by}
    return {"type": v.get("type") or "Risk", "description": v.get("description") or "", "owner": v.get("owner") or ""}


def item_row(item, at=None):
    """(section id, row) for a staged item, or (None, None) for one the minutes don't show (a promise, a milestone)."""
    section = ROW_TABLES.get(item.get("table"))
    if not section:
        return None, None
    row = {"ref": f"@{item['n']}", "n": item["n"], "cells": _cells(item), "shown": True, "does": does(item)}
    if at:
        row["at"] = at
    return section, row


def item_snapshot(item):
    """The staged item as the record keeps it (items, keyed by its row ref)."""
    keep = ("table", "op", "n", "id", "values", "changes", "flags", "looks_like", "decision")
    return {k: item[k] for k in keep if k in item}


def table_section(sid, rows):
    """A table section of the minutes."""
    return {"id": sid, "type": "table", "heading": HEADINGS[sid], "default_heading": HEADINGS[sid], "hidden": False,
            "text": "" if rows else "None recorded.", "columns": COLUMNS[sid], "rows": rows}


def text_section(sid, text, tags=(), data=None, kind="text"):
    """A text section of the minutes."""
    s = {"id": sid, "type": kind, "heading": HEADINGS[sid], "default_heading": HEADINGS[sid], "hidden": False,
         "text": text or "None recorded.", "tags": [t for t in tags if t]}
    if data is not None:
        s["data"] = data
    return s


def _bullets(lines, tr):
    """(markdown list, tags) for a list of lines (text, or {text, at|turn})."""
    md, tags = [], []
    for ln in lines or []:
        text = ln.get("text") if isinstance(ln, dict) else str(ln)
        if text:
            md.append(f"- {text}")
            tags.append(tag(ln, text, tr))
    return "\n".join(md), tags


def _topic_lines(items, tr, tags):
    """One topic's lines ({text, flag}), a flag kept only when it is one of minutes-style's ten; each line's tag added to `tags`."""
    lines = []
    for ln in items or []:
        text = ln.get("text") if isinstance(ln, dict) else str(ln)
        flag = ln.get("flag") if isinstance(ln, dict) and ln.get("flag") in FLAGS else None
        if text:
            lines.append({"text": text, **({"flag": flag} if flag else {})})
            tags.append(tag(ln, text, tr))
    return lines


def updates_section(topics, tr):
    """Updates by topic: a bold heading per topic, then its lines, a flag in capitals before the few that carry one."""
    md, tags, kept = [], [], []
    for t in topics or []:
        heading = str((t or {}).get("heading") or "").strip()
        lines = _topic_lines((t or {}).get("items"), tr, tags)
        if heading or lines:
            md.append("\n".join([f"**{heading}**"] + [f"- {'**' + x['flag'] + '** ' if x.get('flag') else ''}{x['text']}"
                                                       for x in lines]))
            kept.append({"heading": heading, "lines": lines})
    return text_section("updates", "\n\n".join(md), tags, {"topics": kept})


# ── The header and the source line ───────────────────────────────────────────

def clean_title(title):
    """A meeting title as the minutes show it: [CODE] tags removed (the folder and the page show the project)."""
    return re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]", "", str(title or ""))).strip() or "Meeting"


def when(day, start=None, end=None):
    """"30 September 2026, 12:00–13:05 (UAE time)"; without the times when they aren't known."""
    import tracker
    s = start if start and HHMM.match(start) else None
    e = end if end and HHMM.match(end) and s and end > s else None
    return tracker.long_date(day) + (f", {s}{'–' + e if e else ''} (UAE time)" if s else "")


def source_line(title, day, start=None, end=None, chat=True, partial=False):
    """The minutes' source, naming the meeting exactly: "Teams transcript and meeting chat, <title>, <long date>, HH:MM–HH:MM (UAE
    time)"; "Teams transcript" alone when the chat wasn't used. A partial transcript says so."""
    what = "Teams transcript and meeting chat" if chat else "Teams transcript"
    line = f"{what}, {clean_title(title)}, {when(day, start, end)}"
    return line + (". The transcript ends before the meeting does." if partial else "")


def status_line(on):
    """The draft's status line."""
    import tracker
    return f"Draft, generated by creaite on {tracker.long_date(on)}. Not yet reviewed."


def header_section(spec, m):
    """The header: the status line, when it was and who was there."""
    import minutes
    status = status_line(minutes._today().isoformat())
    w = when(spec["date"], m.get("start"), m.get("end"))
    attendees = str(m.get("attendees") or "").strip()
    text = "\n\n".join(x for x in (status, f"**When:** {w}", f"**Attendees:** {attendees}" if attendees else "") if x)
    return text_section("header", text, data={"status": status, "when": w, "attendees": attendees}, kind="header")


# ── The record ───────────────────────────────────────────────────────────────

def item_sections(items, at_of, tr):
    """The decisions, RAID and actions sections from the staged items, in the proposal's order."""
    rows = {"decisions": [], "raid": [], "actions": []}
    for it in items:
        sid, row = item_row(it, position(at_of.get(it["n"]) or {}, tr))
        if sid:
            rows[sid].append(row)
    return [table_section(sid, rows[sid]) for sid in ("decisions", "raid", "actions")]


def record_meta(spec, meeting, proposal_name, tr, line, status):
    """The record's meta: its proposal and meeting key, the transcript, the times, the source line, coverage and milestone notes."""
    m = spec.get("minutes") or {}
    notes = [{"id": str(x.get("id") or ""), "note": str(x.get("note") or "")[:300], "at": position(x, tr)}
             for x in m.get("milestones") or [] if isinstance(x, dict) and x.get("id")]
    return {"proposal": proposal_name, "key": meeting.get("key"), "projects": meeting.get("projects") or [],
            "transcript": spec.get("transcript"), "timed": tr["timed"], "turns": len(tr["turns"]),
            "start": m.get("start"), "end": m.get("end"), "source_line": line, "status_line": status,
            "coverage": [dict(c) for c in meeting.get("coverage") or []], "agenda": meeting.get("agenda"),
            "milestones": notes, "removed": {}}


def build(spec, proposal, proposal_name, at_of):
    """The minutes record for one staged meeting: a creaite document (nothing written). `at_of` maps an item's number to the
    position cx-minutes gave its line ({at} or {turn})."""
    m = spec.get("minutes") or {}
    meeting = proposal["meeting"]
    tr = turns(spec.get("transcript"))
    summary = [p for p in m.get("summary") or [] if p]
    texts = [p.get("text") if isinstance(p, dict) else str(p) for p in summary]
    sections = [header_section(spec, m),
                text_section("summary", "\n\n".join(texts), [tag(p, t, tr) for p, t in zip(summary, texts)]),
                updates_section(m.get("updates"), tr)]
    sections += item_sections(proposal["items"], at_of, tr)
    sections.append(text_section("open_questions", *_bullets(m.get("open_questions"), tr)))
    line = source_line(spec["title"], spec["date"], m.get("start"), m.get("end"), m.get("chat", True), m.get("partial", False))
    sections.append(text_section("source", line))
    items = {f"@{i['n']}": item_snapshot(i) for i in proposal["items"]}
    project = (meeting.get("projects") or ["_portfolio"])[0]
    meta = record_meta(spec, meeting, proposal_name, tr, line, sections[0]["data"]["status"])
    return creaite_doc.new("minutes", project, clean_title(spec["title"]), spec["date"], sections, items=items,
                           sources=[{"ref": spec.get("transcript"), "label": "Teams transcript"}] if spec.get("transcript") else [],
                           meta=meta)


def record_path(day, title):
    """Where the draft record goes: system/staging/drafts/YYYY-MM-DD <title>.html, never over another file."""
    import minutes
    return paths.free_path(paths.DRAFTS, minutes.stem(day, title), ".html")


def filed_paths(projects, day, title):
    """{code: the stored path the minutes are filed at in that project's minutes folder} (creaite_doc.target)."""
    return {code: creaite_doc.target("minutes", code, day, clean_title(title)) for code in projects}


def is_record(path):
    """Whether a meeting's draft is a minutes record (a creaite document), not a Word draft."""
    return bool(path) and str(path).lower().endswith(".html") and creaite_doc.is_doc(path)


# ── Opening a record with its proposal ───────────────────────────────────────

def proposal_for(doc):
    """(path, data) of the proposal the record's items are staged in. Raises RecordError when it is gone (applied, or never)."""
    name = (doc.get("meta") or {}).get("proposal") or ""
    p = paths.STAGING / name
    if not re.fullmatch(r"proposed-[\w.-]+\.json", name) or not p.is_file():
        raise RecordError("These minutes' items aren't pending any more: they were approved or the proposal has gone.")
    return p, json.loads(p.read_text(encoding="utf-8"))


def item_of(data, n):
    """The proposal's item n, not yet applied. Raises RecordError."""
    item = next((i for i in data.get("items") or [] if i.get("n") == n), None)
    if item is None or item.get("applied"):
        raise RecordError(f"Item {n} isn't a pending item of these minutes.")
    return item


def save_proposal(p, data):
    """Write the proposal back (the first as-proposed copy kept, BL-232) and validate it (tracker.py validate; its lines kept quiet)."""
    import review
    import tracker
    review.save(p, data)
    with contextlib.redirect_stdout(io.StringIO()):
        tracker.cmd_validate(str(p))
    return json.loads(p.read_text(encoding="utf-8"))


def section_of(doc, sid):
    """The record's section `sid`, or None."""
    return next((s for s in doc["sections"] if s.get("id") == sid), None)


def find_row(doc, n):
    """(section, index) of item n's row, or (None, None)."""
    for s in doc["sections"]:
        for i, r in enumerate(s.get("rows") or []):
            if r.get("n") == n and r.get("ref"):
                return s, i
    return None, None


def sync_item(doc, item):
    """Item n's row and snapshot follow the staged item (its cells, what it does); a row that isn't there is added."""
    s, i = find_row(doc, item["n"])
    sid, row = item_row(item, (s["rows"][i].get("at") if s else None))
    doc["items"][f"@{item['n']}"] = item_snapshot(item)
    if s is not None and sid == s["id"]:
        s["rows"][i] = row
    elif sid:
        if s is not None:
            del s["rows"][i]
        target = section_of(doc, sid)
        target["rows"].append(row)
        target["text"] = ""
    for t in doc["sections"]:
        if t.get("type") == "table" and t["id"] in COLUMNS:
            t["text"] = "" if t.get("rows") else "None recorded."


REFUSED_FILED = "Filed minutes are never saved over, so nothing was changed. The filed minutes are as they were."


UNSAVED = re.compile(r"creaite-doc \d{4}-\d{2}-\d{2} \d{6}(-\d+)?\.html")


def _save_drafts():
    """The names of creaite_doc.save's own drafts directly in system/staging/drafts/ (`creaite-doc <date> <time>.html`)."""
    try:
        return [f.name for f in paths.DRAFTS.iterdir() if UNSAVED.fullmatch(f.name)]
    except OSError:
        return []


def _drop_unsaved(name):
    """A refused save over filed minutes leaves its unsaved copy in drafts/ "for the card"; with no card path it is never used, so
    it goes (BL-118's rule: only that exact file, only directly inside drafts/ once resolved, never a symlink). A copy a recorded
    request names (an ask creaite run's card) is kept."""
    import filechange
    given = paths.DRAFTS / name
    try:
        real = given.resolve()
        if given.is_symlink() or real.parent != paths.DRAFTS.resolve() or not real.is_file():
            return False
        rel = paths.rel(given)
        for f in filechange.REQUESTS.glob("*.json") if filechange.REQUESTS.is_dir() else []:
            try:
                if json.loads(f.read_text(encoding="utf-8")).get("from") == rel:
                    return False
            except (OSError, ValueError):
                continue                    # an unreadable request names nothing: it keeps no copy
        given.unlink()
    except OSError:
        return False
    return True


def save_record(path, doc, why, base_version=None, via="dashboard"):
    """Save the record as a new version (creaite_doc.save, never with an approver). Saving over filed minutes is refused (Alan,
    15-10-2026): they are the record people were sent, a save from the minutes view is never approved and there is no card path,
    so creaite_doc's code-3 answer (needs approval) comes back as it is, with a plain message, and nothing changes. Raises
    RecordError when it is refused for any other reason."""
    before = set(_save_drafts())
    r = creaite_doc.save(path, doc, why, base_version=base_version, via=via)
    if r.get("needs_approval"):
        for left in sorted(set(_save_drafts()) - before):
            _drop_unsaved(left)
        return {**r, "message": REFUSED_FILED}
    if not r.get("ok"):
        raise RecordError(r.get("message") or "The minutes weren't saved.")
    return r


# ── What Alan does on an item row ────────────────────────────────────────────

def remove(doc, data, n, keep_line=False):
    """✕ Remove: the item is rejected ("Removed in the minutes") and its row leaves the minutes; with keep_line its words stay as a
    line with no item. The row is kept in meta.removed for Undo."""
    item = item_of(data, n)
    s, i = find_row(doc, n)
    if item.get("decision") == "rejected" and str(n) in doc["meta"].get("removed", {}):
        raise RecordError(f"Item {n} is already removed.")
    item.update(decision="rejected", reject_reason="Removed in the minutes", decided_in="minutes")
    removed = doc["meta"].setdefault("removed", {})
    if s is not None:
        row = s["rows"][i]
        removed[str(n)] = {"section": s["id"], "index": i, "row": row, "kept_line": bool(keep_line)}
        if keep_line:
            s["rows"][i] = {"ref": None, "cells": row["cells"], "shown": True, "kept_line": True, "was": row["ref"]}
        else:
            del s["rows"][i]
    doc["items"].pop(f"@{n}", None)
    return f"Removed item {n}" + (" (its line is kept in the minutes)." if keep_line else " and its line.")


def restore(doc, data, n):
    """Undo ✕ Remove: the item is pending again and its row back where it was."""
    item = item_of(data, n)
    if item.get("decision") != "rejected" or item.get("decided_in") != "minutes":
        raise RecordError(f"Item {n} wasn't removed here.")
    _row_back(doc, data, item)
    return f"Item {n} is back."


def _row_back(doc, data, item):
    """The item's row back where it was (out of meta.removed; a kept line gives way to the row) and the item pending again."""
    n = item["n"]
    gone = doc["meta"].get("removed", {}).pop(str(n), None)
    if isinstance(item.get("was"), dict) and item.get("duplicate_of"):    # Update that one found a duplicate: the item as it was
        item = {**item["was"], "n": n}
        data["items"][next(k for k, i in enumerate(data["items"]) if i.get("n") == n)] = item
    item["decision"] = "pending"
    for k in ("reject_reason", "decided_in", "duplicate_of", "retargeted"):
        item.pop(k, None)
    if gone:
        s = section_of(doc, gone["section"])
        s["rows"] = [r for r in s["rows"] if not (r.get("kept_line") and r.get("was") == f"@{n}")]
        s["rows"].insert(min(gone["index"], len(s["rows"])), gone["row"])
    sync_item(doc, item)


def unsettled(doc, data):
    """#268: the rows the record took out (meta.removed: removed, or kept as a line only) whose items are pending again, newest
    first. Undo of Approve minutes (tracker.py undo) puts the proposal's items back to pending but leaves the record as the
    approve's own changes made it, so until it is settled the record doesn't match its items."""
    removed = ((doc or {}).get("meta") or {}).get("removed") or {}
    items = {i.get("n"): i for i in (data or {}).get("items") or []}
    out = []
    for k in reversed(list(removed)):
        it = items.get(int(k)) if str(k).isdigit() else None
        if it and not it.get("applied") and it.get("decision") != "rejected":
            out.append(int(k))
    return out


def settle(doc, data):
    """#268: each unsettled row back as it was, in the reverse order of the changes that took them out (so each goes back to its
    own place): after Undo of Approve minutes the minutes are exactly as they were before Approve. Returns the numbers."""
    ns = unsettled(doc, data)
    for n in ns:
        _row_back(doc, data, next(i for i in data["items"] if i.get("n") == n))
    return ns


def update_that_one(doc, data, p, n, target):
    """"Update that one" (BL-221): the new item becomes an update of an existing item (review.retarget_item's checks and result),
    and its row says so."""
    import review
    target = str(target or "").strip().upper()
    code, msg = review.retarget_item(p, data, item_of(data, n), target, decided_in="minutes")
    if code:
        raise RecordError(msg[:1].upper() + msg[1:])
    item = item_of(data, n)
    if item.get("decision") == "rejected":                  # nothing new to carry: it is the same item, so it leaves the minutes
        s, i = find_row(doc, n)
        if s is not None:
            doc["meta"].setdefault("removed", {})[str(n)] = {"section": s["id"], "index": i, "row": s["rows"].pop(i),
                                                            "kept_line": False}
        doc["items"].pop(f"@{n}", None)
        return f"Nothing new to carry to {target}: item {n} repeats it, so it was taken out of the minutes."
    sync_item(doc, item)
    return f"Item {n} now updates {target} instead."


def keep_new(doc, data, p, n):
    """"Keep as new": the "Looks like" mark is dropped, or a merge undone (review's keep-new and unmerge)."""
    item = item_of(data, n)
    if not isinstance(item.get("was"), dict) and not item.get("looks_like"):
        raise RecordError(f"Item {n} doesn't look like an existing item.")
    if isinstance(item.get("was"), dict):
        item = {**item["was"], "n": n}
        data["items"][next(k for k, i in enumerate(data["items"]) if i.get("n") == n)] = item
    if item.get("looks_like"):
        item["looks_like"] = {**item["looks_like"], "kept": True}
    sync_item(doc, item)
    return f"Item {n} stays a new item."


EDITABLE = {"actions": ("description", "owner", "due_date", "workstream", "priority"),
            "raid": ("description", "owner", "type", "impact", "likelihood", "response_action", "due_date"),
            "decisions": ("decision", "made_by", "reasoning", "options", "needed_by")}


def edit_item(doc, data, n, values):
    """Edit a new item from its row (the row and the staged item are one): only its own fields; a deadline may be words."""
    item = item_of(data, n)
    allowed = EDITABLE.get(item.get("table"), ())
    if item.get("op") != "new" or not allowed:
        raise RecordError(f"Item {n} is an update; change it in Review.")
    bad = sorted(set(values) - set(allowed) - {"due_words"})
    if bad:
        raise RecordError(f"{', '.join(bad)} can't be changed from the minutes.")
    v = item.setdefault("values", {})
    for f, x in values.items():
        if f == "due_words":
            got = date_words.deadline(x, doc["date"]) if str(x or "").strip().lower() not in ("", "not set") else None
            if x and str(x).strip().lower() != "not set" and not got:
                raise RecordError(f"“{x}” isn't a date creaite can read. Try “Friday”, “next week” or 30-10.")
            f, x = "due_date", got
        if x in (None, ""):
            v.pop(f, None)
        else:
            v[f] = x
    item["edited_in"] = "minutes"
    sync_item(doc, item)
    due = v.get("due_date")
    return f"Item {n} changed" + (f"; due {date_words.said(due)}." if "due_words" in values and due else ".")


# ── Agenda coverage: what was done about each point ─────────────────────────

def _point(doc, point):
    """The coverage entry for `point` (by its words). Raises RecordError."""
    import minutes
    hit = next((c for c in doc["meta"].get("coverage") or [] if minutes._norm_point(c.get("point")) == minutes._norm_point(point)),
               None)
    if not hit:
        raise RecordError("That point isn't on this meeting's agenda.")
    return hit


def next_meeting(title, day):
    """The day of the series' next meeting in the saved calendar (YYYY-MM-DD), or None."""
    import build_dashboard
    series = build_dashboard.series_of(title)
    for d, events in sorted(build_dashboard.saved_calendar_days().items()):
        if d > day and any(build_dashboard.series_of(e.get("title") or "") == series for e in events or []):
            return d
    return None


def _line(doc, text):
    """Add a line under "Not covered in this meeting" (the section is made, before the source, the first time)."""
    s = section_of(doc, "not_covered")
    if s is None:
        s = text_section("not_covered", "")
        s["text"] = ""
        doc["sections"].insert(next(i for i, x in enumerate(doc["sections"]) if x["id"] == "source"), s)
    s["text"] = "\n".join(x for x in (s["text"], f"- {text}") if x)


def _unline(doc, text):
    """Take a line out of "Not covered in this meeting" (the section goes when it is empty)."""
    s = section_of(doc, "not_covered")
    if s is None:
        return
    s["text"] = "\n".join(x for x in s["text"].splitlines() if x != f"- {text}")
    if not s["text"].strip():
        doc["sections"].remove(s)


def session_action(doc, data, point):
    """The action "Set up a separate session on <point>" for Alan, due Friday from the meeting's date, added to the proposal."""
    me = (paths.load_settings().get("identity") or {}).get("name") or "Alan"
    project = (doc["meta"].get("projects") or [doc["project"]])[0]
    n = max([i.get("n", 0) for i in data.get("items") or []] + [0]) + 1
    src = next((v.get("source") for v in (i.get("values") or {} for i in data["items"]) if v.get("source")), "")
    where = src.split(" — ")[0] if src else doc["meta"].get("transcript") or ""
    item = {"n": n, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending", "added_in": "minutes",
            "values": {"project": project, "description": f"Set up a separate session on {point}"[:300], "owner": me,
                       "due_date": date_words.deadline("Friday", doc["date"]), "raised": doc["date"],
                       "source": f"{where} — Not covered in this meeting" if where else ""}}
    if not item["values"]["source"]:
        item["values"].pop("source")
    data["items"].append(item)
    sync_item(doc, item)
    return n


def cover(doc, data, point, how, add_line=True):
    """Deal with an agenda point that wasn't covered: carry it to the series' next meeting (minutes.carry, carried.json, as
    /api/meeting/carry), set up a separate session (an action for Alan, due Friday), or drop it (No longer needed, Covered enough).
    With add_line a line goes under "Not covered in this meeting". Recorded on the point for Undo."""
    import minutes
    if how not in HOW:
        raise RecordError("Carry it, set up a separate session, or say it's no longer needed or covered enough.")
    hit = _point(doc, point)
    if hit.get("action"):
        raise RecordError("That point has been dealt with; undo that first.")
    act, text = {"how": how, "line": ""}, hit["point"]
    if how == "carry":
        minutes.carry(True, doc["meta"]["key"], text)
        nxt = next_meeting(doc["title"], doc["date"])
        import tracker
        act["line"] = f"{text} was not discussed; it is carried to the next {doc['title']}" + \
            (f" on {tracker.long_date(nxt)}." if nxt else ".")
    elif how == "session":
        act["item"] = session_action(doc, data, text)
        act["line"] = f"{text} was not discussed; a separate session will be set up."
    else:
        act["line"] = f"{text} was not discussed; no longer needed." if how == "drop" else f"{text} was covered enough."
    if add_line:
        _line(doc, act["line"])
    else:
        act["line"] = ""
    hit["action"] = act
    return HOW[how] + "."


def uncover(doc, data, point):
    """Undo what was done about a point: no longer carried, the session action taken out (while it is pending), the line gone."""
    import minutes
    hit = _point(doc, point)
    act = hit.pop("action", None)
    if not act:
        raise RecordError("Nothing was done about that point.")
    if act["how"] == "carry":
        minutes.carry(False, doc["meta"]["key"], hit["point"])
    if act.get("item"):
        item = item_of(data, act["item"])
        data["items"].remove(item)
        s, i = find_row(doc, act["item"])
        if s is not None:
            del s["rows"][i]
        doc["items"].pop(f"@{act['item']}", None)
    if act.get("line"):
        _unline(doc, act["line"])
    return "Undone."


# ── One change from the minutes view ─────────────────────────────────────────

def _settled_words(settled):
    """The `settle` change's message; with nothing to settle it is refused, so no new version is saved."""
    if not settled:
        raise RecordError("Nothing to put back.")
    return f"Put back {len(settled)} line{'s' if len(settled) != 1 else ''} as they were before approving."


def change(path, op, base_version=None, via="dashboard"):
    """Apply one change from the minutes view to the draft record and its proposal, then save both. `op` is {op: remove | restore |
    update | keep_new | edit | deadline | cover | uncover | settle, n, keep_line, id, values, words, point, how, line}. Returns
    {ok, message, version, doc}; refusals raise RecordError. Every change first settles the record (#268: settle)."""
    doc = creaite_doc.read(path)
    if doc.get("state") == "approved":
        raise RecordError("These minutes are approved; their items are in the tracker. Change the items there.")
    p, data = proposal_for(doc)
    settled = settle(doc, data)                             # #268: after an Undo of the approve, the record follows its items first
    kind, n = op.get("op"), op.get("n")
    if kind in ("remove", "restore", "update", "keep_new", "edit", "deadline") and not isinstance(n, int):
        raise RecordError("Which item?")
    acts = {"remove": lambda: remove(doc, data, n, bool(op.get("keep_line"))), "restore": lambda: restore(doc, data, n),
            "update": lambda: update_that_one(doc, data, p, n, op.get("id")), "keep_new": lambda: keep_new(doc, data, p, n),
            "edit": lambda: edit_item(doc, data, n, dict(op.get("values") or {})),
            "deadline": lambda: edit_item(doc, data, n, {"due_words": op.get("words")}),
            "cover": lambda: cover(doc, data, str(op.get("point") or ""), op.get("how"), op.get("line", True) is not False),
            "uncover": lambda: uncover(doc, data, str(op.get("point") or "")),
            "settle": lambda: _settled_words(settled)}
    if kind not in acts:
        raise RecordError("That isn't a change the minutes know.")
    message = acts[kind]()
    data = save_proposal(p, data)
    for it in data.get("items") or []:                      # validate's flags (invalid, conflict) show on the rows
        if f"@{it['n']}" in doc["items"]:
            doc["items"][f"@{it['n']}"] = item_snapshot(it)
    r = save_record(path, doc, f"Minutes: {kind}", base_version=base_version, via=via)
    if r.get("needs_approval"):
        return r
    return {"ok": True, "message": message, "version": r["version"], "doc": creaite_doc.read(path)}



def _follow_record(p, data):
    """(stored path, record) of the draft minutes record whose items are staged in proposal `p`, or (None, None)."""
    draft = (data.get("meeting") or {}).get("draft")
    if not (draft and str(draft).startswith("system/staging/drafts/") and is_record(draft)):
        return None, None
    doc = creaite_doc.read(draft)
    if doc.get("state") == "approved" or (doc.get("meta") or {}).get("proposal") != p.name:
        return None, None
    return draft, doc


def _row_differs(doc, item):
    """Whether item's row on the record (its section, words and what it does) or its snapshot no longer matches the staged item."""
    s, i = find_row(doc, item["n"])
    sid, row = item_row(item)
    if (s is None) != (sid is None) or (s is not None and sid != s["id"]):
        return True
    had, row, old = (s["rows"][i] if s is not None else {}), row or {}, doc["items"][f"@{item['n']}"]
    return (had.get("cells"), had.get("does"), old.get("values"), old.get("changes")) != \
        (row.get("cells"), row.get("does"), item.get("values"), item.get("changes"))


def follow(proposal, via="dashboard"):
    """Review's edits reach the record: after a staged item is edited in Review (the dashboard's proposal save, review.py edit),
    each row the record shows follows its item (sync_item, as a change from the minutes view does), saved as a new version of the
    draft record. Only a draft record whose items are staged in this proposal, only rows whose words changed; returns the new
    version, or None when nothing needed to change. Never raises: Review's own save has already been made."""
    try:
        p = Path(proposal)
        p = p if p.is_absolute() else paths.STAGING / p.name
        data = json.loads(p.read_text(encoding="utf-8"))
        draft, doc = _follow_record(p, data)
        if not draft:
            return None
        changed = [it for it in data.get("items") or []
                   if not it.get("applied") and f"@{it.get('n')}" in doc["items"] and _row_differs(doc, it)]
        for item in changed:
            sync_item(doc, item)
        if not changed:
            return None
        r = save_record(draft, doc, "Minutes: edited in Review", via=via)
        return r.get("version") if r.get("ok") else None
    except (OSError, ValueError, KeyError, TypeError, RecordError, creaite_doc.DocError):
        return None             # a record that can't be read or saved stays as it was; Review's own save already stands

# ── The minutes view's routes (live_server.py /api/minutes/draft, save, export) ──

RECORD_PATH = re.compile(r"(?:system/staging/drafts|projects)/[^\x00]+\.html")


def record_at(path):
    """(stored path, the record) for a minutes record the view may open: a draft in system/staging/drafts/ or filed minutes in a
    project folder. Raises RecordError, also for a file that is a report by any sign (creaite_doc.report_signs; v2.5.1)."""
    rel = str(path or "")
    if not RECORD_PATH.fullmatch(rel) or ".." in Path(rel).parts or "\\" in rel:
        raise RecordError("Those aren't minutes creaite can open.")
    try:
        doc = creaite_doc.read(rel)
    except creaite_doc.DocError as e:
        raise RecordError(str(e)) from None
    if doc.get("kind") != "minutes" or _report_place(rel, doc):
        raise RecordError("That creaite document isn't a meeting's minutes.")
    signs = creaite_doc.report_signs(rel, doc)        # v2.5.1 (#239, e): a client report edited to say minutes is still a report
    if signs:
        raise RecordError("That file is a report, not minutes (" + "; ".join(signs) + "), so it isn't opened here.")
    return rel, doc


REPORT_NAME = re.compile(r" (?:Client|Weekly) report - ")


def _report_place(rel, doc):
    """v2.5.0: whether a path is a report's (a weekly or client report's file name, or a file in the project's reports folders),
    so a report edited on disk to say minutes is never opened or exported as minutes, beside itself and ungated."""
    if REPORT_NAME.search(Path(rel).name):
        return True
    try:
        here = creaite_doc.real(rel).resolve().parent
        return any(here == Path(paths.folder(doc.get("project"), creaite_doc.FOLDER[k])).resolve() for k in ("weekly", "client"))
    except (LookupError, OSError, KeyError, TypeError, AttributeError, ValueError):
        return False                  # no reports folder to be in (the portfolio's minutes); the name check above still ran


def view(file=None, path=None):
    """What the minutes view opens: the record, its versions, the transcript's turns for the pane, and (while its items are
    pending) the approve popup's plan. By the proposal's file name, or the record's stored path."""
    import review
    data = None
    if file:
        p = paths.STAGING / Path(str(file)).name
        if not re.fullmatch(r"proposed-[\w.-]+\.json", p.name) or not p.is_file():
            raise RecordError("That proposal is no longer pending.")
        data = json.loads(p.read_text(encoding="utf-8"))
        path = (data.get("meeting") or {}).get("draft")
        if not is_record(path):
            raise RecordError("These minutes aren't a minutes record: open them in Review.")
    rel, doc = record_at(path)
    if data is None and doc.get("state") == "draft":
        try:
            data = proposal_for(doc)[1]
        except RecordError:
            data = None
    meta = doc.get("meta") or {}
    labels = item_labels(doc)
    return {"ok": True, "path": rel, "doc": doc, "versions": creaite_doc.versions(rel), "turns": turns(meta.get("transcript")),
            "proposal": meta.get("proposal"), "plan": review.minutes_plan(data) if data and doc["state"] == "draft" else None,
            "labels": labels, "withheld": withheld(doc, labels),
            "settle": unsettled(doc, data) if data and doc["state"] == "draft" else []}


def save_page(path, page, base_version=None, via="dashboard"):
    """Save the page as Alan edited it (text, headings, order, hidden sections) as a new version. While the minutes are a draft the
    item rows stay as staged (they change only through `change`), and the record's items, meta and state are always kept."""
    rel, cur = record_at(path)
    if not isinstance(page, dict) or not isinstance(page.get("sections"), list):
        raise RecordError("Nothing to save.")
    out = {**cur, "sections": [], "layout": page.get("layout") if isinstance(page.get("layout"), dict) else cur.get("layout")}
    seen = set()
    for s in page["sections"]:
        if not isinstance(s, dict) or s.get("id") in seen:
            continue
        seen.add(s.get("id"))
        mine = section_of(cur, s.get("id"))
        if mine is not None and s.get("id") in COLUMNS and cur.get("state") == "draft":
            s = {**s, "rows": mine.get("rows") or [], "columns": mine.get("columns") or COLUMNS[s["id"]]}
        out["sections"].append(s)
    out["sections"] += [s for s in cur["sections"] if s.get("id") in COLUMNS and s["id"] not in seen]
    r = save_record(rel, out, "Minutes saved", base_version=base_version, via=via)
    return {**r, "doc": creaite_doc.read(rel)}


def export(path, fmt, file_beside=True, version="internal"):
    """An export of the minutes (HTML, Word or PDF) through creaite_doc.export (v2.1.0 P2, the contract's call). `version`
    "distributed" exports the distributed version instead (distributed_export)."""
    rel, doc = record_at(path)
    if fmt not in ("html", "docx", "pdf"):
        raise RecordError("Export as HTML, Word or PDF.")
    if version == "distributed":
        return distributed_export(rel, doc, fmt, file_beside)
    if version not in (None, "", "internal"):
        raise RecordError("Export the internal or the distributed version.")
    return creaite_doc.export(rel, fmt, file_beside=bool(file_beside), open_after=False, kind="minutes", doc=doc)   # one read, minutes only


def _followup_rows(use, doc, sid):
    """The rows of section `sid` in `use` that are new in the minutes (not an update, a closure or a record of an existing item)."""
    sec = next((s for s in use.get("sections") or [] if s.get("id") == sid), None) or {}
    out = []
    for r in sec.get("rows") or []:
        it = (doc.get("items") or {}).get(r.get("ref")) or {}
        if it.get("op", "new") == "new" and not str(r.get("does") or "").startswith(("Updates", "Closes", "Records")):
            out.append((r, it))
    return out


def _followup_items(use, doc):
    """[{k, id, t, ...}]: the new decisions, then the new actions, of the version `use`."""
    out = []
    for r, _ in _followup_rows(use, doc, "decisions"):
        c = r.get("cells") or {}
        if c.get("decision"):
            out.append({"k": "decisions", "id": str(r.get("ref") or ""), "t": c["decision"], "by": c.get("by") or ""})
    for r, it in _followup_rows(use, doc, "actions"):
        c, due = r.get("cells") or {}, str((it.get("values") or {}).get("due_date") or "")
        if c.get("action"):
            out.append({"k": "actions", "id": str(r.get("ref") or ""), "t": c["action"], "o": c.get("owner") or "",
                        "due": due if re.fullmatch(r"\d{4}-\d\d-\d\d", due) else None})
    return out


def _followup_text(use, sid):
    """A text section's words as one paragraph (no bullets or bold), empty for 'None recorded.'."""
    sec = next((s for s in use.get("sections") or [] if s.get("id") == sid), None) or {}
    words = " ".join(line_text(ln) for ln in str(sec.get("text") or "").splitlines() if ln.strip())
    return "" if words == "None recorded." else words


def _followup_names(use):
    """The attendees' names from the header section (no organisation in brackets)."""
    header = next((s for s in use.get("sections") or [] if s.get("id") == "header"), None) or {}
    raw = re.split(r"[;,]", str((header.get("data") or {}).get("attendees") or ""))
    return [n for n in (re.sub(r"\s*\([^)]*\)\s*", "", x).strip() for x in raw) if n]


def followup_facts(path, version="internal"):
    """The follow-up email's content from the version shown (v2.1.0 P7; Alan, 15-10-2026): the meeting, its summary, the new
    decisions and actions, and the attendees. The Distributed version is built by distributed_of, the one rule: no Internal only
    line or row, no Sensitive, partner-only or excluded item, so none of it can reach the draft. The Internal version is marked
    internal. Plain code; nothing is sent."""
    import drafts
    if version not in (None, "", "internal", "distributed"):
        raise RecordError("Draft from the internal or the distributed version.")
    rel, doc = record_at(path)
    dist = version == "distributed"
    held = withheld(doc)
    use = distributed_of(doc, held) if dist else doc
    summary = _followup_text(use, "summary")
    codes = (use.get("meta") or {}).get("projects") or [c for c in [use.get("project")] if c]
    return {"ok": True, "path": rel, "version": "distributed" if dist else "internal", "title": use.get("title") or "Meeting",
            "day": use.get("date") or "", "codes": codes,
            "summary": "" if drafts.secret(summary) else drafts.short(summary, 1500),
            "attendees": drafts.attendees_of({"attendees": [{"name": n, "email": ""} for n in _followup_names(use)]}),
            "items": _followup_items(use, doc), "left_out": len(held) if dist else 0, "marked_internal": not dist}


# ── The distributed version (BL-338 point 13; Jarvis, 15-10-2026 on plan #70) ──
# The view shows it as a preview (minutesDoc.js distributedOf); these build the same thing on the server, for its export. What it
# never holds: a line or row marked Internal only (layout.internal_only), and an item that is Sensitive, partner-only or carries a
# label that excludes it (its own flags and labels, and its tracker labels: client_leak.blocking_labels).

def _label_list(v):
    """Label names from a staged item's value: a list, or names separated by commas."""
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in str(v or "").split(",") if x.strip()]


def item_labels(doc, con=None):
    """{row ref: [label names]} for each item the record holds: the staged item's own labels, and the tracker's labels of the item
    it is (an update's ID, or a filed record's ID). Without a tracker, the item's own only."""
    import client_leak
    try:
        con = con or client_leak.connect()
    except (SystemExit, Exception):  # noqa: BLE001  no tracker (a fresh vault): the items' own labels still count
        con = None
    out = {}
    for ref, it in (doc.get("items") or {}).items():
        names = _label_list((it.get("values") or {}).get("labels")) + _label_list((it.get("changes") or {}).get("labels"))
        tid = it.get("id") or ("" if str(ref).startswith("@") else ref)
        if con is not None and tid:
            names += client_leak.labels_of(con, tid)
        out[ref] = sorted(set(names), key=str.lower)
    return out


def _blocking(con=None):
    """{label name in lower case: why} for every label that keeps an item out of the distributed version: Sensitive and the
    partner-only names always (by name), and the tracker's labels that exclude (client_leak.blocking_labels)."""
    import client_leak
    out = {client_leak.SENSITIVE: "Sensitive", **{n: "partner-only" for n in client_leak.PARTNER_ONLY}}
    try:
        out.update(client_leak.blocking_labels(con or client_leak.connect()))
    except (SystemExit, Exception):  # noqa: BLE001  no tracker: Sensitive and partner-only still block, by name
        pass
    return out


def _flagged_sensitive(item):
    """Whether a staged item's own flags or values say Sensitive."""
    return any(re.search("sensitive", str(f), re.I) for f in item.get("flags") or []) or bool((item.get("values") or {}).get("sensitive"))


def withheld(doc, labels=None, con=None):
    """{row ref: why} for each item the distributed version never shows: Sensitive (a flag, a value or a label), partner-only, or
    labelled with a label that excludes."""
    labels = item_labels(doc, con) if labels is None else labels
    blocking = _blocking(con)
    out = {}
    for ref, it in (doc.get("items") or {}).items():
        why = "Sensitive" if _flagged_sensitive(it) else next(
            (blocking[n.lower()] for n in labels.get(ref) or [] if n.lower() in blocking), None)
        if why:
            out[ref] = why
    return out


_TOPIC = re.compile(r"\*\*([^*]+)\*\*")
_FLAGGED = re.compile(r"\*\*([A-Z ]+)\*\* (.*)")


def line_text(raw):
    """A Markdown line's words as the view compares them (minutesDoc.js lines): no bullet, flag or bold."""
    s = raw.strip()
    t = _TOPIC.fullmatch(s)
    if t:
        return t.group(1)
    body = s[2:] if s[:2] in ("- ", "* ") else s
    f = _FLAGGED.fullmatch(body)
    if f and f.group(1) in FLAGS:
        body = f.group(2)
    return re.sub(r"\*([^*]+)\*", r"\1", re.sub(r"\*\*([^*]+)\*\*", r"\1", body))


def _without_lines(text, gone):
    """The Markdown without the lines whose words are in `gone`, blank runs closed up; "None recorded." when nothing is left."""
    kept = [raw for raw in str(text or "").split("\n") if not (raw.strip() and line_text(raw) in gone)]
    out = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
    return out or "None recorded."


def _distributed_table(s, marks, gone_refs):
    """A table section without the rows of withheld items or marked Internal only (a row marked as a draft, "@3", keeps its
    number once filed). Adds the refs it drops to `gone_refs`."""
    marked = {m["ref"] for m in marks if m.get("ref")}
    gone_refs |= {r["ref"] for r in s.get("rows") or [] if r.get("ref") in marked or f"@{r.get('n')}" in marked}
    s["rows"] = [r for r in s.get("rows") or [] if not (r.get("ref") and r["ref"] in gone_refs)]
    s["text"] = "" if s["rows"] else "None recorded."


def _distributed_text(s, marks):
    """A text section without the lines marked Internal only, and their tags."""
    gone = {m["text"] for m in marks if m.get("text")}
    if gone and s.get("text"):
        s["text"] = _without_lines(s["text"], gone)
        s["tags"] = [t for t in s.get("tags") or [] if line_text(str(t.get("text") or "")) not in gone]


def distributed_of(doc, held=None):
    """The distributed version of an internal minutes record (audience "distributed"), as the view's preview makes it: without the
    rows of withheld items or marked Internal only, the lines marked Internal only, their tags and the withheld items; based on
    the internal record. Nothing is written."""
    held = withheld(doc) if held is None else held
    marks = [m for m in (doc.get("layout") or {}).get("internal_only") or [] if isinstance(m, dict)]
    out = json.loads(json.dumps(doc))
    gone_refs = set(held)
    for s in out.get("sections") or []:
        mine = [m for m in marks if m.get("section") == s.get("id")]
        if s.get("type") == "table":
            _distributed_table(s, mine, gone_refs)
        elif s.get("type") != "header":
            _distributed_text(s, mine)
    return _without_items(out, gone_refs, doc.get("version"))


def _without_items(out, gone_refs, version):
    """The distributed record's last step: no tag or item for what it leaves out, no Internal only marks, its audience."""
    for s in out.get("sections") or []:
        if s.get("tags"):
            s["tags"] = [t for t in s["tags"] if t.get("ref") not in gone_refs]
    out["items"] = {k: v for k, v in (out.get("items") or {}).items() if k not in gone_refs}
    out["layout"] = {k: v for k, v in (out.get("layout") or {}).items() if k != "internal_only"}
    out.update(audience="distributed", based_on={"path": None, "version": version})
    return out


def distributed_export(rel, doc, fmt, file_beside=True):
    """Export the distributed version of the minutes at `rel`: the distributed record is built (distributed_of), written as a
    working copy in system/staging/drafts/ (`<name> (distributed).html`), exported through creaite_doc.export into the minutes'
    own folder (a create: never over a file, a taken name gets a number; Alan, 15-10-2026, option (c)), then the working copy goes.
    creaite_doc refuses it until the internal minutes are approved."""
    if (doc.get("audience") or "internal") != "internal":
        raise RecordError("Export the distributed version from the internal minutes.")
    dist = distributed_of(doc)
    dist["based_on"] = {"path": rel, "version": doc.get("version")}
    paths.DRAFTS.mkdir(parents=True, exist_ok=True)
    work = paths.free_path(paths.DRAFTS, f"{creaite_doc.real(rel).stem} (distributed)", ".html")
    work.write_text(creaite_doc.dumps(dist), encoding="utf-8")
    try:
        folder = str(Path(rel).parent) if file_beside else None
        out = creaite_doc.export(paths.rel(work), fmt, out_dir=folder, file_beside=False, open_after=False, kind="minutes")
    finally:
        work.unlink(missing_ok=True)
    return {**out, "version": "distributed"}
