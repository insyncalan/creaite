"""#241 D: a work item's complete history, for the peek's Activity tab (dev/proposals/work-item-history/DESIGN.md).

Read only; a library (no command line). `history_of(item_id)` returns {"id", "events", "exact"}: one event per record change,
newest first, each saying who, via which route (and, from the dashboard, which place), what (the field, its before and after),
when, the source reference, and the undo links: an undo strikes the event it reverses (`struck`, `struck_by`) and is an event
of its own (`undoes`). Created is one event; a label or a link is one event on each item it touches; a status change carries the
closed date it set (`closed`); a history-only reason is the event's `note`.

Where it comes from:
- change_log (one row per field, the before and after already there). The route, place and source are read from the
  item_events row tracker.py writes (`exact`: true) once the guarded diff in dev/proposals/work-item-history/ is applied;
  before that, and for older rows, they are worked out from change_log's `via` and the apply's proposal in
  system/staging/applied/ (`exact`: false). `derive()` is that one rule, used by the diff too.
- Rejections of an update to the item, from the apply's proposal (the item_events row once the diff is in).
- Chases (system/staging/chases.json) and raised again (mentions.jsonl): references only, as those files keep them.

No event carries the text of a message: a proposal's why, evidence, quote, suggestion or reasoning is never read into one, and a
rejection keeps its reason only when it is one of the seven (Alan's own words stay in Review).
"""
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

import paths

ITEM_RE = re.compile(r"[A-Z][A-Z0-9]{2,6}-(?:[ADMPW]-)?\d{3}")
ITEM_TABLES = ("actions", "raid", "decisions", "milestones", "promises", "workstreams")
JOINED = {"links": ("from_item", "links"), "item_labels": ("item_id", "labels")}   # table: (the anchor field, the event's field)
REMOVED = "(removed)"                       # as tracker.REMOVED
REVERT_VIA = "revert:"                      # as tracker.REVERT_VIA (Activity's undo several)
CARD_MARK = "applied_on_card"               # as tracker.CARD_MARK
REJECT_REASONS = ("Not an action", "Duplicate", "Chatter", "Already done", "Wrong project", "Doesn't need tracking",
                  "For another team")       # as tracker.REJECT_REASONS: only these are shown; Alan's own words never are
FIXED = {"dashboard": "dashboard", "cx-edit": "cx-edit", "assistant": "assistant", "excel-import": "excel", "undo": "undo",
         "archive": "archive", "migrate": "migrate"}      # change_log vias that name the route themselves
CREAITE = ("archive", "migrate")            # routes creaite takes by itself; everything else is Alan's doing
PLACES = ("peek", "cell", "bulk", "menu", "board", "today", "card")
REVIEW_PLACES = ("dashboard", "excel", "minutes")          # decided_in: Review in the dashboard, its Excel sheet, a minutes record
TAGS = (("-note", "note"), ("-sweep", "sweep"), ("-archive", "archive"), ("-excel", "excel"))   # proposal file name tags

ROUTE_WORDS = {"dashboard": "the dashboard", "review": "Review", "cx-edit": "Claude Code", "note": "a note's Find updates",
               "assistant": "ask creaite", "excel": "the Excel import", "undo": "Undo", "activity": "Undo in Activity",
               "archive": "the daily archiving", "migrate": "an update", "minutes": "the minutes", "sweep": "the sweep",
               "chase": "Draft email"}
PLACE_WORDS = {"peek": "the peek", "cell": "a cell", "bulk": "the bulk bar", "menu": "the menu", "board": "the Board",
               "today": "Today", "card": "ask creaite's card", "excel": "Review in Excel", "minutes": "the minutes record"}
ORIGIN_WORDS = {"sweep": "from the sweep", "minutes": "from the minutes", "drafts": "from a draft", "report": "from a report"}
LABELS = {"due_date": "Due", "description": "Title", "decision": "Title", "name": "Title", "response_action": "Response",
          "client_visible": "Client-visible", "client_message": "Client messaging", "latest_update": "Latest update",
          "made_by": "Decider", "needed_by": "Needed by", "baseline_date": "Agreed date", "forecast_date": "Forecast",
          "actual_date": "Achieved", "promised_by": "Promised by", "promised_to": "Promised to", "percent_complete": "Progress"}
KINDS = {"client_visible": "cv", "latest_update": "update", "reasoning": "update", "response_action": "update",
         "source": "source", "archived": "archive"}
MADE = ("owner", "due_date", "priority", "type", "status")  # what a created event shows
FOLD = {"closed": "status"}                 # a field set by another one's change rides on that event

ROW_SQL = ("SELECT c.rowid AS rowid, c.at, c.apply_id, c.tbl, c.item_id, c.field, c.old_value, c.new_value, c.op, c.via "
           "FROM change_log c WHERE c.field != 'updated_at' AND ((c.tbl IN ({items}) AND c.item_id = ?) "
           "OR (c.tbl IN ('links', 'item_labels') AND ('|' || c.item_id || '|') LIKE ?)) ORDER BY c.rowid")


def empty(item_id):
    """The answer for an item with no history (or no database)."""
    return {"id": item_id, "events": [], "exact": False}


def history_of(item_id, db=None):
    """{"id", "events", "exact"} for one work item, read only from the vault's tracker.db; empty when there is none."""
    db = Path(db or paths.DB)
    if not isinstance(item_id, str) or not ITEM_RE.fullmatch(item_id) or not db.is_file():
        return empty(item_id)
    with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as con:
        con.row_factory = sqlite3.Row
        return history(con, item_id)


def history(con, item_id):
    """The history of `item_id` from an open connection (rows by name): change_log, rejections, chases and raised again."""
    rows = [dict(r) for r in con.execute(ROW_SQL.format(items=", ".join("?" * len(ITEM_TABLES))),
                                         (*ITEM_TABLES, item_id, f"%|{item_id}|%")) if touches(r, item_id)]
    stored = stored_events(con, item_id, [r["rowid"] for r in rows])
    props = Proposals(con)
    events = from_rows(rows, props, stored) + rejections(con, item_id, props, stored) + chases(item_id) + mentions(item_id)
    link_undos(events)
    events.sort(key=lambda e: e["_sort"], reverse=True)
    exact = bool(stored.get("table")) and all(e["exact"] for e in events)
    return {"id": item_id, "events": [{k: v for k, v in e.items() if not k.startswith("_")} for e in events], "exact": exact}


def touches(r, item_id):
    """True when a change_log row is about the item: its own row, or a link or label row with the item at one end."""
    if r["tbl"] not in JOINED:
        return True
    parts = str(r["item_id"]).split("|")
    return item_id in (parts[:2] if r["tbl"] == "links" else parts[:1])


# ── Stored events (the guarded diff's item_events table) ────────────────────────────────────────────────────────────────

def stored_events(con, item_id, rowids):
    """{"table": whether item_events exists, change rowid: its row, "rejects": [rows]}; just {"table": False} before the diff."""
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'item_events'").fetchone():
        return {"table": False}
    out = {"table": True, "rejects": [], "by_event": {}}
    want = set(rowids)
    for r in con.execute("SELECT * FROM item_events WHERE item_id = ? OR item_id LIKE ? OR item_id LIKE ?",
                         (item_id, f"{item_id}|%", f"%|{item_id}|%")):
        r = dict(r)
        if r["kind"] == "reject":
            out["rejects"].append(r)
        elif r["change"] in want:
            out[r["change"]] = r
        out["by_event"][r["event_id"]] = r["change"]
    return out


# ── The route of a change: stored, or worked out ────────────────────────────────────────────────────────────────────────

def derive(via, data=None, item=None):
    """(route, place, origin, actor) for a change written with change_log `via` from proposal `data` (item `item`), either
    of which may be None. The one rule for today's rows, and the one tracker.py stores once the diff is applied."""
    via = str(via or "")
    data, item = data or {}, item or {}
    if via.startswith(REVERT_VIA):
        return "activity", None, None, "you"
    route = FIXED.get(via)
    if route == "dashboard":
        place = "card" if data.get(CARD_MARK) else data.get("place")
        return route, place if place in PLACES else None, None, "you"
    if route:
        return route, None, None, "creaite" if route in CREAITE else "you"
    return from_proposal(via, data, item)


def from_proposal(via, data, item):
    """The route of a change from a proposal file (its name is the via): a note's Find updates, the archiving, the Excel
    import, or Review, with where it was decided and what made the proposal."""
    run = str(data.get("source_run") or "")
    tag = next((t for s, t in TAGS if s in Path(via).stem), None)
    if run in ("note", "notes") or (not run and tag == "note"):
        return "note", None, None, "you"
    if run == "archive" or (not run and tag == "archive"):
        return "archive", None, None, "creaite"
    if run == "excel-import" or (not run and tag == "excel"):
        return "excel", None, None, "you"
    decided = item.get("decided_in")
    return "review", decided if decided in REVIEW_PLACES else None, origin_of(run, data, tag), "you"


def origin_of(run, data, tag):
    """What made a proposal that went through Review: the sweep, the minutes, an AI draft or a report; None if unknown."""
    if "sweep" in run or tag == "sweep":
        return "sweep"
    if "minutes" in run or data.get("meeting"):
        return "minutes"
    if run == "drafts":
        return "drafts"
    return "report" if "report" in run or data.get("report") else None


def via_words(route, place, origin):
    """How the event came, in words: "the peek", "Review (from the sweep)", "Claude Code"."""
    if route == "dashboard" and place in PLACE_WORDS:
        return PLACE_WORDS[place]
    words = ROUTE_WORDS.get(route, route or "creaite")
    if route == "review":
        words = PLACE_WORDS.get(place, "Review in Claude Code" if place is None else words)
        words = "Review" if words == "Review in Claude Code" and origin else words
    return f"{words} ({ORIGIN_WORDS[origin]})" if origin in ORIGIN_WORDS else words


def one_ref(value):
    """A source reference as kept: one line of at most 300 characters (a path, a mail or chat reference), else None."""
    s = str(value or "").strip()
    return s if s and "\n" not in s and len(s) <= 300 else None


def source_of(item, data, rel):
    """The source reference of a change: the item's own source, the note it came from, else the proposal's file."""
    item, data = item or {}, data or {}
    for cand in (item.get("source"), (item.get("values") or {}).get("source"), (data.get("note") or {}).get("path")):
        if one_ref(cand):
            return one_ref(cand)
    return rel


def route_of(r, props, stored):
    """{route, place, origin, who, via, src, exact} for one change_log row (`r`)."""
    s = stored.get(r["rowid"])
    if s:
        route, place, origin, actor, src, exact = s["route"], s["place"], s.get("origin"), s["actor"], s["src_ref"], True
    else:
        data, item, rel = props.find(r["apply_id"], r["via"], r["tbl"], r["item_id"])
        route, place, origin, actor = derive(r["via"], data, item)
        src, exact = (None if route in ("undo", "activity") else source_of(item, data, rel)), False
    return {"route": route, "place": place, "origin": origin, "who": "creaite" if actor == "creaite" else "You",
            "via": via_words(route, place, origin), "src": src, "exact": exact}


class Proposals:
    """The proposals of each apply, read once from system/staging/applied/ (or staging/, after an undo)."""

    def __init__(self, con):
        self.con, self.applies, self.files = con, {}, {}

    def listed(self, apply_id):
        """[(the proposal's vault path, its data or None)] for an apply."""
        if apply_id not in self.applies:
            row = self.con.execute("SELECT proposals FROM applies WHERE apply_id = ?", (apply_id,)).fetchone()
            try:
                names = json.loads(row["proposals"]) if row and row["proposals"] else []
            except ValueError:
                names = []
            self.applies[apply_id] = [self.load(n) for n in names if isinstance(n, str)]
        return self.applies[apply_id]

    def load(self, rel):
        """(vault path, data) of a proposal by its listed path; data None when it is gone or unreadable."""
        name = Path(rel).name
        if name not in self.files:
            self.files[name] = (rel, None)
            for folder in (paths.APPLIED, paths.STAGING):
                p = folder / name
                if p.is_file():
                    try:
                        self.files[name] = (paths.rel(p), json.loads(p.read_text(encoding="utf-8")))
                    except (OSError, ValueError):
                        self.files[name] = (paths.rel(p), None)    # unreadable: the route is worked out from the via alone
                    break
        return self.files[name]

    def find(self, apply_id, via, tbl, key):
        """(data, item, vault path) of the proposal and item behind a change; item (or all) None when not found."""
        listed = self.listed(apply_id)
        named = [x for x in listed if Path(x[0]).name == via] or listed
        for rel, data in named:
            item = match_item(data, apply_id, tbl, key) if data else None
            if item is not None:
                return data, item, rel
        rel, data = named[0] if len(named) == 1 else (None, None)
        return data, None, rel


def match_item(data, apply_id, tbl, key):
    """The proposal item that made a change to (tbl, key): the one applied in this apply first, else any for it."""
    if tbl == "item_labels":
        tbl, key = None, str(key).split("|")[0]          # labels are set on the item itself
    found = [i for i in data.get("items") or [] if isinstance(i, dict) and item_is(i, tbl, key)]
    return next((i for i in found if i.get("applied") == apply_id), found[0] if found else None)


def item_is(i, tbl, key):
    """True when proposal item `i` is about (tbl, key); tbl None matches any item table."""
    if tbl == "links":
        v = i.get("values") or {}
        return i.get("table") == "links" and (i.get("id") == key or f"{v.get('from_item')}|{v.get('to_item')}" in str(key))
    return (tbl is None or i.get("table") == tbl) and key in (i.get("result_id"), i.get("id"))


# ── change_log rows into events ─────────────────────────────────────────────────────────────────────────────────────────

def from_rows(rows, props, stored):
    """The events of an item's change_log rows: created grouped into one, a link or label row into one, closed and notes
    folded into the change they belong to, undo rows into undo events (linked afterwards, by link_undos)."""
    events, groups, notes = [], {}, []
    for r in rows:
        if r["field"] == "note":
            notes.append(r)
            continue
        if r["op"] == "undo":
            events.append(base(r, props, stored, "undo"))
            continue
        e = grouped(r, groups, props, stored)
        if e is not None:
            events.append(e)
    fold(events, notes)
    return events


def base(r, props, stored, kind):
    """One event for one row, before any grouping: its route, field, before and after."""
    field, before, after = shown_change(r)
    e = {"id": f"c{r['rowid']}", "k": kind, **route_of(r, props, stored), "field": field, "label": label_of(field),
         "before": before, "after": after, "at": (r["at"] or "")[:16], "apply_id": r["apply_id"], "struck": False,
         "struck_by": None, "undoes": None, "_sort": (r["at"] or "", r["rowid"]), "_row": r, "_rowids": {r["rowid"]}}
    s = stored.get(r["rowid"])
    if s and s.get("undoes"):                            # stored by the diff: the change_log row of the event it undoes
        e["_undoes_change"] = stored["by_event"].get(s["undoes"])
    return e


def shown_change(r):
    """(field, before, after) as the event shows them: a link or label row as `links` or `labels`."""
    tbl = r["tbl"]
    if tbl in JOINED:
        anchor, field = JOINED[tbl]
        what = r["item_id"] if tbl == "links" else "|".join(str(r["item_id"]).split("|")[1:])
        gone = r["field"] == REMOVED
        if r["op"] == "undo":
            gone = r["field"] != REMOVED
        return field, (what if gone else None), (None if gone else what)
    if r["field"] == REMOVED:
        return None, None, None                          # a created item removed again (Activity's undo several)
    return r["field"], r["old_value"], r["new_value"]


def label_of(field):
    """A field's name as the peek shows it."""
    return LABELS.get(field, str(field).replace("_", " ").capitalize()) if field else None


def grouped(r, groups, props, stored):
    """The event for a non-undo row, or None when it joins one already made (a created item's other fields)."""
    key = (r["apply_id"], r["tbl"], r["item_id"])
    if r["tbl"] in JOINED and r["op"] == "insert":
        if r["field"] != JOINED[r["tbl"]][0]:
            return None
        return base(r, props, stored, "label" if r["tbl"] == "item_labels" else "link")
    if r["tbl"] in JOINED:
        return base(r, props, stored, "label" if r["tbl"] == "item_labels" else "link")
    if r["op"] == "insert":
        if key in groups:
            g = groups[key]
            g["_rowids"].add(r["rowid"])
            g["made"].update({r["field"]: r["new_value"]} if r["field"] in MADE else {})
            g["src"] = one_ref(r["new_value"]) or g["src"] if r["field"] == "source" else g["src"]
            return None
        e = base(r, props, stored, "create")
        e.update(field=None, label=None, before=None, after=None, made={})
        groups[key] = e
        return e
    return base(r, props, stored, KINDS.get(r["field"], "change"))


def fold(events, notes):
    """Closed rides on the status event of the same apply; a history-only note on the item's first event of that apply."""
    def same(a, b):
        """True when two events are of one apply, one item and one direction (both undo, or neither)."""
        return (a["apply_id"], a["_row"]["item_id"], a["k"] == "undo") == (b["apply_id"], b["_row"]["item_id"], b["k"] == "undo")
    keep = []
    for e in events:
        host = FOLD.get(e["field"]) if e["_row"]["tbl"] in ITEM_TABLES else None
        target = next((x for x in events if host and x["field"] == host and same(x, e)), None)
        if target is not None:
            target["closed"] = {"before": e["before"], "after": e["after"]}
            target["_rowids"] |= e["_rowids"]
        else:
            keep.append(e)
    events[:] = keep
    for n in notes:
        target = next((x for x in events if x["apply_id"] == n["apply_id"] and x["_row"]["item_id"] == n["item_id"]
                       and x["k"] != "undo"), None)
        if target is not None and one_ref(n["new_value"]):
            target["note"] = one_ref(n["new_value"])


# ── Undo links ──────────────────────────────────────────────────────────────────────────────────────────────────────────

def link_undos(events):
    """Each undo event points at the event it reverses (`undoes`), merging an undo of a created item, link or label into one;
    the reversed event is struck (`struck`, `struck_by`) unless its undo is itself undone."""
    by_rowid = {rid: e for e in events for rid in e.get("_rowids", ())}
    reverts = [e for e in events if e.get("route") == "activity" and e.get("_row")]
    for e in reverts:
        e["k"] = "undo"
    keep, merged = [], {}
    for e in events:
        target = undo_target(e, events, by_rowid)
        if target is None:
            keep.append(e)
            continue
        if target["id"] in merged:                      # a created item's fields undone together: one undo event
            continue
        merged[target["id"]] = e
        e["undoes"] = target["id"]
        if target["k"] == "create":
            e.update(field=None, label=None, before=None, after=None)
        keep.append(e)
    events[:] = keep
    strikers = {e["undoes"]: e for e in events if e.get("undoes")}
    for e in events:
        striker = strikers.get(e["id"])
        if striker is not None and not strikers.get(striker["id"]):
            e["struck"], e["struck_by"] = True, striker["id"]


def undo_target(e, events, by_rowid):
    """The event an undo or revert event reverses, or None for an ordinary event (or one whose original is not shown)."""
    r = e.get("_row")
    if not r or e["k"] != "undo":
        return None
    if e.get("_undoes_change") in by_rowid:            # stored by the diff: exact
        return by_rowid[e["_undoes_change"]]
    if r["op"] == "undo":
        return latest_before(events, e, r["apply_id"])
    listed = {int(x) for x in str(r["via"])[len(REVERT_VIA):].split(",") if x.strip().isdigit()}
    cands = [by_rowid[x] for x in sorted(listed) if x in by_rowid]
    return next((x for x in cands if same_change(x, e)), None)


def latest_before(events, e, apply_id):
    """The newest non-undo event of the same apply and change as undo event `e`."""
    found = [x for x in events if x["k"] != "undo" and x["apply_id"] == apply_id and same_change(x, e)
             and x["_sort"][1] < e["_sort"][1]]
    return found[-1] if found else None


def same_change(x, e):
    """True when event x is the change undo event e reverses: same table and key, and the same field (any field of a
    created item, a link or a label)."""
    a, b = x.get("_row"), e.get("_row")
    if not a or not b or (a["tbl"], a["item_id"]) != (b["tbl"], b["item_id"]):
        return False
    return x["k"] in ("create", "link", "label") or x["field"] == e["field"] or (x.get("closed") and b["field"] == "closed")


# ── Rejections, chases and raised again ─────────────────────────────────────────────────────────────────────────────────

def rejections(con, item_id, props, stored):
    """A rejected update to the item, one event each: from item_events once the diff is in, else from the apply's proposal."""
    out = stored_rejections(con, stored)
    covered = {e["apply_id"] for e in out}
    for a in con.execute("SELECT c.apply_id, min(c.at) AS at FROM change_log c WHERE c.tbl = 'rejected' "
                         "GROUP BY c.apply_id ORDER BY c.apply_id"):
        if a["apply_id"] not in covered:
            out += derived_rejections(item_id, a["apply_id"], a["at"], props)
    return out


def stored_rejections(con, stored):
    """The rejection events item_events holds, with the reason from `rejected` (only the seven are shown) and struck when
    the apply was undone (the item went back to Review)."""
    undone = {r[0] for r in con.execute("SELECT apply_id FROM applies WHERE undone_at IS NOT NULL")}
    out = []
    for r in stored.get("rejects") or []:
        got = con.execute("SELECT j.reason FROM change_log c JOIN rejected j ON j.fingerprint = c.item_id WHERE c.rowid = ?",
                          (r["change"],)).fetchone()
        e = reject_event(r["event_id"], r["at"], r["apply_id"], {**r, "reason": got[0] if got else None})
        e["struck"] = r["apply_id"] in undone
        out.append(e)
    return out


def derived_rejections(item_id, apply_id, at, props):
    """The rejections of an update to the item in one apply, from its proposals (only while they are still applied)."""
    out = []
    for rel, data in props.listed(apply_id):
        for i in (data or {}).get("items") or []:
            if isinstance(i, dict) and i.get("decision") == "rejected" and i.get("id") == item_id and i.get("applied") == apply_id:
                out.append(reject_event(f"{apply_id}-{i.get('n')}", at, apply_id, None, i, data, rel))
    return out


def reject_event(ident, at, apply_id, row, item=None, data=None, rel=None):
    """One rejection event: Review, the reason when it is one of the seven, the source reference; never the item's text."""
    if row is not None:
        route, place, origin, src, exact = row["route"], row["place"], row.get("origin"), row["src_ref"], True
        reason = row.get("reason")
    else:
        route, place, origin, _ = derive(Path(rel or "").name, data, item)
        src, exact, reason = source_of(item, data, rel), False, item.get("reject_reason")
    return {"id": f"r{ident}", "k": "reject", "who": "You", "route": route, "place": place, "origin": origin,
            "via": via_words(route, place, origin), "field": None, "label": None, "before": None, "after": None,
            "at": (at or "")[:16], "apply_id": apply_id, "src": src, "struck": False, "struck_by": None, "undoes": None,
            "exact": exact, "note": reason if reason in REJECT_REASONS else None, "_sort": (at or "", 0)}


def chases(item_id):
    """The chases Alan says he sent for the item (system/staging/chases.json: IDs, a date and the mode)."""
    try:
        data = json.loads((paths.STAGING / "chases.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for n, c in enumerate(data.get("chases") or [] if isinstance(data, dict) else []):
        if isinstance(c, dict) and item_id in (c.get("ids") or []) and isinstance(c.get("date"), str):
            out.append(outside_event(f"h{n}", "chase", c["date"], "chase", "You", None, mode=c.get("mode")))
    return out


def mentions(item_id):
    """The meetings, sweeps and notes that raised the item again (system/staging/mentions.jsonl: date, ID, run, source)."""
    try:
        lines = paths.MENTIONS.read_text(encoding="utf-8").splitlines() if paths.MENTIONS.is_file() else []
    except OSError:
        lines = []
    out = []
    for n, line in enumerate(lines):
        try:
            m = json.loads(line)
        except ValueError:
            continue                                      # a damaged line is skipped, as drafts.mentions_of does
        if isinstance(m, dict) and m.get("id") == item_id and isinstance(m.get("at"), str):
            run = str(m.get("run") or "")
            route = "minutes" if "minutes" in run else "sweep" if "sweep" in run else "note" if run == "note" else "sweep"
            out.append(outside_event(f"m{n}", "again", m["at"], route, "creaite", one_ref(m.get("source"))))
    return out


def outside_event(ident, kind, at, route, who, src, mode=None):
    """An event kept outside change_log (a chase, a raised again): references only."""
    e = {"id": ident, "k": kind, "who": who, "route": route, "place": None, "origin": None, "via": ROUTE_WORDS.get(route, route),
         "field": None, "label": None, "before": None, "after": None, "at": at[:16], "apply_id": None, "src": src,
         "struck": False, "struck_by": None, "undoes": None, "exact": True, "_sort": (at, 0)}
    if mode:
        e["mode"] = mode
    return e
