"""creaite tracker — the only writer to system/tracker.db.

Commands (run from anywhere; every location comes from paths.py):
  init                          create tracker.db from schema.sql; add projects from the register
  read [table] [--project X] [--id ID] [--search TEXT] [--status open|closed]   (BL-252)
                                (read promises --list owe|waiting: Alan's open promises, or the overdue ones made to him,
                                with overdue_days and quiet_days, BL-125 A)
                                (read rejected --project X [--days N]: the project's reject reasons, BL-133)
                                print rows as JSON
  validate <proposal>           check every item; mark failures `invalid` with a reason
  apply [proposal ...]          write decided items and file operations under one apply_id
                                (no argument: every proposal in system/staging/ with decided items)
  undo                          reverse the most recent apply that has not been undone
  undo-changes [--dry-run] [--json] <rowid> [<rowid> …]
                                put back several past changes (change_log rows) where they still hold the value that
                                change gave them, as one new apply (via "revert:<rowids>") that "undo" can reverse (BL-164)
  migrate                       bring an existing tracker.db up to schema.sql, keeping every row
  (a proposal item with op "recode" changes a project's code and name everywhere; see recode_project)
  index                         rebuild the vault_search full-text index (minutes, transcripts, reports, documents);
                                runs by itself after every apply and undo
  query "<text>" [--project X]  full-text search; prints paths and snippets as JSON

Standard library only. Dates are stored YYYY-MM-DD; paths are stored relative to the vault root.
"""
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
try:
    import log as debuglog  # BL-102: the debug log (not `log`: some scripts have a function of that name); optional
except ImportError:
    class debuglog:  # the helper is missing: every call does nothing and the script runs as before
        info = debug = warn = error = exception = staticmethod(lambda *a, **k: None)
        rule = staticmethod(lambda text, *a: "")
        main = staticmethod(lambda script, fn, *a: fn(*a))

# ── Rules (mirror schema.sql; the schema is still the final check) ─────────────

TABLES = ("projects", "milestones", "workstreams", "actions", "raid", "decisions", "promises", "links", "labels", "item_labels",
          "updates")
KEYS = {"projects": ("code",), "milestones": ("id",), "workstreams": ("id",), "actions": ("id",), "raid": ("id",), "decisions": ("id",),
        "promises": ("id",), "links": ("from_item", "to_item", "kind"), "labels": ("name",), "item_labels": ("item_id", "label"),
        "updates": ("week_ending", "project")}
REQUIRED_NEW = {
    "projects": ("code", "name"),
    "milestones": ("project", "name", "source"),
    "workstreams": ("project", "name", "source"),
    "actions": ("project", "description", "raised", "source"),
    "raid": ("project", "type", "description", "raised", "source"),
    "decisions": ("project", "decision", "source"),             # `date` is needed only once it is Made (check_row)
    "promises": ("project", "promised_by", "promised_to", "description", "raised", "source"),
    "links": ("from_item", "to_item", "source"),
    "labels": ("name",),
    "item_labels": ("item_id", "label"),
    "updates": ("week_ending", "project", "health", "summary"),
}
ALLOWED = {
    ("actions", "status"): ("Open", "Delayed", "Closed", "Cancelled"),
    ("raid", "status"): ("Open", "Closed", "Cancelled"),
    ("milestones", "status"): ("Planned", "Done", "Cancelled"),          # BL-186: Missed is retired (state Overdue instead)
    ("milestones", "state"): ("Achieved", "On track", "At risk", "Slipped", "Overdue"),
    ("workstreams", "status"): ("Active", "Closed"),
    ("actions", "priority"): ("Urgent", "High", "Medium", "Low"),
    ("raid", "type"): ("Risk", "Assumption", "Issue", "Dependency"),
    ("raid", "impact"): ("High", "Medium", "Low"),
    ("raid", "likelihood"): ("High", "Medium", "Low"),
    ("decisions", "status"): ("Pending", "Made", "Withdrawn"),
    ("promises", "status"): ("Open", "Done", "Dropped"),
    ("links", "kind"): ("blocks",),
    ("labels", "behaviour"): ("warn", "exclude"),
    ("labels", "default_choice"): ("include", "exclude"),
    ("projects", "health"): ("On track", "At risk", "Off track"),
    ("updates", "health"): ("On track", "At risk", "Off track"),
}
CODE_RE = r"[A-Z][A-Z0-9]{2,6}"      # project codes: 3 to 7 capital letters or digits, starting with a letter
DATE_FIELDS = {"milestone_date", "due_date", "raised", "closed", "date", "week_ending", "baseline_date",
               "forecast_date", "created", "needed_by", "actual_date"}
NO_EDIT = {"id", "updated_at"}
ID_PREFIX = {"actions": "-A-", "decisions": "-D-", "raid": "-", "milestones": "-M-", "workstreams": "-W-", "promises": "-P-"}
ITEM_ID = re.compile(r"([A-Z][A-Z0-9]{2,6})-(?:([ADMWP])-)?\d{3}")
ITEM_TABLE = {"A": "actions", "D": "decisions", "M": "milestones", "W": "workstreams", "P": "promises", None: "raid"}
LINKABLE = ("actions", "raid", "milestones", "decisions", "promises")     # either end of a link
LABELLED = ("actions", "raid", "decisions")                               # items that carry labels (BL-94)
ITEM_EXTRAS = ("labels", "label_reason", "label_suggested")                # on an item's values or changes, not columns
REMOVED = "(removed)"                       # change_log field for a deleted links / item_labels / labels row: old_value is the row as JSON
COLOUR_RE = r"[A-Za-z0-9#(),.% -]{1,30}"
HEADINGS = ("What it is:", "What it means for you:", "What is being done:")
CLOSED_STATUSES = ("Closed", "Cancelled")
VIA_NAMES = ("dashboard", "excel-import", "cx-edit", "assistant")

# File operations may only touch these parts of the vault
WRITABLE = ("projects/", "inbox/", "system/staging/", "system/search/")


class Invalid(Exception):
    """An item breaks a rule; the message is shown to Alan."""


class Conflict(Exception):
    """The row changed after the proposal was made (based_on)."""


# ── Small helpers ─────────────────────────────────────────────────────────────

def now():
    """Local time to the millisecond, so based_on catches changes made within the same second. Tests only: CREAITE_STAMP_DAY
    ("YYYY-MM-DD") fixes the date part of these stamps (an apply's time, change_log, updated_at); the time of day stays real,
    so stamps still differ and keep their order within a day."""
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    day = os.environ.get("CREAITE_STAMP_DAY")
    return f"{day[:10]}{t[10:]}" if day and len(day) >= 10 else t


def today():
    """Today's date as YYYY-MM-DD."""
    return date.today().isoformat()


def shown(iso):
    """YYYY-MM-DD → DD-MM-YYYY for anything Alan reads."""
    return f"{iso[8:10]}-{iso[5:7]}-{iso[0:4]}" if iso and len(iso) >= 10 else iso


def long_date(iso):
    """YYYY-MM-DD → '5 October 2026' (minutes and report headers)."""
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B %Y')}"


# ===== BL-181 (sprint-peek-new) ===== a weekend date on a work item is noted, never refused. The dates are the ones an item is due
# or needed by (an action's and a RAID item's due date, a decision's needed-by and a revisit date written as a date); dates that
# record what happened (raised, closed, made) and milestones are left out. The weekend is settings.json `work.weekend_days`
# (Saturday and Sunday by default). Used by propose.py (the cx-edit preview) and review.py (Review's list); no rejection, no schema.
WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKEND_FIELDS = {"actions": (("due_date", "due"),), "raid": (("due_date", "due"),),
                  "decisions": (("needed_by", "needed"), ("revisit", "revisit"))}


def weekend_days(settings=None):
    """{weekday number (Monday 0)} from work.weekend_days (names or numbers); Saturday and Sunday by default."""
    if settings is None:
        try:
            settings = paths.load_settings()
        except (OSError, ValueError):
            settings = {}
    given = ((settings or {}).get("work") or {}).get("weekend_days", ["Saturday", "Sunday"])
    out = set()
    for d in given if isinstance(given, list) else []:
        if isinstance(d, int) and 0 <= d <= 6:
            out.add(d)
        elif isinstance(d, str) and d.strip().title() in WEEKDAY_NAMES:
            out.add(WEEKDAY_NAMES.index(d.strip().title()))
    return out


def weekend(table, values, settings=None, days=None):
    """The notes for a proposed item's dates that fall on a weekend: ["due on a Saturday (17-10-2026)"]; [] when none."""
    days = weekend_days(settings) if days is None else days
    notes = []
    for field, word in WEEKEND_FIELDS.get(table, ()):
        v = str((values or {}).get(field) or "").strip()
        if re.fullmatch(r"\d{2}-\d{2}-\d{4}", v):          # a Revisit is free text, often typed as DD-MM-YYYY
            v = f"{v[6:10]}-{v[3:5]}-{v[0:2]}"
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            continue
        try:
            d = date.fromisoformat(v)
        except ValueError:
            continue
        if d.weekday() in days:
            notes.append(f"{word} on a {WEEKDAY_NAMES[d.weekday()]} ({shown(v)})")
    return notes
# ===== end BL-181 =====


_NAMES = {}


def project_label(code):
    """A project as a person reads it: its full name, never its code (BL-101). Anything that isn't a registered project (a
    blank, "Needs a project", an unknown code) passes through unchanged. Read once per process."""
    if not _NAMES:
        try:
            con = connect()
            _NAMES.update({c: n for c, n in con.execute("SELECT code, name FROM projects")})
            con.close()
        except Exception:  # noqa: BLE001  no database yet: nothing to translate
            _NAMES["_"] = ""
    return _NAMES.get(code) or code


def connect(db=None):
    """A connection to tracker.db (or `db`): rows by column name, foreign keys on, autocommit (callers use
    BEGIN IMMEDIATE). Exits with a message if the database is missing.
    """
    db = Path(db or paths.DB)
    if not db.exists():
        sys.exit(f"creaite: {paths.rel(db)} not found. Run: python3 system/scripts/tracker.py init")
    con = sqlite3.connect(db, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


# ===== BL-228 (sprint-debt-safety) =====
class NoDatabase(Exception):
    """The tracker database isn't there yet: what connect_or_raise raises where connect() would exit."""


def connect_or_raise(db=None):
    """connect(), for a caller that carries on without the database: a missing one raises NoDatabase (a normal error to
    catch), never SystemExit."""
    db = Path(db or paths.DB)
    if not db.exists():
        raise NoDatabase(f"{paths.rel(db)} not found")
    return connect(db)
# ===== end BL-228 =====


def columns(con, table):
    """The column names of a table."""
    return [r["name"] for r in con.execute(f"PRAGMA table_info({table})")]


def key_of(table, row):
    """A row's key as one string: its key columns joined with '|' (an ID, or e.g. 'week_ending|project')."""
    return "|".join(str(row[k]) for k in KEYS[table])


def where_key(table):
    """The SQL WHERE clause matching a table's key columns."""
    return " AND ".join(f"{k} = ?" for k in KEYS[table])


def key_values(table, key):
    """The key column values in a key string made by key_of."""
    return key.split("|") if len(KEYS[table]) > 1 else [key]


def item_table(item_id):
    """The table an item ID belongs to (A actions, D decisions, M milestones, W workstreams, P promises, plain RAID), or None."""
    m = ITEM_ID.fullmatch(str(item_id or ""))
    return ITEM_TABLE[m.group(2)] if m else None


def item_row(con, item_id, tables=LINKABLE):
    """The row an item ID names, if it is in one of `tables` and exists; else None."""
    t = item_table(item_id)
    return fetch(con, t, item_id) if t in tables else None


def label_names(value):
    """A labels value (a list, or the comma-separated text of the Excel cell) as a list of trimmed names, in order, without repeats."""
    if value is None or value == "":
        return []
    names = value.split(",") if isinstance(value, str) else list(value)
    out = []
    for n in names:
        n = str(n).strip()
        if n and n.lower() not in [o.lower() for o in out]:
            out.append(n)
    return out


def canonical_labels(con, value):
    """Each name in `value` in the spelling of the labels table; an unknown label is refused, never created."""
    out = []
    for n in label_names(value):
        r = con.execute("SELECT name FROM labels WHERE name = ?", (n,)).fetchone()
        if not r:
            known = ", ".join(x[0] for x in con.execute("SELECT name FROM labels ORDER BY name")) or "none"
            raise Invalid(f"unknown label {n!r} (labels: {known}); add it in Settings or with cx-edit first")
        out.append(r[0])
    return out


def labels_of(con, item_id):
    """An item's label names, in alphabetical order."""
    return [r[0] for r in con.execute("SELECT label FROM item_labels WHERE item_id = ? ORDER BY label COLLATE NOCASE", (item_id,))]


def blocks_reach(con, start, goal, extra=()):
    """True if `start` blocks `goal`, directly or through other items (so a new link goal→start would close a loop)."""
    edges = {}
    for a, b in list(con.execute("SELECT from_item, to_item FROM links WHERE kind = 'blocks'")) + list(extra):
        edges.setdefault(a, []).append(b)
    seen, todo = set(), [start]
    while todo:
        n = todo.pop()
        if n == goal:
            return True
        if n not in seen:
            seen.add(n)
            todo.extend(edges.get(n, []))
    return False


def fetch(con, table, key):
    """The row of `table` with key `key`, or None."""
    return con.execute(f"SELECT * FROM {table} WHERE {where_key(table)}", key_values(table, key)).fetchone()


def priority(impact, likelihood):
    """A risk or issue's priority from its impact and likelihood: Urgent, High, Medium or Low; None if either is unset."""
    if not impact or not likelihood:
        return None
    if impact == "High" and likelihood == "High":
        return "Urgent"
    if "High" in (impact, likelihood):
        return "High"
    if impact == "Low" and likelihood == "Low":
        return "Low"
    return "Medium"


def fingerprint(item):
    """Hash of project + type + normalised description, so rejected items are not proposed again."""
    v = item.get("values") or {}
    table = item.get("table", "")
    kind = v.get("type") or table
    text = v.get("description") or v.get("decision") or v.get("summary") or v.get("name") or ""
    if table == "links":
        text = f"{v.get('from_item', '')} blocks {v.get('to_item', '')}"
    elif table == "item_labels":
        text = f"{v.get('item_id', '')} {v.get('label', '')}"
    if item.get("op") != "new":
        text = f"{item.get('id', '')} {json.dumps(item.get('changes') or {}, sort_keys=True)}"
    norm = re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", text.lower())).strip()
    project = v.get("project") or (item.get("id") or v.get("from_item") or v.get("item_id") or "").split("-")[0]
    return hashlib.sha1(f"{project}|{kind}|{norm}".encode()).hexdigest()


# ── BL-133 stage B: reject reasons ─────────────────────────────────────────────
REJECT_REASONS = ("Not an action", "Duplicate", "Chatter", "Already done", "Wrong project", "Doesn't need tracking",
                  "For another team")          # BL-315: the seven; any one line of 200 characters is still accepted (BL-133)


def reject_reason(item):
    """(reason, duplicate_of) of a rejected item, or (None, None). A duplicate with no reason given is a "Duplicate"."""
    reason = str(item.get("reject_reason") or "").strip() or None
    dup = str(item.get("duplicate_of") or "").strip().upper() or None
    if dup and not reason:
        reason = "Duplicate"
    return reason, dup


def check_reject(con, item):
    """Check a rejection's reason (one line, 200 characters at most) and the item it duplicates (BL-133);
    raises Invalid.
    """
    reason, dup = reject_reason(item)
    if reason and (len(reason) > 200 or "\n" in reason):
        raise Invalid("a reject reason is one line of at most 200 characters")
    if dup and not item_row(con, dup, ("actions", "raid", "decisions")):
        raise Invalid(f"duplicate of {dup}: there is no such action, RAID item or decision")


def rejected_reasons(con, project, days=None):
    """The project's rejections that carry a reason, newest first, each with the item's text from its proposal (kept in staging
    and staging/applied): what cx-minutes and cx-sweep read as guidance. Rejected rows hold a fingerprint, not a project."""
    texts = {}
    for d in (paths.STAGING, paths.APPLIED):
        for p in sorted(d.glob("proposed-*.json")):
            try:
                items = load(p).get("items", [])
            except (OSError, ValueError):
                continue
            for it in items:
                if it.get("decision") != "rejected":
                    continue
                v = it.get("values") or {}
                code = v.get("project") or (it.get("id") or "").split("-")[0]
                if code == project:
                    texts[fingerprint(it)] = {"table": it.get("table"), "item": v.get("description") or v.get("decision") or
                                              f"{it.get('id', '')} {json.dumps(it.get('changes') or {}, sort_keys=True)}"}
    if "reason" not in columns(con, "rejected"):
        return []
    sql = "SELECT * FROM rejected WHERE reason IS NOT NULL" + (" AND rejected_at >= datetime('now', ?)" if days else "") + " ORDER BY rejected_at DESC"
    rows = con.execute(sql, (f"-{int(days)} days",) if days else ()).fetchall()
    return [{**dict(r), **texts[r["fingerprint"]]} for r in rows if r["fingerprint"] in texts]


def safe_path(rel_path, purpose):
    """Resolve a vault-relative path and refuse anything outside the writable areas."""
    if not rel_path or Path(rel_path).is_absolute() or re.match(r"^[A-Za-z]:", rel_path):
        raise Invalid(f"{purpose}: path must be relative to the vault root ({rel_path!r})")
    p = paths.resolve(rel_path).resolve()              # projects/… maps to the projects root when it is outside the vault (BL-85)
    try:
        r = paths.rel(p)
    except ValueError:
        raise Invalid(f"{purpose}: path is outside the vault ({rel_path!r})")
    if not any(p == base or base in p.parents for base in paths.allowed_roots()):
        raise Invalid(f"{purpose}: path is outside the vault and the projects folder ({rel_path!r})")
    if not r.startswith(WRITABLE):
        raise Invalid(f"{purpose}: {r} is not in projects/, inbox/, system/staging/ or system/search/")
    proot = paths.projects_root().resolve()
    below = [x.lower() for x in p.parts[len(proot.parts):]] if proot in p.parents else []
    if purpose == "mkdir" and below:            # a new project's own empty _Archive folder (from the skeleton) may be made
        below = below[:-1]
    hit = next((n for n in paths.skipped_names() if n.lower() in below), None)
    if hit:                                     # BL-09: never into _Archive (an archived project's folder), _Templates, 99 System
        raise Invalid(f"{purpose}: {hit} is never written by creaite ({rel_path})")
    return p


def file_hash(p):
    """The SHA-256 of a file, or None if it doesn't exist."""
    return hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).exists() else None


# ── Validation of one item's values ───────────────────────────────────────────

def check_values(table, values):
    """Each value's own rules (dates, allowed values, flags, a label's colour and name), field by field, then a
    project's code. BL-229: one function per kind of rule, in the order they always ran."""
    for f, v in values.items():
        if v is None or v == "":
            continue
        _check_date(f, v)
        allowed = ALLOWED.get((table, f))
        if allowed and v not in allowed:
            raise Invalid(f"{f} must be one of {', '.join(allowed)} (got {v!r})")
        _check_number_and_flags(f, v)
        _check_label_value(table, f, v)
    if table == "projects" and "code" in values and not re.fullmatch(CODE_RE, str(values["code"])):
        raise Invalid(f"project code must be 3 to 7 capital letters or digits, starting with a letter "
                      f"(got {values['code']!r})")


def _check_date(f, v):
    if f in DATE_FIELDS:
        if not (isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v)):
            raise Invalid(f"{f} must be a date stored as YYYY-MM-DD (got {v!r})")
        try:
            date.fromisoformat(v)
        except ValueError:
            raise Invalid(f"{f} is not a real date ({v!r})")


def _check_number_and_flags(f, v):
    if f == "percent_complete" and (isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 100):
        raise Invalid(f"percent_complete must be a whole number from 0 to 100 (got {v!r})")
    if f == "client_visible" and v not in (0, 1, True, False):
        raise Invalid("client_visible must be 0 or 1")
    if f in ("builtin", "suggested", "state_set") and v not in (0, 1, True, False):
        raise Invalid(f"{f} must be 0 or 1")


def _check_label_value(table, f, v):
    if (table, f) == ("labels", "colour") and not re.fullmatch(COLOUR_RE, str(v)):
        raise Invalid(f"a label's colour is a short colour name or code (got {v!r})")
    if (table, f) == ("labels", "name") and (re.search(r"[,|]", str(v)) or not str(v).strip()):
        raise Invalid("a label's name can't be empty or hold a comma or a bar")


def message_complete(table, msg):
    """Client messaging: three headings each followed by >= 5 letters or digits (decisions: plain text)."""
    msg = msg or ""
    if table == "decisions":
        return len(re.findall(r"[A-Za-z0-9]", msg)) >= 5
    lines = {h: "" for h in HEADINGS}
    for line in msg.splitlines():
        for h in HEADINGS:
            if line.strip().startswith(h):
                lines[h] = line.strip()[len(h):]
    return all(len(re.findall(r"[A-Za-z0-9]", t)) >= 5 for t in lines.values())


# ===== BL-229: check_row as an ordered list of rules per table. Each table's list is the order the single chain of checks
# reached them before, so the first rule a row breaks, and its message, are unchanged (test_writer_pinned.py).
def check_row(con, table, row, changed):
    """Rules that need the whole row after the change."""
    for rule in ROW_RULES.get(table, ()):
        rule(con, table, row, changed)


def _client_headings(con, table, row, changed):
    msg = row.get("client_message")
    if "client_message" in changed and msg is not None:
        pos = [msg.find(h) for h in HEADINGS]
        if -1 in pos or pos != sorted(pos):
            raise Invalid("client messaging must keep the three headings: " + " / ".join(HEADINGS))


def _client_complete(con, table, row, changed):
    if int(row.get("client_visible") or 0) == 1 and ({"client_visible", "client_message"} & set(changed)) \
            and not message_complete(table, row.get("client_message")):
        raise Invalid("client messaging must be complete before the item is client-visible")


def _decision_source(con, table, row, changed):
    if not (row.get("source") or "").strip():
        raise Invalid("a decision must record its source")


def _decision_rules(con, table, row, changed):
    check_decision(con, row, changed)


def _milestone_rules(con, table, row, changed):
    check_milestone(row, changed)          # BL-186


def _promise_fields(con, table, row, changed):
    for f, what in (("promised_by", "who promised"), ("promised_to", "who it was promised to"), ("description", "what was promised")):
        if not str(row.get(f) or "").strip():
            raise Invalid(f"a promise needs {what} ({f})")


def _link_rules(con, table, row, changed):
    check_link(con, row)


def _item_label(con, table, row, changed):
    t = item_table(row.get("item_id"))
    if t not in LABELLED or not fetch(con, t, row["item_id"]):
        raise Invalid(f"{row.get('item_id')} isn't an action, RAID item or decision in the tracker, so it can't carry a label")
    row["label"] = canonical_labels(con, row.get("label"))[0]


def _label_name(con, table, row, changed):
    if "name" in changed:
        row["name"] = str(row.get("name") or "").strip()


def _item_workstream(con, table, row, changed):
    if "workstream" in changed and str(row.get("workstream") or "").strip():
        w = active_workstream(con, row.get("project"), row["workstream"])     # BL-58; blank is still allowed
        if not w:
            raise Invalid(f"“{row['workstream']}” isn't an active workstream of {row.get('project')}: add it to "
                          f"{row.get('project')}'s workstreams first, or leave the workstream blank")
        row["workstream"] = w["name"]                                          # the workstream's own spelling


def _workstream_unique(con, table, row, changed):
    name = str(row.get("name") or "").strip()
    if row.get("lead") is not None and not str(row["lead"]).strip():
        row["lead"] = None
    same = con.execute("SELECT id FROM workstreams WHERE project = ? AND name = ? COLLATE NOCASE AND id IS NOT ?",
                       (row.get("project"), name, row.get("id"))).fetchone()
    if same:
        raise Invalid(f"{row.get('project')} already has a workstream called “{name}” ({same[0]})")


def _project_exists(con, table, row, changed):
    if row.get("project") and not con.execute("SELECT 1 FROM projects WHERE code = ?", (row["project"],)).fetchone():
        raise Invalid(f"project {row['project']} is not in the tracker")
    if row.get("project") and is_archived(con, row["project"]):         # BL-09
        raise Invalid(f"{project_label(row['project'])} is archived: restore it first (restore project {row['project']})")


def _milestone_link(con, table, row, changed):
    if row.get("milestone"):  # optional link; must exist, in the same project
        ms = con.execute("SELECT project FROM milestones WHERE id = ?", (row["milestone"],)).fetchone()
        if not ms:
            raise Invalid(f"milestone {row['milestone']} is not in the tracker")
        if row.get("project") and ms[0] != row["project"]:
            raise Invalid(f"milestone {row['milestone']} belongs to {ms[0]}, not {row['project']}")


_ITEM_RULES = (_client_headings, _client_complete, _item_workstream, _project_exists, _milestone_link)
ROW_RULES = {
    "actions": _ITEM_RULES,
    "raid": _ITEM_RULES,
    "decisions": (_client_complete, _decision_source, _decision_rules, _project_exists),
    "milestones": (_milestone_rules, _project_exists),
    "promises": (_promise_fields, _project_exists),
    "links": (_link_rules,),
    "item_labels": (_item_label,),
    "labels": (_label_name,),
    "workstreams": (_workstream_unique, _project_exists),
}
# ===== end BL-229 (check_row) =====


def check_decision(con, row, changed):
    """BL-53: a Made decision has its date; a Pending one has none; `replaces` names an earlier decision of the same project."""
    status = row.get("status") or "Made"
    has_date = bool(str(row.get("date") or "").strip())
    if status == "Made" and not has_date:
        raise Invalid("a decision that is Made needs its date (a Pending one has none until it is made)")
    if status == "Pending" and has_date:
        raise Invalid("a Pending decision has no date until it is made; leave date empty, or set status to Made")
    if str(row.get("replaces") or "").strip():
        old = fetch(con, "decisions", row["replaces"])
        if not old:
            raise Invalid(f"{row['replaces']} (replaced by this decision) is not in the tracker")
        if row.get("project") and old["project"] != row["project"]:
            raise Invalid(f"{row['replaces']} belongs to {old['project']}, not {row['project']}")
        if row.get("id"):
            seen, nxt = {row["id"]}, old
            while nxt is not None:                      # no loop: A replaces B replaces A
                if nxt["id"] in seen:
                    raise Invalid(f"{row['id']} and {row['replaces']} would replace each other")
                seen.add(nxt["id"])
                nxt = fetch(con, "decisions", nxt["replaces"]) if nxt["replaces"] else None


def check_link(con, row):
    """BL-90 part 2: both ends exist (any project), they differ, and the links don't loop."""
    a, b = row.get("from_item"), row.get("to_item")
    for end, label in ((a, "from_item"), (b, "to_item")):
        if item_table(end) not in LINKABLE:
            raise Invalid(f"{label} {end!r} isn't an action, RAID item, milestone, decision or promise ID")
        if not item_row(con, end):
            raise Invalid(f"{label} {end} is not in the tracker")
    if a == b:
        raise Invalid("an item can't block itself")
    if blocks_reach(con, b, a):
        raise Invalid(f"{b} already blocks {a}, so {a} can't block {b} (the links would loop)")


def active_workstream(con, project, name):
    """The project's Active workstream with this name (any case), or None (BL-58)."""
    return con.execute("SELECT * FROM workstreams WHERE project = ? AND name = ? COLLATE NOCASE AND status = 'Active'",
                       (project, str(name).strip())).fetchone()


def match_workstream(con, project, text):
    """The name of the project's Active workstream that `text` names, by name or alias in any case; None if none
    does (BL-58: extraction then leaves it blank and flags it for Review, never inventing one)."""
    want = str(text or "").strip().lower()
    if not want:
        return None
    try:
        found = con.execute("SELECT name, aliases FROM workstreams WHERE project = ? AND status = 'Active'",
                            (project,)).fetchall()
    except sqlite3.Error:
        return None
    for name, aliases in found:
        if name.lower() == want or want in [a.strip().lower() for a in (aliases or "").split(",") if a.strip()]:
            return name
    return None


def flag_workstream(con, item):
    """Staging (cx-minutes, cx-sweep): keep a known workstream in its own spelling; blank an unknown one and flag it
    `new-workstream`, keeping the name as `ws_suggest` for Review ("New workstream 'Integration' for ORX?")."""
    v = item.get("values") or {}
    if item.get("table") not in ("actions", "raid") or not str(v.get("workstream") or "").strip():
        return
    hit = match_workstream(con, v.get("project"), v["workstream"])
    if hit:
        v["workstream"] = hit
        return
    item["ws_suggest"] = str(v["workstream"]).strip()
    v["workstream"] = ""
    if "new-workstream" not in item.setdefault("flags", []):
        item["flags"].append("new-workstream")


SHARED_NUMBERS = ("actions", "raid", "decisions", "promises")    # one number sequence per project: ABC-A-002 and ABC-002 never both exist


def next_id(con, table, project):
    """The next ID for `table`. Actions, RAID items, decisions and promises share one sequence per project, so a number is
    never used twice across them (ABC-A-002 means ABC-002 and ABC-D-002 are never issued). Milestones and workstreams
    keep their own."""
    tables = SHARED_NUMBERS if table in SHARED_NUMBERS else (table,)
    n = 0
    for t in tables:
        prefix = f"{project}{ID_PREFIX[t]}"
        for (i,) in con.execute(f"SELECT id FROM {t} WHERE project = ? AND length(id) = ? AND id LIKE ?",
                                (project, len(prefix) + 3, prefix + "%")):
            tail = i[len(prefix):]
            if tail.isdigit():
                n = max(n, int(tail))
    return f"{project}{ID_PREFIX[table]}{n + 1:03d}"


# ── Writing one item (used by validate as a dry run and by apply) ─────────────

def log(con, apply_id, table, key, field, old, new, op, via):
    """Record one field's change in change_log under `apply_id`, so undo can reverse it."""
    con.execute("INSERT INTO change_log (at, apply_id, tbl, item_id, field, old_value, new_value, op, via) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (now(), apply_id, table, key, field,
                 None if old is None else str(old), None if new is None else str(new), op, via))


BLANKABLE = {"decisions": ("date", "needed_by", "replaces", "reasoning", "options", "revisit"),     # an empty string means "not set"
             "milestones": ("state", "state_reason", "owner", "actual_date", "client_message", "description", "internal_note")}   # BL-186


def blank_to_none(table, values):
    """In place: an empty text for an optional field (a pending decision's date, as `"date": ""` from a sweep spec) is not set."""
    for f in BLANKABLE.get(table, ()):
        if f in values and values[f] is not None and not str(values[f]).strip():
            values[f] = None


CLOSING = {"actions": CLOSED_STATUSES, "raid": CLOSED_STATUSES, "promises": ("Done", "Dropped")}   # statuses that set `closed`


def set_labels(con, item_id, want, reason, suggested, apply_id, via):
    """Make `want` (canonical names) the item's label set: add the missing ones, remove the others, each logged."""
    have = labels_of(con, item_id)
    lower = {w.lower() for w in want}
    for old in have:
        if old.lower() not in lower:
            delete_row(con, "item_labels", f"{item_id}|{old}", fetch(con, "item_labels", f"{item_id}|{old}"), apply_id, via)
    for name in want:
        if name.lower() not in {h.lower() for h in have}:
            row = {"item_id": item_id, "label": name, "added_by": via, "added_at": now(), "reason": reason or None,
                   "suggested": 1 if suggested else 0}
            row = {k: v for k, v in row.items() if v is not None}
            con.execute(f"INSERT INTO item_labels ({', '.join(row)}) VALUES ({', '.join('?' * len(row))})", list(row.values()))
            stored = fetch(con, "item_labels", f"{item_id}|{name}")
            for f in stored.keys():
                if stored[f] is not None:
                    log(con, apply_id, "item_labels", f"{item_id}|{name}", f, None, stored[f], "insert", via)
    return bool(set(h.lower() for h in have) ^ lower)


def delete_row(con, table, key, current, apply_id, via):
    """Remove a links, item_labels or labels row. The row is kept in change_log (field REMOVED) so undo can put it back."""
    if table == "labels":
        if current["builtin"]:
            raise Invalid(f"{current['name']} is a built-in label and can't be deleted")
        n = con.execute("SELECT count(*) FROM item_labels WHERE label = ?", (current["name"],)).fetchone()[0]
        if n:
            raise Invalid(f"{n} item(s) still carry {current['name']}; remove it from them first")
    con.execute(f"DELETE FROM {table} WHERE {where_key(table)}", key_values(table, key))
    log(con, apply_id, table, key, REMOVED, json.dumps(dict(current), ensure_ascii=False), None, "update", via)
    return key


# ===== BL-249 (fix-field-names) =====
# An unknown field is still refused; the message lists the valid fields and suggests the likely one (ask creaite guessed
# `title` and `note` for a milestone's `name` and `description`). The first alias that is a column of the table wins.
FIELD_ALIASES = {"title": ("name", "decision", "description"), "note": ("description",), "notes": ("description",),
                 "summary": ("description",), "details": ("description",), "text": ("description", "decision"),
                 "due": ("due_date", "forecast_date"), "date": ("forecast_date", "due_date"),
                 "target_date": ("forecast_date", "due_date"), "baseline": ("baseline_date",), "forecast": ("forecast_date",),
                 "actual": ("actual_date",), "achieved": ("actual_date",), "percent": ("percent_complete",),
                 "progress": ("percent_complete",), "assignee": ("owner",), "assigned_to": ("owner",)}


def unknown_fields_message(table, unknown, cols):
    """'unknown field(s) for milestones: note, title. Valid: … Did you mean: note → description, title → name?'"""
    import difflib
    valid = [c for c in cols if c not in NO_EDIT]
    hints = []
    for f in sorted(unknown):
        to = next((c for c in FIELD_ALIASES.get(str(f).lower(), ()) if c in valid), None) \
            or next(iter(difflib.get_close_matches(str(f), valid, 1, 0.75)), None)
        if to:
            hints.append(f"{f} → {to}")
    msg = f"unknown field(s) for {table}: {', '.join(sorted(map(str, unknown)))}. Valid: {', '.join(valid)}"
    if hints:
        msg += f". Did you mean: {', '.join(hints)}?"
    if "note" in unknown:
        msg += " (A change's reason goes in the item's own `note`, beside `changes`, not in them.)"
    return msg + " (`propose.py fields " + table + "` lists them.)"
# ===== end BL-249 =====


# ===== BL-229: the single writer, split. write_item checks and dispatches; the shared steps are written once; what is
# particular to a table is a hook keyed by table, so a new table adds hooks rather than branches. The order of every
# check is the order before the split (dev/tests/test_writer_pinned.py pins it, error messages included).
def write_item(con, item, apply_id, via):
    """Write one approved item. Returns its key (assigned ID for new rows)."""
    table, op = item.get("table"), item.get("op")
    if table not in TABLES:
        raise Invalid(f"unknown table {table!r}")
    if op == "recode" and table == "projects":
        return recode_project(con, item, apply_id, via)        # BL-111
    if op in ARCHIVE_OPS and table == "projects":
        return archive_project(con, item, apply_id, via)       # BL-09
    if op == AGE_OP:
        return archive_item(con, item, apply_id, via)          # BL-10
    refuse_archived_field(item)
    if op not in ("new", "update", "cancel"):
        raise Invalid(f"op must be new, update or cancel (got {op!r})")
    cols = columns(con, table)
    if op == "new":
        return _insert_row(con, table, item, cols, apply_id, via)
    key, current = _existing_row(con, table, item, op)
    if op == "cancel" and table in DELETED_ON_CANCEL:
        return delete_row(con, table, key, current, apply_id, via)
    changes = _cancel_changes(table) if op == "cancel" else dict(item.get("changes") or {})
    return _update_row(con, table, item, key, current, changes, cols, apply_id, via)


DELETED_ON_CANCEL = ("links", "item_labels", "labels")
CANCEL_CHANGES = {"actions": {"status": "Cancelled"}, "raid": {"status": "Cancelled"}, "promises": {"status": "Dropped"},
                  "projects": {"active": 0}, "workstreams": {"status": "Closed"}}


def _cancel_changes(table):
    """What cancelling a row of `table` changes; a table not listed can't be cancelled."""
    if table not in CANCEL_CHANGES:
        raise Invalid(f"{table} rows can't be cancelled; edit them instead")
    return dict(CANCEL_CHANGES[table])


def _take_extras(table, fields):
    """Pop the item's label fields (not columns) from `fields`; only actions, RAID items and decisions carry labels."""
    extras = {k: fields.pop(k) for k in ITEM_EXTRAS if k in fields}
    if extras and table not in LABELLED:
        raise Invalid("labels can only be put on actions, RAID items and decisions")
    return extras


def _existing_row(con, table, item, op):
    """(key, current row as a dict) for an update or a cancel; a conflict when the row changed after the proposal."""
    key = item.get("id")
    if not key:
        raise Invalid(f"{op} needs the item's id")
    current = fetch(con, table, key)
    if current is None:
        raise Invalid(f"{key} is not in {table}")
    current = dict(current)
    if item.get("based_on") and "updated_at" in current and current["updated_at"] != item["based_on"]:
        raise Conflict(f"{key} changed at {current['updated_at']} after this proposal was made")
    return key, current


# ---------- new rows ----------
def _new_workstream(values, via):
    values["name"] = str(values["name"]).strip()
    values.setdefault("created", today())


def _new_raid(values, via):
    values["priority"] = priority(values.get("impact"), values.get("likelihood"))


def _new_label(values, via):
    if values.get("builtin"):
        raise Invalid("built-in labels are created by creaite; a new label is never built in")
    values["name"] = str(values["name"]).strip()


def _new_milestone(values, via):
    norm_milestone(values, None, set(values))      # BL-186


def _new_link(values, via):
    values.setdefault("kind", "blocks")


def _new_item_label(values, via):
    values.setdefault("added_by", via)


NEW_HOOKS = {"workstreams": _new_workstream, "raid": _new_raid, "labels": _new_label, "milestones": _new_milestone,
             "links": _new_link, "item_labels": _new_item_label}     # normalise a new row of that table


def _check_new_fields(table, values, cols):
    unknown = set(values) - set(cols)
    if unknown:
        raise Invalid(unknown_fields_message(table, unknown, cols))       # BL-249: lists the valid fields
    if table in ID_PREFIX and values.get("id"):
        raise Invalid("new items carry no ID; tracker.py assigns it")
    missing = [f for f in REQUIRED_NEW[table] if not str(values.get(f) or "").strip()]
    if missing:
        raise Invalid(f"missing required field(s): {', '.join(missing)}")


def _closed_for_new(table, values):
    if table in CLOSING:
        status = values.get("status") or "Open"
        if status in CLOSING[table]:
            values.setdefault("closed", today())
        else:
            values["closed"] = None


def _insert_row(con, table, item, cols, apply_id, via):
    """A new row: checked, normalised, given its ID, written and logged field by field."""
    values = dict(item.get("values") or {})
    extras = _take_extras(table, values)
    want = canonical_labels(con, extras.get("labels"))
    blank_to_none(table, values)
    _check_new_fields(table, values, cols)
    check_values(table, values)
    if table in NEW_HOOKS:
        NEW_HOOKS[table](values, via)
    _closed_for_new(table, values)
    check_row(con, table, values, set(values))
    if table in ID_PREFIX:
        values["id"] = next_id(con, table, values["project"])
    if "updated_at" in cols:
        values["updated_at"] = now()
    if fetch(con, table, key_of(table, values)):
        raise Invalid(f"{table} already has {key_of(table, values)}")
    values = {k: v for k, v in values.items() if v is not None}
    con.execute(f"INSERT INTO {table} ({', '.join(values)}) VALUES ({', '.join('?' * len(values))})",
                list(values.values()))
    key = key_of(table, values)
    row = fetch(con, table, key)
    for f in cols:
        if row[f] is not None and not (f == "archived" and not row[f]):     # BL-09: a new row is never archived; not logged
            log(con, apply_id, table, key, f, None, row[f], "insert", via)
    if want:
        set_labels(con, key, want, extras.get("label_reason"), extras.get("label_suggested"), apply_id, via)
    return key


# ---------- updates and cancels ----------
def _prepare_workstream(changes, current):
    if "project" in changes and changes["project"] != current["project"]:
        raise Invalid("a workstream stays in its project; close it and add one to the other project instead")
    if "name" in changes:
        changes["name"] = str(changes["name"]).strip()


UPDATE_PREPARE = {"workstreams": _prepare_workstream}     # on the changes, before they are merged into the row


def _derive_raid(row, current, changes):
    row["priority"] = priority(row.get("impact"), row.get("likelihood"))


DERIVE = {"raid": _derive_raid}                            # fields worked out from the merged row (before `closed`)


def _check_decision(row, current, changes):
    if current.get("status") == "Made" and row.get("status") == "Pending":
        raise Invalid("a decision that has been Made can't go back to Pending; record a new decision that replaces it")


def _check_project(row, current, changes):
    if "health" in changes and changes["health"] != current.get("health") \
            and not str(changes.get("health_reason") or "").strip():
        raise Invalid("a health change needs a reason (health_reason)")


def _check_milestone(row, current, changes):
    norm_milestone(row, current, set(changes))         # BL-186


CHECK = {"decisions": _check_decision, "projects": _check_project, "milestones": _check_milestone}   # after `closed`


def _check_changes(con, table, changes, extras, cols):
    if set(changes) - set(cols):                                         # BL-249: an unknown field, named with the valid ones
        raise Invalid(unknown_fields_message(table, set(changes) - set(cols), cols))
    bad = (set(changes) & NO_EDIT) | (set(changes) - set(cols)) | (set(changes) & set(KEYS[table]))
    if table == "labels":
        bad |= set(changes) & {"builtin"}
    if bad:
        raise Invalid(f"these fields can't be changed: {', '.join(sorted(bad))}")
    if not changes and "labels" not in extras:
        raise Invalid("update has no changes")


def _closed_for_update(table, row, current, changes):
    if table in CLOSING and "status" in changes:
        if row["status"] in CLOSING[table]:
            row["closed"] = changes.get("closed") or current.get("closed") or today()
        else:
            row["closed"] = None


def _merged_row(con, table, item, current, changes):
    """The row as it will be: the changes merged in, derived fields worked out, every rule checked."""
    row = {**current, **changes}
    if table in DERIVE:
        DERIVE[table](row, current, changes)
    _closed_for_update(table, row, current, changes)
    if table in CHECK:
        CHECK[table](row, current, changes)
    check_row(con, table, row, set(changes))
    return row


def _carry_workstream_rename(con, current, diff, apply_id, via):
    """BL-58: a rename carries the project's items with it."""
    if "name" not in diff:
        return
    for t in ("actions", "raid"):
        for r in con.execute(f"SELECT id, workstream, updated_at FROM {t} WHERE project = ? AND "
                             "workstream = ? COLLATE NOCASE", (current["project"], current["name"])).fetchall():
            at = now()
            con.execute(f"UPDATE {t} SET workstream = ?, updated_at = ? WHERE id = ?", (diff["name"], at, r[0]))
            log(con, apply_id, t, r[0], "workstream", r[1], diff["name"], "update", via)
            log(con, apply_id, t, r[0], "updated_at", r[2], at, "update", via)


AFTER_WRITE = {"workstreams": _carry_workstream_rename}    # other rows an update carries with it, in the same apply


def _write_rebaseline(con, table, key, item, rebase, apply_id, via):
    """BL-186: the decision that goes with a rebaseline, in the same apply (so one undo takes both)."""
    did = write_item(con, {"op": "new", "table": "decisions", "values": rebase}, apply_id, via)
    if apply_id is not None:                                      # a dry run (validate) leaves the proposal as it was
        item["rebaseline"]["decision"] = did
    why = str(item.get("note") or rebase["reasoning"]).strip().rstrip(".")
    log(con, apply_id, table, key, "note", None, f"{why}. Agreed with {rebase['made_by']}. Decision {did}", "update", via)


def _unarchive_on_edit(current, diff, want):
    """BL-10: editing an item archived for its age (its fields or its labels) un-archives it, in place in `diff`. An archived
    project's items never get here: they refuse edits."""
    if current.get("archived") and (diff or want is not None):
        diff["archived"] = 0


def _update_row(con, table, item, key, current, changes, cols, apply_id, via):
    """An update (or a cancel, as the update it makes): checked, the changed fields written and logged."""
    extras = _take_extras(table, changes)
    _check_changes(con, table, changes, extras, cols)
    want = canonical_labels(con, extras.get("labels")) if "labels" in extras else None
    blank_to_none(table, changes)
    check_values(table, changes)
    if table in UPDATE_PREPARE:
        UPDATE_PREPARE[table](changes, current)
    row = _merged_row(con, table, item, current, changes)
    rebase = rebaseline_of(item, current, row) if table == "milestones" else None     # BL-186: checked before anything is written
    diff = {f: row[f] for f in cols if f != "updated_at" and row.get(f) != current.get(f)}
    if want is not None:      # the item's labels; a label change alone leaves the item's own row (and updated_at) alone
        set_labels(con, key, want, extras.get("label_reason"), extras.get("label_suggested"), apply_id, via)
    _unarchive_on_edit(current, diff, want)
    if not diff:
        return key
    if "updated_at" in cols:
        diff["updated_at"] = now()
    con.execute(f"UPDATE {table} SET {', '.join(f'{f} = ?' for f in diff)} WHERE {where_key(table)}",
                list(diff.values()) + key_values(table, key))
    for f, v in diff.items():
        log(con, apply_id, table, key, f, current.get(f), v, "update", via)
    if table in AFTER_WRITE:
        AFTER_WRITE[table](con, current, diff, apply_id, via)
    if item.get("note") and not rebase:   # a reason that goes with the change; history only, not a column
        log(con, apply_id, table, key, "note", None, item["note"], "update", via)
    if rebase:
        _write_rebaseline(con, table, key, item, rebase, apply_id, via)
    return key
# ===== end BL-229 =====


# ===== BL-186 (sprint-milestones) ===== milestones: five states, Alan's state with its reason, owner, the achieved date, client
# wording, and the rebaseline's decision. One reading of the rules, used by the dashboard's data, the reports and the one-pager.
MS_STATES = ("Achieved", "On track", "At risk", "Slipped", "Overdue")
MS_RANK = {s: i for i, s in enumerate(MS_STATES)}
MS_CLIENT_WORD = {"Achieved": "Achieved", "On track": "On track", "At risk": "At risk", "Slipped": "Expected later",
                  "Overdue": "Late"}     # Alan, 11-10-2026: a late milestone reads "Late"; BL-299: On track is "On track"


def suggested_state(row, on=None):
    """What the dates say: Achieved when Done; Overdue when the agreed date has passed; Slipped when the forecast is later than
    the agreed date; On track otherwise. At risk is only ever Alan's call."""
    on = on or today()
    if row.get("status") == "Done":
        return "Achieved"
    base = row.get("baseline_date")
    fc = row.get("forecast_date") or base
    if base and base < on:
        return "Overdue"
    if base and fc and fc > base:
        return "Slipped"
    return "On track"


def milestone_state(row, on=None):
    """The state shown: Achieved when Done, Alan's when he set one, else the dates' suggestion."""
    if row.get("status") == "Done":
        return "Achieved"
    if row.get("state_set") and row.get("state"):
        return row["state"]
    return suggested_state(row, on)


def client_milestones(rows_):
    """The client filter (client report, one-pager, the Plan's client preview): client-visible, not cancelled, with its wording."""
    return [m for m in rows_ if int(m.get("client_visible") or 0) == 1 and m.get("status") != "Cancelled"
            and message_complete("decisions", m.get("client_message"))]


def norm_milestone(row, current, changed):
    """In place, before the checks: a state set by hand marks state_set (and clearing it returns the state to the dates); Done
    fills the achieved date (today if none is given) and leaving Done clears it; a Done milestone's state is Achieved or empty."""
    if "state" in changed and "state_set" not in changed:
        row["state_set"] = 1 if row.get("state") else 0
    if "state_set" in changed and not row.get("state_set"):
        row["state"] = None
    if not row.get("state"):
        row["state_set"] = 0
        if {"state", "state_set"} & changed:
            row["state_reason"] = None
    if "status" in changed:
        if row.get("status") == "Done":
            fc = row.get("forecast_date")                       # a forecast already passed is when it was done; else today
            row["actual_date"] = row.get("actual_date") or (fc if fc and fc <= today() else today())
            if "state" not in changed and row.get("state") not in (None, "Achieved"):
                row["state"], row["state_set"], row["state_reason"] = None, 0, None
        elif current is not None and current.get("status") == "Done":
            if "actual_date" not in changed:
                row["actual_date"] = None
            if "state" not in changed and row.get("state") == "Achieved":
                row["state"], row["state_set"], row["state_reason"] = None, 0, None


def check_milestone(row, changed):
    """Check a milestone's status and state agree (Done is Achieved; state_set exactly when a state is set)
    and that a state set by hand has a reason; raises Invalid.
    """
    state, status = row.get("state"), row.get("status") or "Planned"
    if state == "Achieved" and status != "Done":
        raise Invalid("an Achieved milestone is Done: set status Done (with the achieved date, actual_date)")
    if status == "Done" and state not in (None, "Achieved"):
        raise Invalid(f"a Done milestone is Achieved, not {state}; reopen it (status Planned) to give it another state")
    if bool(row.get("state_set")) != bool(state):
        raise Invalid("state_set is 1 exactly when a state is set; leave both empty and creaite suggests the state from the dates")
    if {"state", "state_set", "state_reason"} & changed and state and state != "Achieved":
        sug = suggested_state(row)
        if MS_RANK[state] < MS_RANK[sug] and not str(row.get("state_reason") or "").strip():
            raise Invalid(f"{state} is better than the dates suggest ({sug}): give a one-line reason (state_reason)")
    if {"actual_date", "status"} & changed and row.get("actual_date"):
        if status != "Done":
            raise Invalid("the achieved date (actual_date) is set only when the milestone is Done")
        if row["actual_date"] > today():
            raise Invalid(f"the achieved date can't be after today ({shown(row['actual_date'])})")
    if {"client_visible", "client_message"} & changed and int(row.get("client_visible") or 0) == 1 \
            and not message_complete("decisions", row.get("client_message")):
        raise Invalid("a client-visible milestone needs its client wording (client_message)")


def rebaseline_of(item, current, row):
    """A change to an existing agreed date (baseline_date) is a rebaseline: it needs who agreed it, why and where (the item's
    `rebaseline`: agreed_with, reason, source) and records a decision. Returns the decision's values, or None (no rebaseline)."""
    old, new = current.get("baseline_date"), row.get("baseline_date")
    if not old or old == new:
        return None
    rb = item.get("rebaseline") if isinstance(item.get("rebaseline"), dict) else {}
    who = rb.get("agreed_with")
    who = ", ".join(str(w).strip() for w in who if str(w).strip()) if isinstance(who, list) else str(who or "").strip()
    reason, source = str(rb.get("reason") or "").strip(), str(rb.get("source") or "").strip()
    missing = [w for w, v in (("who agreed it (agreed_with)", who), ("the reason", reason), ("the source", source)) if not v]
    if not new:
        raise Invalid("a milestone's agreed date (baseline_date) can't be cleared once agreed; rebaseline it to a new date")
    if missing:
        raise Invalid(f"changing the agreed date is a rebaseline and records a decision: give {', '.join(missing)} "
                      "in the item's rebaseline")
    when = str(rb.get("date") or "").strip() or today()
    return {"project": row["project"], "decision": f"{row['name']}: agreed date moves from {shown(old)} to {shown(new)}",
            "made_by": who, "date": when, "status": "Made", "reasoning": reason, "source": source}


def milestone_original(con, item_id, current=None):
    """The Original date: the first agreed date in change_log (skipping undone applies), else the current one."""
    r = con.execute("SELECT c.new_value FROM change_log c LEFT JOIN applies a ON a.apply_id = c.apply_id "
                    "WHERE c.tbl = 'milestones' AND c.item_id = ? AND c.field = 'baseline_date' AND c.op != 'undo' "
                    "AND c.new_value IS NOT NULL AND a.undone_at IS NULL ORDER BY c.rowid LIMIT 1", (item_id,)).fetchone()
    return r[0] if r else current


MS_EVENT_FIELDS = ("baseline_date", "forecast_date", "status", "state", "state_reason", "actual_date", "note")


def milestone_events(con, ids=None):
    """{milestone id: [event]} from change_log, oldest first, skipping undone applies and undo rows: each event is
    {at, apply_id, field, old, new, via} for the fields Movement and the slip range read (a note carries the reason given
    with a change in the same apply). Read only."""
    q = ("SELECT c.rowid AS rid, c.at, c.apply_id, c.item_id, c.field, c.old_value, c.new_value, c.op, c.via FROM change_log c "
         "LEFT JOIN applies a ON a.apply_id = c.apply_id WHERE c.tbl = 'milestones' AND c.op != 'undo' AND a.undone_at IS NULL "
         f"AND c.field IN ({', '.join('?' * len(MS_EVENT_FIELDS))})")
    args = list(MS_EVENT_FIELDS)
    if ids is not None:
        ids = list(ids)
        if not ids:
            return {}
        q += f" AND c.item_id IN ({', '.join('?' * len(ids))})"
        args += ids
    out = {}
    for r in con.execute(q + " ORDER BY c.rowid", args):
        out.setdefault(r["item_id"], []).append({"at": r["at"], "apply_id": r["apply_id"], "field": r["field"], "old": r["old_value"],
                                                  "new": r["new_value"], "op": r["op"], "via": r["via"]})
    return out
# ===== end BL-186 =====


# ── Proposals ─────────────────────────────────────────────────────────────────

def load(p):
    """A proposal file's JSON."""
    return json.loads(Path(p).read_text(encoding="utf-8"))


def raised_for(values, created):
    """The Raised date for a proposed action or RAID item that lacks one (BL-26): the source's date (a meeting
    file is named YYYY-MM-DD Title; an email or chat source carries its sent date), else the day it was staged.
    Never today by default, so a late review doesn't make items look newer than they are."""
    staged = (created or "")[:10] if re.fullmatch(r"\d{4}-\d{2}-\d{2}", (created or "")[:10]) else None
    m = re.search(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)", values.get("source") or "")
    if m and (not staged or m.group(1) <= staged):
        return m.group(1)
    return staged or today()


def milestone_progress(con, m):
    """(percent, calculated, closed, linked) for a milestone row (BL-29): Alan's figure wins over the one
    calculated from linked actions (closed ÷ linked, Cancelled ignored); percent is None when neither exists."""
    got = con.execute("SELECT status FROM actions WHERE milestone = ? AND status != 'Cancelled'", (m["id"],)).fetchall()
    closed = sum(1 for (s,) in got if s == "Closed")
    calc = round(100 * closed / len(got)) if got else None
    pc = m["percent_complete"] if "percent_complete" in m.keys() else None
    return (pc if pc is not None else calc), calc, closed, len(got)


def fill_raised(data):
    """Fill a missing Raised on new actions and RAID items, in place; [(item n, date)] for what was filled."""
    filled = []
    for item in data.get("items", []):
        v = item.get("values")
        if item.get("op") == "new" and item.get("table") in ("actions", "raid") and isinstance(v, dict) \
                and not v.get("raised") and not item.get("applied"):
            v["raised"] = raised_for(v, data.get("created"))
            filled.append((item.get("n"), v["raised"]))
    return filled


def save(p, data):
    """Write a proposal file's JSON."""
    Path(p).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ===== BL-232 (fix-as-proposed) =====
def stamp_as_proposed(p, data):
    """Capture edits: before a proposal file is rewritten, give each item whose `values` (new) or `changes` (update)
    differ from the file on disk a write-once `as_proposed` copy of what they were. An item that has one keeps it;
    one whose `as_proposed` was taken away (an undo) isn't given another. `apply` never reads it. In place; returns
    the item numbers stamped. Every Python edit path (review.py's save, minutes.py's refresh) calls this one function;
    the dashboard does the same in `editProposal`."""
    try:
        old = json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []                                   # a new file: nothing was proposed before it
    filled_old, filled_new = json.loads(json.dumps(old)), json.loads(json.dumps(data))
    fill_raised(filled_old)                         # compared as review.py loads them, so a filled Raised isn't an edit
    fill_raised(filled_new)
    pick = lambda d: {i.get("n"): i for i in d.get("items", []) if isinstance(i, dict)}   # noqa: E731
    raw, before, after = pick(old), pick(filled_old), pick(filled_new)
    stamped = []
    for it in data.get("items", []):
        n = it.get("n") if isinstance(it, dict) else None
        o, a = before.get(n), after.get(n)
        if not o or not a or o.get("op") != it.get("op") or it.get("applied") or "as_proposed" in it or "as_proposed" in o:
            continue
        part = "changes" if it.get("op") == "update" else "values"
        if isinstance(o.get(part), dict) and o[part] != a.get(part):
            it["as_proposed"] = json.loads(json.dumps(raw[n][part]))   # what the file held, unfilled
            stamped.append(n)
    return stamped
# ===== end BL-232 =====


def resolve_proposal(arg):
    """The path of a proposal given as a path or a file name in system/staging/; exits if not found."""
    p = Path(arg)
    for cand in (p, paths.ROOT / p, paths.STAGING / p.name):
        if cand.exists():
            return cand.resolve()
    sys.exit(f"creaite: proposal not found: {arg}")


def via_for(prop_path, data):
    """What change_log records as the source of an apply: the proposal's source_run, else its file name. The daily archiving
    (BL-10: items only, each an archive_item) is recorded as "archive", so Activity names it; it is not one of Alan's own
    edits (VIA_NAMES), and a report archive (files only) keeps its file name."""
    run = data.get("source_run", "")
    items = data.get("items") or []
    if run == AGE_SOURCE and items and all(i.get("op") == AGE_OP for i in items):
        return AGE_SOURCE
    return run if run in VIA_NAMES else Path(prop_path).name


def blocks(data):
    """The meeting and report blocks, with their decision field names."""
    out = []
    if data.get("meeting"):
        out.append((data["meeting"], "minutes_decision"))
    if data.get("report"):
        out.append((data["report"], "report_decision"))
    if data.get("file_changes"):   # memory, register and other file edits (dashboard, cx-edit)
        out.append((data["file_changes"], "file_changes_decision"))
    return out


def set_flag(item, flag, on, reason=None):
    """Turn a flag on an item on or off; `invalid` also keeps or clears the reason."""
    flags = [f for f in item.get("flags", []) if f != flag]
    if on:
        flags.append(flag)
    item["flags"] = flags
    if flag == "invalid":
        if on:
            item["invalid_reason"] = reason
        else:
            item.pop("invalid_reason", None)


def dry_run(con, data, via, only_approved):
    """Try every item in order inside a transaction that is always rolled back.

    Returns {n: ("invalid"|"conflict"|"needs-project", reason)}."""
    return dry_run_all(con, [(None, data, via)], only_approved)[None]


def dry_run_all(con, batch, only_approved):
    """Dry-run several proposals together, in the order apply writes them, so a change one makes is seen by the
    next (two proposals editing the same row show as a conflict here, not as a failed apply). Always rolled back.

    batch: [(key, data, via)]. Returns {key: {n: (kind, reason)}}."""
    out = {key: {} for key, _, _ in batch}
    con.execute("BEGIN")
    try:
        for key, data, via in batch:
            _try_items(con, data, via, only_approved, out[key])
    finally:
        con.execute("ROLLBACK")
    return out


def _try_items(con, data, via, only_approved, problems):
    """Each approved (or, for validate, pending) item in order, with a savepoint per item."""
    ids = {}                                  # BL-322: {n: the ID a new item of this proposal was given}, for `@n` links
    for item in data.get("items", []):
        if item.get("applied") or item.get("decision") == "rejected":
            continue
        if only_approved and item.get("decision") != "approved":
            continue
        if item.get("decision") == "approved" and item.get("match") in ("possible", "unresolved"):
            problems[item.get("n")] = ("needs-project", f"needs a project (match is {item['match']})")
            continue
        con.execute("SAVEPOINT item")
        try:
            key = write_item(con, sibling_refs(item, ids), None, via)      # BL-322: a link to a new item of this proposal
            if item.get("op") == "new":
                ids[item.get("n")] = key
            con.execute("RELEASE item")
        except Conflict as e:
            problems[item.get("n")] = ("conflict", str(e))
            con.execute("ROLLBACK TO item")
            con.execute("RELEASE item")
        except (Invalid, sqlite3.Error) as e:
            problems[item.get("n")] = ("invalid", str(e))
            con.execute("ROLLBACK TO item")
            con.execute("RELEASE item")
    return problems


def cmd_validate(arg):
    """Check every item of a proposal without writing to the database: mark failures invalid and conflicts in the
    proposal file, check its file operations and print the problems. Returns 1 if any item is invalid.
    """
    prop = resolve_proposal(arg)
    data = load(prop)
    for n, d in fill_raised(data):
        print(f"Item {n}: Raised set to {shown(d)} (source or staging date)")
    con = connect()
    problems = dry_run(con, data, via_for(prop, data), only_approved=False)
    for item in data.get("items", []):
        if item.get("applied") or item.get("decision") == "rejected":
            continue
        kind, reason = problems.get(item.get("n"), (None, None))
        set_flag(item, "invalid", kind == "invalid", reason)
        set_flag(item, "conflict", kind == "conflict")
        if kind == "conflict":
            item["conflict_reason"] = reason
        else:
            item.pop("conflict_reason", None)
    for blk, field in blocks(data):
        for fop in blk.get("file_ops", []):
            try:
                check_file_op(fop, blk)
            except Invalid as e:
                problems[f"{field}"] = ("invalid", str(e))
    save(prop, data)
    for n, (kind, reason) in problems.items():
        print(f"item {n}: {kind} — {reason}")
    print(f"{paths.rel(prop)}: {len(data.get('items', []))} items, {len(problems)} problem(s)")
    return 1 if any(k == "invalid" for k, _ in problems.values()) else 0


# ── File operations ───────────────────────────────────────────────────────────

def op_source(fop, blk):
    """The source path of a file operation: a draft or transcript reference taken from its block."""
    src = fop.get("from")
    if src in ("draft", "transcript"):
        src = blk.get(src)
    return src


def check_file_op(fop, blk):
    """Check one file operation of a proposal can be done safely (source exists, every path relative and in a
    writable area); raises Invalid.
    """
    op = fop.get("op")
    if op == "copy":
        src = op_source(fop, blk)
        if not src or not paths.resolve(src).is_file():
            raise Invalid(f"copy: source not found ({src})")
        safe_path(fop.get("to"), "copy")
    elif op == "remove":
        safe_path(fop.get("path"), "remove")
    elif op == "mkdir":
        safe_path(fop.get("path"), "mkdir")
    elif op == "write":
        safe_path(fop.get("path"), "write")
        if not isinstance(fop.get("content"), str):
            raise Invalid("write: content must be text")
    elif op == "move":
        check_move(fop, blk)                       # BL-09: a whole folder into or out of _Archive, nothing else
    else:
        raise Invalid(f"unknown file operation {op!r}")


def check_write_base(fop, written):
    """Dry run of run_file_ops' write rule, so a stale write stops the apply before anything is backed up or changed,
    naming the proposal. Writes earlier in the same apply count: a chain of edits to one file, each based on the last, passes."""
    if fop.get("op") != "write":
        return
    p = safe_path(fop["path"], "write")
    current = written[p] if p in written else (p.read_text(encoding="utf-8") if p.exists() else None)
    previous = fop.get("previous")
    if current is not None and current == fop["content"]:
        return
    if previous is None and current is not None:
        raise Invalid(f"write: {paths.rel(p)} already exists")
    if previous is not None and current != previous:
        raise Invalid(f"write: {paths.rel(p)} changed since this proposal was made")
    written[p] = fop["content"]


def selected_ops(blk, field):
    """Which file operations run, given the block's decisions."""
    decision = blk.get(field, "pending")
    if decision == "approved":
        return list(blk.get("file_ops", []))
    if field == "minutes_decision" and decision == "rejected" \
            and blk.get("transcript_decision", "approved") != "rejected":
        # Minutes rejected: file the transcript, discard the draft
        tr = blk.get("transcript")
        ops = [f for f in blk.get("file_ops", [])
               if (f.get("op") == "copy" and f.get("from") == "transcript")
               or (f.get("op") == "remove" and f.get("path") == tr)]
        if blk.get("draft"):
            ops.append({"op": "remove", "path": blk["draft"]})
        return ops
    return []


def set_status_line(docx, text):
    """Replace the draft's status line (the first paragraph starting 'Draft') in a .docx."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    with zipfile.ZipFile(docx) as z:
        items = [(i, z.read(i.filename)) for i in z.infolist()]
    done = False
    out = []
    for info, raw in items:
        if info.filename == "word/document.xml" and not done:
            xml = raw.decode("utf-8")
            for m in re.finditer(r"<w:p[ >].*?</w:p>", xml, re.S):
                para = m.group()
                texts = re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", para)
                if "".join(texts).strip().startswith("Draft"):
                    first = [True]

                    def repl(t):
                        """The first text run gets the new status line; later runs in the paragraph are emptied."""
                        if first[0]:
                            first[0] = False
                            return re.sub(r">[^<]*<", ">" + text + "<", t.group(), count=1)
                        return re.sub(r">[^<]*<", "><", t.group(), count=1)
                    new = re.sub(r"<w:t(?: [^>]*)?>[^<]*</w:t>", repl, para)
                    xml = xml[:m.start()] + new + xml[m.end():]
                    done = True
                    break
            raw = xml.encode("utf-8")
        out.append((info, raw))
    if not done:
        return False
    tmp = Path(str(docx) + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for info, raw in out:
            z.writestr(info, raw)
    tmp.replace(docx)
    return True


def stash(apply_id, src):
    """Keep a copy of a file in system/backups/files/<apply_id>/ so undo can restore it."""
    dest = paths.BACKUPS / "files" / str(apply_id) / paths.rel(src)
    dest.parent.mkdir(parents=True, exist_ok=True)
    n = 1
    while dest.exists():
        dest = dest.with_name(f"{dest.stem}.{n}{dest.suffix}")
        n += 1
    shutil.copy2(src, dest)
    return paths.rel(dest)


def run_file_ops(apply_id, blk, field, ops, done, prop=None):
    """Run ops in order, appending an undo record for each to `done`. BL-229: each operation is its own function. prop: the
    proposal file being applied (a move checks the live server's marker against it, #124 F3)."""
    _stamp_approved(apply_id, blk, field, done)
    for fop in ops:
        check_file_op(fop, blk)
        if fop["op"] == "move":
            _op_move(apply_id, fop, blk, done, prop)
        else:
            FILE_OPS[fop["op"]](apply_id, fop, blk, done)


def _stamp_approved(apply_id, blk, field, done):
    """An approved draft (minutes or a report) says who approved it and when, before it is filed."""
    approved_by = (paths.load_settings().get("identity", {}).get("name") or "Alan").split()[0]
    if field in ("minutes_decision", "report_decision") and blk.get(field) == "approved" and blk.get("draft"):
        draft = paths.resolve(blk["draft"])
        if draft.exists():
            kept = stash(apply_id, draft)
            on = (os.environ.get("CREAITE_NOW") or today())[:10]          # creaite's clock: CREAITE_NOW fixes it in tests
            if set_status_line(draft, f"Approved by {approved_by} on {long_date(on)}"):
                done.append({"op": "status", "path": blk["draft"], "previous": kept, "hash": file_hash(draft)})


def _op_copy(apply_id, fop, blk, done):
    src, dst = paths.resolve(op_source(fop, blk)), safe_path(fop["to"], "copy")
    if dst.exists():
        if file_hash(dst) == file_hash(src):
            return      # already filed (an earlier proposal made the same copy): nothing to copy or undo
        raise Invalid(f"copy: {paths.rel(dst)} already exists; it is never overwritten")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    done.append({"op": "copy", "to": paths.rel(dst), "hash": file_hash(dst)})


def _op_remove(apply_id, fop, blk, done):
    p = safe_path(fop["path"], "remove")
    if p.exists():
        kept = stash(apply_id, p)
        p.unlink()
        done.append({"op": "remove", "path": paths.rel(p), "kept": kept})


def _op_mkdir(apply_id, fop, blk, done):
    p = safe_path(fop["path"], "mkdir")
    created = []
    for parent in reversed([p, *p.parents]):
        if not any(root in parent.parents for root in paths.allowed_roots()):    # below the vault or the projects root, never them
            continue
        if not parent.exists():
            parent.mkdir()
            created.append(paths.rel(parent))
    if created:
        done.append({"op": "mkdir", "created": created})


def _op_write(apply_id, fop, blk, done):
    p = safe_path(fop["path"], "write")
    previous = fop.get("previous")
    current = p.read_text(encoding="utf-8") if p.exists() else None
    if current is not None and current == fop["content"]:
        return      # already as proposed (an earlier proposal made the same change): nothing to write or undo, and it must not block the apply
    if previous is None and current is not None:
        raise Invalid(f"write: {paths.rel(p)} already exists")
    if previous is not None and current != previous:
        raise Invalid(f"write: {paths.rel(p)} changed since this proposal was made")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(fop["content"], encoding="utf-8")
    done.append({"op": "write", "path": paths.rel(p), "previous": current, "hash": file_hash(p)})


# ===== BL-09: archive and restore a whole project =====
# {"op": "archive", "table": "projects", "id": CODE, "register_row": "<the project's register row>", "folder": {"from", "to"}}
# closes the project (active 0) and sets `archived` on it and on every item of it; {"op": "restore", …, "changes": {"active": 0|1}}
# clears them and puts `active` back. Nothing is archived with an item still open (propose.py archive --cancel-open cancels them
# first, in the same proposal). Each field is logged in change_log, so undo reverses it exactly; updated_at is left as it was. The
# register row and the folder are logged too ("register_row", "folder"; not columns), so a restore can put them back. The same
# proposal's file block (archive: "archive" | "restore") moves the folder and rewrites the register (archive_problems).
ARCHIVE_OPS = ("archive", "restore")
ARCHIVABLE = ("milestones", "workstreams", "actions", "raid", "decisions", "promises")
ARCHIVE_OPEN = {"actions": ("Open", "Delayed"), "raid": ("Open",), "decisions": ("Pending",), "promises": ("Open",),
                 "milestones": ("Planned",)}


def is_archived(con, code):
    """Whether project `code` is archived (False on a database from before BL-09)."""
    try:
        r = con.execute("SELECT archived FROM projects WHERE code = ?", (code,)).fetchone()
    except sqlite3.OperationalError:            # no archived column yet: tracker.py migrate adds it
        return False
    return bool(r and r[0])


def open_items(con, code):
    """[(table, id)] of a project's items that are still open (an archived project has none)."""
    out = []
    for t, statuses in ARCHIVE_OPEN.items():
        q = f"SELECT id FROM {t} WHERE project = ? AND status IN ({','.join('?' * len(statuses))}) ORDER BY id"
        out += [(t, r[0]) for r in con.execute(q, (code, *statuses))]
    return out


def refuse_archived_field(item):
    """`archived` is never set by an ordinary new item or update: only an archive or a restore of the project sets it."""
    if "archived" in (item.get("values") or {}) or "archived" in (item.get("changes") or {}):
        raise Invalid("archived is set only by archiving or restoring the project (archive project / restore project)")


def archive_project(con, item, apply_id, via):
    """Write one archive or restore item (see the block's note). Returns the project code."""
    code = item.get("id")
    row = fetch(con, "projects", code)
    if row is None:
        raise Invalid(f"{code} is not a project in the tracker")
    flags, active = _archive_target(con, item, row)
    keep = set() if flags else age_archived_before(con, code)       # BL-10: a restore leaves items archived for their age alone
    for t in ARCHIVABLE:
        for (i,) in con.execute(f"SELECT id FROM {t} WHERE project = ? AND archived = ? ORDER BY id", (code, 1 - flags)).fetchall():
            if (t, i) in keep:
                continue
            con.execute(f"UPDATE {t} SET archived = ? WHERE id = ?", (flags, i))
            log(con, apply_id, t, i, "archived", 1 - flags, flags, "update", via)
    for field, new in (("active", active), ("archived", flags)) if flags else (("archived", flags), ("active", active)):
        if row[field] != new:
            con.execute(f"UPDATE projects SET {field} = ? WHERE code = ?", (new, code))
            log(con, apply_id, "projects", code, field, row[field], new, "update", via)
    for field in ("register_row", "folder"):           # history only: what a restore puts back
        if item.get(field):
            v = item[field] if isinstance(item[field], str) else json.dumps(item[field], ensure_ascii=False)
            log(con, apply_id, "projects", code, field, None, v, "update", via)
    return code


def _archive_target(con, item, row):
    """(archived, active) the project and its items will have: an archive needs no open item; a restore puts active back."""
    code = item.get("id")
    if item.get("op") == "archive":
        if row["archived"]:
            raise Invalid(f"{project_label(code)} is archived already")
        still = open_items(con, code)
        if still:
            raise Invalid(f"{project_label(code)} has {len(still)} open item(s) ({', '.join(i for _, i in still[:8])}): "
                          "cancel them first (archive project --cancel-open) or stop")
        flags, active = 1, 0
    else:
        if not row["archived"]:
            raise Invalid(f"{project_label(code)} isn't archived")
        flags, active = 0, int((item.get("changes") or {}).get("active", 1))
    if active not in (0, 1):
        raise Invalid("a restore's active is 0 or 1")
    return flags, active


def age_archived_before(con, code):
    """{(table, id)} of the project's archived items that its latest archive (not undone) didn't flag: those were archived for
    their age (BL-10) before it, so a restore leaves them archived. Read from change_log; without an archive record, none."""
    r = con.execute("SELECT c.apply_id FROM change_log c JOIN applies a ON a.apply_id = c.apply_id WHERE c.tbl = 'projects' "
                    "AND c.item_id = ? AND c.field = 'archived' AND c.new_value = '1' AND c.op = 'update' "
                    "AND a.undone_at IS NULL ORDER BY c.rowid DESC LIMIT 1", (code,)).fetchone()
    if not r:
        return set()
    flagged = {(t, i) for t, i in con.execute("SELECT tbl, item_id FROM change_log WHERE apply_id = ? AND field = 'archived' "
                                              "AND new_value = '1' AND tbl != 'projects'", (r[0],))}
    out = set()
    for t in ARCHIVABLE:
        out |= {(t, i) for (i,) in con.execute(f"SELECT id FROM {t} WHERE project = ? AND archived = 1", (code,))
                if (t, i) not in flagged}
    return out


def last_archive(con, code):
    """{active, register_row, folder} logged by the latest archive of `code` that hasn't been undone, or None."""
    r = con.execute("SELECT c.apply_id FROM change_log c JOIN applies a ON a.apply_id = c.apply_id WHERE c.tbl = 'projects' "
                    "AND c.item_id = ? AND c.field = 'archived' AND c.new_value = '1' AND c.op = 'update' "
                    "AND a.undone_at IS NULL ORDER BY c.rowid DESC LIMIT 1", (code,)).fetchone()
    if not r:
        return None
    got = {f: (o, n) for f, o, n in con.execute("SELECT field, old_value, new_value FROM change_log WHERE apply_id = ? "
                                                "AND tbl = 'projects' AND item_id = ?", (r[0], code))}
    folder = json.loads(got["folder"][1]) if got.get("folder") else None
    return {"active": int(got["active"][0]) if got.get("active") else 0,
            "register_row": got["register_row"][1] if got.get("register_row") else None, "folder": folder}


def archive_problems(p, data):
    """An approved archive or restore item and its file block go together: the block says the same kind, is approved too, and
    moves that project's folder; a block marked archive or restore has its item. Returns the problems."""
    items = [i for i in data.get("items", []) if i.get("op") in ARCHIVE_OPS and not i.get("applied")
             and i.get("decision") == "approved"]
    blk = data.get("file_changes") or {}
    kind = blk.get("archive") if blk.get("file_changes_decision") == "approved" and not blk.get("applied") else None
    if not items and kind not in ARCHIVE_OPS:
        return []
    if len(items) != 1 or kind != items[0].get("op"):
        return [f"{p.name}: an archive or restore is one project item with its approved file block (archive: archive or restore)"]
    return [] if _moves_its_folder(items[0], blk) else [f"{p.name}: an archive or restore moves exactly its project's folder"]


def _moves_its_folder(item, blk):
    """The block has one move, and it is the item's own folder move (when the item names one)."""
    moves = [o for o in blk.get("file_ops", []) if o.get("op") == "move"]
    want = item.get("folder") or {}
    return len(moves) == 1 and (not want or (moves[0].get("from"), moves[0].get("to")) == (want.get("from"), want.get("to")))


# ===== BL-10: items archived for their age (Alan, 14-10-2026) =====
# Once a day (archive.py daily) closed or cancelled actions and RAID items, and done or dropped promises, whose closed date is
# archive.after_months.<table> months ago or more (6 by default) are flagged archived, through this apply: one item each,
# {"op": "archive_item", "table": "actions", "id": "ABC-A-001"}. The rule is checked again here, so no proposal can archive an
# open item, a decision, a milestone, or one closed too recently. Each flag is logged (undo reverses it); updated_at is left alone.
# An edit un-archives the item (_update_row), and it then stays live for another period from that edit. Client-visible items and
# those a client report cited follow the same rule (Alan, 14-10-2026): the report is a saved file and doesn't change.
AGE_OP = "archive_item"
AGE_SOURCE = "archive"          # the daily run's proposals (source_run)
AGE_ARCHIVABLE = ("actions", "raid", "promises")
AGE_DEFAULT_MONTHS = 6


def clock_day():
    """Today as a date; CREAITE_NOW ("YYYY-MM-DD HH:MM") fixes it for tests, as elsewhere."""
    fixed = os.environ.get("CREAITE_NOW")
    return datetime.strptime(fixed[:10], "%Y-%m-%d").date() if fixed else date.today()


def months_before(day, n):
    """The date n calendar months before `day` (the 31st becomes the month's last day)."""
    y, m = divmod(day.year * 12 + day.month - 1 - int(n), 12)
    m += 1
    last = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)).day
    return date(y, m, min(day.day, last))


def age_months(table, settings=None):
    """archive.after_months.<table> (6 by default); 0 or less means that kind is never archived for its age."""
    try:
        s = settings if settings is not None else paths.load_settings()
        v = ((s.get("archive") or {}).get("after_months") or {}).get(table, AGE_DEFAULT_MONTHS)
        return int(v)
    except (OSError, ValueError, TypeError):
        return AGE_DEFAULT_MONTHS


def unarchived_since(con, table, item_id, cutoff):
    """Whether an edit un-archived the item on or after `cutoff` (an apply not undone): it stays live a full period from then."""
    r = con.execute("SELECT 1 FROM change_log c JOIN applies a ON a.apply_id = c.apply_id WHERE c.tbl = ? AND c.item_id = ? "
                    "AND c.field = 'archived' AND c.old_value = '1' AND c.new_value = '0' AND a.undone_at IS NULL "
                    "AND substr(c.at, 1, 10) >= ? LIMIT 1", (table, item_id, cutoff)).fetchone()
    return bool(r)


def age_archive_problem(con, table, row, on=None, settings=None):
    """None when the item may be archived for its age on day `on` (today), else why not."""
    if table not in AGE_ARCHIVABLE:
        return "only actions, RAID items and promises are archived for their age (never decisions or milestones)"
    if row["archived"]:
        return f"{row['id']} is archived already"
    if is_archived(con, row["project"]):
        return f"{project_label(row['project'])} is archived"
    if row["status"] not in CLOSING[table]:
        return f"{row['id']} is {row['status']}: an open item is never archived"
    months = age_months(table, settings)
    if months <= 0:
        return f"{table} are never archived for their age (archive.after_months.{table} is {months})"
    cutoff = months_before(on or clock_day(), months).isoformat()
    if not row["closed"] or row["closed"] > cutoff:
        return f"{row['id']} closed {shown(row['closed']) if row['closed'] else 'on no date'}: not {months} months ago yet"
    if unarchived_since(con, table, row["id"], cutoff):
        return f"{row['id']} was edited within {months} months, which un-archived it"
    return None


def due_for_age_archive(con, on=None, settings=None):
    """[(table, id)] of the items the daily run would archive on day `on`, in table and ID order."""
    out = []
    for t in AGE_ARCHIVABLE:
        months = age_months(t, settings)
        if months <= 0:
            continue
        cutoff = months_before(on or clock_day(), months).isoformat()
        q = (f"SELECT * FROM main.{t} WHERE archived = 0 AND closed IS NOT NULL AND closed <= ? "
             f"AND status IN ({','.join('?' * len(CLOSING[t]))}) ORDER BY id")
        for r in con.execute(q, (cutoff, *CLOSING[t])).fetchall():
            if age_archive_problem(con, t, dict(r), on, settings) is None:
                out.append((t, r["id"]))
    return out


def archive_item(con, item, apply_id, via):
    """Write one archive_item (see the block's note): the rule checked again, the flag set and logged. Returns the item's ID."""
    table, key = item.get("table"), item.get("id")
    if table not in AGE_ARCHIVABLE:
        raise Invalid("only actions, RAID items and promises are archived for their age (never decisions or milestones)")
    current = fetch(con, table, key) if key else None
    if current is None:
        raise Invalid(f"{key} is not in {table}")
    problem = age_archive_problem(con, table, dict(current))
    if problem:
        raise Invalid(problem)
    con.execute(f"UPDATE {table} SET archived = 1 WHERE id = ?", (key,))
    log(con, apply_id, table, key, "archived", 0, 1, "update", via)
    return key
# ===== end BL-10 =====


def hide_archived(con, settings=None):
    """BL-09: the default views leave archived projects and their items out. Temporary views named like the tables (projects, the
    item tables, links, item_labels, updates) shadow them for this connection only, read-only connections included; the
    tables themselves are still main.<table>. With dashboard.show_archived on, nothing is hidden. Returns con."""
    try:
        s = settings if settings is not None else paths.load_settings()
        have = [r[1] for r in con.execute("PRAGMA main.table_info(projects)")]
        if (s.get("dashboard") or {}).get("show_archived") or "archived" not in have:
            return con
    except (OSError, ValueError, sqlite3.Error):     # no settings or an older database: nothing to hide
        return con
    gone = "SELECT code FROM main.projects WHERE archived = 1"
    views = {t: f"SELECT * FROM main.{t} WHERE archived = 0" for t in ("projects",) + ARCHIVABLE}
    views["links"] = (f"SELECT * FROM main.links WHERE substr(from_item, 1, instr(from_item, '-') - 1) NOT IN ({gone}) "
                      f"AND substr(to_item, 1, instr(to_item, '-') - 1) NOT IN ({gone})")
    views["item_labels"] = f"SELECT * FROM main.item_labels WHERE substr(item_id, 1, instr(item_id, '-') - 1) NOT IN ({gone})"
    views["updates"] = f"SELECT * FROM main.updates WHERE project NOT IN ({gone})"
    for t, sql in views.items():
        con.execute(f"CREATE TEMP VIEW IF NOT EXISTS {t} AS {sql}")
    return con
# ===== end BL-09 =====


# ===== BL-09: the `move` file operation (archive, restore, and renaming an old zz Archive folder) =====
# {"op": "move", "from": "projects/<folder>", "to": "projects/_Archive/<folder>"} in a file block whose "archive" says which kind
# of move it is ("archive", "restore" or "rename"; one file: "reports", BL-03, and its reverse "reports_back", BL-331; one note:
# "notes", #124's Delete note, and its reverse "notes_back").
# reach.archive_move_problem is the one exception to _Archive's never rule: only this apply calls it. The paths are stored paths,
# never mapped into _Archive (paths.resolve(…, archived=False)). Undo moves the
# folder back, and removes the _Archive folder this move made if it is empty again.

def check_move(fop, blk):
    """Check one move: the block says which kind of move it is, and reach.py agrees it is that whole-folder move; raises Invalid."""
    import reach
    kind = blk.get("archive")
    if kind not in reach.ARCHIVE_MOVES:
        raise Invalid("move: a folder is moved only by an archive, a restore or a rename of an old archive folder")
    src, dst = fop.get("from"), fop.get("to")
    for p in (src, dst):
        if not p or Path(str(p)).is_absolute() or not str(p).startswith("projects/"):
            raise Invalid(f"move: path must be a stored projects/ path ({p!r})")
    problem = reach.archive_move_problem(src, dst, kind)
    if problem:
        raise Invalid(f"move: {problem}")
    if kind in ("reports_back", "notes_back"):   # BL-331, #124: only a file an archive (or Delete note) moved there, back
        import archive                            # to where it came from
        was = archive.archived_moves(kind=kind[:-len("_back")]).get(src)
        if was != dst and not (kind == "notes_back" and was and reach.NOTES_BACK_RENAMES and _renamed_back(was, dst)):
            raise Invalid(f"move: {src} isn't a file the archive moved there, so it isn't moved back")


def _renamed_back(was, dst):
    """#124: dst is the deleted note's old stored path `was` with only the -2, -3… a taken name gets (reach.NOTES_BACK_RENAMES)."""
    import reach
    a, b = Path(str(was)), Path(str(dst))
    return a.parent == b.parent and reach._note_name(a.name, b.name)


def card_move_problem(fop, blk, prop):
    """#124 F3: why this move can't be applied here, or None. A move only the live server's card makes (reach.CARD_ONLY_MOVES)
    needs the marker the server writes on Approve (reach.card_move_marker): a regular file (never a symlink), under
    reach.CARD_MOVE_SECONDS old, naming the proposal file being applied and its SHA-256. Checked only by the apply, never by
    check_move (propose.py check runs that for the card's preview, before Approve)."""
    import reach
    import stat
    if blk.get("archive") not in reach.CARD_ONLY_MOVES:
        return None
    m = reach.card_move_marker(blk.get("archive"), fop.get("from"), fop.get("to"))
    try:
        fd = os.open(m, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            st = os.fstat(fd)
            age = time.time() - st.st_mtime
            ok = stat.S_ISREG(st.st_mode) and -5 <= age < reach.CARD_MOVE_SECONDS
            got = json.loads(os.read(fd, 4096).decode("utf-8")) if ok else None
        finally:
            os.close(fd)
        ok = ok and isinstance(got, dict) and prop is not None and got.get("proposal") == Path(prop).name \
            and got.get("sha256") == file_hash(prop)
    except (OSError, ValueError):                 # no marker, a symlink, unreadable: refused
        ok = False
    return None if ok else f"move: {fop.get('from')} is moved only by Approve on the live server's approval card"


def _op_move(apply_id, fop, blk, done, prop=None):
    why = card_move_problem(fop, blk, prop)       # #124 F3: before anything is made or moved
    if why:
        raise Invalid(why)
    a, b = paths.resolve(fop["from"], archived=False), paths.resolve(fop["to"], archived=False)
    made = b.parent
    while not made.parent.exists():               # BL-03: the highest folder this move makes (_Archive/04 Reporting/Weekly)
        made = made.parent
    made = made if not made.exists() else None
    b.parent.mkdir(parents=True, exist_ok=True)
    try:
        _move(a, b, blk.get("archive"))
    except FileExistsError:                       # #124: taken between the check and the move: the apply rolls back
        raise Invalid(f"move: {fop['to']} already exists; a folder move never overwrites") from None
    except SymlinkMove:                           # #124 F1: a symlink put there after the check: never followed, never moved
        raise Invalid(f"move: {fop['from']} is a symlink; a file move never follows one") from None
    done.append({"op": "move", "from": fop["from"], "to": fop["to"], "made": paths.rel(made) if made else None,
                 "kind": blk.get("archive")})


class SymlinkMove(OSError):
    """#124 F1: a one-file move (reach.FILE_MOVES) found a symlink where the file was: it is never followed and never moved."""


def _move(a, b, kind):
    """#124: move a to b, never over a file at b (FileExistsError). os.rename replaces a file on macOS and Linux, so one file
    (reach.FILE_MOVES) moves by os.link, which refuses a name that is taken, then os.unlink; where hard links aren't supported
    it falls back to a check and os.rename. A folder (BL-09) moves by os.rename as before (it never replaces a folder that
    isn't empty). F1: a one-file move never follows a symlink: `a` is a symlink (SymlinkMove) is refused before the link, the
    link itself never follows one (follow_symlinks=False where the platform has it), and a link that isn't `a` itself (a
    symlink swapped in at the last moment, where it hasn't) is removed and refused. A symlink at `b` is a taken name."""
    import reach
    if kind not in reach.FILE_MOVES:
        os.rename(a, b)
        return
    if os.path.islink(a):
        raise SymlinkMove(str(a))
    try:
        if os.link in os.supports_follow_symlinks:
            os.link(a, b, follow_symlinks=False)
        else:
            os.link(a, b)
    except FileExistsError:
        raise
    except OSError:                               # a file system without hard links: the check, then the move
        if os.path.lexists(b):
            raise FileExistsError(str(b)) from None
        if os.path.islink(a):
            raise SymlinkMove(str(a)) from None
        os.rename(a, b)
        return
    try:
        same = not os.path.islink(a) and os.path.samestat(os.lstat(a), os.lstat(b))
    except OSError:
        same = False
    if not same:                                  # what was linked isn't the file at a: never kept
        os.unlink(b)
        raise SymlinkMove(str(a))
    try:
        os.unlink(a)
    except OSError:
        os.unlink(b)                              # never two names for one file: as it was, and the caller is told
        raise


def _move_back(b, a, kind, renames):
    """#124: move b back to a, never over a file; with renames, a name taken (before or between the check and the move) gives
    the next free one. Where it went, or None when it stayed."""
    a.parent.mkdir(parents=True, exist_ok=True)
    want = a
    for _ in range(50):
        if renames and a.exists():
            a = paths.free_path(want.parent, want.stem, want.suffix)
        try:
            _move(b, a, kind)
            return a
        except FileExistsError:
            if not renames:
                return None
    return None


def _reverse_move(rec, report):
    import reach
    a, b = paths.resolve(rec["from"], archived=False), paths.resolve(rec["to"], archived=False)
    kind = rec.get("kind")
    want = b.is_file() if kind in reach.FILE_MOVES else b.is_dir()   # BL-03, BL-331 move one file; BL-09 a folder
    renames = kind == "notes" and reach.NOTES_BACK_RENAMES      # #124: a new note took the name: back as <name>-2.md
    if not want:
        report.append(f"skipped moving {rec['to']} back: it isn't there")
        return
    if a.exists() and not renames:
        report.append(f"skipped moving {rec['to']} back: {rec['from']} is there again")
        return
    old = a
    try:
        a = _move_back(b, a, kind, renames)
    except SymlinkMove:                           # #124 F1: an archived symlink (_move refuses it): never followed, never moved
        report.append(f"skipped moving {rec['to']} back: it is a symlink now")
        return
    if a is None:                                 # whatever took the name is left as it is
        report.append(f"skipped moving {rec['to']} back: {rec['from']} is there again")
        return
    if a != old:
        report.append(f"restored {rec['from']} as {a.name}: a note took its name")
    made = paths.resolve(rec["made"], archived=False) if rec.get("made") else None
    here = b.parent
    while made is not None and here.is_dir() and not any(here.iterdir()) and (here == made or made in here.parents):
        here.rmdir()                              # the folders this move made, once they are empty again
        here = here.parent
# ===== end BL-09 =====


FILE_OPS = {"copy": _op_copy, "remove": _op_remove, "mkdir": _op_mkdir, "write": _op_write, "move": _op_move}


def reverse_file_ops(records, report):
    """Undo file operation records, newest first. Files changed since are skipped and reported."""
    for rec in reversed(records):
        op = rec["op"]
        if op == "copy":
            p = paths.resolve(rec["to"])
            if p.exists() and file_hash(p) != rec["hash"]:
                report.append(f"skipped {rec['to']}: changed since it was filed")
            elif p.exists():
                p.unlink()
        elif op == "remove":
            p = paths.resolve(rec["path"])
            if p.exists():
                report.append(f"skipped restoring {rec['path']}: a file is already there")
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(paths.resolve(rec["kept"]), p)
        elif op == "status":
            p = paths.resolve(rec["path"])
            if p.exists() and file_hash(p) != rec["hash"]:
                report.append(f"skipped restoring the draft status line in {rec['path']}: changed since")
            else:
                shutil.copy2(paths.resolve(rec["previous"]), p)
        elif op == "mkdir":
            for d in reversed(rec["created"]):
                p = paths.resolve(d)
                if p.exists() and not any(p.iterdir()):
                    p.rmdir()
                elif p.exists():
                    report.append(f"kept folder {d}: not empty")
        elif op == "write":
            p = paths.resolve(rec["path"])
            if p.exists() and file_hash(p) != rec["hash"]:
                report.append(f"skipped {rec['path']}: changed since")
            elif rec["previous"] is None:
                p.unlink(missing_ok=True)
            else:
                p.write_text(rec["previous"], encoding="utf-8")
        elif op in REVERSE_MORE:
            REVERSE_MORE[op](rec, report)         # BL-09: processed.txt lines, and a folder move


def _reverse_processed(rec, report):
    lines = paths.PROCESSED.read_text(encoding="utf-8").splitlines(keepends=True)
    for line in rec["lines"]:
        if line in lines:
            lines.remove(line)
    paths.PROCESSED.write_text("".join(lines), encoding="utf-8")


REVERSE_MORE = {"processed": _reverse_processed, "move": _reverse_move}


# ── Apply ─────────────────────────────────────────────────────────────────────

def decided(data):
    """(items, blocks) of a proposal decided but not yet applied."""
    items = [i for i in data.get("items", []) if not i.get("applied")
             and i.get("decision") in ("approved", "rejected")]
    blks = [(b, f) for b, f in blocks(data) if not b.get("applied") and b.get(f) in ("approved", "rejected")]
    return items, blks


def finished(data):
    """Whether every item and block of a proposal has been applied."""
    if any(not i.get("applied") for i in data.get("items", [])):
        return False
    return all(b.get("applied") for b, _ in blocks(data))


# ===== BL-323: the OneDrive copy is the day's closed zip (backup.py); its retention is Tidy up's =====
def offsite_dir():
    """Where the closed daily backup zip goes (BL-85, BL-323): locations.offsite_backup inside the projects folder (the company
    OneDrive), or None when the projects live in the vault or the setting is empty."""
    import backup
    return backup.offsite_dir()


def offsite_copy():
    """Copy the newest daily backup zip into the OneDrive folder, under a temporary name then renamed; never the live database.
    {"copied": path or None, "error": text or None}; a failure never stops anything."""
    import backup
    return backup.copy_offsite()


def last_offsite_copy():
    """(date of the newest copy in the OneDrive folder, a zip or an older database copy, or None)."""
    import backup
    return backup.last_offsite()
# ===== end BL-323 =====


def backup_db(tag):
    """Copy tracker.db to system/backups/tracker-<time>-<tag>.db, never over an earlier backup (BL-266)."""
    paths.BACKUPS.mkdir(parents=True, exist_ok=True)
    dest = paths.free_path(paths.BACKUPS, f"tracker-{datetime.now():%Y-%m-%d-%H%M%S}-{tag}", ".db")   # BL-266: never an earlier backup
    src = sqlite3.connect(paths.DB)
    dst = sqlite3.connect(dest)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()
    return dest


# ===== BL-229 step 3: cmd_apply in steps. The transaction is where it was: one BEGIN IMMEDIATE around every write of the
# apply, one COMMIT, or a ROLLBACK that also reverses the file operations. Messages and their order are unchanged (pinned).
def cmd_apply(args):
    """Write the decided items and file operations of the proposals in `args` (none: every proposal in staging) to
    tracker.db under one apply_id, after a dry run and a backup. All or nothing; a recode is applied on its own
    (BL-111). Then moves finished proposals to applied/ and rebuilds the dashboard, Excel export and search index.
    """
    work = _load_work(args)
    if not work:
        print("Nothing to apply: no decided items.")
        return 0
    work = recode_barrier(work)        # BL-111: a recode is applied on its own
    if work is None:
        return 1
    con = connect()
    blocked, held = _validate_work(con, work)     # dry run first: if any approved item is invalid, nothing is written
    if blocked:
        _report_blocked(work, blocked)
        return 1
    backup = backup_db("apply")
    debuglog.info("tracker", f"apply: backup {paths.rel(backup)}; proposals {', '.join(p.name for p, _ in work)}")
    file_records = []
    summary = {"written": 0, "rejected": 0, "held": 0, "filed": 0}
    con.execute("BEGIN IMMEDIATE")
    try:
        cur = con.execute("INSERT INTO applies (at, proposals, file_ops) VALUES (?, ?, ?)",
                          (now(), json.dumps([paths.rel(p) for p, _ in work]), "[]"))
        apply_id = cur.lastrowid
        for p, data in work:
            via = via_for(p, data)
            for item in data.get("items", []):
                _apply_item(con, p, data, item, held, apply_id, via, summary)
            _apply_blocks(data, apply_id, summary, file_records, p)
        con.execute("UPDATE applies SET file_ops = ? WHERE apply_id = ?", (json.dumps(file_records), apply_id))
        con.execute("COMMIT")
    except Exception as e:
        con.execute("ROLLBACK")
        _report_rolled_back(e, file_records, backup)
        return 1
    _finish_apply(work, apply_id, summary)
    return 0


def _load_work(args):
    """[(proposal path, data)] for the proposals named (or every staged one) that have decided items."""
    if args:
        props = [resolve_proposal(a) for a in args]
    else:
        props = sorted(p.resolve() for p in paths.STAGING.glob("proposed-*.json"))
    work = []
    for p in props:
        data = load(p)
        for n, d in fill_raised(data):   # BL-26; kept in the proposal when it's saved after apply
            print(f"{p.name} item {n}: Raised set to {shown(d)} (source or staging date)")
        items, blks = decided(data)
        if items or blks:
            work.append((p, data))
    return work


def _validate_work(con, work):
    """(problems that stop the apply, {(path, n): (kind, reason)} items to hold): the dry run, the file operations and
    the rejections, in that order. Invalid items are flagged in their proposals."""
    blocked, held = [], {}
    written = {}    # path -> the text an earlier proposal in this apply will leave there
    all_problems = dry_run_all(con, [(p, data, via_for(p, data)) for p, data in work], only_approved=True)
    for p, data in work:
        for n, (kind, reason) in all_problems[p].items():
            if kind == "invalid":
                blocked.append(f"{p.name} item {n}: {reason}")
                item = next(i for i in data["items"] if i.get("n") == n)
                debuglog.warn("tracker", f"invalid {p.name} item {n} ({item.get('table')} {item.get('id') or 'new'}): {debuglog.rule(reason)}")
                set_flag(item, "invalid", True, reason)
            else:
                held[(p, n)] = (kind, reason)
        blocked += _file_op_problems(p, data, written)
        blocked += archive_problems(p, data)           # BL-09: an archive or restore comes with its own folder move
        blocked += minutes_draft_problems(p, data)     # BL-260 point 4: minutes with no draft are never filed
    for p, data in work:                                                   # BL-133 stage B: a rejection's reason and duplicate
        blocked += _rejection_problems(con, p, data)
    return blocked, held


# ===== BL-260 point 4 (fix-minutes-approve) =====
NO_DRAFT_MSG = "No draft minutes to file: reject these minutes in Review and process the meeting again"


def minutes_draft_missing(blk):
    """True when a minutes block (not a quick note) has no Word draft, or its draft file has gone: it can't be approved."""
    if not blk or blk.get("note") or blk.get("applied"):
        return False
    draft = blk.get("draft")
    return not (draft and paths.resolve(draft).is_file())


def minutes_draft_problems(p, data):
    """Validation: a minutes approval with no draft is refused. Nothing is filed and processed.txt is untouched; the
    decision goes back to pending (saved when the apply stops), so the row stays in Review to be rejected."""
    blk = data.get("meeting")
    if not blk or blk.get("minutes_decision") != "approved" or not minutes_draft_missing(blk):
        return []
    blk["minutes_decision"] = "pending"
    blk.pop("decided_in", None)
    debuglog.warn("tracker", f"minutes approval refused in {p.name}: no draft minutes")
    return [f"{p.name} minutes: {NO_DRAFT_MSG} ({blk.get('title') or blk.get('key') or 'untitled'})."]
# ===== end BL-260 point 4 =====


def _file_op_problems(p, data, written):
    problems = []
    for blk, field in blocks(data):
        if blk.get(field) in ("approved", "rejected") and not blk.get("applied"):
            for fop in selected_ops(blk, field):
                try:
                    check_file_op(fop, blk)
                    check_write_base(fop, written)
                except Invalid as e:
                    problems.append(f"{p.name} {field}: {e}")
                    debuglog.warn("tracker", f"file operation refused in {p.name} ({field}): {debuglog.rule(e)}")
    return problems


def _rejection_problems(con, p, data):
    problems = []
    for item in data.get("items", []):
        if item.get("applied") or item.get("decision") != "rejected":
            continue
        try:
            check_reject(con, item)
        except Invalid as e:
            problems.append(f"{p.name} item {item.get('n')}: {e}")
            set_flag(item, "invalid", True, str(e))
    return problems


def _report_blocked(work, blocked):
    debuglog.warn("tracker", f"apply stopped, nothing written: {len(blocked)} problem(s) in {len(work)} proposal(s)")
    for p, data in work:
        save(p, data)
    print("Apply stopped. Nothing was written.")
    for b in blocked:
        print("  " + b)


def _record_rejection(con, item, apply_id, via, summary):
    fp = fingerprint(item)
    reason, dup = reject_reason(item)                     # BL-133 stage B: why, and what it repeats
    old = _redecided_row(con, item, apply_id, via, keep=fp)                  # BL-315: a reject decided again
    if old is not None:
        _change_rejection(con, old, reason, dup, apply_id, via)
    elif not con.execute("SELECT 1 FROM rejected WHERE fingerprint = ?", (fp,)).fetchone():
        con.execute("INSERT INTO rejected (fingerprint, rejected_at, via, reason, duplicate_of) VALUES (?,?,?,?,?)",
                    (fp, now(), via, reason, dup))
        log(con, apply_id, "rejected", fp, "fingerprint", None, fp, "insert", via)
    item["applied"] = apply_id
    summary["rejected"] += 1


# ===== BL-315 (v1.9.2): a reject decided again ===== review.py's unreject, rereason and approve-instead put an applied rejection back
# in staging, marked `redecide` {fingerprint, apply_id} (the row it left in `rejected`). At the next apply the row follows the latest
# choice: approved, the row is removed (logged with the row as JSON, so undo puts it back); rejected again, its reason and duplicate_of
# are updated (logged per field, so undo restores them). Undo returns the item to Review pending, as for any undone rejection, with the
# row as it was. No schema change: `rejected` keeps its columns, and change_log holds the old values.
def _redecided_row(con, item, apply_id, via, keep=None):
    """The `rejected` row an item decided again still owns, or None. An approval (keep=None) or a changed fingerprint removes the row
    (logged); a rejection with the same fingerprint returns it to be updated."""
    mark = item.get("redecide")
    fp = mark.get("fingerprint") if isinstance(mark, dict) else None
    if not fp:
        return None
    row = con.execute("SELECT * FROM rejected WHERE fingerprint = ?", (fp,)).fetchone()
    if row is None:
        return None
    if keep == fp:
        return row
    con.execute("DELETE FROM rejected WHERE fingerprint = ?", (fp,))
    log(con, apply_id, "rejected", fp, REMOVED, json.dumps(dict(row)), None, "update", via)
    return None


def _change_rejection(con, row, reason, dup, apply_id, via):
    """A rejection's new reason and duplicate, each changed field logged with its old value."""
    for field, new in (("reason", reason), ("duplicate_of", dup)):
        if row[field] != new:
            con.execute(f"UPDATE rejected SET {field} = ? WHERE fingerprint = ?", (new, row["fingerprint"]))
            log(con, apply_id, "rejected", row["fingerprint"], field, row[field], new, "update", via)


def _reverse_rejection(con, key, changes):
    """Undo of `rejected` rows: an insert removed, a removed row put back, a changed reason restored (newest change first)."""
    for c in reversed(changes):
        if c["op"] == "insert":
            con.execute("DELETE FROM rejected WHERE fingerprint = ?", (key,))
        elif c["field"] == REMOVED:
            old = json.loads(c["old_value"])
            back = {k: v for k, v in old.items() if k in columns(con, "rejected")}
            con.execute(f"INSERT OR REPLACE INTO rejected ({', '.join(back)}) VALUES ({', '.join('?' * len(back))})",
                        list(back.values()))
        elif c["field"] in ("reason", "duplicate_of"):
            con.execute(f"UPDATE rejected SET {c['field']} = ? WHERE fingerprint = ?", (c["old_value"], key))
# ===== end BL-315 =====


def _hold_conflict(con, item, reason):
    """Hold an item for review: flagged, back to pending, with the database's row beside it."""
    set_flag(item, "conflict", True)
    item["conflict_reason"] = reason
    item["decision"] = "pending"
    row = fetch(con, item["table"], item["id"])
    item["current"] = dict(row) if row else None


def _cite_transcript(data, item):
    """No minutes filed: an item that cites the minutes cites the filed transcript instead."""
    meeting = data.get("meeting") or {}
    if meeting.get("minutes_decision") == "rejected":
        src = (item.get("values") or {}).get("source", "")
        for minutes_copy, transcript_copy in (meeting.get("source_map") or {}).items():
            if src.startswith(minutes_copy):
                item["values"]["source"] = transcript_copy + src[len(minutes_copy):]


# ===== BL-322 (v193-sneak-peek-server) ===== a link to a new item of the same proposal. A proposal never predicts an ID; a link's
# `from_item` or `to_item` may instead be `@n`: the ID tracker.py gives item n of the same proposal, a new item written before it.
# So Sneak peek's follow-on action (or risk, or promise) and its link go in one apply, and one undo takes both.
SIBLING_REF = re.compile(r"@(\d+)")


def sibling_refs(item, ids):
    """The item with its `@n` link ends replaced from ids ({n: ID given}); the item itself when it has none. Raises Invalid when
    n isn't a new item written before it in the same proposal."""
    if item.get("table") != "links" or item.get("op") != "new":
        return item
    values, hit = dict(item.get("values") or {}), False
    for end in ("from_item", "to_item"):
        m = SIBLING_REF.fullmatch(str(values.get(end) or ""))
        if m:
            n = int(m.group(1))
            if n not in ids or n == item.get("n"):
                raise Invalid(f"{end} {values[end]} refers to item {n}, which isn't a new item written before it in this proposal")
            values[end], hit = ids[n], True
    return {**item, "values": values} if hit else item


def resolve_sibling_refs(data, item, apply_id):
    """In an apply: a link item's `@n` ends become the IDs this apply gave (kept in the proposal, the `@n` under `refs`)."""
    if item.get("table") != "links" or item.get("op") != "new":
        return
    ids = {i.get("n"): i["result_id"] for i in data.get("items", [])
           if i.get("op") == "new" and i.get("applied") == apply_id and i.get("result_id")}
    done = sibling_refs(item, ids)
    if done is not item:
        item["refs"] = {k: item["values"][k] for k in ("from_item", "to_item")
                        if SIBLING_REF.fullmatch(str(item["values"].get(k) or ""))}
        item["values"] = done["values"]


def unresolve_sibling_refs(item):
    """Undo's half: a link item returned to pending gets its `@n` ends back from `refs`. The ID the apply gave is never kept,
    because an undone ID is given again to the next new item, and a re-apply must link the item it creates then."""
    refs = item.pop("refs", None)
    if isinstance(refs, dict) and item.get("table") == "links" and isinstance(item.get("values"), dict):
        for end in ("from_item", "to_item"):
            if SIBLING_REF.fullmatch(str(refs.get(end) or "")):
                item["values"][end] = refs[end]
# ===== end BL-322 =====


def _write_approved(con, p, item, apply_id, via, summary):
    con.execute("SAVEPOINT item")
    try:
        _redecided_row(con, item, apply_id, via)                   # BL-315: approved instead of rejected (rolled back with a conflict)
        item["result_id"] = write_item(con, item, apply_id, via)
        con.execute("RELEASE item")
    except Conflict as e:      # safety net: hold it for review rather than abort the apply
        con.execute("ROLLBACK TO item")
        con.execute("RELEASE item")
        _hold_conflict(con, item, str(e))
        summary["held"] += 1
        debuglog.info("tracker", f"held {p.name} item {item.get('n')} (conflict)")
        return
    item["applied"] = apply_id
    set_flag(item, "invalid", False)
    summary["written"] += 1


def _apply_item(con, p, data, item, held, apply_id, via, summary):
    """One item of the apply: a rejection recorded, a held item held, an approved item written; anything else waits."""
    if item.get("applied"):
        return
    d = item.get("decision")
    if d == "rejected":
        _record_rejection(con, item, apply_id, via, summary)
    elif d == "approved":
        if (p, item.get("n")) in held:
            kind, reason = held[(p, item.get("n"))]
            if kind == "conflict":
                _hold_conflict(con, item, reason)
            summary["held"] += 1
            debuglog.info("tracker", f"held {p.name} item {item.get('n')} ({kind})")
            return
        _cite_transcript(data, item)
        resolve_sibling_refs(data, item, apply_id)        # BL-322: `@n` becomes the ID item n was given in this apply
        _write_approved(con, p, item, apply_id, via, summary)


def _apply_blocks(data, apply_id, summary, file_records, prop=None):
    """The proposal's decided file blocks (minutes, reports): their file operations, and the processed.txt lines. prop: the
    proposal file (#124 F3)."""
    processed = []
    for blk, field in blocks(data):
        if blk.get("applied") or blk.get(field) not in ("approved", "rejected"):
            continue
        ops = selected_ops(blk, field)
        run_file_ops(apply_id, blk, field, ops, file_records, prop)
        if ops:
            summary["filed"] += 1
        if field == "minutes_decision" and blk.get("key"):
            filed = [f["to"] for f in ops if f.get("op") == "copy"]
            n_items = sum(1 for i in data.get("items", []) if i.get("applied") == apply_id
                          and i.get("decision") == "approved")
            processed.append(f"{today()} | {blk['key']} | {'; '.join(filed) or 'not filed'} "
                             f"| {n_items}\n")
        blk["applied"] = apply_id
    if processed:
        with open(paths.PROCESSED, "a", encoding="utf-8") as f:
            f.writelines(processed)
        file_records.append({"op": "processed", "lines": processed})


def _report_rolled_back(e, file_records, backup):
    debuglog.exception("tracker", "apply failed, rolled back")
    report = []
    reverse_file_ops(file_records, report)
    print(f"Apply failed; nothing was written. {type(e).__name__}: {e}")
    for r in report:
        print("  " + r)
    print(f"(The database backup from before the apply is {paths.rel(backup)}.)")


def _finish_apply(work, apply_id, summary):
    """Save the proposals (finished ones move to applied/), print the summary, log it, rebuild the views."""
    paths.APPLIED.mkdir(parents=True, exist_ok=True)
    for p, data in work:
        if data.get(CARD_MARK) is True:           # BL-289: the card's own apply, the one an undo leaves out of Review
            data[CARD_MARK] = apply_id
        if finished(data):
            save(p, data)
            p.replace(paths.APPLIED / p.name)
        else:
            save(p, data)
    pending = sum(1 for p in paths.STAGING.glob("proposed-*.json")
                  for i in load(p).get("items", []) if not i.get("applied"))
    print(f"Apply {apply_id}: written {summary['written']}, filed {summary['filed']}, "
          f"rejected {summary['rejected']}, held {summary['held']}, {pending} still pending.")
    by_table = {}
    for _, d in work:
        for i in d.get("items", []):
            if i.get("applied") == apply_id and i.get("decision") == "approved":
                by_table[i.get("table")] = by_table.get(i.get("table"), 0) + 1
    debuglog.info("tracker", f"apply {apply_id}: written {summary['written']} ({', '.join(f'{t} {n}' for t, n in sorted(by_table.items())) or 'none'}), "
                  f"filed {summary['filed']}, rejected {summary['rejected']}, held {summary['held']}, {pending} still pending")
    after_apply()
# ===== end BL-229 step 3 (apply) =====


# ===== BL-327: after an apply, each step timed in the debug log; the live server runs the two slow ones after it answers =====
AFTER_ENV = "CREAITE_AFTER_APPLY"               # "background": the live server runs after_apply_slow itself, after answering
AFTER_DUE = "after-apply-due"                   # in system/search/: the slow steps are owed (the server's worker clears it)


def after_due_flag():
    """The marker that says an apply's index refresh and OneDrive copy are still to run (BL-327)."""
    return paths.SEARCH_DIR / AFTER_DUE


def _timed(step, fn):
    """Run one after-apply step and log how long it took (BL-327); its result."""
    t0 = time.monotonic()
    try:
        return fn()
    finally:
        debuglog.info("tracker", f"after apply: {step} in {time.monotonic() - t0:.2f}s")


def after_apply_slow():
    """The steps a save needn't wait for: the off-laptop copy of the daily backup (BL-85, BL-323; only when the projects live
    outside the vault) and the search index (BL-07, incremental since BL-327). Each is timed in the debug log; neither raises."""
    r = _timed("offsite copy", offsite_copy)
    if r["error"]:
        print(f"Note: off-laptop backup copy not made: {r['error']}")
    _timed("search index", refresh_index)


def after_apply():
    """After an apply or undo: the OneDrive copy and the search index (after_apply_slow), then rebuild the dashboard and
    re-export Excel (each only once it exists), every step timed in the debug log (BL-327). Run by the live server
    (CREAITE_AFTER_APPLY=background), the slow steps are left to its background worker, marked as owed, so the save answers
    as soon as the tracker is written and the dashboard data rebuilt."""
    if os.environ.get(AFTER_ENV) == "background":
        try:
            paths.SEARCH_DIR.mkdir(parents=True, exist_ok=True)
            after_due_flag().touch()
        except OSError:                                # can't mark it: do them now, as before
            after_apply_slow()
    else:
        after_apply_slow()
    for script, args in (("build_dashboard.py", []), ("excel_sync.py", ["export"])):
        s = paths.ROOT / "system" / "scripts" / script
        if s.exists():
            r = _timed(" ".join([script, *args]), lambda s=s, args=args: subprocess.run(
                [sys.executable, str(s), *args], cwd=paths.ROOT, capture_output=True, text=True))
            if r.returncode == 3:      # paused on purpose (e.g. unimported Excel edits); say why
                print(f"Note: {r.stdout.strip()}")
            elif r.returncode != 0:
                print(f"Note: {script} {' '.join(args)} failed: {(r.stderr or r.stdout).strip()[:300]}")
# ===== end BL-327 (after apply) =====


# ── Undo ──────────────────────────────────────────────────────────────────────

# ===== BL-229 step 3b: cmd_undo in steps. One BEGIN IMMEDIATE around every reversal, as before; messages unchanged (pinned).
def cmd_undo():
    """Reverse the most recent apply not yet undone: its database changes (where nothing changed them since) and its
    file operations, after a backup.
    """
    con = connect()
    a = con.execute("SELECT * FROM applies WHERE undone_at IS NULL ORDER BY apply_id DESC LIMIT 1").fetchone()
    if not a:
        print("Nothing to undo.")
        return 0
    apply_id = a["apply_id"]
    rows = con.execute("SELECT rowid, * FROM change_log WHERE apply_id = ? AND op != 'undo' ORDER BY rowid",
                       (apply_id,)).fetchall()
    if rows and all(r["via"] == MIGRATE_VIA for r in rows):           # BL-186: Missed can't come back
        print(f"Apply {apply_id} is the 1.5.0 migration that retired Missed (those milestones are now Overdue). It can't be "
              "undone, as Missed no longer exists; change a milestone's state instead. Nothing was changed.")
        return 1
    by_item = {}
    for r in rows:
        by_item.setdefault((r["tbl"], r["item_id"]), []).append(r)
    later = {k for k, ch in by_item.items() if _changed_since(con, *k, ch)}

    backup = backup_db("undo")
    debuglog.info("tracker", f"undo {apply_id}: backup {paths.rel(backup)}, {len(by_item)} item(s) to reverse, {len(later)} changed since")
    report, undone = [], set()
    con.execute("BEGIN IMMEDIATE")
    try:
        for (table, key), changes in reversed(list(by_item.items())):  # newest first: rows before their project
            if (table, key) in later:
                report.append(f"skipped {key}: changed since that apply")
                continue
            _reverse_item(con, table, key, changes)
            for c in changes:
                log(con, apply_id, table, key, c["field"], c["new_value"], c["old_value"], "undo", "undo")
            undone.add((table, key))
        con.execute("UPDATE applies SET undone_at = ? WHERE apply_id = ?", (now(), apply_id))
        con.execute("COMMIT")
    except Exception as e:
        con.execute("ROLLBACK")
        debuglog.exception("tracker", f"undo {apply_id} failed, rolled back")
        print(f"Undo failed; nothing was changed. {type(e).__name__}: {e}")
        return 1

    reverse_file_ops(json.loads(a["file_ops"] or "[]"), report)
    _return_proposals(json.loads(a["proposals"]), apply_id, later, report)
    print(f"Undid apply {apply_id}: {len(undone)} item(s) reversed.")
    debuglog.info("tracker", f"undid apply {apply_id}: {len(undone)} item(s) reversed, {len(report)} note(s)")
    for r in report:
        print("  " + r)
    after_apply()
    return 0


def _changed_since(con, table, key, changes):
    """True if any field no longer holds the value this apply wrote."""
    if table in ("rejected", "recode"):
        return False
    row = fetch(con, table, key)
    if changes[-1]["field"] == REMOVED:           # a deleted links / item_labels / labels row: unchanged while it is still gone
        return row is not None
    if row is None:
        return True
    latest = {}                                   # a field changed twice in this apply: judge it by its last value
    for c in changes:
        latest[c["field"]] = c["new_value"]
    return any(f in row.keys() and (None if row[f] is None else str(row[f])) != v for f, v in latest.items())


def _reverse_item(con, table, key, changes):
    """Put one item back as it was before the apply: a recode or a rejection reversed, an insert deleted, a deleted row
    put back, or the changed fields restored."""
    if table == "recode":
        undo_recode(con, changes)                 # BL-111
    elif table == "rejected":
        _reverse_rejection(con, key, changes)     # BL-315: an insert removed, a removed row put back, a reason restored
    elif changes[0]["op"] == "insert" or any(c["field"] == REMOVED for c in changes):
        con.execute(f"DELETE FROM {table} WHERE {where_key(table)}", key_values(table, key))
        if changes[0]["field"] == REMOVED:         # the row existed before this apply: put it back as it was
            old = json.loads(changes[0]["old_value"])
            back = {k: v for k, v in old.items() if k in columns(con, table) and v is not None}
            con.execute(f"INSERT INTO {table} ({', '.join(back)}) VALUES ({', '.join('?' * len(back))})",
                        list(back.values()))
    else:
        cols = set(columns(con, table))
        restore = {}                              # a field changed twice in this apply goes back to its first old value
        for c in changes:
            if c["field"] in cols:
                restore.setdefault(c["field"], c["old_value"])
        con.execute(f"UPDATE {table} SET {', '.join(f'{f} = ?' for f in restore)} "
                    f"WHERE {where_key(table)}", list(restore.values()) + key_values(table, key))


CARD_MARK = "applied_on_card"     # BL-289: set only by the live server, on a change Alan approved on ask creaite's card


def _mark_card_undone(p, data, apply_id):
    """BL-289: a card's proposal stays in applied/, marked undone; BL-322: its links go back to `@n` (never a reused ID)."""
    for item in data.get("items", []):
        if item.get("applied") == apply_id:
            unresolve_sibling_refs(item)
    data["undone"] = apply_id
    save(p, data)


def _kept_out_of_review(p, data, apply_id, report):
    """True (and the proposal marked undone) for one that was never in Review, so undoing it leaves nothing there: a change
    approved on ask creaite's card (BL-289), or the daily archiving (BL-10)."""
    if data.get(CARD_MARK) == apply_id and not isinstance(data.get(CARD_MARK), bool):
        why = "was approved on ask creaite's card"
    elif data.get("source_run") == AGE_SOURCE and all(i.get("op") == AGE_OP for i in data.get("items", [])):
        why = "was the daily archiving"
    else:
        return False
    _mark_card_undone(p, data, apply_id)
    report.append(f"proposal {p.name} {why}: not returned to Review")
    return True


def _return_proposals(proposals, apply_id, later, report):
    """Return the apply's proposals to staging with the undone items (and file blocks) pending again. BL-289: a change
    approved on ask creaite's card was never in Review, so undoing it leaves nothing there: its proposal stays in
    applied/, marked undone, and asking again offers the same card."""
    for rel_prop in proposals:
        name = Path(rel_prop).name
        p = paths.STAGING / name if (paths.STAGING / name).exists() else paths.APPLIED / name
        if not p.exists():
            report.append(f"proposal {name} not found; items not returned to pending")
            continue
        data = load(p)
        if _kept_out_of_review(p, data, apply_id, report):
            continue
        for item in data.get("items", []):
            if item.get("applied") != apply_id:
                continue
            key = item.get("result_id") or item.get("id")
            if item.get("decision") == "rejected" or (item.get("table"), key) not in later:
                item.pop("applied", None)
                item.pop("result_id", None)
                unresolve_sibling_refs(item)            # BL-322: back to `@n`, so a re-apply links the item it creates
                item["decision"] = "pending"
        for blk, field in blocks(data):
            if blk.get("applied") == apply_id:
                blk.pop("applied", None)
                blk[field] = "pending"
        save(p, data)
        if p.parent == paths.APPLIED:
            p.replace(paths.STAGING / name)
# ===== end BL-229 step 3b (undo) =====


# ===== BL-164 (sprint-rail): undo several past changes ===================================================================
# Activity can put back chosen past changes (change_log rows), not only the latest whole apply. It is built from cmd_undo's
# pieces (by item, "changed since", the old values restored, backup_db, one transaction) but leaves cmd_undo and cmd_apply as
# they are. The rule: a field goes back to what it was before that change only where it still holds the value that change
# gave it; otherwise the entry is skipped and listed. A change that created an item removes it only if nothing has been
# added to it since and nothing refers to it. Every restore goes through write_item (validated and logged like any
# update), and the whole run is ONE new apply whose rows carry via = "revert:<rowid>,<rowid>,…" (the rows it reverted), so
# no schema change is needed, Activity can mark those entries "undone", and "undo last apply" (or its row's Undo) reverses
# the revert itself. Undos, rejections, recodes, history-only notes and settings lines (not in change_log) can't be chosen.

REVERT_VIA = "revert:"
REVERT_CREATED = ("actions", "raid", "decisions", "milestones", "promises")     # a creation of these may be undone
REVERT_REFS = (("actions", "milestone"), ("raid", "milestone"), ("decisions", "replaces"), ("links", "from_item"),
               ("links", "to_item"), ("item_labels", "item_id"))             # columns that hold another item's ID


def reverted_rowids(con):
    """change_log rowids put back by a revert apply that is still in force (BL-164)."""
    out = set()
    for (via,) in con.execute("SELECT DISTINCT c.via FROM change_log c JOIN applies a ON a.apply_id = c.apply_id "
                              "WHERE c.via LIKE 'revert:%' AND a.undone_at IS NULL"):
        out |= {int(x) for x in via[len(REVERT_VIA):].split(",") if x.strip().isdigit()}
    return out


def holds(con, table, key, changes):
    """cmd_undo's "changed since", turned round: True while every field still holds the value these rows wrote.
    (The same test as the one nested in cmd_undo, which is left as it is.)"""
    row = fetch(con, table, key)
    if changes[-1]["field"] == REMOVED:                # a deleted row: it holds while it is still gone
        return row is None
    if row is None:
        return False
    return not any(c["field"] in row.keys() and (None if row[c["field"]] is None else str(row[c["field"]])) != c["new_value"]
                   for c in changes)


def referred_to(con, key):
    """Where an item is named by another row (a milestone on an action, a link, a label, a decision it replaces)."""
    for table, col in REVERT_REFS:
        if col in columns(con, table) and con.execute(f"SELECT 1 FROM {table} WHERE {col} = ? LIMIT 1", (key,)).fetchone():
            return table
    return None


def changed_after(con, rowid, table, key):
    """True if a later change still in force touched the item (or a row keyed by it, such as its labels)."""
    return bool(con.execute(
        "SELECT 1 FROM change_log c LEFT JOIN applies a ON a.apply_id = c.apply_id WHERE c.rowid > ? AND c.op != 'undo' "
        "AND (a.undone_at IS NULL) AND c.via NOT LIKE 'revert:pending' AND ((c.tbl = ? AND c.item_id = ?) OR c.item_id LIKE ?) LIMIT 1",
        (rowid, table, key, key + "|%")).fetchone())


def why_not(con, r, reverted, done_ids):
    """Why a change_log row can't be chosen at all, or None."""
    if r is None:
        return "not in the change log"
    if r["op"] == "undo" or r["via"] == "undo" or str(r["via"]).startswith(REVERT_VIA):
        return "is itself an undo"
    if r["tbl"] in ("rejected", "recode") or r["tbl"] not in TABLES:
        return "can't be undone here; use “undo last apply”"
    if r["undone_at"]:
        return "its apply was undone already"
    if r["rowid"] in reverted or r["rowid"] in done_ids:
        return "already undone"
    if r["field"] in ("note", "updated_at") or (r["field"] != REMOVED and r["field"] not in columns(con, r["tbl"])):
        return "history only; nothing to put back"
    if r["op"] == "insert" and r["tbl"] not in REVERT_CREATED:
        return "a new " + r["tbl"].rstrip("s") + " can't be removed here; use “undo last apply”"
    return None


def age_archive_refusal(r):
    """BL-10: why the daily archiving's change can't be chosen (its own Undo, or an edit, brings the item back), or None."""
    if r["field"] == "archived" and is_age_archive_via(r["via"]):
        return "archived for its age: use Undo on the archive apply, or edit the item to bring it back"
    return None


def is_age_archive_via(via):
    """BL-10: whether a change_log source is the daily archiving: "archive" (via_for), or its proposal's file name as
    recorded before v1.9.5's fix (proposed-<stamp>-archive.json)."""
    via = str(via or "")
    return via == AGE_SOURCE or bool(re.fullmatch(r"proposed-[\d-]+-archive(-\d+)?\.json", via))


def revert_plan(con, rowids, apply_id, via):
    """Put back the chosen rows inside the caller's transaction. Returns (done, skipped): lists of dicts."""
    reverted = reverted_rowids(con)
    found = {r["rowid"]: r for r in con.execute(
        f"SELECT c.rowid AS rowid, c.*, a.undone_at FROM change_log c LEFT JOIN applies a ON a.apply_id = c.apply_id "
        f"WHERE c.rowid IN ({','.join('?' * len(rowids))})", rowids)} if rowids else {}
    done, skipped, done_ids = [], [], set()
    groups = {}                                        # (apply, table, item) → the chosen rows of that apply on that item
    for rid in sorted(set(rowids), reverse=True):     # newest first, so two changes to one field go back in turn
        r = found.get(rid)
        why = why_not(con, r, reverted, done_ids) or age_archive_refusal(r)
        if why:
            skipped.append({"rowid": rid, "id": r["item_id"] if r else "", "field": r["field"] if r else "", "why": why})
            continue
        groups.setdefault((r["apply_id"], r["tbl"], r["item_id"]), []).append(r)
    new_apply = apply_id
    for (apply_id, table, key), rows_ in sorted(groups.items(), key=lambda kv: -max(x["rowid"] for x in kv[1])):
        con.execute("SAVEPOINT revert_item")
        try:
            got = revert_group(con, apply_id, table, key, rows_, new_apply, via)
        except (Invalid, Conflict) as e:
            con.execute("ROLLBACK TO revert_item")
            got = [], [{"rowid": x["rowid"], "id": key, "field": x["field"], "why": str(e)} for x in rows_]
        con.execute("RELEASE revert_item")
        done += got[0]
        skipped += got[1]
        done_ids |= {d["rowid"] for d in got[0]}
    return done, skipped


def revert_group(con, apply_id, table, key, rows_, new_apply, via):
    """One item's chosen rows from one apply (`apply_id`), written under `new_apply`. Returns (done, skipped)."""
    entry = lambda r, **k: {"rowid": r["rowid"], "id": key, "field": r["field"], **k}  # noqa: E731
    created = [r for r in rows_ if r["op"] == "insert"]
    if created:                                        # the change created the item: remove it, only if untouched since
        made = con.execute("SELECT rowid, * FROM change_log WHERE apply_id = ? AND tbl = ? AND item_id = ? AND op = 'insert' "
                           "ORDER BY rowid", (apply_id, table, key)).fetchall()
        why = ("has changed since: left as it is" if not holds(con, table, key, made) or changed_after(con, made[-1]["rowid"], table, key)
               else None)
        ref = None if why else referred_to(con, key)
        if why or ref:
            return [], [entry(r, why=why or f"something refers to it now ({ref}): left as it is") for r in rows_]
        current = fetch(con, table, key)
        con.execute(f"DELETE FROM {table} WHERE {where_key(table)}", key_values(table, key))
        log(con, new_apply, table, key, REMOVED, json.dumps(dict(current), ensure_ascii=False), None, "update", via)
        return [entry(r, change="removed", text="") for r in rows_], []
    removed = [r for r in rows_ if r["field"] == REMOVED]
    if removed:                                        # the change deleted a link or a label: put it back while it is still gone
        r = removed[0]
        if fetch(con, table, key) is not None:
            return [], [entry(x, why="is back already: left as it is") for x in rows_]
        old = json.loads(r["old_value"])
        back = {k: v for k, v in old.items() if k in columns(con, table) and v is not None}
        check_row(con, table, dict(back), set(back))
        con.execute(f"INSERT INTO {table} ({', '.join(back)}) VALUES ({', '.join('?' * len(back))})", list(back.values()))
        for f, v in back.items():
            log(con, new_apply, table, key, f, None, v, "insert", via)
        return [entry(x, change="put back") for x in rows_], []
    done, skipped, changes = [], [], {}
    row = fetch(con, table, key)
    if row is None:
        return [], [entry(r, why="no longer exists") for r in rows_]
    for r in rows_:
        now_v = None if row[r["field"]] is None else str(row[r["field"]])
        if now_v != r["new_value"]:
            skipped.append(entry(r, why="has changed since: left as it is"))
        else:
            changes[r["field"]] = r["old_value"]
    if table == "projects" and "health" in changes and "health_reason" not in changes:    # a health change takes its reason back too
        hr = con.execute("SELECT * FROM change_log WHERE apply_id = ? AND tbl = 'projects' AND item_id = ? AND field = 'health_reason' "
                         "AND op = 'update' ORDER BY rowid DESC LIMIT 1", (apply_id, key)).fetchone()
        if hr and (row["health_reason"] if row["health_reason"] is None else str(row["health_reason"])) == hr["new_value"]:
            changes["health_reason"] = hr["old_value"]
    if not changes:
        return done, skipped
    write_item(con, {"table": table, "op": "update", "id": key, "changes": changes}, new_apply, via)
    after = fetch(con, table, key)
    for r in rows_:
        if r["field"] not in changes:
            continue
        now_v = None if after[r["field"]] is None else str(after[r["field"]])
        if now_v == r["old_value"]:
            done.append(entry(r, change="set", **{"from": r["new_value"], "to": r["old_value"]}))
        else:                                          # derived (a RAID priority, a closed date): it follows other fields
            skipped.append(entry(r, why="it follows other fields: left as it is"))
    return done, skipped


def cmd_undo_changes(args):
    """Put back several past changes (change_log rowids) where they still hold the value that change gave them,
    as one new apply that undo can reverse (BL-164). `--dry-run` shows it; backed up first.
    """
    dry, as_json = "--dry-run" in args, "--json" in args
    rest = [a for a in args if a not in ("--dry-run", "--json")]
    if not rest or not all(a.isdigit() for a in rest):
        print("Usage: tracker.py undo-changes [--dry-run] [--json] <rowid> [<rowid> …]")
        return 2
    rowids = sorted({int(a) for a in rest})
    con = connect()
    backup = None if dry else backup_db("revert")
    con.execute("BEGIN IMMEDIATE")
    try:
        cur = con.execute("INSERT INTO applies (at, proposals, file_ops) VALUES (?, ?, ?)", (now(), "[]", "[]"))
        apply_id = cur.lastrowid
        done, skipped = revert_plan(con, rowids, apply_id, REVERT_VIA + "pending")
        via = REVERT_VIA + ",".join(str(d["rowid"]) for d in sorted(done, key=lambda d: d["rowid"]))
        con.execute("UPDATE change_log SET via = ? WHERE apply_id = ?", (via, apply_id))
        if dry or not done:
            con.execute("ROLLBACK")
            apply_id = None
        else:
            con.execute("COMMIT")
    except Exception as e:
        con.execute("ROLLBACK")
        debuglog.exception("tracker", "undo-changes failed, rolled back")
        msg = f"Nothing was changed. {type(e).__name__}: {e}"
        print(json.dumps({"ok": False, "message": msg}) if as_json else msg)
        return 1
    n, k = len(done), len(skipped)
    message = (("Would undo" if dry else "Undid") + f" {n} change{'' if n == 1 else 's'}" + (f", skipped {k}" if k else "")) if n \
        else "Nothing to undo" + (f": {k} skipped" if k else "")
    if not dry and done:
        debuglog.info("tracker", f"undo-changes: apply {apply_id}, {n} put back, {k} skipped, backup {paths.rel(backup)}")
        after_apply()
    if as_json:
        print(json.dumps({"ok": True, "dry_run": dry, "apply_id": apply_id, "done": done, "skipped": skipped, "message": message},
                         ensure_ascii=False))
    else:
        print(message + (f" (apply {apply_id})" if apply_id else ""))
        for d in done:
            print(f"  {d['id']} · {d['field'] if d['field'] != REMOVED else 'row'} " +
                  (f"{d.get('from')} → {d.get('to')}" if d.get("change") == "set" else d.get("change", "")))
        for x in skipped:
            print(f"  skipped {x['id'] or x['rowid']}: {x['why']}")
    return 0
# ===== end BL-164 =====


# ── Init, read, index, query ──────────────────────────────────────────────────

def register_projects():
    """Projects from the register's Projects table: (code, name)."""
    out, in_table = [], False
    for line in paths.REGISTER.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_table = line.strip() == "## Projects"
            continue
        if in_table and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and re.fullmatch(CODE_RE, cells[0]):
                out.append((cells[0], cells[1]))
    return out


def schema_tables():
    """{table: CREATE TABLE statement} from schema.sql (ordinary tables only)."""
    sql = paths.SCHEMA.read_text(encoding="utf-8")
    return {m.group(1): m.group(0) for m in
            re.finditer(r"CREATE TABLE IF NOT EXISTS (\w+) \(.*?\n\);", sql, re.S)}


def normalise_sql(sql):
    """A CREATE statement with comments, quotes and spacing removed, for comparing with schema.sql."""
    sql = re.sub(r"--[^\n]*", "", sql)
    sql = sql.replace("IF NOT EXISTS ", "").replace('"', "").rstrip().rstrip(";")  # renames add quotes
    return re.sub(r"\s+", " ", sql).strip()


def outdated_tables(con):
    """Tables whose stored definition differs from schema.sql."""
    stored = {r[0]: r[1] for r in con.execute("SELECT name, sql FROM sqlite_master WHERE type = 'table'")}
    return [t for t, sql in schema_tables().items()
            if t in stored and normalise_sql(stored[t]) != normalise_sql(sql)]


def seed_workstreams(con):
    """BL-58: give each project its workstreams, once. From every project and workstream pair already on actions and
    RAID items, and the per-project keys in settings.json `workstreams` (BL-57: "CODE|name"; hidden ones, and plain
    names hidden everywhere, come in Closed). Leads, keywords and aliases are left for Alan. Running it again adds
    nothing and changes nothing already there. Returns the "CODE name" of each workstream added."""
    codes = {r[0] for r in con.execute("SELECT code FROM projects")}
    wanted = {}                      # (project, name in lower case) → [name, status, source]
    for table in ("actions", "raid"):
        for project, name in con.execute(f"SELECT project, trim(workstream) FROM {table} "
                                         "WHERE trim(COALESCE(workstream, '')) <> '' ORDER BY id"):
            wanted.setdefault((project, name.lower()), [name, "Active", "tracker.py migrate (from items)"])
    kept = paths.load_settings().get("workstreams") or {}
    for key in kept.get("added") or []:
        project, _, name = str(key).partition("|")
        if name.strip():
            wanted.setdefault((project, name.strip().lower()), [name.strip(), "Active", "tracker.py migrate (from settings)"])
    for key in kept.get("hidden") or []:
        project, bar, name = str(key).partition("|")
        if not bar:                  # a plain name, hidden in every project (before BL-57)
            for (p, low), w in wanted.items():
                if low == project.strip().lower():
                    w[1] = "Closed"
        elif name.strip():
            wanted.setdefault((project, name.strip().lower()), [name.strip(), "Closed", "tracker.py migrate (from settings)"])[1] = "Closed"
    added = []
    for (project, _), (name, status, source) in sorted(wanted.items()):
        if project not in codes or con.execute("SELECT 1 FROM workstreams WHERE project = ? AND name = ? COLLATE NOCASE",
                                               (project, name)).fetchone():
            continue
        con.execute("INSERT INTO workstreams (id, project, name, status, created, source, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)", (next_id(con, "workstreams", project), project, name, status, today(),
                                                     source, now()))
        added.append(f"{project} {name}")
    return added


def migrate_workstreams(con):
    """Add the workstreams named in items and old settings to the workstreams table (BL-58), in one transaction."""
    con.execute("BEGIN IMMEDIATE")
    try:
        added = seed_workstreams(con)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    if added:
        print(f"Workstreams added from items and settings ({len(added)}): {', '.join(added)}. Leads and keywords are "
              "yours to fill (Settings › Workstreams or cx-edit).")


def cmd_migrate():
    """Rebuild tables whose rules changed in schema.sql, keeping every row (SQLite's 12-step procedure). Then the engine's own
    settings and rule migrations (update.py tidy), so an update run by an older update.py still gets them."""
    code = migrate_schema()
    tidy_after_update()
    return code


def tidy_after_update():
    """update.tidy(): retired rules and settings migrations of this engine; a failure is logged and never fails the migration."""
    try:
        import update
        changes = update.tidy()
        if changes:
            print("Tidied after the update: " + "; ".join(changes))
    except Exception:  # noqa: BLE001
        debuglog.exception("tracker", "update tidy failed")


def migrate_schema():
    """Bring tracker.db up to schema.sql, keeping every row: rebuild changed tables after a backup, add new
    tables, recreate the search index if needed and move workstreams into their table.
    """
    con = connect()
    if ensure_search_table(con):
        print(f"The search index is recreated with word forms and rebuilt ({build_index()} file(s)).")
    todo = outdated_tables(con)
    if not todo:
        con.executescript(paths.SCHEMA.read_text(encoding="utf-8"))  # adds any new tables
        print("Schema is up to date.")
        migrate_workstreams(con)
        return 0
    backup = backup_db("migrate")
    creates = schema_tables()
    con.execute("PRAGMA foreign_keys = OFF")
    con.execute("BEGIN IMMEDIATE")
    try:
        counts, missed = {}, []
        for t in todo:
            old_cols = columns(con, t)
            if t == "milestones" and "state" not in old_cols:      # BL-186: Missed is retired; see retire_missed
                missed = [dict(r) for r in con.execute("SELECT id, updated_at FROM milestones WHERE status = 'Missed' ORDER BY id")]
                con.execute("UPDATE milestones SET status = 'Planned' WHERE status = 'Missed'")
            con.execute(creates[t].replace(f"CREATE TABLE IF NOT EXISTS {t} (", f"CREATE TABLE {t}__new (", 1))
            keep = [c for c in columns(con, f"{t}__new") if c in old_cols]
            con.execute(f"INSERT INTO {t}__new ({', '.join(keep)}) SELECT {', '.join(keep)} FROM {t}")
            before = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            con.execute(f"DROP TABLE {t}")
            con.execute(f"ALTER TABLE {t}__new RENAME TO {t}")
            after = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            if before != after:
                raise RuntimeError(f"{t}: {before} rows before, {after} after")
            counts[t] = after
        bad = con.execute("PRAGMA foreign_key_check").fetchall()
        if bad:
            raise RuntimeError(f"foreign key check failed: {bad[:3]}")
        retired = retire_missed(con, missed)
        con.execute("COMMIT")
    except Exception as e:
        con.execute("ROLLBACK")
        debuglog.exception("tracker", "migration failed, rolled back")
        print(f"Migration failed; nothing was changed. {type(e).__name__}: {e}")
        return 1
    finally:
        con.execute("PRAGMA foreign_keys = ON")
    con.executescript(paths.SCHEMA.read_text(encoding="utf-8"))  # adds any new tables
    debuglog.info("tracker", f"migrated {', '.join(f'{t} ({n} rows)' for t, n in counts.items())}; backup {paths.rel(backup)}")
    print(f"Migrated {', '.join(f'{t} ({n} rows)' for t, n in counts.items())}. "
          f"Backup from before: {paths.rel(backup)}")
    if retired:
        debuglog.info("tracker", f"migrate: {len(retired)} Missed milestone(s) became Planned, state Overdue (apply {retired[0]})")
        print(f"Missed is retired: {len(retired[1])} milestone(s) ({', '.join(retired[1])}) are now Planned with the state Overdue "
              f"(apply {retired[0]}, in Activity).")
    migrate_workstreams(con)
    return 0


MIGRATE_VIA = "migrate"
MISSED_NOTE = "Missed is retired (1.5.0): now Planned with the state Overdue"


def retire_missed(con, missed):
    """BL-186: each milestone that was Missed (its status already set to Planned before the rebuild) gets the state Overdue,
    set by Alan (state_set 1: he had marked it Missed). Logged as one apply (via "migrate") so Activity and each milestone's
    history show it. Every row is kept; with no Missed milestone nothing is written, so a second run does nothing.
    Returns (apply_id, [ids]) or None."""
    if not missed:
        return None
    at = now()
    apply_id = con.execute("INSERT INTO applies (at, proposals, file_ops) VALUES (?, ?, ?)",
                           (at, json.dumps([]), "[]")).lastrowid
    for m in missed:
        con.execute("UPDATE milestones SET state = 'Overdue', state_set = 1, updated_at = ? WHERE id = ?", (at, m["id"]))
        for f, old, new in (("status", "Missed", "Planned"), ("state", None, "Overdue"), ("state_set", 0, 1),
                            ("updated_at", m["updated_at"], at), ("note", None, MISSED_NOTE)):
            log(con, apply_id, "milestones", m["id"], f, old, new, "update", MIGRATE_VIA)
    return apply_id, [m["id"] for m in missed]


def cmd_init():
    """Create tracker.db from schema.sql and add the projects in the register that aren't in it yet."""
    new = not paths.DB.exists()
    paths.DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(paths.DB)
    con.executescript(paths.SCHEMA.read_text(encoding="utf-8"))
    added = []
    for code, name in register_projects():
        if not con.execute("SELECT 1 FROM projects WHERE code = ?", (code,)).fetchone():
            con.execute("INSERT INTO projects (code, name, updated_at) VALUES (?, ?, ?)", (code, name, now()))
            added.append(code)
    con.commit()
    con.close()
    print(f"{'Created' if new else 'Checked'} {paths.rel(paths.DB)}; projects added: {', '.join(added) or 'none'}.")
    if not new:
        con = sqlite3.connect(paths.DB)
        stale = outdated_tables(con)
        con.close()
        if stale:
            print(f"Schema changed for {', '.join(stale)}: run tracker.py migrate.")
    return 0


# ===== BL-252 (fix-search-read) =====
# read --search TEXT: a case-insensitive match on an item's own words; --status open|closed. Read only.
READ_OPTIONS = ("--project", "--id", "--search", "--status")
SEARCH_FIELDS = ("title", "name", "description", "decision", "notes", "note", "latest_update", "response_action",
                 "reasoning")
OPEN_STATUSES = ("Open", "Delayed", "Planned", "Active", "Pending")
TABLE_OPTIONS = {"rejected": ("--days",), "promises": ("--list",)}    # --list owe|waiting: BL-125 A


def read_options(table, rest):
    """The read options as a dict; an unknown option, one with no value or a bad --status fails with the valid ones."""
    valid = READ_OPTIONS + TABLE_OPTIONS.get(table, ())
    if len(rest) % 2:
        sys.exit(f"creaite: option {rest[-1]} needs a value. Options: {', '.join(valid)}")
    opts = dict(zip(rest[0::2], rest[1::2]))
    for k in opts:
        if k not in valid:
            sys.exit(f"creaite: unknown option {k}. Options: {', '.join(valid)}")
    if opts.get("--status", "open").lower() not in ("open", "closed"):
        sys.exit(f"creaite: --status is open or closed, not {opts['--status']}")
    return opts


def search_filter(t, cols, text, named):
    """(condition, params) matching text, case-insensitively, in t's text columns; None if t has none."""
    fields = [f for f in SEARCH_FIELDS if f in cols]
    if not fields:
        if named:
            sys.exit(f"creaite: {t} has no text to search. --search works on: "
                     f"{', '.join(x for x in TABLES if x not in ('links', 'item_labels', 'updates'))}")
        return None
    return ("(" + " OR ".join(f"instr(lower(coalesce({f}, '')), ?) > 0" for f in fields) + ")",
            [text.lower()] * len(fields))


def status_filter(t, cols, status, named):
    """(condition, params) for --status open|closed; None if t has no status."""
    if "status" not in cols:
        if named:
            sys.exit(f"creaite: {t} has no status, so --status does not apply")
        return None
    marks = ", ".join("?" * len(OPEN_STATUSES))
    return f"status {'IN' if status.lower() == 'open' else 'NOT IN'} ({marks})", list(OPEN_STATUSES)


def read_filters(t, cols, opts, named):
    """(conditions, params) for --project, --id, --search and --status on table t, or None to leave t out of an
    all-tables read. A named table that cannot take a filter fails."""
    conds, params = [], []
    if "--project" in opts:
        conds.append("project = ?" if "project" in cols else "code = ?")
        params.append(opts["--project"])
    if "--id" in opts:
        conds.append(f"{'id' if 'id' in cols else KEYS[t][0]} = ?" if t != "projects" else "code = ?")
        params.append(opts["--id"])
    for opt, make in (("--search", search_filter), ("--status", status_filter)):
        if opt in opts:
            found = make(t, cols, opts[opt], named)
            if found is None:
                return None
            conds.append(found[0])
            params += found[1]
    return conds, params
# ===== end BL-252 =====


# ===== BL-125 A (v19-promises-data) =====
# Promises and waiting on: what Alan has promised ("You owe") and what others have promised him that is overdue ("Waiting on",
# each with how long it has been quiet: the days since it was raised, last raised again in mentions.jsonl (BL-51) or last edited by
# Alan (an applied change to the promise from the dashboard, cx-edit, ask creaite or the Excel import, in change_log; Alan,
# 13-10-2026, decision 5); silence is the signal). Read only: `read promises --list owe|waiting` prints them; report.py's weekly
# report and the dashboard use promise_lists. A promise between two other people is in neither list; one with no due date is never overdue.
PROMISE_LISTS = {"owe": "you_owe", "waiting": "waiting_on"}


def promise_day():
    """Today's date for the promise lists: CREAITE_NOW (tests fix the clock) or the real date."""
    fixed = os.environ.get("CREAITE_NOW")
    return date.fromisoformat(fixed[:10]) if fixed else date.today()


def my_names():
    """Alan's own names, lower case: settings.json identity's name and short forms."""
    ident = paths.load_settings().get("identity") or {}
    return {str(n).strip().lower() for n in [ident.get("name"), *(ident.get("short_forms") or [])] if str(n or "").strip()}


def last_heard():
    """{item ID: the latest day it was raised again} from the mentions log (BL-51)."""
    out = {}
    text = paths.MENTIONS.read_text(encoding="utf-8") if paths.MENTIONS.is_file() else ""
    for line in text.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue                                   # a torn line: the rest of the log still counts
        if isinstance(m, dict) and m.get("id") and str(m.get("at") or "")[:10] > out.get(m["id"], ""):
            out[m["id"]] = str(m["at"])[:10]
    return out


def last_edited(con):
    """{promise ID: the latest day Alan edited it}: change_log updates from his own edits (VIA_NAMES), in applies not undone."""
    q = (f"SELECT c.item_id, MAX(c.at) FROM change_log c LEFT JOIN applies a ON a.apply_id = c.apply_id WHERE c.tbl = 'promises' "
         f"AND c.op = 'update' AND c.via IN ({','.join('?' * len(VIA_NAMES))}) AND a.undone_at IS NULL GROUP BY c.item_id")
    return {r[0]: str(r[1] or "")[:10] for r in con.execute(q, VIA_NAMES)}


def last_touched(con=None):
    """{item ID: the latest day it was raised again (mentions.jsonl) or, for a promise, edited by Alan}: what restarts the quiet
    clock. Without a connection it opens the tracker's; with no tracker, mentions only."""
    heard = last_heard()
    try:
        own = con or connect_or_raise()
    except NoDatabase:
        return heard
    try:
        for k, v in last_edited(own).items():
            if v > heard.get(k, ""):
                heard[k] = v
    finally:
        if con is None:
            own.close()
    return heard


def days_between(earlier, later):
    """Whole days from an ISO date (or timestamp) to a date; 0 when there is no date."""
    return (later - date.fromisoformat(earlier[:10])).days if earlier else 0


def promise_lists(rows_, on=None, con=None):
    """{"you_owe": [...], "waiting_on": [...]} from promise rows (dicts): Alan's open promises, soonest due first, each with
    overdue_days; and the open promises others made to him whose due date has passed, most overdue first, each with
    overdue_days and quiet_days (since it was raised, last raised again or last edited by Alan: last_touched)."""
    on, mine, heard = on or promise_day(), my_names(), last_touched(con)
    owe, waiting = [], []
    for r in rows_:
        if r.get("status") != "Open":
            continue
        late = max(days_between(r.get("due_date"), on), 0)
        if str(r.get("promised_by") or "").strip().lower() in mine:
            owe.append({**r, "overdue_days": late})
        elif str(r.get("promised_to") or "").strip().lower() in mine and late:
            quiet = days_between(max(str(r.get("raised") or ""), heard.get(r["id"], "")), on)
            waiting.append({**r, "overdue_days": late, "quiet_days": max(quiet, 0)})
    owe.sort(key=lambda r: (r.get("due_date") or "9999", r["id"]))
    waiting.sort(key=lambda r: (-r["overdue_days"], r["id"]))
    return {"you_owe": owe, "waiting_on": waiting}


def plural_days(n):
    """'1 day', '3 days'."""
    return f"{n} day{'s' if n != 1 else ''}"


def promise_line(r, waiting=False):
    """One promise for a person to read: "Send the SOW — to Sara Example, by 16-10-2026 (3 days overdue)", or for Waiting
    on "Sara Example: Send the data extract — due 06-10-2026, 3 days overdue, quiet for 5 days"."""
    late = r.get("overdue_days") or 0
    if waiting:
        quiet = f", quiet for {plural_days(r['quiet_days'])}" if r.get("quiet_days") else ""
        return f"{r['promised_by']}: {r['description']} — due {shown(r['due_date'])}, {plural_days(late)} overdue{quiet}"
    when = f"by {shown(r['due_date'])}" if r.get("due_date") else "no date given"
    return f"{r['description']} — to {r['promised_to']}, {when}" + (f" ({plural_days(late)} overdue)" if late else "")


def who_of(values):
    """Who an item is with, as a list shows it: its owner, or a promise's "Alan Carter → Sara Example"."""
    if values.get("promised_by") or values.get("promised_to"):
        return f"{values.get('promised_by') or '?'} → {values.get('promised_to') or '?'}"
    return values.get("owner", "")


def read_list(rows_, which, con=None):
    """`read promises --list owe|waiting`: the rows already read (and filtered), as that list."""
    if which not in PROMISE_LISTS:
        sys.exit(f"creaite: --list is owe or waiting, not {which}")
    return promise_lists(rows_, con=con)[PROMISE_LISTS[which]]
# ===== end BL-125 A =====


def cmd_read(args):
    """Print tracker rows as JSON: one table or all, filtered by project, ID, text or status (BL-252); or a
    project's reject reasons (BL-133). Read only.
    """
    table = args[0] if args and not args[0].startswith("--") else None
    rest = args[1:] if table else args
    opts = read_options(table, rest)                      # BL-252: unknown options fail
    con = connect()
    names = [table] if table else list(TABLES)
    allowed = (*TABLES, "change_log", "rejected", "applies")
    out = {}
    if table == "rejected" and "--project" in opts:      # BL-133 stage B: a project's reasons, with what was rejected
        print(json.dumps(rejected_reasons(con, opts["--project"], opts.get("--days")), indent=2, ensure_ascii=False))
        return 0
    for t in names:
        if t not in allowed:
            sys.exit(f"creaite: unknown table {t}. Tables: {', '.join(allowed)}")
        sql, cols = f"SELECT * FROM {t}", columns(con, t)
        found = read_filters(t, cols, opts, bool(table))  # BL-252: --project, --id, --search, --status
        if found is None:
            continue
        conds, params = found
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        out[t] = [dict(r) for r in con.execute(sql, params)]
        if "--list" in opts:                              # BL-125 A: You owe, or Waiting on
            out[t] = read_list(out[t], opts["--list"], con)
    print(json.dumps(out[table] if table else out, indent=2, ensure_ascii=False))
    return 0


# ===== BL-275: PDF text for the search index (the bundled pypdf) =====
def mostly_letters(text, limit):
    """`text` cut to `limit` if at least half of it (spaces aside) is letters, else "" (a scan or binary noise)."""
    text = re.sub(r"[ \t]+", " ", re.sub(r"\s*\n\s*", "\n", text.replace("\x00", ""))).strip()
    letters = sum(c.isalpha() for c in text)
    return text[:limit] if text and letters >= 0.5 * len(re.sub(r"\s", "", text)) else ""


def pdf_text(p, limit=400_000):
    """Text of a PDF with the bundled pypdf (BL-275): each page's text, joined, kept to `limit`. An encrypted, damaged
    or unreadable PDF gives "" (indexed by name only) and a debug line with its path, never its text; a scan with no
    text layer gives "" too. Without pypdf, the standard-library reader below."""
    try:
        import logging
        import warnings
        import pypdf
    except Exception:  # noqa: BLE001  (pypdf missing or broken: today's reader)
        return pdf_text_stdlib(p, limit)
    quiet = logging.getLogger("pypdf")              # pypdf's own warnings never reach the terminal or the log
    if not quiet.handlers:
        quiet.addHandler(logging.NullHandler())
    quiet.propagate = False
    why = "unreadable"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            reader = pypdf.PdfReader(str(p), strict=False)
            if reader.is_encrypted:
                why = "encrypted"
                raise ValueError(why)
            out, size = [], 0
            for page in reader.pages:
                out.append(page.extract_text() or "")
                size += len(out[-1])
                if size >= limit:
                    break
        return mostly_letters("\n".join(out), limit)
    except Exception as e:  # noqa: BLE001  (fails safe: indexed by name, never stops the build)
        debuglog.debug("tracker", f"search index: PDF not read ({why}, {type(e).__name__}): {log_path(p)}")
        return ""


# ===== end BL-275 =====


def pdf_text_stdlib(p, limit=400_000):
    """Best-effort text of a PDF with the standard library, used only when pypdf can't be imported: the text-showing
    operators in each (Flate-compressed or plain) content stream. PDFs whose fonts map glyphs through a ToUnicode
    table give nothing readable, and then the file is indexed by name only."""
    import zlib
    try:
        raw = p.read_bytes()
    except OSError:
        return ""
    out = []

    def unescape(b):
        """A PDF string's backslash escapes (octal codes, line breaks, tabs) turned into bytes."""
        b = re.sub(rb"\\([0-7]{1,3})", lambda m: bytes([int(m.group(1), 8) & 255]), b)
        return re.sub(rb"\\(.)", lambda m: {b"n": b"\n", b"r": b"\n", b"t": b" "}.get(m.group(1), m.group(1)), b, flags=re.S)
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S):
        data = m.group(1)
        try:
            data = zlib.decompress(data)
        except zlib.error:  # BL-228: an uncompressed PDF stream is read as it is
            pass
        if b"BT" not in data:
            continue
        for block in re.findall(rb"BT(.*?)ET", data, re.S):
            for t in re.finditer(rb"\[(.*?)\]\s*TJ|\(((?:\\.|[^\\)])*)\)\s*(?:Tj|'|\")", block, re.S):
                if t.group(1) is not None:
                    parts = re.findall(rb"\(((?:\\.|[^\\)])*)\)|(-?\d+\.?\d*)", t.group(1))
                    out.append("".join(unescape(a).decode("latin-1") if a or not n else (" " if float(n) < -200 else "")
                                       for a, n in parts))
                else:
                    out.append(unescape(t.group(2)).decode("latin-1"))
            out.append("\n")
    return mostly_letters(" ".join(out), limit)


# ===== BL-276: saved-email text for the search index =====
INDEX_READERS = 3   # BL-276 (2), BL-275 (3): raise when text_of reads more, so the next build reads every file again


def log_path(p):
    """A file's vault path for the debug log, or just its name when it is outside the vault."""
    try:
        return paths.rel(p)
    except (ValueError, OSError):
        return Path(p).name


def eml_text(p, limit=400_000):
    """Text of a saved email (.eml, BL-276) with the standard library: From, To, Cc, Date and Subject, the plain-text
    body (or the HTML body without its tags), and a line naming the attachments, whose contents aren't read. A
    malformed message gives what could be read, or ""; only its path goes into the debug log."""
    import html
    from email import policy
    from email.parser import BytesParser
    try:
        msg = BytesParser(policy=policy.default).parsebytes(p.read_bytes())
    except Exception as e:  # noqa: BLE001
        debuglog.debug("tracker", f"search index: email not read ({type(e).__name__}): {log_path(p)}")
        return ""
    lines, broken = [], 0
    for h in ("From", "To", "Cc", "Date", "Subject"):
        try:
            if msg[h]:
                lines.append(f"{h}: {msg[h]}")
        except Exception:  # noqa: BLE001  (a header that can't be parsed is left out)
            broken += 1
    try:
        part = msg.get_body(preferencelist=("plain", "html"))
        body = part.get_content() if part is not None else ""
        if part is not None and part.get_content_subtype() == "html":
            body = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", body)
            body = html.unescape(re.sub(r"(?s)<br\s*/?>|</p>|</div>|</tr>", "\n", body))
            body = re.sub(r"<[^>]+>", " ", body)
        lines.append(body)
    except Exception:  # noqa: BLE001  (an unreadable body: the headers and attachment names still count)
        broken += 1
    try:
        names = [n for n in (part.get_filename() for part in msg.walk() if part.get_content_maintype() != "multipart") if n]
        if names:
            lines.append("Attachments: " + ", ".join(names))
    except Exception:  # noqa: BLE001
        broken += 1
    if broken:
        debuglog.debug("tracker", f"search index: email partly read ({broken} part(s) skipped): {log_path(p)}")
    return re.sub(r"[ \t]+", " ", re.sub(r"\s*\n\s*", "\n", "\n".join(lines))).strip()[:limit]
# ===== end BL-276 =====


def text_of(p):
    """Plain text of a vault file for the search index (standard library, and the bundled pypdf for PDFs)."""
    suffix = p.suffix.lower()
    try:
        if suffix in (".docx", ".pptx", ".xlsx"):
            with zipfile.ZipFile(p) as z:
                parts = [n for n in z.namelist() if re.match(
                    r"word/document\.xml|ppt/slides/slide\d+\.xml|xl/sharedStrings\.xml", n)]
                xml = " ".join(z.read(n).decode("utf-8", "ignore") for n in sorted(parts))
            xml = re.sub(r"</w:p>|</a:p>|</si>", "\n", xml)
            return re.sub(r"[ \t]+", " ", re.sub(r"<[^>]+>", "", xml)).strip()
        if suffix in (".vtt", ".srt"):
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            keep = [ln for ln in lines if ln.strip() and "-->" not in ln and ln.strip() != "WEBVTT"
                    and not ln.strip().isdigit()]
            return "\n".join(re.sub(r"<v ([^>]+)>", r"\1: ", re.sub(r"</?[a-z][^>]*>", "", k))
                             if k.startswith("<v ") else re.sub(r"<[^>]+>", "", k) for k in keep)
        if suffix in (".txt", ".md", ".csv"):
            return p.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".pdf":
            return pdf_text(p)
        if suffix == ".eml":
            return eml_text(p)
    except (OSError, zipfile.BadZipFile):
        return ""
    return ""  # other types are indexed by name only


# ── The search index (BL-07) ──────────────────────────────────────────────────

INDEX_FOLDERS = ("minutes", "transcripts", "reports", "documents", "notes")      # what the index covers, in every project
STORED_KIND = {"reports": "report", "agendas": "documents", "notes": "note"}     # the others are stored as their folder name (BL-135: an agenda
#                                                                                  is a document to search; BL-301: a note is kind `note`)
INDEX_VERSION = 2          # BL-301: raised when what the index holds changes, so a vault built by an older release rebuilds once


def index_entry_text(f, folder):
    """(text, date) a file is indexed with. A note (BL-301) is read by notes.py (front matter left out, its own date); every other
    file by text_of, dated as before."""
    if folder == "notes":
        import notes
        return notes.index_text(f), notes.index_date(f)
    when = paths.file_date(f)[0] if folder in ("minutes", "transcripts") else (paths.name_date(f.name)[0] or "")
    return text_of(f), when


def index_files():
    """Every file the index covers: (path, folder, project code), in a fixed order."""
    out = []
    for code, _ in paths.project_folders():
        out += [(f, kind, code) for f, kind, _ in paths.project_files(code)]
    return out


def search_table_sql():
    """The vault_search statement from schema.sql, the one place its columns and tokenizer are defined."""
    m = re.search(r"CREATE VIRTUAL TABLE IF NOT EXISTS vault_search USING fts5\([^;]*\);",
                  paths.SCHEMA.read_text(encoding="utf-8"))
    return m.group(0)


def ensure_search_table(con):
    """Make vault_search match schema.sql. The table is a derived index, so a table made before word forms were added
    is dropped and recreated (the next `index` fills it). True if it had to be recreated."""
    row = con.execute("SELECT sql FROM sqlite_master WHERE name = 'vault_search'").fetchone()
    if row and "porter" in row[0]:
        return False
    if row:
        con.execute("DROP TABLE vault_search")
    con.execute(search_table_sql().replace("IF NOT EXISTS ", ""))
    index_stamp().unlink(missing_ok=True)            # the new table is empty: the index must be rebuilt
    return True


def index_stamp():
    """The search index's build stamp: system/search/index-built.json."""
    return paths.SEARCH_DIR / "index-built.json"


def index_state():
    """(stale, why): is the index older than the newest indexed file, or covering a different set of files?
    A cheap check of modification times and a count; nothing is read."""
    files = index_files()
    try:
        stamp = json.loads(index_stamp().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return True, "never built"
    if stamp.get("version", 1) != INDEX_VERSION:
        return True, "built by an older release"
    sidecars = list(paths.SEARCH_DIR.glob("*.json")) if paths.SEARCH_DIR.is_dir() else []
    newest = max([f.stat().st_mtime for f, _, _ in files] + [s.stat().st_mtime for s in sidecars
                                                              if s.name != index_stamp().name] + [0])
    if stamp.get("files") != len(files):
        return True, "files added or removed"
    if newest > stamp.get("built", 0):
        return True, "files changed"
    if stamp.get("readers", 1) != INDEX_READERS:     # BL-275, BL-276: PDFs and saved emails are read anew
        return True, "file readers changed"
    if stamp.get("layout") != INDEX_LAYOUT:          # BL-327: a stamp without each file's record is rebuilt once in full
        return True, "index layout changed"
    return False, ""


def sidecar_path(rel):
    """Where a file's summary and tags live (BL-07 enrichment): system/search/<sha256 of its vault path>.json."""
    return paths.SEARCH_DIR / (hashlib.sha256(rel.encode("utf-8")).hexdigest() + ".json")


def read_sidecar(rel):
    """{summary, tags[]} written for this file when it was processed, or None."""
    try:
        rec = json.loads(sidecar_path(rel).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return rec if isinstance(rec, dict) and rec.get("path") == rel else None


# ===== BL-327: an incremental index. The stamp keeps each file's modification time, size, sidecar time and (for a meeting,
# indexed once wherever it is filed) its content hash; a build re-reads only the files whose stamp changed, or that share a
# meeting's hash with one that did. A full rebuild only when the readers (INDEX_READERS) or this layout (INDEX_LAYOUT) change,
# when the table is recreated, or when asked (`tracker.py index`).
INDEX_LAYOUT = 1
INDEX_LOCK = threading.Lock()          # one build at a time within a process (the live server's threads)
MEETING_FOLDERS = ("minutes", "transcripts")


def _sidecar_time(rel):
    """The modification time (ns) of a file's sidecar, or 0."""
    try:
        return sidecar_path(rel).stat().st_mtime_ns
    except OSError:                                     # no sidecar (most files have none)
        return 0


def _index_scan(old):
    """[(slot, file, folder, code, meta, changed)] for every indexed file now. meta is the stamp's record for the file; a
    meeting's content hash is worked out again only when its stamp changed."""
    out = []
    for f, folder, code in index_files():
        rel = paths.rel(f)
        try:
            st = f.stat()
        except OSError:
            continue                                     # gone while it was listed
        meta = {"m": st.st_mtime_ns, "s": st.st_size, "n": _sidecar_time(rel), "f": folder, "c": code}
        slot = f"{code}|{rel}"
        prev = (old or {}).get(slot)
        same = bool(prev) and all(prev.get(k) == v for k, v in meta.items())
        if same:
            meta["k"] = prev.get("k")
        else:
            try:
                meta["k"] = hashlib.sha256(f.read_bytes()).hexdigest() if folder in MEETING_FOLDERS else rel
            except OSError:                              # unreadable now: left out, and read at the next build
                continue
        out.append((slot, f, folder, code, meta, not same))
    return out


def _index_entries(scan, keys):
    """The vault_search rows for these dedup keys, from the files now listed: a meeting filed in several projects once."""
    found = {}
    for _slot, f, folder, code, meta, _changed in scan:
        if meta["k"] not in keys:
            continue
        rel = paths.rel(f)
        entry = found.get(meta["k"])
        if entry is None:
            content, when = index_entry_text(f, folder)          # BL-301: a note is read by notes.py, with its own date
            entry = found[meta["k"]] = {"path": rel, "projects": [], "kind": STORED_KIND.get(folder, folder),
                                        "date": when, "text": content, "stem": f.stem, "note": None}
        entry["note"] = entry["note"] or read_sidecar(rel)        # any copy's sidecar will do
        if code not in entry["projects"]:
            entry["projects"].append(code)
    for e in found.values():
        note = e.pop("note")
        extra = f"{note.get('summary', '')}\n{', '.join(note.get('tags') or [])}\n" if note else ""
        e["content"] = f"{e.pop('stem')}\n{extra}{e.pop('text')}"
    return list(found.values())


def _index_old(full, recreated):
    """The last build's per-file records, or None when this build must read everything (asked for, a recreated table, new
    readers or a new layout, or no stamp)."""
    try:
        stamp = json.loads(index_stamp().read_text(encoding="utf-8"))
    except (OSError, ValueError):                      # never built, or a stamp caught half-written: a full build
        return None
    if (full or recreated or stamp.get("readers", 1) != INDEX_READERS or stamp.get("layout") != INDEX_LAYOUT
            or stamp.get("version", 1) != INDEX_VERSION):      # BL-301: what the index holds changed (notes): read it all once
        return None
    return stamp.get("entries")


def _index_plan(old, scan):
    """(the dedup keys to write again, the paths whose rows go first). Everything when `old` is None; otherwise the keys of
    the files changed, added or removed (before and now), and every path a row for them may be under."""
    if old is None:
        return {meta["k"] for *_, meta, _c in scan}, set()
    now_slots = {slot for slot, *_ in scan}
    keys = {meta["k"] for *_, meta, changed in scan if changed}
    keys |= {old[slot].get("k") for slot, *_, changed in scan if changed and slot in old}
    keys |= {m.get("k") for slot, m in old.items() if slot not in now_slots}
    gone = {slot.split("|", 1)[1] for slot, m in old.items() if m.get("k") in keys}
    gone |= {paths.rel(f) for _s, f, _fo, _c, meta, _ch in scan if meta["k"] in keys}
    return keys, gone


def _index_write(con, everything, gone, entries):
    """One transaction: the rows going (all of them for a full build), then the new rows."""
    con.execute("BEGIN IMMEDIATE")
    if everything:
        con.execute("DELETE FROM vault_search")
    listed = sorted(gone)
    for i in range(0, len(listed), 500):
        part = listed[i:i + 500]
        con.execute(f"DELETE FROM vault_search WHERE path IN ({','.join('?' * len(part))})", part)
    con.executemany("INSERT INTO vault_search (path, project, kind, date, content) VALUES (?,?,?,?,?)",
                    [(e["path"], " ".join(e["projects"]), e["kind"], e["date"], e["content"]) for e in entries])
    con.execute("COMMIT")


def build_index(full=False):
    """Bring vault_search up to date and return how many entries it holds. Only the files whose stamp changed since the last
    build are read again (BL-327); `full`, a change of readers or layout, or a recreated table rebuild it all. A meeting's
    or report's summary and tags (its sidecar) are part of its content, so keyword search matches them. The time, the files
    read and removed are in the debug log."""
    with INDEX_LOCK:
        t0, started = time.monotonic(), datetime.now().timestamp()
        con = connect()
        try:
            old = _index_old(full, ensure_search_table(con))
            scan = _index_scan(old)
            keys, gone = _index_plan(old, scan)
            entries = _index_entries(scan, keys)
            if old is None or keys:                    # nothing changed: tracker.db isn't touched (its stamp is the page's signal)
                _index_write(con, old is None, gone, entries)
        finally:
            con.close()
        paths.SEARCH_DIR.mkdir(parents=True, exist_ok=True)
        total = len({meta["k"] for *_, meta, _c in scan})
        tmp = index_stamp().with_suffix(".tmp")
        tmp.write_text(json.dumps({"built": started, "files": len(scan), "readers": INDEX_READERS, "layout": INDEX_LAYOUT,
                                   "version": INDEX_VERSION, "entries": {slot: meta for slot, _f, _fo, _c, meta, _ch in scan}}), encoding="utf-8")
        os.replace(tmp, index_stamp())
        now_slots = {slot for slot, *_ in scan}
        removed = sum(1 for slot in (old or {}) if slot not in now_slots)
        debuglog.info("tracker", f"search index: {'full' if old is None else 'incremental'} in "
                                 f"{time.monotonic() - t0:.2f}s: {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} "
                                 f"read again, {removed} file(s) removed, {total} indexed")
        return total
# ===== end BL-327 (index) =====


def cmd_index():
    """Rebuild the full-text search index (BL-07) and say which online-only files were skipped (BL-85)."""
    print(f"Indexed {build_index(full=True)} file(s).")
    away = paths.online_only_files()
    if away:                                         # BL-85: never read, so never downloaded
        print(f"Skipped {len(away)} online-only file(s) (not on this device): " + ", ".join(f.name for _, _, f in away[:5])
              + (" …" if len(away) > 5 else ""))
    return 0


def refresh_index():
    """After an apply or undo: bring the index up to date (BL-327: only what changed is read again). Never stops the apply."""
    try:
        build_index()
    except Exception as e:  # noqa: BLE001
        print(f"Note: the search index wasn't refreshed: {e}")


def fts_terms(text, prefix=False):
    """Quote every term so hyphens and other punctuation are searched literally; with prefix, the last term matches
    as a prefix too (search as you type)."""
    terms = [t.strip('"') for t in re.findall(r'"[^"]+"|\S+', text) if t.strip('"')]
    quoted = ['"' + t.replace('"', '""') + '"' for t in terms]
    if prefix and quoted:
        quoted[-1] += "*"
    return " ".join(quoted)


def cmd_query(args):
    """Full-text search of the vault index; print paths, projects, kinds, dates and snippets as JSON."""
    if not args:
        sys.exit('creaite: query needs search text, e.g. tracker.py query "ABC-A-003"')
    text, opts = args[0], dict(zip(args[1::2], args[2::2]))
    con = connect()
    sql = ("SELECT path, project, kind, date, snippet(vault_search, 4, '[', ']', '…', 12) AS snippet "
           "FROM vault_search WHERE vault_search MATCH ?")
    params = [fts_terms(text, prefix=True)]
    if "--project" in opts:
        sql += " AND (' ' || project || ' ') LIKE ?"
        params.append(f"% {opts['--project']} %")
    rows = [dict(r) for r in con.execute(sql + " ORDER BY rank LIMIT 50", params)]
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    return 0


def main(argv):
    """Run the tracker command in `argv` (see the module docstring)."""
    if not argv:
        print(__doc__)
        return 2
    cmd, args = argv[0], argv[1:]
    if cmd == "init":
        return cmd_init()
    if cmd == "read":
        return cmd_read(args)
    if cmd == "validate" and len(args) == 1:
        return cmd_validate(args[0])
    if cmd == "apply":
        return cmd_apply(args)
    if cmd == "undo":
        return cmd_undo()
    if cmd == "undo-changes":
        return cmd_undo_changes(args)          # BL-164 (sprint-rail)
    if cmd == "migrate":
        return cmd_migrate()
    if cmd == "index":
        return cmd_index()
    if cmd == "query":
        return cmd_query(args)
    print(__doc__)
    return 2


# ===== Recode a project (BL-111) =====
# A proposal item {"op": "recode", "table": "projects", "id": OLD, "changes": {"code": NEW, "name": …}, "folder": {"from": …, "to": …}}
# changes a project's code (and optionally its name and folder) everywhere in one apply, and undo restores it exactly. Built by
# `propose.py recode`. A recode is applied on its own (recode_barrier), so undo has only the recode to reverse.

RECODE_COLUMNS = {      # per table, the columns that hold a project code, an item ID or a project folder path
    "projects": ("code",),
    "milestones": ("id", "project", "source"),
    "workstreams": ("id", "project", "source"),
    "actions": ("id", "project", "milestone", "source"),
    "raid": ("id", "project", "milestone", "source"),
    "decisions": ("id", "project", "source", "replaces"),
    "promises": ("id", "project", "source"),
    "links": ("from_item", "to_item", "source"),
    "item_labels": ("item_id",),
    "updates": ("project",),
}
RECODE_ID_TABLES = ("milestones", "workstreams", "actions", "raid", "decisions", "promises")    # the ID starts with the project code
RECODE_LINKS = {"actions": ("milestone",), "raid": ("milestone",), "decisions": ("replaces",),     # columns holding another item's ID,
                "links": ("from_item", "to_item"), "item_labels": ("item_id",)}                    # of any project (rewritten in every row)
RECODE_KEYED = {"links": 2, "item_labels": 1}       # change_log keys made of IDs joined by "|": links "from|to|kind", item_labels "item|label"
RECODE_ID_FIELDS = ("id", "milestone", "replaces", "from_item", "to_item", "item_id")     # change_log fields whose values are item IDs
RECODE_OTHER = ("applies", "change_log", "rejected", "vault_search", "labels")             # rewritten by hand below, or hold no code
RECODE_LOOKS_LIKE = re.compile(r"^(id|code|project|source|replaces|milestone)$|_id$|_item$|^(from|to)(_|$)")


def recode_unclassified(con):
    """Tables and columns of the database that the recode doesn't know about (a new table that carries a project or an item ID
    must be added to the lists above, or a recode would leave it behind). Empty when all is known."""
    gaps = []
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        if t.startswith("vault_search_"):          # the search index's own shadow tables
            continue
        if t in RECODE_OTHER:
            continue
        if t not in RECODE_COLUMNS:
            gaps.append(t)
            continue
        names = [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
        gaps += [f"{t}.{c}" for c in names if RECODE_LOOKS_LIKE.search(c) and c not in RECODE_COLUMNS[t]]
    return gaps


def recode_id(value, old, new):
    """An item ID with the project code swapped (every ID of a project starts with its code and a hyphen)."""
    return new + value[len(old):] if isinstance(value, str) and value.startswith(old + "-") else value


def register_all_codes():
    """Every code in the project register: the Projects table, the Shared table and the Retired codes."""
    codes = set()
    for line in paths.REGISTER.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if cells and re.fullmatch(CODE_RE, cells[0]):
            codes.add(cells[0])
    return codes


def code_token(code):
    """A pattern matching a project code as a whole token, not inside a longer word or ID."""
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(code) + r"(?![A-Za-z0-9])")


def is_recode_of(item, old, new=None):
    """Whether an item is a recode of project `old` (to `new`, when given) (BL-111)."""
    ch = item.get("changes") or {}
    return item.get("op") == "recode" and item.get("id") == old and (new is None or ch.get("code") == new)


def recode_pending(old, new=None):
    """Names of pending proposals (other than the recode's own) that still mention the old code as a whole token."""
    token, out = code_token(old), []
    for p in sorted(paths.STAGING.glob("proposed-*.json")):
        try:
            data = load(p)
        except (OSError, ValueError):
            continue
        items = [i for i in data.get("items", []) if not i.get("applied") and i.get("decision") != "rejected"]
        if any(is_recode_of(i, old, new) for i in items):
            continue
        live = {"items": items, "blocks": [b for b, _ in blocks(data) if not b.get("applied")]}
        if token.search(json.dumps(live, ensure_ascii=False)):
            out.append(p.name)
    return out


def recode_item_copy(item, old, new):
    """An item as it will read under the new code (its project, its ID and any item IDs in its changes)."""
    c = json.loads(json.dumps(item))
    if isinstance(c.get("values"), dict):
        if c["values"].get("project") == old:
            c["values"]["project"] = new
        for k in ("from_item", "to_item", "item_id", "replaces"):
            if isinstance(c["values"].get(k), str):
                c["values"][k] = recode_id(c["values"][k], old, new)
    if c.get("id"):
        c["id"] = recode_id(c["id"], old, new)
    if isinstance(c.get("changes"), dict):
        c["changes"] = {k: recode_id(v, old, new) for k, v in c["changes"].items()}
    return c


def recode_fingerprints(con, old, new):
    """{old fingerprint: new fingerprint} for the project's rejected items. A fingerprint is a hash that includes the project code, so
    it is recomputed from the rejected items kept in staging; one that matches none of them can't be tied to a project and stays."""
    have = {r[0] for r in con.execute("SELECT fingerprint FROM rejected")}
    out = {}
    for d in (paths.STAGING, paths.APPLIED):
        for p in sorted(d.glob("proposed-*.json")):
            try:
                items = load(p).get("items", [])
            except (OSError, ValueError):
                continue
            for it in items:
                if it.get("decision") != "rejected":
                    continue
                v = it.get("values") or {}
                if (v.get("project") or (it.get("id") or v.get("from_item") or v.get("item_id") or "").split("-")[0]) != old:
                    continue
                fp = fingerprint(it)
                if fp in have:
                    out[fp] = fingerprint(recode_item_copy(it, old, new))
    return out


def rewrite_project(con, old, new, name=None, folder=None, fingerprints=None):
    """Change a project's code (and name) in every table, in the open transaction. Used by apply and, swapped round, by undo.
    folder: (from, to) engagement folder names, to rewrite the `source` paths. Returns {table: rows changed}.
    BL-229: each rewrite is its own step, in the order they always ran."""
    con.execute("PRAGMA defer_foreign_keys = ON")            # the keys point at each other; checked at commit
    fingerprints = fingerprints or {}
    counts = {}
    sets, args = "code = ?", [new]                   # updated_at is left as it was, so undo restores the row exactly
    if name:
        sets, args = sets + ", name = ?", args + [name]
    con.execute(f"UPDATE projects SET {sets} WHERE code = ?", args + [old])
    counts["projects"] = 1
    _recode_items(con, old, new, counts)
    _recode_links(con, old, new, counts)
    counts["updates"] = con.execute("UPDATE updates SET project = ? WHERE project = ?", (new, old)).rowcount
    if folder and folder[0] != folder[1]:
        _recode_sources(con, new, folder)
    _recode_rejected(con, fingerprints)
    counts["rejected"] = len(fingerprints)
    counts["history"] = _recode_history(con, old, new, fingerprints)
    _recode_search(con, old, new)
    broken = con.execute("PRAGMA foreign_key_check").fetchall()
    if broken:
        raise Invalid(f"the recode would leave {len(broken)} broken link(s) between items")
    return counts


def _recode_items(con, old, new, counts):
    for t in RECODE_ID_TABLES:
        ids = [r[0] for r in con.execute(f"SELECT id FROM {t} WHERE project = ?", (old,))]
        for i in ids:
            if not i.startswith(old + "-"):
                raise Invalid(f"{t} {i} doesn't start with {old}-, so it can't be recoded")
            con.execute(f"UPDATE {t} SET id = ?, project = ? WHERE id = ?", (recode_id(i, old, new), new, i))
        counts[t] = len(ids)


def _recode_links(con, old, new, counts):
    for t, cols in RECODE_LINKS.items():
        for c in cols:
            for rowid, v in con.execute(f"SELECT rowid, {c} FROM {t} WHERE substr({c}, 1, ?) = ?", (len(old) + 1, old + "-")).fetchall():
                counts[f"{t}.{c}"] = counts.get(f"{t}.{c}", 0) + 1
                con.execute(f"UPDATE {t} SET {c} = ? WHERE rowid = ?", (recode_id(v, old, new), rowid))


def _recode_sources(con, new, folder):
    """The `source` paths, when the engagement folder was renamed too."""
    a, b = f"projects/{folder[0]}/", f"projects/{folder[1]}/"
    for t in RECODE_ID_TABLES:
        con.execute(f"UPDATE {t} SET source = ? || substr(source, ?) WHERE project = ? AND substr(source, 1, ?) = ?",
                    (b, len(a) + 1, new, len(a), a))
    con.execute("UPDATE links SET source = ? || substr(source, ?) WHERE substr(source, 1, ?) = ?", (b, len(a) + 1, len(a), a))


def _recode_rejected(con, fingerprints):
    for o, n in fingerprints.items():
        if con.execute("SELECT 1 FROM rejected WHERE fingerprint = ?", (n,)).fetchone():
            con.execute("DELETE FROM rejected WHERE fingerprint = ?", (o,))
        else:
            con.execute("UPDATE rejected SET fingerprint = ? WHERE fingerprint = ?", (n, o))


def _recode_history_key(tbl, item_id, old, new, fingerprints):
    """A change_log row's item key under the new code."""
    if tbl == "projects":
        return new if item_id == old else item_id
    if tbl == "updates":
        week, _, who = item_id.partition("|")
        return f"{week}|{new}" if who == old else item_id
    if tbl == "rejected":
        return fingerprints.get(item_id, item_id)
    if tbl in RECODE_ID_TABLES:
        return recode_id(item_id, old, new)
    if tbl in RECODE_KEYED:
        parts = item_id.split("|")
        return "|".join(recode_id(x, old, new) if k < RECODE_KEYED[tbl] else x for k, x in enumerate(parts))
    return item_id


def _recode_history_value(tbl, field, v, old, new, fingerprints):
    """A change_log row's old or new value under the new code."""
    if v is None:
        return v
    if field == "project" and v == old:
        return new
    if tbl == "projects" and field == "code" and v == old:
        return new
    if field in RECODE_ID_FIELDS and (tbl in RECODE_ID_TABLES or tbl in RECODE_KEYED):
        return recode_id(v, old, new)
    if tbl == "rejected" and field == "fingerprint":
        return fingerprints.get(v, v)
    return v


def _recode_history(con, old, new, fingerprints):
    """Rewrite the history (change_log) so it reads under the new code; returns how many rows changed."""
    n = 0
    for rowid, tbl, item_id, field, ov, nv in con.execute(
            "SELECT rowid, tbl, item_id, field, old_value, new_value FROM change_log WHERE tbl != 'recode'").fetchall():
        key = _recode_history_key(tbl, item_id, old, new, fingerprints)
        o2 = _recode_history_value(tbl, field, ov, old, new, fingerprints)
        n2 = _recode_history_value(tbl, field, nv, old, new, fingerprints)
        if (key, o2, n2) != (item_id, ov, nv):
            con.execute("UPDATE change_log SET item_id = ?, old_value = ?, new_value = ? WHERE rowid = ?", (key, o2, n2, rowid))
            n += 1
    return n


def _recode_search(con, old, new):
    if con.execute("SELECT 1 FROM sqlite_master WHERE name = 'vault_search'").fetchone():
        for rowid, proj in con.execute("SELECT rowid, project FROM vault_search").fetchall():
            tokens = (proj or "").split()
            if old in tokens:
                con.execute("UPDATE vault_search SET project = ? WHERE rowid = ?",
                            (" ".join(new if t == old else t for t in tokens), rowid))


def recode_code_problem(con, old, new):
    """Why OLD can't become NEW, or None."""
    if not con.execute("SELECT 1 FROM projects WHERE code = ?", (old,)).fetchone():
        return f"{old} is not a project in the tracker"
    if not new or not re.fullmatch(CODE_RE, str(new)):
        return f"the new code must be 3 to 7 capital letters or digits, starting with a letter (got {new!r})"
    if new == old:
        return f"{old} is already the code; to rename the project only, edit its name"
    if con.execute("SELECT 1 FROM projects WHERE code = ?", (new,)).fetchone():
        return f"{new} is already a project"
    if new in register_all_codes():
        return f"{new} is already in the project register (retired codes can't be reused)"
    return None


def recode_project(con, item, apply_id, via):
    """Write one recode item (see the block's note). Returns the new code."""
    old, ch, folder = item.get("id"), dict(item.get("changes") or {}), item.get("folder") or {}
    new, name = ch.get("code"), (ch.get("name") or "").strip() or None
    gaps = recode_unclassified(con)
    if gaps:
        raise Invalid("this version of creaite doesn't know how to recode " + ", ".join(gaps) + ": update creaite, or add it to RECODE_COLUMNS")
    if set(ch) - {"code", "name"}:
        raise Invalid("a recode changes only the code and the name")
    row = con.execute("SELECT * FROM projects WHERE code = ?", (old,)).fetchone()
    problem = recode_code_problem(con, old, new)
    if problem:
        raise Invalid(problem)
    pending = recode_pending(old, new)
    if pending:
        raise Invalid(f"{len(pending)} pending proposal(s) still mention {old}: {', '.join(pending)}. Apply or reject them first")
    if folder.get("to") and not paths.resolve(f"projects/{folder['to']}").is_dir():
        raise Invalid(f"the folder “{folder['to']}” doesn't exist; rename the engagement folder first")
    fps = recode_fingerprints(con, old, new)
    counts = rewrite_project(con, old, new, name, (folder["from"], folder["to"]) if folder.get("from") and folder.get("to") else None, fps)
    debuglog.info("tracker", f"recode {old} to {new}: " + ", ".join(f"{k} {v}" for k, v in counts.items() if v))
    log(con, apply_id, "recode", new, "code", old, new, "update", via)
    if name and name != row["name"]:
        log(con, apply_id, "recode", new, "name", row["name"], name, "update", via)
    if folder.get("from") and folder.get("to"):
        log(con, apply_id, "recode", new, "folder", folder["from"], folder["to"], "update", via)
    if fps:
        log(con, apply_id, "recode", new, "rejected_map", None, json.dumps(fps), "update", via)
    return new


def undo_recode(con, changes):
    """Reverse a recode from its change_log entries: the same rewrite, the other way round."""
    f = {c["field"]: c for c in changes}
    old, new = f["code"]["old_value"], f["code"]["new_value"]
    if not con.execute("SELECT 1 FROM projects WHERE code = ?", (new,)).fetchone():
        raise Invalid(f"{new} is no longer a project, so the recode can't be undone")
    if con.execute("SELECT 1 FROM projects WHERE code = ?", (old,)).fetchone():
        raise Invalid(f"{old} has been used again, so the recode can't be undone")
    folder = (f["folder"]["new_value"], f["folder"]["old_value"]) if "folder" in f else None
    fps = {v: k for k, v in json.loads(f["rejected_map"]["new_value"]).items()} if "rejected_map" in f else None
    rewrite_project(con, new, old, f["name"]["old_value"] if "name" in f else None, folder, fps)


def recode_barrier(work):
    """A recode is applied on its own: with other proposals waiting, it goes first and the rest wait for the next apply. Returns the
    work to do, or None (printing why) when a recode shares its proposal with other items."""
    def recodes(d):
        """The approved, unapplied recode items in a proposal (BL-111)."""
        return [i for i in d.get("items", []) if i.get("op") == "recode" and not i.get("applied") and i.get("decision") == "approved"]
    own = [(p, d) for p, d in work if recodes(d)]
    if not own:
        return work
    p, d = own[0]
    others = [i for i in d.get("items", []) if i.get("op") != "recode" and not i.get("applied") and i.get("decision") in ("approved", "rejected")]
    if len(recodes(d)) > 1 or others:
        print(f"Apply stopped. Nothing was written.\n  {p.name}: a recode is applied on its own, with no other items in its proposal.")
        return None
    if len(work) > 1:
        print(f"{p.name} is a recode: applying it first, on its own. Run apply again for the other proposals.")
    return [(p, d)]


if __name__ == "__main__":
    sys.exit(debuglog.main("tracker.py", main, sys.argv[1:]))
