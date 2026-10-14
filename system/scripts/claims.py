"""creaite ask creaite claims check (BL-314, v1.9.1). Standard library only; plain code, never a model call.

Before an ask creaite reply is shown, the live server passes each finished block of its text through check(): every work-item ID
in it (ABC-A-001 actions, ABC-001 RAID, ABC-D-001 decisions, and milestones and promises) is looked up in the tracker through
tracker.py's own read functions (tracker.connect_or_raise, tracker.item_row, tracker.fetch: read only), and what the reply says
about it is compared with the record:
  - a title given beside the ID ("ABC-A-007 · Set up weekly cadence", "ABC-A-007: …", "ABC-A-007 (…)", a table's title column)
    that doesn't match is flagged inline: "(⚠ doesn't match the tracker: <real title>)";
  - an owner given beside it ("owner Omar", "· Omar Haddad", "(Sara Khan)", a table's owner column) that isn't the item's owner
    is corrected inline to the tracker's owner, saying what the reply had said;
  - an ID of a registered project that isn't in the tracker is flagged "(⚠ not in the tracker)".
A reply with no IDs, or whose claims all match, comes back unchanged. Text inside a ``` fence is left alone. Nothing is
written: the check reads the tracker and the people register, and only changes the words the panel shows.

  check(text, lookup=None, people=None) -> (text, findings)   findings: [{id, kind: title|owner|missing, said, real}]
"""
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402,F401  (the vault's locations, for tracker.py)

ID = re.compile(r"(?<![A-Za-z0-9-])([A-Z][A-Z0-9]{2,6})-(?:([ADMWP])-)?(\d{3})(?![0-9A-Za-z])")
TITLE_FIELD = {"actions": "description", "raid": "description", "decisions": "decision", "milestones": "name",
               "promises": "description"}
OWNER_FIELD = {"actions": "owner", "raid": "owner", "decisions": "made_by", "milestones": "owner", "promises": "promised_by"}
SEP = re.compile(r"^\s*(?:[·—–:]|-(?=\s))\s*")
STOP = re.compile(r"\s+[·—–|]\s+|\s+-\s+|\s*\(|\s*\[|;|\.\s|\.$|,\s*(?=(?:owner|owned|due|by|made|lead|status|priority|raised|"
                  r"open|closed|overdue)\b)|\s+(?=(?:owner|owned by|owned|due)\b[:\s])|\s*\|", re.I)
MARKER = re.compile(r"(?i:\b(?:owner|owned by|made by|lead|promised by|assigned to)\b)\s*[:\-–]?\s*\**"
                    r"([A-Z][\w'’.-]*(?:\s+[A-Z][\w'’-]*){0,2}|TBC)")
WRAP = "*_`\"'“”‘’ "
STOPWORDS = {"the", "and", "for", "with", "from", "into", "onto", "about", "a", "an", "of", "to", "on", "in", "at", "by", "or",
             "is", "be", "set", "get", "its", "their", "our", "your", "this", "that"}
TITLE_HEAD = re.compile(r"title|item|action|description|decision|risk|issue|what|name|summary|promise|milestone|subject", re.I)
OWNER_HEAD = re.compile(r"owner|who|made by|lead|promised by|assignee", re.I)
MAX_REAL = 140


def _plain(s):
    """Lower case, punctuation out, spaces collapsed."""
    return " ".join(re.sub(r"[^\w\s]", " ", str(s or "").lower().replace("…", " ")).split())


def _words(s):
    return [w for w in _plain(s).split() if len(w) > 2 and w not in STOPWORDS]


def title_matches(said, real):
    """True when the title a reply gave is the tracker's title, a shortening of it or a close paraphrase. Lenient on purpose:
    only a clearly different title is flagged."""
    a, b = _plain(said), _plain(real)
    if not a or not b or a in b or b in a:
        return True
    if SequenceMatcher(None, a, b).ratio() >= 0.6:
        return True
    words = _words(said)
    if not words:
        return True
    real_stems = {w[:5] for w in _words(real)}
    hit = sum(1 for w in words if w[:5] in real_stems)
    return hit / len(words) >= 0.5


def _person(name, people):
    """The register entry a name, alias or first name stands for (case-insensitive), or None."""
    n = _plain(name)
    if not n:
        return None
    for p in people or []:
        names = [_plain(p.get("name"))] + [_plain(a) for a in p.get("aliases") or []]
        if n in names or n == names[0].split(" ")[0]:
            return p
    return None


def owner_matches(said, real, people=None):
    """True when the owner a reply gave is the item's owner: the full name, the first name, or an alias in the register."""
    a, b = _plain(said), _plain(real)
    if not a or not b:
        return not a
    if a == b or a == b.split(" ")[0] or b in a:
        return True
    p = _person(real, people)
    return bool(p) and a in [_plain(x) for x in p.get("aliases") or []]


def _looks_owner(piece, people):
    """The piece names a person in the register (or TBC): an owner claim."""
    t = piece.strip(WRAP + ".,")
    if not t or len(t) > 40 or re.search(r"\d", t):
        return None
    if t.upper() == "TBC" or _person(t, people):
        return t
    return None


def _clean(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()[:MAX_REAL]


def tracker_lookup():
    """A lookup over the tracker's read functions, opened once per reply: id -> {table, title, owner} or None, plus
    whether a project code is registered. None when there is no database yet (nothing is checked)."""
    try:
        import tracker
        con = tracker.connect_or_raise()
    except Exception:  # noqa: BLE001  no database (or none readable): the reply is shown as it is
        return None
    cache = {}

    def look(item_id):
        """The item's table, title and owner, or None."""
        if item_id not in cache:
            row = tracker.item_row(con, item_id)
            t = tracker.item_table(item_id)
            cache[item_id] = None if row is None else {
                "table": t, "title": _clean(row[TITLE_FIELD[t]]), "owner": _clean(row[OWNER_FIELD[t]])}
        return cache[item_id]

    def project(code):
        """Whether the code is a registered project."""
        if code not in cache:
            cache[code] = tracker.fetch(con, "projects", code) is not None
        return cache[code]

    look.project, look.close = project, con.close
    return look


def _register():
    try:
        import extraction
        return extraction.people()
    except Exception:  # noqa: BLE001  no register: owners are compared as written
        return []


# ── one line of text ─────────────────────────────────────────────────────────────

def _after_id(line, end, stop_at):
    """Where a title claim starts after the ID ending at `end`, and how it is closed: (start, closer) or (None, None)."""
    rest = line[end:stop_at]
    i = 0
    while i < len(rest) and rest[i] in "*`_":
        i += 1
    if rest[i:i + 2] == "](":                            # a link: [ABC-A-003](…)
        j = rest.find(")", i)
        i = j + 1 if j >= 0 else i
    while i < len(rest) and rest[i] in "*`_]":
        i += 1
    m = SEP.match(rest[i:])
    if m:
        return end + i + m.end(), None
    p = re.match(r"\s*\(", rest[i:])
    if p:
        return end + i + p.end(), ")"
    return None, None


def _title_span(line, start, closer, stop_at):
    """The (start, end) of the title text the reply gave, trimmed of markdown."""
    seg = line[start:stop_at]
    if closer:
        j = seg.find(closer)
        seg = seg[:j] if j >= 0 else seg
        k = re.search(r",|;|\s+[·—–]\s+", seg)
        seg = seg[:k.start()] if k else seg
    else:
        k = STOP.search(seg)
        seg = seg[:k.start()] if k else seg
    a = 0
    while a < len(seg) and seg[a] in WRAP:
        a += 1
    b = len(seg)
    while b > a and seg[b - 1] in WRAP + ".,:":
        b -= 1
    return start + a, start + b


def _owner_claim(line, start, stop_at, people):
    """(start, end, name) of an owner the reply gave in line[start:stop_at], or None."""
    seg = line[start:stop_at]
    m = MARKER.search(seg)
    if m:
        name = m.group(1).rstrip(".,")
        return start + m.start(1), start + m.start(1) + len(name), name
    pos = 0
    for piece in re.split(r"([·—–|(),;]|\s-\s)", seg):
        name = _looks_owner(piece, people) if piece and piece not in "·—–|(),;" else None
        if name:
            a = start + pos + piece.index(name)
            return a, a + len(name), name
        pos += len(piece)
    return None


def _check_line(line, look, people, found):
    """The line with its claims checked; findings appended to `found`."""
    if line.lstrip().startswith("|"):
        return line                                       # table rows are checked with their table
    ids = list(ID.finditer(line))
    edits = []                                            # (start, end, replacement), applied right to left
    for n, m in enumerate(ids):
        item_id, nxt = m.group(0), (ids[n + 1].start() if n + 1 < len(ids) else len(line))
        real = look(item_id)
        if real is None:
            if look.project(m.group(1)):
                edits.append((m.end(), m.end(), " (⚠ not in the tracker)"))
                found.append({"id": item_id, "kind": "missing", "said": "", "real": ""})
            continue
        start, closer = _after_id(line, m.end(), nxt)
        tail = m.end()
        if start is not None:
            a, b = _title_span(line, start, closer, nxt)
            said = line[a:b]
            if len(_plain(said)) >= 3 and not _looks_owner(said, people):
                if not title_matches(said, real["title"]):
                    edits.append((b, b, f" (⚠ doesn't match the tracker: {real['title']})"))
                    found.append({"id": item_id, "kind": "title", "said": said, "real": real["title"]})
                tail = b
        oc = _owner_claim(line, tail, nxt, people)
        if oc and real["owner"] and not owner_matches(oc[2], real["owner"], people):
            edits.append((oc[0], oc[1], f"{real['owner']} (corrected from the tracker: the reply said {oc[2]})"))
            found.append({"id": item_id, "kind": "owner", "said": oc[2], "real": real["owner"]})
    for a, b, rep in sorted(edits, key=lambda e: e[0], reverse=True):
        line = line[:a] + rep + line[b:]
    return line


# ── a markdown table ─────────────────────────────────────────────────────────────

def _cells(row):
    """A table row's cells, without the outer pipes."""
    s = row.strip()
    s = s[1:] if s.startswith("|") else s
    s = s[:-1] if s.endswith("|") else s
    return s.split("|")


def _join(row, cells):
    lead = row[:len(row) - len(row.lstrip())]
    return lead + "|" + "|".join(cells) + "|"


def _table_title(cells, i, m, head, owner_col):
    """(what the row says the title is, the cell it is in) for the ID in cells[i], or ("", None)."""
    rest = cells[i][m.end():].strip(WRAP)
    if rest and len(_plain(rest)) >= 3:
        return re.sub(r"^\s*[·—–:-]\s*", "", rest).strip(WRAP), i
    col = next((j for j, h in enumerate(head) if j != i and j != owner_col and TITLE_HEAD.search(h)), None)
    if col is not None and col < len(cells):
        return cells[col].strip().strip(WRAP), col
    return "", None


def _table_row(cells, head, owner_col, look, people, found):
    """One row's cells with its claims checked (in place); True when anything changed."""
    hit = next(((i, ID.search(c)) for i, c in enumerate(cells) if ID.search(c)), None)
    if not hit:
        return False
    i, m = hit
    item_id, real = m.group(0), look(m.group(0))
    if real is None:
        if not look.project(m.group(1)):
            return False
        cells[i] = cells[i].rstrip() + " (⚠ not in the tracker) "
        found.append({"id": item_id, "kind": "missing", "said": "", "real": ""})
        return True
    n = len(found)
    said, where = _table_title(cells, i, m, head, owner_col)
    if where is not None and len(_plain(said)) >= 3 and not title_matches(said, real["title"]):
        cells[where] = cells[where].rstrip() + f" (⚠ doesn't match the tracker: {real['title'].replace('|', '/')}) "
        found.append({"id": item_id, "kind": "title", "said": said, "real": real["title"]})
    said_o = cells[owner_col].strip().strip(WRAP) if owner_col is not None and owner_col < len(cells) and owner_col != i else ""
    if said_o not in ("", "—", "-") and real["owner"] and not owner_matches(said_o, real["owner"], people):
        cells[owner_col] = f" {real['owner']} (corrected from the tracker: the reply said {said_o.replace('|', '/')}) "
        found.append({"id": item_id, "kind": "owner", "said": said_o, "real": real["owner"]})
    return len(found) > n


def _check_table(rows, look, people, found):
    """The table's rows with their claims checked, by its header's title and owner columns."""
    head = [c.strip() for c in _cells(rows[0])]
    owner_col = next((i for i, h in enumerate(head) if OWNER_HEAD.search(h)), None)
    out = list(rows)
    for r, row in enumerate(rows):
        if r == 0 or re.fullmatch(r"\s*\|?[\s:|-]+\|?\s*", row):
            continue
        cells = _cells(row)
        if _table_row(cells, head, owner_col, look, people, found):
            out[r] = _join(row, cells)
    return out


# ── the whole reply ──────────────────────────────────────────────────────────────

def _walk(lines, look, people, found):
    """The reply's lines with each line, or each table as a whole, checked; a ``` fence left alone."""
    out, fence, i = [], False, 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("```") or fence:
            fence = fence != line.lstrip().startswith("```")
            out.append(line)
            i += 1
        elif line.lstrip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            block = lines[i:j]
            out.extend(_check_table(block, look, people, found) if ID.search("\n".join(block)) else block)
            i = j
        else:
            out.append(_check_line(line, look, people, found) if ID.search(line) else line)
            i += 1
    return out


def check(text, lookup=None, people=None):
    """(the text with its claims checked, the findings). Unchanged, with no findings, when it names no item IDs, when there
    is no tracker, or when every claim matches."""
    if not text or not ID.search(text):
        return text, []
    look = lookup or tracker_lookup()
    if look is None:
        return text, []
    if not hasattr(look, "project"):
        look.project = lambda code: False
    found = []
    try:
        out = _walk(text.split("\n"), look, _register() if people is None else people, found)
    finally:
        if lookup is None and hasattr(look, "close"):
            look.close()
    return "\n".join(out), found


def summary(found):
    """One plain line for the panel: how many claims were corrected or flagged, or "" when none."""
    if not found:
        return ""
    t = sum(1 for f in found if f["kind"] == "title")
    o = sum(1 for f in found if f["kind"] == "owner")
    m = sum(1 for f in found if f["kind"] == "missing")
    parts = ([f"{t} title{'s' if t != 1 else ''} didn't match"] if t else []) + \
            ([f"{o} owner{'s' if o != 1 else ''} corrected"] if o else []) + \
            ([f"{m} ID{'s' if m != 1 else ''} not in the tracker"] if m else [])
    return "Checked against the tracker: " + ", ".join(parts) + "."


# ── the plain "I can't" (BL-314 part b) ──────────────────────────────────────────
# What the panel can never do, whatever is confirmed: Microsoft 365 actions (sending mail or Teams messages, changing the calendar
# or files online: DENY_TOOLS in live_server.py) and starting, stopping or installing the live server, the app or the login agent
# (reach.py refuses live_server.py and launch.py). Wording and routing only: what is allowed or refused is decided by the guard
# (reach.py, the hook, the tool lists), never here. A CONFIRM that asks for one of these is never offered as Go ahead; a refused
# tool call for one of them leads with the same sentence. Each names where in the dashboard (or outside it) it can be done.
CANT = {
    "server": ("ask creaite can't start, stop or restart the live server or the app, or set up the login agent. "
               "Settings › Live server does that.", {"page": "settings", "arg": "live", "label": "Open Settings"}),
    "teams": ("ask creaite can't post or send Teams messages: Microsoft 365 actions stay off in the panel. Draft the words here "
              "or in Draft email, then send them from Teams yourself.", None),
    "calendar": ("ask creaite can't create, move, cancel or answer meeting invites: Microsoft 365 actions stay off in the panel. "
                 "Do it in Outlook; Today shows the result after the next calendar refresh.",
                 {"page": "today", "label": "Open Today"}),
    "files": ("ask creaite can't change files in SharePoint or OneDrive online: Microsoft 365 actions stay off in the panel. "
              "Project files on this Mac it can change, on a card; open Files to find them.",
              {"page": "files", "label": "Open Files"}),
    "mail": ("ask creaite can't send, forward or reply to email: Microsoft 365 actions stay off in the panel. Draft email builds "
             "the message for you to copy into Outlook and send.", None),
}
_SERVER = re.compile(r"\b(?:start|stop|restart|quit|install|set up)\b[^.|\n]{0,30}\b(?:live server|the server|the app|launcher|"
                     r"login agent|launch agent)\b|\blaunchctl\b|\blogin agent\b", re.I)
_TEAMS = re.compile(r"\b(?:post|send|sending|message|reply)\b[^.|\n]{0,60}\b(?:in|on|to|via)\s+(?:the\s+)?teams\b|"
                    r"\bteams\s+(?:message|chat|post|channel)\b[^.|\n]{0,40}\b(?:to|in)\b", re.I)
_CAL = re.compile(r"\b(?:book|schedule|reschedule|move|cancel|accept|decline|send)\b[^.|\n]{0,50}\b(?:meeting invite|invite|"
                  r"invitation|calendar|meeting|event)\b", re.I)
_NOT_CAL = re.compile(r"\b(?:minutes|prep|agenda|transcript|actions?|items?|report|one-pager|tracker)\b", re.I)
_FILES = re.compile(r"\b(?:upload|move|rename|delete|copy)\b[^.|\n]{0,50}\b(?:sharepoint|onedrive online|in onedrive)\b", re.I)
_MAIL = re.compile(r"\b(?:send|sends|sending|forward|forwarding|reply(?:-all)? to|e-?mail (?:him|her|them))\b"
                   r"(?![^.|\n]{0,40}\bto (?:review|staging|the tracker|drafts)\b)[^.|\n]{0,60}?\b(?:e-?mail|mail|message|note|"
                   r"reminder|chase|nudge|update|reply|report|minutes|him|her|them|to)\b", re.I)
_DRAFT_ONLY = re.compile(r"^\s*(?:draft|write|prepare|word)\b", re.I)


def _named(text, people):
    """The first register person named in the text (full name, alias or first name), or None."""
    for p in people or []:
        for n in [p.get("name", "")] + list(p.get("aliases") or []) + [str(p.get("name", "")).split(" ")[0]]:
            if n and len(n) > 2 and re.search(rf"(?<![\w@]){re.escape(n)}(?![\w@])", text, re.I):
                return p.get("name")
    return None


def _offer(what, text="", people=None):
    line, go = CANT[what]
    if what in ("mail", "teams"):
        name = _named(text, people if people is not None else _register())
        go = ({"email": name, "mode": "chase" if re.search(r"\bchase|nudge|overdue\b", text, re.I) else "update",
               "label": f"Draft email to {name}"} if name else {"page": "people", "label": "Open People"})
    return {"what": what, "line": line, "go": go}


def cant(title, body="", people=None):
    """The plain "I can't" for a CONFIRM the panel could never carry out, or None when it can (then it is offered as usual)."""
    text = f"{title or ''} | {body or ''}"
    if _SERVER.search(text):
        return _offer("server", text, people)
    if _TEAMS.search(text):
        return _offer("teams", text, people)
    if _FILES.search(text):
        return _offer("files", text, people)
    if _CAL.search(text) and not _NOT_CAL.search(title or ""):
        return _offer("calendar", text, people)
    if _MAIL.search(text) and not _DRAFT_ONLY.search(title or ""):
        return _offer("mail", text, people)
    return None


def _denied_kind(name, given):
    """Which "I can't" a refused tool call is, or None."""
    short = name.rsplit("__", 1)[-1]
    if name == "Bash":
        return "server" if re.search(r"\b(?:live_server|launch)\.py\b|\blaunchctl\b", str(given.get("command") or "")) else None
    if short.startswith("outlook_"):
        return "calendar" if ("event" in short or "respond" in short) else "mail"
    return {"teams_": "teams", "sharepoint_": "files"}.get(short.split("_", 1)[0] + "_")


def cant_denied(denials, people=None):
    """The plain "I can't" for refused tool calls that no confirmation would allow (a Microsoft 365 action, the live server
    or the app), or None. Only the tool's name, a script's name and a recipient's name are read."""
    for d in denials or []:
        if not isinstance(d, dict):
            continue
        given = d.get("tool_input") if isinstance(d.get("tool_input"), dict) else {}
        what = _denied_kind(str(d.get("tool_name") or ""), given)
        if what:
            who = " ".join(str(given.get(k) or "") for k in ("to", "toRecipients", "recipients", "attendees"))
            return _offer(what, who if what in ("mail", "teams") else "", people)
    return None
