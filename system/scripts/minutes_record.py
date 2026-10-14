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


NEEDS_CARD = ("Saving over filed minutes needs your approval, and creaite's approval card can't show a save made from this page "
              "yet, so nothing was changed. The filed minutes are as they were.")


def save_record(path, doc, why, base_version=None, via="dashboard"):
    """Save the record as a new version (creaite_doc.save, never with an approver: a save over filed minutes is sensitive and
    waits for Alan's approval card, BL-141). Returns creaite_doc's answer; its code-3 answer (needs approval) comes back as it is,
    with a plain message. Raises RecordError when it is refused."""
    r = creaite_doc.save(path, doc, why, base_version=base_version, via=via)
    if r.get("needs_approval"):
        return {**r, "message": NEEDS_CARD}
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
    gone = doc["meta"].get("removed", {}).pop(str(n), None)
    if item.get("decision") != "rejected" or item.get("decided_in") != "minutes":
        raise RecordError(f"Item {n} wasn't removed here.")
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
    return f"Item {n} is back."


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

def change(path, op, base_version=None, via="dashboard"):
    """Apply one change from the minutes view to the draft record and its proposal, then save both. `op` is {op: remove | restore |
    update | keep_new | edit | deadline | cover | uncover, n, keep_line, id, values, words, point, how, line}. Returns {ok, message,
    version, doc}; refusals raise RecordError."""
    doc = creaite_doc.read(path)
    if doc.get("state") == "approved":
        raise RecordError("These minutes are approved; their items are in the tracker. Change the items there.")
    p, data = proposal_for(doc)
    kind, n = op.get("op"), op.get("n")
    if kind in ("remove", "restore", "update", "keep_new", "edit", "deadline") and not isinstance(n, int):
        raise RecordError("Which item?")
    acts = {"remove": lambda: remove(doc, data, n, bool(op.get("keep_line"))), "restore": lambda: restore(doc, data, n),
            "update": lambda: update_that_one(doc, data, p, n, op.get("id")), "keep_new": lambda: keep_new(doc, data, p, n),
            "edit": lambda: edit_item(doc, data, n, dict(op.get("values") or {})),
            "deadline": lambda: edit_item(doc, data, n, {"due_words": op.get("words")}),
            "cover": lambda: cover(doc, data, str(op.get("point") or ""), op.get("how"), op.get("line", True) is not False),
            "uncover": lambda: uncover(doc, data, str(op.get("point") or ""))}
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


# ── The minutes view's routes (live_server.py /api/minutes/draft, save, export) ──

RECORD_PATH = re.compile(r"(?:system/staging/drafts|projects)/[^\x00]+\.html")


def record_at(path):
    """(stored path, the record) for a minutes record the view may open: a draft in system/staging/drafts/ or filed minutes in a
    project folder. Raises RecordError."""
    rel = str(path or "")
    if not RECORD_PATH.fullmatch(rel) or ".." in Path(rel).parts or "\\" in rel:
        raise RecordError("Those aren't minutes creaite can open.")
    try:
        doc = creaite_doc.read(rel)
    except creaite_doc.DocError as e:
        raise RecordError(str(e)) from None
    if doc.get("kind") != "minutes":
        raise RecordError("That creaite document isn't a meeting's minutes.")
    return rel, doc


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
    return {"ok": True, "path": rel, "doc": doc, "versions": creaite_doc.versions(rel), "turns": turns(meta.get("transcript")),
            "proposal": meta.get("proposal"), "plan": review.minutes_plan(data) if data and doc["state"] == "draft" else None}


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


def export(path, fmt, file_beside=True):
    """An export of the minutes (HTML, Word or PDF) through creaite_doc.export (v2.1.0 P2, the contract's call). Until P2 is on the
    branch it answers that it isn't there yet (a stub, never a guess at the format)."""
    rel, _doc = record_at(path)
    if fmt not in ("html", "docx", "pdf"):
        raise RecordError("Export as HTML, Word or PDF.")
    fn = getattr(creaite_doc, "export", None)
    if fn is None:
        return {"ok": False, "format": fmt, "stub": True,
                "message": "Exporting isn't in this version yet: it comes with creaite_doc.export (v2.1.0 P2)."}
    return fn(rel, fmt, file_beside=bool(file_beside), open_after=False)
