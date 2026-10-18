"""The check of what is left out of a client report (v2.1.0 P8; BL-336). A library: no command line; report_server.py calls it.

Read only: it writes nothing. For one client document it works out
  - left_out: what the tracker holds for the project that this report does not show, and why (not client-visible, Sensitive,
    partner-only or a label that excludes it, hidden here, not the client's own), the sections hidden, any logo unticked and the
    health difference (BL-336 decided 8), with the leak findings (client_leak.findings) that block approving and exporting;
  - addable: rows a fresh client-safe build would have that the document lacks (an item made client-visible since), so the
    view can offer to add them. Built by report_doc.client_doc, so the wording is the client's and every row has been through
    client_leak.make_safe.
The list names internal items by ID and title: it is for Alan's eyes in the check, never part of a document.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402,F401
import creaite_doc  # noqa: E402
import report_doc  # noqa: E402

GROUPS = (("risks", "risks and issues", "raid"), ("overdue", "overdue actions", "actions"), ("decisions", "decisions", "decisions"),
          ("milestones", "milestones", "milestones"))
TITLE = {"raid": "description", "actions": "description", "decisions": "decision", "milestones": "name"}


def shown_refs(doc):
    """The item references a client document shows: shown rows of its tables, and the milestones its timeline and list hold."""
    out = set()
    for s in doc.get("sections") or []:
        if s.get("hidden"):
            continue
        out |= {r.get("ref") for r in s.get("rows") or [] if r.get("shown", True) and r.get("ref")}
        data = s.get("data") or {}
        out |= set(data.get("timeline") or []) | set(data.get("milestones") or [])
    return out


def hidden_rows(doc):
    """{ref: section id} of the rows the document keeps but does not show (an eye closed)."""
    return {r["ref"]: s["id"] for s in doc.get("sections") or [] if not s.get("hidden")
            for r in s.get("rows") or [] if r.get("ref") and r.get("shown") is False}


def universe(con, code, fri):
    """[(group key, table, id, title)] of what a client report could say about the project this week: open risks and issues,
    overdue actions, decisions made or pending, milestones not cancelled."""
    out = []
    for r in con.execute("SELECT id, description FROM raid WHERE project = ? AND status = 'Open' AND type IN ('Risk', 'Issue') "
                         "ORDER BY id", (code,)):
        out.append(("risks", "raid", r[0], r[1]))
    for r in con.execute("SELECT id, description FROM actions WHERE project = ? AND status IN ('Open', 'Delayed') "
                         "AND due_date IS NOT NULL AND due_date < ? ORDER BY id", (code, fri)):
        out.append(("overdue", "actions", r[0], r[1]))
    for r in con.execute("SELECT id, decision FROM decisions WHERE project = ? AND status IN ('Made', 'Pending') ORDER BY id", (code,)):
        out.append(("decisions", "decisions", r[0], r[1]))
    for r in con.execute("SELECT id, name FROM milestones WHERE project = ? AND status != 'Cancelled' ORDER BY id", (code,)):
        out.append(("milestones", "milestones", r[0], r[1]))
    return out


def _short(text, n=90):
    """One line of an internal title."""
    t = " ".join(str(text or "").split())
    return t if len(t) <= n else t[:n - 1] + "…"


def left_items(doc, con):
    """[{group, ref, title, why, kind}] of the items the document does not show. `kind`: sensitive (never), blocked (a label or not
    client-visible: Alan can change that), hidden (an eye closed here), other."""
    import client_leak
    blocking = client_leak.blocking_labels(con)
    on, closed = shown_refs(doc), hidden_rows(doc)
    out = []
    for group, _table, ref, title in universe(con, doc["project"], doc["date"]):
        if ref in on:
            continue
        why = client_leak.item_problem(con, ref, blocking)
        if why and "Sensitive" in why:
            kind, text = "sensitive", "Sensitive: never in a client report"
        elif why and "partner-only" in why:
            kind, text = "sensitive", "partner-only: never in a client report"
        elif why and "isn't client-visible" in why:
            kind, text = "blocked", "not client-visible"
        elif why:
            kind, text = "blocked", why.replace(ref + " is ", "").replace(ref + " ", "")
        elif ref in closed:
            kind, text = "hidden", "hidden in this report"
        else:
            kind, text = "other", "not in this report"
        out.append({"group": group, "ref": ref, "title": _short(title), "why": text, "kind": kind})
    return out


def _unticked_logos(doc):
    """The client or partner logos set for the project that this document's layout leaves out."""
    code = doc["project"]
    have = set(report_doc.resolve_logos(code, (doc.get("layout") or {}).get("logos") or report_doc.logo_kinds(code)))
    names = {"partner:" + p["slug"]: "partner " + p["name"] for p in report_doc.partners(code)}
    return [names.get(k, k) for k in report_doc.logo_kinds(code) if k != "firm" and k not in have and report_doc.logo_file(code, k)]


def _health_difference(doc):
    """The health difference kept in the document's meta, or None when the client's flag is the internal one."""
    diff = (doc.get("meta") or {}).get("health_diff") or None
    return diff if diff and diff.get("client") != diff.get("internal") else None


def left_out(doc, con=None):
    """What a client document leaves out, for the check before an export (see the module's description)."""
    import client_leak
    con = con or client_leak.connect()
    meta = doc.get("meta") or {}
    ready, why = report_doc.client_ready(doc)
    diff = _health_difference(doc)
    if ready and diff and not str(diff.get("reason") or "").strip():       # #203: a differing flag needs its reason, written by Alan
        ready, why = False, "Write why the client's health differs from the internal health: open the health flag on the client report."
    return {"items": left_items(doc, con),
            "sections": [{"id": s["id"], "heading": s.get("heading") or s["id"]} for s in doc.get("sections") or [] if s.get("hidden")],
            "logos": _unticked_logos(doc), "tags": sum(len(s.get("tags") or []) for s in doc.get("sections") or [] if not s.get("hidden")),
            "health": _health_difference(doc), "findings": client_leak.findings(doc, con), "ready": ready, "not_ready": why,
            "facts_week": meta.get("facts_week")}


def addable(doc):
    """[{section, row, item}]: rows a fresh build has that the document lacks, with the item as it stands (client wording)."""
    have = {(s["id"], r.get("ref")) for s in doc.get("sections") or [] for r in s.get("rows") or []}
    fresh = report_doc.client_doc(doc["project"], doc["date"], doc.get("client"), layout=doc.get("layout"))
    out = []
    for s in fresh["sections"]:
        for r in s.get("rows") or []:
            if (s["id"], r.get("ref")) not in have:
                out.append({"section": s["id"], "row": r, "item": (fresh.get("items") or {}).get(r.get("ref"))})
    return out


def check(doc):
    """The check's answer for the route: {ok, left_out, addable}. Raises creaite_doc.DocError for a document that is not a client
    report."""
    creaite_doc.check(doc)
    if doc.get("kind") != "client":
        raise creaite_doc.DocError("Only a client report has this check.")
    return {"ok": True, "left_out": left_out(doc), "addable": addable(doc)}
