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
LOGO_KINDS = ("firm", "client", "partner")          # the static kinds (#228 B: a project's real kinds are logo_kinds(code))
LOGO_KIND = re.compile(r"(firm|client|partner(:[a-z0-9]+(-[a-z0-9]+)*)?)\Z")  # a layout kind; a slug is checked per project
LOGO_EXT = (".png", ".jpg", ".jpeg", ".svg")
DEFAULT_ROWS = {"risks": {"top": 5}}
LAYOUT_KEYS = ("order", "hidden", "headings", "glance", "logos", "milestones", "rows")
CODE = re.compile(r"[A-Z][A-Z0-9]{2,6}\Z")   # \Z, not $: "ABC\n" is not a code
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
            "logos": _logo_list(logos_) if isinstance(logos_, list) else base["logos"],
            "milestones": [str(m) for m in miles] if isinstance(miles, list) else None}


def _logo_list(raw):
    """The kinds of a layout's logos that are well formed, once each: the firm, the client, a bare `partner` (every partner), then each
    `partner:<slug>` in the order given. Whether a slug is one of the project's partners is for layout_for, which knows the project."""
    kinds = [x for x in dict.fromkeys(raw) if isinstance(x, str) and LOGO_KIND.match(x)]
    return sorted(kinds, key=lambda x: {"firm": 0, "client": 1, "partner": 2}.get(x, 3))


def stored_layouts():
    """settings.json `report_layouts`: {CODE: {"weekly": layout, "clients": {client: layout}}}."""
    return paths.load_settings().get("report_layouts") or {}


def layout_for(code, kind, client=None):
    """The layout a project's next weekly report (or a client's next client report) starts from."""
    mine = stored_layouts().get(code) or {}
    saved = mine.get("weekly") if kind == "weekly" else (mine.get("clients") or {}).get(client or "")
    lay = normal_layout(kind, saved)
    chosen = project_logos(code)
    lay["logos"] = chosen if chosen is not None else resolve_logos(code, lay["logos"])   # H3 (#221): one choice for both reports' headers
    return lay


def project_logos(code):
    """The logos the project's client report setting ticks (its CLAUDE.md `Client report logos` line), the firm's first; None when
    the project has no such line, or no folder yet, so a report keeps the layout it remembered."""
    import re
    import build_dashboard
    try:
        text = (paths.project_dir(code) / "CLAUDE.md").read_text(encoding="utf-8")
    except (LookupError, OSError):
        return None
    if not re.search(r"\*\*Client report logos:\*\*", text):
        return None
    return build_dashboard.client_report_setting(text)["logos"]


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

def partners(code):
    """[{name, slug}] from the project's CLAUDE.md `Partners` line (build_dashboard.partners_of); [] when it has none or no folder."""
    import build_dashboard
    try:
        return build_dashboard.partners_of((paths.project_dir(code) / "CLAUDE.md").read_text(encoding="utf-8"))
    except (LookupError, OSError):
        return []


def logo_kinds(code):
    """The project's logo kinds: firm, client, then `partner:<slug>` for each partner in line order (or the one old `partner`)."""
    import build_dashboard
    return build_dashboard.logo_kinds_of(partners(code))


def resolve_logos(code, wanted):
    """`wanted` (a layout's logo kinds) made exact for the project: a bare `partner` is every partner, a slug that is not one of its
    partners is dropped, and the order is firm, client, partners in line order."""
    wanted = set(wanted)
    every = "partner" in wanted
    return [k for k in logo_kinds(code) if k in wanted or (every and k.startswith("partner"))]


def logo_stems(code, kind):
    """The file stems a kind's logo may be saved under, the one it is written as first: the firm's `firm`, `<CODE>-client`, a partner's
    `<CODE>-partner-<slug>`. The first partner's also has the old `<CODE>-partner` (read as its logo until it has a file of its own)."""
    if kind == "firm":
        return ["firm"]
    if kind.startswith("partner:"):
        slug = kind[len("partner:"):]
        first = partners(code)[:1]
        return [f"{code}-partner-{slug}"] + ([f"{code}-partner"] if first and first[0]["slug"] == slug else [])
    return [f"{code}-{kind}"]


def _newest(stem):
    have = [paths.REPORT_LOGOS / f"{stem}{e}" for e in LOGO_EXT if (paths.REPORT_LOGOS / f"{stem}{e}").is_file()]
    return max(have, key=lambda f: f.stat().st_mtime) if have else None          # H3: the one added last wins


def logo_file(code, kind):
    """The logo file for the firm, or a project's client or partner logo, or None when none is set. A partner's own file wins; the first
    partner with none of its own is drawn from the old `<CODE>-partner` file (#228 B: no migration)."""
    for stem in logo_stems(code, kind):
        found = _newest(stem)
        if found:
            return found
    return None


def logos(code, wanted=None):
    """[{kind, path}] of the logos set for the project, in `wanted` (a layout's; None is all), in the project's order: the firm's first,
    the client's, then each partner in line order."""
    kinds = logo_kinds(code) if wanted is None else resolve_logos(code, wanted)
    return [{"kind": k, "path": paths.rel(f)} for k in kinds for f in [logo_file(code, k)] if f]


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


def _meta(*parts):
    """Non-empty parts joined with ' · '."""
    return " · ".join(x for x in parts if x)


def _cand(ref, title, meta, item, cells):
    """One thing Add from the tracker can offer: the row it would add (marked added) and the item the document keeps of it."""
    return {"ref": ref, "title": title, "meta": meta, "item": item, "row": {"ref": ref, "shown": True, "source": "added", "cells": cells}}


def _pick_client(code):
    """The client report's candidates: only client-safe facts, in the client's words."""
    facts, out = client_facts(code), {"risks": [], "overdue": [], "decisions": []}
    for r in facts["raid"]:
        out["risks"].append(_cand(r["id"], r["title"], r["type"], r, {"type": r["type"], "risk": r["title"]}))
    for a in facts["actions"]:
        if a["status"] in ("In progress", "Delayed"):
            due = shown(a["due_date"])
            cells = {"action": a["title"], "owner": a["owner"], "due": due}
            out["overdue"].append(_cand(a["id"], a["title"], _meta(a["owner"], due), a, cells))
    for d in facts["decisions"]:
        made = d["status"] == "Made"
        when = shown(d["date"]) if made else ("Needed by " + shown(d["needed_by"]) if d.get("needed_by") else "Needed")
        words = d["title"] if made else f"Decision needed: {d['title']}"
        out["decisions"].append(_cand(d["id"], d["title"], when, d, {"decision": words, "date": when}))
    return out


def _pick_weekly(code):
    """The weekly report's candidates: any open RAID item or action, and the project's decisions."""
    import report
    import tracker
    out = {"risks": [], "overdue": [], "decisions": []}
    with tracker.connect() as con:
        raid = [dict(r) for r in con.execute("SELECT * FROM raid WHERE project = ? AND status = 'Open'", (code,))]
        raid.sort(key=lambda r: report.ORDER.index(r["priority"] or "Low"))
        for r in raid:
            text = f"{r['type']}: {r['description']}"
            out["risks"].append(_cand(r["id"], text, _meta(r["priority"], r["owner"]), item(con, r["id"]),
                                      {"id": r["id"], "risk": text, "priority": r["priority"] or "", "owner": r["owner"]}))
        for a in con.execute("SELECT * FROM actions WHERE project = ? AND status IN ('Open', 'Delayed') "
                             "ORDER BY COALESCE(due_date, '9999'), id", (code,)):
            a = dict(a)
            due = shown(a["due_date"])
            out["overdue"].append(_cand(a["id"], a["description"], _meta(a["owner"], due), item(con, a["id"]),
                                        {"id": a["id"], "action": a["description"], "owner": a["owner"], "due": due or "not due yet"}))
        for d in con.execute("SELECT * FROM decisions WHERE project = ? AND status IN ('Made', 'Pending') "
                             "ORDER BY COALESCE(date, needed_by, '0') DESC, id DESC", (code,)):
            d = dict(d)
            it = item(con, d["id"])
            cells = {"decision": d["decision"], "by": d["made_by"] or "Not recorded", "date": shown(d["date"]),
                     "source": source_label((it or {}).get("source"))}
            out["decisions"].append(_cand(d["id"], d["decision"], _meta(d["made_by"], shown(d["date"])), it, cells))
    return out


def pickable(doc):
    """Add from the tracker (#217, #221): the open items Alan may add to this report's tables, per section, not already in it.
    Read only: nothing is written, and the tracker is never changed by adding. Each candidate is {ref, title, meta, row, item}: the
    row is what the section would hold (marked `source: "added"`), the item what the document keeps of it. A weekly report may
    take any open RAID item or action (not only overdue ones, which then read 'not due yet') and any decision of the project; a client
    report only the client-safe facts (client-visible, complete client wording, no label that keeps it out), so a private item is
    never even offered."""
    kind, code = doc.get("kind"), str(doc.get("project") or "")
    if kind not in KINDS or not CODE.match(code):
        raise ReportError("Say which report: weekly or client, and the project's code.")
    have = {s["id"]: {r.get("ref") for r in s.get("rows") or []} for s in doc.get("sections") or [] if s.get("type") == "table"}
    out = _pick_client(code) if kind == "client" else _pick_weekly(code)
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


def _links_in(s):
    """Whether a stored string may hold a creaite: link (as client_leak reads one: decoded, invisible characters undone)."""
    import client_leak
    return "creaite" in client_leak._decoded(s).lower() or client_leak.overencoded(s)


def _schemes(t):
    """How many creaite: schemes a text holds, as client_leak reads them (decoded)."""
    import client_leak
    return len(client_leak.SCHEME.findall(client_leak._decoded(t)))


def _part_stripped(s, out):
    """Whether drop_item_links' output `out` may hold part of a link it took out of `s` (#123 review): its words' brackets or
    parentheses no longer balance as they did (a line break or a [bracket] inside a link's words, so only its tail went), or a
    reference definition went while its [label] stays (a collapsed or shortcut reference link keeps its words)."""
    import client_leak
    import edit_ai
    import html
    t = html.unescape(edit_ai.unseen(s))
    if any(t.count(a) - t.count(b) != out.count(a) - out.count(b) for a, b in ("[]", "()")):
        return True
    labels = lambda x: {m.group(1).strip().lower() for m in client_leak.REF_DEF.finditer(x)}   # noqa: E731
    low = out.lower()
    return any(f"[{lab}]" in low for lab in labels(t) - labels(out))


WHOLE_LINK = re.compile(r"!?\[[^\[\]\n]*\]\(.*\)|<a\s[^<>]*>[^<]*</a\s*>|<(?!a\s)[a-z][a-z0-9+.-]*:[^<>\s]+>", re.I | re.S)
REFUSED = ("A work-item link a client report can't show couldn't be taken out whole (a line break, brackets or formatting in its "
           "words, a reference link, a bare address or a creaite: address that isn't a work item), so nothing was saved. "
           "Take the link out, then save again.")


def _scheme_count(x):
    """How many creaite: schemes a text holds, in the larger of its two readings: as written and as client_leak decodes it
    (%- and entity-encoding undone, NFKC, so a full-width colon too; invisible characters gone)."""
    import client_leak
    return max(len(client_leak.SCHEME.findall(x)), len(client_leak.SCHEME.findall(client_leak._decoded(x))))


def _whole_or_refuse(s, code, con):
    """#123 third review: fail closed on EVERY creaite: occurrence, not on a list of shapes. Each one in the string must sit inside
    a link client_leak.LINK_SPAN matched whole, words and address together (an inline link, a whole HTML link with plain words, an
    <auto> link), whose every address client_leak.item_links reads as an item the tracker holds: a client-visible one is kept, a
    hidden one goes whole. Anything else (another noun such as item: item# task/ note/ person/, a bare address, a reference
    definition, a bare <a> tag, an unknown ID) refuses. Returns the hidden items' IDs (for the second check)."""
    import client_leak
    import edit_ai
    import html
    blocking = client_leak.blocking_labels(con)
    t = edit_ai.unseen(html.unescape(s))                                   # as drop_item_links reads it
    t = client_leak.LINK_GAP.sub(lambda m: re.sub(r"\s+", "", m.group(0)), t)
    covered, gone = 0, set()
    for m in client_leak.LINK_SPAN.finditer(t):
        span = m.group(0)
        n = _scheme_count(span)
        if not n or not WHOLE_LINK.fullmatch(span):
            continue
        addresses = client_leak.item_links(span)
        ids = [edit_ai.loose_ids(con, a) for a in addresses]
        if len(addresses) != n or any(not x or not all(edit_ai.in_tracker(con, i) for i in x) for x in ids):
            continue
        covered += n
        gone |= {i for a, x in zip(addresses, ids) for i in x
                 if not client_leak._link_ok(con, code, f"creaite:item/{a}", blocking)}
    if covered < _scheme_count(t) or client_leak.overencoded(s):
        raise ReportError(REFUSED)
    return gone


def _drop_one(s, code, con):
    """One string with the creaite: links a client may not have taken out whole; the string exactly as it was when none went (#123
    review: drop_item_links rewrites entities in the whole string). When any went, refuses (ReportError) rather than keep part of a
    link: every creaite: occurrence must be inside a whole link to a known item (_whole_or_refuse), and, a second check, what is left
    may not hold a removed hidden item's ID or wording (client_leak.text_findings)."""
    import client_leak
    if not _links_in(s):
        return s
    out = client_leak.drop_item_links(code, s, con)
    if _schemes(out) == _schemes(s):
        return s
    gone = _whole_or_refuse(s, code, con)
    if _part_stripped(s, out) or any(f.split(" ")[0] in gone for f in client_leak.text_findings(con, code, out)):
        raise ReportError(REFUSED)
    return out


def _drop_links(x, code, con):
    """A section's value with every string's creaite: links a client may not have taken out (_drop_one)."""
    if isinstance(x, str):
        return _drop_one(x, code, con)
    if isinstance(x, list):
        return [_drop_links(v, code, con) for v in x]
    if isinstance(x, dict):
        return {k: _drop_links(v, code, con) for k, v in x.items()}
    return x


def client_item_links(doc, con=None):
    """#123 (#122 step C, client path): (a copy of a client document with every work-item link a client may not have taken out
    WHOLE from every section, words and address, [why each went]). A link's words may have been edited so they no longer name the
    item, and its address would stay in the stored text; client_leak.drop_item_links reads the address. A link to an item a client
    may see stays as it is. An internal document is returned as it is. Fails closed: when the tracker can't be read, ReportError
    (nothing is built or saved)."""
    import client_leak
    if (doc.get("audience") or "internal") == "internal":
        return doc, []
    code = doc.get("project") or ""
    try:
        con = con or client_leak.connect()
        before = client_leak.raw_strings({"sections": doc.get("sections") or []})
        sections = _drop_links(doc.get("sections") or [], code, con)
        after = client_leak.raw_strings({"sections": sections})
        gone = sorted({i for i in client_leak.item_links(before)} - {i for i in client_leak.item_links(after)})
    except ReportError:
        raise
    except Exception as e:  # noqa: BLE001  fails closed
        raise ReportError("The work-item links couldn't be checked against the tracker, so nothing was built or saved. "
                          "Try again; if it keeps happening, run the health check.") from e
    if after == before:
        return doc, []
    return dict(doc, sections=sections), [f"a link to {i}, an item a client report can't show, was taken out" for i in gone] or [
        "a link a client report can't hold was taken out"]


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
    return client_item_links(client_leak.make_safe(doc)[0])[0]


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
    doc, dropped = client_item_links(doc)
    removed = removed + dropped
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
