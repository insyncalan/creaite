"""creaite Sneak peek (BL-322): read what Alan types about the one item open in the peek, in plain code.

The box in the peek sends its text here (POST /api/sneak/read, through the live server). This module reads it with no model call
and writes nothing: owners from the people register (two matches ask which one, none changes nothing), dates in Alan's words,
status, priority, impact and likelihood, workstream and milestone, labels, client-visible, revisit, the wording, a link, a
follow-on action, risk or promise, a chase hand-off, quick facts, where to go, and the parts only Claude can do (through the AI
drafts route). It answers with what it understood, the changes as from → to, the exact proposal items for the peek's own save
path, whether a confirm is needed, and anything refused with where to go instead. The staged items are tried in the tracker's
own dry run (the rules apply and record use), so what is offered is what an apply accepts. The contract is
dev/sprints/BL-322-contract.md.

  python3 system/scripts/sneak_peek.py read        JSON {id, text, picks} on stdin → the reading, as JSON (read only)

Set CREAITE_NOW="YYYY-MM-DD HH:MM" to fix the clock (tests).
"""
import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import tracker  # noqa: E402

KINDS = {"actions": "action", "raid": "raid", "decisions": "decision", "milestones": "milestone", "promises": "promise"}
TITLE = {"actions": "description", "raid": "description", "decisions": "decision", "milestones": "name", "promises": "description"}
TITLE_LABEL = {"actions": "Description", "raid": "Description", "decisions": "Decision", "milestones": "Name",
               "promises": "Description"}
DATE_FIELD = {"actions": ("due_date", "Due"), "raid": ("due_date", "Target"), "decisions": ("needed_by", "Needed by"),
              "milestones": ("forecast_date", "Forecast"), "promises": ("due_date", "Due")}
OWNER_FIELD = {"actions": ("owner", "Owner"), "raid": ("owner", "Owner"), "decisions": ("made_by", "Decision maker"),
               "milestones": ("owner", "Owner"), "promises": ("promised_by", "Promised by")}
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
NUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
LEVELS = ("Urgent", "High", "Medium", "Low")
MS_STATE_WORDS = {"achieved": "Achieved", "on track": "On track", "at risk": "At risk", "slipped": "Slipped",
                  "overdue": "Overdue", "late": "Overdue"}
POINT = {"draft_chase": "Draft email (C in the peek)", "ask": "ask creaite (one /), with this item attached",
         "cx_edit": "cx-edit in Claude Code", "milestone_form": "the milestone form", "project_page": "the project page",
         "settings": "Settings", "people": "Settings › People"}


def today():
    """Today as YYYY-MM-DD, or CREAITE_NOW's date in tests."""
    now = os.environ.get("CREAITE_NOW")
    return now[:10] if now else date.today().isoformat()


def day_of(iso):
    """A date from YYYY-MM-DD."""
    return date.fromisoformat(iso)


def shown_long(iso):
    """'Friday 16-10-2026'."""
    return f"{day_of(iso).strftime('%A')} {tracker.shown(iso)}" if iso else "none"


def u16(text, i):
    """A Python string index as a JavaScript (UTF-16) one."""
    return len(text[:i].encode("utf-16-le")) // 2


# ── dates in Alan's words ────────────────────────────────────────────────────

def _iso(y, m, d):
    """YYYY-MM-DD, or None for a date that doesn't exist (31-02)."""
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def _weekday(m, t):
    """"Friday" is the next Friday after today; "next Tuesday" is next week's Tuesday."""
    want = DAYS.index(m.group(2))
    if (m.group(1) or "").strip() == "next":
        return (t + timedelta(days=7 - t.weekday() + want)).isoformat()
    return (t + timedelta(days=(want - t.weekday()) % 7 or 7)).isoformat()


def _end_of_month(m, t):
    """The last day of this month."""
    return (date(t.year + (t.month == 12), t.month % 12 + 1, 1) - timedelta(days=1)).isoformat()


def _in_days(m, t):
    """"in 3 days", "in two weeks"."""
    n = NUM.get(m.group(1)) or int(m.group(1))
    return (t + timedelta(days=n * (7 if m.group(2) == "week" else 1))).isoformat()


def _day_month(m, t):
    """"20-10" (this year), "20-10-2026", "20/10/26"."""
    y = int(m.group(3)) if m.group(3) else t.year
    return _iso(2000 + y if y < 100 else y, int(m.group(2)), int(m.group(1)))


DATE_WORDS = [
    (re.compile(r"today"), lambda m, t: t.isoformat()),
    (re.compile(r"tomorrow"), lambda m, t: (t + timedelta(days=1)).isoformat()),
    (re.compile(r"(next\s+|this\s+)?(" + "|".join(DAYS) + r")"), _weekday),
    (re.compile(r"next week"), lambda m, t: (t + timedelta(days=7)).isoformat()),
    (re.compile(r"end of (?:the |this )?month"), _end_of_month),
    (re.compile(r"in\s+(\d+|a|an|one|two|three|four|five|six)\s+(day|week)s?"), _in_days),
    (re.compile(r"(\d{1,2})[-/.](\d{1,2})(?:[-/.](\d{2}|\d{4}))?"), _day_month),
    (re.compile(r"(\d{4})-(\d{2})-(\d{2})"), lambda m, t: _iso(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
]


def parse_date(words, base=None):
    """YYYY-MM-DD for a date in Alan's words, or None. `base` (YYYY-MM-DD) is today unless given."""
    t = day_of(base or today())
    s = re.sub(r"[.!]+$", "", str(words or "").strip().lower())
    s = re.sub(r"^the\s+", "", re.sub(r"^(?:on|to|for|by|is|until|till)\s+", "", s))
    for pattern, fn in DATE_WORDS:
        m = pattern.fullmatch(s)
        if m:
            return fn(m, t)
    return None


PUSH = re.compile(r"\b(?:push|move|slip|put)(?:\s+it)?\s+(out|back|forward|on)?\s*(?:by\s+)?(a|an|one|two|three|four|\d+)\s+"
                  r"(day|week)s?\b|\bbring(?:\s+it)?\s+forward\s+(?:by\s+)?(a|an|one|two|three|four|\d+)\s+(day|week)s?\b", re.I)


def shifted(m, base):
    """The date a "push it out a week" match makes from `base` (or today)."""
    if m.group(2):
        sign = -1 if (m.group(1) or "").lower() == "forward" else 1
        n, unit = NUM.get(m.group(2).lower()) or int(m.group(2)), m.group(3).lower()
    else:
        n, unit, sign = NUM.get(m.group(4).lower()) or int(m.group(4)), m.group(5).lower(), -1
    return (day_of(base or today()) + timedelta(days=sign * n * (7 if unit == "week" else 1))).isoformat()


# ── people ───────────────────────────────────────────────────────────────────

def people():
    """[{name, aliases, org, role, hidden}] from the people register, with Alan himself (settings identity) when missing."""
    try:
        import propose
        out = [{"name": p["name"], "aliases": p["aliases"], "org": p["org"], "role": p["role"], "hidden": p["hidden"]}
               for p in propose.people_parse(propose.people_register_text()[0])]
    except Exception:  # noqa: BLE001  no register yet: no one to match
        out = []
    me = me_name()
    if me and not any(p["name"].lower() == me.lower() for p in out):
        out.append({"name": me, "aliases": [], "org": "", "role": "", "hidden": False})
    return out


def me_name():
    """Alan's full name (settings identity)."""
    return str((paths.load_settings().get("identity") or {}).get("name") or "").strip()


def me_words():
    """The words that mean Alan: his name, his short forms, me, myself, I."""
    s = paths.load_settings().get("identity") or {}
    return {w.lower() for w in [s.get("name") or ""] + list(s.get("short_forms") or []) if w} | {"me", "myself", "i"}


def who(name, register, picks=None):
    """The register's full names a typed name could be: one is a match, two or more ask, none changes nothing."""
    n = " ".join(str(name or "").strip().lstrip("@").replace("’", "'").split()).strip(" .,!").lower()
    if not n:
        return []
    if picks and picks.get(n):
        chosen = str(picks[n])
        return [p["name"] for p in register if p["name"].lower() == chosen.lower()][:1]
    if n in me_words() and me_name():
        return [me_name()]
    exact = [p["name"] for p in register if p["name"].lower() == n]
    if exact:
        return exact
    alias = [p["name"] for p in register if n in (a.lower() for a in p["aliases"])]
    if alias:
        return sorted(set(alias))
    first = [p["name"] for p in register if not p["hidden"] and p["name"].lower().split()[0] == n]
    return first


# ── the item ─────────────────────────────────────────────────────────────────

def load_item(con, item_id):
    """(table, row as a dict) for an item ID, or (None, None) / (table, None) when it isn't one or isn't there."""
    table = tracker.item_table(item_id)
    if table not in KINDS:
        return None, None
    row = tracker.fetch(con, table, item_id)
    return table, dict(row) if row else None


def item_labels(con, item_id):
    """The item's labels, in the order they were added."""
    return [r[0] for r in con.execute("SELECT label FROM item_labels WHERE item_id = ? ORDER BY added_at, label", (item_id,))]


def title_of(con, item_id):
    """An item's own words (its description, decision or name), for a link's card."""
    table, row = load_item(con, item_id)
    return (row or {}).get(TITLE.get(table, "description")) or ""


def links_of(con, item_id):
    """[("blocks" | "blocked by", the other item's ID)] for an item."""
    return ([("blocks", r[0]) for r in con.execute("SELECT to_item FROM links WHERE from_item = ?", (item_id,))]
            + [("blocked by", r[0]) for r in con.execute("SELECT from_item FROM links WHERE to_item = ?", (item_id,))])


def source_path(src):
    """A vault-relative file the source names (the part before " — "), when it exists."""
    head = str(src or "").split(" — ")[0].split(" – ")[0].strip()
    if not head.startswith("projects/") or ".." in head:
        return None
    try:
        p = paths.resolve(head)
        return head if p.is_file() else None
    except Exception:  # noqa: BLE001
        return None


# ── the reading ──────────────────────────────────────────────────────────────

class Reading:
    def __init__(self, text, table, row, con, picks):
        """The reading so far, for one instruction on one item."""
        self.text, self.table, self.row, self.con, self.picks = text, table, row, con, picks or {}
        self.kind = KINDS[table]
        self.understood, self.changes, self.problems = [], [], []
        self.task = self.refused = self.choices = None
        self.needs_claude, self.confirm_why, self.offer_closing = False, [], False
        self.new_items = []                 # follow-on new items (each with its link)
        self.patch = {}                     # column → new value, on the open item
        self.register = None

    # helpers
    def mark(self, start, end, what):
        """Record a stretch of the text as understood."""
        self.understood.append({"start": start, "end": end, "what": what})

    def person(self, typed, field):
        """One full name for a typed name; two or more set `choices`, none adds a problem; None unless exactly one."""
        if self.register is None:
            self.register = people()
        if str(typed).strip().lower() in ("tbc", "nobody", "no one", "unassigned"):
            return "TBC" if self.table in ("actions", "raid") else None
        got = who(typed, self.register, self.picks)
        if len(got) == 1:
            return got[0]
        if len(got) > 1:
            org = {p["name"]: p for p in self.register}
            self.choices = {"field": field, "typed": " ".join(str(typed).split()).lstrip("@").lower(),
                            "options": [{"value": n, "label": " · ".join(x for x in (n, org[n]["org"] or org[n]["role"]) if x)}
                                        for n in got]}
            return None
        self.problems.append(f"No one called “{typed.strip()}” is in the people register, so nothing changes. "
                             "Add them in Settings › People first.")
        return None

    def change(self, field, label, to, span=None, what=None, confirm=False, to_shown=None, from_shown=None):
        """One change to the open item (the latest for a field wins); the same value again is a problem, not a change."""
        frm = self.row.get(field) if field != "labels" else item_labels(self.con, self.row["id"])
        if field != "labels" and frm == to:
            self.problems.append(f"{label} is already {to_shown or self.show(field, to)}.")
            return
        self.patch[field] = to
        row = {"field": field, "label": label, "from": frm, "to": to,
               "from_shown": from_shown if from_shown is not None else self.show(field, frm),
               "to_shown": to_shown if to_shown is not None else self.show(field, to, long=True), "confirm": confirm}
        self.changes = [c for c in self.changes if c["field"] != field] + [row]
        if span:
            self.mark(span[0], span[1], what or f"{label}: {row['to_shown']}")

    @staticmethod
    def show(field, v, long=False):
        """A stored value as the card shows it."""
        if v is None or v == "":
            return "none"
        if field in ("due_date", "needed_by", "forecast_date", "date", "baseline_date") and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)):
            return shown_long(v) if long else tracker.shown(v)
        if field == "client_visible":
            return "Yes" if int(v or 0) else "No"
        if field == "labels":
            return ", ".join(v) or "none"
        if field == "revisit" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)):
            return shown_long(v) if long else tracker.shown(v)
        return str(v)

    def refuse(self, why, point_to):
        """Refuse it, with where to go instead."""
        self.refused = {"why": why, "point_to": point_to}

    def date_field(self):
        """(column, label) of the item's own date."""
        return DATE_FIELD[self.table]


def _clauses(text, start, end):
    """(start, end) of each clause between start and end: split at commas, semicolons, " and ", " also "."""
    out, pos = [], start
    for m in re.finditer(r"\s*(?:[,;]|\band\b|\balso\b|\bthen\b)\s*", text[start:end], re.I):
        a, b = start + m.start(), start + m.end()
        out.append((pos, a))
        pos = b
    out.append((pos, end))
    trimmed = []
    for a, b in out:
        seg = text[a:b]
        lead = len(seg) - len(seg.lstrip())
        a2, b2 = a + lead, a + len(seg.rstrip())
        if b2 > a2:
            trimmed.append((a2, b2))
    return trimmed


LEAD = re.compile(r"^(?:(?:please|can you|could you|just)\s+)?(?:(?:change|set|update|make|move|put)\s+(?:it\s+)?)?(?:the\s+)?", re.I)


def read(con, item_id, text, picks=None):
    """The whole reading for one instruction on one item (the contract's reply), with no write."""
    table, row = load_item(con, item_id)
    if not row:
        return {"ok": False, "message": f"{item_id} isn't in the tracker."}
    raw = str(text or "")[:1000]
    r = Reading(raw, table, row, con, picks)
    if raw.strip():
        _read_whole(r, raw)
    return _answer(r)


# Whole-text readings first (each ends the reading); the clause readings after.

def _read_whole(r, raw):
    """The whole-text readings in order (each ends the reading), then the clauses."""
    t = raw.strip()
    s0 = len(raw) - len(raw.lstrip())
    low = t.lower().rstrip(".!")
    full = (s0, s0 + len(t))
    if _never(r, low, full):
        return
    for fn in (_promise, _chase, _goto, _facts, _question, _follow_on_action, _risk_from_action, _link, _draft, _decision_made,
               _withdraw, _reword, _revisit):
        if fn(r, raw, t, low, s0):
            return
    _read_clauses(r, raw, s0, s0 + len(t.rstrip(".!")))


NEVER_HEAD = re.compile(r":|\b(?:re(?:word|name|phrase)(?:\s+it)?|description|title|wording|decision)\s+(?:to|as)\b|\bbecause\b")
NEW_ITEM = re.compile(r"^(?:add|create|raise|log|new)\s+(?:a\s+|an\s+)?(?:follow[- ]?on\s+|new\s+)?(?:action|risk)\b|"
                      r"^i(?:'ve| have)?\s+promised\b")
NEVER = [   # (what it looks like, why, where to go instead); the first that matches is the answer
    (re.compile(r"^(?:please\s+)?(?:close|cancel|move|mark|set|change|update|reassign|assign|push|reopen|delete|make|chase)\b.*"
                r"\b(?:all|every|each|both)\b|\b(?:all|every|each)\s+(?:of\s+)?(?:the\s+|my\s+|[a-z]+'s\s+)?"
                r"(?:items?|actions?|overdue|risks?|issues?|decisions?|milestones?)\b"),
     "This box changes the one item that's open. For several items at once, ask creaite or say it in Claude Code (cx-edit).", "ask"),
    (re.compile(r"^(?!.*client (?:message|messaging|wording)).*\b(?:email|e-mail|mail|teams|send|message|ping|whatsapp|slack)\b"),
     "Nothing is ever sent from here. Draft chase writes the email for you to copy and send.", "draft_chase"),
    (re.compile(r"\b(?:health|rag|project details?|sponsor|phase)\b"),
     "That isn't part of this item. Health and project details are on the project page.", "project_page"),
    (re.compile(r"\bsettings?\b"), "Settings aren't changed from here.", "settings"),
    (re.compile(r"\b(?:people register|add (?:a )?person|new person)\b"), "The people register is changed in Settings › People.",
     "people"),
    (re.compile(r"\b(?:baseline|agreed date|rebaseline)\b"),
     "The baseline (agreed) date changes only in the milestone form, because a rebaseline also records a decision.", "milestone_form"),
    (re.compile(r"^(?:(?:change|set|move)\s+(?:it\s+)?(?:the\s+)?)?project\s+(?:to|is|=)|\bmove (?:it )?to (?:the )?project\b|"
                r"\bchange (?:the )?project\b"), "An item's project isn't changed here.", "cx_edit"),
    (re.compile(r"\b(?:change|set)\s+(?:the\s+)?(?:id|source|raised(?: date)?|closed date)\b|"
                r"^(?:id|source|raised|closed date)\s+(?:to|is|=)"),
     "The ID, source, raised and closed dates are kept as recorded.", "cx_edit"),
    (re.compile(r"^(?:delete|remove|erase|destroy)(?:\s+(?:it|this|the item|this item))?$"),
     "creaite never deletes an item from here. Cancel or withdraw it instead.", "cx_edit"),
]


def _never(r, low, full):
    """The Never list: refused with where to go instead. A new item's own words, and wording after a colon, are never read."""
    low = NEVER_HEAD.split(low)[0]
    if NEW_ITEM.match(low):
        return False
    hit = next(((why, where) for pattern, why, where in NEVER if pattern.search(low)), None)
    if not hit:
        return False
    r.refuse(*hit)
    r.mark(full[0], full[1], "Not in this box")
    return True


def _promise(r, raw, t, low, s0):
    """"I promised Tom the Northgate terms by Friday": a new promise by Alan, linked to this item."""
    m = re.match(r"^i(?:'ve|’ve| have)?\s+promised\s+(.+)$", t, re.I)
    if not m:
        return False
    rest = m.group(1)
    words = rest.split()
    name, body = None, None
    for n in (2, 1):
        if len(words) > n:
            cand = " ".join(words[:n])
            if who(cand, r.register or people()) or (r.picks and cand.lower() in r.picks):
                name, body = cand, " ".join(words[n:])
                break
    if name is None:
        name, body = words[0], " ".join(words[1:])
    body = re.sub(r"^(?:that\s+)?(?:i'd|i would|i will|i'll|to)\s+", "", body, flags=re.I)
    due = None
    dm = re.search(r",?\s+by\s+(.+)$", body, re.I)
    if dm:
        due = parse_date(dm.group(1))
        if not due:
            r.problems.append(f"“{dm.group(1)}” isn't a date creaite can read. Try Friday, next Tuesday, 20-10 or in 3 days.")
            return True
        body = body[:dm.start()]
    to = r.person(name, "promised_to")
    if not to:
        return True
    me = me_name() or "Alan"
    values = {"project": r.row["project"], "promised_by": me, "promised_to": to, "description": _cap(body.strip()),
              "status": "Open", "raised": today(), "source": _source(r)}
    if due:
        values["due_date"] = due
    _new(r, "promise", "promises", values, {"from_item": r.row["id"], "to_item": "@1"},
         f"Promise to {to}{' by ' + shown_long(due) if due else ''}", (s0, s0 + len(t)))
    return True


def _chase(r, raw, t, low, s0):
    """"chase Tom, firmer": hand over to Draft chase (BL-298) with the recipient and the tone. Nothing is sent."""
    m = re.match(r"^chase\s+(.+?)(?:[,\s]+(?:in\s+)?(?:a\s+|the\s+)?(first|second|firmer|firm|gentle|polite|friendly|stronger)"
                 r"(?:\s+(?:one|reminder|tone|time))?)?$", low)
    if not m:
        return False
    name = m.group(1).strip()
    if name in ("it", "this", "them", "up"):
        to = None
    else:
        to = r.person(name, "to")
        if not to:
            return True
    tone = {"first": 0, "gentle": 0, "polite": 0, "friendly": 0, "second": 1, "firmer": 2, "firm": 2, "stronger": 2}.get(m.group(2))
    r.task = {"kind": "chase", "pane": {"id": r.row["id"], "tone": tone, "to": to}}
    word = {0: "First", 1: "Second", 2: "Firmer"}.get(tone, "the tone from how often it was chased")
    r.mark(s0, s0 + len(t), f"Draft chase{(' to ' + to) if to else ''}, {word}. Nothing is sent")
    return True


def _goto(r, raw, t, low, s0):
    """"open the source", "show the milestone", "open the project"."""
    m = re.match(r"^(?:open|show|go to|take me to|jump to)\s+(?:me\s+)?(?:the\s+|its\s+)?(source|milestone|project)\b", low)
    if not m:
        return False
    what = m.group(1)
    if what == "source":
        r.task = {"kind": "goto", "target": "source", "ref": r.row.get("source") or "", "path": source_path(r.row.get("source"))}
    elif what == "project":
        r.task = {"kind": "goto", "target": "project", "ref": r.row["project"], "path": None}
    else:
        ms = r.row.get("milestone") if r.table in ("actions", "raid") else (r.row["id"] if r.table == "milestones" else None)
        if not ms:
            ms = next((i for _, i in links_of(r.con, r.row["id"]) if tracker.item_table(i) == "milestones"), None)
        if not ms:
            r.problems.append("This item has no milestone. Say “milestone to <its name>” to set one.")
            return True
        r.task = {"kind": "goto", "target": "milestone", "ref": ms, "path": None}
    r.mark(s0, s0 + len(t), f"Open the {what}")
    return True


def _facts(r, raw, t, low, s0):
    """Quick facts, read only: last chased, where it came from, what it blocks."""
    rows = None
    if re.search(r"\bchased\b|\blast chase", low):
        import drafts
        c = drafts.chase_counts().get(r.row["id"]) or {"n": 0, "last": ""}
        txt = "Not chased yet." if not c["n"] else \
            f"Chased {'once' if c['n'] == 1 else str(c['n']) + ' times'}, last on {tracker.shown(c['last'])}."
        topic, rows = "chased", [{"label": "Last chased", "text": txt}]
    elif re.search(r"where did (?:this|it) come from|what(?:'s| is) (?:the|its) source|who raised|when was (?:this|it) raised", low):
        raised = r.row.get("raised") or (r.row.get("date") if r.table == "decisions" else None)
        topic, rows = "source", [{"label": "Source", "text": r.row.get("source") or "Not recorded"}] + \
            ([{"label": "Raised", "text": tracker.shown(raised)}] if raised else [])
    elif re.search(r"what does (?:this|it) block|what(?:'s| is) (?:blocking|it blocked by|this blocked by)|blocked by\?$|"
                   r"what is (?:it|this) linked to|^links\??$|what(?:'s| is) linked", low):
        ls = links_of(r.con, r.row["id"])
        topic, rows = "links", ([{"label": f"{'Blocks' if k == 'blocks' else 'Blocked by'} {i}", "text": title_of(r.con, i)}
                                 for k, i in ls] or [{"label": "Links", "text": "Nothing links to this item."}])
    if rows is None:
        return False
    r.task = {"kind": "facts", "topic": topic, "rows": rows}
    r.mark(s0, s0 + len(t), "A question about this item (read only)")
    return True


def _question(r, raw, t, low, s0):
    """Any other question goes to ask creaite, with the item attached."""
    if t.endswith("?") or re.match(r"^(what|why|who|how|when|where|is|are|does|did|has|have|can|should|will|would)\b", low):
        r.refuse("That needs more than this item's own facts. ask creaite can answer it, with this item attached.", "ask")
        r.mark(s0, s0 + len(t), "A question for ask creaite")
        return True
    return False


def _due_tail(r, body):
    """(body without a trailing ", due Friday" / "by Friday", the date or None, a problem or None)."""
    m = re.search(r",?\s+(?:due|by)\s+(.+)$", body, re.I)
    if not m:
        return body, None, None
    d = parse_date(m.group(1))
    if not d:
        return body, None, f"“{m.group(1)}” isn't a date creaite can read. Try Friday, next Tuesday, 20-10 or in 3 days."
    return body[:m.start()], d, None


def _follow_on_action(r, raw, t, low, s0):
    """"add an action for Leo to confirm the test dates, due Friday": a new action that blocks this item."""
    m = re.match(r"^(?:add|create|raise|log|new)\s+(?:a\s+|an\s+)?(?:follow[- ]?on\s+|new\s+)?action\s+for\s+(.+?)\s+to\s+(.+)$", t, re.I)
    if not m:
        return False
    body, due, bad = _due_tail(r, m.group(2))
    if bad:
        r.problems.append(bad)
        return True
    owner = r.person(m.group(1), "owner")
    if not owner:
        return True
    settings = paths.load_settings()
    pr = (settings.get("defaults") or {}).get("new_action_priority") or "Medium"
    values = {"project": r.row["project"], "description": _cap(body.strip()), "owner": owner, "priority": pr,
              "status": "Open", "raised": today(), "source": _source(r)}
    if due:
        values["due_date"] = due
    _new(r, "action", "actions", values, {"from_item": "@1", "to_item": r.row["id"]},
         f"New action for {owner}{', due ' + shown_long(due) if due else ''}, blocking {r.row['id']}", (s0, s0 + len(t)))
    return True


def _risk_from_action(r, raw, t, low, s0):
    """"raise a risk that Northgate's test dates slip": a new risk (impact and likelihood Medium), from an action only."""
    m = re.match(r"^(?:raise|add|log|create|new)\s+(?:a\s+)?(?:new\s+)?risk\s+(?:that\s+|of\s+|about\s+)?(.+)$", t, re.I)
    if not m:
        return False
    if r.table != "actions":
        r.problems.append("A new risk is raised from an action. On this item, add a link to an existing risk instead "
                          "(“blocked by ABC-012”).")
        return True
    values = {"project": r.row["project"], "type": "Risk", "description": _cap(m.group(1).strip()), "owner": me_name() or "TBC",
              "impact": "Medium", "likelihood": "Medium", "status": "Open", "raised": today(), "source": _source(r)}
    _new(r, "risk", "raid", values, {"from_item": "@1", "to_item": r.row["id"]},
         f"New risk (impact and likelihood Medium), linked to {r.row['id']}", (s0, s0 + len(t)))
    return True


def _link(r, raw, t, low, s0):
    """"blocked by ABC-012", "this blocks ABC-M-003": a new link; both ends must exist."""
    m = re.match(r"^(?:this\s+|it\s+)?(?:is\s+|'s\s+)?(blocked by|blocks|is blocking|blocking|depends on|waits on|waiting on|"
                 r"waiting for)\s+([A-Za-z][A-Za-z0-9]{2,6}-(?:[A-Za-z]-)?\d{3})$", low)
    if not m:
        return False
    other = m.group(2).upper()
    if other == r.row["id"]:
        r.problems.append("An item can't block itself.")
        return True
    if not tracker.item_row(r.con, other):
        r.problems.append(f"There's no item {other} in the tracker. Check the ID.")
        return True
    blocks = m.group(1) in ("blocks", "is blocking", "blocking")
    a, b = (r.row["id"], other) if blocks else (other, r.row["id"])
    if r.con.execute("SELECT 1 FROM links WHERE from_item = ? AND to_item = ?", (a, b)).fetchone():
        r.problems.append(f"{a} already blocks {b}.")
        return True
    r.task = {"kind": "link", "from_item": a, "to_item": b, "other": {"id": other, "title": title_of(r.con, other)}}
    r.new_items.append({"op": "new", "table": "links", "values": {"from_item": a, "to_item": b, "source": _source(r)}})
    r.mark(s0, s0 + len(t), f"{'Blocks' if blocks else 'Blocked by'} {other}")
    return True


def _draft(r, raw, t, low, s0):
    """The Claude parts: client message, a decision's reasoning or options, tidy the update (AI drafts)."""
    import drafts
    req = None
    if re.match(r"^(?:write|draft|suggest)\s+(?:me\s+)?(?:a\s+|the\s+)?client\s+(?:message|messaging|wording)", low):
        req, feature, field = {"kind": "client", "id": r.row["id"]}, "client", "client_message"
        if r.table not in ("actions", "raid", "decisions"):
            r.problems.append("Client wording is drafted for actions, RAID items and decisions.")
            return True
    elif re.match(r"^(?:write|draft|suggest)\s+(?:me\s+)?(?:the\s+)?(reasoning|options)", low):
        field = re.match(r"^\w+\s+(?:me\s+)?(?:the\s+)?(reasoning|options)", low).group(1)
        if r.table != "decisions":
            r.problems.append("Only decisions have reasoning and options.")
            return True
        req, feature = {"kind": "thinking", "id": r.row["id"], "field": field}, "thinking"
    elif re.match(r"^(?:tidy|sharpen|improve|tighten|reword|polish)\s+(?:up\s+)?(?:the\s+)?(?:latest\s+)?update", low):
        if r.table != "actions":
            r.problems.append("Only actions have a latest update to tidy.")
            return True
        if not (r.row.get("latest_update") or "").strip():
            r.problems.append("There's no update to tidy yet.")
            return True
        req, feature, field = {"kind": "sneak-update", "id": r.row["id"], "mode": "tidy"}, "update", "latest_update"
    elif re.match(r"^(?:reasoning|options)\b", low):
        r.problems.append("Reasoning and options are drafted by Claude for you to check. Try “draft the reasoning”.")
        return True
    else:
        return False
    r.task = {"kind": "draft", "field": field, "draft_kind": req["kind"]}
    r.needs_claude = _claude(drafts, req, feature, f"Claude drafts the {field.replace('_', ' ')}; you choose Use this or Keep mine.")
    r.mark(s0, s0 + len(t), "Drafted by Claude")
    return True


def _claude(drafts, req, feature, why, optional=False):
    """needs_claude for a draft request, or why it can't be drafted when that AI draft is off."""
    if not drafts.enabled(feature):
        label = drafts.FEATURES.get(feature, (feature,))[0]
        return {"kind": req["kind"], "off": True, "optional": optional, "request": None,
                "why": f"AI drafts are off for “{label}” (Settings › General › AI drafts), so Claude can't draft this. "
                       "The plain-code changes still work."}
    return {"kind": req["kind"], "off": False, "optional": optional, "request": req, "why": why}


def _decision_made(r, raw, t, low, s0):
    """"Chris decided …", "decision made": Made, today's date and who made it (a confirm)."""
    if r.table != "decisions":
        return False
    m = re.match(r"^(?:decision\s+made|decided|made|mark\s+it\s+made|it(?:'s| is| was)\s+(?:been\s+)?(?:made|decided))"
                 r"(?:\s+by\s+(@?[^:,;-]+?))?\s*(?:[:,;-]\s*(.*))?$", t, re.I)
    by_typed, what = None, ""
    if m:
        by_typed, what = m.group(1), (m.group(2) or "").strip()
    else:
        m = re.match(r"^(.+?)\s+(?:has\s+)?decided\s*(?::|on\s+|to\s+(?:go\s+with\s+)?|that\s+)?\s*(.*)$", t, re.I)
        if not m or len(m.group(1).split()) > 3:
            return False
        by_typed, what = m.group(1), (m.group(2) or "").strip()
    if r.row.get("status") == "Made":
        r.problems.append("This decision is already made. To change it, record a new decision that replaces it (cx-edit).")
        return True
    by = r.row.get("made_by")
    if by_typed:
        by = r.person(by_typed, "made_by")
        if not by:
            return True
    if not by:
        r.problems.append("Who made it? Try “Chris decided …”.")
        return True
    span = (s0, s0 + len(t))
    r.change("status", "Status", "Made", span, "Decision made", confirm=True)
    r.change("date", "Date made", today(), confirm=True)
    if by != r.row.get("made_by"):
        r.change("made_by", "Made by", by, confirm=True)
    if what:
        r.change("decision", "Decision", _cap(what), confirm=True)
    r.confirm_why.append("Recording a decision as made")
    return True


def _withdraw(r, raw, t, low, s0):
    """"withdraw it": a decision withdrawn (a confirm)."""
    if not re.match(r"^withdraw(?:\s+it|\s+this|\s+the decision)?$", low):
        return False
    if r.table != "decisions":
        r.problems.append("Only a decision is withdrawn. Cancel an action or a RAID item instead.")
        return True
    r.change("status", "Status", "Withdrawn", (s0, s0 + len(t)), "Withdraw the decision", confirm=True)
    r.confirm_why.append("Withdrawing a decision")
    return True


def _reword(r, raw, t, low, s0):
    """"rename to …", "reword to …": the item's own words (a confirm, old and new side by side)."""
    m = re.match(r"^(?:(?:change|set)\s+)?(?:the\s+)?(?:description|title|wording|name|decision)\s+(?:to|as)\s+(.+)$", t, re.I) \
        or re.match(r"^re(?:word|name|phrase)(?:\s+it)?\s+(?:to|as)\s+(.+)$", t, re.I)
    if not m:
        return False
    field, label = TITLE[r.table], TITLE_LABEL[r.table]
    r.change(field, label, _cap(m.group(1).strip()), (s0, s0 + len(t)), f"Reword the {label.lower()}", confirm=True)
    r.confirm_why.append(f"Rewording the {label.lower()}")
    return True


def _revisit(r, raw, t, low, s0):
    """A decision's revisit: a date, or a condition in words."""
    m = re.match(r"^(?:set\s+)?(?:the\s+)?revisit\s*(?:to\s+|on\s+|at\s+|by\s+|date\s+|:\s*)?(.+)$", t, re.I)
    if not m:
        return False
    if r.table != "decisions":
        r.problems.append("Only decisions have a revisit.")
        return True
    words = m.group(1).strip()
    d = parse_date(words)
    if d:
        r.change("revisit", "Revisit", d, (s0, s0 + len(t)))
    elif re.match(r"^(?:if|when|once|after|unless)\b", words, re.I):
        r.change("revisit", "Revisit", "Revisit " + words[0].lower() + words[1:], (s0, s0 + len(t)))
    else:
        r.problems.append(f"“{words}” isn't a date creaite can read. Give a date (30-11) or a condition (“if adoption falls below 60%”).")
    return True


# ── clause by clause ─────────────────────────────────────────────────────────

STATE = re.compile(r"^\s*(?:set\s+)?(?:the\s+)?state\s+(?:to\s+|is\s+)?(achieved|on track|at risk|slipped|overdue|late)\s*$", re.I)


def _read_clauses(r, raw, start, end):
    """Tails first (an update, a response, a reason, a state with its reason, a push), then each clause."""
    reason = None
    m = re.search(r"(?:^|[\s,;])(?:add\s+(?:an?\s+)?(?:update|note)|update|note)\s*(?::|saying|that|-)\s*(.+)$", raw[start:end], re.I) \
        or re.search(r"(?:^|[\s,;])add\s+(?:an?\s+)?(?:closing\s+)?(?:update|note)\s+(.+)$", raw[start:end], re.I)
    update = None
    if m:
        a = start + m.start() + (1 if raw[start + m.start()] in " ,;" else 0)
        update = (raw[start + m.start(1):end].strip(), (a, end))
        end = start + m.start()
    m = re.search(r"(?:^|[\s,;])(?:mitigation|response|resolution|response action|validation|management)\s*(?::|to|is|=)\s*(.+)$",
                  raw[start:end], re.I)
    if m:
        a = start + m.start() + (1 if raw[start + m.start()] in " ,;" else 0)
        if r.table != "raid":
            r.problems.append("Only risks, issues, assumptions and dependencies have a response action.")
        else:
            r.change("response_action", "Response", _cap(m.group(1).strip()), (a, end))
        end = start + m.start()
    m = re.search(r"\s+because\s+(.+)$", raw[start:end], re.I)
    if m:
        reason = (m.group(1).strip(), (start + m.start() + 1, end))
        end = start + m.start()
    m = STATE.match(raw[start:end])
    if m:
        _ms_state(r, m.group(1).lower(), reason, (start, end))
        reason = None if r.table == "milestones" else reason
        end = start
    m = PUSH.search(raw[start:end])
    if m:
        field, label = r.date_field()
        d = shifted(m, r.row.get(field))
        r.change(field, label, d, (start + m.start(), start + m.end()))
        a, b = start + m.start(), start + m.end()
        _clauses_read(r, raw, [c for c in _clauses(raw, start, a)] + [c for c in _clauses(raw, b, end)])
    else:
        _clauses_read(r, raw, _clauses(raw, start, end))
    _tails(r, update, reason)


def _clauses_read(r, raw, spans):
    """Each clause read; one not understood is said in problems."""
    for a, b in spans:
        c = LEAD.sub("", raw[a:b].strip().rstrip(".!")).strip()
        if not c:
            continue
        if not _clause(r, c, c.lower(), (a, b)):
            r.problems.append(f"creaite didn't understand “{raw[a:b].strip()}”. Try owner to …, due Friday, close it, or "
                              "ask creaite for anything wider.")


def _reason(r, what, span, update):
    """A "… because" reason: an action's update says it (Claude may word it better), a milestone keeps it as its internal note;
    other kinds have nowhere to keep it. Returns the update to stage."""
    if r.table == "actions":
        moved = next((c for c in r.changes if c["field"] == "due_date"), None)
        st = next((c for c in r.changes if c["field"] == "status"), None)
        head = f"Due moved to {tracker.shown(moved['to'])}" if moved else (st["to"] if st else "")
        import drafts
        r.needs_claude = _claude(drafts, {"kind": "sneak-update", "id": r.row["id"], "mode": "reason", "text": what[:1500]},
                                 "update", "Claude can word the reason as the update; the update below already says it.",
                                 optional=True)
        r.mark(span[0], span[1], "The reason, in the update")
        return update or ((f"{head}: {_cap(what)}" if head else _cap(what)), None)
    if r.table == "milestones":
        r.change("internal_note", "Internal note", _cap(what), span, "The reason, as an internal note (never shown to the client)")
    else:
        r.problems.append(f"A {KINDS[r.table]} has no latest update in the tracker, so the reason isn't kept. "
                          "Put it in the response (“response: …”) if it belongs there.")
    return update


def _update(r, text, span):
    """The update typed, as the action's latest update: "Alan: … (DD-MM-YYYY)"."""
    if r.table != "actions":
        where = "response (“response: …”)." if r.table == "raid" else "item's own wording."
        r.problems.append(f"Only actions have a latest update. On a {'RAID item' if r.table == 'raid' else KINDS[r.table]}, "
                          f"put it in the {where}")
        return
    me_first = (me_name() or "Alan").split()[0]
    r.change("latest_update", "Latest update", f"{me_first}: {_cap(text.rstrip('.'))}. ({tracker.shown(today())})", span,
             "Add an update")


def _tails(r, update, reason):
    """The reason and the update typed at the end; an action closed with neither offers a closing update."""
    if reason:
        update = _reason(r, reason[0], reason[1], update)
    if update:
        _update(r, *update)
    st = next((c for c in r.changes if c["field"] == "status"), None)
    if r.table == "actions" and st and st["to"] in ("Closed", "Cancelled") and not update:
        r.offer_closing = True


def _ms_state(r, word, reason, span):
    """A milestone's state (a confirm), with the reason it needs when it is better than the dates suggest."""
    if r.table != "milestones":
        r.problems.append("Only milestones have a state.")
        return
    st = MS_STATE_WORDS[word]
    if st == "Achieved":
        r.change("status", "Status", "Done", span, "Mark it done (Achieved)", confirm=True)
        r.confirm_why.append("Changing a milestone's state")
        return
    sug = tracker.suggested_state({**r.row, **r.patch}, today())
    if tracker.MS_RANK[st] < tracker.MS_RANK[sug] and not reason:
        r.problems.append(f"“{st}” is better than the dates suggest ({sug}), so it needs a reason. Try: state {word} because …")
        return
    r.change("state", "State", st, span, f"State: {st}", confirm=True)
    if reason:
        r.change("state_reason", "Reason", _cap(reason[0]), reason[1], "The reason for the state", confirm=True)
    r.confirm_why.append("Changing a milestone's state")


def _clause(r, c, low, span):
    """One clause: True when it was read (a change, a problem or a refusal), False when it wasn't understood."""
    for fn in (_c_owner, _c_date, _c_status, _c_priority, _c_impact, _c_workstream, _c_milestone, _c_client, _c_label,
               _c_issue):
        got = fn(r, c, low, span)
        if got is not None:
            return got
    d = parse_date(low)                                   # a bare date ("Friday", "by 20-10") is the item's date
    if d:
        field, label = r.date_field()
        r.change(field, label, d, span)
        return True
    return False


def _c_owner(r, c, low, span):
    """Owner, decision maker, promised by or to: a full name from the people register."""
    m = re.match(r"^(?:owner|owned by|assignee|decision maker|made by|promised to|promised by)\s*(?:to|is|as|:|=)?\s*(.+)$", c, re.I) \
        or re.match(r"^(?:re)?assign(?:\s+it)?\s+to\s+(.+)$", c, re.I) or re.match(r"^give\s+(?:it\s+)?to\s+(.+)$", c, re.I) \
        or re.match(r"^(?:it'?s\s+)?(?:for|over to)\s+(@?\S+(?:\s+\S+)?)$", c, re.I) if not parse_date(low) else None
    if not m:
        return None
    field, label = OWNER_FIELD[r.table]
    if low.startswith("promised to"):
        if r.table != "promises":
            r.problems.append("Only a promise has someone it is promised to.")
            return True
        field, label = "promised_to", "Promised to"
    name = r.person(m.group(1), field)
    if name:
        r.change(field, label, name, span)
    elif r.choices:
        r.mark(span[0], span[1], f"{label}: which {m.group(1).strip()}?")
    return True


def _c_date(r, c, low, span):
    """The item's date (due, target, needed by, forecast) in Alan's words."""
    m = re.match(r"^(?:due(?:\s+date)?|deadline|date|target(?:\s+date)?|needed\s+by|forecast(?:\s+date)?|due\s+by|by)\s*"
                 r"(?:to|is|for|on|by|:|=)?\s*(.+)$", low)
    if not m:
        return None
    d = parse_date(m.group(1))
    if not d:
        r.problems.append(f"“{m.group(1)}” isn't a date creaite can read. Try Friday, next Tuesday, 20-10 or in 3 days.")
        return True
    field, label = r.date_field()
    r.change(field, label, d, span)
    return True


STATUS_WORDS = re.compile(r"^(?:status\s+(?:to\s+|is\s+|as\s+)?|mark\s+(?:it\s+)?(?:as\s+)?|it(?:'s| is)\s+)?"
                          r"(closed|close(?: it)?|done|complete(?:d)?|finished|achieved|cancel(?:led)?(?: it)?|delayed|"
                          r"open|re-?open(?:ed)?(?: it)?|drop(?:ped)?(?: it)?|pending)$")


STATUS_TO = {   # each kind's status for each kind of word; a word a kind lacks is refused with its own line
    "actions": {"close": "Closed", "cancel": "Cancelled", "delay": "Delayed", "open": "Open"},
    "raid": {"close": "Closed", "cancel": "Cancelled", "open": "Open"},
    "promises": {"close": "Done", "cancel": "Dropped", "open": "Open"},
    "milestones": {"close": "Done", "cancel": "Cancelled", "open": "Planned"},
}
STATUS_NOT = {"raid": {"delay": "A RAID item is open, closed or cancelled. Move its target date instead (“target next Friday”)."}}
STATUS_CONFIRM = {"milestones": "Changing a milestone's state", "promises": "Dropping a promise"}


def _status_word(w):
    """close, cancel, delay or open: what a status word means."""
    if re.match(r"clos|done|complet|finish|achiev", w):
        return "close"
    if w.startswith(("cancel", "drop")):
        return "cancel"
    return "delay" if w == "delayed" else "open" if "open" in w else "pending"


def _c_status(r, c, low, span):
    """Status: closed, done, cancelled, delayed, reopen, dropped, in each kind's own words."""
    m = STATUS_WORDS.match(low)
    if not m:
        return None
    if r.table == "decisions":
        r.problems.append("A decision is made or withdrawn. Try “Chris decided …” or “withdraw it”.")
        return True
    word = _status_word(m.group(1))
    st = STATUS_TO[r.table].get(word)
    if not st:
        r.problems.append(STATUS_NOT.get(r.table, {}).get(word) or f"A {KINDS[r.table]} can't be {m.group(1)}.")
        return True
    confirm = word == "cancel" or r.table == "milestones"
    r.change("status", "Status", st, span, f"Status: {st}", confirm=confirm)
    if confirm:
        r.confirm_why.append(STATUS_CONFIRM.get(r.table, "Cancelling it"))
    return True


def _c_priority(r, c, low, span):
    """An action's priority."""
    m = re.match(r"^(?:priority\s+(?:to\s+|is\s+|as\s+)?|it(?:'s| is)\s+)?(urgent|high|medium|low)(?:\s+priority)?$", low)
    if not m:
        return None
    if r.table != "actions":
        r.problems.append("A RAID item's priority comes from its impact and likelihood. Try “impact low” or “likelihood high”."
                          if r.table == "raid" else "Only actions have a priority.")
        return True
    r.change("priority", "Priority", m.group(1).capitalize(), span)
    return True


def _c_impact(r, c, low, span):
    """A RAID item's impact or likelihood, with the priority the tracker will work out."""
    m = re.match(r"^(impact|likelihood)\s+(?:to\s+|is\s+|:\s*)?(high|medium|low)$", low) \
        or re.match(r"^(high|medium|low)\s+(impact|likelihood)$", low)
    if not m:
        return None
    if r.table != "raid":
        r.problems.append("Only risks, issues, assumptions and dependencies have impact and likelihood.")
        return True
    a, b = m.group(1), m.group(2)
    field, val = (a, b) if a in ("impact", "likelihood") else (b, a)
    val = val.capitalize()
    before = tracker.priority(r.row.get("impact"), r.row.get("likelihood"))
    r.change(field, field.capitalize(), val, span)
    after = tracker.priority(r.patch.get("impact", r.row.get("impact")), r.patch.get("likelihood", r.row.get("likelihood")))
    r.changes = [x for x in r.changes if x["field"] != "priority"]
    if after != before:
        r.changes.append({"field": "priority", "label": "Priority", "from": before, "to": after, "from_shown": before or "none",
                          "to_shown": after or "none", "confirm": False, "derived": True})
    return True


def _c_workstream(r, c, low, span):
    """An active workstream of the item's project."""
    m = re.match(r"^(?:workstream\s+(?:to\s+|is\s+|:\s*)?(.+)|(?:in(?:to)?|to)\s+(?:the\s+)?(.+?)\s+workstream)$", c, re.I)
    if not m:
        return None
    if r.table not in ("actions", "raid"):
        r.problems.append("Only actions and RAID items have a workstream.")
        return True
    name = (m.group(1) or m.group(2)).strip()
    if name.lower() in ("none", "no workstream", "nothing"):
        r.change("workstream", "Workstream", None, span)
        return True
    rows = r.con.execute("SELECT name, status FROM workstreams WHERE project = ?", (r.row["project"],)).fetchall()
    hit = next((x for x in rows if x["name"].lower() == name.lower()), None)
    active = [x["name"] for x in rows if x["status"] == "Active"]
    if hit and hit["status"] == "Active":
        r.change("workstream", "Workstream", hit["name"], span)
    elif hit:
        r.problems.append(f"{hit['name']} is a closed workstream, so it can't take items.")
    else:
        r.problems.append(f"This project has no workstream called “{name}”." + (f" It has: {', '.join(active)}." if active else ""))
    return True


def _c_milestone(r, c, low, span):
    """A milestone of the item's project, by name or ID."""
    m = re.match(r"^milestone\s+(?:to\s+|is\s+|:\s*)?(.+)$", c, re.I)
    if not m:
        return None
    if r.table not in ("actions", "raid"):
        r.problems.append("Only actions and RAID items are put under a milestone.")
        return True
    name = m.group(1).strip()
    if name.lower() in ("none", "nothing", "no milestone"):
        r.change("milestone", "Milestone", None, span, to_shown="None")
        return True
    rows = r.con.execute("SELECT id, name FROM milestones WHERE project = ? AND status <> 'Cancelled'", (r.row["project"],)).fetchall()
    hit = [x for x in rows if x["id"].lower() == name.lower() or x["name"].lower() == name.lower()] \
        or [x for x in rows if name.lower() in x["name"].lower()]
    if len(hit) == 1:
        r.change("milestone", "Milestone", hit[0]["id"], span, f"Milestone: {hit[0]['name']}", to_shown=f"{hit[0]['id']} {hit[0]['name']}")
    elif hit:
        r.problems.append(f"“{name}” matches {len(hit)} milestones: {', '.join(x['name'] for x in hit)}. Name one.")
    else:
        r.problems.append(f"This project has no milestone called “{name}”.")
    return True


def _c_client(r, c, low, span):
    """Client-visible off (Enter) or on (a confirm, refused until the client message is complete)."""
    m = re.match(r"^(?:make\s+it\s+|it'?s\s+|turn\s+)?(not\s+client[- ]visible|internal(?:\s+only)?|hide (?:it )?from (?:the )?client|"
                 r"client[- ]visible(?:\s+(?:on|off))?|visible to (?:the )?client|client[- ]visible\s+off)$", low)
    if not m:
        return None
    w = m.group(1)
    on = ("client" in w or "visible" in w) and not w.startswith("not") and not w.endswith("off") and not w.startswith("hide")
    if not on:
        r.change("client_visible", "Client-visible", 0, span)
        return True
    if r.table == "promises":
        r.problems.append("A promise is never shown to the client.")
        return True
    shape = "decisions" if r.table in ("decisions", "milestones") else r.table
    if not tracker.message_complete(shape, r.row.get("client_message")):
        r.problems.append("To make it client-visible, the client message must be complete first. Say “write a client message” "
                          "and Claude drafts it, or write it in the peek.")
        if r.table in ("actions", "raid", "decisions"):
            import drafts
            r.needs_claude = _claude(drafts, {"kind": "client", "id": r.row["id"]}, "client",
                                     "Claude can draft the client message first.", optional=True)
        r.mark(span[0], span[1], "Client-visible: needs the client message first")
        return True
    r.change("client_visible", "Client-visible", 1, span, confirm=True)
    r.confirm_why.append("Making it client-visible")
    return True


LABEL_ADD = re.compile(r"^(?:add\s+(?:the\s+)?label|label(?:\s+it)?|tag(?:\s+it)?|mark\s+(?:it\s+)?(?:as\s+)?)\s*"
                       r"(?:as\s+|:\s*)?(.+)$", re.I)
LABEL_REMOVE = re.compile(r"^(?:remove|take\s+off|drop|clear|untag|unlabel)\s+(?:the\s+)?(.+?)(?:\s+label)?$|^not\s+(sensitive)$", re.I)


def _label_change(r, label, add, span):
    """Add or remove one label: the item's full set is staged (labels already changed in this instruction count)."""
    have = r.patch.get("labels", item_labels(r.con, r.row["id"]))
    if add == (label in have):
        r.problems.append(f"It's already labelled {label}." if add else f"It isn't labelled {label}.")
        return
    after = have + [label] if add else [x for x in have if x != label]
    sens = not add and label.lower() == "sensitive"
    r.change("labels", "Labels", after, span, f"{'Add' if add else 'Remove'} the label {label}", confirm=sens,
             to_shown=", ".join(after) or "none", from_shown=", ".join(item_labels(r.con, r.row["id"])) or "none")
    if sens:
        r.confirm_why.append("Removing Sensitive")


def _c_label(r, c, low, span):
    """Add a label (from the labels list), or remove one (removing Sensitive is a confirm)."""
    rm = LABEL_REMOVE.match(c)
    m = rm or LABEL_ADD.match(c)
    if not m:
        return None
    name = (m.group(1) or m.group(2) if rm else m.group(1)).strip()
    known = {x[0].lower(): x[0] for x in r.con.execute("SELECT name FROM labels")}
    if name.lower() not in known and not rm and low.startswith("mark"):
        return None                                   # "mark it done" is a status
    if r.table not in tracker.LABELLED:
        r.problems.append("Labels are put on actions, RAID items and decisions.")
    elif name.lower() not in known:
        r.problems.append(f"There's no label called “{name}”. Labels are managed in Settings › Labels.")
    else:
        _label_change(r, known[name.lower()], not rm, span)
    return True


def _c_issue(r, c, low, span):
    """"this has happened": a risk becomes an issue (a confirm); its response becomes the resolution."""
    if not re.match(r"^(?:make\s+it\s+an\s+issue|(?:an\s+)?issue\s+now|it\s+has\s+happened|this\s+has\s+happened|it'?s\s+happened|"
                    r"(?:turn|change)\s+(?:it\s+)?into\s+an\s+issue|type\s+(?:to\s+)?issue)$", low):
        return None
    if r.table != "raid" or r.row.get("type") != "Risk":
        r.problems.append("Only a risk can become an issue.")
        return True
    r.change("type", "Type", "Issue", span, "It has happened: the risk becomes an issue", confirm=True,
             to_shown="Issue (the response becomes its resolution)")
    r.confirm_why.append("A risk becoming an issue")
    return True


# ── new items and the answer ─────────────────────────────────────────────────

def _cap(s):
    """The text with a capital first letter."""
    s = str(s or "").strip()
    return s[:1].upper() + s[1:]


def _source(r):
    """A new item's source: who, from which item, and when."""
    return f"{me_name() or 'Alan'} (Sneak peek on {r.row['id']}), {today()}"


def _new(r, kind, table, values, link, what, span):
    """A new item and its link, as a task and two staged items."""
    r.task = {"kind": kind, "values": values, "link": link}
    r.new_items.append({"op": "new", "table": table, "values": values})
    r.new_items.append({"op": "new", "table": "links", "values": {**link, "source": _source(r)}, "new_ref": True})
    r.mark(span[0], span[1], what)


def _stage(r):
    """The proposal items: one update to the open item, then any new items, a link's `@n` set to its new item's place."""
    items = []
    if r.patch:
        changes = {k: v for k, v in r.patch.items()}
        upd = {"op": "update", "table": r.table, "id": r.row["id"], "changes": changes}
        if r.row.get("updated_at"):
            upd["based_on"] = r.row["updated_at"]
        items.append(upd)
    for it in r.new_items:                  # `@1` in a link names the new item before it: its place in this proposal
        it = json.loads(json.dumps(it))
        if it.pop("new_ref", False):
            for end in ("from_item", "to_item"):
                if it["values"][end] == "@1":
                    it["values"][end] = f"@{len(items)}"
            if r.task and r.task.get("link") is not None:
                r.task["link"] = {k: it["values"][k] for k in ("from_item", "to_item")}
        items.append(it)
    return items


def _dry_run(con, items):
    """The tracker's own dry run on the staged items (always rolled back): {n: reason} for each one it refuses."""
    data = {"items": [dict(it, n=i + 1, match="strong", flags=[], decision="approved") for i, it in enumerate(items)]}
    found = tracker.dry_run(con, json.loads(json.dumps(data)), "dashboard", only_approved=True)
    return {n: reason for n, (kind, reason) in found.items()}


def _checked(r):
    """The items to stage, tried in the tracker's dry run; [] when there is nothing, it is refused or a choice waits."""
    if r.refused or r.choices:
        return []
    items = _stage(r)
    if any(i["op"] != "new" and i.get("id") != r.row["id"] for i in items):       # never another existing item
        raise RuntimeError("Sneak peek staged a change to another item")
    bad = _dry_run(r.con, items) if items else {}
    if bad:
        r.problems += [f"The tracker won't take it: {why}" for why in bad.values()]
        return []
    return items


def _stage_label(r):
    """What the staged pill and the feed call it: "ABC-A-001 owner, due updated (Sneak peek)"."""
    names = list(dict.fromkeys(c["label"].lower() for c in r.changes if not c.get("derived")))
    bits = [f"{r.row['id']} {', '.join(names)} updated"] if names else []
    if r.new_items:
        kind = (r.task or {}).get("kind")
        bits.append(f"new {kind} linked to {r.row['id']}" if kind in ("action", "risk", "promise") else f"{r.row['id']} linked")
    return "; ".join(bits) + " (Sneak peek)"


def _answer(r):
    """The reply, as the contract (dev/sprints/BL-322-contract.md) sets it out."""
    items = _checked(r)
    stage = {"label": _stage_label(r), "items": items} if items else None
    understood = [{"start": u16(r.text, u["start"]), "end": u16(r.text, u["end"]), "what": u["what"]}
                  for u in sorted(r.understood, key=lambda x: x["start"])]
    row = r.row
    return {"ok": True,
            "item": {"id": row["id"], "kind": r.kind, "table": r.table, "project": row["project"], "title": row.get(TITLE[r.table]) or "",
                     "type": row.get("type") if r.table == "raid" else None, "updated_at": row.get("updated_at")},
            "by": "code", "understood": understood,
            "changes": [] if (r.refused or r.choices) else r.changes,
            "task": None if r.refused else r.task,
            "stage": stage,
            "confirm": {"why": "; ".join(dict.fromkeys(r.confirm_why))} if (r.confirm_why and stage) else False,
            "needs_claude": r.needs_claude, "choices": r.choices, "problems": list(dict.fromkeys(r.problems)),
            "refused": ({**r.refused, "where": POINT.get(r.refused["point_to"])} if r.refused else None),
            "offer_closing_update": bool(r.offer_closing and stage)}


def read_request(req):
    """The read route's work: {id, text, picks} → the reading (no write)."""
    if not isinstance(req, dict) or not isinstance(req.get("id"), str) or not isinstance(req.get("text"), str):
        return {"ok": False, "message": "Send {id, text}."}
    picks = req.get("picks") if isinstance(req.get("picks"), dict) else {}
    picks = {str(k).strip().lstrip("@").lower(): str(v) for k, v in picks.items() if isinstance(v, str)}
    item_id = req["id"].strip().upper()[:20]
    try:
        con = tracker.connect_or_raise()
    except tracker.NoDatabase as e:
        return {"ok": False, "message": f"No tracker yet ({e})."}
    try:
        return read(con, item_id, req["text"], picks)
    finally:
        con.close()


def main(argv):
    """The command line: `read` (JSON on stdin)."""
    cmd = argv[0] if argv else ""
    if cmd == "read":
        try:
            req = json.loads(sys.stdin.read() or "{}")
        except ValueError:
            req = None
        print(json.dumps(read_request(req), ensure_ascii=False))
        return 0
    print(__doc__.strip())
    return 2 if cmd else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
