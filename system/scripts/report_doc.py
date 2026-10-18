"""The weekly and client reports as creaite documents (v2.1.0 P3; BL-335, BL-336). Standard library only. A library: no command line.

report.py's weekly_data and client_data (unchanged: their JSON is pinned) feed the creaite-data model (dev/sprints/v210-contract.md):
  weekly_doc   a week's internal report: every section of BL-335, from the tracker, laid out as the project's layout says;
  client_doc   a client's view of the week (BL-336): client-safe facts only, locked to the latest approved internal week;
  layout_for / remember_layout   the layout per project (weekly) and per client: section order, hidden sections, renamed
               headings, At a glance, logos, the milestone list and the row rules, kept in settings.json `report_layouts`;
  logos        the report logos, in the git-ignored system/branding/logos/ (firm.<ext>, <CODE>-client.<ext>, <CODE>-partner.<ext>);
  baseline     the approved internal week a client report locks to; client_ready says whether it may be approved or exported;
  stage_weekly / stage_client   Approve's one proposal (the week's update and health, the Current state, filing the report),
               which the live server applies with tracker.py apply, the one writer, so Undo works as it always has.
The Word drafts (report.py weekly_stage, client_stage) still work for the old flow until the docs step retires them.
"""
import copy
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import creaite_doc  # noqa: E402

KINDS = ("weekly", "client")
SECTIONS = {   # kind: (id, type, creaite's own heading), in the default order
    "weekly": (("header", "header", "Weekly report"), ("health", "health", "Health"), ("glance", "figures", "At a glance"),
               ("summary", "text", "Summary"), ("milestones", "timeline", "Milestones"),
               ("asks", "table", "What we need from people"), ("this_week", "text", "This week"),
               ("next_week", "text", "Next week"), ("decisions", "table", "Decisions made this week"),
               ("risks", "table", "Risks and issues"), ("overdue", "table", "Overdue actions"),
               ("current_state", "panes", "Current state")),
    "client": (("header", "header", "Client report"), ("health", "health", "Health"), ("glance", "figures", "At a glance"),
               ("summary", "text", "Summary"), ("milestones", "timeline", "Milestones"),
               ("asks", "table", "What we need from you"), ("this_week", "text", "Progress"),
               ("next_week", "text", "Next steps"), ("decisions", "table", "Decisions"),
               ("risks", "table", "Risks and issues"), ("overdue", "table", "Overdue actions"),
               ("current_state", "panes", "Current state")),
}
GLANCE = {"weekly": ("next_milestone", "overdue", "high_risks", "decisions_needed"),
          "client": ("next_milestone", "client_asks", "watch")}
LOGO_KINDS = ("firm", "client", "partner")          # the firm's always first
LOGO_EXT = (".png", ".jpg", ".jpeg", ".svg")
DEFAULT_ROWS = {"risks": {"top": 5}}
LAYOUT_KEYS = ("order", "hidden", "headings", "glance", "logos", "milestones", "rows")
CODE = re.compile(r"[A-Z][A-Z0-9]{2,6}$")
TITLE = {"actions": "description", "raid": "description", "decisions": "decision", "milestones": "name", "promises": "description"}
CLIENT_STATUS = {"Open": "In progress", "Delayed": "Delayed", "Closed": "Complete", "Cancelled": "Cancelled"}


class ReportError(ValueError):
    """Why a report can't be drafted, saved or approved, as a plain sentence for Alan."""


def shown(iso):
    """A stored date as DD-MM-YYYY ('' for none)."""
    import tracker
    return tracker.shown(iso) or ""


def friday(day=None):
    """The week ending (Friday) of `day` (YYYY-MM-DD), or of today on creaite's clock."""
    import report
    return report.friday_of(date.fromisoformat(day) if day else report.today()).isoformat()


# ── Layouts (per project, per client) ────────────────────────────────────────

def default_layout(kind):
    """creaite's own layout for a weekly or client report."""
    return {"order": [s[0] for s in SECTIONS[kind]], "hidden": [], "headings": {}, "glance": list(GLANCE[kind]),
            "logos": list(LOGO_KINDS), "milestones": None, "rows": copy.deepcopy(DEFAULT_ROWS)}


def _ids(kind):
    """The section ids of a kind, in creaite's order."""
    return [s[0] for s in SECTIONS[kind]]


def _rows_rules(kind, rules, base):
    """Row rules ({section id: {"top": n}}) from what was sent; the default when there is none."""
    if not isinstance(rules, dict):
        return base
    out = {}
    for sid, rule in rules.items():
        top = rule.get("top") if isinstance(rule, dict) else None
        if sid in _ids(kind) and isinstance(top, int) and not isinstance(top, bool) and 0 < top <= 500:
            out[sid] = {"top": top}
    return out


def normal_layout(kind, layout):
    """A whole layout from what was saved or sent: unknown sections, figures and logos dropped, missing keys defaulted, every
    section in the order (one the layout doesn't name goes where creaite puts it)."""
    base, lay, ids = default_layout(kind), layout if isinstance(layout, dict) else {}, _ids(kind)
    order = [i for i in dict.fromkeys(lay.get("order") or []) if i in ids]
    for i in ids:
        if i not in order:
            order.insert(min(ids.index(i), len(order)), i)
    return {"order": order, "hidden": [i for i in ids if i in (lay.get("hidden") or [])],
            "headings": {k: str(v).strip()[:120] for k, v in (lay.get("headings") or {}).items() if k in ids and str(v).strip()},
            **_lists(kind, lay, base), "rows": _rows_rules(kind, lay.get("rows"), base["rows"])}


def _lists(kind, lay, base):
    """At a glance's figures, the logos and the milestone list from a layout; each defaulted when it isn't a list."""
    glance, logos_, miles = lay.get("glance"), lay.get("logos"), lay.get("milestones")
    return {"glance": [g for g in dict.fromkeys(glance) if g in GLANCE[kind]] if isinstance(glance, list) else base["glance"],
            "logos": [x for x in LOGO_KINDS if x in logos_] if isinstance(logos_, list) else base["logos"],
            "milestones": [str(m) for m in miles] if isinstance(miles, list) else None}


def stored_layouts():
    """settings.json `report_layouts`: {CODE: {"weekly": layout, "clients": {client: layout}}}."""
    return paths.load_settings().get("report_layouts") or {}


def layout_for(code, kind, client=None):
    """The layout a project's next weekly report (or a client's next client report) starts from."""
    mine = stored_layouts().get(code) or {}
    saved = mine.get("weekly") if kind == "weekly" else (mine.get("clients") or {}).get(client or "")
    return normal_layout(kind, saved)


def remember_layout(code, kind, layout, client=None):
    """Keep a layout as the project's (weekly) or the client's: settings.json `report_layouts.<CODE>`, written as the dashboard's
    settings are (a backup and a settings-log line, settings_catalogue.save). Returns whether it changed. A row hidden by its eye
    is that week's only, so it is never part of the layout."""
    import settings_catalogue
    if kind not in KINDS or not CODE.match(code or ""):
        raise ReportError("A layout needs a weekly or client report and a project code.")
    lay = normal_layout(kind, layout)
    mine = copy.deepcopy(stored_layouts().get(code) or {})
    if kind == "weekly":
        if mine.get("weekly") == lay:
            return False
        mine["weekly"] = lay
    else:
        clients = mine.setdefault("clients", {})
        if clients.get(client or "") == lay:
            return False
        clients[client or ""] = lay
    settings_catalogue.save({f"report_layouts.{code}": mine})
    return True


# ── Logos (system/branding/logos/, kept out of git) ──────────────────────────

def logo_file(code, kind):
    """The logo file for the firm, or a project's client or partner logo, or None when none is set."""
    stem = "firm" if kind == "firm" else f"{code}-{kind}"
    return next((paths.REPORT_LOGOS / f"{stem}{e}" for e in LOGO_EXT if (paths.REPORT_LOGOS / f"{stem}{e}").is_file()), None)


def logos(code, wanted=LOGO_KINDS):
    """[{kind, path}] of the logos set for the project, in `wanted` (the layout's), the firm's first."""
    found = [(k, logo_file(code, k)) for k in LOGO_KINDS if k in wanted]
    return [{"kind": k, "path": paths.rel(f)} for k, f in found if f]


# ── Arranging the sections as the layout says ───────────────────────────────

def _figures_in_order(figures, glance):
    """At a glance's figures in the layout's order; a figure the layout leaves out is hidden."""
    by_key = {f["key"]: f for f in figures}
    first = [dict(by_key[g], shown=True) for g in glance if g in by_key]
    return first + [dict(f, shown=False) for f in figures if f["key"] not in glance]


def _top_rows(rows, top):
    """Rows with only the first `top` shown (the rest keep their eye closed, so Alan can show one)."""
    out, n = [], 0
    for r in rows:
        on = r.get("shown", True) and n < top
        n += 1 if on else 0
        out.append(dict(r, shown=on))
    return out


def arrange(kind, built, layout):
    """The built sections in the layout's order, hidden and renamed as it says, At a glance and the row rules applied."""
    defaults = {sid: (stype, heading) for sid, stype, heading in SECTIONS[kind]}
    out = []
    for sid in layout["order"]:
        if sid not in built:
            continue
        stype, heading = defaults[sid]
        s = {"id": sid, "type": stype, "heading": layout["headings"].get(sid, heading), "default_heading": heading,
             "hidden": sid in layout["hidden"], **built[sid]}
        if stype == "figures":
            s["figures"] = _figures_in_order(s.get("figures") or [], layout["glance"])
        top = (layout["rows"].get(sid) or {}).get("top")
        if top and s.get("rows"):
            s["rows"] = _top_rows(s["rows"], top)
        out.append(s)
    return out


# ── Items as they stood ──────────────────────────────────────────────────────

def item(con, ref):
    """An item's tracker row as it stands, with its table and a title (an internal report's `items` entry), or None."""
    import tracker
    table = tracker.item_table(ref)
    if table not in TITLE:
        return None
    row = con.execute(f"SELECT * FROM {table} WHERE id = ?", (ref,)).fetchone()
    if row is None:
        return None
    row = dict(row)
    extra = {"due_date": row.get("forecast_date") or row.get("baseline_date")} if table == "milestones" else {}
    return {**row, "table": table, "title": row.get(TITLE[table]) or "", **extra}


def items_of(con, sections):
    """{ref: item} for every item a section's rows, tags or milestone lists name."""
    refs = []
    for s in sections:
        refs += [r.get("ref") for r in s.get("rows") or []] + [t.get("ref") for t in s.get("tags") or []]
        refs += list((s.get("data") or {}).get("timeline") or [])
    found = {r: item(con, r) for r in dict.fromkeys(x for x in refs if x)}
    return {k: v for k, v in found.items() if v}


def bullets(lines):
    """Lines as a Markdown list ('' for none)."""
    return "\n".join(f"- {str(x).strip()}" for x in lines if str(x).strip())


def paras(x):
    """A list or text as Markdown paragraphs."""
    if isinstance(x, list):
        return "\n\n".join(str(p).strip() for p in x if str(p).strip())
    return str(x or "").strip()


def plain(md):
    """Markdown as one line of plain words (for the health reason and the summary row)."""
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", str(md or ""))
    return re.sub(r"\s+", " ", re.sub(r"[*_`#>]+", "", t)).strip()


def source_label(source):
    """An item's source as a short label: the file's name, else the text."""
    first = str(source or "").split(" — ")[0].strip()
    return Path(first).stem if "/" in first else first


# ── The weekly report ────────────────────────────────────────────────────────

class _Weekly:
    """What every weekly section shares: the week's facts (report.weekly_data), the project, the spec's words."""

    def __init__(self, code, week_ending, spec):
        import report
        import tracker
        self.code, self.spec = code, spec or {}
        self.data = report.weekly_data(code, week_ending)
        self.con = tracker.connect()
        self.p, self.folder, self.mem = report.project(self.con, code)
        self.fri = self.data["week_ending"]

    def rows(self, sql, *args):
        """A query's rows as dicts."""
        return [dict(r) for r in self.con.execute(sql, args)]


def _w_header(w, lay):
    return {"text": "", "data": {"label": "Weekly report · Internal", "week_ending": w.fri, "client": w.mem.get("client") or "",
                                 "logos": logos(w.code, lay["logos"])}}


def _w_health(w, lay):
    d = w.data
    trend = list(reversed(w.rows("SELECT week_ending, health FROM updates WHERE project = ? AND week_ending <= ? "
                                 "ORDER BY week_ending DESC LIMIT 6", w.code, w.fri)))
    last = d.get("last_update") or {}
    return {"text": paras(w.spec.get("health_reason", d.get("health_reason") or "")),
            "data": {"flag": w.spec.get("health") or d.get("health") or d["suggested_health"], "suggested": d["suggested_health"],
                     "reasons": d["reasons"], "trend": [{"date": t["week_ending"], "flag": t["health"]} for t in trend],
                     "last_week": {"flag": last.get("health"), "why": last.get("summary") or "", "date": last.get("week_ending")}
                     if last else None}}


def _w_glance(w, lay):
    d = w.data
    nxt = next((m for m in d["milestones"] if m["status"] == "Planned"), None)
    note = (shown(nxt["forecast"]) + (f", moved {nxt['slip_days']} days" if nxt["slip_days"] > 0 else "")) if nxt else ""
    high = [r for r in w.rows("SELECT priority FROM raid WHERE project = ? AND status = 'Open' AND type IN ('Risk', 'Issue')",
                              w.code) if r["priority"] in ("Urgent", "High")]
    figures = [("next_milestone", "Next milestone", nxt["name"] if nxt else "None planned", note),
               ("overdue", "Overdue actions", str(len(d["overdue"])), ""),
               ("high_risks", "High risks open", str(len(high)), ""),
               ("decisions_needed", "Decisions needed", str(len(d["decisions_needed"])), "")]
    return {"figures": [{"key": k, "label": lab, "value": v, "note": n, "shown": True} for k, lab, v, n in figures]}


def _w_milestones(w, lay):
    refs = [m["id"] for m in w.data["milestones"]]
    listed = [r for r in lay["milestones"] if r in refs] if lay["milestones"] is not None else refs
    return {"text": "", "data": {"timeline": refs, "milestones": listed}}


def _w_asks(w, lay):
    rows = [{"ref": d["id"], "source": "decision needed",
             "cells": {"ask": d["text"], "from": d["by"] or "Not asked yet", "by": shown(d["needed_by"]),
                       "why": "A decision is needed" + (f" ({d['overdue_days']} days overdue)" if d["overdue_days"] else "")}}
            for d in w.data["decisions_needed"]]
    rows += [{"ref": p["id"], "source": "promise",
              "cells": {"ask": p["description"], "from": p["promised_by"], "by": shown(p.get("due_date")),
                        "why": f"Promised to {p['promised_to']}"
                               + (f"; {p['overdue_days']} days overdue" if p.get("overdue_days") else "")}}
             for p in (w.data.get("promises") or {}).get("waiting_on", [])]
    return {"columns": [{"key": "ask", "label": "Ask"}, {"key": "from", "label": "From"}, {"key": "by", "label": "By"},
                        {"key": "why", "label": "Why it matters"}],
            "rows": [dict(r, shown=True) for r in rows]}


def _w_this_week(w, lay):
    closed = [ln.split(" ", 1) for ln in w.data["actions_closed"]]
    lines = list(w.spec.get("progress") or []) or [f"Closed: {t}" for _i, t in closed]
    flow = [f"Flow: {w.data['flow']}."] if w.data.get("flow") else []
    return {"text": bullets(flow + lines), "tags": [{"ref": i, "text": t} for i, t in closed if t]}


def _w_next_week(w, lay):
    owe = (w.data.get("promises") or {}).get("you_owe", [])
    lines = [f"Promised: {p['line']}." for p in owe] + list(w.spec.get("next_week") or [])
    return {"text": bullets(lines), "tags": [{"ref": p["id"], "text": p["description"]} for p in owe]}


def _w_decisions(w, lay):
    rows = []
    for d in w.data["decisions"]:
        src = (item(w.con, d["id"]) or {}).get("source")
        rows.append({"ref": d["id"], "shown": True, "cells": {"decision": d["text"], "by": d["by"] or "Not recorded",
                                                               "date": shown(d["date"]), "source": source_label(src)}})
    return {"columns": [{"key": "decision", "label": "Decision"}, {"key": "by", "label": "Made by"},
                        {"key": "date", "label": "Date"}, {"key": "source", "label": "Source"}], "rows": rows}


def _w_risks(w, lay):
    import report
    raid = w.rows("SELECT * FROM raid WHERE project = ? AND status = 'Open' AND type IN ('Risk', 'Issue')", w.code)
    raid.sort(key=lambda r: report.ORDER.index(r["priority"] or "Low"))
    return {"columns": [{"key": "id", "label": "ID"}, {"key": "risk", "label": "Risk or issue"},
                        {"key": "priority", "label": "Priority"}, {"key": "owner", "label": "Owner"}],
            "rows": [{"ref": r["id"], "shown": True, "cells": {"id": r["id"], "risk": f"{r['type']}: {r['description']}",
                                                               "priority": r["priority"] or "", "owner": r["owner"]}} for r in raid]}


def _w_overdue(w, lay):
    return {"columns": [{"key": "id", "label": "ID"}, {"key": "action", "label": "Action"}, {"key": "owner", "label": "Owner"},
                        {"key": "due", "label": "Due"}],
            "rows": [{"ref": a["id"], "shown": True, "cells": {"id": a["id"], "action": a["text"], "owner": a["owner"],
                                                               "due": shown(a["due"])}} for a in w.data["overdue"]]}


def _w_current(w, lay):
    import docx_tools
    left, right = docx_tools.split_panes(paras(w.spec.get("current_state")) or w.data.get("current_state") or "")
    return {"panes": [{"title": "", "text": left}] + ([{"title": "", "text": right}] if right else [])}


WEEKLY_BUILDERS = {"header": _w_header, "health": _w_health, "glance": _w_glance,
                   "summary": lambda w, lay: {"text": paras(w.spec.get("summary"))},
                   "milestones": _w_milestones, "asks": _w_asks, "this_week": _w_this_week, "next_week": _w_next_week,
                   "decisions": _w_decisions, "risks": _w_risks, "overdue": _w_overdue, "current_state": _w_current}


def weekly_doc(code, week_ending=None, spec=None, layout=None):
    """A week's internal report as a creaite document (version 0, a draft; nothing written). `spec` may carry cx-weekly-report's
    words (summary, progress, next_week, current_state, health, health_reason, key_changes); `layout` overrides the project's."""
    w = _Weekly(code, week_ending, spec)
    lay = normal_layout("weekly", layout if layout is not None else layout_for(code, "weekly"))
    built = {sid: f(w, lay) for sid, f in WEEKLY_BUILDERS.items()}
    sections = arrange("weekly", built, lay)
    items = items_of(w.con, sections)
    d = w.data
    meta = {"week_start": d["week_start"], "suggested_health": d["suggested_health"], "reasons": d["reasons"],
            "flow": d.get("flow") or "", "quiet_week": d["quiet_week"], "blocked": d["blocked"],
            "key_changes": (spec or {}).get("key_changes", "")}
    return creaite_doc.new("weekly", code, "Weekly report", w.fri, sections, layout=lay, items=items, meta=meta,
                           sources=[{"ref": "tracker", "label": f"creaite tracker, week ending {shown(w.fri)}"}])


# ── The client's facts, and the lock to the approved internal week ──────────

def _client_item(table, r, client):
    """The client-safe fields of one item (its client wording, never its internal wording or notes)."""
    import report
    import tracker
    if table == "actions":
        return {"table": table, "id": r["id"], "title": report.message_parts(r["client_message"]).get(report.HEADINGS[0]) or "",
                "owner": r["owner"], "due_date": r["due_date"], "status": CLIENT_STATUS[r["status"]], "closed": r["closed"],
                "client_owned": report._is_client_owner(r["owner"], client)}
    if table == "decisions":
        return {"table": table, "id": r["id"], "title": (r["client_message"] or "").strip(), "status": r["status"],
                "date": r["date"], "needed_by": r["needed_by"], "made_by": r["made_by"]}
    if table == "raid":
        return {"table": table, "id": r["id"], "type": r["type"], "title": report.client_text(r["client_message"]),
                "status": r["status"]}
    return {"table": table, "id": r["id"], "title": r["name"], "status": r["status"], "state": tracker.MS_CLIENT_WORD[r["state"]],
            "due_date": r.get("forecast_date") or r.get("baseline_date"), "shown_date": report.client_date(r)}


def client_facts(code):
    """The project's client-safe facts as they stand: health's flag, and every client-visible milestone, action, decision and open
    risk or issue with complete client wording that no label keeps out (client_leak.item_problem). Kept in an approved internal
    report (meta.client_facts) so the week's client reports lock to it (BL-336)."""
    import client_leak
    import report
    import tracker
    con = tracker.connect()
    p, _folder, mem = report.project(con, code)
    client = mem.get("client") or ""
    blocking = client_leak.blocking_labels(con)
    sql = {"actions": "SELECT * FROM actions WHERE project = ? AND client_visible = 1 AND status != 'Cancelled' ORDER BY id",
           "decisions": "SELECT * FROM decisions WHERE project = ? AND client_visible = 1 AND status IN ('Made', 'Pending') "
                        "ORDER BY COALESCE(date, needed_by, '9999'), id",
           "raid": "SELECT * FROM raid WHERE project = ? AND client_visible = 1 AND status = 'Open' AND type IN ('Risk', 'Issue') "
                   "ORDER BY id"}
    out = {"on": report.today().isoformat(), "client": client, "health": p["health"]}
    for table, q in sql.items():
        rows = [dict(r) for r in con.execute(q, (code,))]
        out[table] = [_client_item(table, r, client) for r in rows if tracker.message_complete(table, r["client_message"])
                      and not client_leak.item_problem(con, r["id"], blocking)]
    ms = tracker.client_milestones(report.milestones(con, code))
    out["milestones"] = [_client_item("milestones", m, client) for m in ms if not client_leak.item_problem(con, m["id"], blocking)]
    return out


def approved_weeks(code):
    """[(week ending, stored path, version)] of the project's filed, approved internal weekly reports, newest first."""
    folder = paths.folder(code, "weekly_reports")
    out = []
    for f in sorted(folder.glob("* Weekly report*.html")) if folder.is_dir() else []:
        try:
            doc = creaite_doc.read(f)
        except creaite_doc.DocError:
            continue        # an .html file that isn't a creaite report: not a week
        if doc.get("kind") == "weekly" and doc.get("project") == code and doc.get("state") == "approved":
            out.append((doc["date"], paths.rel(f), int(doc.get("version") or 0)))
    return sorted(out, reverse=True)


def pickable(doc):
    """Add from the tracker (#217, #221): the open items Alan may add to this report's tables, per section, not already in it.
    Read only: nothing is written, and the tracker is never changed by adding. Each candidate is {ref, title, meta, row, item}: the
    row is what the section would hold (marked `source: "added"`), the item what the document keeps of it. A weekly report may
    take any open RAID item (an assumption or a dependency too) or action and any decision of the project; a client report only the client-safe facts (client-visible,
    complete client wording, no label that keeps it out: client_facts), so a private item is never even offered. Actions that are not
    overdue can be picked too (they go under Overdue actions as 'not due yet')."""
    kind, code = doc.get("kind"), str(doc.get("project") or "")
    if kind not in KINDS or not CODE.match(code):
        raise ReportError("Say which report: weekly or client, and the project's code.")
    have = {s["id"]: {r.get("ref") for r in s.get("rows") or []} for s in doc.get("sections") or [] if s.get("type") == "table"}
    out = {"risks": [], "overdue": [], "decisions": []}
    if kind == "client":
        facts = client_facts(code)
        for r in facts["raid"]:
            out["risks"].append({"ref": r["id"], "title": r["title"], "meta": r["type"], "item": r,
                                 "row": {"ref": r["id"], "shown": True, "source": "added", "cells": {"type": r["type"], "risk": r["title"]}}})
        for a in facts["actions"]:
            if a["status"] in ("In progress", "Delayed"):
                out["overdue"].append({"ref": a["id"], "title": a["title"], "meta": " · ".join(x for x in (a["owner"], shown(a["due_date"])) if x),
                                       "item": a, "row": {"ref": a["id"], "shown": True, "source": "added",
                                                          "cells": {"action": a["title"], "owner": a["owner"], "due": shown(a["due_date"])}}})
        for d in facts["decisions"]:
            when = shown(d["date"]) if d["status"] == "Made" else ("Needed by " + shown(d["needed_by"]) if d.get("needed_by") else "Needed")
            out["decisions"].append({"ref": d["id"], "title": d["title"], "meta": when, "item": d, "row": {
                "ref": d["id"], "shown": True, "source": "added",
                "cells": {"decision": d["title"] if d["status"] == "Made" else f"Decision needed: {d['title']}", "date": when}}})
    else:
        import report
        import tracker
        with tracker.connect() as con:
            def one(ref):
                return item(con, ref)
            for r in con.execute("SELECT * FROM raid WHERE project = ? AND status = 'Open'", (code,)).fetchall():
                r = dict(r)
                out["risks"].append({"ref": r["id"], "title": f"{r['type']}: {r['description']}", "meta": " · ".join(x for x in (r["priority"], r["owner"]) if x),
                                     "_p": report.ORDER.index(r["priority"] or "Low"), "item": one(r["id"]), "row": {
                                         "ref": r["id"], "shown": True, "source": "added",
                                         "cells": {"id": r["id"], "risk": f"{r['type']}: {r['description']}", "priority": r["priority"] or "", "owner": r["owner"]}}})
            for a in con.execute("SELECT * FROM actions WHERE project = ? AND status IN ('Open', 'Delayed') "
                                 "ORDER BY COALESCE(due_date, '9999'), id", (code,)).fetchall():
                a = dict(a)
                due = shown(a["due_date"])
                out["overdue"].append({"ref": a["id"], "title": a["description"], "meta": " · ".join(x for x in (a["owner"], due) if x),
                                       "item": one(a["id"]), "row": {"ref": a["id"], "shown": True, "source": "added", "cells": {
                                           "id": a["id"], "action": a["description"], "owner": a["owner"], "due": due or "not due yet"}}})
            for d in con.execute("SELECT * FROM decisions WHERE project = ? AND status IN ('Made', 'Pending') "
                                 "ORDER BY COALESCE(date, needed_by, '0') DESC, id DESC LIMIT 60", (code,)).fetchall():
                d = dict(d)
                src = (one(d["id"]) or {}).get("source")
                out["decisions"].append({"ref": d["id"], "title": d["decision"], "meta": " · ".join(x for x in (d["made_by"], shown(d["date"])) if x),
                                         "item": one(d["id"]), "row": {"ref": d["id"], "shown": True, "source": "added", "cells": {
                                             "decision": d["decision"], "by": d["made_by"] or "Not recorded", "date": shown(d["date"]),
                                             "source": source_label(src)}}})
        out["risks"].sort(key=lambda c: c.pop("_p"))
    return {sid: [c for c in found if c["ref"] not in have.get(sid, set())] for sid, found in out.items() if sid in have}


def baseline(code, on):
    """The approved internal week a client report dated `on` locks to: the latest approved week ending on or before it, as
    {date, path, version}, or None (BL-336: a fortnightly or monthly client uses the latest approved week)."""
    hit = next((w for w in approved_weeks(code) if w[0] <= on), None)
    return {"date": hit[0], "path": hit[1], "version": hit[2]} if hit else None


def client_ready(doc):
    """(True, '') when a client report may be approved or exported: that week's internal report is approved; else (False, why)."""
    base = baseline(doc["project"], doc["date"])
    if not base:
        return False, (f"Approve the internal weekly report for week ending {shown(doc['date'])} first: a client report is "
                       "approved or exported only after it.")
    return True, ""


def _client_period(code, fri, spec):
    """(start, end) of the client report's period: the spec's start, else the day after the last client report, else the week."""
    import report
    _last, start = report._client_period(code, (spec or {}).get("period_start"))
    return start or (date.fromisoformat(fri) - timedelta(days=4)).isoformat(), fri


# ── The client report ────────────────────────────────────────────────────────

class _Client:
    """What every client section shares: the facts (locked or live), the period, the spec's words."""

    def __init__(self, code, fri, client, spec):
        self.code, self.fri, self.spec = code, fri, spec or {}
        self.base = baseline(code, fri)
        locked = creaite_doc.read(self.base["path"]).get("meta", {}).get("client_facts") if self.base else None
        self.locked = bool(locked)
        self.facts = locked or client_facts(code)
        self.client = client or self.facts.get("client") or ""
        self.start, self.end = _client_period(code, fri, spec)

    def of(self, table):
        """The facts' items of one table."""
        return self.facts.get(table) or []


def _c_header(c, lay):
    return {"text": "", "data": {"label": "Client report", "client": c.client, "period_start": c.start, "period_end": c.end,
                                 "facts_week": c.base["date"] if c.base else None, "logos": logos(c.code, lay["logos"])}}


def _c_glance(c, lay):
    nxt = next((m for m in c.of("milestones") if m["status"] == "Planned"), None)
    asks = [a for a in c.of("actions") if a["client_owned"] and a["status"] in ("In progress", "Delayed")]
    figures = [("next_milestone", "Next milestone", nxt["title"] if nxt else "None planned",
                f"{nxt['shown_date']} · {nxt['state']}" if nxt else ""),
               ("client_asks", "What we need from you", str(len(asks)), ""),
               ("watch", "Points to watch", str(len(c.of("raid"))), "")]
    return {"figures": [{"key": k, "label": lab, "value": v, "note": n, "shown": True} for k, lab, v, n in figures]}


def _c_milestones(c, lay):
    refs = [m["id"] for m in c.of("milestones")]
    listed = [r for r in lay["milestones"] if r in refs] if lay["milestones"] is not None else refs
    return {"text": "", "data": {"timeline": refs, "milestones": listed}}


def _c_asks(c, lay):
    rows = [{"ref": a["id"], "shown": True, "cells": {"ask": a["title"], "from": a["owner"], "by": shown(a["due_date"]), "why": ""}}
            for a in c.of("actions") if a["client_owned"] and a["status"] in ("In progress", "Delayed")]
    return {"columns": [{"key": "ask", "label": "Ask"}, {"key": "from", "label": "From"}, {"key": "by", "label": "By"},
                        {"key": "why", "label": "Why it matters"}], "rows": rows}


def _c_progress(c, lay):
    done = [a for a in c.of("actions") if a["status"] == "Complete" and c.start <= (a.get("closed") or "")[:10] <= c.end]
    lines = list(c.spec.get("progress") or []) or [f"Completed: {a['title']}" for a in done]
    return {"text": bullets(lines), "tags": [{"ref": a["id"], "text": a["title"]} for a in done]}


def _c_decisions(c, lay):
    rows = []
    for d in c.of("decisions"):
        if d["status"] == "Made" and (d.get("date") or "") < c.start:
            continue
        when = shown(d["date"]) if d["status"] == "Made" else ("Needed by " + shown(d["needed_by"]) if d.get("needed_by") else "Needed")
        rows.append({"ref": d["id"], "shown": True, "cells": {"decision": d["title"] if d["status"] == "Made"
                                                                          else f"Decision needed: {d['title']}", "date": when}})
    return {"columns": [{"key": "decision", "label": "Decision"}, {"key": "date", "label": "Date"}], "rows": rows}


def _c_risks(c, lay):
    return {"columns": [{"key": "type", "label": "Type"}, {"key": "risk", "label": "What it is"}],
            "rows": [{"ref": r["id"], "shown": True, "cells": {"type": r["type"], "risk": r["title"]}} for r in c.of("raid")]}


def _c_overdue(c, lay):
    late = [a for a in c.of("actions") if a["status"] in ("In progress", "Delayed") and a.get("due_date") and a["due_date"] < c.fri]
    return {"columns": [{"key": "action", "label": "Action"}, {"key": "owner", "label": "Owner"}, {"key": "due", "label": "Due"}],
            "rows": [{"ref": a["id"], "shown": bool(a["client_owned"]),          # the client's own by default; the others greyed
                      "cells": {"action": a["title"], "owner": a["owner"], "due": shown(a["due_date"])}} for a in late]}


CLIENT_BUILDERS = {"header": _c_header,
                   "health": lambda c, lay: {"text": paras(c.spec.get("health_reason", "")),
                                             "data": {"flag": c.spec.get("health") or c.facts.get("health") or "On track"}},
                   "glance": _c_glance, "summary": lambda c, lay: {"text": paras(c.spec.get("summary"))},
                   "milestones": _c_milestones, "asks": _c_asks, "this_week": _c_progress,
                   "next_week": lambda c, lay: {"text": bullets(c.spec.get("next_steps") or [])},
                   "decisions": _c_decisions, "risks": _c_risks, "overdue": _c_overdue,
                   "current_state": lambda c, lay: {"panes": [{"title": "", "text": paras(c.spec.get("current_state"))}]}}


def client_doc(code, week_ending=None, client=None, spec=None, layout=None):
    """A client's view of the week as a creaite document (version 0, a draft; nothing written): client-safe facts only, from the
    latest approved internal week when there is one (its facts locked, `based_on` naming it), else from the tracker as it stands
    (a draft can be made at any time; it is approved or exported only once the internal week is). Every item is checked again by
    client_leak.make_safe before it is returned."""
    import client_leak
    fri = friday(week_ending)
    c = _Client(code, fri, client, spec)
    lay = normal_layout("client", layout if layout is not None else layout_for(code, "client", c.client))
    sections = arrange("client", {sid: f(c, lay) for sid, f in CLIENT_BUILDERS.items()}, lay)
    by_id = {x["id"]: x for t in ("actions", "decisions", "raid", "milestones") for x in c.of(t)}
    used = client_leak.refs({"sections": sections})
    meta = {"period_start": c.start, "period_end": c.end, "locked": c.locked, "facts_on": c.facts.get("on"),
            "facts_week": c.base["date"] if c.base else None}
    doc = creaite_doc.new("client", code, "Client report", fri, sections, audience="client", client=c.client or None, layout=lay,
                          items={r: by_id[r] for r in sorted(used) if r in by_id}, meta=meta,
                          sources=[{"ref": "tracker", "label": "creaite tracker" + (f", as approved for week ending "
                                                                                    f"{shown(c.base['date'])}" if c.base else "")}])
    doc["based_on"] = {"path": c.base["path"], "version": c.base["version"]} if c.base else None
    return client_leak.make_safe(doc)[0]


def build(kind, code, week_ending=None, client=None, spec=None, layout=None):
    """A new weekly or client report document."""
    if kind == "weekly":
        return weekly_doc(code, week_ending, spec, layout)
    return client_doc(code, week_ending, client, spec, layout)


# ── Where a report lives: its draft, and where it is filed ───────────────────

def filed_path(kind, code, week_ending, client=None):
    """The stored path the report is filed at (creaite_doc.target)."""
    return creaite_doc.target(kind, code, week_ending, client=client)


def draft_path(kind, code, week_ending, client=None):
    """The stored path of the report's draft: system/staging/drafts/ with the filed report's name."""
    return paths.rel(paths.DRAFTS / Path(filed_path(kind, code, week_ending, client)).name)


def where(kind, code, week_ending, client=None):
    """("draft" | "filed" | None, stored path): the report to open now. A draft comes first: a filed report is never changed in
    place (Alan, 15-10-2026), so its edits wait as a new draft until that is approved."""
    for state, p in (("draft", draft_path(kind, code, week_ending, client)), ("filed", filed_path(kind, code, week_ending, client))):
        if paths.resolve(p).is_file():
            return state, p
    return None, draft_path(kind, code, week_ending, client)


def save_draft(doc, base_version=None, why=None):
    """Save a report's edits as its draft (system/staging/drafts/, an ordinary change through creaite_doc.save and filechange.py).
    A filed report is never changed in place (Alan, 15-10-2026: option C): Save on a filed report starts a new draft from it, and the
    filed file stays exactly as it is until that draft is approved (stage_weekly or stage_client, one apply with Undo).
    `base_version` is the version the editor opened: the draft's, or the filed report's when there is no draft yet."""
    import client_leak
    kind, code, fri, client = doc.get("kind"), doc.get("project"), doc.get("date"), doc.get("client")
    if kind not in KINDS:
        raise ReportError("Only a weekly or client report is saved here.")
    doc, removed = client_leak.make_safe(doc)
    draft, filed = draft_path(kind, code, fri, client), filed_path(kind, code, fri, client)
    if not paths.resolve(draft).is_file() and paths.resolve(filed).is_file():
        now = int(creaite_doc.read(filed).get("version") or 0)
        if base_version is not None and int(base_version) != now:
            return {"ok": False, "code": 1, "conflict": True, "path": None, "version": None, "removed": removed,
                    "message": f"It was saved elsewhere since you opened it (now version {now})."}
        doc = dict(doc, state="draft", approved_at=None)
        base_version = None
    out = creaite_doc.save(draft, doc, why or f"{'Weekly' if kind == 'weekly' else 'Client'} report saved", base_version=base_version,
                           via="dashboard")
    return {**out, "removed": removed, "filed": paths.resolve(filed).is_file()}


# ── Approve: one proposal, applied with tracker.py apply (the one writer) ───

def _current_ops(doc, folder):
    """The write of the project's Current state when the report's Current state section changed it ([] when unchanged)."""
    import docx_tools
    import report
    s = next((x for x in doc["sections"] if x["id"] == "current_state" and not x.get("hidden")), None)
    panes = (s or {}).get("panes") or []
    if not s or not any((p.get("text") or "").strip() for p in panes):
        return []
    text = docx_tools.join_panes(panes[0].get("text") if panes else "", panes[1].get("text") if len(panes) > 1 else "")
    memory = folder / "CLAUDE.md"
    old = memory.read_text(encoding="utf-8") if memory.exists() else ""
    new = report.replace_current(old, text)
    return [{"op": "write", "path": paths.rel(memory), "content": new, "previous": old}] if new != old else []


def _file_ops(kind, code, fri, client, draft):
    """How Approve files the draft: a first filing of a weekly report copies it; a filed report is replaced whole by the approved new
    version (a write whose earlier text tracker.py keeps, so Undo puts the filed report back exactly as it was). A client report is
    always written whole, without meta.health_diff (the health difference and its reason stay in the draft, Alan 15-10-2026). The
    draft is removed either way."""
    import tracker
    filed = filed_path(kind, code, fri, client)
    exists = paths.resolve(filed).is_file()
    if not exists and kind != "client":
        return [{"op": "copy", "from": "draft", "to": filed}, {"op": "remove", "path": draft}]
    old = paths.resolve(filed).read_text(encoding="utf-8") if exists else None
    doc = creaite_doc.clean(creaite_doc.read(draft))
    on = (os.environ.get("CREAITE_NOW") or tracker.today())[:10]       # as tracker stamps an approved draft
    doc.update(version=int(creaite_doc.loads(old).get("version") or 0) + 1 if exists else int(doc.get("version") or 1),
               saved_at=creaite_doc.now(), state="approved", approved_at=on)
    if kind == "client":
        # Alan, 15-10-2026: the client health difference and its reason live only in the draft. The filed client file, its data
        # block included, never holds them (the internal flag would be in them): the whole key goes, not just the reason.
        doc["meta"] = {k: v for k, v in (doc.get("meta") or {}).items() if k != "health_diff"}
    return [{"op": "write", "path": filed, "content": creaite_doc.dumps(doc), "previous": old}, {"op": "remove", "path": draft}]


def _section(doc, sid):
    """A shown section of the document, or {}."""
    return next((s for s in doc["sections"] if s["id"] == sid and not s.get("hidden")), {})


def stage_weekly(draft, force=False):
    """Stage Approve's proposal for a weekly report draft: the week's update row and any health change (approved), the Current state
    written to the project's memory, and the draft filed as the creaite report (its state set to approved by tracker.py apply).
    The client facts are kept in it first (meta.client_facts), so the week's client reports lock to them. Returns the proposal's
    path; raises ReportError when it can't be approved (items awaiting review, already filed, health better than the evidence
    with no reason)."""
    import report
    import sweep
    import tracker
    doc = creaite_doc.read(draft)
    code, fri = doc["project"], doc["date"]
    data = report.weekly_data(code, fri)
    health_s = _section(doc, "health")
    health = (health_s.get("data") or {}).get("flag") or data["health"] or data["suggested_health"]
    reason = plain(health_s.get("text"))
    refusal = report._weekly_refusal(dict(data, already_filed=False), {"force": force}, health, reason)   # a new version may replace it
    if refusal:
        raise ReportError(refusal)
    con = tracker.connect()
    p, folder, _mem = report.project(con, code)
    if (health != p["health"] or reason != (p["health_reason"] or "")) and not reason:
        raise ReportError(f"Say why health is {health}: write the reason under Health, then approve.")
    doc.setdefault("meta", {})["client_facts"] = client_facts(code)
    saved = creaite_doc.save(draft, doc, "Weekly report approved: the client facts kept", via="dashboard")
    if not saved["ok"]:
        raise ReportError(saved["message"])
    summary = paras(_section(doc, "summary").get("text")) or "No change this week."
    items = report._weekly_items(con, code, p, fri, {"key_changes": (doc.get("meta") or {}).get("key_changes", "")}, health, reason,
                                 summary)
    for it in items:
        it["decision"] = "approved"
    ops = _current_ops(doc, folder) + _file_ops("weekly", code, fri, None, draft)
    return report.stage(f"weekly-{code}", {
        "created": sweep.now().strftime("%Y-%m-%dT%H:%M:00"), "source_run": "dashboard", "files": [], "items": items,
        "report": {"kind": "weekly", "format": "creaite", "title": f"{p['name']} weekly report, week ending {shown(fri)}",
                   "project": code, "projects": [code], "week_ending": fri, "draft": draft, "report_decision": "approved",
                   "file_ops": ops, "health": health, "health_reason": reason, "summary": summary}})


def stage_client(draft, force=False):
    """Stage Approve's proposal for a client report draft: filed as the creaite report beside the internal one. Raises ReportError
    before the internal week is approved, while items await review (unless forced), or when the leak check finds anything."""
    import client_leak
    import report
    import sweep
    doc = creaite_doc.read(draft)
    code, fri = doc["project"], doc["date"]
    ok, why = client_ready(doc)
    if not ok:
        raise ReportError(why)
    found = client_leak.findings(doc)
    if found:
        raise ReportError("Not approved: possible internal content in the client report: " + "; ".join(found))
    blocked = report.pending_for(code)
    if blocked and not force:
        raise ReportError(f"{doc.get('project_name') or code} has {blocked} item{'s' if blocked > 1 else ''} awaiting review — "
                          "review first, or go ahead anyway.")
    base = baseline(code, fri)
    if doc.get("based_on") != {"path": base["path"], "version": base["version"]}:
        doc["based_on"] = {"path": base["path"], "version": base["version"]}
        saved = creaite_doc.save(draft, doc, "Client report approved: locked to the approved week", via="dashboard")
        if not saved["ok"]:
            raise ReportError(saved["message"])
    client = doc.get("client")
    return report.stage(f"client-{code}", {
        "created": sweep.now().strftime("%Y-%m-%dT%H:%M:00"), "source_run": "dashboard", "files": [], "items": [],
        "report": {"kind": "client", "format": "creaite", "title": f"{doc.get('project_name') or code} client report, week ending "
                                                                    f"{shown(fri)}" + (f" ({client})" if client else ""),
                   "project": code, "projects": [code], "week_ending": fri, "draft": draft, "report_decision": "approved",
                   "file_ops": _file_ops("client", code, fri, client, draft)}})
