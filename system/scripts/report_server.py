"""The live server's report routes (v2.1.0 P3; BL-335, BL-336). A library: no command line; live_server.py registers `routes`.

  POST /api/report/draft   {kind, code, week_ending?, client?, fresh?}: the report to edit: its draft, else the filed report,
                           else a new one built from the tracker with the remembered layout (nothing written until Save)
  POST /api/report/save    {doc, base_version?}: the edits saved as the draft (creaite_doc.save through filechange.py); the layout
                           remembered for the project or the client. A filed report is never changed in place (Alan, 15-10-2026):
                           its edits become a new draft, and the filed file stays as it is until that draft is approved
  POST /api/report/approve {kind, code, week_ending, client?, force?, doc?, base_version?}: one proposal (report_doc.stage_weekly
                           or stage_client), applied at once with tracker.py apply, the one writer, so Undo works as always
                           A weekly approval re-locks the project's client drafts to that week (relock_client_drafts; `relocked`)
  POST /api/report/logo    {code, paths}: the project's logo files as data (read only; v2.1.0 P6): only files report_doc.logos names
  POST /api/report/check   {doc}: a client report's check of what is left out (client_check.py; read only, nothing written): the
                           items, hidden sections, unticked logos and health difference, the leak findings, whether its internal
                           week is approved, and the rows now client-visible that it could add (v2.1.0 P8, BL-336)
  POST /api/report/pick    {doc}: Add from the tracker (read only; #217): per table section the open items not in the report yet
                           (a client report: only client-safe facts), each with the row it would add; nothing is written
  POST /api/report/export  {kind, code, week_ending, client?, fmt, on_clash?, new_name?, page?}: P2's export (the contract's call), from the
                           draft or the filed report, saved first into the project's Reports folder through filechange.py (#220:
                           a taken name asks, on_clash "number", "rename" or "overwrite"; opening is separate).
                           #226: HTML and PDF are the report page's own exported view, posted as `page: {html, css, palette, version}`
                           and re-checked against the saved report by export_page.build; with no page, or one that fails, the plain
                           renderer makes the file and the answer says `plain: true`;
  POST /api/report/reveal  {path}: Show in Finder for a saved file under projects/;
                           A client report is exported only once its internal week is approved and nothing would leak, and its
                           answer then carries `left_out`: the check of what is left out runs before every client export
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


def relock_client_drafts(code, fri):
    """Re-lock the client drafts that depend on the internal week just approved (or approved again with changes): each draft of the
    project dated on or after `fri` whose latest approved internal week is now a different one gets `based_on` and its facts
    (meta.locked, facts_week, facts_on) from that week's approved facts (meta.client_facts), so a client draft saved before the
    approval can be exported after it. It errs towards withholding: a row, tag, milestone or item the approved facts don't hold is
    dropped, and nothing is ever added that the draft didn't have; wording Alan edited in a cell is left. Returns the stored paths
    re-locked. A draft that can't be read or saved is left as it was. Filed client reports are never touched."""
    done = []
    for f in sorted(paths.DRAFTS.glob("* Client report*.html")):
        try:
            if _relock_one(f, code, fri):
                done.append(paths.rel(f))
        except (creaite_doc.DocError, report_doc.ReportError, OSError, KeyError):
            continue          # left as it was: its Approve and export still check the baseline
    return done


def _relock_one(f, code, fri):
    """Re-lock one client draft file (see relock_client_drafts); whether it was saved."""
    doc = creaite_doc.read(f)
    if doc.get("kind") != "client" or doc.get("project") != code or doc["date"] < fri or doc.get("state") == "approved":
        return False
    base = report_doc.baseline(code, doc["date"])
    if not base or doc.get("based_on") == {"path": base["path"], "version": base["version"]}:
        return False
    facts = (creaite_doc.read(base["path"]).get("meta") or {}).get("client_facts") or {}
    allowed = {x["id"]: x for t in ("actions", "decisions", "raid", "milestones") for x in facts.get(t) or []}
    out = _held_to(doc, allowed)
    out["based_on"] = {"path": base["path"], "version": base["version"]}
    out["meta"] = {**(out.get("meta") or {}), "locked": bool(facts), "facts_week": base["date"], "facts_on": facts.get("on")}
    return bool(creaite_doc.save(paths.rel(f), out, "Client draft re-locked to the approved internal week", via="dashboard").get("ok"))


def _held_to(doc, allowed):
    """A copy of a client draft holding only what the approved facts (`allowed`: {item id: fact}) hold: rows, tags and milestone
    references to an item outside them are dropped, and the items it keeps take the approved facts' values."""
    out = dict(doc)
    out["sections"] = []
    for s in doc.get("sections") or []:
        s = dict(s)
        if s.get("rows"):
            s["rows"] = [r for r in s["rows"] if not r.get("ref") or r["ref"] in allowed]
        if s.get("tags"):
            s["tags"] = [t for t in s["tags"] if t.get("ref") in allowed]
        if isinstance(s.get("data"), dict):
            s["data"] = {k: ([m for m in v if m in allowed] if k in ("milestones", "timeline") and isinstance(v, list) else v)
                         for k, v in s["data"].items()}
        out["sections"].append(s)
    out["items"] = {k: allowed[k] for k in (doc.get("items") or {}) if k in allowed}
    return out


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
        answered = {"ok": code_ == 0, "message": out, "apply_id": HOST["latest_apply"](),
                    "path": report_doc.filed_path(kind, code, fri, client)}
        if code_ == 0 and kind == "weekly":
            answered["relocked"] = relock_client_drafts(code, fri)         # the week's client drafts lock to what was approved
        return answer(handler, answered)


def check_route(handler, req):
    """POST /api/report/check: a client report's check of what is left out (see the module's description). Writes nothing."""
    import client_check
    return answer(handler, client_check.check(req.get("doc")))


def pick_route(handler, req):
    """POST /api/report/pick: what Add from the tracker can offer (see the module's description). Writes nothing."""
    doc = req.get("doc")
    if not isinstance(doc, dict):
        raise report_doc.ReportError("Say which report to add to.")
    return answer(handler, {"ok": True, "sections": report_doc.pickable(doc)})


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


def _plain_name(name, ext):
    """A typed file name made safe: one name (no folder, no leading dot, 150 characters at most) that ends with `ext`; None when it
    can't be a file name."""
    name = " ".join(str(name or "").split())
    if not name or "/" in name or "\\" in name or name.startswith(".") or len(name) > 150:
        return None
    return name if name.lower().endswith(ext) else name + ext


def _taken(folder, name, reserved=None):
    """Whether anything of that name is in the folder already, or the name is `reserved` (the name an unfiled report will be filed
    under: nothing is there yet, but an export in the way would block Approve and file)."""
    f = folder / name
    return f.exists() or f.is_symlink() or (reserved is not None and name.lower() == reserved.lower())


def _numbered(folder, name, reserved=None):
    """The next free "Name (2).ext" in the folder (what a create adds by itself), skipping the reserved filing name."""
    stem, dot, ext = name.rpartition(".")
    stem, ext = (stem, dot + ext) if dot else (name, "")
    n, final = 2, name
    while _taken(folder, final, reserved):
        final, n = f"{stem} ({n}){ext}", n + 1
    return final


def _not_saved(handler, why, **extra):
    """The answer when the file was not saved: plainly why, and that nothing was written (#220)."""
    return refuse(handler, f"Not saved: {why} Nothing was written.", saved=False, **extra)


def _file_in_reports(handler, draft, folder, name, overwrite, fmt, label):
    """File the exported draft in the Reports folder as `name` through filechange.py: a create (never overwriting) or, on Overwrite,
    an edit that backs the earlier file up first. The draft in system/staging/drafts/ goes in every case."""
    import re
    import filechange
    import reach
    target = folder / name
    ch = {"op": "edit" if overwrite else "create", "path": paths.rel(target), "data": draft.read_bytes(), "from": paths.rel(draft),
          "why": f"{fmt.upper()} export of {target.stem}" + (" (replaced at your choice)" if overwrite else "")}
    try:
        token = reach.APPROVALS.issue(filechange.fingerprint(ch)) if overwrite else None   # Alan's own Overwrite: this change, once
        code, msg = filechange.perform(ch, token, "dashboard")
    except OSError as e:
        for stray in folder.glob(f".{name}.part"):
            stray.unlink(missing_ok=True)
        return _not_saved(handler, f"the {label} folder can't be written to ({e.strerror or e.__class__.__name__}).")
    finally:
        draft.unlink(missing_ok=True)
    if code == filechange.NEEDS:
        filechange.record_request(ch, msg[len("Needs approval: "):].rstrip("."))
        return _not_saved(handler, msg)
    if code != 0:
        return _not_saved(handler, msg)
    final = re.match(r"(?:Created|Changed) (.+?) \(change (\d+)", msg)
    stored = final.group(1) if final else ch["path"]
    return {"ok": True, "saved": True, "format": fmt, "path": stored, "name": Path(stored).name, "folder": paths.rel(folder),
            "folder_label": label, "replaced": bool(overwrite), "change": int(final.group(2)) if final else None, "filed": True,
            "message": f"{'Replaced' if overwrite else 'Saved'} {Path(stored).name} in {label}."}


def _settle_name(folder, name, ext, req, label, reserved=None):
    """(name, overwrite, asked): the file name to save as, from the page's choice for a taken name (`on_clash`: number, rename with
    `new_name`, or overwrite), and `asked`: the answer to give instead when the name is taken and no choice was made (or the typed
    name can't be used), else None. `reserved` is the filing name of a report not yet filed: taken, but with nothing there, so
    Overwrite is never offered or accepted for it (`reserved: true` in the answer)."""
    choice = req.get("on_clash")
    if choice == "rename":
        name = _plain_name(req.get("new_name"), ext)
        if not name:
            return name, False, {"message": "Type a file name (no folders, not starting with a dot).", "clash": True}
    if not _taken(folder, name, reserved):
        return name, False, None
    if choice == "number":
        return _numbered(folder, name, reserved), False, None
    if choice == "overwrite" and (folder / name).is_file():
        return name, True, None
    only = not (folder / name).exists()
    return name, False, {"ok": False, "clash": True, "name": name, "numbered": _numbered(folder, name, reserved), "reserved": only,
                         "message": (f"{name} is the name this report will be filed under in {label}." if only
                                     else f"{name} is already in {label}.")}


def carry_plain(saved, made):
    """#226: a saved export the plain renderer made says so (plain, plain_why and the message's note)."""
    if saved.get("ok") and made.get("plain"):
        saved["plain"] = True
        if made.get("plain_why"):
            saved["plain_why"] = made["plain_why"]
        plain_note(saved)


def plain_note(out):
    """#226: an export the plain renderer made (no page, or one the server's check refused) says so in its message."""
    if not (out.get("ok") and out.get("plain")):
        return
    why = out.get("plain_why")
    out["message"] = (f"{out.get('message') or 'Exported.'} This is the plain version "
                      + (f"(the report page was not used: {why})." if why else "(open the report in creaite to export the formatted one)."))


def export_route(handler, req):
    """POST /api/report/export: the report exported as HTML, Word or PDF, and saved first into the project's Reports folder (#220).
    Opening is a separate choice (/api/open, /api/report/reveal). The answer: {ok, saved, path, name, folder, folder_label,
    replaced, message}; a taken name answers {ok: false, clash: true, name, numbered, folder, folder_label} and writes nothing
    until the page asks again with on_clash "number", "rename" (and new_name) or "overwrite"; a failed save says why and that
    nothing was written. Nothing is ever sent."""
    kind, code, fri, client = target(req)
    fmt = req.get("fmt")
    if fmt not in FORMATS:
        return refuse(handler, "Export as html, docx or pdf.")
    state, path = report_doc.where(kind, code, fri, client)
    if not state:
        return refuse(handler, "Save the report before exporting it.")
    doc = creaite_doc.read(path)
    left = None
    if kind == "client":
        import client_check
        left = client_check.left_out(doc)          # the check runs before every client export, whoever asks
        if not left["ready"] or left["findings"]:
            return refuse(handler, left["not_ready"] or "Not exported: possible internal content in the client report.",
                          findings=left["findings"], left_out=left)
    fn = export_call()
    if fn is None:
        return refuse(handler, "Exports aren't built yet in this version of creaite.")
    filed = paths.resolve(report_doc.filed_path(kind, code, fri, client))
    folder, ext = filed.parent, creaite_doc.EXPORTS[fmt]
    name = filed.stem + ext          # the plain name for all three (Alan, 18-10-2026): HTML meets the filed report's name and asks
    label = f"{creaite_doc.project_name(code) or code} › Reports"
    where = {"folder": paths.rel(folder), "folder_label": label, "format": fmt}
    name, overwrite, asked = _settle_name(folder, name, ext, req, label, filed.name)
    if asked:
        return answer(handler, {"ok": False, **asked, **where})
    out = fn(path, fmt, file_beside=False, open_after=False,
             page=req.get("page") if isinstance(req.get("page"), dict) else None)           # made in system/staging/drafts/, filed below
    if not out.get("ok"):
        return _not_saved(handler, str(out.get("message") or "the report couldn't be made."), **where)
    saved = _file_in_reports(handler, paths.resolve(out["path"]), folder, name, overwrite, fmt, label)
    carry_plain(saved, out)
    if left is not None:
        saved["left_out"] = left
    return answer(handler, saved)


def reveal_route(handler, req):
    """POST /api/report/reveal {path}: show a saved file in Finder (Show in Finder), or open the folder when the path is a folder.
    Only a stored path under projects/. With CREAITE_NO_LAUNCH (the tests) nothing opens and `launched` is false."""
    import re
    rel = str(req.get("path") or "")
    if not re.fullmatch(r"projects/.+", rel) or ".." in Path(rel).parts or not paths.resolve(rel).exists():
        return refuse(handler, "That file or folder isn't there to show.")
    real = paths.resolve(rel)
    if os.environ.get("CREAITE_NO_LAUNCH"):
        return answer(handler, {"ok": True, "launched": False, "path": str(real)})
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(real)] if real.is_file() else ["open", str(real)])
    elif os.name == "nt":
        subprocess.Popen(["explorer", "/select,", str(real)] if real.is_file() else ["explorer", str(real)])
    else:
        subprocess.Popen(["xdg-open", str(real.parent if real.is_file() else real)])
    return answer(handler, {"ok": True, "launched": True})


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
            "/api/report/approve": guarded(approve_route), "/api/report/check": guarded(check_route),
            "/api/report/pick": guarded(pick_route),
            "/api/report/export": guarded(export_route), "/api/report/reveal": guarded(reveal_route),
            "/api/report/logo": guarded(logo_route)}
