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
  POST /api/report/logo/save   {code, kind, ext, original, drawn?}: a logo added or changed from the screen (H3, #221; base64): the file
                           chosen is kept as it was (`<name>-original.<ext>`) and the trimmed copy that is drawn is `<name>.png`; an
                           SVG, or a file sent without a trimmed copy, is saved as `<name>.<ext>`. Through filechange.py
  POST /api/report/logo/remove {code, kind}: the logo and its original deleted (Alan's own click: one approval for exactly that change)
  POST /api/report/image   {code, name, data (base64)}: a PNG or JPEG (2 MB at most) for a text section (H5, #218), created through
                           filechange.py in the project's Reports folder under `_images/`; answers its `ref` (`_images/<name>`)
  POST /api/report/images  {code, refs}: those pictures as data addresses ({ref: "data:…"}) for the editor to draw; read only, and
                           only an `_images/<name>.png|jpg` that is a file in the Reports folder is ever read
  POST /api/report/check   {doc}: a client report's check of what is left out (client_check.py; read only, nothing written): the
                           items, hidden sections, unticked logos and health difference, the leak findings, whether its internal
                           week is approved, and the rows now client-visible that it could add (v2.1.0 P8, BL-336)
  POST /api/report/match-check {docs: [doc]}: the leak findings (client_leak.findings) of each client document, one list per
                           document, in order (read only, nothing is written; at most 60). Match internal asks it before it copies
                           internal wording into the client page, so internal words never sit on the client draft (v2.5.0)
  POST /api/report/pick    {doc}: Add from the tracker (read only; #217): per table section the open items not in the report yet
                           (a client report: only client-safe facts), each with the row it would add; nothing is written
  POST /api/report/export  {kind, code, week_ending, client?, fmt, on_clash?, new_name?, page?}: P2's export (the contract's call), from the
                           draft or the filed report, saved first into the project's Reports folder through filechange.py (#220:
                           a taken name asks, on_clash "number", "rename" or "overwrite"; opening is separate).
                           #226: HTML and PDF are the report page's own exported view, posted as `page: {html, css, palette, version}`
                           and re-checked against the saved report by export_page.build; with no page, or one that fails, the plain
                           renderer makes the file and the answer says `plain: true`; a client report never uses a posted page
                           (v2.5.1, #239): it is always rendered from the saved report, under the lock, and its output checked;
  POST /api/report/reveal  {path}: Show in Finder for a saved file under projects/;
                           A client report is exported only once its internal week is approved and nothing would leak, and its
                           answer then carries `left_out`: the check of what is left out runs before every client export
"""
import base64
import copy
import re
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
    return kind, code, fri, project_client(code)      # v2.5.0: the project's client always; a client named in the request is ignored


CLIENT_NAME_MAX = 80


def project_client(code):
    """The project's client (its memory's Client / partner line), the client a client report is for when none is named; or None."""
    return creaite_doc.project_client(code)          # one line, 80 characters at most (the panel holds the same cap)


CLIENT_OFF = "This project has no separate client report switched on. Turn it on in the Client report settings first."


def client_report_off(code):
    """True when the project's client report setting is off (#233 L10); a project with no such line is on."""
    import build_dashboard
    try:
        return not build_dashboard.memory(paths.project_dir(code)).get("client_report", True)
    except Exception:                                  # a project folder that can't be read: the setting is not known to be off
        return False


def refuse_client_off(handler, kind, code):
    """The refusal for a new client draft, a client save, export or approve while the project's setting is off; None otherwise.
    Reading or opening a client report that already exists is never refused: turning the setting off deletes nothing."""
    if kind == "client" and client_report_off(code):
        return refuse(handler, CLIENT_OFF)
    return None


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
        except (LookupError, ValueError, TypeError, AttributeError):     # v2.5.1 (#239): a document edited into a shape creaite
            return refuse(handler, "That report can't be read as it is (it was changed outside creaite), so nothing was done. "
                                   "Open the report again from creaite.")         # can't read is refused, never a fault
    route.__doc__ = fn.__doc__
    return route


def draft_route(handler, req):
    """POST /api/report/draft: the report to edit (see the module's description)."""
    import client_leak
    kind, code, fri, client = target(req)
    state, path = report_doc.where(kind, code, fri, client)
    if state and not (req.get("fresh") and state == "draft"):
        doc = creaite_doc.read_report(path, kind)       # v2.5.0 audience bypass: a draft edited on disk is read as a client report
    else:
        off = refuse_client_off(handler, kind, code)       # a client report is made only while the setting is on
        if off:
            return off
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
    creaite_doc.check_audience(doc)            # v2.5.0 audience bypass: refuses a client report whose audience isn't client
    doc = creaite_doc.force_client_audience(doc)
    kind, code, fri, client = target({"kind": doc.get("kind"), "code": doc.get("project"), "week_ending": doc.get("date"),
                                      "client": doc.get("client")})
    if fri != doc["date"]:
        raise report_doc.ReportError("A report's date is its week ending, a Friday.")
    off = refuse_client_off(handler, kind, code)
    if off:
        return off
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
    doc = creaite_doc.read_report(f, "client")
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
    off = refuse_client_off(handler, kind, code)
    if off:
        return off
    draft = report_doc.draft_path(kind, code, fri, client)
    with handler_lock(handler):
        if isinstance(req.get("doc"), dict):
            saved = report_doc.save_draft(req["doc"], req.get("base_version"))     # checks it first (v2.5.0 audience bypass)
            if not saved.get("ok"):
                return answer(handler, saved)
        if not paths.resolve(draft).is_file():
            return refuse(handler, "There is no draft to approve: save the report first (a filed report is approved already).")
        stage = report_doc.stage_weekly if kind == "weekly" else report_doc.stage_client
        prop = stage(draft, force=bool(req.get("force")), code=code, fri=fri)
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


MATCH_MAX_DOCS, MATCH_MAX_DOC, MATCH_MAX_TOTAL = 60, 100_000, 1_000_000       # documents, bytes of one document, bytes of all


def match_check_route(handler, req):
    """POST /api/report/match-check: the leak findings of each client document sent, as [{code, message}] (see the module's
    description). Always the client gate, whatever audience the request names. Capped (60 documents, 100 kB each, 1 MB in all);
    over the cap it refuses with a sentence (HTTP 400) and checks nothing. Writes nothing."""
    import json
    import client_leak
    docs = req.get("docs")
    if not isinstance(docs, list) or len(docs) > MATCH_MAX_DOCS:
        return handler.send(400, {"ok": False, "message": f"Send up to {MATCH_MAX_DOCS} client reports to check."})
    sizes = [len(json.dumps(d, default=str)) for d in docs]
    if any(n > MATCH_MAX_DOC for n in sizes) or sum(sizes) > MATCH_MAX_TOTAL:
        return handler.send(400, {"ok": False, "message": "Those client reports are too large to check together: "
                                                           "send fewer, or shorter ones."})
    con = client_leak.connect()
    out = []
    for d in docs:
        creaite_doc.check(d)
        if d.get("kind") != "client":
            raise creaite_doc.DocError("Only a client report has this check.")
        # v2.5.1 (#239): read as the export reads a client report (its header derived, another project's rows dropped), so Match
        # internal is held exactly when the export would refuse the same document on its content
        out.append(client_leak.coded_findings(creaite_doc.force_client_audience(copy.deepcopy(d)), con))
    return answer(handler, {"ok": True, "findings": out})


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


def _plain_name(name, ext, own=None):
    """A typed file name made safe: one name (no folder, no leading dot, 150 characters at most) that ends with `ext`; None when it
    can't be a file name (or _name_problem refuses it). `own`: this report's filing name, which a typed name may start with."""
    name = str(name or "")
    if any(ord(c) < 32 or ord(c) == 127 for c in name):
        return None                                            # a control character (NUL, a newline, a tab...) is never in a file name
    name = " ".join(name.split())
    if not name or "/" in name or "\\" in name or name.startswith(".") or len(name) > 150:
        return None
    name = name if name.lower().endswith(ext) else name + ext
    return None if _name_problem(name, own) else name


RESERVED_NAME = re.compile(r"(?i)^(?:con|prn|aux|nul|com[0-9\u00b9\u00b2\u00b3]|lpt[0-9\u00b9\u00b2\u00b3]|conin\$|conout\$)(?:\..*)?$")
REPORT_WORDS = re.compile(r"(?i)(?:weekly|client)\s*report")


def _name_problem(name, own=None):
    """v2.5.1 (#239): why a typed export name can't be used, or None: a name Windows reserves (CON, NUL, COM1...), a character a
    file name can't hold there (< > : " | ? *), a stem ending in a dot or a space, or a name that reads as a report's filing name
    (weekly report, client report: in any case or spacing) other than this report's own (`own`, its filing name, which the name
    may start with: the clash question then says it is reserved), which belongs to a filing and could block an Approve."""
    stem = name.rsplit(".", 1)[0]
    if RESERVED_NAME.match(stem) or RESERVED_NAME.match(name) or re.search(r'[<>:"|?*]', name) or stem != stem.rstrip(". "):
        return "reserved"
    import unicodedata
    plain = " ".join(unicodedata.normalize("NFKC", name).split())
    mine = own and plain.lower().startswith(" ".join(Path(own).stem.split()).lower())
    if REPORT_WORDS.search(plain) and not mine:
        return "a report's name"
    return None


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
    except (OSError, ValueError) as e:
        for stray in folder.glob(f".{name}.part"):
            stray.unlink(missing_ok=True)
        return _not_saved(handler, f"the {label} folder can't be written to ({getattr(e, 'strerror', None) or e.__class__.__name__}).")
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
        name = _plain_name(req.get("new_name"), ext, reserved)
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
    nothing was written. Nothing is ever sent.
    v2.5.1 (#239, d): the whole export runs under the save route's lock (the live server's one LOCK): the report is read ONCE,
    checked, and exactly that document is rendered (passed through, never read again) and filed, so a save can't land between the
    check and the file. A client report's posted page is never used (f, creaite_doc._posted_page): the server renders it from the
    report, and the answer says plain: true and why."""
    kind, code, fri, client = target(req)
    fmt = req.get("fmt")
    if fmt not in FORMATS:
        return refuse(handler, "Export as html, docx or pdf.")
    off = refuse_client_off(handler, kind, code)
    if off:
        return off
    fn = export_call()
    if fn is None:
        return refuse(handler, "Exports aren't built yet in this version of creaite.")
    with handler_lock(handler):
        return _export_locked(handler, req, (kind, code, fri, client), fmt, fn)


def _export_locked(handler, req, which, fmt, fn):
    """export_route's work, under the lock: read once, check, render that document, file it."""
    kind, code, fri, client = which
    state, path = report_doc.where(kind, code, fri, client)
    if not state:
        return refuse(handler, "Save the report before exporting it.")
    doc = creaite_doc.read_report(path, kind)           # v2.5.0 audience bypass: a draft edited on disk too; another kind refused
    report_doc.same_report(doc, kind, code, fri)
    left = None
    if kind == "client":
        import client_check
        left = client_check.left_out(doc)          # the check runs before every client export, whoever asks
        if not left["ready"] or left["findings"]:
            return refuse(handler, left["not_ready"] or "Not exported: possible internal content in the client report.",
                          findings=left["findings"], left_out=left)
    filed = paths.resolve(report_doc.filed_path(kind, code, fri, client))
    folder, ext = filed.parent, creaite_doc.EXPORTS[fmt]
    name = filed.stem + ext          # the plain name for all three (Alan, 18-10-2026): HTML meets the filed report's name and asks
    label = f"{creaite_doc.project_name(code) or code} › Reports"
    where = {"folder": paths.rel(folder), "folder_label": label, "format": fmt}
    name, overwrite, asked = _settle_name(folder, name, ext, req, label, filed.name)
    if asked:
        return answer(handler, {"ok": False, **asked, **where})
    page = req.get("page") if isinstance(req.get("page"), dict) else None          # creaite_doc never uses one for a client report
    out = fn(path, fmt, file_beside=False, open_after=False, page=page, kind=kind, doc=doc)     # made in drafts/, filed below
    if not out.get("ok"):
        extra = {"findings": out["findings"]} if out.get("findings") else {}
        return _not_saved(handler, str(out.get("message") or "the report couldn't be made."), **where, **extra)
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
    for stored in req.get("paths") or list(known):                 # H3: no list asked for = all of the project's logos
        if stored not in known:
            continue
        f = paths.resolve(stored)
        if f.suffix.lower() in LOGO_TYPES and f.is_file() and not f.is_symlink() and f.stat().st_size <= LOGO_MAX:
            out[stored] = f"data:{LOGO_TYPES[f.suffix.lower()]};base64,{base64.b64encode(f.read_bytes()).decode()}"
    orphans = report_doc.orphan_logos(code)
    for o in orphans:                                               # an unused partner logo is shown with its Remove button (#228 C)
        f = paths.resolve(o["path"])
        if f.suffix.lower() in LOGO_TYPES and f.stat().st_size <= LOGO_MAX:
            out[o["path"]] = f"data:{LOGO_TYPES[f.suffix.lower()]};base64,{base64.b64encode(f.read_bytes()).decode()}"
    return answer(handler, {"ok": True, "logos": out, "list": list(known.values()), "orphans": orphans,
                            "partners": [{"kind": "partner:" + p["slug"], **p} for p in report_doc.partners(code)]})


def _plain_list(names):
    return ", ".join(names[:-1]) + " and " + names[-1] if len(names) > 1 else (names[0] if names else "")
JPEG_HINT = "A transparent PNG or SVG sits better. The picture is kept as it is."


def _logo_type(raw):
    """"png", "jpg" or "svg" from the file's own first bytes, or None when it is not a picture creaite draws."""
    import logo_check
    return logo_check.kind_of(raw)


def _logo_bytes(value):
    """The bytes of a base64 field, or None when it is missing or not base64."""
    try:
        return base64.b64decode(str(value or ""), validate=True) or None
    except ValueError:
        return None


def _no_paths(msg):
    """A message with the vault's and the home folder's absolute paths taken out (LOGO 5: an error never names a place on the disk)."""
    out = str(msg)
    for root in (str(paths.ROOT), str(Path.home())):
        out = out.replace(root, "")
    return out


def _logo_change(handler, ch):
    """Make one file change for the logos through filechange.py. Alan's own click: a delete or a replace carries a one-time approval
    for exactly that change. Returns the refusal's answer, or None when it was made."""
    import filechange
    import reach
    token = reach.APPROVALS.issue(filechange.fingerprint(ch)) if ch["op"] in ("edit", "delete") else None
    code, msg = filechange.perform(ch, token, "dashboard")
    if code == filechange.NEEDS:
        filechange.record_request(ch, msg[len("Needs approval: "):].rstrip("."))
    return None if code == 0 else refuse(handler, f"Logo not saved: {_no_paths(msg)}")


def _kind_ok(kind):
    """Whether a logo kind is well formed: firm, client, partner or partner:<slug> (a slug of at most 40 characters that does not end in
    `-original`, which is the name of a kept picture)."""
    return (isinstance(kind, str) and bool(report_doc.LOGO_KIND.match(kind)) and len(kind) <= len("partner:") + 40
            and not re.search(r"-original\Z", kind))


def _logo_target(req, orphans=False):
    """(code, kind, stem) of a logo request; raises ReportError for a project or kind creaite doesn't know. `orphans`: a remove may
    name a partner logo no partner owns now (#228 C); a save may not."""
    code, kind = str(req.get("code") or ""), req.get("kind")
    if not report_doc.CODE.match(code) or not _kind_ok(kind):
        raise report_doc.ReportError("Say which project and which logo: firm, client or a partner.")
    try:
        paths.project_dir(code)
    except LookupError:
        raise report_doc.ReportError(f"{code} isn't a project creaite knows.") from None
    names = [p["name"] for p in report_doc.partners(code)]
    if kind == "partner" and names:
        raise report_doc.ReportError(f"This project lists its partners ({_plain_list(names)}). Say which partner the logo is for.")
    if orphans and kind in {o["kind"] for o in report_doc.orphan_logos(code)}:
        return code, kind, f"{code}-partner-{kind[len('partner:'):]}"
    if kind.startswith("partner:") and kind not in report_doc.logo_kinds(code):
        listed = f"Its Partners line has {_plain_list(names)}." if names else "It has no Partners line, so no partner has a logo yet."
        raise report_doc.ReportError(f"That partner isn't in this project's Partners line. {listed} Nothing was saved.")
    return code, kind, report_doc.logo_stems(code, kind)[0]


def _logo_files(stems):
    """Every logo file of those names (a stem or a list of them) now in the logos folder: the picture drawn and the original kept."""
    stems = [stems] if isinstance(stems, str) else list(stems)
    names = set(stems) | {f"{s}-original" for s in stems}
    if not paths.REPORT_LOGOS.is_dir():
        return []
    return [f for f in sorted(paths.REPORT_LOGOS.iterdir())
            if f.is_file() and f.suffix.lower() in report_doc.LOGO_EXT and f.stem in names]


def _kind_label(code, kind):
    """What a logo is called to Alan: firm, client, or the partner's own name."""
    return next((p["name"] for p in report_doc.partners(code) if "partner:" + p["slug"] == kind), kind)


def _logo_refusal(req):
    """(raw, drawn, type, None) for a logo request that can be saved, else (None, None, None, the sentence to refuse with). The
    picture is looked into, not just its first bytes (logo_check): a sound PNG, JPEG or SVG of a sane size with nothing added."""
    import logo_check
    raw, drawn = _logo_bytes(req.get("original")), _logo_bytes(req.get("drawn"))
    kind_of = _logo_type(raw or b"")
    ext = str(req.get("ext") or "").lower().lstrip(".").replace("jpeg", "jpg")
    if not raw or not kind_of or kind_of != ext:
        return None, None, None, "That isn't a PNG, JPEG or SVG picture. Nothing was saved."
    if len(raw) > LOGO_MAX or (drawn and len(drawn) > LOGO_MAX):
        return None, None, None, "That logo is over 400 kB. Choose a smaller file. Nothing was saved."
    if drawn is not None and _logo_type(drawn) != "png":
        return None, None, None, "The trimmed copy must be a PNG. Nothing was saved."
    try:
        logo_check.inspect(raw)
        if drawn is not None:
            logo_check.inspect(drawn)
    except logo_check.LogoRefused as e:
        return None, None, None, str(e)
    return raw, drawn, kind_of, None


def _logo_links(stems, names):
    """Whether the logos folder, or a file in it with this logo's name (or one about to be written), is a symbolic link."""
    folder = paths.REPORT_LOGOS
    if folder.is_symlink():
        return True
    if not folder.is_dir():
        return False
    stems = [stems] if isinstance(stems, str) else list(stems)
    mine = set(stems) | {f"{s}-original" for s in stems}
    return any(f.is_symlink() for f in folder.iterdir() if f.stem in mine or f.name in names)


def logo_save_route(handler, req):
    """POST /api/report/logo/save (see the module's description): the logo for the firm or a project's client or partner, saved under
    its name in system/branding/logos/. A file that isn't a PNG, JPEG or SVG picture, or is over 400 kB, is refused and nothing is
    written."""
    code, kind, stem = _logo_target(req)
    raw, drawn, kind_of, why = _logo_refusal(req)
    if why:
        return refuse(handler, why)
    ext = "jpg" if kind_of == "jpg" else kind_of
    keep = [(f"{stem}-original.{ext}", raw), (f"{stem}.png", drawn)] if drawn and kind_of != "svg" else [(f"{stem}.{ext}", raw)]
    stems, label = report_doc.logo_stems(code, kind), _kind_label(code, kind)
    if _logo_links(stems, {n for n, _d in keep}):
        return refuse(handler, "A file in the logos folder is a shortcut (a symbolic link). Remove the shortcut and try again. "
                               "Nothing was saved.")
    for name, data in keep:                                        # the new files first: a failed write leaves the old logo standing
        target = paths.REPORT_LOGOS / name
        ch = {"op": "edit" if target.exists() else "create", "path": paths.rel(target), "data": data,
              "why": f"{label.capitalize()} logo added or changed from the report settings"}
        err = _logo_change(handler, ch)
        if err:
            return err
    for old in _logo_files(stems):                                 # a stale file of another type, or the old partner file, must not win
        if old.name not in dict(keep):
            err = _logo_change(handler, {"op": "delete", "path": paths.rel(old), "why": f"Replaced the {label} logo"})
            if err:
                return err
    out = {"ok": True, "logos": report_doc.logos(code), "message": f"The {label} logo is saved."}
    if kind_of == "jpg":
        out["hint"] = JPEG_HINT
    return answer(handler, out)


def logo_remove_route(handler, req):
    """POST /api/report/logo/remove (see the module's description)."""
    code, kind, stem = _logo_target(req, orphans=True)
    stems = [stem] if kind in {o["kind"] for o in report_doc.orphan_logos(code)} else report_doc.logo_stems(code, kind)
    label = _kind_label(code, kind)
    if _logo_links(stems, set()):
        return refuse(handler, "A file in the logos folder is a shortcut (a symbolic link). Remove the shortcut yourself. "
                               "Nothing was removed.")
    for old in _logo_files(stems):
        err = _logo_change(handler, {"op": "delete", "path": paths.rel(old), "why": f"Removed the {label} logo"})
        if err:
            return err
    return answer(handler, {"ok": True, "logos": report_doc.logos(code), "message": f"The {label} logo is removed."})


IMAGE_MAX = 2 * 1024 * 1024        # the same cap as a note's picture (live_server.UPLOAD_LIMIT)


def image_route(handler, req):
    """POST /api/report/image: a text section's picture, checked (PNG or JPEG, 2 MB at most, by its first bytes, never its name) and
    created through filechange.py in the project's Reports folder under `_images/`. A taken name gets a number: nothing is overwritten."""
    import filechange
    import notes
    code = str(req.get("code") or "")
    if not report_doc.CODE.match(code):
        return refuse(handler, "Say which project's report the picture is for.")
    try:
        raw = base64.b64decode(str(req.get("data") or ""), validate=True)
    except ValueError:
        return refuse(handler, "That picture couldn't be read.")
    if len(raw) > IMAGE_MAX:
        return refuse(handler, "Pictures can be 2 MB at most.")
    ext = "png" if raw.startswith(b"\x89PNG\r\n\x1a\n") else "jpg" if raw.startswith(b"\xff\xd8\xff") else None
    if not ext:
        return refuse(handler, "Only PNG or JPEG pictures.")
    folder = creaite_doc.images_dir({"project": code})
    if folder is None:
        return refuse(handler, f"{code} isn't a project creaite knows.")
    label = os.path.splitext(str(req.get("name") or ""))[0]
    with handler_lock(handler):
        named = notes.image_name(label, ext)[:-len(ext) - 1]
        target = paths.free_path(folder / "_images", named, f".{ext}")
        done, msg = filechange.perform({"op": "create", "path": paths.rel(target), "data": raw,
                                        "why": "a picture added to a report's text section"}, via="dashboard")
    if done != 0:
        return refuse(handler, msg, wait=done == filechange.NEEDS)
    return answer(handler, {"ok": True, "ref": f"_images/{target.name}"})


def images_route(handler, req):
    """POST /api/report/images: the asked-for pictures as data addresses; an address of any other shape, or a file that isn't there, is
    left out. Read only."""
    code = str(req.get("code") or "")
    if not report_doc.CODE.match(code):
        return refuse(handler, "Say which project's pictures.")
    out = {}
    for ref in list(req.get("refs") or [])[:200]:
        f = creaite_doc.text_image({"project": code}, str(ref))
        if f is not None and f.stat().st_size <= IMAGE_MAX:
            mime = "image/png" if f.suffix.lower() == ".png" else "image/jpeg"
            out[str(ref)] = f"data:{mime};base64,{base64.b64encode(f.read_bytes()).decode('ascii')}"
    return answer(handler, {"ok": True, "images": out})


HOST = {}       # the live server's own lock, run and latest_apply (live_server registers them; never a second copy of the module)


def routes(lock, run, latest_apply):
    """The report routes for live_server's route table, given its lock, its script runner and its latest_apply."""
    HOST.update(lock=lock, run=run, latest_apply=latest_apply)
    return {"/api/report/draft": guarded(draft_route), "/api/report/save": guarded(save_route),
            "/api/report/approve": guarded(approve_route), "/api/report/check": guarded(check_route),
            "/api/report/match-check": guarded(match_check_route),
            "/api/report/pick": guarded(pick_route),
            "/api/report/export": guarded(export_route), "/api/report/reveal": guarded(reveal_route),
            "/api/report/logo": guarded(logo_route), "/api/report/logo/save": guarded(logo_save_route),
            "/api/report/logo/remove": guarded(logo_remove_route), "/api/report/image": guarded(image_route),
            "/api/report/images": guarded(images_route)}
