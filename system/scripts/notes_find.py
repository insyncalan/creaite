"""creaite Find updates (BL-301 E): from a note to the tracker. A library the live server calls (`/api/notes/find`, `/api/notes/apply`,
`/api/notes/undo`); it has no command line, so no `reach.SCRIPT_COMMANDS` entry, and it never writes the database (tracker.py apply,
run by the live server, is the one writer) or a project file (a person or a memory line is a proposal's file operation, written at
apply and undone with it).

The engine is the one quick capture (cx-minutes) and cx-edit use, given a note as the source:
- `context(rel)`: the note's lines that are new or changed since the last Find updates (`notes.unsent`), the project's open items,
  milestones and people, and plain code's guesses at which lines may close an item (BL-218's passage candidates), as the prompt
  Claude answers with no tools (`notes-find-prompt.md`). Nothing to read: no model call.
- `rows(ctx, reply)`: Claude's rows checked by plain code. New items and updates go through cx-minutes' staging (`minutes.Staging`:
  the project, rejected before, already open, flags, workstreams; an open item's updatable fields and `based_on`), then the staging
  checks: repeats of an existing item (BL-221), probably-done evidence and its owner rule (BL-218), vague actions (BL-220). Every
  row is dry-run against the schema (`propose.check`); one that fails says why and starts unticked. The bulk rule sets the ticks:
  new risks, new decisions, milestone moves and health changes start unticked; routine rows start ticked. A hedged line ("probably",
  "might", "to confirm") never moves a milestone or changes health: that row is locked, and a confirm action linked to the milestone
  (its early warning) is proposed beside it.
- `stage(rel, sent, mode)`: the rows Alan ticked, checked again (the line must still be in the note as it was), written as one
  proposal (`source_run: "note"`): approved, for the live server to apply at once as one apply ("apply"), or pending for Review
  ("later"). Unticked rows are never staged.
- `record(rel, data, apply_id)`: what was applied or saved, in `system/staging/notes-sent.json` (paragraph, fingerprint, item IDs;
  never text), so the next Find updates looks only at new or changed lines; `forget(rel, apply_id)` after an Undo.

Each item's source is the note and its line: `projects/<folder>/08 Notes/<title>.md#p4`. A confidential note's new items are labelled
Sensitive. Never run unattended or by the sweep: only the panel beside a note calls it.
"""
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import notes  # noqa: E402
import tracker  # noqa: E402

PROMPT = "notes-find-prompt.md"
NOTE_LIMIT = 60000                         # characters of new lines sent to Claude (a note is far shorter)
HEDGE = re.compile(r"\b(?:probably|possibly|perhaps|maybe|might|could|likely|unlikely|hopefully|tentative(?:ly)?|"
                   r"to (?:be )?confirm(?:ed)?|tbc|tbd|not (?:yet )?confirmed|unconfirmed|subject to|pending confirmation|"
                   r"may(?!\s+\d))\b", re.I)
RAID_KINDS = {"risk": "Risk", "issue": "Issue", "assumption": "Assumption", "dependency": "Dependency"}
# What a note may change on an open item: cx-minutes' fields (BL-65), plus the owner (BL-301 E: "due date, done, owner, latest update")
NOTE_UPDATE = {"actions": ("status", "due_date", "latest_update", "owner"), "raid": ("status", "response_action", "due_date", "owner"),
               "decisions": ("status", "date", "made_by", "needed_by", "reasoning", "options", "revisit"),
               "promises": ("status", "due_date")}
PROJECT_FIELDS = ("sponsor", "phase")
GROUPS = ("new", "update", "milestone", "info")
LEVELS = ("Urgent", "High", "Medium", "Low")
ID_RE = re.compile(r"[A-Z][A-Z0-9]{2,6}-(?:[A-Z]-)?\d{3,}")
DAY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
TABLE_OF = {"A": "actions", "D": "decisions", "P": "promises", "M": "milestones"}


def table_of(item_id):
    """The table an item ID belongs to (ABC-A-001 actions, ABC-001 RAID, ABC-M-001 milestones…), or None."""
    m = re.fullmatch(r"[A-Z][A-Z0-9]{2,6}-(?:([A-Z])-)?\d{3,}", str(item_id or ""))
    if not m:
        return None
    return TABLE_OF.get(m.group(1)) if m.group(1) else "raid"


def today():
    """Today, YYYY-MM-DD (CREAITE_NOW fixes it in tests, as extraction does)."""
    import extraction
    return extraction.today()


def hedged(text):
    """The hedge word in a line ("probably"), or None. Plain code: a hedged line never moves a milestone or changes health."""
    m = HEDGE.search(text or "")
    return m.group(0).lower() if m else None


def me():
    """Alan's own name (settings identity), "" when it isn't set."""
    return (paths.load_settings().get("identity") or {}).get("name") or ""


def shown(d):
    """YYYY-MM-DD as DD-MM-YYYY (blank stays blank)."""
    return tracker.shown(d) if d else ""


def working_day_after(day, n):
    """The n-th working day after `day` (YYYY-MM-DD), weekends from settings."""
    off, d, left = tracker.weekend_days(), date.fromisoformat(day), n
    while left:
        d += timedelta(days=1)
        if d.weekday() not in off:
            left -= 1
    return d.isoformat()


# ── The note ─────────────────────────────────────────────────────────────────

def note_of(rel):
    """{rel, code, name, meta, body, day, confidential} for the stored note path `rel`, or {"refused": why}."""
    rel = str(rel or "").strip()
    if not rel.startswith("projects/") or ".." in Path(rel).parts or not rel.lower().endswith(".md"):
        return {"refused": "That isn't a note."}
    try:
        is_note = paths.is_note(rel)
    except (OSError, ValueError):
        is_note = False
    p = paths.resolve(rel)
    if not is_note or not p.is_file():
        return {"refused": "That note isn't there any more."}
    area = paths.project_area(rel)
    code = area[0] if area else ""
    if not code or code == "_portfolio":
        return {"refused": "Find updates works on a project's note. Move this note to its project first."}
    meta, body = notes.read(p)
    con = tracker.connect()
    try:
        row = con.execute("SELECT name, active FROM projects WHERE code = ?", (code,)).fetchone()
    finally:
        con.close()
    if row is None:
        return {"refused": "This note's project isn't in your project record."}
    when = str(meta.get("date") or "")
    return {"rel": rel, "code": code, "name": row["name"], "meta": meta, "body": body,
            "day": when if DAY_RE.fullmatch(when) else today(), "confidential": bool(meta.get("confidential")),
            "title": str(meta.get("title") or p.stem)}


def lines_of(note, only=None):
    """The note's lines to look at: new or changed since the last Find updates, or just line `only` (one line, BL-301 E's
    "from one line"). [(n, text)]."""
    if only:
        return [(n, t) for n, t in notes.paragraphs(note["body"]) if n == only]
    return notes.unsent(note["rel"], note["body"])


# ── The prompt ───────────────────────────────────────────────────────────────

def open_lines(con, code):
    """The project's open items as prompt lines: ID · title · owner · due."""
    import extraction
    items = extraction.open_items(con, code)
    items += [{"id": r["id"], "text": r["decision"], "owner": r["made_by"] or "", "due_date": r["needed_by"] or ""}
              for r in con.execute("SELECT id, decision, made_by, needed_by FROM decisions WHERE project = ? AND status = 'Pending'",
                                   (code,))]
    return [f"- {i['id']} · {i['text']} · {i.get('owner') or 'TBC'} · {i.get('due_date') or 'no date'}" for i in items] or ["- none"]


def project_context(con, code):
    """The open items, milestones and people the prompt lists, as text lines: IDs, titles, owners and dates (no other text)."""
    import extraction
    out = ["Open items (ID · title · owner · due):"] + open_lines(con, code) + ["Milestones (ID · name · forecast):"]
    ms = con.execute("SELECT id, name, forecast_date, baseline_date FROM milestones WHERE project = ? AND status = 'Planned' "
                     "ORDER BY sort_order, id", (code,)).fetchall()
    out += [f"- {m['id']} · {m['name']} · {m['forecast_date'] or m['baseline_date'] or 'no date'}" for m in ms] or ["- none"]
    p = dict(con.execute("SELECT health, sponsor, phase FROM projects WHERE code = ?", (code,)).fetchone())
    out.append(" ".join(f"{k.capitalize()}: {p[k] or 'not set'}." for k in ("health", "sponsor", "phase")))
    out.append("People register: " + (", ".join(x["name"] for x in extraction.people()) or "empty"))
    return "\n".join(out)


def context(rel, only=None):
    """What /api/notes/find needs before Claude is asked: {prompt, code, name, lines: [{p, fp}], skipped, confidential}, or
    {"nothing": why} (no model call) or {"refused": why}."""
    note = note_of(rel)
    if note.get("refused"):
        return note
    lines = lines_of(note, only)
    total = len(notes.paragraphs(note["body"]))
    if not lines:
        return {"nothing": "Nothing new in this note since the last Find updates." if total else "This note is empty.",
                "sent": total, **{k: note[k] for k in ("code", "name")}}
    import extraction
    con = tracker.connect()
    try:
        ctx = project_context(con, note["code"])
        hints = []
        for n, t in lines:
            for c in extraction.passage_candidates(con, note["code"], t):
                hints.append(f"- [p{n}] may close {c['id']} ({c['hint']}; plain code's guess: judge it)")
    finally:
        con.close()
    text = "\n".join(f"[p{n}] {t}" for n, t in lines)[:NOTE_LIMIT]
    prompt = (paths.TEMPLATES / PROMPT).read_text(encoding="utf-8").format(
        name=note["name"], today=f"{today()} ({date.fromisoformat(today()):%A})", title=note["title"], when=session_of(note),
        context=ctx + ("\nLines that may close an item:\n" + "\n".join(hints) if hints else ""), lines=text)
    return {"prompt": prompt, "code": note["code"], "name": note["name"], "confidential": note["confidential"],
            "lines": [{"p": n, "fp": notes.fingerprint(t)} for n, t in lines], "sent": total - len(lines)}


def session_of(note):
    """", a working session on 2026-10-13 with Omar Ali" for a Working session note; "" otherwise."""
    when, who = note["meta"].get("date"), note["meta"].get("with") or []
    if not when:
        return ""
    return f", a working session on {when}" + (f" with {', '.join(who)}" if who else "")


def parse_reply(reply):
    """Claude's rows: the `rows` list of the reply's JSON object (in a ```json block or bare); [] when there is none."""
    text = str(reply or "")
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    raw = m.group(1) if m else text[text.find("{"):text.rfind("}") + 1] if "{" in text else ""
    try:
        data = json.loads(raw)
    except ValueError:                    # not JSON: Claude answered in words, so there are no rows
        return []
    rows = data.get("rows") if isinstance(data, dict) else None
    return [r for r in rows if isinstance(r, dict)][:80] if isinstance(rows, list) else []


# ── Rows: Claude's answer checked by plain code ──────────────────────────────

class NoteStaging:
    """cx-minutes' staging (minutes.Staging) for one note: its project only, each item's source the note's line, and the mentions it
    would log collected instead (logged only for what Alan applies or saves)."""

    def __init__(self, note):
        import minutes

        class _S(minutes.Staging):
            def source_for(self, project, section, table):
                """The note and its line ("#p4")."""
                return f"{self.note}{section}"

            def mention(self, ids):
                """Collected, not logged: only what Alan applies or saves is logged (stage)."""
                self.mentioned.extend(ids)

        spec = {"date": note["day"], "title": note["title"], "note": note["rel"], "projects": [note["code"]]}
        self.s = _S(spec, f"note:{note['rel']}", "", {note["code"]: ("", "")}, {})
        self.s.mentioned = []
        self.note = note

    def take(self, raw):
        """One spec item through cx-minutes' staging: (items it gave, its note when it gave none)."""
        s = self.s
        s.items, s.updated, before = [], {}, len(s.notes)
        s.take(raw)
        return s.items, (s.notes[before:] or [""])[-1]

    def close(self):
        """Close the staging's two database connections."""
        self.s.con.close()
        self.s.rcon.close()


def clean(v, n=500):
    """A value from Claude or the page as one trimmed line of at most n characters."""
    return re.sub(r"\s+", " ", str(v if v is not None else "")).strip()[:n]


def day_or_none(v):
    """A YYYY-MM-DD date, or None."""
    v = clean(v, 10)
    return v if DAY_RE.fullmatch(v) else None


def action_spec(code, raw, title):
    """A new action's spec item."""
    v = {"project": code, "description": title, "owner": clean(raw.get("owner"), 80) or "TBC",
         "priority": raw.get("priority") if raw.get("priority") in LEVELS else "Medium"}
    if day_or_none(raw.get("due")):
        v["due_date"] = day_or_none(raw.get("due"))
    if table_of(clean(raw.get("milestone"), 20)) == "milestones":
        v["milestone"] = clean(raw.get("milestone"), 20)
    return {"table": "actions", "values": v}


def raid_spec(code, raw, title):
    """A new RAID item's spec item."""
    v = {"project": code, "type": RAID_KINDS[clean(raw.get("kind")).lower()], "description": title,
         "owner": clean(raw.get("owner"), 80) or "TBC"}
    v.update({f: raw[f] for f in ("impact", "likelihood") if raw.get(f) in ("High", "Medium", "Low")})
    return {"table": "raid", "values": v}


def decision_spec(code, raw, title):
    """A new decision's spec item: made, or needed (Pending) by a date."""
    status = "Pending" if raw.get("status") == "Pending" else "Made"
    v = {"project": code, "decision": title, "status": status}
    if clean(raw.get("made_by"), 80):
        v["made_by"] = clean(raw.get("made_by"), 80)
    if status == "Pending" and day_or_none(raw.get("needed_by")):
        v["needed_by"] = day_or_none(raw.get("needed_by"))
    return {"table": "decisions", "values": v}


def new_spec(code, raw):
    """A Claude row for a new action, RAID item or decision as a cx-minutes spec item, or None."""
    kind, title = clean(raw.get("kind")).lower(), clean(raw.get("title"), 300)
    make = action_spec if kind == "action" else raid_spec if kind in RAID_KINDS else decision_spec if kind == "decision" else None
    return make(code, raw, title) if make and title else None


def update_item(con, note, item_id, wanted, why, p):
    """An update to one open item of the note's project: (proposal item, None) or (None, why not). cx-minutes' checks (BL-65), with
    the owner allowed (a note is Alan's own)."""
    import minutes
    table = table_of(item_id)
    if table not in NOTE_UPDATE:
        return None, f"{item_id or 'that item'} can't be updated from a note"
    row = tracker.fetch(con, table, item_id)
    if row is None:
        return None, f"{item_id} isn't in the tracker"
    row = dict(row)
    if row["project"] != note["code"]:
        return None, f"{item_id} belongs to another project"
    if row["status"] not in minutes.STILL_OPEN[table]:
        return None, f"{item_id} is {row['status']}; only open items are updated"
    want = {k: clean(v) for k, v in (wanted or {}).items() if k in NOTE_UPDATE[table] and clean(v)}
    changes = {k: v for k, v in want.items() if v != (row.get(k) or "")}
    if any(k in tracker.DATE_FIELDS and not DAY_RE.fullmatch(v) for k, v in changes.items()):
        return None, "a date must be YYYY-MM-DD"
    changes = minutes.made_on(table, changes, note["day"])
    if not changes:
        return None, f"{item_id} is already as the note says"
    return {"op": "update", "table": table, "id": item_id, "changes": changes, "based_on": row["updated_at"], "why": clean(why, 300),
            "source": f"{note['rel']}#p{p}", "match": "strong", "flags": []}, None


def done_item(con, note, raw, p, line):
    """A probably-done update (BL-218): the item closed with its evidence, the strength after the owner rule (Alan wrote the note)."""
    import extraction
    item_id = clean(raw.get("id"), 20)
    table = table_of(item_id)
    if table not in ("actions", "raid", "promises"):
        return None, f"{item_id or 'that item'} can't be closed from a note"
    quote = clean(raw.get("quote"), 300) or clean(line, 300)
    strength = raw.get("strength") if raw.get("strength") in ("Looks done", "Maybe done") else "Maybe done"
    done = {"strength": strength, "quote": quote, "at": note["day"], "who": me()}
    changes = {"status": "Done" if table == "promises" else "Closed"}
    if table == "actions":
        changes["latest_update"] = f"Done: in the note “{note['title']}” ({shown(note['day'])}): “{quote}”"[:500]
    item, why = update_item(con, note, item_id, changes, "", p)
    if not item:
        return None, why
    extraction.mark_meeting_update(item, done)
    item["suggested"]["evidence"]["kind"] = "note"
    item["why"] = f"{item['suggested']['strength']}: “{quote}” ({shown(note['day'])})"
    return item, None


def person_row(raw):
    """A new person for the people register, or None (already in it, or no name)."""
    import propose
    name = clean(raw.get("name"), 80)
    if not name:
        return None
    people, _ = propose.people_pool()
    if propose.find_person(people, name):
        return None
    return {"name": name, "role": clean(raw.get("role"), 80), "org": clean(raw.get("org"), 80),
            "email": clean(raw.get("email"), 120)}


def memory_row(raw):
    """A line for the project memory, or None."""
    line = clean(raw.get("line"), 300)
    return {"section": clean(raw.get("section"), 40) or "Notes", "line": line} if line else None


def new_label(item):
    """A new item's type line ("Action · Omar Ali · due 19-10-2026") and its title."""
    t, v = item.get("table"), item.get("values") or {}
    bits = [v.get("type") or {"actions": "Action", "decisions": "Decision"}.get(t, t)]
    if t == "decisions":
        bits.append("needed" if v.get("status") == "Pending" else "made")
    bits.append(v.get("owner") or v.get("made_by") or "")
    due = v.get("due_date") or v.get("needed_by")
    bits.append(f"due {shown(due)}" if due else "")
    return " · ".join(b for b in bits if b), v.get("description") or v.get("decision") or ""


TITLE = {"milestones": "name", "actions": "description", "raid": "description", "promises": "description", "decisions": "decision"}


def label_for(item, note):
    """The row's type line and main text, as the panel shows them."""
    if item.get("op") == "new":
        return new_label(item)
    t = item.get("table")
    if t == "projects":
        return note["name"], ""
    con = tracker.connect()
    try:
        row = tracker.fetch(con, t, item["id"])
    finally:
        con.close()
    return f"{item['id']} · {row[TITLE[t]] if row is not None else ''}", ""


def changes_of(item):
    """[{f, label, from, to}] for an update, dates shown DD-MM-YYYY."""
    import propose
    if item.get("op") != "update":
        return []
    con = tracker.connect()
    try:
        row = tracker.fetch(con, item["table"], item["id"])
    finally:
        con.close()
    cur = dict(row) if row is not None else {}
    fmt = lambda f, x: shown(x) if f in tracker.DATE_FIELDS else clean(x, 300)      # noqa: E731
    done = "status" in item["changes"] and (item.get("suggested") or {}).get("feature") == "done"
    return [{"f": f, "label": propose.label(f), "from": fmt(f, cur.get(f)), "to": fmt(f, x)}
            for f, x in item["changes"].items() if f != "closed" and not (done and f == "latest_update")]


FIELDS = {   # what the panel lets Alan edit on a row before applying: (field, label, kind, options)
    "actions": [("description", "Title", "text", None), ("owner", "Owner", "person", None), ("due_date", "Due", "date", None),
                ("priority", "Priority", "enum", list(LEVELS))],
    "raid": [("description", "Title", "text", None), ("owner", "Owner", "person", None),
             ("impact", "Impact", "enum", ["High", "Medium", "Low"]), ("likelihood", "Likelihood", "enum", ["High", "Medium", "Low"])],
    "decisions": [("decision", "Decision", "text", None), ("made_by", "Made by", "person", None),
                  ("status", "Status", "enum", ["Made", "Pending"])],
}


def fields_for(item, kind):
    """The editable fields of a row: [{f, label, kind, options, part}]."""
    if kind == "person":
        return [{"f": f, "label": l, "kind": "text", "part": "person"}
                for f, l in (("name", "Name"), ("role", "Role"), ("org", "Organisation"))]
    if kind == "memory":
        return [{"f": "line", "label": "Memory line", "kind": "text", "part": "memory"}]
    if item.get("op") == "new":
        return [{"f": f, "label": l, "kind": k, "options": o, "part": "values"} for f, l, k, o in FIELDS.get(item["table"], [])]
    import propose
    return [{"f": f, "label": propose.label(f), "kind": "date" if f in tracker.DATE_FIELDS else "person" if f in ("owner", "made_by")
             else "text", "part": "changes"} for f in (item.get("changes") or {}) if f != "closed"]


FLAG_WORDS = {"no-owner": "No owner", "no-due-date": "No due date", "unknown-owner": "Owner not in the register",
              "new-workstream": "New workstream"}


def item_flags(item):
    """The staging checks' marks as the panel's flags: a repeat (BL-221), probably done (BL-218), a vague title (BL-220), and the
    item's own flags."""
    out, ll = [], item.get("looks_like")
    if ll:
        out.append({"t": f"Looks like {ll['id']}", "tone": "one" if ll["strength"] == "Very likely" else "soft",
                    "tip": f"{ll['strength']}: {ll['t']}"})
    if (item.get("suggested") or {}).get("feature") == "done":
        out.append({"t": "Probably done" if item["suggested"]["strength"] == "Looks done" else "Maybe done", "tone": "soft"})
    if any(x.get("field") == "description" for x in item.get("inferred") or []):
        out.append({"t": "Vague title", "tone": "soft", "tip": "Under four words or no verb: make it clearer before saving"})
    return out + [{"t": FLAG_WORDS[f], "tone": "soft"} for f in item.get("flags") or [] if f in FLAG_WORDS]


def finish(row, note):
    """The panel's view of a row: its group, label, changes, fields and flags (from the item)."""
    item, kind = row.get("item") or {}, row["kind"]
    flags = list(row.get("flags") or [])
    if kind == "person":
        row.update(group="info", type="People register · new person",
                   text=" · ".join(x for x in (item["person"]["name"], item["person"]["role"], item["person"]["org"]) if x))
    elif kind == "memory":
        row.update(group="info", type=f"Project memory · {item['memory']['section']}", text=f"“{item['memory']['line']}”")
    else:
        typ, text = label_for(item, note)
        row.update(type=typ, text=text, change=changes_of(item))
        row["group"] = ("new" if item.get("op") == "new" else "milestone" if item["table"] == "milestones"
                        else "info" if item["table"] == "projects" else "update")
        flags += item_flags(item)
        if item.get("why"):
            row.setdefault("notes", []).append(item["why"])
    row["flags"] = flags
    row["fields"] = fields_for(item, kind)
    return row


def bulk_tick(row):
    """The bulk rule: new risks, new decisions, milestone moves and health changes start unticked; routine rows start ticked."""
    item = row.get("item") or {}
    if row["kind"] in ("memory",):
        return False
    if item.get("op") == "new" and (item["table"] == "decisions" or (item.get("values") or {}).get("type") == "Risk"):
        return False
    if item.get("table") == "milestones" or (item.get("table") == "projects" and "health" in (item.get("changes") or {})):
        return False
    if (item.get("looks_like") or {}).get("strength") == "Very likely":
        return False                                                     # very likely a repeat: Alan decides
    return True


class Finder:
    """One Find updates run's rows from Claude's reply: each kind of row has its handler (`kind_<kind>`), which fills `row["item"]`
    and returns True to keep it, or marks it "left" (with why) or returns False to drop it."""

    def __init__(self, note, wanted):
        self.note, self.wanted = note, wanted
        self.lines = dict(notes.paragraphs(note["body"]))
        self.st, self.con = NoteStaging(note), tracker.connect()

    def close(self):
        """Close the database connections."""
        self.st.close()
        self.con.close()

    def row(self, i, raw):
        """One of Claude's rows checked, or None: only for a line that was sent, as it was sent."""
        try:
            p = int(raw.get("p"))
        except (TypeError, ValueError):
            return None
        if p not in self.wanted or notes.fingerprint(self.lines.get(p, "")) != self.wanted[p]:
            return None
        kind = clean(raw.get("kind")).lower()
        row = {"key": f"r{i + 1}", "p": p, "fp": self.wanted[p], "kind": kind, "notes": []}
        handler = getattr(self, f"kind_{'new' if kind in NEW_KINDS else kind}", None)
        return row if handler and handler(row, raw) else None

    def left(self, row, why):
        """A row plain code turned down: kept only to count it, with why."""
        row.update(kind="left", why=why)
        return True

    def kind_new(self, row, raw):
        """A new action, RAID item or decision, through cx-minutes' staging (an exact repeat becomes an update or is left)."""
        spec = new_spec(self.note["code"], raw)
        if not spec:
            return False
        items, why = self.st.take({**spec, "section": f"#p{row['p']}"})
        if not items:
            return self.left(row, why)
        row["item"] = items[0]
        row["kind"] = "update" if items[0]["op"] == "update" else row["kind"]
        row["notes"] += [clean(raw.get("why"), 200)] if clean(raw.get("why")) else []
        if ID_RE.fullmatch(clean(raw.get("related"), 20)):
            row["notes"].append(f"Linked to {clean(raw.get('related'), 20)}")
        ms = (items[0].get("values") or {}).get("milestone")
        row["notes"] += [f"Shows as an early warning on {ms} until it's done"] if ms else []
        return True

    def kind_update(self, row, raw):
        """A change to an open item."""
        item, why = update_item(self.con, self.note, clean(raw.get("id"), 20), raw.get("set"), raw.get("why"), row["p"])
        if not item:
            return self.left(row, why)
        row["item"] = item
        return True

    def kind_done(self, row, raw):
        """An open item the line says is finished (BL-218)."""
        item, why = done_item(self.con, self.note, raw, row["p"], self.lines[row["p"]])
        if not item:
            return self.left(row, why)
        row["item"] = item
        return True

    def kind_milestone(self, row, raw):
        """A milestone's forecast moving (locked later when the line is hedged)."""
        mid, fd = clean(raw.get("id"), 20), day_or_none(raw.get("forecast_date"))
        ms = tracker.fetch(self.con, "milestones", mid) if table_of(mid) == "milestones" else None
        if ms is None or ms["project"] != self.note["code"] or not fd or fd == ms["forecast_date"]:
            return False
        row["item"] = {"op": "update", "table": "milestones", "id": mid, "changes": {"forecast_date": fd}, "based_on": ms["updated_at"],
                       "why": clean(raw.get("why"), 300), "source": f"{self.note['rel']}#p{row['p']}", "match": "strong", "flags": []}
        row["ms"] = {"id": mid, "name": ms["name"]}
        return True

    def kind_health(self, row, raw):
        """The project's health changing (locked later when the line is hedged)."""
        if raw.get("health") not in HEALTH:
            return False
        reason = clean(raw.get("reason"), 300) or f"From the note “{self.note['title']}”"
        row["item"] = {"op": "update", "table": "projects", "id": self.note["code"],
                       "changes": {"health": raw["health"], "health_reason": reason}, "match": "strong", "flags": []}
        return True

    def kind_project(self, row, raw):
        """A project detail (sponsor, phase)."""
        ch = {k: clean(v, 120) for k, v in (raw.get("set") or {}).items() if k in PROJECT_FIELDS and clean(v)}
        row["item"] = {"op": "update", "table": "projects", "id": self.note["code"], "changes": ch, "match": "strong", "flags": []}
        return bool(ch)

    def kind_person(self, row, raw):
        """Someone new for the people register."""
        row["item"] = {"person": person_row(raw)}
        return bool(row["item"]["person"])

    def kind_memory(self, row, raw):
        """A line for the project memory."""
        row["item"] = {"memory": memory_row(raw)}
        return bool(row["item"]["memory"])


NEW_KINDS = ("action", "decision", *RAID_KINDS)
HEALTH = ("On track", "At risk", "Off track")


def rows(ctx, reply):
    """The panel's rows from Claude's reply, each checked by plain code: {rows, left, quiet, confidential, code, name}."""
    note = note_of(ctx["rel"])
    if note.get("refused"):
        return {"rows": [], "left": [], "quiet": 0, "message": note["refused"]}
    wanted = {x["p"]: x["fp"] for x in ctx.get("lines") or []}
    f = Finder(note, wanted)
    try:
        out = [r for r in (f.row(i, raw) for i, raw in enumerate(parse_reply(reply))) if r]
        out = hedge(out, f.lines, note)
        marks(out, note)
    finally:
        f.close()
    kept = [r for r in out if r["kind"] != "left"]
    validate(kept, note)
    for r in kept:
        finish(r, note)
        r["tick"] = bool(r.get("tick", bulk_tick(r))) and not r.get("lock")
    found, order = {r["p"] for r in kept}, {g: i for i, g in enumerate(GROUPS)}
    kept.sort(key=lambda r: (order.get(r["group"], 9), r["p"]))
    return {"rows": kept, "left": [{"p": r["p"], "why": r.get("why") or ""} for r in out if r["kind"] == "left"],
            "quiet": len([n for n in wanted if n not in found]), "confidential": note["confidential"], "code": note["code"],
            "name": note["name"]}


def moving(item):
    """Whether a row moves a milestone or changes health (what a hedged line may never do)."""
    return item.get("table") == "milestones" or (item.get("table") == "projects" and "health" in (item.get("changes") or {}))


def has_confirm(out, r, mid):
    """Whether Claude already gave a confirm action for this row's line (linked to the milestone, when there is one)."""
    return any(x is not r and x["p"] == r["p"] and (x.get("item") or {}).get("op") == "new" and x["item"]["table"] == "actions"
               and (not mid or (x["item"].get("values") or {}).get("milestone") == mid) for x in out)


def confirm_row(r, note):
    """The confirm action plain code proposes beside a hedged row: linked to the milestone (its early warning), Alan's own."""
    mid = (r.get("ms") or {}).get("id")
    what = f"the {r['ms']['name']} date ({shown(r['item']['changes'].get('forecast_date'))})" if mid else "the project's health"
    v = {"project": note["code"], "description": f"Confirm {what}", "owner": me() or "TBC", "priority": "Medium",
         "raised": note["day"], "due_date": working_day_after(today(), 2), "source": f"{note['rel']}#p{r['p']}"}
    v.update({"milestone": mid} if mid else {})
    return {"key": r["key"] + "c", "p": r["p"], "fp": r["fp"], "kind": "action",
            "notes": [f"Shows as an early warning on {mid} until it's done" if mid else "Proposed because the line is hedged"],
            "item": {"op": "new", "table": "actions", "values": v, "match": "strong", "flags": []}}


def hedge(out, lines, note):
    """A hedged line never moves a milestone or changes health: the row is locked (shown, unticked, Tentative), and a confirm action
    linked to the milestone is proposed beside it when Claude gave none."""
    extra = []
    for r in out:
        word = hedged(lines.get(r["p"])) if moving(r.get("item") or {}) else None
        if not word:
            continue
        r.update(lock="hedged", tick=False)
        r.setdefault("flags", []).append({"t": "Tentative", "tone": "one", "tip": f"“{word}”: confirm it first"})
        r["notes"].append(f"“{word}”: left unticked, and it can't be applied from here. A confirm action is proposed instead")
        if not has_confirm(out, r, (r.get("ms") or {}).get("id")):
            extra.append(confirm_row(r, note))
    return out + extra


def marks(out, note):
    """A confidential note's new items are labelled Sensitive (BL-301: "A Confidential note's items are marked Sensitive"), and the
    staging checks run: repeats (BL-221) and vague actions (BL-220)."""
    import extraction
    items = [r["item"] for r in out if (r.get("item") or {}).get("op") == "new"]
    if not items:
        return
    data = {"items": items}
    con = tracker.connect()
    try:
        extraction.mark_repeats(con, data, {"items": []})
    finally:
        con.close()
    extraction.mark_vague(data)
    if note["confidential"]:
        for it in items:
            if it["table"] in ("actions", "raid", "decisions"):
                it["values"]["labels"] = ["Sensitive"]
                it["values"]["label_reason"] = "From a confidential note"


def validate(kept, note):
    """Dry-run every row against the schema (propose.check, nothing written): a row that fails says why and stays unticked."""
    spec = spec_of(kept, note, "pending")
    import propose
    try:
        problems = propose.check(propose.complete(spec))
    except tracker.Invalid as e:                         # a file operation that can't stand
        problems = {None: ("invalid", str(e))}
    by_n = {it["n"]: r for it, r in zip(spec["items"], spec["_rows"])}
    for n, (_, reason) in problems.items():
        r = by_n.get(n)
        if r is not None:
            r["invalid"] = reason
            r["lock"] = r.get("lock") or "invalid"
            r["tick"] = False


# ── Staging: the ticked rows as one proposal ─────────────────────────────────

def memory_op(code, entries):
    """One write file operation for the project's CLAUDE.md: each line added at the end of its section (a section that isn't there
    is added at the end). None when there is no memory file."""
    try:
        target = paths.project_dir(code) / "CLAUDE.md"
    except LookupError:
        return None
    if not target.is_file():
        return None
    text = target.read_text(encoding="utf-8")
    for e in entries:
        lines = text.split("\n")
        head = next((i for i, ln in enumerate(lines) if ln.strip().lower() == f"## {e['section']}".lower()), None)
        add = f"- {e['line']}"
        if head is None:
            text = text.rstrip("\n") + f"\n\n## {e['section']}\n\n{add}\n"
            continue
        end = next((i for i in range(head + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        while end > head + 1 and not lines[end - 1].strip():
            end -= 1
        lines.insert(end, add)
        text = "\n".join(lines)
    return {"op": "write", "path": paths.rel(target), "content": text}


def people_op(entries):
    """One write file operation for the people register, adding each new person."""
    import propose
    text, _ = propose.people_register_text()
    people = propose.people_parse(text)
    for e in entries:
        if not propose.find_person(people, e["name"]):
            people.append({"name": e["name"], "email": e.get("email", ""), "org": e.get("org", ""), "role": e.get("role", ""),
                           "aliases": [], "hidden": False, "extra": {}})
    return {"op": "write", "path": paths.rel(paths.PEOPLE_REGISTER), "content": propose.people_text(text, people)}


def merged(items):
    """Two updates to one item in one proposal would conflict with each other: they become one (the later line's values win)."""
    out, seen = [], {}
    for it in items:
        if it.get("op") == "update" and (it["table"], it["id"]) in seen:
            first = seen[(it["table"], it["id"])]
            first["changes"] = {**first["changes"], **it["changes"]}
            first["why"] = " · ".join(x for x in (first.get("why"), it.get("why")) if x)
            continue
        if it.get("op") == "update":
            seen[(it["table"], it["id"])] = it
        out.append(it)
    return out


def spec_of(rows_in, note, decision):
    """The proposal for these rows: tracker items in order (n from 1) and one file-changes block for people and memory lines. Its
    `_rows` (dropped before writing) lines the items up with their rows."""
    items, rows_for, people, memory = [], [], [], []
    for r in rows_in:
        item = r.get("item") or {}
        if "person" in item:
            people.append(item["person"])
        elif "memory" in item:
            memory.append(item["memory"])
        elif item.get("op") in ("new", "update"):
            items.append(json.loads(json.dumps(item)))
            rows_for.append(r)
    keep, rows_kept = [], []
    for it, r in zip(items, rows_for):
        before = len(keep)
        keep = merged(keep + [it])
        if len(keep) > before:
            rows_kept.append(r)
    for n, it in enumerate(keep, 1):
        it.update(n=n, decision=decision, match="strong")
        it.setdefault("flags", [])
    spec = {"created": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), "source_run": "note", "files": [note["rel"]], "items": keep,
            "note": {"path": note["rel"]}, "_rows": rows_kept}
    ops = [op for op in ([people_op(people)] if people else []) + ([memory_op(note["code"], memory)] if memory else []) if op]
    if ops:
        spec["file_changes"] = {"title": f"From the note “{note['title']}”", "project": note["code"], "file_ops": ops,
                                "file_changes_decision": decision}
    return spec


def sent_row(con, note, r, by_fp, lines):
    """One row the page sent back, rebuilt: (row or None, why it can't be applied or None)."""
    key, fp, item = clean(r.get("key"), 20), clean(r.get("fp"), 20), r["item"]
    if fp not in by_fp:
        return None, "That line of the note has changed since: run Find updates again"
    p = by_fp[fp]
    if "person" in item or "memory" in item:
        kind = "person" if "person" in item else "memory"
        got = (person_row if kind == "person" else memory_row)(item[kind] if isinstance(item[kind], dict) else {})
        return ({"key": key, "p": p, "fp": fp, "item": {kind: got}} if got else None), None
    built, why = rebuild(con, note, item, p, lines[p])
    return ({"key": key, "p": p, "fp": fp, "item": built} if built else None), why


def check_sent(note, sent):
    """The rows the page sent back, checked against the note as it is now and rebuilt by plain code: (rows, problems by key)."""
    lines = dict(notes.paragraphs(note["body"]))
    by_fp = {notes.fingerprint(t): n for n, t in lines.items()}
    out, problems = [], {}
    con = tracker.connect()
    try:
        for r in [x for x in sent if isinstance(x, dict) and isinstance(x.get("item"), dict)] if isinstance(sent, list) else []:
            row, why = sent_row(con, note, r, by_fp, lines)
            if why:
                problems[clean(r.get("key"), 20)] = why
            elif row:
                out.append(row)
    finally:
        con.close()
    return out, problems


NEW_KEYS = {"type", "due_date", "needed_by", "milestone", "raised", "date", "workstream"}


def rebuild_new(note, item, src):
    """A new item from the page: only its own fields, the project and source set here, the dates defaulted as staging does."""
    table = item.get("table")
    v = {k: clean(x, 4000) for k, x in (item.get("values") or {}).items() if k in {f for f, *_ in FIELDS[table]} | NEW_KEYS}
    v.update(project=note["code"], source=src)
    if table == "raid" and v.get("type") not in RAID_KINDS.values():
        return None, "A RAID item needs its type"
    if table == "decisions":
        v.setdefault("status", "Made")
        v.update({"date": v.get("date") or note["day"]} if v["status"] == "Made" else {"date": ""})
    else:
        v.setdefault("raised", note["day"])
    out = {"op": "new", "table": table, "values": {k: x for k, x in v.items() if x not in ("", None)},
           "flags": [f for f in item.get("flags") or [] if f in ("no-owner", "no-due-date", "unknown-owner")]}
    if note["confidential"]:
        out["values"].update(labels=["Sensitive"], label_reason="From a confidential note")
    out.update({k: item[k] for k in ("looks_like", "inferred") if isinstance(item.get(k), (dict, list))})   # for Review, if saved
    return out, None


def rebuild_milestone(con, note, item_id, changes, item, src):
    """A milestone move from the page (never from a hedged line: checked before)."""
    ms = tracker.fetch(con, "milestones", item_id)
    fd = day_or_none(changes.get("forecast_date"))
    if ms is None or ms["project"] != note["code"] or not fd:
        return None, "That milestone can't be moved from this note"
    return {"op": "update", "table": "milestones", "id": item_id, "changes": {"forecast_date": fd},
            "based_on": clean(item.get("based_on"), 40) or ms["updated_at"], "source": src, "flags": []}, None


def rebuild_project(note, item_id, changes):
    """A project detail or health change from the page: this note's project only."""
    ch = {k: clean(x, 300) for k, x in changes.items() if k in PROJECT_FIELDS + ("health", "health_reason") and clean(x)}
    if item_id != note["code"] or not ch or ch.get("health", HEALTH[0]) not in HEALTH:
        return None, "Not a change creaite knows"
    return {"op": "update", "table": "projects", "id": item_id, "changes": ch, "flags": []}, None


def rebuild(con, note, item, p, line):
    """One tracker item from the page, rebuilt from its own fields: (item, None) or (None, why not)."""
    op, table, src = item.get("op"), item.get("table"), f"{note['rel']}#p{p}"
    if op == "new" and table in FIELDS:
        return rebuild_new(note, item, src)
    if op != "update":
        return None, "Not a change creaite knows"
    item_id, changes = clean(item.get("id"), 20), item.get("changes") if isinstance(item.get("changes"), dict) else {}
    if moving({"table": table, "changes": changes}) and hedged(line):
        return None, f"The line is hedged (“{hedged(line)}”): confirm it first, then change it on the milestone or the project"
    if table == "milestones":
        return rebuild_milestone(con, note, item_id, changes, item, src)
    if table == "projects":
        return rebuild_project(note, item_id, changes)
    built, why = update_item(con, note, item_id, changes, item.get("why"), p)
    if why:
        return None, why
    built["based_on"] = clean(item.get("based_on"), 40) or built["based_on"]
    built.update({"suggested": item["suggested"]} if isinstance(item.get("suggested"), dict) else {})
    return built, None


def file_rows(built):
    """The rows that are file changes (a person, a memory line)."""
    return [r for r in built if "person" in r["item"] or "memory" in r["item"]]


def refused(bad, spec, rows_kept, built):
    """The tracker's dry run's problems by row key (a file change's problem goes to every file row)."""
    by_n = {it["n"]: r["key"] for it, r in zip(spec["items"], rows_kept)}
    return {k: reason for n, (_, reason) in bad.items() for k in ([by_n[n]] if n in by_n else [r["key"] for r in file_rows(built)])}


def proposal_path():
    """A free name for the proposal: proposed-YYYY-MM-DD-HHMMSS-note.json."""
    stamp, out, i = f"{datetime.now():%Y-%m-%d-%H%M%S}", None, 1
    while out is None or out.exists():
        out = paths.STAGING / f"proposed-{stamp}{f'-{i}' if i > 1 else ''}-note.json"
        i += 1
    return out


def stage(rel, sent, mode):
    """Write the ticked rows as one proposal in system/staging/: approved ("apply", for the live server to apply at once) or pending
    ("later", for Review). {ok, file, items, files} or {ok: False, problems | message}."""
    import minutes
    import propose
    note = note_of(rel)
    if note.get("refused"):
        return {"ok": False, "message": note["refused"]}
    built, problems = check_sent(note, sent)
    if problems or not built:
        return {"ok": False, "problems": problems, "message": "Some rows can't be saved as they are" if problems else "Tick a row first"}
    spec = spec_of(built, note, "approved" if mode == "apply" else "pending")
    rows_kept = spec.pop("_rows")
    propose.complete(spec)
    propose.people_check_spec(spec)
    bad = propose.check(spec)
    if bad:
        return {"ok": False, "problems": refused(bad, spec, rows_kept, built),
                "message": "Some rows don't pass your project record's checks"}
    spec["note"]["rows"] = [{"n": it["n"], "p": r["p"], "fp": r["fp"]} for it, r in zip(spec["items"], rows_kept)]
    spec["note"]["files"] = [{"p": r["p"], "fp": r["fp"]} for r in file_rows(built)]
    out = proposal_path()
    paths.STAGING.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    mentioned = [it["id"] for it in spec["items"] if it["op"] == "update" and it["table"] in ("actions", "raid", "promises")]
    if mentioned:
        minutes.note_mention(mentioned, rel, "note", note["day"])            # BL-51: raised again, as cx-minutes logs it
    return {"ok": True, "file": out.name, "items": len(spec["items"]), "files": len((spec.get("file_changes") or {}).get("file_ops", []))}


def staged_proposal(name):
    """A note proposal by file name, applied or still in staging; {} when it can't be read."""
    f = paths.STAGING / "applied" / name
    f = f if f.is_file() else paths.STAGING / name
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):          # gone or unreadable: nothing to record
        return {}


def became(it):
    """The item ID a proposal item became: the new row's ID once applied, the updated row's ID, or None."""
    return it.get("result_id") or (it.get("id") if it.get("op") == "update" else None)


def record(rel, name, apply_id=None):
    """After an apply (or Save for later): what each line became, in notes-sent.json (paragraph, fingerprint, item IDs). The IDs of
    new items are read from the applied proposal (`result_id`); a pending one records its lines with the IDs it updates. Returns the
    IDs."""
    data = staged_proposal(name)
    meta = data.get("note") or {}
    lines = {notes.fingerprint(t): (n, t) for n, t in notes.paragraphs(note_of(rel).get("body") or "")}
    by_n = {it["n"]: it for it in data.get("items") or []}
    entries, ids = {r["fp"]: [] for r in meta.get("files") or []}, []
    for r in meta.get("rows") or []:
        got = became(by_n.get(r["n"]) or {})
        entries.setdefault(r["fp"], []).extend([got] if got else [])
        ids += [got] if got else []
    at = datetime.now().strftime("%Y-%m-%d %H:%M")
    notes.record_sent(rel, [(lines[fp][0], lines[fp][1], list(dict.fromkeys(x))) for fp, x in entries.items() if fp in lines], at,
                      apply_id=apply_id)
    return list(dict.fromkeys(ids))


def forget(rel, apply_id):
    """After an Undo: the lines that apply sent are new again (notes.forget_sent)."""
    return notes.forget_sent(rel, apply_id)
