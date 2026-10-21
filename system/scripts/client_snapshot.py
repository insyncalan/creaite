"""v2.5.1 (#239, step 2): a client report's output comes from one checked snapshot. A library: no command line.

dev/proposals/client-output-snapshot.md is the design. In short:
  - build(doc): the SNAPSHOT of a client report: the cleaned client document (creaite_doc.clean: the allow-list of keys, the header
    derived from the tracker and the project's memory, never the one stored; hidden sections and rows emptied; meta.health_diff and
    every other key the filed file never holds gone, report_doc.filed_client_data), its PICTURE TABLE (the `_images/client-<name>`
    pictures its text names, each by name and SHA-256: known gap C, a picture added for the internal report is never a client
    report's) and its LOGO TABLE (the project's logos the report ticks now, by file name and SHA-256, never a path). It is checked
    ONCE: what client_check.left_out says (ready, the client health reason, the gate's findings), client_leak.findings on the
    snapshot's own document, and the picture rule. A snapshot with a finding is never written.
  - Approve writes the snapshot beside the filed report, `<filed name>.client.json` (report_doc._file_ops, through tracker.py
    apply, so Undo takes it back); a client export with no approved snapshot (a draft, or a filed report from before 2.5.1 or
    edited since) builds one into system/staging/client-snapshots/. Every snapshot's SHA-256 is recorded in
    system/staging/client-snapshots.json (REGISTRY: hashes, dates and counts only, never a word of the report). A snapshot is never
    edited: a change is a new snapshot.
  - client_export(code, week, fmt): THE ONE way a client Word, HTML or PDF file is made. Under the live server's lock (locked()),
    it reads ONLY the snapshot (load: its SHA-256 must be one the registry recorded), derives the header again, renders it with the
    tables in force (creaite_doc.client_tables: a picture or logo is drawn only when its name and bytes are in the table), and
    checks the made file's text and pictures (client_output.check, with the tables as the allowed pictures). Any finding: the file
    is deleted and nothing is kept. creaite_doc.export, _make_export and word_export refuse a client report without TOKEN.
  - preview: Show as exported asks for the same render of a snapshot built in memory from the saved report, marked Preview, never
    written or recorded.
"""
import contextlib
import copy
import hashlib
import json
import os
import re
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import creaite_doc  # noqa: E402
import report_doc  # noqa: E402
import sweep  # noqa: E402

FORMAT, SCHEMA = "creaite-client-snapshot", 1
REGISTRY = paths.STAGING / "client-snapshots.json"
STORE = paths.STAGING / "client-snapshots"
SUFFIX = ".client.json"
TOKEN = object()                    # creaite_doc renders a client report only when handed this (client_export's own)
PICTURE_REF = re.compile(r"_images/[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.(?:png|jpe?g)", re.I)
CLIENT_PICTURE = "client-"          # gap C: the name a picture added from the client report takes (report_server.image_route)
KEEP_HASHES = 20                    # the earlier snapshots of one report the registry still knows (an Undo puts one back)


class SnapshotError(ValueError):
    """A snapshot that can't be used: refused with a sentence Alan can read (`findings` when the check found something)."""

    def __init__(self, message, findings=(), left=None):
        super().__init__(message)
        self.findings, self.left = list(findings), left


# ── the lock ─────────────────────────────────────────────────────────────────

_HELD = threading.local()
_OWN_LOCK = threading.Lock()          # outside the live server (a script, a test): a lock of its own


def _host_lock():
    """The live server's one lock (report_server.HOST, which live_server registers), or this module's own."""
    import report_server
    return report_server.HOST.get("lock") or _OWN_LOCK


@contextlib.contextmanager
def locked():
    """Hold the live server's lock (the save route's) for a client export, once per thread: an export route that holds it already
    and calls client_export inside does not take it twice."""
    if getattr(_HELD, "on", False):
        yield
        return
    with _host_lock():
        _HELD.on = True
        try:
            yield
        finally:
            _HELD.on = False


def held():
    """Whether this thread holds the lock through locked() (the tests' check that the snapshot is read under it)."""
    return bool(getattr(_HELD, "on", False))


# ── where a snapshot lives ───────────────────────────────────────────────────

def filed_snapshot(code, fri, client):
    """The stored path of the snapshot beside the filed report: `<filed name>.client.json`."""
    filed = Path(report_doc.filed_path("client", code, fri, client))
    return (filed.parent / (filed.stem + SUFFIX)).as_posix()


def store_snapshot(code, fri, client, state):
    """The stored path of a snapshot creaite builds for an export with no approved one (`state` draft or filed)."""
    stem = Path(report_doc.filed_path("client", code, fri, client)).stem
    return paths.rel(STORE / f"{stem} ({state}){SUFFIX}")


def is_snapshot_name(name):
    """Whether a file name is a client snapshot's (the Files list leaves them out)."""
    return str(name).endswith(SUFFIX)


# ── the registry (hashes and counts only) ────────────────────────────────────

def sha(text):
    """The SHA-256 of a text as UTF-8."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def key(stored):
    """A snapshot's key in the registry: the SHA-256 of its stored path (the registry names no report, project or client)."""
    return sha(str(stored))


def entry(stored):
    """The registry's entry for the snapshot at `stored`, or None."""
    return registry().get(key(stored))


def registry():
    """{key: entry} of every snapshot creaite wrote; {} when there is none or it can't be read (snapshots are then rebuilt)."""
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    snaps = data.get("snapshots") if isinstance(data, dict) else None
    return {k: v for k, v in snaps.items() if isinstance(v, dict)} if isinstance(snaps, dict) else {}


MADE = ("approve", "export")           # how a registry entry was made: Approve's checked filing, or an export's own rebuild


def record(stored, content, snap, made):
    """Record a snapshot's SHA-256 (and when, for which report, how it was made, and its counts) in the registry, keeping the
    earlier hashes of the same report (an Undo of an Approve puts an earlier snapshot back). Written whole (a temporary file, then
    replaced). v2.5.3 (#259 round 2, HIGH 1): `made` is "approve" (for_filing: the snapshot beside the filed report, built from
    the document Approve checked) or "export" (ensure: built from a file as it is on disk); only an "approve" entry at the filed
    report's own snapshot path vouches for a filed file (approved_source)."""
    if made not in MADE:
        raise ValueError(f"made must be one of {MADE}")
    reg = registry()
    old = reg.get(key(stored)) or {}
    hashes = [h for h in old.get("hashes") or [] if isinstance(h, str)]
    h = sha(content)
    hashes = ([x for x in hashes if x != h] + [h])[-KEEP_HASHES:]
    doc = snap.get("doc") or {}
    reg[key(stored)] = {"hashes": hashes, "project": snap.get("project"), "week_ending": snap.get("week_ending"),
                   "state": snap.get("state"), "made_at": snap.get("made_at"), "made": made,
                   "source_sha256": (snap.get("source") or {}).get("sha256"),
                   "sections": len(doc.get("sections") or []), "pictures": len(snap.get("pictures") or []),
                   "logos": len(snap.get("logos") or [])}
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    tmp = REGISTRY.with_name(REGISTRY.name + ".part")
    tmp.write_text(json.dumps({"format": "creaite-client-snapshots", "schema": 1, "snapshots": reg}, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    os.replace(tmp, REGISTRY)


def beside(filed):
    """The stored path of the snapshot beside the report filed at `filed` (stored or a Path): `<its name>.client.json`, the path
    filed_snapshot gives for that report."""
    rel = Path(paths.rel(creaite_doc.real(filed)))
    return (rel.parent / (rel.stem + SUFFIX)).as_posix()


def approved_source(filed):
    """v2.5.3 (#259 round 2, HIGH 1): the SHA-256 of the filed report's text that the snapshot Approve wrote beside it names as its
    source, or None. Bound to that one path: the snapshot is the one at beside(filed), its registry entry was made by Approve (an
    entry an export made is never one), its bytes are a hash that entry recorded, and its source is that same filed path. A
    snapshot an export built (system/staging/client-snapshots/) never vouches for anything."""
    rel = paths.rel(creaite_doc.real(filed))
    stored = beside(filed)
    e = entry(stored) or {}
    if e.get("made", "approve") != "approve" or not e.get("hashes"):     # (entries from before 2.5.3 were all Approve's)
        return None
    p = paths.resolve(stored)
    if p.is_symlink() or not p.is_file():
        return None
    try:
        text = p.read_text(encoding="utf-8")
        snap = json.loads(text)
    except (OSError, ValueError):
        return None
    if sha(text) not in e["hashes"] or not isinstance(snap, dict) or snap.get("state") != "filed":
        return None
    source = snap.get("source") if isinstance(snap.get("source"), dict) else {}
    if source.get("path") != rel or not isinstance(source.get("sha256"), str):
        return None
    return source["sha256"]


def dumps(snap):
    """A snapshot as the text written (sorted keys, so the same snapshot is the same bytes)."""
    return json.dumps(snap, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


# ── building and checking a snapshot ─────────────────────────────────────────

def _shown_text(doc):
    """The text of the shown sections (their text, panes and cells), where a picture reference can stand."""
    return json.dumps([s for s in doc.get("sections") or [] if isinstance(s, dict) and not s.get("hidden")], ensure_ascii=False)


def _hashes(data):
    """(SHA-256 of the bytes, SHA-256 without metadata as an export embeds them, or None for a picture that can't be read)."""
    import client_output
    return hashlib.sha256(data).hexdigest(), client_output.pic_hash(data)


def picture_table(doc):
    """([{name, sha256, stripped}], [finding]) of the pictures a client report's shown text names: only `_images/client-<name>`
    pictures (added from the client report) are a client report's; one added for the internal report is a finding (gap C). A
    picture that isn't there or can't be read is left out of the table (the export says it wasn't found)."""
    table, found = [], []
    for ref in sorted(set(PICTURE_REF.findall(_shown_text(doc)))):
        if not Path(ref).name.lower().startswith(CLIENT_PICTURE):
            found.append(f"a picture added for the internal report ({ref}) is in the client report's text: add the picture again "
                         "from the client report")
            continue
        f = creaite_doc.text_image(doc, ref)
        try:
            data = f.read_bytes() if f is not None and not creaite_doc._too_big(f) else None
        except OSError:
            data = None                 # a picture that can't be read is left out of the table: it is never drawn
        if data is not None:
            raw, stripped = _hashes(data)
            if stripped:
                table.append({"name": ref, "sha256": raw, "stripped": stripped})
    return table, found


def logo_table(code, layout):
    """[{kind, name, sha256, stripped}] of the logos a client report draws now (report_doc.client_logos), by file name, never a
    path."""
    out = []
    for lg in report_doc.client_logos(code, layout):
        f = paths.resolve(lg["path"])
        try:
            if f.is_symlink() or not f.is_file() or f.stat().st_nlink > 1 or f.parent.resolve() != paths.REPORT_LOGOS.resolve():
                continue
            raw, stripped = _hashes(f.read_bytes())
        except OSError:
            continue                    # a logo that can't be read is left out of the table: it is never drawn
        out.append({"kind": lg["kind"], "name": f.name, "sha256": raw, "stripped": stripped})
    return out


def shaped(doc):
    """The document a snapshot holds: clean (allow-listed, header derived, hidden emptied) with meta.health_diff and every key the
    filed file never holds gone (report_doc.filed_client_data)."""
    with creaite_doc.facts_once():                           # v2.6 review: the facts read once for both derives
        d = creaite_doc.clean(creaite_doc.force_client_audience(copy.deepcopy(doc)))
    d["meta"] = {k: v for k, v in (d.get("meta") or {}).items() if k != "health_diff"} if isinstance(d.get("meta"), dict) else {}
    return report_doc.filed_client_data(d)


def check(doc):
    """(left_out, [finding]) for a client document about to become a snapshot: client_check.left_out (ready, the client health
    reason, the gate's findings) and client_leak.findings on the shaped document; [] findings when it may be exported."""
    import client_check
    left = client_check.left_out(doc)
    found = list(left["findings"] or [])
    if not left["ready"]:
        found.insert(0, left["not_ready"] or "The client report isn't ready to export.")
    return left, found


def build(doc, *, source=None, state="draft", preview=False):
    """(snapshot, left_out, [finding]) for a client document (see the module's description). `source`: {path, version, sha256} of
    the file it was read from. Raises creaite_doc.DocError for a document that isn't a client report."""
    import client_leak
    creaite_doc.check(doc)
    if doc.get("kind") != "client":
        raise creaite_doc.DocError("Only a client report has a snapshot.")
    with creaite_doc.facts_once():                           # v2.6 review: the facts read once for the whole snapshot
        doc = creaite_doc.force_client_audience(copy.deepcopy(doc))
        left, found = check(doc)
        snap_doc = shaped(doc)
    found += [f for f in client_leak.findings(snap_doc) if f not in found]
    pictures, gap_c = picture_table(snap_doc)
    found += gap_c
    code = str(snap_doc.get("project") or "")
    snap = {"format": FORMAT, "schema": SCHEMA, "project": code, "week_ending": snap_doc.get("date"), "state": state,
            "preview": bool(preview), "made_at": sweep.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "source": dict(source or {}), "doc": snap_doc, "pictures": pictures,
            "logos": logo_table(code, snap_doc.get("layout"))}
    return snap, left, list(dict.fromkeys(found))


def source_of(stored, text, doc):
    """A snapshot's `source`: the file it was built from, its version and the SHA-256 of its text."""
    return {"path": stored, "version": int(doc.get("version") or 0) if str(doc.get("version") or "0").isdigit() else 0,
            "sha256": sha(text)}


def for_filing(doc, content, stored_filed):
    """(stored path, snapshot text) of the snapshot Approve writes beside the filed report: built from the document filed (`doc`, as
    report_doc._file_ops made it) and its text (`content`), checked, and its hash recorded now (the write is tracker.py apply's).
    Raises SnapshotError when the check finds anything (nothing is approved)."""
    snap, _left, found = build(doc, source={"path": stored_filed, "version": int(doc.get("version") or 0), "sha256": sha(content)},
                               state="filed")
    if found:
        raise SnapshotError("Not approved: possible internal content in the client report: " + "; ".join(found), found)
    stored = filed_snapshot(snap["project"], snap["week_ending"], doc.get("client"))
    text = dumps(snap)
    record(stored, text, snap, "approve")
    return stored, text


# ── reading a snapshot back ──────────────────────────────────────────────────

def load(stored, code, fri):
    """The snapshot at `stored`, read once and verified: its SHA-256 must be one the registry recorded for that path, its format
    and schema creaite's, its project and week the ones asked for. Raises SnapshotError."""
    p = paths.resolve(stored)
    try:
        text = p.read_text(encoding="utf-8") if not p.is_symlink() else None
    except OSError:
        text = None
    if text is None:
        raise SnapshotError("The checked copy of this client report isn't there. Export it again.")
    if sha(text) not in ((entry(stored) or {}).get("hashes") or []):
        raise SnapshotError("The checked copy of this client report was changed outside creaite, so it isn't exported. "
                            "Approve the report again.")
    try:
        snap = json.loads(text)
    except ValueError:
        raise SnapshotError("The checked copy of this client report can't be read. Approve the report again.") from None
    if not isinstance(snap, dict) or snap.get("format") != FORMAT or snap.get("schema") != SCHEMA \
            or (snap.get("project"), snap.get("week_ending")) != (code, fri) or not isinstance(snap.get("doc"), dict):
        raise SnapshotError("The checked copy isn't this client report, so nothing was exported.")
    return snap


def _filed_current(stored, filed_text):
    """Whether the snapshot beside the filed report is the one for the filed file as it is now: True when it is (recorded, and its
    source the filed file's text); False when there is none to use (no snapshot, none recorded: a report filed before 2.5.1 or a
    registry deleted; or the filed file edited since), so one is built from the filed file and checked. Raises SnapshotError when
    a recorded snapshot was changed on disk since creaite wrote it."""
    p = paths.resolve(stored)
    known = (entry(stored) or {}).get("hashes") or []
    if not known or not (p.is_file() or p.is_symlink()):
        return False
    try:
        text = p.read_text(encoding="utf-8") if not p.is_symlink() else ""
    except OSError:
        text = ""                       # unreadable: not one creaite wrote, refused below
    if sha(text) not in known:
        raise SnapshotError("The checked copy of this client report was changed outside creaite, so it isn't exported. "
                            "Approve the report again.")
    try:
        snap = json.loads(text)
    except ValueError:
        return False                    # recorded but not JSON can't happen; built again from the filed file if it does
    return isinstance(snap, dict) and (snap.get("source") or {}).get("sha256") == sha(filed_text)


def read_once(path):
    """(text, document) of the client report file at `path`, read ONCE: the document parsed from exactly those bytes, read as a
    client report (creaite_doc.force_client_audience); a file of another kind is refused (DocError). v2.5.3 (#259, K2): its
    sections' audience derived as creaite_doc.read_report derives it (derive_sections: a text section is the client's only in a
    file creaite itself wrote), never taken from the file."""
    raw = creaite_doc.read_raw(path)
    text = raw.decode("utf-8", errors="replace")
    doc = creaite_doc.loads(text)
    if doc.get("kind") != "client":
        raise creaite_doc.DocError("That file isn't this report (its kind was changed), so nothing was done. "
                                   "Open the report again from creaite.")
    return text, creaite_doc.force_client_audience(creaite_doc.derive_sections(doc, creaite_doc.creaite_wrote(path, raw)))


def _built(code, fri, client, path, state, preview):
    """(snapshot, left_out) built from the report file at `path`, checked; raises SnapshotError with the findings."""
    text, doc = read_once(path)
    report_doc.same_report(doc, "client", code, fri)
    snap, left, found = build(doc, source=source_of(path, text, doc), state=state, preview=preview)
    if found:
        again = " again" if state == "filed" else ""
        raise SnapshotError(f"This client report can't be exported{again}: " + "; ".join(found), found, left)
    return snap, left


def ensure(code, fri, client, preview=False):
    """(stored path or None for a preview, snapshot, left_out) of the snapshot an export of the report renders: the approved one
    beside the filed report while it is the filed file's; else one built now from the draft (or from a filed report from before
    2.5.1, or edited since), checked and written to system/staging/client-snapshots/ (a preview: built, checked, never written).
    Raises SnapshotError (and report_doc.ReportError / creaite_doc.DocError for a report that isn't there or isn't this one)."""
    state, path = report_doc.where("client", code, fri, client)
    if not state:
        raise report_doc.ReportError("Save the report before exporting it.")
    if state == "filed":
        stored = filed_snapshot(code, fri, client)
        try:
            filed_text = paths.resolve(path).read_text(encoding="utf-8", errors="replace")
        except OSError:                 # v2.5.3 (#259 round 2, LOW 7): a sentence, never a fault
            raise SnapshotError("The filed client report can't be read (creaite isn't allowed to open it), so nothing was "
                                "exported.") from None
        if _filed_current(stored, filed_text):
            return (None if preview else stored), load(stored, code, fri), None
    snap, left = _built(code, fri, client, path, state, preview)
    if preview:
        return None, snap, left
    stored = store_snapshot(code, fri, client, state)
    text = dumps(snap)
    p = paths.resolve(stored)
    p.parent.mkdir(parents=True, exist_ok=True)
    record(stored, text, snap, "export")     # #259 round 2, HIGH 1: an export's own rebuild, never a source of trust
    tmp = p.with_name(p.name + ".part")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, p)
    return stored, load(stored, code, fri), left


# ── rendering a snapshot: the one client export ──────────────────────────────

def render_doc(snap):
    """The document a snapshot renders: its own document with the header derived again now (project name, client, audience, title,
    logos: creaite_doc.derive_client), never anything else stored."""
    doc = copy.deepcopy(snap["doc"])
    doc["kind"], doc["project"], doc["date"] = "client", snap["project"], snap["week_ending"]
    return creaite_doc.derive_client(doc)


def tables(snap):
    """{pictures: {name: sha256}, logos: {file name: sha256}, allowed: every hash an output may embed} of a snapshot (what
    creaite_doc.client_tables puts in force while it renders)."""
    pics = {p["name"]: p["sha256"] for p in snap.get("pictures") or [] if isinstance(p, dict) and p.get("name")}
    logos = {x["name"]: x["sha256"] for x in snap.get("logos") or [] if isinstance(x, dict) and x.get("name")}
    allowed = {h for x in (snap.get("pictures") or []) + (snap.get("logos") or []) if isinstance(x, dict)
               for h in (x.get("sha256"), x.get("stripped")) if isinstance(h, str)}
    return {"pictures": pics, "logos": logos, "allowed": allowed}


def _fail(fmt, message, **extra):
    """client_export's answer when nothing was made."""
    return {"ok": False, "format": fmt, "message": message, **extra}


def client_export(code, fri, fmt, *, client=None, preview=False, settle=None):
    """THE client export (see the module's description): the report's snapshot rendered as `fmt` (html, docx or pdf) into
    system/staging/drafts/, its output checked; never from a page the browser drew (v2.5.1 step 3: there is no `page`). `preview`:
    the snapshot is built in memory and marked Preview (Show as exported).
    `settle`: called once the snapshot passed its check and before anything is rendered; an answer from it (a taken file name)
    is passed back as {ok: false, asked}. Returns {ok, path, format, snapshot, sha256, preview, left_out} or {ok: false, message,
    findings, left_out, stage}; `stage` is "check" when the snapshot's check refused it, "output" when the made file's did."""
    if fmt not in creaite_doc.EXPORTS:
        return _fail(fmt, f"creaite exports to HTML, Word or PDF; not {fmt!r}.")
    client = creaite_doc.project_client(code) if client is None else client          # the project's client (v2.5.0)
    with locked():
        try:
            stored, snap, left = ensure(code, fri, client, preview=preview)
        except SnapshotError as e:
            return _fail(fmt, str(e), findings=e.findings, left_out=e.left, stage="check")
        asked = settle() if settle else None
        if asked:
            return {"ok": False, "asked": asked}
        doc = render_doc(snap)
        stem = Path(report_doc.filed_path("client", code, fri, client)).stem
        with creaite_doc.client_tables(tables(snap)):
            out = creaite_doc.export(f"system/staging/drafts/{stem}.html", fmt, file_beside=False, open_after=False,
                                     kind="client", doc=doc, token=TOKEN)
    out.update(snapshot=stored, preview=bool(preview), left_out=left)
    if stored:
        out["sha256"] = sha(paths.resolve(stored).read_text(encoding="utf-8"))
    if not out.get("ok"):
        out["stage"] = "output"
    return out


def preview_html(code, fri, client=None):
    """{ok, html, preview, identity} for Show as exported: the HTML export of the report's snapshot (a preview one, built from the
    saved report and never written), made and checked as an export is, then read and deleted; or {ok: false, message, findings}.
    `identity` names the report the page is of (project, week, client, version), so the page uses an answer only for the report it
    shows (P12)."""
    client = creaite_doc.project_client(code) if client is None else client
    out = client_export(code, fri, "html", client=client, preview=True)
    ident = {"code": code, "week_ending": fri, "client": client or ""}
    if not out.get("ok"):
        return {"ok": False, "message": out.get("message"), "findings": out.get("findings") or [], "identity": ident}
    p = paths.resolve(out["path"])
    try:
        html = p.read_text(encoding="utf-8")
    finally:
        p.unlink(missing_ok=True)
    state, path = report_doc.where("client", code, fri, client)
    try:
        version = int(creaite_doc.read(path).get("version") or 0) if state else 0
    except (creaite_doc.DocError, OSError, ValueError):
        version = 0
    return {"ok": True, "html": html, "preview": True, "identity": {**ident, "version": version}}
