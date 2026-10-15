"""The live server's report routes (v2.1.0 P3; BL-335, BL-336). A library: no command line; live_server.py registers `routes`.

  POST /api/report/draft   {kind, code, week_ending?, client?, fresh?}: the report to edit: its draft, else the filed report,
                           else a new one built from the tracker with the remembered layout (nothing written until Save)
  POST /api/report/save    {doc, base_version?}: the edits saved as the draft (creaite_doc.save through filechange.py); the layout
                           remembered for the project or the client. A filed report is never changed in place (Alan, 15-10-2026):
                           its edits become a new draft, and the filed file stays as it is until that draft is approved
  POST /api/report/approve {kind, code, week_ending, client?, force?, doc?, base_version?}: one proposal (report_doc.stage_weekly
                           or stage_client), applied at once with tracker.py apply, the one writer, so Undo works as always
  POST /api/report/logo    {code, paths}: the project's logo files as data (read only; v2.1.0 P6): only files report_doc.logos names
  POST /api/report/export  {kind, code, week_ending, client?, fmt, file_beside?}: P2's export (the contract's call), from the draft
                           or the filed report; a client report only once its internal week is approved and nothing would leak
"""
import base64
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import creaite_doc  # noqa: E402
import report_doc  # noqa: E402

FORMATS = ("html", "docx", "pdf")


def answer(handler, body):
    """Send a 200 with the route's answer."""
    return handler.send(200, body)


def refuse(handler, message, **extra):
    """Send a refusal Alan can read (nothing was changed)."""
    return handler.send(200, {"ok": False, "message": message, **extra})


def target(req):
    """(kind, code, week ending, client) from a request; raises ReportError for a kind, project or date creaite doesn't know."""
    import tracker
    kind, code = req.get("kind"), str(req.get("code") or "")
    if kind not in report_doc.KINDS or not report_doc.CODE.match(code):
        raise report_doc.ReportError("Say which report: weekly or client, and the project's code.")
    with tracker.connect() as con:
        if not con.execute("SELECT 1 FROM projects WHERE code = ?", (code,)).fetchone():
            raise report_doc.ReportError(f"{code} isn't in the tracker.")
    try:
        fri = report_doc.friday(req.get("week_ending") or None)
    except ValueError:
        raise report_doc.ReportError("The week ending must be YYYY-MM-DD.") from None
    if kind == "weekly":
        return kind, code, fri, None
    return kind, code, fri, str(req.get("client") or "").strip()[:120] or project_client(code)


def project_client(code):
    """The project's client (its memory's Client / partner line), the client a client report is for when none is named; or None."""
    import build_dashboard
    return build_dashboard.memory(paths.project_dir(code)).get("client") or None


def guarded(fn):
    """A route that answers a ReportError, a DocError or a script's exit as a refusal instead of a fault."""
    def route(handler, req):
        """The route, its refusals answered."""
        try:
            return fn(handler, req)
        except (report_doc.ReportError, creaite_doc.DocError) as e:
            return refuse(handler, str(e))
        except SystemExit as e:              # report.py exits with a sentence when a project isn't there
            return refuse(handler, str(e.code) if e.code not in (None, 0) else "That report can't be made.")
    route.__doc__ = fn.__doc__
    return route


def draft_route(handler, req):
    """POST /api/report/draft: the report to edit (see the module's description)."""
    import client_leak
    kind, code, fri, client = target(req)
    state, path = report_doc.where(kind, code, fri, client)
    if state and not (req.get("fresh") and state == "draft"):
        doc = creaite_doc.read(path)
    else:
        doc, state = report_doc.build(kind, code, fri, client), "new"
        path = report_doc.draft_path(kind, code, fri, client)
    out = {"ok": True, "doc": doc, "path": path, "where": state, "version": int(doc.get("version") or 0),
           "filed": paths.resolve(report_doc.filed_path(kind, code, fri, client)).is_file(),
           "logos": report_doc.logos(code)}
    if kind == "client":
        ready, why = report_doc.client_ready(doc)
        out.update(ready=ready, not_ready=why, findings=client_leak.findings(doc), baseline=report_doc.baseline(code, fri))
    return answer(handler, out)


def save_route(handler, req):
    """POST /api/report/save: save the edits as the draft and remember the layout (see the module's description)."""
    doc = req.get("doc")
    creaite_doc.check(doc)
    kind, code, fri, client = target({"kind": doc.get("kind"), "code": doc.get("project"), "week_ending": doc.get("date"),
                                      "client": doc.get("client")})
    if fri != doc["date"]:
        raise report_doc.ReportError("A report's date is its week ending, a Friday.")
    with handler_lock(handler):
        out = report_doc.save_draft(doc, req.get("base_version"))
        if out.get("ok"):
            report_doc.remember_layout(code, kind, doc.get("layout"), client)
    return answer(handler, out)


def handler_lock(handler):
    """The live server's one lock for tracker and file changes (live_server.LOCK), through the host module."""
    return HOST["lock"]


def approve_route(handler, req):
    """POST /api/report/approve: save any edits sent, stage the one proposal and apply it (see the module's description)."""
    kind, code, fri, client = target(req)
    draft = report_doc.draft_path(kind, code, fri, client)
    with handler_lock(handler):
        if isinstance(req.get("doc"), dict):
            saved = report_doc.save_draft(req["doc"], req.get("base_version"))
            if not saved.get("ok"):
                return answer(handler, saved)
        if not paths.resolve(draft).is_file():
            return refuse(handler, "There is no draft to approve: save the report first (a filed report is approved already).")
        stage = report_doc.stage_weekly if kind == "weekly" else report_doc.stage_client
        prop = stage(draft, force=bool(req.get("force")))
        code_, out = HOST["run"]("tracker.py", "apply", prop.name)
        if code_ != 0 and prop.exists():
            prop.unlink()                    # nothing was written: the proposal this Approve staged goes, the draft stays
        return answer(handler, {"ok": code_ == 0, "message": out, "apply_id": HOST["latest_apply"](),
                                "path": report_doc.filed_path(kind, code, fri, client)})


def export_call():
    """P2's export function (the contract's `export(path, fmt, *, out_dir, file_beside, open_after)`), or None while it isn't
    built: looked for in creaite_doc, then a module of its own."""
    import importlib
    for name in ("creaite_doc", "doc_export", "report_export"):
        try:
            fn = getattr(importlib.import_module(name), "export", None)
        except ImportError:
            continue        # that module isn't there (P2 not merged yet)
        if callable(fn):
            return fn
    return None


def launch(stored):
    """Open a file in its default app, as /api/open does (nothing opens under CREAITE_NO_LAUNCH, the tests' setting). Returns whether
    it was launched."""
    if os.environ.get("CREAITE_NO_LAUNCH"):
        return False
    p = str(paths.resolve(stored))
    if sys.platform == "darwin":
        subprocess.Popen(["open", p])
    elif os.name == "nt":
        os.startfile(p)  # noqa: S606  (Windows only)
    else:
        subprocess.Popen(["xdg-open", p])
    return True


def export_route(handler, req):
    """POST /api/report/export: the report exported as HTML, Word or PDF (see the module's description). Nothing is ever sent."""
    import client_leak
    kind, code, fri, client = target(req)
    fmt = req.get("fmt")
    if fmt not in FORMATS:
        return refuse(handler, "Export as html, docx or pdf.")
    state, path = report_doc.where(kind, code, fri, client)
    if not state:
        return refuse(handler, "Save the report before exporting it.")
    doc = creaite_doc.read(path)
    if kind == "client":
        ready, why = report_doc.client_ready(doc)
        found = client_leak.findings(doc)
        if not ready or found:
            return refuse(handler, why or "Not exported: possible internal content in the client report.", findings=found)
    fn = export_call()
    if fn is None:
        return refuse(handler, "Exports aren't built yet in this version of creaite.")
    out = fn(path, fmt, file_beside=bool(req.get("file_beside", creaite_doc.file_beside_default(kind))), open_after=True)
    if out.get("ok") and out.get("path"):
        out["launched"] = launch(out["path"])
    return answer(handler, out)


LOGO_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml"}
LOGO_MAX = 400_000


def logo_route(handler, req):
    """POST /api/report/logo {code, paths}: each asked-for logo of the project as a data address ({path: "data:…"}), for the report
    view to draw. Read only; only the files report_doc.logos names for that project (its firm, client and partner logos), each
    up to 400 kB; anything else asked for is left out."""
    code = str(req.get("code") or "")
    if not report_doc.CODE.match(code):
        return refuse(handler, "Say which project's logos.")
    known = {x["path"]: x for x in report_doc.logos(code)}
    out = {}
    for stored in req.get("paths") or []:
        if stored not in known:
            continue
        f = paths.resolve(stored)
        if f.suffix.lower() in LOGO_TYPES and f.is_file() and f.stat().st_size <= LOGO_MAX:
            out[stored] = f"data:{LOGO_TYPES[f.suffix.lower()]};base64,{base64.b64encode(f.read_bytes()).decode()}"
    return answer(handler, {"ok": True, "logos": out})


HOST = {}       # the live server's own lock, run and latest_apply (live_server registers them; never a second copy of the module)


def routes(lock, run, latest_apply):
    """The report routes for live_server's route table, given its lock, its script runner and its latest_apply."""
    HOST.update(lock=lock, run=run, latest_apply=latest_apply)
    return {"/api/report/draft": guarded(draft_route), "/api/report/save": guarded(save_route),
            "/api/report/approve": guarded(approve_route), "/api/report/export": guarded(export_route),
            "/api/report/logo": guarded(logo_route)}
