"""creaite report helper — the exact parts of cx-weekly-report and cx-client-report (standard library only).

Commands:
  weekly-data <CODE> [--week-ending YYYY-MM-DD]
        the week's facts as JSON: blocked (pending items), already filed, actions opened/closed/overdue, top risks and
        issues, decisions, milestones, changes, status signals, last update, current state, and the health the
        criteria suggest with its reasons (settings.json `health`); promises: what Alan owes and what he is waiting on
        (BL-125 A), which weekly-stage lists first in Next Week and Help Needed
  weekly-stage <spec.json>
        fill the weekly report and stage one proposal: the updates row, any health change, the current-state rewrite
        and the report (filed to reports/YYYY-MM-DD Weekly report - <Project name>.docx on approval)
  steerco-data <CODE> [--version internal|client] [--since YYYY-MM-DD] [--date YYYY-MM-DD] [--include ID,ID]
        the steering one-pager's facts as JSON (BL-92): status and trend, what changed since the last one-pager, milestones, top
        risks, decisions needed, blockers, flow, the next period, and what the client-safe version left out and why
  steerco-stage <spec.json>
        fill steerco-template.docx (sections with nothing to say are left out) into system/staging/drafts/ and stage it; on
        approval it is filed in the project's Steerco folder as YYYY-MM-DD <Project name> Steerco one-pager[ (client)].docx, never overwriting
  client-data <CODE> [--since YYYY-MM-DD]
        the client-safe facts as JSON: period, health, milestones, client-visible actions (theirs and ours), decisions
        and risks/issues with their client messaging, plus what's excluded or missing messaging
  client-stage <spec.json>
        fill the client report and stage it (filed to reports/YYYY-MM-DD Client report - <Project name>.docx on approval)
  current-context <CODE> [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--sources tracker,minutes,reports,updates,swept,documents]
                         [--audience internal|client] [--length short|standard|fuller]
        the material for drafting a project's Current state (BL-46), as plain text for the prompt: tracker changes
        and the open position, minutes, transcripts and reports in the period (paths, for Claude to read), updates
        rows, items already swept from mail and Teams, documents only if asked, the current text and the last sweep

  facts <CODE> [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--audience internal|client] [--json]
        the ranked facts sheet an executive status is written from (BL-106; see status_facts.py)
  adhoc <spec.json>
        build a one-off branded Word document (BL-75), such as an actions register, a RAID extract or a decision log, in
        system/staging/drafts/YYYY-MM-DD <title>.docx (never overwriting; nothing is filed). Tables can come straight
        from the tracker. spec: {"title", "subtitle", "status", "when", "source", "landscape", "sections": [
          {"heading", "paragraphs": [..], "bullets": [..], "note", "table": {"columns": [..], "rows": [[..]]},
           "tracker": {"table": "actions"|"raid"|"decisions"|"milestones", "project": "ABC" or [..], "owner", "status":
                       "open"|"closed"|"all", "type": "Risk", "overdue": true, "due_before", "due_after", "workstream",
                       "columns": [..], "group_by": "project", "limit": 500}} ]}
  adhoc-data <table> [--project CODE] [--owner NAME] [--status open|closed|all] [--type T] [--overdue] [--due-before D]
        the same rows as JSON (columns, rows, count), to read before writing an introduction

weekly spec: {"code", "week_ending", "health", "health_reason", "summary": [..], "key_changes", "current_state",
              "progress": [..], "next_week": [..], "help_needed": [..], "force": false}
client spec: {"code", "period_start", "summary": [..], "progress": [..], "next_steps": [..], "input_needed": [..],
              "force": false}
steerco spec: {"code", "version": "internal" | "client", "steerco_date", "since", "summary": [..], "include_labelled": [ids],
               "force": false}
The tables (milestones, overdue actions, risks, client actions) come from the tracker, never from Claude.
Set CREAITE_NOW="YYYY-MM-DD HH:MM" to fix the clock (tests).
"""
import json
import re
import sys
from datetime import date, timedelta
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
import review  # noqa: E402
import build_dashboard  # noqa: E402
import docx_tools  # noqa: E402
import sweep  # noqa: E402  (now(), the shared clock)

ORDER = ["Urgent", "High", "Medium", "Low"]
HEADINGS = ("What it is:", "What it means for you:", "What is being done:")


def today():
    """Today on creaite's clock (sweep.now; CREAITE_NOW fixes it for tests)."""
    return sweep.now().date()


def long_date(iso):
    """A stored date written out in full for a report; '' when there is none."""
    return tracker.long_date(iso) if iso else ""


def rows(con, sql, *args):
    """The rows a query returns, as dicts."""
    return [dict(r) for r in con.execute(sql, args)]


def doc_stem(name):
    """A project's name as it goes into a file name (BL-101)."""
    return re.sub(r"\s+", " ", re.sub(r'[\\/:*?"<>|\x00-\x1f]', " ", name or "")).strip(" .") or "Project"


def report_file(day, kind, name, ext=".docx"):
    """YYYY-MM-DD Weekly report - <Project name>.docx (or Client report): the project's full name, never its code (BL-101).
    Files named the earlier way (YYYY-MM-DD Weekly report.docx) are still recognised and never renamed. v2.1.0 P1: ext=".html"
    names a creaite report (creaite_doc.target); the Word drafts keep .docx until P3 retires them."""
    return f"{day} {kind} - {doc_stem(name)}{ext}"


def project(con, code):
    """(project row, project folder, memory) for a code; exits with a message when the code isn't in the tracker."""
    p = rows(con, "SELECT * FROM projects WHERE code = ?", code)
    if not p:
        sys.exit(f"{code} isn't in the tracker.")
    folder = paths.project_dir(code)
    return p[0], folder, build_dashboard.memory(folder)


def pending_for(code):
    """How many review rows are pending for a project: a report waits while any are, unless forced."""
    return sum(1 for r in review.build_rows() if r["project"] == code)


def friday_of(d):
    """The Friday of d's working week; a weekend day gives the Friday just gone."""
    return d + timedelta(days=(4 - d.weekday()) % 7) if d.weekday() <= 4 else d - timedelta(days=d.weekday() - 4)


def milestones(con, code):
    """A project's milestones, Cancelled left out, in order, each with its slip in days, percent complete and state (BL-186: the five
    states, and the client's word for each)."""
    out = []
    for m in rows(con, "SELECT * FROM milestones WHERE project = ? AND status != 'Cancelled' ORDER BY sort_order, "
                       "forecast_date", code):
        slip = 0
        if m["baseline_date"] and m["forecast_date"]:
            slip = (date.fromisoformat(m["forecast_date"]) - date.fromisoformat(m["baseline_date"])).days
        st = tracker.milestone_state(m)               # BL-186: one vocabulary (the five states; the client's words for a client)
        out.append({**m, "slip_days": slip, "percent": tracker.milestone_progress(con, m)[0], "state": st,
                    "client_word": tracker.MS_CLIENT_WORD[st]})   # BL-29
    return out


def client_date(m):
    """BL-186: what a client reads as the date: the agreed date, and the expected one when it is later."""
    base, fc = m.get("baseline_date"), m.get("forecast_date")
    if m.get("status") == "Done":
        return tracker.shown(m.get("actual_date") or fc or base) or "Not set"
    if base and fc and fc > base:
        return f"{tracker.shown(base)}; expected {tracker.shown(fc)}"
    return tracker.shown(base or fc) or "Not set"


def pct(m):
    """A milestone's percent complete as text, or "—" when there is none."""
    return f"{m['percent']}%" if m.get("percent") is not None else "—"


def write_values(values, name):
    """Write a template's values to system/staging/drafts/<name>.values.json for docx_tools fill; returns the file."""
    f = paths.DRAFTS / f"{name}.values.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8")
    return f


def fill(template, values, out):
    """Fill a Word template with `values` into `out` (docx_tools fill), removing the values file after. Exits, staging nothing, if it
    can't be filled."""
    f = write_values(values, out.stem)
    try:
        code = docx_tools.cmd_fill(str(template), str(f), str(out))
    finally:
        f.unlink(missing_ok=True)
    if code:
        debuglog.warn("report", f"the template couldn't be filled for {out.name}; nothing was staged")
        sys.exit("The report template couldn't be filled; nothing was staged.")


def stage(name, data):
    """Write a report proposal to system/staging/proposed-<time>-<name>.json, validating its items, and log it. Returns the file."""
    out = paths.STAGING / f"proposed-{sweep.now():%Y-%m-%d-%H%M}-{name}.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if data.get("items"):
        tracker.cmd_validate(str(out))
    rep = data.get("report") or {}
    debuglog.info("report", f"staged {out.name}: {rep.get('kind', 'report')} for {rep.get('project') or 'no project'}, "
                  f"draft {rep.get('draft') or 'none'}, {len(data.get('items') or [])} item(s)")
    return out


# ── Ad-hoc documents (BL-75) ──────────────────────────────────────────────────
# A one-off Word document in the house style from the same scripts as the reports: the tables come from the tracker,
# the words from the spec. It goes to system/staging/drafts/ and nothing is filed or sent.

AD_COLUMNS = {   # table -> {key: (header, how to show it)}; the first entries are the defaults
    "actions": {"id": "ID", "project": "Project", "description": "Action", "owner": "Owner", "due_date": "Due",
                "priority": "Priority", "status": "Status", "workstream": "Workstream", "latest_update": "Latest update",
                "raised": "Raised", "closed": "Closed"},
    "raid": {"id": "ID", "project": "Project", "type": "Type", "description": "Description", "owner": "Owner",
             "priority": "Priority", "response_action": "Response", "due_date": "Due", "status": "Status",
             "workstream": "Workstream", "raised": "Raised", "closed": "Closed"},
    "decisions": {"id": "ID", "project": "Project", "decision": "Decision", "status": "Status", "made_by": "Made by",
                  "needed_by": "Needed by", "date": "Date"},
    "milestones": {"id": "ID", "project": "Project", "name": "Milestone", "baseline_date": "Baseline",
                   "forecast_date": "Forecast", "percent": "% complete", "status": "Status"},
}
AD_DEFAULT = {"actions": ("id", "description", "owner", "due_date", "priority", "status"),
              "raid": ("id", "type", "description", "owner", "priority", "response_action", "due_date", "status"),
              "decisions": ("id", "decision", "status", "made_by", "needed_by", "date"),
              "milestones": ("id", "name", "baseline_date", "forecast_date", "percent", "status")}
AD_KEYS = {"table", "project", "owner", "status", "type", "overdue", "due_before", "due_after", "workstream", "columns",
           "group_by", "limit"}
OPEN_STATUS = {"actions": ("Open", "Delayed"), "raid": ("Open",), "decisions": (), "milestones": ("Planned",)}


# ===== BL-229 (v1.7.0): adhoc_rows in steps: check the query, build its filters, run it, shape each row's cells.
# The SQL, the order, the messages and the cells are unchanged (test_report_builders_pinned.py, test_adhoc_docs.py).
def adhoc_rows(q):
    """The tracker rows a query asks for, as {"columns": [headers], "rows": [[cells]], "count", "groups": {code: rows}}.
    Dates are DD-MM-YYYY; an open item that is late says how late."""
    table, keys = _adhoc_query(q)
    con = tracker.connect()
    names = {x["code"]: x["name"] for x in rows(con, "SELECT code, name FROM projects")}
    due_col = {"actions": "due_date", "raid": "due_date", "milestones": "forecast_date", "decisions": "date"}[table]
    today_iso = today().isoformat()
    where, args = _adhoc_filters(q, table, due_col, today_iso)
    sql = f"SELECT * FROM {table}" + (" WHERE " + " AND ".join(where) if where else "")
    order = f"project, COALESCE({due_col}, '9999'), id" if table != "decisions" else "project, date DESC, id"
    found = rows(con, sql + f" ORDER BY {order} LIMIT {max(1, min(int(q.get('limit') or 500), 2000))}", *args)
    if table == "milestones":
        for m in found:
            done = tracker.milestone_progress(con, m)[0]
            m["percent"] = f"{done}%" if done is not None else "—"
    out = [(r["project"], [_adhoc_cell(r, k, table, names, today_iso) for k in keys]) for r in found]
    con.close()
    groups = {}
    for code, cells in out:
        groups.setdefault(code, []).append(cells)
    return {"columns": [AD_COLUMNS[table][k] for k in keys], "keys": keys, "rows": [c for _, c in out], "count": len(out),
            "groups": groups}


def _adhoc_query(q):
    """(table, column keys) of a query, or an exit naming what's wrong with it."""
    bad = sorted(set(q) - AD_KEYS)
    table = q.get("table")
    if bad or table not in AD_COLUMNS:
        sys.exit(f"tracker query: {'unknown key ' + ', '.join(bad) if bad else 'table must be one of ' + ', '.join(AD_COLUMNS)}")
    keys = list(q.get("columns") or AD_DEFAULT[table])
    unknown = [k for k in keys if k not in AD_COLUMNS[table]]
    if unknown:
        sys.exit(f"tracker query: {table} has no column {', '.join(unknown)} (use {', '.join(AD_COLUMNS[table])})")
    return table, keys


def _adhoc_filters(q, table, due_col, today_iso):
    """The WHERE clauses and their arguments, in the order they always had."""
    where, args = [], []
    projects = [q["project"]] if isinstance(q.get("project"), str) else list(q.get("project") or [])
    if projects:
        where.append(f"project IN ({','.join('?' * len(projects))})")
        args += projects
    if q.get("owner") and table != "milestones":
        col = "made_by" if table == "decisions" else "owner"
        where.append(f"(lower({col}) = lower(?) OR lower({col}) LIKE lower(?))")      # "Name" or "Name (Company)"
        args += [q["owner"], q["owner"] + " (%"]
    _adhoc_status(q.get("status", "open"), table, where, args)
    if q.get("type") and table == "raid":
        where.append("type = ?")
        args.append(q["type"])
    if q.get("workstream") and table in ("actions", "raid"):
        where.append("lower(workstream) = lower(?)")
        args.append(q["workstream"])
    for key, op in (("due_before", "<="), ("due_after", ">=")):
        if q.get(key):
            where.append(f"{due_col} {op} ?")
            args.append(q[key])
    if q.get("overdue") and table in ("actions", "raid"):
        where.append(f"due_date < ? AND status IN ({','.join('?' * len(OPEN_STATUS[table]))})")
        args += [today_iso, *OPEN_STATUS[table]]
    return where, args


def _adhoc_status(status, table, where, args):
    """open (the default), closed, all, a status by name, or (decisions, BL-53) pending, made or withdrawn."""
    if status == "open" and OPEN_STATUS[table]:
        where.append(f"status IN ({','.join('?' * len(OPEN_STATUS[table]))})")
        args += OPEN_STATUS[table]
    elif status == "closed" and table in ("actions", "raid"):
        where.append("status IN ('Closed','Cancelled')")
    elif status not in ("open", "closed", "all") and table != "decisions":
        where.append("status = ?")
        args.append(status)
    elif table == "decisions" and status.lower() in ("pending", "made", "withdrawn"):       # BL-53
        where.append("status = ?")
        args.append(status.capitalize())


def _adhoc_cell(r, k, table, names, today_iso):
    """One cell: dates as DD-MM-YYYY (an open item's late due date says how late), a project by its name."""
    v = r.get(k)
    if k in tracker.DATE_FIELDS or k.endswith("_date") or k in ("date", "raised", "closed"):
        late = r.get("status") in OPEN_STATUS[table] and k == "due_date" and v and v < today_iso
        v = (tracker.shown(v) if v else "") + (f" · {(today() - date.fromisoformat(r['due_date'])).days} days late" if late else "")
    if k == "project":
        v = names.get(v, v)                                  # BL-101: the project's name, not its code
    return v if v not in (None,) else ""
# ===== end BL-229 (adhoc_rows) =====


def adhoc_spec(spec):
    """The spec with each tracker query replaced by the table it describes (one section per project if group_by)."""
    sections = []
    con = tracker.connect()
    names = {r["code"]: r["name"] for r in rows(con, "SELECT code, name FROM projects")}
    con.close()
    for sec in spec.get("sections") or []:
        q = sec.get("tracker")
        if not q:
            sections.append(sec)
            continue
        data = adhoc_rows(q)
        label = {"actions": "action", "raid": "RAID item", "decisions": "decision", "milestones": "milestone"}[q["table"]]
        if q.get("group_by") == "project" and "project" not in data["keys"]:
            for code, rws in data["groups"].items():
                sections.append({**{k: v for k, v in sec.items() if k != "tracker"}, "heading": names.get(code) or code,
                                 "paragraphs": [f"{len(rws)} {label}{'s' if len(rws) != 1 else ''}."] + list(sec.get("paragraphs") or []),
                                 "table": {"columns": data["columns"], "rows": rws}})
            if not data["groups"]:
                sections.append({**{k: v for k, v in sec.items() if k != "tracker"}, "paragraphs": [f"No {label}s match."]})
        else:
            first = {**{k: v for k, v in sec.items() if k != "tracker"},
                     "paragraphs": [f"{data['count']} {label}{'s' if data['count'] != 1 else ''}."] + list(sec.get("paragraphs") or [])}
            if data["rows"]:
                first["table"] = {"columns": data["columns"], "rows": data["rows"]}
            else:
                first["paragraphs"] = [f"No {label}s match."] + list(sec.get("paragraphs") or [])
            sections.append(first)
    return {**spec, "sections": sections}


def adhoc_name(title):
    """A one-off document's title made safe for a file name, at most 80 characters (BL-75)."""
    clean = re.sub(r'[\\/:*?"<>|]+', " ", title or "Document").strip() or "Document"
    return re.sub(r"\s+", " ", clean)[:80]


def adhoc(spec):
    """Build the document into system/staging/drafts/ and say where it is."""
    if not isinstance(spec, dict) or not (spec.get("title") or "").strip():
        sys.exit("The document needs a title.")
    if str(spec.get("audience") or "internal").strip().lower() != "internal":     # #127: never a client path; nothing checks it
        sys.exit("A one-off document is internal only. For the client, say \"client report ABC\" or \"steerco one-pager ABC "
                 "client-safe\": those are checked before they are filed.")
    built = adhoc_spec(spec)
    built.setdefault("status", f"Draft, generated by creaite on {long_date(today().isoformat())}. Internal: not for the client "
                               "unless you decide otherwise.")
    built.setdefault("when", tracker.shown(today().isoformat()))
    template = paths.TEMPLATES / "adhoc-template.docx"
    if not template.exists():
        sys.exit("system/templates/adhoc-template.docx is missing; update creaite or run dev/tools/build_templates.py adhoc.")
    stem = f"{today().isoformat()} {adhoc_name(spec['title'])}"
    out, n = paths.DRAFTS / f"{stem}.docx", 2
    paths.DRAFTS.mkdir(parents=True, exist_ok=True)
    while out.exists():
        out, n = paths.DRAFTS / f"{stem} {n}.docx", n + 1
    try:
        tables = docx_tools.build_adhoc(template, built, out)
    except ValueError as e:
        debuglog.warn("report", "an ad hoc document couldn't be built")
        sys.exit(f"The document couldn't be built: {e}")
    rows_n = sum(len(sec["table"]["rows"]) for sec in built["sections"] if sec.get("table"))
    debuglog.info("report", f"ad hoc document written: {paths.rel(out)} ({tables} table(s), {rows_n} row(s))")
    print(f"Wrote {paths.rel(out)} ({tables} table{'s' if tables != 1 else ''}, {rows_n} row{'s' if rows_n != 1 else ''}). "
          "A draft in house style: open it in Word to review. Nothing is filed or sent.")
    return 0


def adhoc_data(table, opts):
    """The adhoc-data command's answer: one tracker table's rows, filtered by the options in AD_KEYS (project, owner, overdue and the
    rest), for cx-document to build from (BL-75). Read only."""
    q = {"table": table, **{k: v for k, v in opts.items() if k in AD_KEYS and k != "overdue"}}
    if opts.get("overdue"):
        q["overdue"] = True
    if q.get("project") and isinstance(q["project"], str) and "," in q["project"]:
        q["project"] = q["project"].split(",")
    data = adhoc_rows(q)
    return {"table": table, "count": data["count"], "columns": data["columns"], "rows": data["rows"]}


# ── Weekly ────────────────────────────────────────────────────────────────────

def criteria(overdue, raid, nxt, cut, h):
    """The health the evidence suggests, with its reasons (settings.json `health`)."""
    reasons_off, reasons_risk = [], []
    over_n = [a for a in overdue if (cut - date.fromisoformat(a["due_date"])).days > h.get("at_risk_overdue_days", 7)]
    urgent = [r for r in raid if r["priority"] == "Urgent"]
    slip = nxt["slip_days"] if nxt else 0
    if slip > h.get("off_track_milestone_slip_weeks_over", 2) * 7:
        reasons_off.append(f"{nxt['name']} moved {slip} days ({tracker.shown(nxt['baseline_date'])} → "
                           f"{tracker.shown(nxt['forecast_date'])})")
    if len(urgent) >= h.get("off_track_urgent_risks_min", 2):
        reasons_off.append(f"{len(urgent)} open Urgent risks or issues ({', '.join(r['id'] for r in urgent)})")
    if over_n:
        reasons_risk.append(f"{len(over_n)} action{'s' if len(over_n) > 1 else ''} overdue by more than "
                            f"{h.get('at_risk_overdue_days', 7)} days ({', '.join(a['id'] for a in over_n)})")
    if urgent and not reasons_off:
        reasons_risk.append(f"open Urgent risk or issue ({', '.join(r['id'] for r in urgent)})")
    if 0 < slip <= h.get("at_risk_milestone_slip_weeks_max", 2) * 7:
        reasons_risk.append(f"{nxt['name']} moved {slip} days")
    return ("Off track" if reasons_off else "At risk" if reasons_risk else "On track"), reasons_off, reasons_risk


HEALTH_RANK = {"On track": 0, "At risk": 1, "Off track": 2}


def health_evidence(code, client_only=False, live_only=False):
    """{suggested, reasons} for a project now (BL-52: health better than this needs a reason). `client_only` (#203): the same criteria
    over client-visible items alone (client_leak.item_problem passes them), so an internal-only item never drives a client-facing
    flag; it carries no early warnings. `live_only`: archived items are left out (suggest mode; default keeps the old behaviour)."""
    con = tracker.connect()
    cut = today()
    actions = rows(con, "SELECT * FROM actions WHERE project = ? AND status IN ('Open','Delayed') AND due_date < ?",
                   code, cut.isoformat())
    raid = rows(con, "SELECT * FROM raid WHERE project = ? AND status = 'Open'", code)
    mss = [m for m in milestones(con, code) if m["status"] == "Planned"]
    if live_only:
        actions, raid, mss = ([x for x in xs if not x.get("archived")] for xs in (actions, raid, mss))
    if client_only:
        import client_leak
        blocking = client_leak.blocking_labels(con)
        shown_ = lambda x: not client_leak.item_problem(con, x["id"], blocking)      # noqa: E731
        actions, raid, mss = ([x for x in xs if shown_(x)] for xs in (actions, raid, mss))
    nxt = mss[0] if mss else None
    suggested, off, risk = criteria(actions, raid, nxt, cut, paths.load_settings().get("health", {}))
    return {"suggested": suggested, "reasons": off or risk, "warnings": [] if client_only else project_warnings(code)}   # BL-51


def project_warnings(code):
    """BL-51's early warnings for one project: "ID: reason" lines (evidence for health and the weekly draft)."""
    return [f"{tracker.project_label(w['id']) if w.get('k') == 'projects' else w['id']}: {w['text']}"     # BL-101: a project is its name
            for w in build_dashboard.early_warnings(paths.load_settings(), today()) if w["p"] == code]


def better_than_evidence(health, evidence):
    """Whether a health is better than the tracker's evidence suggests (so it needs a reason)."""
    return HEALTH_RANK.get(health, 0) < HEALTH_RANK.get(evidence["suggested"], 0)


# ===== Decisions and schema (BL-53, sprint 5) =====

def decisions_needed(con, code, as_of):
    """A project's pending decisions, soonest needed first: {id, text, by, needed_by, overdue_days} (a decision needed from nobody
    yet has by None; one with no needed-by date has needed_by None and is never overdue)."""
    out = []
    for d in rows(con, "SELECT * FROM decisions WHERE project = ? AND status = 'Pending' ORDER BY COALESCE(needed_by, '9999'), id", code):
        late = (as_of - date.fromisoformat(d["needed_by"][:10])).days if d["needed_by"] else 0
        out.append({"id": d["id"], "text": d["decision"], "by": d["made_by"], "needed_by": d["needed_by"],
                    "overdue_days": late if late > 0 else 0})
    return out


def decision_needed_line(d):
    """'Needed: Extend the pilot — from Sara Example, by 16-10-2026 (3 days overdue)' for the Word report's Decisions list."""
    when = f"by {tracker.shown(d['needed_by'])}" if d["needed_by"] else "no date needed by"
    late = f" ({d['overdue_days']} day{'s' if d['overdue_days'] != 1 else ''} overdue)" if d["overdue_days"] else ""
    return f"Needed: {d['text']} — {('from ' + d['by']) if d['by'] else 'no one asked yet'}, {when}{late}"


# ===== BL-229 (v1.7.0): weekly_data in gather and shape steps. The keys and their order are unchanged (the JSON is
# printed unsorted; test_report_builders_pinned.py and test_reports.py).
class _Week:
    """The reporting week: Monday to Friday, and the cut-off for "overdue" (today, or Friday if the week is past)."""

    def __init__(self, week_ending):
        self.fri = date.fromisoformat(week_ending) if week_ending else friday_of(today())
        self.mon = self.fri - timedelta(days=4)
        self.cut = min(today(), self.fri)

    def holds(self, d):
        """Whether a date (or a timestamp's date) falls in the week."""
        return bool(d) and self.mon.isoformat() <= d[:10] <= self.fri.isoformat()


def weekly_data(code, week_ending=None):
    """The facts a weekly report is drafted from (the weekly-data command): the week, health and the suggested health, overdue actions,
    risks, milestones, the week's changes and the rest. Read only."""
    con = tracker.connect()
    p, folder, mem = project(con, code)
    wk = _Week(week_ending)
    h = paths.load_settings().get("health", {})
    actions = rows(con, "SELECT * FROM actions WHERE project = ?", code)
    overdue = sorted([a for a in actions if a["status"] in ("Open", "Delayed") and a["due_date"]
                      and a["due_date"] < wk.cut.isoformat()], key=lambda a: a["due_date"])
    raid = rows(con, "SELECT * FROM raid WHERE project = ? AND status = 'Open'", code)
    risks = sorted([r for r in raid if r["type"] in ("Risk", "Issue")], key=lambda r: ORDER.index(r["priority"] or "Low"))
    ms = milestones(con, code)
    nxt = next((m for m in ms if m["status"] == "Planned"), None)
    changes = rows(con, "SELECT at, tbl, item_id, field, old_value, new_value FROM change_log WHERE op = 'update' AND "
                        "substr(at, 1, 10) BETWEEN ? AND ? AND field IN ('health', 'forecast_date', 'baseline_date', "
                        "'priority', 'status', 'milestone_date') AND (item_id = ? OR item_id LIKE ?)",
                   wk.mon.isoformat(), wk.fri.isoformat(), code, f"{code}-%")
    signals = _week_signals(code, wk)
    last = rows(con, "SELECT * FROM updates WHERE project = ? AND week_ending < ? ORDER BY week_ending DESC LIMIT 1",
                code, wk.fri.isoformat())
    wdir = paths.folder(code, "weekly_reports")
    filed = week_filed(wdir, wk.fri.isoformat())

    # Health criteria (dev/dashboard-spec.md): proposed, never set silently
    suggested, reasons_off, reasons_risk = criteria(overdue, raid, nxt, wk.cut, h)
    blocking = [r["id"] for r in raid if r["type"] == "Issue" and r["priority"] in ("Urgent", "High")]

    return {
        "code": code, "name": p["name"], "week_ending": wk.fri.isoformat(), "week_start": wk.mon.isoformat(),
        "blocked": pending_for(code), "already_filed": filed,
        "health": p["health"], "health_reason": p["health_reason"],
        "suggested_health": suggested, "reasons": reasons_off or reasons_risk,
        "check_blocking_issues": blocking,
        "actions_opened": [a["id"] + " " + a["description"] for a in actions if wk.holds(a["raised"])],
        "actions_closed": [a["id"] + " " + a["description"] for a in actions if a["status"] == "Closed" and wk.holds(a["closed"])],
        "overdue": [{"id": a["id"], "text": a["description"], "owner": a["owner"], "due": a["due_date"]} for a in overdue],
        "top_risks": [{"id": r["id"], "type": r["type"], "text": r["description"], "priority": r["priority"],
                       "owner": r["owner"], "response": r["response_action"]} for r in risks[:5]],
        "decisions": _week_decisions(con, code, wk),
        "decisions_needed": decisions_needed(con, code, wk.cut),                       # BL-53
        "decisions_to_revisit": _week_revisits(con, code, wk),
        "milestones": _week_milestones(con, ms),
        "changes": changes, "status_signals": signals, "last_update": last[0] if last else None,
        "current_state": mem["current"], "images": [i["alt"] for i in mem["images"]],
        "flow": flow_line_for(code, wk.fri),      # BL-91: "12 opened, 9 closed; 3 overdue, down from 5; the oldest open …"
        "quiet_week": not (changes or signals or any(wk.holds(a["raised"]) or wk.holds(a["closed"]) for a in actions)),
        "early_warnings": project_warnings(code),      # BL-51: for the draft's summary and help needed; not health alone
        "vip": weekly_vip(code, [a["owner"] for a in overdue] + [r["owner"] for r in risks[:5]]),   # BL-99
        "promises": _week_promises(con, code, wk),     # BL-125 A: what Alan owes, and the overdue promises he is waiting on
    }


def week_filed(wdir, fri):
    """Whether the week's weekly report is filed: a Word report, or (v2.1.0 P3) a creaite report."""
    return wdir.is_dir() and any(f.suffix in (".docx", ".html") for f in wdir.glob(f"{fri} Weekly report*"))


def _week_signals(code, wk):
    """Status signals from the week's proposals: this project's meetings, and sweeps (flagged to check)."""
    signals = []
    for folder_ in (paths.STAGING, paths.APPLIED):
        for prop in folder_.glob("proposed-*.json"):
            d = json.loads(prop.read_text(encoding="utf-8"))
            if not wk.holds(d.get("created", "")):
                continue
            projects = (d.get("meeting") or {}).get("projects") or []
            for s_ in d.get("status_signals", []):
                if code in projects:
                    signals.append(s_)
                elif d.get("source_run") == "cx-sweep":
                    signals.append(f"{s_} (from a sweep; check it applies to {code})")
    return signals


def _week_decisions(con, code, wk):
    return [{"id": d["id"], "text": d["decision"], "by": d["made_by"], "date": d["date"]}
            for d in rows(con, "SELECT * FROM decisions WHERE project = ? AND status = 'Made'", code) if wk.holds(d["date"])]


def _week_revisits(con, code, wk):
    return [{"id": d["id"], "text": d["decision"], "revisit": d["revisit"]} for d in rows(
        con, "SELECT * FROM decisions WHERE project = ? AND status = 'Made' AND revisit GLOB "
             "'[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND revisit <= ? ORDER BY revisit", code, wk.cut.isoformat())]


def _week_promises(con, code, wk):
    """BL-125 A: the project's open promises as the week ends: {"you_owe": [...], "waiting_on": [...]}, each with its line for
    the Word report (tracker.promise_lists; Waiting on holds only the overdue ones, with how long each has been quiet)."""
    lists = tracker.promise_lists(rows(con, "SELECT * FROM promises WHERE project = ?", code), wk.cut, con)
    keep = ("id", "description", "promised_by", "promised_to", "due_date", "overdue_days", "quiet_days")
    return {k: [{**{f: r[f] for f in keep if f in r}, "line": tracker.promise_line(r, k == "waiting_on")} for r in v]
            for k, v in lists.items()}


def promise_lines(promises):
    """The weekly report's promise lines (BL-125 A): what Alan has promised, for Next Week; what he is waiting on, for Help
    Needed."""
    return ([f"Promised: {r['line']}." for r in promises.get("you_owe", [])],
            [f"Waiting on {r['line']}." for r in promises.get("waiting_on", [])])


def _week_milestones(con, ms):
    import forecast                                        # BL-184: the slip range, for the internal weekly facts only
    likely = forecast.ranges(con, {m["id"] for m in ms})
    return [{"id": m["id"], "name": m["name"], "forecast": m["forecast_date"], "baseline": m["baseline_date"],
             "status": m["status"], "slip_days": m["slip_days"], "percent": m["percent"], "state": m["state"],
             "likely": (likely.get(m["id"]) or {}).get("text")} for m in ms]   # BL-184: internal weekly only
# ===== end BL-229 (weekly_data) =====
def weekly_vip(code, owners):
    """BL-99: VIPs among the owners of the overdue items and top risks, and VIP messages about the project not yet
    seen, so the report reflects them (references only, never message text)."""
    try:
        import propose
        import sweep
        vips = {v["name"]: v["kind"] for v in propose.vip_people()}
        alerts = [{"who": a["who"], "subject": a["subject"], "sent": a["sent"], "marker": a.get("marker")}
                  for a in sweep.vip_state()["alerts"] if sweep.vip_open(a) and a.get("p") == code]
    except Exception:  # noqa: BLE001  VIP facts are a help, never a blocker
        return {"owners": [], "unseen_alerts": []}
    return {"owners": sorted({o: vips[o] for o in owners if o in vips}.items()), "unseen_alerts": alerts}


def flow_line_for(code, week_ending):
    """The week's flow in one line (BL-91), from build_dashboard's measures; "" if they can't be worked out."""
    try:
        import build_dashboard
        return build_dashboard.flow_line(code, date.fromisoformat(str(week_ending)[:10]))
    except Exception:
        return ""


def memory_images(folder):
    """Current-state images as vault-relative paths with captions (BL-12)."""
    text = (folder / "CLAUDE.md").read_text(encoding="utf-8") if (folder / "CLAUDE.md").exists() else ""
    m = re.search(r"^## Current state\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    found = re.findall(r"!\[([^\]]*)\]\(([^)\s]+)\)", m.group(1)) if m else []
    return [{"image": paths.rel(paths.resolve_image(folder, ref)), "caption": alt} for alt, ref in found if paths.resolve_image(folder, ref).is_file()]


def current_entries(folder, text):
    """Current state for the Word report, in order (BL-63): Markdown between images, each image where Alan placed it.
    An image whose file is missing is left out with a note."""
    out, chunk = [], []
    marks = docx_tools.pane_lines(text)                  # a marker inside another comment is text (13-10-2026)
    for n, line in enumerate((text or "").splitlines()):
        if n in marks:       # BL-89: the two panes read as one piece; the marker only separates paragraphs
            chunk.append("")
            continue
        m = docx_tools.IMAGE_LINE.match(line)
        if not m:
            chunk.append(line)
            continue
        if "\n".join(chunk).strip():
            out.append({"md": "\n".join(chunk)})
        chunk = []
        f = paths.resolve_image(folder, m.group(2))
        if f.is_file():
            out.append({"image": paths.rel(f), "caption": m.group(1).strip()})
        else:
            print(f"Note: current-state image not found, left out: {paths.rel(folder)}/{m.group(2)}")
    if "\n".join(chunk).strip():
        out.append({"md": "\n".join(chunk)})
    return out


# ===== BL-229 (v1.7.0): weekly_stage in steps: the refusals, the template's values, the proposal's items and file
# operations, then staging and the printout; messages and the staged proposal unchanged (test_report_builders_pinned.py).
def weekly_stage(spec):
    """Stage a weekly report from cx-weekly-report's spec: the Word draft in system/staging/drafts/ and a proposal (health, the updates
    row, the Current state for the project's CLAUDE.md, filing the report on approval). Returns 3 if it refuses."""
    code = spec["code"]
    data = weekly_data(code, spec.get("week_ending"))
    con = tracker.connect()
    p, folder, _ = project(con, code)
    fri = data["week_ending"]
    health, reason = spec["health"], spec.get("health_reason", "")
    refusal = _weekly_refusal(data, spec, health, reason)
    if refusal:
        print(refusal)
        return 3
    current = "\n\n".join(_paras(spec.get("current_state"))) or data["current_state"] or "No current state yet."
    memory_path = folder / "CLAUDE.md"
    old = memory_path.read_text(encoding="utf-8")
    new_memory = replace_current(old, current)       # images the text leaves out are kept at the end (BL-63)
    values = _weekly_values(code, p, folder, data, spec, new_memory, health, reason)
    draft = paths.DRAFTS / report_file(fri, "Weekly report", p["name"])
    fill(paths.WEEKLY_TEMPLATE, values, draft)
    summary_text = "\n\n".join(values["SUMMARY"])
    items = _weekly_items(con, code, p, fri, spec, health, reason, summary_text)
    reports = paths.rel(paths.folder(code, "weekly_reports") / report_file(fri, "Weekly report", p["name"]))
    ops = ([{"op": "write", "path": paths.rel(memory_path), "content": new_memory, "previous": old}] if new_memory != old else []) + \
        [{"op": "copy", "from": "draft", "to": reports}, {"op": "remove", "path": paths.rel(draft)}]
    out = stage(f"weekly-{code}", {
        "created": sweep.now().strftime("%Y-%m-%dT%H:%M:00"), "source_run": "cx-weekly-report", "files": [],
        "items": items, "report": {"kind": "weekly", "title": f"{p['name']} weekly report, week ending {tracker.shown(fri)}",
                                   "project": code, "projects": [code], "week_ending": fri, "draft": paths.rel(draft),
                                   "report_decision": "pending", "file_ops": ops,
                                   "health": health, "health_reason": reason, "summary": summary_text,
                                   "current_state": current}})
    print(f"Staged {paths.rel(out)}: {p['name']} weekly report, week ending {tracker.shown(fri)}")
    print(f"Draft: {paths.rel(draft)}")
    print(f"Health: {health} — {reason}" + ("" if health == data["suggested_health"] else
                                           f"  (the criteria suggest {data['suggested_health']})"))
    if ops and ops[0]["op"] == "write":
        print("Current state: rewritten in the project's CLAUDE.md on approval.")
    return 0


def _paras(x):
    """A list as it is; text split into its paragraphs."""
    return x if isinstance(x, list) else [t for t in re.split(r"\n\s*\n", x or "") if t.strip()]


def _weekly_refusal(data, spec, health, reason):
    """Why the report can't be staged yet, or None: items awaiting review, already filed, or health better than the
    evidence with no reason given (BL-52)."""
    if data["blocked"] and not spec.get("force"):
        return f"{data['name']} has {data['blocked']} item{'s' if data['blocked'] > 1 else ''} awaiting review — review first."
    if data["already_filed"]:
        return f"{data['name']}'s weekly report for week ending {tracker.shown(data['week_ending'])} is already filed."
    if HEALTH_RANK.get(health, 0) < HEALTH_RANK.get(data["suggested_health"], 0) and not reason.strip():   # BL-52
        return (f"{data['name']}: health {health} is better than the evidence suggests ({data['suggested_health']}: "
                f"{'; '.join(data['reasons'])}). Give a health_reason saying why.")
    return None


def _weekly_values(code, p, folder, data, spec, new_memory, health, reason):
    """The weekly template's values."""
    fri = data["week_ending"]
    owe, waiting = promise_lines(data.get("promises") or {})          # BL-125 A
    return {
        "PROJECT_CODE": code, "PROJECT_NAME": p["name"],
        "STATUS_LINE": f"Draft, generated by creaite on {long_date(today().isoformat())}. Not yet reviewed.",
        "WEEK_ENDING": long_date(fri), "HEALTH_LINE": [{"flag": health.upper(), "text": reason}],
        "SUMMARY": _paras(spec.get("summary")) or ["No change this week."],
        "CURRENT_STATE": current_entries(folder, saved_current(new_memory)) or [{"md": "No current state yet."}],   # BL-63
        "IMAGES": "",                                # images now sit inside Current state where they were placed
        "PROGRESS": ([f"Flow: {data['flow']}."] if data.get("flow") else []) + list(spec.get("progress", [])),   # BL-91
        "NEXT_WEEK": owe + list(spec.get("next_week", [])),
        "MILESTONES": [{"M_TEXT": m["name"], "M_DATE": tracker.shown(m["forecast"]) or "Not set", "M_PCT": pct(m),
                        "M_BASE": tracker.shown(m["baseline"]) or "Not set",
                        "M_STATUS": m["state"]} for m in data["milestones"]],      # BL-186: the five states
        "OVERDUE": [{"O_ID": a["id"], "O_TEXT": a["text"], "O_OWNER": a["owner"], "O_DUE": tracker.shown(a["due"])}
                    for a in data["overdue"]],
        "RISKS": [{"R_ID": r["id"], "R_TEXT": f"{r['type']}: {r['text']}", "R_PRIORITY": r["priority"] or "",
                   "R_OWNER": r["owner"]} for r in data["top_risks"]],
        "DECISIONS": [f"{d['text']} — {d['by'] or 'not recorded'}, {tracker.shown(d['date'])}" for d in data["decisions"]]
                     + [decision_needed_line(d) for d in data["decisions_needed"]],
        "HELP_NEEDED": waiting + list(spec.get("help_needed", [])),
        "SOURCE": f"creaite tracker and project memory, week ending {long_date(fri)}",
    }


def _weekly_items(con, code, p, fri, spec, health, reason, summary_text):
    """The proposal's items: the week's updates row (new, or an update of the one there), and a health change."""
    items = [{"op": "new", "table": "updates", "values": {"week_ending": fri, "project": code, "health": health,
                                                          "summary": summary_text, "key_changes": spec.get("key_changes", "")}}]
    if rows(con, "SELECT 1 FROM updates WHERE week_ending = ? AND project = ?", fri, code):
        items = [{"op": "update", "table": "updates", "id": f"{fri}|{code}",
                  "changes": {"health": health, "summary": summary_text, "key_changes": spec.get("key_changes", "")}}]
    if health != p["health"] or reason != (p["health_reason"] or ""):
        items.append({"op": "update", "table": "projects", "id": code, "based_on": p["updated_at"],
                      "changes": {"health": health, "health_reason": reason}})
    for n, it in enumerate(items, start=1):
        it.update(n=n, match="strong", flags=[], decision="pending")
    return items
# ===== end BL-229 (weekly_stage) =====
def saved_current(md):
    """The Current state text of a CLAUDE.md as it will be saved: guidance lines left out, images in place (BL-63)."""
    m = re.search(r"^## Current state[^\n]*\n(.*?)(?=^## |\Z)", md, re.M | re.S)
    return "\n".join(ln for ln in (m.group(1) if m else "").splitlines() if not re.fullmatch(r"_.*_", ln.strip())).strip()


def replace_current(md, text):
    """The project's CLAUDE.md with its Current state section replaced. Guidance lines are kept; images stay where
    the new text places them (BL-63), and any the new text leaves out are kept at the end, so none is lost."""
    m = re.search(r"(^## Current state[^\n]*\n)(.*?)(?=^## |\Z)", md, re.M | re.S)
    if not m:
        return md.rstrip() + f"\n\n## Current state\n\n{text.strip()}\n"
    # BL-89: a new text without the pane marker keeps the right pane the section already has (the panes are one text, and the
    # right pane is Alan's own writing); a text with the marker is taken as it stands
    old_left, old_right = docx_tools.split_panes(saved_current(md))
    if old_right and not docx_tools.pane_markers(text):
        split = lambda t: [x.strip() for x in re.split(r"\n\s*\n", t.strip()) if x.strip()]   # noqa: E731
        tp, rp = split(text), split(old_right)
        if len(tp) >= len(rp) and tp[len(tp) - len(rp):] == rp:      # the text came back from Word, both panes as one piece:
            text = docx_tools.join_panes("\n\n".join(tp[:len(tp) - len(rp)]), old_right)    # put the marker back where it was
        else:
            text = docx_tools.join_panes(text, old_right)
    lines = m.group(2).splitlines()
    guide = [ln for ln in lines if re.fullmatch(r"_.*_", ln.strip())]
    placed = {im.group(2) for im in map(docx_tools.IMAGE_LINE.match, text.splitlines()) if im}
    images = [ln for ln in lines if ln.strip().startswith("![") and
              (docx_tools.IMAGE_LINE.match(ln) is None or docx_tools.IMAGE_LINE.match(ln).group(2) not in placed)]
    body = m.group(1) + "\n" + ("\n".join(guide) + "\n\n" if guide else "") + text.strip() + "\n" + \
        ("\n" + "\n".join(images) + "\n" if images else "") + "\n"
    return md[:m.start()] + body + md[m.end():]


# ── Client ────────────────────────────────────────────────────────────────────

def message_parts(msg):
    """A client message split by its headings (What it is, What it means for you, What is being done): {heading: text}."""
    parts = {}
    for line in (msg or "").splitlines():
        for h in HEADINGS:
            if line.strip().startswith(h):
                parts[h] = line.strip()[len(h):].strip()
    return parts


def client_text(msg):
    """Client messaging as one client-facing sentence group."""
    p = message_parts(msg)
    return " ".join(x.rstrip(".") + "." for x in (p.get(h) for h in HEADINGS) if x)


# ===== BL-229 (v1.7.0): client_data in gather and shape steps. The keys, their order, and the order items join
# "needs_client_messaging" (actions, decisions, risks) are unchanged (test_report_builders_pinned.py, test_reports.py).
def client_data(code, since=None):
    """The facts a client report is drafted from (the client-data command): the period since the last one (or `since`), client-visible
    milestones, actions, decisions and risks, what still needs client messaging and what is left out. Read only."""
    con = tracker.connect()
    p, folder, mem = project(con, code)
    client = mem["client"] or ""
    last, start = _client_period(code, since)
    needs = []
    theirs, ours = _client_actions(con, code, client, start, needs)
    decisions = _client_decisions(con, code, start, needs)
    risks = _client_risks(con, code, needs)
    excluded = [f"{r['id']} {r['type']}: {r['description']} ({r['priority']})" for r in
                rows(con, "SELECT * FROM raid WHERE project = ? AND client_visible = 0 AND status = 'Open' AND "
                          "priority IN ('Urgent', 'High')", code)]
    memory_text = (folder / "CLAUDE.md").read_text(encoding="utf-8") if (folder / "CLAUDE.md").exists() else ""
    return {
        "code": code, "name": p["name"], "client": client, "last_client_report": last,
        "period_start": start, "period_end": today().isoformat(), "needs_start_date": start is None,
        "blocked": pending_for(code), "health": p["health"], "health_reason": p["health_reason"],
        "milestones": [{"name": m["name"], "date": m["forecast_date"], "status": m["status"], "slip_days": m["slip_days"],
                        "percent": m["percent"], "state": m["client_word"], "shown_date": client_date(m)}
                       for m in tracker.client_milestones(milestones(con, code))],   # BL-186: client-visible ones, in the client's words
        "client_actions": theirs, "our_commitments": ours, "decisions": decisions, "risks": risks,
        "needs_client_messaging": needs, "excluded_high_risks": excluded,
        "client_safe_no": [ln.strip() for ln in memory_text.splitlines() if "Client-safe: no" in ln],
    }


def _client_period(code, since):
    """(the last client report's date, the period's start): `since`, else the day after the last report, else None."""
    cdir = paths.folder(code, "client_reports")
    last = max((f.name[:10] for f in cdir.glob("* Client report*") if f.suffix in (".docx", ".html")), default=None) \
        if cdir.exists() else None                                                     # v2.1.0 P3: a creaite client report too
    start = since or ((date.fromisoformat(last) + timedelta(days=1)).isoformat() if last else None)
    return last, start


def _is_client_owner(owner, client):
    """True when an owner's "(Company)" is the client's."""
    org = (re.search(r"\(([^)]+)\)\s*$", owner or "") or [None, ""])[1]
    return bool(client and org and (org.lower() in client.lower() or client.lower().split()[0] in org.lower()))


_CLIENT_STATUS = {"Open": "In progress", "Delayed": "Delayed", "Closed": "Complete", "Cancelled": "Cancelled"}


def _client_actions(con, code, client, start, needs):
    """(the client's actions, our commitments): client-visible, complete messaging; the rest join `needs`."""
    theirs, ours = [], []
    for a in rows(con, "SELECT * FROM actions WHERE project = ? AND client_visible = 1", code):
        if a["status"] == "Cancelled" or (a["status"] == "Closed" and start and (a["closed"] or "") < start):
            continue
        if not tracker.message_complete("actions", a["client_message"]):
            needs.append(f"{a['id']} {a['description']}")
            continue
        row = {"id": a["id"], "text": message_parts(a["client_message"]).get(HEADINGS[0]) or a["description"],
               "owner": a["owner"], "due": a["due_date"], "status": _CLIENT_STATUS[a["status"]]}
        (theirs if _is_client_owner(a["owner"], client) else ours).append(row)
    return theirs, ours


def _client_decisions(con, code, start, needs):
    """Client-visible decisions made in the period, and pending ones (BL-53)."""
    out = []
    for d in rows(con, "SELECT * FROM decisions WHERE project = ? AND client_visible = 1 AND status IN ('Made', 'Pending') "
                       "ORDER BY COALESCE(date, needed_by, '9999'), id", code):         # BL-53: a pending one shows only if client-visible
        if start and d["status"] == "Made" and d["date"] < start:
            continue
        if tracker.message_complete("decisions", d["client_message"]):
            out.append({"id": d["id"], "text": d["client_message"].strip(), "date": d["date"], "status": d["status"],
                        "needed_by": d["needed_by"]})
        else:
            needs.append(f"{d['id']} {d['decision']}")
    return out


def _client_risks(con, code, needs):
    out = []
    for r in rows(con, "SELECT * FROM raid WHERE project = ? AND client_visible = 1 AND status = 'Open'", code):
        if tracker.message_complete("raid", r["client_message"]):
            out.append({"id": r["id"], "type": r["type"], "text": client_text(r["client_message"])})
        else:
            needs.append(f"{r['id']} {r['description']}")
    return out
# ===== end BL-229 (client_data) =====
def client_stage(spec):
    """Stage a client report from cx-client-report's spec: the Word draft in system/staging/drafts/ and a proposal that files it in the
    project's reports folder on approval. Never sends. Returns 3 when it needs a start date or items await review."""
    code = spec["code"]
    data = client_data(code, spec.get("period_start"))
    if data["needs_start_date"]:
        print(f"This is {data['name']}'s first client report: give the period's start date (period_start).")
        return 3
    if data["blocked"] and not spec.get("force"):
        print(f"{data['name']} has {data['blocked']} item{'s' if data['blocked'] > 1 else ''} awaiting review — review first, "
              f"or go ahead anyway (force).")
        return 3
    con = tracker.connect()
    p, folder, _ = project(con, code)
    end = data["period_end"]
    values = {
        "PROJECT_NAME": p["name"], "CLIENT_NAME": data["client"] or "Client",
        "STATUS_LINE": f"Draft, generated by creaite on {long_date(today().isoformat())}. Not yet reviewed.",
        "PERIOD_START": long_date(data["period_start"]), "PERIOD_END": long_date(end),
        "REPORT_DATE": f"Report date: {long_date(end)}",
        "HEALTH_LINE": [{"flag": (data["health"] or "On track").upper(), "text": data["health_reason"] or ""}],
        "SUMMARY": spec.get("summary") or ["No significant change in this period."],
        "PROGRESS": spec.get("progress", []),
        "MILESTONES": [{"M_TEXT": m["name"], "M_DATE": m["shown_date"], "M_PCT": pct(m),
                        "M_STATUS": m["state"]}                  # BL-186: the client's words for the five states
                       for m in data["milestones"]],
        "C_ROWS": [{"C_TEXT": a["text"], "C_OWNER": a["owner"], "C_DUE": tracker.shown(a["due"]) or "Not set"}
                   for a in data["client_actions"]],
        "U_ROWS": [{"U_TEXT": a["text"], "U_OWNER": a["owner"], "U_DUE": tracker.shown(a["due"]) or "Not set"}
                   for a in data["our_commitments"]],
        "DECISIONS": [f"{d['text']} ({tracker.shown(d['date'])})" if d.get("status", "Made") == "Made" else
                      f"Decision needed: {d['text']}" + (f" (by {tracker.shown(d['needed_by'])})" if d.get("needed_by") else "")
                      for d in data["decisions"]],
        "CLIENT_RISKS": [f"{r['type']}: {r['text']}" for r in data["risks"]],
        "NEXT_STEPS": spec.get("next_steps", []), "INPUT_NEEDED": spec.get("input_needed", []),
    }
    draft = paths.DRAFTS / report_file(end, "Client report", p["name"])
    fill(paths.CLIENT_TEMPLATE, values, draft)
    out = stage(f"client-{code}", {
        "created": sweep.now().strftime("%Y-%m-%dT%H:%M:00"), "source_run": "cx-client-report", "files": [], "items": [],
        "report": {"kind": "client", "title": f"{p['name']} client report, {tracker.shown(data['period_start'])} to "
                                              f"{tracker.shown(end)}", "project": code, "projects": [code],
                   "draft": paths.rel(draft), "report_decision": "pending",
                   "file_ops": [{"op": "copy", "from": "draft",
                                 "to": paths.rel(paths.folder(code, "client_reports") / report_file(end, "Client report", p["name"]))},
                                {"op": "remove", "path": paths.rel(draft)}]}})
    print(f"Staged {paths.rel(out)}: {p['name']} client report, {tracker.shown(data['period_start'])} to {tracker.shown(end)}")
    print(f"Draft: {paths.rel(draft)}")
    print("Included (client-visible): " + (", ".join([a["id"] for a in data["client_actions"] + data["our_commitments"]]
                                                       + [d["id"] for d in data["decisions"]] + [r["id"] for r in data["risks"]])
                                           or "none"))
    for n in data["needs_client_messaging"]:
        print(f"Needs your client messaging (left out): {n}")
    for x in data["excluded_high_risks"]:
        print(f"Not client-visible, so left out: {x}")
    return 0


CONTEXT_SOURCES = ("tracker", "minutes", "reports", "updates", "swept")   # documents: only when asked (passive)


def style_guide(forms=False):
    """The executive voice (BL-106): one file that every status prompt reads. Its "## Forms" section (BL-227) is for the other
    forms only, so the Current state's guide is left as it was unless `forms` asks for it."""
    text = (paths.TEMPLATES / "executive-style.md").read_text(encoding="utf-8")
    return (text if forms else text.split("\n## Forms (BL-227)")[0]).strip()


# BL-227 (sprint-drafts-writing): the audience line of a Current state's material; steering and sponsor get internal wording with
# nothing sensitive (status_facts leaves those lines out of their sheet).
AUDIENCE_NOTES = {
    "internal": "Audience: internal. Be candid; lines marked `Client-safe: no` may be used.",
    "client": "Audience: client-safe. Use only the facts below, which hold only items marked client-visible, in their client wording. "
              "Nothing internal.",
    "steering": "Audience: the steering committee. Internal wording, decisions and asks first; the facts below hold nothing confidential, "
                "restricted or marked `Client-safe: no`, and nothing else from the vault may add it.",
    "sponsor": "Audience: the sponsor. Internal wording, the position and what is needed from the sponsor first; the facts below hold "
               "nothing confidential, restricted or marked `Client-safe: no`, and nothing else from the vault may add it.",
}

AUDIENCE_SOURCES = {"client": ("reports",), "steering": ("reports", "updates"), "sponsor": ("reports", "updates")}


# ===== BL-229 step 4: current_context in gather and shape steps: the opening (guide, audience, facts, the Current state's
# panes), then one section per source, in the order the single function wrote them (test_report_builders_pinned.py).
def current_context(code, start=None, end=None, sources=CONTEXT_SOURCES, audience="internal", length="standard"):
    """What a Current state draft may draw on, for one project and period, from the vault only (BL-46). BL-106: it opens
    with the writing guide, the audience and length, and the ranked facts sheet; the open lists and files come after as
    reference. A client-safe context holds nothing internal: no open lists, minutes, updates, swept items or documents,
    and only client reports."""
    import status_facts
    client = audience == "client"
    if audience not in AUDIENCE_NOTES:                                  # BL-227: steering committee and sponsor too
        raise ValueError("audience must be internal, client, steering or sponsor")
    words = status_facts.settings()["length_words"]
    if length not in words:
        raise ValueError(f"length must be one of {', '.join(words)}")
    sources = tuple(s for s in sources if s in AUDIENCE_SOURCES.get(audience, sources))   # client, steering, sponsor: less
    con = tracker.connect()
    p, folder, mem = project(con, code)
    end = end or today().isoformat()
    start = start or (date.fromisoformat(end) - timedelta(days=7)).isoformat()
    period = _Period(start, end)
    out = _context_opening(code, p, mem, period, audience, length, words, status_facts)
    if "tracker" in sources:
        out += _context_tracker(con, code, period)
    out += _context_files(code, sources, client, period)
    if "updates" in sources:
        out += _context_updates(con, code, period)
    if "swept" in sources:
        out += _context_swept(code, period)
    out += _context_last_sweep()
    return "\n".join(out)


class _Period:
    """The context's period: whether a date (or a dated file name) falls in it."""

    def __init__(self, start, end):
        self.start, self.end = start, end

    def holds(self, d):
        """Whether the date (or the date at the start of a timestamp) falls in the period."""
        return bool(d) and self.start <= d[:10] <= self.end

    def holds_file(self, f):
        """Whether a file named `YYYY-MM-DD …` is dated in the period."""
        m = re.match(r"(\d{4}-\d{2}-\d{2})", f.name)
        return bool(m) and self.holds(m.group(1))


def _context_opening(code, p, mem, period, audience, length, words, status_facts):
    """The project line, the writing guide, the audience and length, the ranked facts, and the Current state's panes."""
    out = [f"Project: {code} {p['name']}. Period: {tracker.shown(period.start)} to {tracker.shown(period.end)}.",
           f"Health now: {p['health'] or 'not set'}{' — ' + p['health_reason'] if p['health_reason'] else ''}.",
           ""]
    facts = status_facts.facts(code, period.start, period.end, audience)
    out += ["## Writing guide (follow it)", style_guide(), "",
            "## Audience and length",
            AUDIENCE_NOTES[audience],
            f"Length: {length.capitalize()}, about {words[length]} words.", "",
            "## Facts (ranked; write the status from these)", facts["text"], "",
            "## Reference material (the facts above come first; use these only to explain a fact, never to report item by item)", ""]
    left, right = docx_tools.split_panes(mem["current"])       # BL-89: two panes, one message; only the left is drafted
    if audience == "client":                                    # #127: no link to an item a client may not see, words or address
        import client_leak
        left, right = (client_leak.drop_item_links(code, x) if x else x for x in (left, right))
    out += ["## Current state now: the left pane (the part you draft)", left or "(none yet)"]
    if right:
        out += ["", "## Current state now: the right pane (Alan's own writing; read it as part of what is already said)", right]
    return out


def _context_tracker(con, code, period):
    """The tracker's changes in the period, then the open actions, the open RAID items and the milestones."""
    return _context_changes(con, code, period) + _context_open(con, code, period) + _context_milestones(con, code)


def _context_changes(con, code, period):
    ch = rows(con, "SELECT at, tbl, item_id, field, old_value, new_value, op FROM change_log WHERE substr(at,1,10) "
                   "BETWEEN ? AND ? AND (item_id = ? OR item_id LIKE ? OR item_id LIKE ?) AND field NOT IN "
                   "('updated_at','source','client_message') AND tbl != 'rejected' ORDER BY rowid", period.start, period.end, code,
              f"{code}-%", f"%|{code}")
    made = {c["item_id"]: c["new_value"] for c in ch if c["op"] == "insert" and c["field"] in ("description", "decision",
                                                                                                "name", "summary")}
    return ["", "## Tracker changes in the period"] + \
        [f"- {tracker.shown(c['at'][:10])} {c['item_id']} "
         + (f"created: {made.get(c['item_id'], '')}" if c["op"] == "insert"
            else f"{c['field']}: {c['old_value'] or '—'} → {c['new_value'] or '—'}")
         for c in ch if c["op"] != "insert" or c["field"] in ("id", "code", "week_ending")] or ["- none"]


def _context_open(con, code, period):
    acts = rows(con, "SELECT * FROM actions WHERE project = ? AND status IN ('Open','Delayed') ORDER BY due_date", code)
    risks = rows(con, "SELECT * FROM raid WHERE project = ? AND status = 'Open'", code)
    out = ["", "## Open actions"] + [f"- {a['id']} {a['description']} — {a['owner']}, due {tracker.shown(a['due_date']) or 'not set'}"
                                     + (" (overdue)" if a["due_date"] and a["due_date"] < period.end else "") for a in acts] or []
    return out + ["", "## Open risks, issues, assumptions and dependencies"] + \
        [f"- {r['id']} {r['type']}, {r['priority'] or 'priority not set'}: {r['description']}"
         + (f" — response: {r['response_action']}" if r["response_action"] else " — no response yet") for r in risks]


def _context_milestones(con, code):
    return ["", "## Milestones"] + [f"- {m['name']}: forecast {tracker.shown(m['forecast']) or 'not set'}, baseline "
                                    f"{tracker.shown(m['baseline']) or 'not set'}, {m['state']}"
                                    + (f", {m['percent']}% complete" if m.get("percent") is not None else "")
                                    for m in [{**x, "forecast": x["forecast_date"], "baseline": x["baseline_date"]}
                                              for x in milestones(con, code)]]


def _context_files(code, sources, client, period):
    """The files to read: meetings and reports dated in the period (client: client reports only), and documents if asked."""
    files = []
    if "minutes" in sources:
        files += [f for d in paths.extract_dirs(code) if d.is_dir() for f in sorted(d.glob("*")) if period.holds_file(f)]
    if "reports" in sources:
        rdirs = {d.resolve(): d for d in (paths.folder(code, "weekly_reports"), paths.folder(code, "client_reports")) if d.is_dir()}
        files += [f for d in rdirs.values() for f in sorted(d.glob("*")) if period.holds_file(f)
                  and (not client or "client report" in f.name.lower())]
    if "documents" in sources:
        files += paths.document_files(code)
    return ["", "## Files to read (paths in the vault)"] + ([f"- {paths.rel(f)}" for f in files] or ["- none in the period"])


def _context_updates(con, code, period):
    ups = rows(con, "SELECT * FROM updates WHERE project = ? AND week_ending BETWEEN ? AND ? ORDER BY week_ending", code,
               period.start, period.end)
    return ["", "## Weekly updates"] + ([f"- week ending {tracker.shown(u['week_ending'])}, {u['health']}: {u['summary']}"
                                         for u in ups] or ["- none"])


def _context_swept(code, period):
    """Items the sweep proposed for this project in the period, staged or applied."""
    swept = []
    for f in sorted(paths.STAGING.glob("proposed-*.json")) + sorted(paths.APPLIED.glob("proposed-*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        if data.get("source_run") != "cx-sweep":
            continue
        for it in data.get("items", []):
            v = it.get("values") or {}
            if (v.get("project") or "") == code and period.holds(v.get("raised") or data.get("created", "")):
                swept.append(f"- {v.get('description') or v.get('decision') or ''} (from {v.get('source', '')[:120]})")
    return ["", "## Items already swept from mail and Teams"] + (swept or ["- none"])


def _context_last_sweep():
    last = paths.SWEEP_STATE.read_text(encoding="utf-8").strip().splitlines()[0] if paths.SWEEP_STATE.exists() and \
        paths.SWEEP_STATE.read_text(encoding="utf-8").strip() else None
    return ["", f"Last mail and Teams sweep: {tracker.shown(last[:10]) + last[10:16] if last else 'never'}."]
# ===== end BL-229 step 4 (current_context) =====


# ===== Steering one-pager (BL-92, sprint 5) =====
# A Word one-pager for a project's steering committee, from the tracker, drafted for approval like the weekly and client
# reports and filed on approval into the project's Steerco folder (never overwriting). Two versions: internal (everything,
# sensitive items marked) and client-safe (the client-report rules: only client-visible items with complete messaging, their
# client wording, no flow, and nothing carrying a label that excludes it unless Alan includes it).

STEERCO_SECTIONS = ("What Changed", "Milestones", "Top Risks and Issues", "Decisions Needed", "Blockers", "Flow", "Next Period")
STEERCO_CAPS = {"changes": 8, "milestones": 7, "risks": 5, "decisions": 6, "blockers": 6, "next": 8}
STEERCO_WINDOW_DAYS = 14               # the next period: actions overdue or due within this many days
STEERCO_FIRST_DAYS = 14                # with no earlier one-pager: what changed in this many days


def last_steerco(code):
    """The date of the project's latest filed one-pager (either version) in its Steerco folder, or None."""
    d = paths.folder(code, "steerco")
    found = sorted(f.name[:10] for f in d.glob("* Steerco one-pager*.docx") if re.match(r"\d{4}-\d{2}-\d{2} ", f.name)) if d.is_dir() else []
    return found[-1] if found else None


def project_labels(con, code):
    """({item ID: [labels]}, {item ID: [labels]} for those carrying a label that excludes it from client output) for a project's items."""
    every, excluded = {}, {}
    try:
        found = con.execute("SELECT il.item_id, il.label, l.behaviour, l.default_choice FROM item_labels il JOIN labels l ON l.name = il.label "
                            "WHERE il.item_id LIKE ? ORDER BY il.label COLLATE NOCASE", (f"{code}-%",)).fetchall()
    # ===== BL-228 (sprint-debt-safety) =====  A: only a database without the labels tables has none; any other error stops
    except Exception as e:  # noqa: BLE001  the client-safe one-pager must never be built without its label check
        import review
        if review.labels_missing(con, e):
            return {}, {}
        debuglog.warn("report", f"label lookup failed for {code}: {type(e).__name__}")
        sys.exit(f"creaite: couldn't read the labels for {code} ({type(e).__name__}: {e}), so the one-pager can't be checked "
                 "for items a label excludes. Nothing was written.")
    # ===== end BL-228 =====
    for item_id, label, behaviour, default in found:
        every.setdefault(item_id, []).append(label)
        if behaviour == "exclude" or default == "exclude":
            excluded.setdefault(item_id, []).append(label)
    return every, excluded


# ===== BL-225 (sprint-drafts-fields) ===== the client-safe context for one item's client wording: only the item's own words
# (its title and its latest update, response or reasoning), never its source, other items, the project's internal notes or the
# people around it. A confidential or restricted item (a label that keeps it out of client output, or those words in its text or
# source) is refused. Read only.
CLIENT_SHAPE = {"actions": "Three short lines, each starting with its heading: \"What it is: \", \"What it means for you: \", \"What is being done: \".",
                "raid": "Three short lines, each starting with its heading: \"What it is: \", \"What it means for you: \", \"What is being done: \".",
                "decisions": "Two or three plain sentences, no headings."}


def client_item_context(con, item_id):
    """One item's text and the shape of its client wording, for drafting that wording (BL-225). Raises drafts.Refused for an item of
    another kind, not in the tracker, labelled out of client output, or confidential."""
    import drafts
    table = tracker.item_table(item_id)
    if table not in CLIENT_SHAPE:
        raise drafts.Refused("Client wording is drafted for actions, RAID items and decisions.")
    row = con.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
    if not row:
        raise drafts.Refused(f"{item_id} isn't in the tracker.")
    x = dict(row)
    _, excluded = project_labels(con, x["project"])
    if item_id in excluded:
        raise drafts.Refused(f"{item_id} is labelled {', '.join(excluded[item_id])}: client wording isn't drafted for it.")
    title = x.get("description") if table != "decisions" else x.get("decision")
    more = {"actions": x.get("latest_update"), "raid": x.get("response_action"), "decisions": x.get("reasoning")}[table]
    if drafts.secret(f"{title} {more or ''} {x.get('source') or ''}"):
        raise drafts.Refused(f"{item_id} is marked confidential or restricted: client wording isn't drafted for it.")
    kind = {"actions": "action", "raid": (x.get("type") or "risk").lower(), "decisions": "decision"}[table]
    text = title.strip() + (f"\n{({'actions': 'Latest update', 'raid': 'Response', 'decisions': 'Reasoning'})[table]}: {more.strip()}" if more and more.strip() else "")
    return {"id": item_id, "table": table, "kind": kind, "text": text, "shape": CLIENT_SHAPE[table]}
# ===== end BL-225 =====


def is_me(name):
    """Whether a name is Alan's own (settings.json identity: his name or a short form)."""
    ident = paths.load_settings().get("identity") or {}
    mine = {str(n).strip().lower() for n in [ident.get("name"), *(ident.get("short_forms") or [])] if n}
    return bool(name) and str(name).strip().lower() in mine


def run_lengths(seq):
    """Runs of equal neighbours: [[value, how many in a row], …]."""
    out = []
    for w in seq:
        if out and out[-1][0] == w:
            out[-1][1] += 1
        else:
            out.append([w, 1])
    return out


# ===== BL-229 step 4: steerco_data in gather and shape steps. _Steerco carries what every section shares (the client-safe
# rule, the wording, the label tags, the items shown and those left out); each section is its own builder, called in the
# order the single function ran them, so the output is unchanged (dev/tests/test_report_builders_pinned.py).
class _Steerco:
    def __init__(self, con, code, client, include, on, start):
        self.con, self.code, self.client, self.include, self.on, self.start = con, code, client, include, on, start
        self.every, self.excluded = project_labels(con, code)
        self.omitted = []
        self.shown_ids = []                                # items that appear, for the sensitive count
        ms = milestones(con, code)
        self.ms = tracker.client_milestones(ms) if client else ms      # BL-186: the client filter, as in the client report
        self.names = {m["id"]: m["name"] for m in self.ms}

    def usable(self, table, row):
        """The client-safe rule for one item: client-visible, complete messaging, not excluded by a label (unless included)."""
        if not self.client:
            return True
        if not row["client_visible"]:
            return False
        if not tracker.message_complete(table, row["client_message"]):
            self.omitted.append(f"{row['id']} needs its client messaging completed")
            return False
        if row["id"] in self.excluded and row["id"] not in self.include:
            self.omitted.append(f"{row['id']} is flagged client-visible and labelled {', '.join(self.excluded[row['id']])}: left out "
                                f"(say \"include {row['id']}\" to keep it)")
            return False
        return True

    def text(self, table, row, field):
        """An item's text for the one-pager: as recorded, or its client wording in the client-safe version."""
        if not self.client:
            return row[field]
        if table == "decisions":
            return row["client_message"].strip()
        if table == "raid":
            return client_text(row["client_message"])
        return message_parts(row["client_message"]).get(HEADINGS[0]) or row[field]

    def tag(self, item_id):
        """The item's labels as " [label, …]" in the internal version; '' otherwise."""
        return f" [{', '.join(self.every[item_id])}]" if not self.client and item_id in self.every else ""

    def see(self, item_id):
        """Note that an item is shown (for the sensitive count) and return its ID."""
        self.shown_ids.append(item_id)
        return item_id


def _steer_trend(con, code, on):
    """Health is in the heading line; the text adds the trend over the weekly updates."""
    words = {"ok": "On track", "warn": "At risk", "bad": "Off track"}
    seq = [words[t] for t in build_dashboard.trail(con, code, on) if t]
    if len(seq) >= 2:
        return f"Over the last {len(seq)} weekly updates: " + " → ".join(f"{w} ({n})" if n > 1 else w for w, n in run_lengths(seq)) + "."
    return ("One weekly update so far: " + seq[0] + ".") if seq else ""


def _steer_changes(st):
    """What changed since the last steering: milestones moved, new risks and issues, decisions made, items closed."""
    con, code, start, client = st.con, st.code, st.start, st.client
    changes = []
    moved = rows(con, "SELECT item_id, old_value, new_value FROM change_log c WHERE c.tbl = 'milestones' AND c.field = 'forecast_date' AND "
                      "c.op = 'update' AND c.old_value IS NOT NULL AND substr(c.at, 1, 10) >= ? AND c.item_id LIKE ? AND "
                      + build_dashboard.NOT_UNDONE + " ORDER BY c.at", start, f"{code}-M-%")
    for m in moved:
        if m["item_id"] not in st.names:               # BL-186: a cancelled, or (client-safe) a hidden, milestone
            continue
        changes.append(f"Milestone moved: {st.names.get(m['item_id'], m['item_id'])}, {tracker.shown(m['old_value'])} → {tracker.shown(m['new_value'])}")
    for r in rows(con, "SELECT * FROM raid WHERE project = ? AND type IN ('Risk', 'Issue') AND raised >= ? ORDER BY raised, id", code, start):
        if st.usable("raid", r):
            changes.append(f"New {r['type'].lower()}: {st.see(r['id']) + ' ' if not client else ''}{st.text('raid', r, 'description')}{st.tag(r['id'])}")
    for d in rows(con, "SELECT * FROM decisions WHERE project = ? AND status = 'Made' AND date >= ? ORDER BY date, id", code, start):
        if st.usable("decisions", d):
            changes.append(f"Decided: {st.text('decisions', d, 'decision')}{st.tag(d['id'])}" + (f" ({d['made_by']})" if d["made_by"] and not client else ""))
            st.see(d["id"])
    for table, label in (("actions", "Closed"), ("raid", "Resolved")):
        for r in rows(con, f"SELECT * FROM {table} WHERE project = ? AND status = 'Closed' AND closed >= ? ORDER BY closed, id", code, start):
            if table == "raid" and r["type"] not in ("Risk", "Issue", "Dependency"):
                continue
            if st.usable(table, r):
                changes.append(f"{label}: {st.text(table, r, 'description')}{st.tag(r['id'])}")
                st.see(r["id"])
    return _capped(changes, "changes")


def _capped(items, cap):
    n = len(items)
    return items[:STEERCO_CAPS[cap]] + ([f"+{n - STEERCO_CAPS[cap]} more in the tracker"] if n > STEERCO_CAPS[cap] else [])


def _steer_milestones(st):
    """The last two done, then those still to come, the nearest first."""
    done = [m for m in st.ms if m["status"] == "Done"][-2:]
    ahead = [m for m in st.ms if m["status"] == "Planned"]
    out = []
    for m in (done + ahead)[:STEERCO_CAPS["milestones"]]:
        status = m["client_word"] if st.client else m["state"]           # BL-186: one vocabulary
        out.append({"M_TEXT": m["name"], "M_DATE": (client_date(m) if st.client else tracker.shown(m["forecast_date"])) or "Not set",
                    "M_BASE": tracker.shown(m["baseline_date"]) or "Not set", "M_STATUS": status})
    return out


def _steer_risks(st):
    """The open risks and issues, highest priority first."""
    risks = []
    for r in sorted(rows(st.con, "SELECT * FROM raid WHERE project = ? AND status = 'Open' AND type IN ('Risk', 'Issue')", st.code),
                    key=lambda r: ORDER.index(r["priority"] or "Low")):
        if not st.usable("raid", r):
            continue
        if st.client:
            risks.append({"R_ID": "—", "R_TEXT": f"{r['type']}: {st.text('raid', r, 'description')}", "R_PRIORITY": "—", "R_OWNER": "—"})
        else:
            response = (r["response_action"] or "").strip()
            risks.append({"R_ID": st.see(r["id"]), "R_TEXT": f"{r['type']}: {r['description']}{st.tag(r['id'])}. "
                          + (f"Response: {response}" if response else "No response yet."),
                          "R_PRIORITY": r["priority"] or "", "R_OWNER": r["owner"]})
    return risks[:STEERCO_CAPS["risks"]]


def _steer_needed(st):
    """Decisions needed (BL-53), from the committee and from Alan."""
    needed = []
    for d in rows(st.con, "SELECT * FROM decisions WHERE project = ? AND status = 'Pending' ORDER BY COALESCE(needed_by, '9999'), id", st.code):
        if not st.usable("decisions", d):
            continue
        late = (st.on - date.fromisoformat(d["needed_by"])).days if d["needed_by"] else 0
        when = (f", needed by {tracker.shown(d['needed_by'])}" if d["needed_by"] else "") + (f" ({late} day{'s' if late != 1 else ''} overdue)" if late > 0 else "")
        if st.client:
            needed.append(f"{st.text('decisions', d, 'decision')}" + (f" (by {tracker.shown(d['needed_by'])})" if d["needed_by"] else ""))
        else:
            who = "For Alan" if is_me(d["made_by"]) else "For the committee"
            needed.append(f"{who}: {d['decision']}{st.tag(d['id'])} — {('from ' + d['made_by']) if d['made_by'] else 'no one asked yet'}{when}")
            st.see(d["id"])
    return needed[:STEERCO_CAPS["decisions"]]


def _steer_dependencies(st):
    """Blockers (BL-90), part one: open dependencies attached to a milestone."""
    out = []
    warn = {w["id"]: w["text"] for w in build_dashboard.early_warnings(paths.load_settings(), st.on) if w.get("sig") == "dependency"}
    for r in rows(st.con, "SELECT * FROM raid WHERE project = ? AND type = 'Dependency' AND status = 'Open' AND milestone IS NOT NULL ORDER BY due_date, id", st.code):
        if not st.usable("raid", r):
            continue
        what = st.names.get(r["milestone"]) or ("a milestone" if st.client else r["milestone"])   # BL-186: never a hidden milestone's ID
        fc = next((m["forecast_date"] for m in st.ms if m["id"] == r["milestone"]), None)
        if st.client:
            out.append(f"{st.text('raid', r, 'description')}: waiting on this for {what}")
        else:
            out.append(f"{st.see(r['id'])} {r['description']}{st.tag(r['id'])} ({r['owner']}" + (f", due {tracker.shown(r['due_date'])}" if r["due_date"] else "")
                       + f") blocks {what}" + (f" (forecast {tracker.shown(fc)})" if fc else "") + (f". {warn[r['id']]}" if r["id"] in warn else ""))
    return out


_BLOCK_LABEL = {"actions": ("description", ("Open", "Delayed")), "raid": ("description", ("Open",)), "promises": ("description", ("Open",)),
                "decisions": ("decision", ("Pending",)), "milestones": ("name", ("Planned",))}


def _steer_links(st):
    """Blockers (BL-90), part two: the links table's "blocks", internal version only, while the blocker is still open."""
    def item_text(item_id):
        """(row, "ID text") for a linked item in a table the blockers cover; (None, the ID) otherwise."""
        table = tracker.item_table(item_id)
        row = tracker.fetch(st.con, table, item_id) if table in _BLOCK_LABEL else None
        return (row, f"{item_id} {row[_BLOCK_LABEL[table][0]]}") if row else (None, item_id)
    try:
        links = rows(st.con, "SELECT * FROM links WHERE kind = 'blocks' AND (from_item LIKE ? OR to_item LIKE ?) ORDER BY from_item, to_item",
                     f"{st.code}-%", f"{st.code}-%")
    except Exception:
        links = []
    out = []
    for k in links:
        (frm, ftext), (to, ttext) = item_text(k["from_item"]), item_text(k["to_item"])
        if frm is None or frm["status"] not in _BLOCK_LABEL[tracker.item_table(k["from_item"])][1]:
            continue                                    # the blocker is gone, so it blocks nothing
        out.append(f"{ftext}{st.tag(k['from_item'])} blocks {ttext}{st.tag(k['to_item'])}")
        st.see(k["from_item"])
    return out


def _steer_next(st):
    """The next period: overdue actions, then those due within the window."""
    limit = (st.on + timedelta(days=STEERCO_WINDOW_DAYS)).isoformat()
    nxt = []
    for a in rows(st.con, "SELECT * FROM actions WHERE project = ? AND status IN ('Open', 'Delayed') AND due_date IS NOT NULL AND due_date <= ? "
                          "ORDER BY due_date, id", st.code, limit):
        if not st.usable("actions", a):
            continue
        late = a["due_date"] < st.on.isoformat()
        nxt.append(f"{st.text('actions', a, 'description')}{st.tag(a['id'])} — {a['owner']}, due {tracker.shown(a['due_date'])}{' (overdue)' if late else ''}")
        st.see(a["id"])
    return _capped(nxt, "next")


def steerco_data(code, version="internal", since=None, steerco_date=None, include=()):
    """The one-pager's facts as JSON-able data. `include`: item IDs Alan chose to keep in the client-safe version although a label
    excludes them. Nothing here is written by Claude; the only free text is the optional summary in the spec."""
    if version not in ("internal", "client"):
        sys.exit("version must be internal or client.")
    client = version == "client"
    con = tracker.connect()
    p, folder, mem = project(con, code)
    on = date.fromisoformat(steerco_date) if steerco_date else today()
    start = since or last_steerco(code) or (on - timedelta(days=STEERCO_FIRST_DAYS)).isoformat()
    st = _Steerco(con, code, client, set(include or ()), on, start)
    trend = _steer_trend(con, code, on)
    evidence = None if client else health_evidence(code)
    changes = _steer_changes(st)
    ms_rows = _steer_milestones(st)
    risks = _steer_risks(st)
    needed = _steer_needed(st)
    blockers = (_steer_dependencies(st) + ([] if client else _steer_links(st)))[:STEERCO_CAPS["blockers"]]
    flow = "" if client else flow_line_for(code, on)
    nxt = _steer_next(st)
    sensitive = [] if client else sorted({i for i in st.shown_ids if i in st.every})   # the internal version marks them; the client one shows no label
    return {
        "code": code, "name": p["name"], "version": version, "steerco_date": on.isoformat(), "since": start,
        "last_steerco": last_steerco(code), "blocked": pending_for(code), "health": p["health"], "health_reason": p["health_reason"],
        "trend": trend, "evidence": evidence, "early_warnings": [] if client else project_warnings(code)[:3],
        "changes": changes, "milestones": ms_rows, "risks": risks, "decisions_needed": needed, "blockers": blockers, "flow": flow,
        "next_period": nxt, "sensitive": sensitive, "omitted": st.omitted,
        "labelled_but_excluded": sorted(st.excluded) if client else [],
    }
# ===== end BL-229 step 4 (steerco_data) =====


def steerco_values(data, spec):
    """The template's values and the sections to leave out, from steerco_data's facts."""
    client = data["version"] == "client"
    health = data["health"]
    status_text = [t for t in (data["trend"],) if t]
    if data["evidence"]:
        ev = data["evidence"]
        status_text.append(f"The evidence suggests {ev['suggested']}" + (f": {'; '.join(ev['reasons'])}" if ev["reasons"] else "") + ".")
    if data["early_warnings"]:
        status_text.append("Early warnings: " + "; ".join(data["early_warnings"]) + ".")
    status_text += list(spec.get("summary") or [])
    if data["sensitive"]:
        status_text.append(f"Sensitive: {len(data['sensitive'])} item{'s' if len(data['sensitive']) != 1 else ''} below carry a label "
                           f"({', '.join(data['sensitive'])}) and are marked. Internal only: don't send this version.")
    values = {
        "PROJECT_NAME": data["name"],
        "STATUS_LINE": f"Draft, generated by creaite on {long_date(today().isoformat())}. Not yet reviewed. "
                       + ("Client-safe version." if client else "Internal version: not for the client."),
        "STEERCO_WHEN": f"Steering committee, {long_date(data['steerco_date'])} · changes since {long_date(data['since'])}",
        "HEALTH_LINE": [{"flag": health.upper(), "text": data["health_reason"] or ""} if health else {"text": "Health not set."}],
        "STATUS_TEXT": status_text or ["No weekly updates yet."],
        "SOURCE": "creaite tracker" + ("" if not client else ", client-visible items only") + f", {long_date(data['steerco_date'])}",
    }
    sections = {
        "What Changed": ("CHANGES", data["changes"]), "Milestones": ("MILESTONES", data["milestones"]),
        "Top Risks and Issues": ("RISKS", data["risks"]), "Decisions Needed": ("DECISIONS_NEEDED", data["decisions_needed"]),
        "Blockers": ("BLOCKERS", data["blockers"]), "Flow": ("FLOW", data["flow"]), "Next Period": ("NEXT_PERIOD", data["next_period"])}
    drop = []
    for heading, (key, content) in sections.items():
        if content:
            values[key] = content
        else:
            drop.append(heading)
    return values, drop


def trim_template(template, drop, out):
    """A copy of the template without the named sections (each heading and what follows it up to the next heading)."""
    parts = docx_tools.read_parts(template)
    heads = {"Overall Status", *STEERCO_SECTIONS}
    result = []
    for info, raw in parts:
        if info.filename == "word/document.xml":
            xml = raw.decode("utf-8")
            a, z = xml.index("<w:body>") + len("<w:body>"), xml.rindex("<w:sectPr")
            body = xml[a:z]
            blocks = re.findall(r"<w:tbl>.*?</w:tbl>|<w:p>.*?</w:p>|<w:p/>", body, re.S)
            if "".join(blocks) != body:
                sys.exit("The steerco template has a layout this can't trim; rebuild it with dev/tools/build_templates.py steerco.")
            keep, skipping = [], False
            for b in blocks:
                t = "".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", b)).replace("&amp;", "&")
                if not b.startswith("<w:tbl>") and t in heads:
                    skipping = t in drop
                elif t.startswith("Source:"):
                    skipping = False
                if not skipping:
                    keep.append(b)
            raw = (xml[:a] + "".join(keep) + xml[z:]).encode("utf-8")
        result.append((info, raw))
    docx_tools.write_parts(result, out)


def free_name(folder_, stem_, suffix, ext=".docx"):
    """'<stem><suffix>.docx', or with ' 2', ' 3'… before the extension when that name is taken: nothing is ever overwritten."""
    n, name = 1, f"{stem_}{suffix}{ext}"
    while (folder_ / name).exists():
        n += 1
        name = f"{stem_}{suffix} {n}{ext}"
    return name


def steerco_stage(spec):
    """Stage a steering one-pager (BL-92) from cx-steerco's spec: the Word draft in system/staging/drafts/ and a proposal that files it in
    the Steerco folder on approval, never overwriting. Returns 3 when items await review."""
    code, version = spec["code"], spec.get("version", "internal")
    data = steerco_data(code, version, spec.get("since"), spec.get("steerco_date"), spec.get("include_labelled") or ())
    if data["blocked"] and not spec.get("force"):
        print(f"{data['name']} has {data['blocked']} item{'s' if data['blocked'] > 1 else ''} awaiting review — review first, "
              f"or go ahead anyway (force).")
        return 3
    values, drop = steerco_values(data, spec)
    suffix = " (client)" if version == "client" else ""
    on = data["steerco_date"]
    paths.DRAFTS.mkdir(parents=True, exist_ok=True)
    draft = paths.DRAFTS / free_name(paths.DRAFTS, f"{on} {doc_stem(data['name'])} Steerco one-pager", suffix)     # BL-101: the name, never the code
    tmp = paths.DRAFTS / f"{draft.stem}.template.docx"
    try:
        trim_template(paths.STEERCO_TEMPLATE, drop, tmp)
        fill(tmp, values, draft)
    finally:
        tmp.unlink(missing_ok=True)
    target_dir = paths.folder(code, "steerco")
    target = target_dir / free_name(target_dir, f"{on} {doc_stem(data['name'])} Steerco one-pager", suffix)     # YYYY-MM-DD <Project name> Steerco one-pager[ (client)].docx
    ops = ([] if target_dir.is_dir() else [{"op": "mkdir", "path": paths.rel(target_dir)}]) + \
        [{"op": "copy", "from": "draft", "to": paths.rel(target)}, {"op": "remove", "path": paths.rel(draft)}]
    title = f"{data['name']} steering one-pager{suffix}, {tracker.shown(on)}"
    out = stage(f"steerco-{code}" + ("-client" if version == "client" else ""), {
        "created": sweep.now().strftime("%Y-%m-%dT%H:%M:00"), "source_run": "cx-steerco", "files": [], "items": [],
        "report": {"kind": "steerco", "version": version, "title": title, "project": code, "projects": [code],
                   "draft": paths.rel(draft), "report_decision": "pending", "file_ops": ops,
                   **({"included_labelled": sorted(set(spec.get("include_labelled") or []) & set(data["labelled_but_excluded"]))}
                      if version == "client" and spec.get("include_labelled") else {})}})     # Alan's choice, logged against the report
    print(f"Staged {paths.rel(out)}: {title}")
    print(f"Draft: {paths.rel(draft)}")
    print(f"On approval it is filed as: {paths.rel(target)}")
    if drop:
        print("Left out (nothing to say): " + ", ".join(drop))
    if data["sensitive"]:
        print(f"Includes {len(data['sensitive'])} sensitive item(s), marked in the document: {', '.join(data['sensitive'])}. Don't send the internal version.")
    for o in data["omitted"]:
        print(f"Left out of the client-safe version: {o}")
    kept = sorted(set(spec.get("include_labelled") or []) & set(data["labelled_but_excluded"]))
    if kept:
        print(f"Included at your request although labelled: {', '.join(kept)}. Review stops at these; approve with --as-staged to file it.")
    return 0


def main(argv):
    """The command line: weekly-data, client-data, steerco-data, current-context, facts, adhoc, adhoc-data, and weekly-stage, client-stage
    and steerco-stage (the spec file is deleted once used, BL-118)."""
    cmd, args = (argv[0], argv[1:]) if argv else ("", [])
    opts = dict(zip(args[1::2], args[2::2])) if len(args) > 1 else {}
    if cmd == "weekly-data" and args:
        print(json.dumps(weekly_data(args[0], opts.get("--week-ending")), indent=1, ensure_ascii=False))
        return 0
    if cmd == "client-data" and args:
        print(json.dumps(client_data(args[0], opts.get("--since")), indent=1, ensure_ascii=False))
        return 0
    if cmd == "steerco-data" and args:                                                  # BL-92
        print(json.dumps(steerco_data(args[0], opts.get("--version", "internal"), opts.get("--since"), opts.get("--date"),
                                      [i for i in opts.get("--include", "").split(",") if i]), indent=1, ensure_ascii=False))
        return 0
    if cmd == "current-context" and args:
        srcs = tuple(x for x in opts.get("--sources", ",".join(CONTEXT_SOURCES)).split(",") if x)
        try:
            print(current_context(args[0], opts.get("--from"), opts.get("--to"), srcs, opts.get("--audience", "internal"),
                                  opts.get("--length", "standard")))
        except ValueError as e:
            sys.exit(str(e))
        return 0
    if cmd == "facts" and args:                         # BL-106: the ranked facts sheet (status_facts.py); also its own script
        import status_facts
        return status_facts.main(["facts", *args])
    if cmd == "adhoc" and len(args) == 1:
        code = adhoc(json.loads(Path(args[0]).read_text(encoding="utf-8")))
        if not code:
            paths.consume_draft(args[0])                                         # BL-118: built, so the spec has done its job
        return code
    if cmd == "adhoc-data" and args:
        flags, vals, i = {"--overdue"}, {}, 1
        while i < len(args):
            if args[i] in flags:
                vals["overdue"] = True
                i += 1
            elif args[i].startswith("--") and i + 1 < len(args):
                vals[args[i][2:].replace("-", "_")] = args[i + 1]
                i += 2
            else:
                sys.exit(f"unexpected {args[i]}")
        print(json.dumps(adhoc_data(args[0], vals), indent=1, ensure_ascii=False))
        return 0
    if cmd in ("weekly-stage", "client-stage", "steerco-stage") and len(args) == 1:
        spec = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        code = weekly_stage(spec) if cmd == "weekly-stage" else steerco_stage(spec) if cmd == "steerco-stage" else client_stage(spec)
        if not code:
            paths.consume_draft(args[0])                                         # BL-118: staged, so the spec has done its job
        return code
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(debuglog.main("report.py", main, sys.argv[1:]))
