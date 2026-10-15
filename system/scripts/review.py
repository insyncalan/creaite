"""creaite review — list pending proposals and record Alan's decisions (cx-review's engine).

Commands:
  pending                       one line per project: drafts, needs a project, conflicts, individual, routine, stale
  list [CODE | minutes] [--json]
                                the numbered review, grouped by project; numbers are saved for the commands below
  approve <numbers> [--sync | --as-staged]
                                e.g. "1-6,9". Draft minutes are first compared with the staged items; if they
                                differ, nothing is approved and the differences are listed. --sync updates the
                                staged owners and due dates to match the draft; --as-staged keeps them. Approved
                                drafts are cleaned (tracked changes accepted, comments removed). A draft open in
                                Word is refused (close it first); no sensitivity label is needed.
  reject <numbers> [--reason=TEXT] [--duplicate-of=ID]
                                BL-133: the reason is stored with the rejection (Duplicate, Not mine to track, Not an
                                action, Other or Alan's words) and given to extraction as guidance; "reject 4 as a
                                duplicate of ABC-A-009" works too. The exact item is never proposed again, as before.
                                BL-315: the seven reasons (Not an action, Duplicate, Chatter, Already done, Wrong project,
                                Doesn't need tracking, For another team) are spelt as listed; --guess rejects each with its own guess
  reasons [--json]              BL-315: the seven reasons, in the menu's order
  guesses [CODE] [--json]       BL-315: creaite's guess per pending item (Chatter, Duplicate of an open item, Already done, Doesn't
                                need tracking when no owner is named); plain code, never a model
  unreject <file>#<n> …         BL-315: undo rejects (pending or applied): back in Review, pending
  rereason <file>#<n> … [--reason=TEXT] [--duplicate-of=ID]
                                BL-315: change rejects' reason; none clears it
  approve-instead <file>#<n> …  BL-315: undo rejects and approve them in one step; an item approved only on its own (minutes, a new
                                decision, a new risk, …) goes back to Review to be opened. Each of these three takes --json
  rejects [--json] [--limit=N]  BL-315: the latest rejects, newest first (Activity › What you rejected)
  bulk [CODE] [--strong]        approve routine items only (never drafts, health changes, new decisions, new risks,
                                weekly updates, conflicts or items without a project; an update to a work item only when it
                                changes nothing but its due date and latest update, BL-297; a promise marked Done or Dropped
                                is routine unless it is a "probably done" guess, BL-125 A)
  assign <number> <CODE> [--from=CODE] [--all] [--dry-run [--json]]
                                BL-200: give a pending new item another project (its old project's milestone and
                                workstream are cleared; the match becomes strong). On a minutes entry, move every item
                                from those minutes and the minutes' filing (file_ops, projects) to CODE; --from names the
                                project to move when the minutes span several; --all also moves items already moved on
                                their own; --dry-run shows the result first. Update items stay with their project
  edit <number> field=value …   change a pending item, validate it, and approve it if valid (dates DD-MM-YYYY)
  keep <number>                 conflict: keep the database version (rejects the edit)
  override <number>             conflict: apply the edit over the newer change
  merge <number>                BL-221: a new item marked "Looks like ABC-A-009" becomes an update to ABC-A-009 carrying any new
                                date, latest update or response (nothing new: rejected as its duplicate). Same project, open item
  keep-new <number>             BL-221: keep it as a new item; the "Looks like" mark is dropped
  retarget <number> <ID>        BL-297: a pending new action, RAID item or decision becomes an update to ID (an open item of the same
                                project and table), carrying its date and latest update or response, as merge does (nothing new:
                                rejected as its duplicate). Marked or not; the choice is recorded for Activity › Quality
  unmerge <number> | <file>#<n> BL-297: undo a merge or a retarget; the proposal is the new item it was (by file and item number
                                when it was rejected as a duplicate, so it has no review number)
  candidates <number> [--json]  BL-297: the open items a pending new item could update, best matches first (the Review picker)
  workstream <number> add [--lead=… --keywords=… --aliases=… --channel=…] | skip
                                an item flagged new-workstream (BL-58): add the suggested workstream to its project
                                (approved; it goes into the same proposal, before the item) and set it on the item, or
                                leave the item's workstream blank

Decisions are written into the proposal files in system/staging/; nothing reaches the database until
"tracker.py apply". Numbers refer to the last "list"; run it again if proposals have changed.
"""
import difflib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
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
import tracker  # noqa: E402
import docx_tools  # noqa: E402

INDEX = paths.STAGING / "review-index.json"
DOCX_TOOLS = Path(__file__).with_name("docx_tools.py")
BLOCKS = (("meeting", "minutes_decision", "Minutes"), ("report", "report_decision", "Report"),
          ("file_changes", "file_changes_decision", "File change"))


# ── Loading and classifying ───────────────────────────────────────────────────

def proposals():
    """Yield (path, data) for each pending proposal file in system/staging/, with `raised` pre-filled (BL-26)."""
    for p in sorted(paths.STAGING.glob("proposed-*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        tracker.fill_raised(data)   # shown pre-filled (BL-26); apply fills it the same way
        yield p, data


def save(p, data):
    """Write a proposal file back to system/staging/, keeping the first as-proposed copy of each item (BL-232)."""
    tracker.stamp_as_proposed(p, data)              # ===== BL-232 (fix-as-proposed): the first edit keeps what was proposed =====
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def project_of(item):
    """The project code an item belongs to: from its values, else from its ID."""
    key = item.get("id") or ""
    if (item.get("values") or {}).get("project"):
        return item["values"]["project"]
    if "|" in key:                      # updates rows: "<week_ending>|<CODE>"
        return key.split("|")[1]
    return key.split("-")[0] or None


def needs_project(item):
    """Whether an item still needs Alan to choose its project (a possible or unresolved match, or none)."""
    return item.get("match") in ("possible", "unresolved") or not project_of(item)


CLOSING = ("Closed", "Cancelled", "Done", "Dropped")      # an action or RAID item closed; a promise kept or dropped (BL-125 A)


def closes_individually(item):
    """Whether an update closes an item that is decided on its own (BL-65): an action or RAID item closed or cancelled; a promise
    only when it is a probably-done guess (BL-218), judged on its evidence as an action is. Any other promise marked Done or
    Dropped is routine, like a new promise (BL-125 A, decision 6: Alan, 13-10-2026)."""
    table = item.get("table")
    if (item.get("changes") or {}).get("status") not in CLOSING:
        return False
    return table in ("actions", "raid") or (table == "promises" and (item.get("suggested") or {}).get("feature") == "done")


def individual_only(item):
    """The bulk rule: these are only ever approved one at a time."""
    v, op, table = item.get("values") or {}, item.get("op"), item.get("table")
    if item.get("drafted"):                      # ===== AI drafts (sprint-drafts-fields): a drafted text is decided on its own =====
        return {"client": "client wording"}.get(item["drafted"], "drafted update")
    if op == "update" and "client_message" in (item.get("changes") or {}):
        return "client wording"                  # BL-225: wording that faces a client is never approved in bulk
    if op == "new" and table == "decisions":
        return "new decision"
    if op == "new" and table == "raid" and v.get("type") == "Risk":
        return "new risk"
    if table == "projects" and "health" in (item.get("changes") or {}):
        return "health change"
    if table == "updates":
        return "weekly update"
    if op == "update" and closes_individually(item):
        return "closing update"
    if op == "update" and table == "decisions" and (item.get("changes") or {}).get("status") in ("Made", "Withdrawn"):
        return "decision made"                   # BL-53: recording or withdrawing a decision is decided on its own
    if op == "update" and table == "milestones" and "baseline_date" in (item.get("changes") or {}):
        return "rebaseline"                      # BL-186: a rebaseline records a decision, so it is approved on its own
    return update_rule(item)                     # BL-297: a work item's update is routine only for its date and latest update


# ===== AI drafts (sprint-drafts-fields) ===== a drafted proposal decided here is counted in draft-stats.json (counts only): approved
# as drafted is "used", approved after an edit "edited", rejected "rejected". The dashboard's Review counts its own decisions.
def count_draft(item, decision):
    """Count Alan's decision on an AI-drafted field (used, edited or rejected) in draft-stats.json; counts only."""
    feature = item.get("drafted")
    if not feature or decision not in ("approved", "rejected"):
        return
    try:
        import drafts
        field = next(iter(item.get("changes") or {}), None)
        same = field and (item.get("changes") or {}).get(field) == item.get("drafted_text")
        drafts.record(feature, "rejected" if decision == "rejected" else "used" if same else "edited")
    except Exception:  # noqa: BLE001  a count never stops a decision
        pass
# ===== end AI drafts =====


# ===== BL-221, BL-218 (sprint-drafts-extraction) ===== a decision on a suggestion from extraction is counted too (counts only)
def count_suggestion(item, decision):
    """Count a decided proposal: a drafted text (count_draft) and a repeat or "probably done" suggestion (extraction)."""
    count_draft(item, decision)
    import extraction
    extraction.count_decision(item, decision)
# ===== end BL-221, BL-218 =====


def stale_days():
    """After how many days a pending proposal is stale (settings review.stale_after_days, default 7)."""
    return paths.load_settings().get("review", {}).get("stale_after_days", 7)


def age(data):
    """How many days old a proposal is, from its `created` time; 0 if that can't be read."""
    try:
        fixed = os.environ.get("CREAITE_NOW")           # creaite's clock: CREAITE_NOW fixes it in tests, as elsewhere
        now = datetime.fromisoformat(fixed) if fixed else datetime.now()
        return (now - datetime.fromisoformat(data.get("created", ""))).days
    except ValueError:
        return 0


UPDATE_LABELS = {"due_date": "due", "response_action": "response", "latest_update": "latest update", "made_by": "made by",
                 "needed_by": "needed by"}


def update_text(item):
    """An update from a meeting (BL-65) as 'ABC-A-003 Send revised SOW: status Open → Closed; due 09-10-2026 → 16-10-2026'."""
    title, changes = update_parts(item)
    return f"{title}: {changes}"


def update_parts(item):
    """(the item's ID and text, each changed field from what it is now to what the meeting says), read fresh each time."""
    table, item_id = item.get("table"), item.get("id")
    row = {}
    # ===== BL-228 (sprint-debt-safety) =====  C: a connect that raises, and only the errors expected here are quiet
    import sqlite3
    try:
        con = tracker.connect_or_raise()
        found = con.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
        row = dict(found) if found else {}
        con.close()
    except (tracker.NoDatabase, sqlite3.Error):     # no database or no such table yet: show what changes, not from what
        pass
    except Exception as e:  # noqa: BLE001  unexpected: logged by name only (BL-102), and the line still shows the change
        debuglog.debug("review", f"update_parts {item_id}: {type(e).__name__} ignored")
    # ===== end BL-228 =====
    fmt = lambda f, x: (tracker.shown(x) if f in tracker.DATE_FIELDS else str(x)) if x not in (None, "") else "—"  # noqa: E731
    changes = "; ".join(f"{UPDATE_LABELS.get(f, f)} {fmt(f, row.get(f))} → {fmt(f, c)}" for f, c in (item.get("changes") or {}).items())
    return f"{item_id} {row.get('description') or row.get('decision') or ''}".strip(), changes


def describe(item):
    """(kind, text, owner, due) for one item, as the review list shows it."""
    v = item.get("values") or {}
    if item.get("op") == "new":
        kind = v.get("type") or {"actions": "Action", "decisions": "Decision", "projects": "Project", "milestones": "Milestone",
                                 "updates": "Weekly update", "promises": "Promise"}.get(item.get("table"), item.get("table"))
        text = v.get("description") or v.get("decision") or v.get("summary") or v.get("name") or ""
        return kind, text, tracker.who_of(v), tracker.shown(v.get("due_date")) or ""      # a promise: by → to (BL-125 A)
    changes = item.get("changes") or {}
    if item.get("op") == "update" and item.get("table") in ("actions", "raid", "decisions", "promises") and "why" in item:     # BL-65
        return "Update", update_text(item), changes.get("owner", ""), tracker.shown(changes.get("due_date")) or ""
    shown = ", ".join(f"{k} → {tracker.shown(c) if k in tracker.DATE_FIELDS else c}" for k, c in changes.items())
    kind = {"cancel": "Cancel", "recode": "Recode"}.get(item.get("op"), "Change")
    return kind, f"{item.get('id')}: {shown or item.get('confirm', 'cancel')}", changes.get("owner", ""), \
        tracker.shown(changes.get("due_date")) or ""


_MS_NAMES = None


def milestone_name(ms_id):
    """A milestone's name for display (BL-27); the ID if it isn't in the tracker."""
    global _MS_NAMES
    if _MS_NAMES is None:
        try:
            con = tracker.connect()
            _MS_NAMES = {r[0]: r[1] for r in con.execute("SELECT id, name FROM milestones")}
            con.close()
        except (Exception, SystemExit):  # no database yet (connect() exits): show IDs
            _MS_NAMES = {}
    return _MS_NAMES.get(ms_id, ms_id) if ms_id else ""


def decision_detail(v):
    """What's needed to decide a new decision: who it is needed from and by when (BL-53), or who made it and when."""
    if v.get("status") == "Pending":           # BL-53: a decision needed
        return [f"Needed from {v['made_by']}" if v.get("made_by") else "Needed (asked of no one yet)",
                f"by {tracker.shown(v['needed_by'])}" if v.get("needed_by") else "no date needed by"]
    return [f"Made by {v.get('made_by') or 'not recorded'}", tracker.shown(v.get("date")) or ""]


def detail(item):
    """What's needed to decide (BL-25): priority or impact × likelihood, response, workstream, milestone."""
    v = item.get("values") or {}
    parts = []
    if item.get("op") == "new" and item.get("table") == "actions":
        parts = [f"Priority {v.get('priority') or 'Medium'}", v.get("workstream") or "", milestone_name(v.get("milestone"))]
    elif item.get("op") == "new" and item.get("table") == "raid":
        pr = tracker.priority(v.get("impact"), v.get("likelihood"))
        parts = [f"Impact {v.get('impact') or '—'} × Likelihood {v.get('likelihood') or '—'} → {pr or 'priority not set'}",
                 f"Response: {v['response_action']}" if v.get("response_action") else "No response yet",
                 v.get("workstream") or ""]
    elif item.get("op") == "new" and item.get("table") == "decisions":
        parts = decision_detail(v)
    elif item.get("op") == "new" and item.get("table") == "promises":       # BL-125 A
        parts = [f"Promised by {v.get('promised_by') or '?'} to {v.get('promised_to') or '?'}"]
    elif item.get("op") == "update" and "why" in item:
        parts = [item["why"]] if item.get("why") else []        # BL-65: what the meeting said
    return " · ".join(p for p in parts if p)


def weekend_note(item):
    """BL-181: "due on a Saturday (17-10-2026)" for a proposed new item or update whose date is a weekend day; "" otherwise."""
    if item.get("table") not in tracker.WEEKEND_FIELDS or item.get("op") not in ("new", "update"):
        return ""
    return "; ".join(tracker.weekend(item["table"], item.get("values") if item.get("op") == "new" else item.get("changes")))


def short_source(src):
    """An item's source shortened for the review list: the mail subject, the Teams chat or the file name."""
    src = src or ""
    if src.startswith("Email"):
        m = re.search(r"Subject: ([^·]+)", src)
        return f"Email · {m.group(1).strip() if m else ''}"
    if src.startswith("Teams"):
        m = re.search(r"(Channel|Chat): ([^·]+)", src)
        return f"Teams · {m.group(2).strip() if m else ''}"
    return Path(src.split(" — ")[0]).name + (f" — {src.split(' — ')[1]}" if " — " in src else "")


def build_rows(scope=None):
    """Every pending entry, ordered as the review shows it."""
    limit = stale_days()
    rows = []
    for p, data in proposals():
        old = age(data) > limit
        mt = data.get("meeting") or {}
        minutes_pending = bool(mt) and not mt.get("applied") and mt.get("minutes_decision", "pending") == "pending"
        for key, field, label in BLOCKS:
            b = data.get(key)
            if b and not b.get("applied") and b.get(field, "pending") == "pending":
                for code in b.get("projects") or [b.get("project") or "?"]:
                    rows.append({"file": p.name, "ref": key, "project": code, "section": 0, "stale": old,
                                 "kind": label, "text": f"{b.get('title', '')} ({tracker.shown(b.get('date'))})",
                                 "owner": "", "due": "", "match": "", "flags": "",
                                 "source": b.get("draft") or "", "first": code == (b.get("projects") or ["?"])[0],
                                 "nest": p.name if key == "meeting" else None, "child": False})
        for item in data.get("items", []):
            if item.get("applied") or item.get("decision") != "pending":
                continue
            kind, text, owner, due = describe(item)
            if needs_project(item):
                project, section = "Needs a project", -1
            elif "conflict" in item.get("flags", []):
                project, section = project_of(item), 1
            elif individual_only(item):
                project, section = project_of(item), 2
            else:
                project, section = project_of(item), 3
            rows.append({"file": p.name, "ref": item.get("n"), "project": project, "section": section,
                         "stale": old, "kind": kind, "text": text, "owner": owner, "due": due, "detail": detail(item),
                         "match": item.get("match", ""), "flags": ", ".join(item.get("flags", [])),
                         "source": short_source((item.get("values") or {}).get("source") or item.get("source")), "first": True,
                         "why": individual_only(item), "note": item.get("invalid_reason") or item.get("conflict_reason")
                         or item.get("review_note") or ws_note(item) or "",
                         "weekend": weekend_note(item),                                    # BL-181: a note, never a block
                         # BL-41: an item from minutes still pending sits under them, in this project
                         "nest": p.name if minutes_pending and project in (mt.get("projects") or []) else None,
                         "child": bool(minutes_pending and project in (mt.get("projects") or []))})
    if scope == "minutes":
        rows = [r for r in rows if r["ref"] == "meeting"]
    elif scope:
        rows = [r for r in rows if r["project"] == scope]
    # A draft filed under several projects is listed under each, but numbered once
    # Items from pending minutes follow their minutes line (BL-41); everything else by section as before
    rows.sort(key=lambda r: (r["project"] != "Needs a project", r["project"] or "", 0 if r.get("nest") else r["section"],
                             r.get("nest") or "", r.get("child", False), r["section"], not r["stale"]))
    return rows


def numbered(rows):
    """The review rows with their review numbers: one number per item, shared by its rows."""
    out, seen, n = [], {}, 0
    for r in rows:
        ident = (r["file"], r["ref"])
        if ident not in seen:
            n += 1
            seen[ident] = n
        out.append({**r, "n": seen[ident]})
    return out


# ── Commands ──────────────────────────────────────────────────────────────────

SECTION_NAMES = {0: "Draft documents (with the items from each)", 1: "Conflicts", 2: "Individual approval only", 3: "Everything else"}


def write_index(rows):
    """The numbers 'approve 5' refers to; written by list and by the dashboard build, so both agree."""
    INDEX.write_text(json.dumps({"at": datetime.now().isoformat(timespec="seconds"),
                                 "entries": {str(r["n"]): [r["file"], r["ref"]] for r in rows}}, indent=1),
                     encoding="utf-8")


def numbers():
    """{(proposal file, ref): n} for everything pending, numbered as review.py list numbers it."""
    rows = numbered(build_rows())
    return rows, {(r["file"], r["ref"]): r["n"] for r in rows}


project_label = tracker.project_label        # BL-101: a project is shown by its name


def cmd_list(scope=None, as_json=False):
    """Print the numbered review, grouped by project (one project, or minutes, with `scope`), or JSON.
    Saves the numbers to system/staging/review-index.json for approve, reject and the other commands.
    """
    rows = numbered(build_rows(scope))
    if not scope:
        write_index(rows)
    else:     # a scoped list keeps the full numbering, so numbers mean the same everywhere
        all_rows, num = numbers()
        write_index(all_rows)
        rows = [{**r, "n": num[(r["file"], r["ref"])]} for r in rows]
    if as_json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0
    if not rows:
        print("Nothing is waiting for review.")
        return 0
    current = (None, None)
    for r in rows:
        if r["project"] != current[0]:
            print(f"\n## {project_label(r['project'])}")
            current = (r["project"], None)
        shown_section = 0 if r.get("nest") else r["section"]
        if r["project"] != "Needs a project" and shown_section != current[1]:
            print(f"### {SECTION_NAMES[shown_section]}")
            current = (r["project"], shown_section)
        mark = "⚠ " if r["stale"] else ""
        extra = f" — {r['why']}" if r.get("why") else ""
        note = f" — {r['note']}" if r.get("note") else ""
        note += f" — {r['weekend']}" if r.get("weekend") else ""                              # BL-181
        owner = r["owner"] or ("No owner" if r["kind"] == "Action" else "")
        due = r["due"] or ("No due date" if r["kind"] == "Action" else "")
        indent = "   ↳ " if r.get("child") else ""
        print(f"{indent}{r['n']} · {mark}{r['kind']} · {r['text']} · {owner} · {due}" + (f" · {r['detail']}" if r.get("detail") else "")
              + f" · {r['match']} · {r['flags']} · {r['source']}{extra}{note}")
    return 0


def cmd_pending():
    """Print one line per project: drafts, needs a project, conflicts, individual, routine and stale counts."""
    rows = build_rows()
    if not rows:
        print("Nothing pending.")
        return 0
    by = {}
    for r in rows:
        c = by.setdefault(r["project"], {"drafts": 0, "needs a project": 0, "conflicts": 0, "individual": 0,
                                         "routine": 0, "stale": 0})
        if r["project"] == "Needs a project":
            c["needs a project"] += 1
        elif r["section"] == 0:
            if r["first"]:
                c["drafts"] += 1
        else:
            c[{1: "conflicts", 2: "individual", 3: "routine"}[r["section"]]] += 1
        c["stale"] += r["stale"]
    for project, c in by.items():
        print(f"{project_label(project)}: " + ", ".join(f"{v} {k}" for k, v in c.items() if v))
    return 0


def parse_numbers(spec):
    """The review numbers in a spec such as '1-6,9'."""
    nums = []
    for part in re.split(r"[,\s]+", spec.replace("–", "-").strip()):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            nums.extend(range(int(a), int(b) + 1))
        else:
            nums.append(int(part))
    return nums


def lookup(n):
    """(proposal path, data, ref, item) for a review number from the last list; exits if it is unknown."""
    if not INDEX.exists():
        sys.exit("creaite: no review numbers yet. Run: python3 system/scripts/review.py list")
    entries = json.loads(INDEX.read_text(encoding="utf-8"))["entries"]
    if str(n) not in entries:
        sys.exit(f"creaite: {n} isn't in the last review. Run the review again.")
    fname, ref = entries[str(n)]
    p = paths.STAGING / fname
    if not p.exists():
        sys.exit(f"creaite: {fname} is no longer pending. Run the review again.")
    data = json.loads(p.read_text(encoding="utf-8"))
    if ref in ("meeting", "report", "file_changes"):
        return p, data, ref, data.get(ref)
    item = next((i for i in data.get("items", []) if i.get("n") == ref), None)
    if item is None or item.get("applied"):
        sys.exit(f"creaite: {n} has already been applied. Run the review again.")
    return p, data, ref, item


def norm(text):
    """Text for matching: lower case, letters, digits and single spaces only."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (text or "").lower())).strip()


def best(text, candidates, cutoff):
    """The candidate most like text, if similar enough."""
    scored = [(difflib.SequenceMatcher(None, norm(text), norm(c[0])).ratio(), c) for c in candidates]
    scored = [x for x in scored if x[0] >= cutoff]
    return max(scored, key=lambda x: x[0])[1] if scored else None


def section(lines, start, end):
    """The lines between the `start` and `end` headings of a draft, or [] if there is no such section."""
    try:
        i = lines.index(start)
    except ValueError:
        return []
    out = []
    for line in lines[i + 1:]:
        if line == end:
            break
        if line.strip() and line.strip() != docx_tools.NONE:
            out.append(line.strip())
    return out


def minutes_differences(data, block):
    """Compare the (possibly edited) draft minutes with the staged items: owners, due dates, missing items."""
    import minutes
    parsed = minutes.parse_draft(paths.resolve(block["draft"]))
    live = [i for i in data.get("items", []) if i.get("decision") != "rejected" and i.get("op") == "new"]
    actions = [((i["values"].get("description") or ""), i) for i in live if i["table"] == "actions"]
    diffs, matched = [], set()
    for k, row in enumerate(parsed["actions"], start=1):
        hit = best(row["text"], actions, 0.75)
        if not hit:
            diffs.append({"msg": f"Action {k} is in the draft but not staged: {row['text']}"})
            continue
        item = hit[1]
        matched.add(id(item))
        v = item["values"]
        for field, draft_value in (("owner", row["owner"]), ("due_date", row["due"])):
            staged_value = v.get(field) or None
            if field == "owner":  # the tracker writes "Name (Company)"; minutes may show the name alone
                staged_value = re.sub(r"\s*\([^)]*\)$", "", staged_value or "TBC")
                draft_value = re.sub(r"\s*\([^)]*\)$", "", draft_value or "TBC")
            if staged_value != (draft_value or None):
                label = "owner" if field == "owner" else "due"
                shown_draft = tracker.shown(draft_value) if field == "due_date" else draft_value
                shown_staged = tracker.shown(v.get(field)) if field == "due_date" else v.get(field, "TBC")
                diffs.append({"item": item, "field": field, "value": draft_value,
                              "msg": f"Action {k} {label}: draft says {shown_draft or 'none'}; "
                                     f"staged {shown_staged or 'none'}"})
    for text, item in actions:
        if id(item) not in matched:
            diffs.append({"msg": f"Staged action not in the draft: {text}"})
    for kind, table, drafted in (("decision", "decisions", parsed["decisions"]),
                                 ("RAID item", "raid", [f"{d['type'] or 'Risk'}: {d['text']}" for d in parsed["raid"]])):
        staged = [((f"{i['values'].get('type')}: " if table == "raid" else "") +
                   (i["values"].get("decision") or i["values"].get("description") or ""), i)
                  for i in live if i["table"] == table]
        for text in drafted:
            if not best(text, staged, 0.6):
                diffs.append({"msg": f"Draft has a {kind} that isn't staged: {text}"})
        for text, _ in staged:
            if not best(text, [(t, None) for t in drafted], 0.6):
                diffs.append({"msg": f"Staged {kind} not in the draft: {text}"})
    return diffs


def draft_lines(path):
    """The text lines of a Word draft, with tracked changes accepted."""
    parts = docx_tools.read_parts(path)
    xml = next(raw.decode("utf-8") for info, raw in parts if info.filename == "word/document.xml")
    return docx_tools.story_text(docx_tools.accept_xml(xml)[0]).splitlines()


def squash(t):
    """Text with its whitespace squeezed to single spaces."""
    return re.sub(r"\s+", " ", t or "").strip()


def weekly_differences(block):
    """Weekly report: the draft's health line, summary and current state against what's staged."""
    import report
    lines = draft_lines(paths.resolve(block["draft"]))
    health = reason = None
    for i, line in enumerate(lines):
        if line.startswith("Week ending"):
            m = re.match(r"\s*(ON TRACK|AT RISK|OFF TRACK)\s+(.*)$", next((x for x in lines[i + 1:] if x.strip()), ""))
            if m:
                health = {"ON TRACK": "On track", "AT RISK": "At risk", "OFF TRACK": "Off track"}[m.group(1)]
                reason = m.group(2).strip()
            break
    captions = {i["caption"] for i in report.memory_images(paths.project_dir(block["project"]))}
    summary = "\n\n".join(section(lines, "Summary", "Current State"))
    current = [x for x in section(lines, "Current State", "Progress This Week") if x not in captions]
    found = {"health": health, "health_reason": reason, "summary": summary,
             "current_state": docx_tools.md_from_lines(current)}
    labels = {"health": "Health", "health_reason": "Health reason", "summary": "Summary", "current_state": "Current state"}
    # Current state is Markdown when staged and plain in Word: compare it as Word shows it (BL-22)
    shown = {"current_state": " ".join(current)}
    staged = {**block, "current_state": " ".join(docx_tools.md_lines(block.get("current_state")))}
    return [{"field": k, "value": v, "msg": f"{labels[k]}: draft says “{squash(shown.get(k, v))[:120]}”; staged “{squash(staged.get(k))[:120]}”"}
            for k, v in found.items() if v is not None and squash(shown.get(k, v)) != squash(staged.get(k))]


def sync_weekly(data, block, diffs):
    """Carry the draft's edits into the staged updates row, health change and current-state rewrite."""
    import report
    for d in diffs:
        block[d["field"]] = d["value"]
    for it in data.get("items", []):
        target = it.get("values") if it.get("op") == "new" else it.get("changes")
        if it.get("table") == "updates":
            target.update(health=block["health"], summary=block["summary"])
        if it.get("table") == "projects":
            target.update(health=block["health"], health_reason=block.get("health_reason", ""))
    if any(d["field"] in ("health", "health_reason") for d in diffs) and \
            not any(i.get("table") == "projects" for i in data.get("items", [])):
        data["items"].append({"n": max([i["n"] for i in data["items"]] + [0]) + 1, "op": "update", "table": "projects",
                              "id": block["project"], "changes": {"health": block["health"],
                                                                 "health_reason": block.get("health_reason", "")},
                              "match": "strong", "flags": [], "decision": "pending"})
    memory = paths.rel(paths.project_dir(block["project"]) / "CLAUDE.md")
    op = next((o for o in block["file_ops"] if o.get("op") == "write" and o.get("path") == memory), None)
    previous = op["previous"] if op else (paths.resolve(memory)).read_text(encoding="utf-8")
    content = report.replace_current(previous, block["current_state"])
    if op:
        op["content"] = content
    elif content != previous:
        block["file_ops"].insert(0, {"op": "write", "path": memory, "content": content, "previous": previous})


# ===== BL-228 (sprint-debt-safety) =====
def labels_missing(con, err):
    """True only when `err` is SQLite's "no such table" and the labels or item_labels table really isn't there (an old
    database). A broken view, a locked database or any other error is False, so the caller reports it (fails closed)."""
    import sqlite3
    if not (isinstance(err, sqlite3.OperationalError) and str(err).startswith("no such table")):
        return False
    try:
        have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE name IN ('labels', 'item_labels')")}
    except sqlite3.Error:  # can't tell: treat it as present, so the error is reported
        return False
    return not {"labels", "item_labels"} <= have


def label_check_failure(con, err, code):
    """A: the finding for a label check that failed: none only when the tables aren't there; otherwise one (fails closed)."""
    if labels_missing(con, err):
        return []
    debuglog.warn("review", f"label exclusion check failed for {code}: {type(err).__name__}")
    return [f"Couldn't check the label exclusions: {type(err).__name__}: {err}; check before sending"]
# ===== end BL-228 =====


def client_findings(block):
    """Client report: internal-only content in the (possibly edited) draft. v2.1.0 P3: the check itself lives in client_leak.py, on
    the data; a creaite document is checked there whole (its items too), a Word draft by its text."""
    import client_leak
    import creaite_doc
    draft = paths.resolve(block["draft"])
    if creaite_doc.is_doc(draft):
        return client_leak.findings(creaite_doc.read(draft))
    return client_leak.text_findings(tracker.connect(), block["project"], "\n".join(draft_lines(draft)))


# ===== BL-260 point 4 (fix-minutes-approve) =====
def no_draft_refusal(n, ref, block, decision):
    """Minutes with no Word draft can't be approved (apply refuses them too); Reject still works."""
    if decision == "approved" and ref == "meeting" and tracker.minutes_draft_missing(block):
        return f"{n}: not approved — {tracker.NO_DRAFT_MSG}."
    return None


def decide_entry(n, p, data, ref, block, decision, mode=None):
    """decide_draft, after the no-draft check."""
    return no_draft_refusal(n, ref, block, decision) or decide_draft(n, p, data, ref, block, decision, mode)
# ===== end BL-260 point 4 =====


def word_draft(draft):
    """Whether a block's draft is a Word file (v2.1.0 P3: a creaite document has no Word to compare or clean)."""
    return bool(draft) and not str(draft).lower().endswith(".html")


def decide_draft(n, p, data, ref, block, decision, mode=None):
    """Record a decision on draft minutes, a report or a file change in its proposal. Approving minutes first
    compares the draft with the staged items (`mode` sync or as-staged settles a difference) and cleans the Word
    file; a draft open in Word is refused. Returns a message for Alan.
    """
    field = {"meeting": "minutes_decision", "report": "report_decision"}.get(ref, "file_changes_decision")
    draft = block.get("draft")
    if decision == "approved" and draft and docx_tools.is_open(paths.resolve(draft)):
        return f"{n}: {Path(draft).name} is open in Word. Close it, then approve again."
    if decision == "approved" and draft and ref == "meeting" and mode != "as-staged":
        diffs = minutes_differences(data, block)
        if mode == "sync":
            for d in [d for d in diffs if d.get("item")]:
                d["item"]["values"][d["field"]] = d["value"] if d["value"] else None
            save(p, data)
            tracker.cmd_validate(str(p))
            data.update(json.loads(p.read_text(encoding="utf-8")))
            block = data[ref]
            diffs = [d for d in diffs if not d.get("item")]
        if diffs:
            listed = "\n    ".join(d["msg"] for d in diffs)
            hint = (f'say "approve {n} --sync" to update the staged items to match the draft, or '
                    f'"approve {n} --as-staged" to keep them') if any(d.get("item") for d in diffs) else \
                   f'say "re-extract" (minutes.py refresh) to rebuild the staged items from the draft, or "approve {n} --as-staged" to keep them'
            return f"{n}: not approved — the draft differs from the staged items:\n    {listed}\n  ({hint})"
    if decision == "approved" and word_draft(draft) and ref == "report" and block.get("kind") == "weekly" and mode != "as-staged":
        diffs = weekly_differences(block)
        if diffs and mode == "sync":
            sync_weekly(data, block, diffs)
            save(p, data)
            tracker.cmd_validate(str(p))
            diffs = []
        if diffs:
            listed = "\n    ".join(d["msg"] for d in diffs)
            return (f"{n}: not approved — the draft differs from the staged items:\n    {listed}\n  (say \"approve {n} "
                    f"--sync\" to update the staged items to match the draft, or \"approve {n} --as-staged\" to keep them)")
    if decision == "approved" and draft and ref == "report" and mode != "as-staged" and \
            (block.get("kind") == "client" or (block.get("kind") == "steerco" and block.get("version") == "client")):   # BL-92: the client-safe one-pager is checked like a client report
        found = client_findings(block)
        if found:
            listed = "\n    ".join(found)
            return (f"{n}: not approved — possible internal content in the client report:\n    {listed}\n  (edit the "
                    f"draft, or say \"approve {n} --as-staged\" to file it anyway)")
    if decision == "approved" and word_draft(draft):
        r = subprocess.run([sys.executable, str(DOCX_TOOLS), "clean", str(paths.resolve(draft))],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return f"{n}: {r.stdout.strip()}"
        msg = r.stdout.strip()
    else:
        msg = ""
    block[field] = decision
    save(p, data)
    what = {"meeting": "Minutes", "report": "Report"}.get(ref, "File change")
    return f"{n}: {what} {decision} — {block.get('title', '')}" + (f". {msg}" if msg else "")


DUP_ID = r"[A-Z][A-Z0-9]{1,6}-(?:[A-Z]-)?\d{3,}"


def reject_phrase(words):
    """BL-133 stage B: "4 as a duplicate of ABC-A-009" or "4 because not mine to track" → (numbers, reason, duplicate_of)."""
    text = " ".join(words)
    m = re.search(rf"\s+as (?:a )?duplicate of ({DUP_ID})\s*$", text, re.I)
    if m:
        return text[:m.start()].strip(), "Duplicate", m.group(1).upper()
    m = re.search(r"\s+(?:because|as)\s+(.+)$", text, re.I)
    if m:
        return text[:m.start()].strip(), m.group(1).strip().rstrip(".")[:1].upper() + m.group(1).strip().rstrip(".")[1:], None
    return text, None, None


def mark_rejected(target, why, dup):
    """A rejection's reason and the item it duplicates (BL-133), and when it was made (BL-315: Activity's recent rejects)."""
    if why or dup:
        target["reject_reason"] = why
        if dup:
            target["duplicate_of"] = dup
    target["rejected_at"] = datetime.now().isoformat(timespec="seconds")


def cmd_decide(spec, decision, mode=None, reason=None, duplicate_of=None, guesses=None):
    """Approve or reject the numbered items, writing the decisions into their proposals in system/staging/.
    A rejection keeps its reason or the item it duplicates (BL-133); with `guesses` ({n: (reason, duplicate_of)}, BL-315's Use each
    guess) each item takes its own. Nothing reaches the database until apply.
    """
    out, done = [], 0
    reason = canonical_reason(reason)                                        # BL-315: "chatter" is Chatter
    if duplicate_of:
        duplicate_of = duplicate_of.upper()
        if not re.fullmatch(DUP_ID, duplicate_of):
            print(f"{duplicate_of} isn't an item ID (like ABC-A-009, ABC-014 or ABC-D-002). Nothing was rejected.")
            return 2
        with tracker.connect() as con:
            if not tracker.item_row(con, duplicate_of, ("actions", "raid", "decisions")):
                print(f"There is no {duplicate_of} in the tracker. Nothing was rejected.")
                return 2
        reason = reason or "Duplicate"
    if reason and (len(reason) > 200 or "\n" in reason):
        print("A reason is one line of at most 200 characters. Nothing was rejected.")
        return 2
    for n in parse_numbers(spec):
        p, data, ref, target = lookup(n)
        if ref in ("meeting", "report", "file_changes"):
            msg = decide_entry(n, p, data, ref, target, decision, mode)   # BL-260 point 4: refuses minutes with no draft
            out.append(msg)
            recorded = "not approved" not in msg and "open in Word" not in msg and "is open" not in msg
            done += recorded
            debuglog.info("review", f"{ref} {decision if recorded else 'not ' + decision}: {Path(target.get('draft') or p.name).name}")
            continue
        if target.get("decision") != "pending":
            out.append(f"{n}: already {target.get('decision')}")
            continue
        if decision == "approved" and needs_project(target):
            out.append(f"{n}: needs a project first (say \"{n} is <CODE>\")")
            debuglog.info("review", f"not approved: {p.name} item {target.get('n')} needs a project")
            continue
        if decision == "approved" and "conflict" in target.get("flags", []):
            out.append(f"{n}: conflict — say \"keep {n}\" (database version) or \"override {n}\" (this edit)")
            debuglog.info("review", f"not approved: {target.get('id') or p.name} is a conflict")
            continue
        if decision == "approved" and "invalid" in target.get("flags", []):
            out.append(f"{n}: invalid — {target.get('invalid_reason')}; edit it first")
            debuglog.info("review", f"not approved: {p.name} item {target.get('n')} is invalid: {debuglog.rule(target.get('invalid_reason'))}")
            continue
        target["decision"] = decision
        if decision == "rejected":                                           # BL-133 stage B; BL-315's own guess per item
            mark_rejected(target, *((guesses.get(n) or (None, None)) if guesses is not None else (reason, duplicate_of)))
        save(p, data)
        done += 1
        count_suggestion(target, decision)                                   # AI drafts (sprint-drafts-fields, -extraction)
        debuglog.info("review", f"{decision} {p.name} item {target.get('n')} ({target.get('table')} {target.get('id') or 'new'})")
    print(f"{'Approved' if decision == 'approved' else 'Rejected'} {done}.")
    debuglog.info("review", f"{decision}: {done} of {len(parse_numbers(spec))} decided")
    for line in out:
        print("  " + line)
    return 0


PLURALS = {"decision made": "decisions made", "new decision": "new decisions", "new risk": "new risks", "health change": "health changes",
           "weekly update": "weekly updates", "need a project": "need a project", "conflict": "conflicts",
           "invalid": "invalid", "not a strong match": "not strong matches", "minutes": "sets of minutes",
           "report": "reports"}
SINGULAR = {"need a project": "needs a project", "minutes": "set of minutes", "not a strong match": "not a strong match"}


def plural(k, v):
    """The count label `k` in the singular or plural for `v`."""
    return PLURALS.get(k, k) if v != 1 else SINGULAR.get(k, k)


# ===== BL-260 point 4 (fix-minutes-approve) =====
PLURALS["minutes with no Word draft"] = "sets of minutes with no Word draft (reject them and process the meeting again)"
SINGULAR["minutes with no Word draft"] = "set of minutes with no Word draft (reject it and process the meeting again)"


def no_draft_minutes(drafts):
    """The (file, "meeting") entries among drafts whose minutes have no Word draft: never approved, in bulk or alone."""
    found = set()
    for p, data in proposals():
        if (p.name, "meeting") in drafts and tracker.minutes_draft_missing(data.get("meeting")):
            found.add((p.name, "meeting"))
    return found
# ===== end BL-260 point 4 =====


def cmd_bulk(scope=None, strong=False):
    """Approve the routine pending items (one project with `scope`; strong matches only with `strong`). Never drafts,
    health changes, new decisions, new risks, weekly updates, conflicts or items without a project.
    """
    approved, held = 0, {}
    rows = build_rows(scope if scope else None)
    for p, data in proposals():
        changed = False
        for item in data.get("items", []):
            if item.get("applied") or item.get("decision") != "pending":
                continue
            if scope and project_of(item) != scope:
                continue
            reason = individual_only(item)
            if needs_project(item):
                reason = "need a project"
            elif "conflict" in item.get("flags", []):
                reason = "conflict"
            elif "invalid" in item.get("flags", []):
                reason = "invalid"
            elif strong and item.get("match") != "strong":
                reason = "not a strong match"
            if reason:
                held[reason] = held.get(reason, 0) + 1
                continue
            item["decision"] = "approved"
            approved += 1
            changed = True
        if changed:
            save(p, data)
    drafts = {(r["file"], r["ref"]) for r in rows if r["section"] == 0}
    nodraft = no_draft_minutes(drafts)                                       # BL-260 point 4
    for r in drafts:
        k = "minutes with no Word draft" if r in nodraft else "minutes" if r[1] == "meeting" else "report"
        held[k] = held.get(k, 0) + 1
    left = ", ".join(f"{v} {plural(k, v)}" for k, v in held.items())
    print(f"Approved {approved}." + (f" Still need individual approval: {left}." if left else ""))
    debuglog.info("review", f"bulk approved {approved}" + (f", held: {left}" if left else "") + (f" (project {scope})" if scope else ""))
    return 0


# ===== BL-200 (sprint-review-work) ===== change the project in Review: one pending new item, or a whole set of minutes.
# "assign <n> <CODE>" moves any pending new item (no longer only a Possible or unresolved one); on a minutes entry it moves
# every item from those minutes, rebuilds the minutes' file_ops for the new project (paths.folder, so the OneDrive layout
# holds) and updates meeting.projects, so the processed line names the new project at apply. Nothing reaches the tracker
# until approval and apply; nothing moves on disk until the minutes are approved. An update item names one tracker row,
# so it is never moved (it is left with a note). The match signals are kept, so BL-28's "remember this signal" is offered
# for the new project.

def project_refusal(con, code):
    """Why `code` can't take items (unknown or closed), or None."""
    row = con.execute("SELECT name, active FROM projects WHERE code = ?", (code,)).fetchone()
    if not row:
        return f"project {code} isn't in the tracker."
    if not row[1]:
        return f"{row[0]} ({code}) is closed; reopen it first, or choose an active project."
    return None


def remember_cleared(item, old, code, kept):
    """BL-281: keep what a move from `old` cleared (`kept`) in the item's moved_cleared, keyed by `old`, and put back what an
    earlier move from `code` cleared, now that the item has moved back there."""
    held = item.get("moved_cleared")
    held = dict(held) if isinstance(held, dict) else {}
    back = held.pop(code, None) or {}
    v = item["values"]
    for f in ("milestone", "workstream"):
        if back.get(f) and not v.get(f):
            v[f] = back[f]
    if "ws_suggest" in back:
        item["flags"] = [*[f for f in item.get("flags", []) if f != "new-workstream"], "new-workstream"]
        if back["ws_suggest"] is not None:
            item["ws_suggest"] = back["ws_suggest"]
    if kept and old and old != code:
        held[old] = {**held.get(old, {}), **kept}
    if held:
        item["moved_cleared"] = held
    else:
        item.pop("moved_cleared", None)


def move_item(con, item, code):
    """Give a new item another project: a milestone or workstream of the old project is cleared; the match becomes strong.
    Returns what was cleared, for the message."""
    v = item.setdefault("values", {})
    old = v.get("project")
    cleared = []
    kept = {}                                       # BL-281: what this move clears, so moving back puts it back
    v["project"] = code
    if v.get("milestone") and not str(v["milestone"]).startswith(f"{code}-M-"):
        kept["milestone"] = v["milestone"]
        v["milestone"] = None                       # a milestone link stays within its project
        cleared.append("milestone")
    if v.get("workstream"):
        same = tracker.match_workstream(con, code, v["workstream"])
        if same:
            v["workstream"] = same
        else:
            kept["workstream"] = v["workstream"]
            v["workstream"] = None
            cleared.append("workstream")
    if "new-workstream" in item.get("flags", []):  # BL-58: the suggestion was for the old project
        item["flags"] = [f for f in item["flags"] if f != "new-workstream"]
        kept["ws_suggest"] = item.pop("ws_suggest", None)
    remember_cleared(item, old, code, kept)
    item["match"] = "strong"
    if item.get("moved_from") == code:
        item.pop("moved_from")                      # moved back where it came from
    elif old and old != code:
        item["moved_from"] = item.get("moved_from") or old
    item["edited_in"] = "review"
    return cleared


def cmd_assign(n, code, frm=None, moved="leave", dry_run=False, as_json=False):
    """Give a pending new item another project (BL-200), clearing its old milestone and workstream; on a minutes
    entry, moves the minutes' items and filing instead. `dry_run` only shows it. Writes the proposal file.
    """
    code = code.upper()
    p, data, ref, item = lookup(int(n))
    if ref == "meeting":
        return cmd_assign_minutes(n, p, data, item, code, frm and frm.upper(), moved, dry_run, as_json)
    if ref in ("report", "file_changes"):
        sys.exit(f"creaite: {n} is a {'report' if ref == 'report' else 'file change'}; its project can't be changed here.")
    if item.get("op") != "new":
        sys.exit(f"creaite: {n} is an update to {item.get('id')}, an item already in the tracker; it stays with its project.")
    con = tracker.connect()
    why = project_refusal(con, code)
    if why:
        sys.exit(f"creaite: {why}")
    old = (item.get("values") or {}).get("project")
    if old == code and item.get("match") == "strong":
        print(f"{n} is already in {project_label(code)}.")
        return 0
    if dry_run:
        print(f"Move {n} from {project_label(old) if old else 'no project'} to {project_label(code)}")
        return 0
    cleared = move_item(con, item, code)
    if item.get("decision") == "approved":
        item["decision"] = "pending"
    save(p, data)
    print(f"{n}: project set to {project_label(code)}; waiting for a decision."
          + (f" Cleared its {' and '.join(cleared)} (they belonged to {project_label(old)})." if cleared and old else ""))
    debuglog.info("review", f"{p.name} item {item.get('n')} moved from {old or 'none'} to {code}"
                  + (f", cleared {', '.join(cleared)}" if cleared else ""))
    return 0


def _swap(path, pairs):
    """`path` with a leading old folder replaced by the new one (pairs: [(old_dir, new_dir)]); unchanged if none matches."""
    for old, new in pairs:
        if path and (path == old or path.startswith(old + "/")):
            return new + path[len(old):]
    return path


def cmd_assign_minutes(n, p, data, block, code, frm, moved, dry_run, as_json):
    """Move draft minutes' items and filing from project `frm` to `code` (BL-200); `moved` 'all' also takes items
    already moved on their own. Update items stay with their project. Writes the proposal file.
    """
    if block.get("applied"):
        sys.exit(f"creaite: minutes {n} have already been filed.")
    projects = list(block.get("projects") or [])
    if not frm:
        if len(projects) != 1:
            names = ", ".join(f"{project_label(c)} ({c})" for c in projects)
            sys.exit(f"creaite: these minutes are filed under {names}. Say which project's items to move, "
                     f"for example: assign {n} {code} --from={projects[0] if projects else 'ABC'}")
        frm = projects[0]
    if frm not in projects:
        sys.exit(f"creaite: these minutes aren't filed under {frm}.")
    if frm == code:
        sys.exit(f"creaite: these minutes are already filed under {project_label(code)}.")
    con = tracker.connect()
    why = project_refusal(con, code)
    if why:
        sys.exit(f"creaite: {why}")
    live = [i for i in data.get("items", []) if not i.get("applied") and i.get("decision") != "rejected"]
    mine = [i for i in live if i.get("op") == "new" and project_of(i) == frm and not needs_project(i)]
    alone = [i for i in live if i.get("op") == "new" and i.get("moved_from") == frm and project_of(i) not in (frm, code)]
    updates = [i for i in live if i.get("op") == "update" and project_of(i) == frm]
    take = mine + (alone if moved == "all" else [])
    count = len(take)
    headline = f"Move {count} item{'' if count == 1 else 's'} from {project_label(frm)} to {project_label(code)}"
    notes = [f"{i.get('id')} is an update to an item already in the tracker, so it stays with {project_label(frm)}."
             for i in updates]
    if alone and moved != "all":
        notes.append(f"{len(alone)} item{' was' if len(alone) == 1 else 's were'} moved on {'its' if len(alone) == 1 else 'their'} "
                     f"own before and stay{'s' if len(alone) == 1 else ''} where {'it is' if len(alone) == 1 else 'they are'} "
                     f"(add --all to move {'it' if len(alone) == 1 else 'them'} too).")
    # the files follow: the minutes and transcript copies go to the new project's folders
    pairs = [(paths.rel(paths.folder(frm, "minutes")), paths.rel(paths.folder(code, "minutes"))),
             (paths.rel(paths.folder(frm, "transcripts")), paths.rel(paths.folder(code, "transcripts")))]
    merging = code in projects                       # the new project already has its own copies
    ops = []
    for op in block.get("file_ops", []):
        if op.get("op") == "copy" and _swap(op.get("to"), pairs) != op.get("to"):
            if not merging:
                ops.append({**op, "to": _swap(op["to"], pairs)})
            continue
        ops.append(dict(op))
    tr = block.get("transcript")
    if tr and not merging and not any(o.get("op") == "copy" and o.get("from") == "transcript"
                                      and str(o.get("to")).startswith(pairs[1][1] + "/") for o in ops):
        tpath = paths.resolve(tr).resolve()
        here = lambda c: paths.folder(c, "transcripts").resolve() in (tpath.parent, *tpath.parents)   # noqa: E731
        if here(frm) and not here(code):          # Alan's own file in the old project's folder: left there, copied to the new
            stem = next((Path(o["to"]).stem for o in ops if o.get("op") == "copy" and o.get("from") == "draft"), Path(tr).stem)
            at = next((k for k, o in enumerate(ops) if o.get("op") == "remove"), len(ops))
            ops.insert(at, {"op": "copy", "from": "transcript", "to": f"{pairs[1][1]}/{stem}{Path(tr).suffix}"})
    files = [o["to"] for o in ops if o.get("op") == "copy"]
    if dry_run:
        out = {"from": frm, "to": code, "items": count, "alone": len(alone), "updates": [i.get("id") for i in updates],
               "files": files, "headline": headline, "notes": notes, "projects": projects}
        print(json.dumps(out, ensure_ascii=False) if as_json else "\n".join([headline] + notes))
        return 0
    cleared = 0
    for i in take:
        cleared += bool(move_item(con, i, code))
        v = i["values"]
        if v.get("source"):
            v["source"] = _swap(v["source"], pairs)
        if i.get("decision") == "approved":
            i["decision"] = "pending"
    block["file_ops"] = ops
    block["projects"] = list(dict.fromkeys(code if c == frm else c for c in projects))
    if block.get("source_map"):
        block["source_map"] = {_swap(k, pairs): _swap(v, pairs) for k, v in block["source_map"].items()}
    block.setdefault("moved", []).append({"from": frm, "to": code, "at": datetime.now().isoformat(timespec="seconds"),
                                          "items": count})
    save(p, data)
    print(f"Minutes {n}: moved {count} item{'' if count == 1 else 's'} from {project_label(frm)} to {project_label(code)}. "
          f"The minutes and transcript will be filed in {project_label(code)}'s folders when the minutes are approved."
          + (f" {cleared} had a milestone or workstream of {project_label(frm)}, now cleared." if cleared else ""))
    for note in notes:
        print("Note: " + note)
    debuglog.info("review", f"{p.name} minutes moved from {frm} to {code}: {count} item(s), {len(updates)} update(s) left, "
                  f"{len(alone)} moved alone ({'taken' if moved == 'all' else 'left'}), {len(files)} copy op(s)")
    return 0
# ===== end BL-200 =====


def to_stored(field, value):
    """A value as typed in 'field=value' converted for storing: DD-MM-YYYY dates to YYYY-MM-DD, yes/no flags to 1/0."""
    if value.lower() in ("", "none", "blank"):
        return None
    if field in tracker.DATE_FIELDS and re.fullmatch(r"\d{2}-\d{2}-\d{4}", value):
        d, m, y = value.split("-")
        return f"{y}-{m}-{d}"
    if field == "client_visible":
        return 1 if value.lower() in ("1", "yes", "true") else 0
    return value


def cmd_edit(n, pairs):
    """Change fields of a pending item ('field=value', dates DD-MM-YYYY), validate it and approve it if valid."""
    p, data, ref, item = lookup(int(n))
    if ref in ("meeting", "report", "file_changes"):
        sys.exit("creaite: edit drafts in Word (or ask Claude to change a file change), then approve.")
    target = item.setdefault("values", {}) if item.get("op") == "new" else item.setdefault("changes", {})
    for pair in pairs:
        field, _, value = pair.partition("=")
        target[field.strip()] = to_stored(field.strip(), value.strip())
    save(p, data)
    tracker.cmd_validate(str(p))
    data = json.loads(p.read_text(encoding="utf-8"))
    item = next(i for i in data["items"] if i.get("n") == ref)
    fields = ", ".join(x.partition("=")[0].strip() for x in pairs)
    if "invalid" in item.get("flags", []):
        print(f"{n}: not approved — {item.get('invalid_reason')}")
        debuglog.info("review", f"{p.name} item {item.get('n')} edited ({fields}), still invalid: {debuglog.rule(item.get('invalid_reason'))}")
        return 1
    if needs_project(item):
        print(f"{n}: edited; still needs a project.")
        debuglog.info("review", f"{p.name} item {item.get('n')} edited ({fields}); still needs a project")
        return 0
    item["decision"] = "approved"
    save(p, data)
    print(f"{n}: edited and approved.")
    debuglog.info("review", f"{p.name} item {item.get('n')} edited ({fields}) and approved")
    return 0


# ===== Workstreams (BL-58, BL-56) =====

def ws_note(item):
    """The Review line for an item whose workstream isn't one of its project's (BL-58)."""
    if "new-workstream" not in item.get("flags", []) or not item.get("ws_suggest"):
        return ""
    return f"New workstream “{item['ws_suggest']}” for {project_of(item)}? (workstream N add, or skip)"


def cmd_workstream(n, action, opts):
    """Settle an item flagged new-workstream (BL-58): add the suggested workstream, approved, ahead of the item
    in the same proposal and set it on the item, or skip and leave it blank.
    """
    p, data, ref, item = lookup(int(n))
    if not isinstance(item, dict) or "new-workstream" not in item.get("flags", []):
        sys.exit(f"creaite: {n} isn't waiting for a workstream decision.")
    name, project = item.get("ws_suggest", ""), project_of(item)
    item["flags"] = [f for f in item["flags"] if f != "new-workstream"]
    if action == "skip":
        item.pop("ws_suggest", None)
        save(p, data)
        print(f"{n}: left without a workstream.")
        return 0
    con = tracker.connect()
    existing = tracker.match_workstream(con, project, name)
    if not existing:
        values = {"project": project, "name": name, "source": f"Alan in review, {datetime.now():%Y-%m-%d}"}
        values.update({k: v.strip() for k, v in opts.items() if v and v.strip()})
        at = data["items"].index(item)
        new_n = max(int(i.get("n") or 0) for i in data["items"]) + 1
        data["items"].insert(at, {"n": new_n, "op": "new", "table": "workstreams", "values": values,
                                  "match": "strong", "flags": [], "decision": "approved"})
    (item.get("values") or item.setdefault("changes", {}))["workstream"] = existing or name
    item.pop("ws_suggest", None)
    save(p, data)
    tracker.cmd_validate(str(p))
    print(f"{n}: workstream {existing or name} " + ("set (it already exists)." if existing else
                                                     f"added to {project} and set; approve the item as usual."))
    return 0


def cmd_conflict(n, keep):
    """Settle a conflict: `keep` the database version (the edit is rejected) or apply the edit over it."""
    p, data, ref, item = lookup(int(n))
    if "conflict" not in item.get("flags", []):
        sys.exit(f"creaite: {n} isn't a conflict.")
    if keep:
        item["decision"] = "rejected"
        print(f"{n}: kept the database version; the edit is rejected.")
        debuglog.info("review", f"conflict on {item.get('id')}: kept the database version")
    else:
        row = tracker.fetch(tracker.connect(), item["table"], item["id"])
        item["based_on"] = row["updated_at"] if row is not None and "updated_at" in row.keys() else None
        item["flags"] = [f for f in item.get("flags", []) if f != "conflict"]
        item.pop("conflict_reason", None)
        item.pop("current", None)
        item["decision"] = "approved"
        print(f"{n}: the edit will replace the newer change at the next apply.")
        debuglog.info("review", f"conflict on {item.get('id')}: the edit overrides")
    save(p, data)
    return 0



# ===== BL-208 (sprint-insight) ===== Review one proposal at a time: the focus queue and the spot-check sample. The queue is what needs
# Alan (minutes, reports, new decisions and risks, conflicts, no project, guessed fields), guessed fields first; routine items are
# approved together and one in review.spot_check_every (10) are shown as a spot-check. The sample is random but stable for a
# batch (seeded by its files), so a reload shows the same ones. Never zero in the first month: the rate floor holds for 30 days
# after the tracker's first apply.
SPOT_DEFAULT = 0.1


INFERRED_FIELDS = {"owner", "made_by", "due_date", "needed_by", "priority", "impact", "likelihood", "type", "status", "response_action",
                   "description", "decision", "date", "workstream", "milestone", "project"}


def clean_inferred(raw):
    """An item's guessed fields (`inferred`: [{field, why}], written by cx-minutes and cx-sweep), kept only when well formed."""
    out = []
    for x in raw if isinstance(raw, list) else []:
        if isinstance(x, dict) and x.get("field") in INFERRED_FIELDS and isinstance(x.get("why"), str) and x["why"].strip():
            out.append({"field": x["field"], "why": " ".join(x["why"].split())[:160]})
    return out[:10]


def spot_rate(settings=None, first_apply=None, today=None):
    """The share of routine items shown as a spot-check: one in review.spot_check_every; never zero in the
    tracker's first 30 days (BL-208).
    """
    cfg = (settings if settings is not None else paths.load_settings()).get("review") or {}
    try:
        every = int(cfg.get("spot_check_every", 10))            # one routine item in this many is shown; 0 shows none
    except (TypeError, ValueError):
        every = 10
    rate = 0.0 if every <= 0 else min(1.0, 1 / every)
    if rate == 0 and first_apply and today:
        from datetime import date as _d
        try:
            if (_d.fromisoformat(today) - _d.fromisoformat(first_apply[:10])).days < 30:
                rate = SPOT_DEFAULT
        except ValueError:
            pass
    return rate


def focus_queue(rows, rate):
    """{"queue": [n…], "spot": [n…], "routine": [n…]} from Review's rows (build_dashboard.review_queue): rows needing Alan first,
    those with guessed fields (`inferred`) at the head; routine rows (a project, nothing individual, no conflict) sampled at `rate`."""
    import hashlib
    import math
    live = [r for r in rows if not r.get("done")]
    routine = [r for r in live if r.get("p") and not r.get("indiv") and not r.get("inferred") and "conflict" not in (r.get("flags") or [])]
    need = [r for r in live if r not in routine]
    need.sort(key=lambda r: (not r.get("inferred"), r.get("kind") == "draft", r.get("n") or 0))
    seed = hashlib.sha1("|".join(sorted({r.get("file") or "" for r in live})).encode()).hexdigest()
    k = 0 if not routine or rate <= 0 else max(1, math.floor(len(routine) * rate + 0.5))
    pick = sorted(routine, key=lambda r: hashlib.sha1(f"{seed}|{r.get('file')}|{r.get('n')}".encode()).hexdigest())[:k]
    spot = sorted((r["n"] for r in pick))
    return {"queue": [r["n"] for r in need] + spot, "spot": spot, "routine": [r["n"] for r in routine], "rate": rate}


def main(argv):
    """Run the review command in `argv` (see the module docstring)."""
    if not argv:
        print(__doc__)
        return 2
    cmd, args = argv[0], argv[1:]
    flags = {a for a in args if a.startswith("--")}
    args = [a for a in args if not a.startswith("--")]
    if cmd == "pending":
        return cmd_pending()
    if cmd == "list":
        return cmd_list(args[0] if args else None, "--json" in flags)
    if cmd in ("approve", "reject") and args:
        mode = "sync" if "--sync" in flags else "as-staged" if "--as-staged" in flags else None
        if cmd == "reject":                                               # BL-133 stage B: a reason and what it duplicates
            kv = dict(a[2:].partition("=")[::2] for a in argv[1:] if a.startswith("--") and "=" in a)
            spec, reason, dup = reject_phrase(args)
            return cmd_decide(spec, "rejected", None, kv.get("reason") or reason, kv.get("duplicate-of") or dup)
        if "--unlabelled" in flags:                    # BL-121: gone, as there is no label check any more
            print("--unlabelled is no longer an option: a draft is approved without any sensitivity label. Say it again without it.")
            return 2
        return cmd_decide(" ".join(args), "approved" if cmd == "approve" else "rejected", mode)
    if cmd == "bulk":
        return cmd_bulk(args[0] if args else None, "--strong" in flags)
    if cmd == "assign" and len(args) == 2:                     # BL-200: any pending new item, or a set of minutes
        kv = dict(a[2:].partition("=")[::2] for a in argv[1:] if a.startswith("--") and "=" in a)
        return cmd_assign(args[0], args[1], kv.get("from"), "all" if "--all" in flags else "leave",
                          "--dry-run" in flags, "--json" in flags)
    if cmd == "edit" and len(args) >= 2:
        return cmd_edit(args[0], args[1:])
    if cmd == "workstream" and len(args) >= 2 and args[1] in ("add", "skip"):
        opts = dict(a[2:].partition("=")[::2] for a in argv[1:] if a.startswith("--") and "=" in a)
        return cmd_workstream(args[0], args[1], {k: v for k, v in opts.items() if k in ("lead", "keywords", "aliases", "channel")})
    if cmd in ("keep", "override") and len(args) == 1:
        return cmd_conflict(args[0], cmd == "keep")
    print(__doc__)
    return 2



# ===== BL-221 (sprint-drafts-extraction) ===== "Looks like": a pending new item marked at staging as repeating an existing one
# (`looks_like`, extraction.py). merge turns it into an update to that item, carrying any new date, latest update or response (a
# repeat that brings nothing new is rejected as its duplicate instead, so the reason is recorded); keep-new leaves it a new item and
# drops the mark. Only within the item's own project and into an open item: across projects, or onto a closed item, it is Keep as
# new or Reject as a duplicate. Each is counted for BL-233 (feature "repeat"; counts only). Nothing reaches the tracker here.
def repeat_target(n):
    """(proposal path, data, item, its looks_like mark) for review number n, or exits saying why it can't be merged."""
    p, data, ref, item = lookup(int(n))
    ll = item.get("looks_like") if ref not in ("meeting", "report", "file_changes") else None
    if not ll or item.get("op") != "new" or ll.get("merged"):
        sys.exit(f"creaite: {n} isn't marked as looking like an existing item.")
    return p, data, item, ll


def cmd_merge(n):
    """Merge a repeat into the item it repeats, as an update (BL-221)."""
    import extraction
    p, data, item, ll = repeat_target(n)
    if not ll.get("same"):
        print(f"{n}: {ll['id']} is in {tracker.project_label(ll.get('project') or '')}, another project: keep it as new, "
              "or reject it as a duplicate.")
        return 1
    con = tracker.connect()
    row = tracker.fetch(con, item["table"], ll["id"])
    con.close()
    if row is None or dict(row)["status"] not in extraction.OPEN[item["table"]]:
        print(f"{n}: {ll['id']} is {'closed' if row is not None else 'not in the tracker'}: keep it as new, or reject it as a duplicate.")
        return 1
    new = extraction.merged_item(item, dict(row))
    if new is None:                                  # nothing to carry: it is the same item, so it is rejected as its duplicate
        item.update(decision="rejected", reject_reason="Duplicate", duplicate_of=ll["id"], decided_in="review", was=snapshot(item))
        save(p, data)
        extraction.count("repeat", "used")
        print(f"{n}: nothing new to carry to {ll['id']}, so it was rejected as a duplicate of it.")
        return 0
    data["items"][data["items"].index(item)] = new
    save(p, data)
    extraction.count("repeat", "used")
    debuglog.info("review", f"{p.name} item {new['n']} merged into {ll['id']} ({', '.join(new['changes'])})")
    print(f"{n}: merged as an update to {ll['id']} ({', '.join(UPDATE_LABELS.get(f, f) for f in new['changes'])}); approve it as usual.")
    return tracker.cmd_validate(str(p))


def cmd_keep_new(n):
    """Keep a repeat as a new item: the mark is dropped and the choice counted (BL-221)."""
    import extraction
    p, data, item, ll = repeat_target(n)
    item["looks_like"] = {**ll, "kept": True}
    save(p, data)
    extraction.count("repeat", "rejected")
    print(f"{n}: kept as a new item; it no longer says it looks like {ll['id']}.")
    return 0


def repeat_note(item):
    """The line Review shows for a repeat: "Looks like ABC-A-009 (same project, open) · Very likely"."""
    ll = item.get("looks_like") or {}
    if not ll or ll.get("kept") or ll.get("merged") or item.get("op") != "new":
        return ""
    where = "same project" if ll.get("same") else tracker.project_label(ll.get("project") or "")
    return f"Looks like {ll['id']} ({where}, {ll.get('state', 'open')}) · {ll.get('strength', 'Possible')}"


_ws_note_before_repeats = ws_note


def _ws_note_with_repeats(item):
    return " · ".join(x for x in (_ws_note_before_repeats(item), repeat_note(item)) if x)


ws_note = _ws_note_with_repeats
_main_before_repeats = main


def _main_with_repeats(argv):
    if len(argv) == 2 and argv[0] in ("merge", "keep-new"):
        return (cmd_merge if argv[0] == "merge" else cmd_keep_new)(argv[1])
    return _main_before_repeats(argv)


main = _main_with_repeats
# ===== end BL-221 =====

# ===== BL-297 (sprint-smart-updates) ===== Smarter updates in Review.
# E (Alan, 13-10-2026): an update to an action, RAID item or decision that changes only its due date (a decision's needed-by) and latest
# update is routine; one that changes anything else (status, response, owner, title, project, …) is approved on its own. The rules
# above it (closing, a decision made, drafted text, client wording) still come first. Nothing outside these work items changes.
# D: retarget turns a pending new item into an update to an existing item Alan picks (the same result as merge, marked or not), and
# unmerge undoes either; candidates lists what the picker offers. Only the proposal changes; nothing reaches tracker.db before apply.
ROUTINE_FIELDS = {"actions": ("due_date", "latest_update"), "raid": ("due_date",), "decisions": ("needed_by",)}
CHANGE_WORDS = {"status": "status change", "response_action": "response change", "owner": "owner change", "made_by": "owner change",
                "description": "title change", "decision": "title change", "project": "project change"}


def update_rule(item):
    """Why a work item's update is approved on its own (it changes more than the due date and latest update), or None."""
    table = item.get("table")
    if item.get("op") != "update" or table not in ROUTINE_FIELDS:
        return None
    other = [f for f in item.get("changes") or {} if f not in ROUTINE_FIELDS[table]]
    return (CHANGE_WORDS.get(other[0]) or f"change to {UPDATE_LABELS.get(other[0], other[0].replace('_', ' '))}") if other else None


def snapshot(item):
    """The item as it was, for unmerge (a copy, without an older snapshot inside it)."""
    return json.loads(json.dumps({k: v for k, v in item.items() if k != "was"}))


def retarget_refusal(ref, item, target):
    """Why item can't be retargeted (not a pending new item, no project, not an ID), or None."""
    import extraction
    if ref in ("meeting", "report", "file_changes") or item.get("op") != "new" or item.get("table") not in extraction.TEXT:
        return "only a new action, RAID item or decision can update an existing item instead"
    if item.get("decision") not in (None, "pending"):
        return "it has already been decided; undo the decision first"
    if not (item.get("values") or {}).get("project") or needs_project(item):
        return "choose its project first"
    if not re.fullmatch(r"[A-Z][A-Z0-9]{2,6}-(?:[AD]-)?\d{3}", target):
        return f"{target or '(no ID)'} isn't an item ID"
    return None


def target_refusal(item, row, target):
    """Why the chosen item can't take the update (not in the tracker as this kind, another project, closed), or None."""
    import extraction
    kind = {"actions": "an action", "raid": "a RAID item", "decisions": "a decision"}[item["table"]]
    if row is None:
        return f"{target} isn't {kind} in the tracker"
    if row["project"] != item["values"]["project"]:
        return f"{target} is in {tracker.project_label(row['project'])}, another project"
    if row["status"] not in extraction.OPEN[item["table"]]:
        return f"{target} is {row['status']}; only an open item is updated"
    return None


def retarget_note(item, target):
    """What Quality keeps about a retarget (counts and IDs only): the item chosen, the one marked (if any), the day."""
    import extraction
    ll = item.get("looks_like") or {}
    marked = ll.get("id") if ll and not ll.get("kept") else None
    return {"to": target, "marked": marked, "at": extraction.today()}


def cmd_retarget(n, target):
    """Turn a pending new item into an update to `target`, an open item of its project (BL-297 part D)."""
    import extraction
    p, data, ref, item = lookup(int(n))
    target = str(target or "").strip().upper()
    why = retarget_refusal(ref, item, target)
    con = tracker.connect()
    row = None if why else tracker.fetch(con, item["table"], target)
    con.close()
    why = why or target_refusal(item, dict(row) if row is not None else None, target)
    if why:
        print(f"{n}: {why}.")
        return 1
    note, new = retarget_note(item, target), extraction.merged_item(item, dict(row))
    if note["marked"] == target:
        extraction.count("repeat", "used")
    if new is None:                                  # nothing to carry: it is the same item, so it is rejected as its duplicate
        item.update(decision="rejected", reject_reason="Duplicate", duplicate_of=target, decided_in="review", was=snapshot(item),
                    retargeted=note)
        save(p, data)
        print(f"{n}: nothing new to carry to {target}, so it was rejected as a duplicate of it.")
        return 0
    v = item.get("values") or {}
    new.update(retargeted=note, why=f"Update instead: raised as “{v.get(extraction.TEXT[item['table']]) or ''}”")
    data["items"][data["items"].index(item)] = new
    save(p, data)
    debuglog.info("review", f"{p.name} item {new['n']} retargeted to {target} ({', '.join(new['changes'])}"
                  + (", unmarked" if not note["marked"] else "") + ")")
    print(f"{n}: now an update to {target} ({', '.join(UPDATE_LABELS.get(f, f) for f in new['changes'])}); approve it as usual.")
    return tracker.cmd_validate(str(p))


def entry(spec):
    """(proposal path, data, ref, item) for a review number, or for "<proposal file>#<item number>" (an item no longer pending,
    such as one a retarget rejected as a duplicate, has no review number)."""
    if "#" not in str(spec):
        return lookup(int(spec))
    name, _, ref = str(spec).partition("#")
    p = paths.STAGING / name
    if not re.fullmatch(r"proposed-[\w.-]+\.json", name) or not p.exists() or not ref.isdigit():
        sys.exit(f"creaite: {spec} isn't a pending proposal's item.")
    data = json.loads(p.read_text(encoding="utf-8"))
    item = next((i for i in data.get("items", []) if i.get("n") == int(ref) and not i.get("applied")), None)
    if item is None:
        sys.exit(f"creaite: {spec} isn't a pending proposal's item.")
    return p, data, int(ref), item


def cmd_unmerge(n):
    """Undo a merge or a retarget: the proposal is the new item it was, pending again (BL-297)."""
    p, data, ref, item = entry(n)
    was = item.get("was") if ref not in ("meeting", "report", "file_changes") else None
    if not isinstance(was, dict):
        print(f"{n}: it wasn't merged or retargeted, so there is nothing to undo.")
        return 1
    data["items"][data["items"].index(item)] = {**was, "n": item["n"]}
    save(p, data)
    debuglog.info("review", f"{p.name} item {item['n']} unmerged from {item.get('id') or item.get('duplicate_of')}")
    print(f"{n}: back to a new item, as it was proposed.")
    return 0


def cmd_candidates(n, as_json=False):
    """The open items a pending new item could update instead, best matches first (Review's picker)."""
    import extraction
    _, _, ref, item = lookup(int(n))
    con = tracker.connect()
    try:
        rows = extraction.picker(con, item) if ref not in ("meeting", "report", "file_changes") else []
    finally:
        con.close()
    if as_json:
        print(json.dumps(rows, ensure_ascii=False))
        return 0
    for r in rows:
        said = f"  · {r['strength']}: {r['why']}" if r["strength"] else ""
        print(f"  {r['id']}  {r['t']}{said}" + ("  (marked)" if r["marked"] else ""))
    if not rows:
        print(f"{n}: no open item of its project to update.")
    return 0


_main_before_retarget = main


def _main_with_retarget(argv):
    if len(argv) == 3 and argv[0] == "retarget":
        return cmd_retarget(argv[1], argv[2])
    if len(argv) == 2 and argv[0] == "unmerge":
        return cmd_unmerge(argv[1])
    if argv[:1] == ["candidates"] and len(argv) in (2, 3):
        return cmd_candidates(argv[1], "--json" in argv[2:])
    return _main_before_retarget(argv)


main = _main_with_retarget
# ===== end BL-297 =====

# ===== BL-315 (v1.9.2) ===== Rejects, in real life. One reasons menu for one row or many: the seven reasons (tracker.REJECT_REASONS)
# or none; creaite's guess per row (plain code, no model): a thank-you or scheduling chatter, a near-duplicate of an open item (BL-221's
# mark or best_repeat), already done (a recently closed look-alike, or closing an item already closed), no owner named. "reject <n…>
# --guess" rejects each with its own guess. Every reject can then be undone (unreject), its reason changed (rereason) or turned into an
# approval (approve-instead), named by "<proposal file>#<item>", pending or applied. An applied reject goes back to its proposal in
# staging (out of applied/), marked `redecide` {fingerprint, apply_id}: the next apply removes or updates its `rejected` row
# (tracker.py, logged, so undo puts it back). Approve instead approves a routine item at once; one approved only on its own (minutes, a
# new decision, a new risk and the rest of individual_only) goes back to Review pending and is listed to open. The item's own decision
# changes, so Activity › Quality follows the latest choice. No schema change.
REASONS = tracker.REJECT_REASONS
THANKS = re.compile(r"\b(thanks?|thank you|cheers|many thanks|appreciated?|great (?:session|job|work|meeting|call|discussion)|"
                    r"well done|congrat\w*|welcome (?:to|aboard)|nice to meet)\b", re.I)
SCHEDULING = re.compile(r"\b(check (?:the |their |our |your )?calendars?|calendar invite|send (?:an |the |a )?invite|"
                        r"find (?:a )?(?:time|slot)|(?:re)?schedul\w+|availability|doodle|"
                        r"set up (?:a )?(?:call|meeting|catch[- ]?up)|out of (?:the )?office)\b", re.I)


def canonical_reason(reason):
    """One of the seven as it is spelt, when `reason` names it (any case); otherwise Alan's own words, unchanged."""
    text = str(reason or "").strip()
    if not text:
        return reason
    return next((r for r in REASONS if r.lower() == text.lower().rstrip(".")), text)


def no_owner(item):
    """A new action with no owner named (or TBC)."""
    v = item.get("values") or {}
    return item.get("op") == "new" and item.get("table") == "actions" and \
        (not str(v.get("owner") or "").strip() or str(v.get("owner")).strip().lower() in ("tbc", "unassigned", "?"))


def repeat_guess(con, item, register):
    """Duplicate (of an open item) or Already done (a closed one) from the item's "Looks like" mark, or plain code's best match."""
    import extraction
    if item.get("op") != "new" or not extraction.switched_on("repeat"):
        return None
    ll = item.get("looks_like") or {}
    if ll.get("kept") or ll.get("merged") or not ll.get("id"):
        try:
            ll = extraction.best_repeat(con, item, register) or {}
        except Exception:  # noqa: BLE001  a guess is a hint: it never stops the review
            ll = {}
    if not ll.get("id"):
        return None
    if ll.get("state") == "closed":
        return {"reason": "Already done", "why": f"{ll['id']} is already closed", "of": ll["id"]}
    return {"reason": "Duplicate", "why": f"looks like {ll['id']}", "of": ll["id"]}


def closed_guess(con, item):
    """Already done: an update that closes an item the tracker already has closed."""
    if item.get("op") != "update" or item.get("table") not in ("actions", "raid"):
        return None
    if (item.get("changes") or {}).get("status") not in ("Closed", "Cancelled"):
        return None
    row = tracker.fetch(con, item["table"], item.get("id") or "")
    if row is not None and dict(row).get("status") in ("Closed", "Cancelled"):
        return {"reason": "Already done", "why": f"{item['id']} is already {dict(row)['status'].lower()}", "of": item["id"]}
    return None


def guess(con, item, register=None):
    """creaite's guess at why Alan would reject an item, {reason, why, of}, or None. Plain code: the words, the owner, the tracker."""
    if not isinstance(item, dict) or item.get("table") not in ("actions", "raid", "decisions"):
        return None
    v = item.get("values") or {}
    text = str(v.get("description") or v.get("decision") or "")
    if item.get("op") == "new" and THANKS.search(text):
        return {"reason": "Chatter", "why": "a thank-you", "of": None}
    found = repeat_guess(con, item, register) or closed_guess(con, item)
    if found:
        return found
    if no_owner(item) and SCHEDULING.search(text):
        return {"reason": "Chatter", "why": "scheduling, no owner named", "of": None}
    if no_owner(item):
        return {"reason": "Doesn't need tracking", "why": "no owner named", "of": None}
    return None


def pending_guesses(scope=None):
    """[{n, file, ref, reason, why, of}] for each pending item that has a guess, in review order."""
    import extraction
    rows, num = numbers()
    register = extraction.people()
    out = []
    con = tracker.connect()
    try:
        for p, data in proposals():
            for item in data.get("items", []):
                if item.get("applied") or item.get("decision") != "pending":
                    continue
                n = num.get((p.name, item.get("n")))
                if n is None or (scope and project_of(item) != scope):
                    continue
                g = guess(con, item, register)
                if g:
                    out.append({"n": n, "file": p.name, "ref": item.get("n"), **g})
    finally:
        con.close()
    return sorted(out, key=lambda r: r["n"])


def guesses_for(nums):
    """{n: (reason, duplicate_of)} for Use each guess: a Duplicate guess records the item it repeats; no guess, no reason."""
    have = {g["n"]: g for g in pending_guesses()}
    return {n: (have[n]["reason"], have[n]["of"] if have[n]["reason"] == "Duplicate" else None) if n in have else (None, None)
            for n in nums}


def rejected_entry(key):
    """(proposal path, data, ref, item or block) for "<proposal file>#<item number | meeting | report | file_changes>", in staging or
    applied/; exits when it isn't a rejected one."""
    name, _, ref = str(key).partition("#")
    if not re.fullmatch(r"proposed-[\w.-]+\.json", name) or not (ref.isdigit() or ref in ("meeting", "report", "file_changes")):
        sys.exit(f"creaite: {key} isn't a proposal's item.")
    p = next((d / name for d in (paths.STAGING, paths.APPLIED) if (d / name).is_file()), None)
    if p is None:
        sys.exit(f"creaite: {name} isn't in staging.")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not ref.isdigit():
        field = dict((k, f) for k, f, _ in BLOCKS)[ref]
        b = data.get(ref)
        if not b or b.get(field) != "rejected":
            sys.exit(f"creaite: {key} isn't rejected.")
        if b.get("applied"):
            what = "minutes" if ref == "meeting" else "files"
            sys.exit(f"creaite: {key}: rejected {what} were filed; use “undo last apply” instead.")
        return p, data, ref, b
    item = next((i for i in data.get("items", []) if i.get("n") == int(ref)), None)
    if item is None or item.get("decision") != "rejected":
        sys.exit(f"creaite: {key} isn't rejected.")
    return p, data, int(ref), item


def reopen(p, item):
    """Make an applied reject decidable again: marked with the `rejected` row it left (`redecide`), no longer applied."""
    if item.get("applied"):
        item["redecide"] = {"fingerprint": tracker.fingerprint(item), "apply_id": item["applied"]}
        item.pop("applied", None)
        item.pop("result_id", None)


def save_back(p, data):
    """Save a proposal; one in applied/ that has an item decidable again goes back to staging (as undo returns it). Returns its path."""
    if p.parent == paths.APPLIED and not tracker.finished(data):
        dest = paths.STAGING / p.name
        if dest.exists():
            sys.exit(f"creaite: {p.name} is in staging and in applied/; nothing was changed.")
        save(dest, data)
        p.unlink()
        return dest
    save(p, data)
    return p


def was_of(target, ref):
    """What a reject was before a change: its decision, reason and duplicate (for the page's Undo)."""
    if isinstance(ref, str):
        return {"decision": "rejected", "reason": None, "duplicate_of": None}
    return {"decision": target.get("decision"), "reason": target.get("reject_reason"), "duplicate_of": target.get("duplicate_of")}


def print_outcome(verb, done, extra, as_json):
    """Print the outcome of unreject, rereason or approve-instead: a line each, or one JSON line for the live server."""
    if as_json:
        print(json.dumps({"ok": True, "done": done, **extra}, ensure_ascii=False))
        return 0
    print(f"{verb} {len(done)}.")
    for k in extra.get("open") or []:
        print(f"  {k}: back in Review; approve it on its own")
    return 0


def cmd_unreject(keys, as_json=False):
    """Undo rejects: each item back in Review, pending, as it was proposed (BL-315)."""
    done = []
    for key in keys:
        p, data, ref, target = rejected_entry(key)
        done.append({"key": key, "was": was_of(target, ref)})
        if isinstance(ref, str):
            target[dict((k, f) for k, f, _ in BLOCKS)[ref]] = "pending"
        else:
            reopen(p, target)
            target["decision"] = "pending"
            for f in ("reject_reason", "duplicate_of", "rejected_at"):
                target.pop(f, None)
        save_back(p, data)
        debuglog.info("review", f"unrejected {p.name} item {ref}")
    return print_outcome("Back in Review:", done, {}, as_json)


def cmd_rereason(keys, reason=None, duplicate_of=None, as_json=False):
    """Change rejects' reason (and the item a Duplicate repeats); no reason clears it (BL-315)."""
    reason = canonical_reason(reason)
    if reason and (len(reason) > 200 or "\n" in reason):
        print("A reason is one line of at most 200 characters. Nothing was changed.")
        return 2
    if duplicate_of:
        duplicate_of = duplicate_of.upper()
        if not re.fullmatch(DUP_ID, duplicate_of):
            print(f"{duplicate_of} isn't an item ID (like ABC-A-009, ABC-014 or ABC-D-002). Nothing was changed.")
            return 2
        with tracker.connect() as con:
            if not tracker.item_row(con, duplicate_of, ("actions", "raid", "decisions")):
                print(f"There is no {duplicate_of} in the tracker. Nothing was changed.")
                return 2
        reason = reason or "Duplicate"
    done = []
    for key in keys:
        p, data, ref, target = rejected_entry(key)
        if isinstance(ref, str):
            print(f"{key}: minutes, reports and file changes have no reason. Nothing was changed.")
            return 2
        done.append({"key": key, "was": was_of(target, ref)})
        reopen(p, target)
        target["reject_reason"] = reason or None
        if not target["reject_reason"]:
            target.pop("reject_reason")
        if duplicate_of:
            target["duplicate_of"] = duplicate_of
        else:
            target.pop("duplicate_of", None)
        save_back(p, data)
        debuglog.info("review", f"reject reason changed: {p.name} item {ref}")
    return print_outcome("Reason changed:", done, {}, as_json)


def cmd_approve_instead(keys, as_json=False):
    """Undo rejects and approve them in one step; minutes, new decisions, new risks and the rest approved only on their own go back
    to Review pending, to be opened (BL-315). Needs a project, a conflict or an invalid item: back in Review, with why."""
    done, opened = [], []
    for key in keys:
        p, data, ref, target = rejected_entry(key)
        done.append({"key": key, "was": was_of(target, ref)})
        if isinstance(ref, str):
            target[dict((k, f) for k, f, _ in BLOCKS)[ref]] = "pending"
            opened.append(key)
        else:
            reopen(p, target)
            for f in ("reject_reason", "duplicate_of", "rejected_at"):
                target.pop(f, None)
            held = individual_only(target) or (needs_project(target) and "needs a project") \
                or ("conflict" in target.get("flags", []) and "conflict") or ("invalid" in target.get("flags", []) and "invalid")
            target["decision"] = "pending" if held else "approved"
            if held:
                opened.append(key)
        save_back(p, data)
        debuglog.info("review", f"approve instead: {p.name} item {ref}" + (" (back to Review)" if key in opened else ""))
    return print_outcome("Approved instead:", [d for d in done if d["key"] not in opened], {"open": opened}, as_json)


def cmd_rejects(as_json=False, limit=50):
    """The latest rejects, newest first: Activity › What you rejected (quality.recent_rejects)."""
    import quality
    rows = quality.recent_rejects(limit)
    if as_json:
        print(json.dumps(rows, ensure_ascii=False))
        return 0
    for r in rows:
        dup = f" ({r['duplicate_of']})" if r["duplicate_of"] else ""
        print(f"  {r['key']}  {r['text']}  · Rejected · {r['reason'] or 'No reason'}{dup}")
    if not rows:
        print("Nothing has been rejected.")
    return 0


_main_before_rejects = main


def cmd_reasons(as_json=False):
    """The seven reasons, in the menu's order."""
    print(json.dumps(list(REASONS)) if as_json else "\n".join(f"{i}. {r}" for i, r in enumerate(REASONS, 1)))
    return 0


def cmd_guesses(scope=None, as_json=False):
    """creaite's guess per pending item."""
    rows = pending_guesses(scope)
    print(json.dumps(rows, ensure_ascii=False) if as_json else "\n".join(f"  {r['n']}: guess: {r['reason']} ({r['why']})" for r in rows))
    return 0


REJECT_COMMANDS = {
    "reasons": lambda keys, kv, js: cmd_reasons(js),
    "guesses": lambda keys, kv, js: cmd_guesses(keys[0] if keys else None, js),
    "rejects": lambda keys, kv, js: cmd_rejects(js, int(kv.get("limit") or 50)),
    "unreject": lambda keys, kv, js: cmd_unreject(keys, js) if keys else None,
    "approve-instead": lambda keys, kv, js: cmd_approve_instead(keys, js) if keys else None,
    "rereason": lambda keys, kv, js: cmd_rereason(keys, kv.get("reason"), kv.get("duplicate-of"), js) if keys else None,
    "reject": lambda keys, kv, js: cmd_decide(" ".join(keys), "rejected", guesses=guesses_for(parse_numbers(" ".join(keys))))
    if keys and kv.get("guess") is not None else None,                         # Use each guess: "reject 2-6 --guess"
}


def _main_with_rejects(argv):
    cmd, rest = (argv[0], argv[1:]) if argv else ("", [])
    if cmd not in ("reasons", "guesses", "rejects", "unreject", "approve-instead", "rereason", "reject"):   # REJECT_COMMANDS' keys,
        return _main_before_rejects(argv)                                    # named here so the dispatcher declares them (BL-267)
    kv = {a[2:].partition("=")[0]: a[2:].partition("=")[2] for a in rest if a.startswith("--")}
    keys = [a for a in rest if not a.startswith("--")]
    run_ = REJECT_COMMANDS.get(cmd)
    code = run_(keys, kv, "json" in kv) if run_ else None
    return _main_before_rejects(argv) if code is None else code


main = _main_with_rejects
# ===== end BL-315 =====

if __name__ == "__main__":
    sys.exit(debuglog.main("review.py", main, sys.argv[1:]))
