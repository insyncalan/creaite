"""A larger fictional portfolio for the Work filter tests (BL-77), and an oracle that works out in Python what each
filter should show, so the page's rows and counts can be checked against something that doesn't share its code.

`load(v)` adds, on top of test_dashboard.populate's two projects, about 60 actions, 30 RAID items and 12 decisions
with every status, priority, owner spelling, due-date kind, workstream, source and client-visible flag that the
filters care about. Dates are relative to today, so the data is always current.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import action  # noqa: E402
from test_dashboard import _today, stamped_apply  # noqa: E402

TODAY = _today()        # CREAITE_NOW's day when it is set, as test_dashboard's sample data uses
DUE_SOON = 7


def d(n):
    return (TODAY + timedelta(days=n)).isoformat()


OWNERS = ["Alan Carter", "Alan", "Sara Example", "Omar Ali", "Jane Doe", "Priya Nair", "TBC"]   # "Alan" is Alan's short form
STATUSES = ["Open", "Open", "Open", "Delayed", "Closed", "Cancelled"]
PRIORITIES = ["Urgent", "High", "Medium", "Low"]
DUES = [-9, -3, 0, 2, 6, 7, 8, 20, None]            # overdue, today, soon (within 7 days), later, no date
WORKSTREAMS = ["Build", "Test", "", "Change", "Build"]
SOURCES = ["ABC Example Programme/minutes/2026-10-01 Steering.docx — Actions",
           "Email · From: Omar Ali <omar@def.example> · Subject: Pilot · Sent: 2026-10-01 09:00 · Link: https://outlook.office365.com/owa/?ItemID=abc",
           "Teams · Chat: Omar",
           "Dashboard (Alan)", "Excel import", "cx-edit"]


CM = ("What it is: An item the client is waiting on.\nWhat it means for you: It affects the next milestone.\n"
      "What is being done: We are chasing it weekly.")


def load(v):
    items = []
    n = 0
    for code in ("ABC", "DEF"):                                  # workstreams must exist (BL-58) before items use them
        for name in ("Build", "Test", "Change"):
            n += 1
            items.append({"n": n, "op": "new", "table": "workstreams", "values": {"project": code, "name": name,
                          "source": "Test data (fictional)"}, "match": "strong", "flags": [], "decision": "approved"})
    for i in range(60):
        n += 1
        due = DUES[i % len(DUES)]
        status = STATUSES[i % len(STATUSES)]
        values = {"project": "ABC" if i % 3 else "DEF", "description": f"Action number {i:02d} {'alpha' if i % 4 == 0 else 'beta'}",
                  "owner": OWNERS[i % len(OWNERS)], "priority": PRIORITIES[i % 4], "status": status,
                  "raised": d(-30), "source": SOURCES[i % len(SOURCES)]}
        if i % 5 == 0:
            values.update(client_visible=1, client_message=CM)
        if due is not None:
            values["due_date"] = d(due)
        ws = WORKSTREAMS[i % len(WORKSTREAMS)]
        if ws:
            values["workstream"] = ws
        if status in ("Closed", "Cancelled"):
            values["closed"] = d(-1)
        items.append(action(n, **values))
    types = ["Risk", "Issue", "Assumption", "Dependency"]
    for i in range(30):
        n += 1
        due = DUES[(i * 2) % len(DUES)]
        values = {"project": "ABC" if i % 2 else "DEF", "type": types[i % 4], "description": f"Raid number {i:02d}",
                  "owner": OWNERS[(i * 3) % len(OWNERS)], "impact": ["High", "Medium", "Low"][i % 3],
                  "likelihood": ["High", "Medium", "Low"][(i // 3) % 3], "status": ["Open", "Open", "Closed"][i % 3],
                  "raised": d(-20), "source": SOURCES[i % len(SOURCES)]}
        if i % 4 == 0:
            values.update(client_visible=1, client_message=CM)
        if i % 3 == 1:
            values["response_action"] = "Mitigation agreed"
        if due is not None:
            values["due_date"] = d(due)
        if i % 5 == 0:
            values["workstream"] = "Build"
        if values["status"] == "Closed":
            values["closed"] = d(-2)
        items.append({"n": n, "op": "new", "table": "raid", "values": values, "match": "strong", "flags": [], "decision": "approved"})
    for i in range(12):
        n += 1
        items.append({"n": n, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
                      "values": {"project": "ABC" if i % 2 else "DEF", "decision": f"Decision number {i:02d}",
                                 "made_by": OWNERS[i % len(OWNERS)], "date": d(-3 * i),
                                 "source": SOURCES[i % len(SOURCES)],
                                 **({"client_visible": 1, "client_message": CM} if i % 3 == 0 else {})}})
    v.propose("rich", items)
    stamped_apply(v)


# ── the oracle ──

ME = {"alan carter", "alan", "ac"}


def is_me(owner):
    return (owner or "").lower() in ME


def open_action(r):
    return r["status"] in ("Open", "Delayed")


def due_kind(r, is_open):
    if not is_open:
        return "closed"
    due = r["due_date"]
    if not due:
        return "none"
    if due < TODAY.isoformat():
        return "overdue"
    return "soon" if (date.fromisoformat(due) - TODAY).days <= DUE_SOON else "later"


def source_kind(src):
    s = src or ""
    import re
    if re.search("dashboard", s, re.I):
        return "Dashboard"
    if re.search("excel", s, re.I):
        return "Excel"
    if re.search("cx-edit", s, re.I):
        return "cx-edit"
    if re.search(r'^Teams|Teams ·|"type":\s*"Teams"', s, re.I):
        return "Teams"
    if re.search(r'Outlook|"type":\s*"Email"|^RE:|^FW:', s, re.I):
        return "Mail"
    if re.search(r"\.(docx|vtt|txt|md)\b", s, re.I):
        return "Minutes"
    return "Other"


PROJECT_NAMES = {"ABC": "Example Programme", "DEF": "Digital Enablement"}


def shown_date(iso):
    return f"{iso[8:10]}-{iso[5:7]}-{iso[0:4]}" if iso else ""


def expected_ids(rows, table, status=None, due=None, owner=None, project=None, priority=None, ws=None, src=None, cv=None,
                 typ=None, resp=None, between=None, query="", last_days=None):
    """The ids that the filters should leave. Each argument is a set of chosen values (None: not filtering);
    values within one filter are OR, different filters are AND."""
    out = []
    for r in rows:
        is_open = open_action(r) if table == "actions" else r.get("status") == "Open"
        who = r.get("owner") if table != "decisions" else r.get("made_by")
        if status and r["status"] not in status:
            continue
        if due and due_kind(r, is_open) not in due:
            continue
        if owner and who not in owner:
            continue
        if project and r["project"] not in project:
            continue
        if priority and r["priority"] not in priority:
            continue
        if ws is not None and (r["workstream"] or "") not in ws:
            continue
        if src and source_kind(r["source"]) not in src:
            continue
        if cv and ("yes" if r["client_visible"] else "no") not in cv:
            continue
        if typ and r.get("type") not in typ:
            continue
        if resp and ("yes" if r.get("response_action") else "none") not in resp:
            continue
        if between and not (r["due_date"] and (not between[0] or r["due_date"] >= between[0]) and (not between[1] or r["due_date"] <= between[1])):
            continue
        if last_days is not None:
            ago = (TODAY - date.fromisoformat(r["date"])).days
            if not any(0 <= ago <= n for n in last_days):
                continue
        if query:
            dates = [shown_date(r.get(k)) for k in ("due_date", "raised", "closed", "date")]
            hay = " ".join([str(v) for v in r.values() if isinstance(v, str)] + dates + [PROJECT_NAMES.get(r["project"], "")]).lower()
            if not all(w in hay for w in query.lower().split()):
                continue
        out.append(r["id"])
    return sorted(out)
