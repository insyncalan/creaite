"""creaite's own document format (v2.1.0 P1; BL-335, BL-336, BL-338). Standard library only. A library: no command line.

A weekly report, a client report or a meeting's minutes is one .html file: a self-contained A4 page rendered from the data (inline
CSS, no script but the data block, nothing loaded from anywhere, so it opens in any browser) and a
<script type="application/json" id="creaite-data"> block holding the data. The data is the record; the page is always rendered from
it, so the filed page and every export match. The data block's shape is in dev/sprints/v210-contract.md.

Saving goes through filechange.py: a new file is a create, a later save an edit (the earlier version backed up, logged and
undoable). Hidden sections, rows and figures never reach the page, an export or the file (clean). Search reads every shown section
(search_text, called by tracker.text_of).

Exports (P2, `export`): HTML (the page without the data block), Word (the kind's firm template, filled by docx_tools.py) and PDF
(Chrome's print to PDF of the HTML export), each made from the data and filed beside the document through filechange.py.
"""
import copy
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

FORMAT = "creaite-doc"
SCHEMA = 1
KINDS = ("weekly", "client", "minutes")
AUDIENCES = ("internal", "client", "distributed")
STATES = ("draft", "approved")
FOLDER = {"weekly": "weekly_reports", "client": "client_reports", "minutes": "minutes"}
REPORT_KIND = {"weekly": "Weekly report", "client": "Client report"}
DATA_ID = "creaite-data"
BLOCK = re.compile(r'<script type="application/json" id="creaite-data">(.*?)</script>', re.S)
HIDDEN_KEEP = ("id", "type", "heading", "default_heading", "hidden")
TEXT_TYPE = "freetext"       # H5, #218: a section Alan adds anywhere, named by him, written in the one editor with the Notes profile
DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")


class DocError(ValueError):
    """Why a document can't be read or written, as a plain sentence for Alan."""


def now():
    """The time now as YYYY-MM-DD HH:MM:SS."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def project_name(code):
    """A project's full name (BL-101); '' for an unknown code or when there is no tracker database."""
    import tracker
    try:
        label = tracker.project_label(code)
    except SystemExit:      # tracker.connect exits when there is no database: the name is then left out
        return ""
    return "" if not label or label == code else label


# ── The document ─────────────────────────────────────────────────────────────

def new(kind, project, title, date, sections=(), *, audience=None, client=None, layout=None, items=None, sources=None,
        meta=None):
    """A schema-1 document, version 0 and a draft; nothing is written. Raises DocError for a kind, audience or date it can't hold."""
    audience = audience or ("client" if kind == "client" else "internal")
    doc = {"format": FORMAT, "schema": SCHEMA, "kind": kind, "audience": audience, "project": project,
           "project_name": project_name(project) if project != "_portfolio" else "", "title": title, "date": date,
           "client": client, "version": 0, "saved_at": None, "state": "draft", "approved_at": None, "based_on": None,
           "layout": dict(layout or {}), "sections": [dict(s) for s in sections], "items": dict(items or {}),
           "sources": list(sources or []), "meta": dict(meta or {})}
    check(doc)
    return doc


def is_client(doc):
    """v2.5.0 audience bypass: whether a document is read as one a client may see. A client report is one whatever its audience says
    (or with none), and a document whose audience is client or distributed is one whatever its kind."""
    return doc.get("kind") == "client" or doc.get("audience") in ("client", "distributed")


def project_client(code):
    """The project's client (its memory's Client / partner line, one line, 80 characters at most), or None. Never raises."""
    try:
        import build_dashboard
        name = str(build_dashboard.memory(paths.project_dir(code)).get("client") or "")
    except Exception:  # noqa: BLE001  an unknown project or a memory that can't be read: no client name
        return None
    return " ".join(name.split())[:80] or None


def force_client_audience(doc):
    """v2.5.0 audience bypass: the document with a client report's audience set to "client" (whatever it was, or when it is missing),
    so the client gate (client_leak.findings, make_safe), which reads the audience, always checks a client report as one; and its
    header fields the gate never reads, `project_name` and `client`, derived again from the tracker (the project's name) and the
    project's memory (its client), whatever was sent or stored: they are shown in the header and the page title and name the files.
    Changed in place and returned. Any other kind is left as it is: a weekly report or minutes whose audience is client or
    distributed is already read as client by is_client and by the gate, and its kind decides where it is filed."""
    if isinstance(doc, dict) and doc.get("kind") == "client":
        derive_client(doc)
        drop_other_projects(doc)
    return doc


def derive_client(doc):
    """v2.5.1 (#239, b): a client report's header, made again from the tracker, the project's memory and its logo files, in place:
    its audience (always client), `project_name`, `client`, and the header section's label, client and logos
    (report_doc.client_logos: the project's files the report and the project's setting tick now). Whatever a draft stored there (a
    picture's path, a logo unticked since, another name) is never kept. Any other document is returned as it is."""
    if not (isinstance(doc, dict) and doc.get("kind") == "client"):
        return doc
    import report_doc
    code = str(doc.get("project") or "")
    doc["audience"] = "client"
    doc["project_name"] = project_name(code) if code else ""
    doc["client"] = project_client(code) if code else None
    logos = report_doc.client_logos(code, doc.get("layout")) if report_doc.CODE.match(code) else []
    for s in doc.get("sections") or []:
        if isinstance(s, dict) and s.get("type") == "header":
            data = s.get("data") if isinstance(s.get("data"), dict) else {}
            s["data"] = {**data, "label": "Client report", "client": doc["client"] or "", "logos": [dict(x) for x in logos]}
    return doc


def drop_other_projects(doc):
    """v2.5.0 (B): a client report's rows, source tags, milestone lists and items that name another project's item are dropped, in
    place: a client report shows its own project's items only, whatever another project lets a client see."""
    import client_leak
    import tracker
    code = str(doc.get("project") or "").upper()
    bad = {r for r in client_leak.refs(doc) if tracker.item_table(r) is not None and not str(r).upper().startswith(code + "-")}
    if bad:
        doc["sections"] = [client_leak._drop_section_refs(s, bad) if isinstance(s, dict) else s for s in doc.get("sections") or []]
        doc["items"] = {k: v for k, v in (doc.get("items") or {}).items() if k not in bad}
    return doc


def check_audience(doc):
    """v2.5.0 audience bypass: raise DocError for a client report whose audience isn't "client" (or is missing), with check()'s
    other refusals first. Saving (the save and approve routes, report_doc.save_draft) calls it: a client report is never saved as
    anything else."""
    check(doc)
    if doc.get("kind") == "client" and doc.get("audience") != "client":
        raise DocError("A client report's audience is always client: this one says "
                       f"{doc.get('audience', 'nothing')!r}, so nothing was saved. Open the client report again and save it from there.")


def read_report(path, kind=None):
    """read(path), with a client report read as one (force_client_audience): its audience client and its header fields derived
    again, however the file was edited on disk. Every place that approves, files, exports or checks a stored report reads it so.
    `kind`: the kind the caller's route or path expects; a file whose own kind is anything else (edited on disk) is refused
    (DocError), never read as another kind (v2.5.0: a client draft edited to say weekly or minutes escaped the client gate)."""
    doc = read(path)
    if kind is not None and doc.get("kind") != kind:
        raise DocError("That file isn't this report (its kind was changed), so nothing was done. Open the report again from creaite.")
    return force_client_audience(doc)


def check(doc):
    """Raise DocError when the document's shape is wrong: the kind, audience, state, date and the sections' ids."""
    if not isinstance(doc, dict) or doc.get("format") != FORMAT:
        raise DocError("That isn't a creaite document.")
    if doc.get("kind") not in KINDS:
        raise DocError(f"A creaite document is a {', '.join(KINDS)}; not {doc.get('kind')!r}.")
    if doc.get("audience", "internal") not in AUDIENCES or doc.get("state", "draft") not in STATES:
        raise DocError("Its audience or state isn't one creaite knows.")
    if not DATE.match(str(doc.get("date") or "")):
        raise DocError("Its date must be YYYY-MM-DD.")
    check_sections(doc.get("sections") or [])


def check_sections(sections):
    """Raise DocError unless every section is an object with its own id."""
    ids = [s.get("id") for s in sections if isinstance(s, dict)]
    if len(ids) != len(sections) or not all(isinstance(i, str) and i for i in ids) or len(set(ids)) != len(ids):
        raise DocError("Every section needs its own id.")
    for s in sections:
        if s.get("type") == TEXT_TYPE and (not isinstance(s.get("text", ""), str) or not isinstance(s.get("heading", ""), str)):
            raise DocError("A text section's heading and text must be text.")


def _stub_row(row):
    """A hidden row as it is kept: its reference only."""
    return {"ref": row.get("ref"), "shown": False}


def _clean_section(s, keep_text=False):
    """A section with its hidden content dropped (a hidden section keeps only its place and heading). `keep_text` (the saved working
    draft only: H5, Alan's own words can't be refilled) also keeps a hidden text section's words; a filed, exported or client file
    never does (v240-leak2)."""
    if s.get("hidden"):
        keep = HIDDEN_KEEP + (("text", "audience") if keep_text and s.get("type") == TEXT_TYPE else ())
        return {k: s[k] for k in keep if k in s}
    out = dict(s)
    if isinstance(s.get("rows"), list):
        out["rows"] = [r if r.get("shown", True) else _stub_row(r) for r in s["rows"]]
    if isinstance(s.get("figures"), list):
        out["figures"] = [f if f.get("shown", True) else {"key": f.get("key"), "shown": False} for f in s["figures"]]
    return out


def _hidden_refs(sections):
    """Every item reference in hidden sections and hidden rows."""
    refs = set()
    for s in sections:
        rows = s.get("rows") or []
        refs |= {r.get("ref") for r in rows if s.get("hidden") or not r.get("shown", True)}
        if s.get("hidden"):
            refs |= {t.get("ref") for t in s.get("tags") or []} | set((s.get("data") or {}).get("milestones") or [])
    return {r for r in refs if r}


def _visible_text(sections):
    """The cleaned sections as text, without hidden sections or hidden rows: where a kept item must be named."""
    shown = [{**s, "rows": [r for r in s.get("rows") or [] if r.get("shown", True)]} for s in sections if not s.get("hidden")]
    return json.dumps(shown, ensure_ascii=False)


def _internal_text(doc, s):
    """True for a text section that belongs to the internal report and is in a client or distributed document: it was never matched
    or written there (H5, #218), so no output shows it. v2.5.1: only a section whose audience is exactly "client" was matched; any
    other spelling ("Internal", " internal", "weekly", none) is the internal report's."""
    return s.get("type") == TEXT_TYPE and is_client(doc) and s.get("audience") != "client"


# ── v2.5.1 (#239, a): the keys a client report may hold ──────────────────────
# A client report holds only these keys, at every level; anything else (a key the gate never reads, a section's `ref` or
# `milestones`) is dropped by client_shape, which clean (so every render, export, save and the gate's own reading, client_leak.doc_text)
# and filing (report_doc.filed_client_data) use. Values are kept as they are: the gate reads every one that is left.
TOP_KEYS = ("format", "schema", "kind", "audience", "project", "project_name", "title", "date", "client", "version", "saved_at",
            "state", "approved_at", "based_on", "layout", "sections", "items", "sources", "meta")
SECTION_KEYS = ("id", "type", "heading", "default_heading", "hidden", "text", "audience", "data", "rows", "columns", "figures",
                "panes", "tags")
DATA_KEYS = ("label", "client", "period_start", "period_end", "facts_week", "week_ending", "logos", "flag", "timeline", "milestones")
ROW_KEYS, COLUMN_KEYS, FIGURE_KEYS = ("ref", "cells", "shown", "source"), ("key", "label"), ("key", "label", "value", "note", "shown")
PANE_KEYS, TAG_KEYS, SOURCE_KEYS, BASED_KEYS = ("title", "text"), ("ref", "text"), ("ref", "label"), ("path", "version")
META_KEYS = ("period_start", "period_end", "locked", "facts_on", "facts_week", "health_diff")
LAYOUT_KEYS = ("order", "hidden", "headings", "glance", "logos", "milestones", "rows")
REF_LISTS = ("timeline", "milestones")


def _only(x, keys):
    """A dict with only `keys` (a non-dict is dropped: None)."""
    return {k: x[k] for k in keys if k in x} if isinstance(x, dict) else None


def _list_of(x, keys):
    """A list of dicts, each with only `keys` (anything not a dict is dropped)."""
    return [d for d in (_only(v, keys) for v in x) if d is not None] if isinstance(x, list) else []


def _shape_data(d):
    """A section's data with only DATA_KEYS; its milestone lists hold item references (strings) only."""
    out = _only(d, DATA_KEYS) or {}
    for k in REF_LISTS:
        if k in out:
            out[k] = [r for r in out[k] if isinstance(r, str)] if isinstance(out[k], list) else []
    if "logos" in out:
        out["logos"] = _list_of(out["logos"], ("kind", "path"))
    return out


SECTION_LISTS = {"rows": ROW_KEYS, "columns": COLUMN_KEYS, "figures": FIGURE_KEYS, "panes": PANE_KEYS, "tags": TAG_KEYS}


def _shape_section(s):
    """One section with only SECTION_KEYS, its rows, columns, figures, panes and tags each with only their own keys."""
    out = _only(s, SECTION_KEYS)
    if out is None:
        return None
    for k, keys in SECTION_LISTS.items():
        if k in out:
            out[k] = _list_of(out[k], keys)
    if "data" in out:
        out["data"] = _shape_data(out["data"])
    return out


def client_shape(doc):
    """v2.5.1 (#239, a): a copy of a client report holding only the keys creaite writes (TOP_KEYS, SECTION_KEYS and the rest above):
    whatever else a draft carries (sent, or edited on disk) is never read by the gate, so it never reaches a file or an export. A
    document that isn't a client report is returned as it is."""
    if not (isinstance(doc, dict) and doc.get("kind") == "client"):
        return doc
    out = _only(copy.deepcopy(doc), TOP_KEYS)
    if "sections" in out:
        out["sections"] = [x for x in (_shape_section(s) for s in out["sections"] or []) if x is not None]
    for k, keys in (("meta", META_KEYS), ("layout", LAYOUT_KEYS), ("based_on", BASED_KEYS)):
        if isinstance(out.get(k), dict):
            out[k] = _only(out[k], keys)
    if "sources" in out:
        out["sources"] = _list_of(out["sources"], SOURCE_KEYS)
    if "items" in out:
        out["items"] = {k: v for k, v in out["items"].items() if isinstance(v, dict)} if isinstance(out["items"], dict) else {}
    return out


def clean(doc, keep_text=False):
    """A copy with hidden sections, rows and figures emptied, and the items only they named dropped. check()s it first. A text section
    of the internal report that sits in a client document unmatched is dropped (H5, #218). v2.5.1: a client report holds only its
    known keys (client_shape) and its header is derived again (derive_client), whatever was stored."""
    check(doc)
    out = derive_client(client_shape(doc)) if doc.get("kind") == "client" else copy.deepcopy(doc)
    out["sections"] = [s for s in out.get("sections") or [] if not _internal_text(out, s)]
    hidden = _hidden_refs(out.get("sections") or [])
    out["sections"] = [_clean_section(s, keep_text) for s in out.get("sections") or []]
    visible = _visible_text(out["sections"])
    out["items"] = {k: v for k, v in (out.get("items") or {}).items() if k not in hidden or k in visible}
    return out


# ── The file ─────────────────────────────────────────────────────────────────

def data_json(doc):
    """The data block's JSON, safe inside a <script> element: every '<' written as \\u003c, which JSON reads back as it was."""
    return json.dumps(doc, ensure_ascii=False, indent=1).replace("<", "\\u003c")


def dumps(doc, keep_text=False):
    """The whole file: the page with the data block. `keep_text`: see clean (the working draft only)."""
    return render(doc, editing=True, keep_text=keep_text)


def loads(text):
    """The data block of a file's text, upgraded to this schema. Raises DocError."""
    m = BLOCK.search(text or "")
    if not m:
        raise DocError("That isn't a creaite document (no creaite-data block).")
    try:
        doc = json.loads(m.group(1))
    except ValueError:
        raise DocError("Its data isn't valid JSON.") from None
    if not isinstance(doc, dict) or doc.get("format") != FORMAT:
        raise DocError("That isn't a creaite document (no creaite-data block).")
    if not isinstance(doc.get("schema"), int) or doc["schema"] > SCHEMA:
        raise DocError(f"It was saved by a newer creaite (schema {doc.get('schema')}); update creaite to open it.")
    return doc        # schema 1 is the first: nothing to upgrade yet


def real(path):
    """A stored path (projects/…, a vault path) or a Path, as a real Path."""
    return path if isinstance(path, Path) else paths.resolve(str(path))


def read(path):
    """The document at `path` (stored or a Path). Raises DocError."""
    p = real(path)
    if not p.is_file():
        raise DocError("That file isn't there.")
    return loads(p.read_text(encoding="utf-8", errors="replace"))


def is_doc(path):
    """Whether `path` is a .html file holding a creaite-data block. Never raises."""
    try:
        p = real(path)
        return p.suffix.lower() == ".html" and p.is_file() and bool(BLOCK.search(p.read_text(encoding="utf-8", errors="ignore")))
    except (OSError, ValueError):
        return False


# ── The page ─────────────────────────────────────────────────────────────────

CSS = """
:root{color-scheme:light}
body{margin:0;background:#e9eaee;font:14px/1.5 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif;color:#1d2433}
.page{box-sizing:border-box;width:210mm;min-height:297mm;margin:24px auto;padding:18mm 16mm;background:#fff;
box-shadow:0 1px 4px rgba(0,0,0,.15)}
header.doc{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid #1d2433;margin-bottom:14px}
header.doc h1{font-size:20px;margin:0 0 6px}
header.doc .sub{color:#555;font-size:12.5px}
section{margin:0 0 16px;break-inside:avoid-page}
section h2{font-size:15px;margin:0 0 6px;border-bottom:1px solid #d6d9e0;padding-bottom:3px}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th,td{border:1px solid #d6d9e0;padding:4px 6px;text-align:left;vertical-align:top}
th{background:#f3f4f7}
.figures{display:flex;flex-wrap:wrap;gap:10px}
.figure{border:1px solid #d6d9e0;border-radius:6px;padding:6px 10px;min-width:110px}
.figure b{display:block;font-size:18px}
.panes{display:flex;gap:14px}.panes>div{flex:1}
.flag{font-weight:700}
blockquote{margin:0 0 8px;padding:0 0 0 12px;border-left:3px solid #d6d9e0;color:#555}blockquote p{margin:0}
.ft h3{font-size:14px;margin:10px 0 4px}.ft h4{font-size:13px;margin:8px 0 4px}
.ft h5,.ft h6{font-size:12.5px;font-style:italic;margin:6px 0 3px}
.ft p{margin:0 0 8px}.ft ul,.ft ol{margin:0 0 8px;padding-left:22px}.ft ul.tasks{list-style:none;padding-left:4px}
.ft li>ul,.ft li>ol{margin:2px 0}
pre{background:#f3f4f7;border:1px solid #d6d9e0;border-radius:4px;padding:8px 10px;margin:0 0 8px;
font:12px/1.45 ui-monospace,Menlo,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere}
code{font:12px ui-monospace,Menlo,Consolas,monospace;background:#f3f4f7;padding:0 3px;border-radius:3px}
pre code{background:none;padding:0}
.ft table{margin:0 0 8px}.ft figure{margin:0 0 8px}.ft figure img{max-width:100%;height:auto}
.ft figcaption{font-size:12px;color:#555}
.ft a{color:#1a4fa0}.ft hr{border:0;border-top:1px solid #d6d9e0;margin:8px 0}
@media print{body{background:#fff}.page{margin:0;box-shadow:none;width:auto;min-height:0;padding:0}@page{size:A4;margin:16mm}}
"""


def esc(t):
    """Text escaped for HTML; None becomes ''."""
    return html.escape(str(t if t is not None else ""), quote=True)


def md_html(text):
    """Markdown (as the one editor writes it) as safe HTML: paragraphs, lists and bold; links keep their text only."""
    import prep_page
    return prep_page.blocks_html(prep_page.md_blocks(text))


# ── The text section (H5, #218) ──────────────────────────────────────────────
# A section of type "freetext" holds Markdown as the one editor (Notes profile) writes it: headings, bold, italic, strike, inline and
# block code, lists, checklists, quotes, links, tables and pictures. This is its reader: a small Markdown parser (text_blocks) whose
# blocks the HTML renderer (text_html) and the Word writer (_Word.freetext) both read, so the two agree. Everything is escaped: raw
# HTML in the text is shown as the characters typed, never passed through. A picture is read only from `_images/<name>.png|jpg` in the
# project's reports folder (images_dir): any other address is never opened.

TEXT_IMAGE = re.compile(r"^_images/[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.(?:png|jpe?g)$", re.I)
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})\s*([^`\s]*)[^`]*$")
_HEAD = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
_RULE = re.compile(r"^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$")
_ITEM = re.compile(r"^([ \t]*)([-*+]|\d{1,9}[.)])[ \t]+(.*)$")
_EMPTY_ITEM = re.compile(r"^([ \t]*)([-*+]|\d{1,9}[.)])[ \t]*$")
_TABLE_SEP = re.compile(r"^[ \t]*\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$")
_TASK = re.compile(r"^\[([ xX])\](?:[ \t]+(.*))?$")
_IMG_LINE = re.compile(r"^\s*!\[([^\]\n]*)\]\(([^)\s]+)\)\s*$")
MAX_TEXT_DEPTH = 8                    # quotes in quotes and lists in lists: deeper than this is plain text


class TextBlock:
    """One block of a text section's Markdown: `kind` (h, p, code, hr, table, img, quote, list), its `data`, and the lines it came from
    (`lo` up to but not including `hi`, of the lines that were read)."""
    __slots__ = ("kind", "data", "lo", "hi")

    def __init__(self, kind, data, lo, hi):
        """A block."""
        self.kind, self.data, self.lo, self.hi = kind, data, lo, hi


def _indent(line):
    """The width of a line's leading whitespace (a tab counts four)."""
    return len(line[:len(line) - len(line.lstrip(" \t"))].expandtabs(4))


def _table_at(line, nxt):
    """True when `line` is a table's header row (a line with a bar) and `nxt` its separator row."""
    return nxt is not None and "|" in line and "|" in nxt and "-" in nxt and bool(_TABLE_SEP.match(nxt))


def _starts_block(line, nxt):
    """True when `line` begins something that is not a paragraph's next line."""
    return bool(_FENCE.match(line) or _HEAD.match(line) or _RULE.match(line) or _ITEM.match(line) or _IMG_LINE.match(line)
                or line.lstrip().startswith(">") or _table_at(line, nxt))


def _cells(line):
    """A table row's cells: split on bars not escaped, outer bars dropped, each cell trimmed (an escaped bar is a bar)."""
    t = line.strip()
    t = t[1:] if t.startswith("|") else t
    t = t[:-1] if t.endswith("|") and not t.endswith("\\|") else t
    return [c.replace("\\|", "|").strip() for c in re.split(r"(?<!\\)\|", t)]


def text_blocks(text):
    """The blocks of a text section's Markdown, in order (see TextBlock). Never raises; an odd line is a paragraph."""
    lines = str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return _read(lines, 0, len(lines), 0)


def _fence_end(lines, i, hi, fence):
    """The line that closes the fence opened at lines[i] (a line of the same mark, at least as long), or `hi` when none does."""
    for j in range(i + 1, hi):
        t = lines[j].strip()
        if t.startswith(fence[0] * len(fence)) and not t.strip(fence[0]):
            return j
    return hi


def _read(lines, lo, hi, depth):
    """The blocks of lines[lo:hi]."""
    out, i = [], lo
    while i < hi:
        if not lines[i].strip():
            i += 1
            continue
        block, i = _next_block(lines, i, hi, depth)
        out.append(block)
    return out


def _next_block(lines, i, hi, depth):
    """(the block that starts at lines[i], the line after it): the first form that fits, else a paragraph."""
    for take in (_fenced, _heading, _rule, _picture, _read_table, _quote, _listed):
        got = take(lines, i, hi, depth)
        if got:
            return got
    return _paragraph(lines, i, hi)


def _fenced(lines, i, hi, _depth):
    """A fenced code block."""
    m = _FENCE.match(lines[i])
    if not m:
        return None
    j = _fence_end(lines, i, hi, m.group(1))
    return TextBlock("code", (m.group(2), "\n".join(lines[i + 1:j])), i, min(j + 1, hi)), min(j + 1, hi)


def _heading(lines, i, _hi, _depth):
    """A heading of one to six levels."""
    m = _HEAD.match(lines[i])
    return (TextBlock("h", (len(m.group(1)), m.group(2)), i, i + 1), i + 1) if m else None


def _rule(lines, i, _hi, _depth):
    """A horizontal rule."""
    return (TextBlock("hr", None, i, i + 1), i + 1) if _RULE.match(lines[i]) else None


def _picture(lines, i, _hi, _depth):
    """A picture on a line of its own."""
    m = _IMG_LINE.match(lines[i])
    return (TextBlock("img", (m.group(1).strip(), m.group(2)), i, i + 1), i + 1) if m else None


def _read_table(lines, i, hi, _depth):
    """A table: a header row, the separator row, then rows while they hold a bar."""
    if not _table_at(lines[i], lines[i + 1] if i + 1 < hi else None):
        return None
    j = i + 2
    while j < hi and lines[j].strip() and "|" in lines[j]:
        j += 1
    return TextBlock("table", (_cells(lines[i]), [_cells(x) for x in lines[i + 2:j]]), i, j), j


def _quote(lines, i, hi, depth):
    """A quote: its lines with one level of `>` taken off, read again as blocks."""
    if not lines[i].lstrip().startswith(">"):
        return None
    j = i
    while j < hi and lines[j].lstrip().startswith(">"):
        j += 1
    inner = [re.sub(r"^\s*>[ ]?", "", x) for x in lines[i:j]]
    kids = _read(inner, 0, len(inner), depth + 1) if depth < MAX_TEXT_DEPTH else [TextBlock("p", " ".join(inner), 0, 1)]
    return TextBlock("quote", kids, i, j), j


def _listed(lines, i, hi, depth):
    """A list."""
    return _list(lines, i, hi, depth) if (_ITEM.match(lines[i]) or _EMPTY_ITEM.match(lines[i])) else None


def _paragraph(lines, i, hi):
    """A paragraph: lines up to a blank one or the start of another block, joined by a space."""
    j = i + 1
    while j < hi and lines[j].strip() and not _starts_block(lines[j], lines[j + 1] if j + 1 < hi else None):
        j += 1
    text = ""
    for k in range(i, j):
        line = lines[k]
        body, hard = line.strip(), k < j - 1 and (line.endswith("  ") or line.strip().endswith("\\"))
        text += (body[:-1] if hard and body.endswith("\\") else body) + ("\n" if hard else " " if k < j - 1 else "")
    return TextBlock("p", text, i, j), j


def _item_end(lines, i, hi, base):
    """The line after the item that starts at lines[i]: its deeper lines, a blank between them, and a lazy continuation of its text."""
    j = i + 1
    while j < hi:
        if not lines[j].strip():
            k = j
            while k < hi and not lines[k].strip():
                k += 1
            if k < hi and _indent(lines[k]) > base:
                j = k
                continue
            break
        if _indent(lines[j]) <= base and _starts_block(lines[j], None):
            break
        j += 1
    return j


def _task_of(text, ordered):
    """(the checklist state of a bullet's text: " " or "x", else None; its words without the box)."""
    t = None if ordered else _TASK.match(text)
    return (t.group(1).lower(), (t.group(2) or "").strip()) if t else (None, text)


def _list_item(lines, i, hi, base, ordered, depth):
    """(the item that starts at lines[i]: (checklist state, text, nested blocks); the line after it)."""
    m = _ITEM.match(lines[i]) or _EMPTY_ITEM.match(lines[i])
    j = _item_end(lines, i, hi, base)
    rest, lead = lines[i + 1:j], []
    while rest and rest[0].strip() and _indent(rest[0]) <= base and not _starts_block(rest[0], None):
        lead.append(rest.pop(0).strip())               # a soft-wrapped line of the item's own text
    task, text = _task_of(" ".join([(m.group(3) if m.re is _ITEM else "").strip()] + lead).strip(), ordered)
    deep = min((_indent(x) for x in rest if x.strip()), default=0)
    under = [x.expandtabs(4)[deep:] if x.strip() else "" for x in rest]
    kids = _read(under, 0, len(under), depth + 1) if depth < MAX_TEXT_DEPTH and any(x.strip() for x in under) else []
    return (task, text, kids), j


def _same_list(lines, i, hi, base, ordered):
    """True when lines[i] is an item of the list being read: the same indent and kind."""
    m = (_ITEM.match(lines[i]) or _EMPTY_ITEM.match(lines[i])) if i < hi else None
    return bool(m) and _indent(lines[i]) == base and m.group(2)[0].isdigit() == ordered


def _list(lines, i, hi, depth):
    """(a list block, the next line) for the list that starts at lines[i]: items of one kind (bullets or numbers) at one indent."""
    first = _ITEM.match(lines[i]) or _EMPTY_ITEM.match(lines[i])
    base, ordered = _indent(lines[i]), first.group(2)[0].isdigit()
    items, start = [], i
    while _same_list(lines, i, hi, base, ordered):
        item, i = _list_item(lines, i, hi, base, ordered, depth)
        items.append(item)
        k = i
        while k < hi and not lines[k].strip():
            k += 1
        if _same_list(lines, k, hi, base, ordered):
            i = k                                      # blank lines between items of one list
    return TextBlock("list", (ordered, items), start, i), i


def images_dir(doc):
    """The folder whose `_images/` holds a report's pictures: the project's reports folder. None when the project has no folder."""
    try:
        return paths.folder(doc.get("project"), FOLDER["weekly"])
    except (LookupError, OSError, KeyError, TypeError, AttributeError):
        return None


IMAGE_MAX = 2 * 1024 * 1024        # a picture in a text section: the same cap as its upload (report_server.IMAGE_MAX)


def _too_big(f):
    """Whether a picture file is over the cap (a file that can't be read counts as not too big: the caller reports it as missing)."""
    try:
        return f.stat().st_size > IMAGE_MAX
    except OSError:
        return False


def text_image(doc, ref):
    """The picture file a text section's `_images/<name>` address names (PNG or JPEG), or None: only that shape of address is read, and
    only inside the reports folder."""
    if not TEXT_IMAGE.match(str(ref or "")):
        return None
    root = images_dir(doc or {})
    if root is None:
        return None
    f = Path(root) / ref
    try:
        if f.is_symlink() or not f.is_file() or (Path(root).resolve() / "_images") not in f.resolve().parents:
            return None
    except OSError:
        return None
    return f


def picture_ref_ok(ref):
    """Whether a Markdown picture line may stay in a document: the document's own picture (`_images/<name>`) or a plain relative
    `images/<name>` (paths.safe_image_ref); never an absolute path, `..`, a URL or a drive letter (v2.5.0 leak fix)."""
    ref = str(ref or "")
    return bool(TEXT_IMAGE.match(ref)) or (ref.startswith("images/") and paths.safe_image_ref(ref))


def drop_outside_pictures(doc):
    """(a copy of the document, what was dropped): every Markdown picture line in a section's or a pane's text whose target
    picture_ref_ok refuses is taken out, so a hand-written draft can't carry one to an export (v2.5.0 leak fix)."""
    import docx_tools
    gone = []

    def clean(text):
        """The text without the picture lines it may not carry."""
        if not isinstance(text, str) or "![" not in text:
            return text
        keep, fence = [], None
        for line in text.split("\n"):
            f = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
            if f and (fence is None or (f.group(1)[0] == fence[0] and len(f.group(1)) >= len(fence))):
                fence = f.group(1) if fence is None else None       # a fenced code block's lines are code, kept as written
            m = None if fence is not None or f else docx_tools.IMAGE_LINE.match(line)
            if m and not picture_ref_ok(m.group(2)):
                gone.append(m.group(1).strip() or "a picture")
                continue
            keep.append(line)
        return "\n".join(keep)
    sections = []
    for s in doc.get("sections") or []:
        if isinstance(s, dict):
            s = dict(s, text=clean(s["text"])) if "text" in s else dict(s)
            if isinstance(s.get("panes"), list):
                s["panes"] = [dict(p, text=clean(p["text"])) if isinstance(p, dict) and "text" in p else p for p in s["panes"]]
        sections.append(s)
    if not gone:
        return doc, []
    return dict(doc, sections=sections), [f"a picture line ({g}) naming a file outside the report's own pictures was taken out"
                                          for g in gone]


def _inline(t):
    """Inline Markdown as escaped HTML: bold, italic, strike, `code` and links with their address (http, https and mailto only), nested
    as docx_tools.md_spans reads them (the same reading as Word's); a backslash escape is the character."""
    import docx_tools
    out = []
    for text, bold, italic, strike, url, code in docx_tools.md_spans(str(t or ""), True):
        x = esc(text).replace("\n", "<br>")
        if code:
            x = f"<code>{x}</code>"
        if url:
            x = f'<a href="{esc(url)}">{x}</a>'
        for on, tag in ((italic, "em"), (strike, "s"), (bold, "strong")):
            if on:
                x = f"<{tag}>{x}</{tag}>"
        out.append(x)
    return "".join(out)


def _picture_ok(f):
    """Whether a picture file can be walked and checked (docx_tools.strip_image_metadata): one that can't is not included anywhere."""
    import docx_tools
    try:
        docx_tools.strip_image_metadata(Path(f).read_bytes())
        return True
    except (docx_tools.PictureRefused, OSError):
        return False


def _image_html(doc, alt, ref):
    """A picture as a figure with the file inside the page (a data address), or the words saying it wasn't found."""
    import base64
    import docx_tools
    f = text_image(doc, ref)
    if f is None:
        return f"<p><em>Picture not found: {esc(alt or ref)}</em></p>"
    if _too_big(f):
        return f"<p><em>Picture too large to include: {esc(alt or ref)}</em></p>"
    if not _picture_ok(f):
        return f"<p><em>Picture not included: {esc(alt or ref)}</em></p>"
    mime = "image/png" if f.suffix.lower() == ".png" else "image/jpeg"
    cap = f"<figcaption>{esc(alt)}</figcaption>" if alt else ""
    data = base64.b64encode(docx_tools.strip_image_metadata(f.read_bytes())).decode("ascii")
    return f'<figure><img src="data:{mime};base64,{data}" alt="{esc(alt)}">{cap}</figure>'


def _list_html(b, doc):
    """A list block as HTML; a checklist item starts with its box."""
    ordered, items = b.data
    tag = "ol" if ordered else "ul"
    cls = ' class="tasks"' if any(t for t, _x, _k in items) else ""
    lis = "".join("<li>" + (("☑ " if t == "x" else "☐ ") if t else "") + _inline(x)
                  + "".join(_block_html(y, doc) for y in kids) + "</li>" for t, x, kids in items)
    return f"<{tag}{cls}>{lis}</{tag}>"


def _table_html(b):
    """A table block as HTML: the first row is the header."""
    head, rows = b.data
    width = len(head)
    body = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in (r + [""] * width)[:width]) + "</tr>" for r in rows)
    return "<table><thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in head) + f"</tr></thead><tbody>{body}</tbody></table>"


def _block_html(b, doc):
    """One block as HTML."""
    k = b.kind
    if k == "h":
        n = min(b.data[0] + 2, 6)                 # the page's own headings are h1 (title) and h2 (section): the text starts at h3
        return f"<h{n}>{_inline(b.data[1])}</h{n}>"
    return {"p": lambda: f"<p>{_inline(b.data)}</p>", "hr": lambda: "<hr>", "table": lambda: _table_html(b),
            "code": lambda: f"<pre><code>{esc(b.data[1])}</code></pre>", "img": lambda: _image_html(doc, *b.data),
            "quote": lambda: "<blockquote>" + "".join(_block_html(x, doc) for x in b.data) + "</blockquote>",
            "list": lambda: _list_html(b, doc)}[k]()


def text_html(text, doc=None):
    """A text section's Markdown as safe HTML (see the note above): headings, paragraphs, lists, checklists as boxes, quotes, code,
    tables, pictures inside the page, links with their address."""
    return '<div class="ft">' + "".join(_block_html(b, doc) for b in text_blocks(text)) + "</div>"


def _table(s):
    """A table section's shown rows."""
    cols = s.get("columns") or []
    head = "".join(f"<th>{esc(c.get('label'))}</th>" for c in cols)
    body = "".join("<tr>" + "".join(f"<td>{esc((r.get('cells') or {}).get(c.get('key')))}</td>" for c in cols) + "</tr>"
                   for r in s.get("rows") or [] if r.get("shown", True))
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>" if cols else ""


def _figures(s):
    """At a glance: the shown figures."""
    cells = "".join(f'<div class="figure">{esc(f.get("label"))}<b>{esc(f.get("value"))}</b>{esc(f.get("note"))}</div>'
                    for f in s.get("figures") or [] if f.get("shown", True))
    return f'<div class="figures">{cells}</div>'


def _panes(s):
    """Current state's panes; one pane takes the full width."""
    panes = [p for p in s.get("panes") or [] if (p.get("text") or "").strip() or p.get("title")]
    return '<div class="panes">' + "".join(f"<div><h3>{esc(p.get('title'))}</h3>{md_html(p.get('text'))}</div>" for p in panes) + "</div>"


def _health(s):
    """Health: the flag in words (never colour alone), then the text."""
    flag = (s.get("data") or {}).get("flag")
    return (f'<p class="flag">{esc(flag)}</p>' if flag else "") + md_html(s.get("text"))


def _timeline(s, items):
    """Milestones: the ones chosen for the list, with their dates, from the items as they stood."""
    rows = [items.get(ref) or {"title": ref} for ref in (s.get("data") or {}).get("milestones") or []]
    lis = "".join(f"<li>{esc(m.get('title'))}{(' · ' + esc(m.get('due_date'))) if m.get('due_date') else ''}</li>" for m in rows)
    return md_html(s.get("text")) + (f"<ul>{lis}</ul>" if lis else "")


def section_html(s, items, doc=None):
    """One shown section's HTML; an unknown type renders its text only."""
    kind = s.get("type")
    if kind == TEXT_TYPE:
        head = f"<h2>{esc(s.get('heading'))}</h2>" if str(s.get("heading") or "").strip() else ""
        return f'<section data-id="{esc(s.get("id"))}">{head}{text_html(s.get("text"), doc)}</section>'
    words = [s.get("text")] + [x for p in s.get("panes") or [] for x in (p.get("title"), p.get("text"))]
    if kind in (None, "text", "panes") and not any(str(w or "").strip() for w in words):
        return ""                                                     # nothing in it: no empty heading, as the Word writer leaves it out
    body = {"table": lambda: md_html(s.get("text")) + _table(s), "figures": lambda: _figures(s), "panes": lambda: _panes(s),
            "health": lambda: _health(s), "timeline": lambda: _timeline(s, items)}.get(kind, lambda: md_html(s.get("text")))()
    return f'<section data-id="{esc(s.get("id"))}"><h2>{esc(s.get("heading"))}</h2>{body}</section>'


def page_title(doc):
    """The tab title: '<Title> - <Project name>, DD-MM-YYYY'."""
    d = doc.get("date") or ""
    shown = f"{d[8:10]}-{d[5:7]}-{d[:4]}" if DATE.match(d) else d
    who = doc.get("project_name") or ""
    extra = f" ({doc['client']})" if doc.get("client") else ""
    return f"{doc.get('title') or ''}{' - ' + who if who else ''}{extra}, {shown}"


def render(doc, editing=True, keep_text=False):
    """The page for the document; with `editing` the data block is included (the filed file), without it not (the HTML export).
    Hidden content is never rendered; source tags never are."""
    doc = clean(doc, keep_text)
    items = doc.get("items") or {}
    body = "".join(section_html(s, items, doc) for s in doc["sections"] if not s.get("hidden"))
    label = {"internal": "Internal", "client": "Client", "distributed": "Distributed"}[doc.get("audience") or "internal"]
    head = (f'<header class="doc"><div><h1>{esc(doc.get("title"))}</h1><div class="sub">{esc(doc.get("project_name"))}'
            f'{(" · " + esc(doc["client"])) if doc.get("client") else ""}</div></div><div class="sub">{esc(label)}</div></header>')
    data = f'\n<script type="application/json" id="{DATA_ID}">{data_json(doc)}</script>' if editing else ""
    return (f'<!doctype html>\n<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            f"<title>{esc(page_title(doc))}</title><style>{CSS}</style></head>\n"
            f'<body><main class="page">{head}{body}</main>{data}\n</body></html>\n')


# ── Search ───────────────────────────────────────────────────────────────────

LINK_ADDRESS = r"[^()]{0,2000}(?:\([^()]{0,200}\)[^()]{0,2000})?"     # a link's address, with at most one pair of brackets in it


def _plain(md):
    """Markdown as plain words."""
    t = re.sub(r"!\[[^\]]{0,2000}\]\([^)]{0,2000}\)", "", str(md or ""))     # #127 review: bounded, so linear
    t = re.sub(r"\[([^\[\]]{1,2000})\]\(" + LINK_ADDRESS + r"\)", r"\1", t)   # #127 review: bounded, crossing no bracket: linear
    return re.sub(r"[*_`#>]+", "", t).strip()


def _section_words(s):
    """A shown section's words: its text, then table cells, figures and panes."""
    parts = [_plain(s.get("text"))]
    parts += [" · ".join(str(v) for v in (r.get("cells") or {}).values() if v not in (None, ""))
              for r in s.get("rows") or [] if r.get("shown", True)]
    parts += [" ".join(str(f.get(k) or "") for k in ("label", "value", "note")).strip()
              for f in s.get("figures") or [] if f.get("shown", True)]
    parts += [f"{p.get('title') or ''}\n{_plain(p.get('text'))}".strip() for p in s.get("panes") or []]
    return "\n".join(p for p in parts if p)


def sections_text(doc):
    """[(id, heading, text)] of every shown section, in page order."""
    doc = clean(doc)
    return [(s["id"], s.get("heading") or "", _section_words(s)) for s in doc["sections"] if not s.get("hidden")]


def search_text(path_or_doc):
    """What the search index reads: each shown section's heading, then its words, a blank line between sections. '' for a file that
    isn't a creaite document."""
    try:
        doc = path_or_doc if isinstance(path_or_doc, dict) else read(path_or_doc)
        parts = [doc.get("title") or ""] + [f"{h}\n\n{t}" for _i, h, t in sections_text(doc)]
    except (DocError, OSError):
        return ""
    return "\n\n".join(p for p in parts if p.strip())


# ── Where a document is filed ────────────────────────────────────────────────

def safe_title(title):
    """A title made safe for a file name: no reserved characters, spaces collapsed, at most 80 characters."""
    t = re.sub(r'[\\/:*?"<>|\x00-\x1f]', " ", str(title or "Meeting"))
    return re.sub(r"\s+", " ", t).strip(" .")[:80] or "Meeting"


def target(kind, project, date, name=None, client=None):
    """The stored path a document is filed at: a report in the project's weekly or client reports folder
    (report.report_file, .html), minutes as 'YYYY-MM-DD <Meeting title>.html' in its minutes folder."""
    if kind not in KINDS or not DATE.match(str(date or "")):
        raise DocError("A kind (weekly, client or minutes) and a YYYY-MM-DD date are needed.")
    if kind == "minutes":
        file = f"{date} {safe_title(name)}.html"
    else:
        import report
        who = project_name(project) or project
        file = report.report_file(date, REPORT_KIND[kind], f"{who} ({client})" if client else who, ext=".html")
    return paths.rel(paths.folder(project, FOLDER[kind]) / file)


# ── Saving, versions and Undo (filechange.py) ────────────────────────────────

def stored(path):
    """A path as filechange logs it."""
    import filechange
    return filechange.stored(real(path))


def _current_version(p):
    """(version of the file now, or 0 when there is none). Raises DocError when a file is there that isn't a creaite document."""
    if not p.exists():
        return 0
    if not is_doc(p):
        raise DocError("A file that isn't a creaite document is there; creaite never overwrites it.")
    return int(read(p).get("version") or 0)


def _refusal(message, **extra):
    """save's answer when nothing was written."""
    return {"ok": False, "code": 1, "path": None, "version": None, "change": None, "message": message, **extra}


def save(path, doc, why, *, base_version=None, approver=None, via="cli"):
    """Save `doc` at `path` as a new version through filechange.py (a create, or an edit that keeps the earlier version). See the
    contract for the answer's shape. `approver` is the live server's own reach.APPROVALS.issue, passed only when Alan pressed Save."""
    import filechange
    p = real(path)
    try:
        was = _current_version(p)
        out = clean(doc, keep_text=True)         # the working draft keeps a hidden text section's words
    except DocError as e:
        return _refusal(str(e))
    if base_version is not None and int(base_version) != was:
        return _refusal(f"It was saved elsewhere since you opened it (now version {was}).", conflict=True)
    out.update(version=was + 1, saved_at=now())
    data = dumps(out, keep_text=True).encode("utf-8")
    paths.DRAFTS.mkdir(parents=True, exist_ok=True)
    draft = paths.free_path(paths.DRAFTS, f"creaite-doc {datetime.now():%Y-%m-%d %H%M%S}", ".html")
    draft.write_bytes(data)
    ch = {"op": "edit" if p.exists() else "create", "path": stored(p), "data": data, "from": paths.rel(draft), "why": why}
    token = approver(filechange.fingerprint(ch)) if approver else None
    code, msg = filechange.perform(ch, token, via)
    if code == filechange.NEEDS:
        filechange.record_request(ch, msg[len("Needs approval: "):].rstrip("."))
        return {"ok": False, "code": code, "needs_approval": True, "path": ch["path"], "version": was, "change": None, "message": msg}
    draft.unlink()
    if code != 0:
        return _refusal(msg)
    m = re.search(r"\(change (\d+)", msg)
    final = re.match(r"(?:Created|Changed) (.+?) \(change", msg)
    return {"ok": True, "code": 0, "path": final.group(1) if final else ch["path"], "version": was + 1,
            "change": int(m.group(1)) if m else None, "message": msg}


def _changes(path):
    """filechange's creates and edits of this file that aren't undone, oldest first."""
    import filechange
    where = stored(path)
    return [e for e in filechange.changes() if e.get("path") == where and e.get("op") in ("create", "edit") and not e["undone"]]


def versions(path):
    """The file's versions, newest first: the current file, then each earlier version kept in a backup (the save that replaced it as
    `change`). A backup Tidy up removed is not listed."""
    p = real(path)
    es = _changes(p)
    if not p.is_file():
        return []
    last = es[-1] if es else {}
    out = [{"version": int(read(p).get("version") or 0), "current": True, "at": last.get("at"), "change": last.get("id"),
            "why": last.get("why")}]
    for e in reversed([e for e in es if e["op"] == "edit"]):
        b = paths.resolve(e["backup"]) if e.get("backup") else None
        if b and b.is_file():
            try:
                v = int(loads(b.read_text(encoding="utf-8")).get("version") or 0)
            except DocError:
                continue        # an earlier file that wasn't a creaite document has no version to show
            out.append({"version": v, "current": False, "at": e.get("at"), "change": e["id"], "backup": e["backup"]})
    return out


def read_version(path, change):
    """The version that save `change` replaced, read from its backup. Raises DocError."""
    e = next((e for e in _changes(path) if e["id"] == int(change) and e["op"] == "edit"), None)
    if not e or not e.get("backup") or not paths.resolve(e["backup"]).is_file():
        raise DocError("That earlier version isn't kept any more.")
    return read(paths.resolve(e["backup"]))


def undo(path):
    """Undo the latest save of this file that isn't undone: {ok, message, version} (version None when the file is gone)."""
    import contextlib
    import io
    import filechange
    es = _changes(path)
    if not es:
        return {"ok": False, "message": "Nothing to undo for this file.", "version": None}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = filechange.cmd_undo(es[-1]["id"])
    p = real(path)
    version = int(read(p).get("version") or 0) if p.is_file() and is_doc(p) else None
    return {"ok": code == 0, "message": buf.getvalue().strip(), "version": version}


# ── Exports: HTML, Word and PDF (P2; BL-335, BL-336, BL-338) ─────────────────
# Every export is made from the data block, so all three have the same sections in the same order and nothing hidden.

EXPORTS = {"html": ".html", "docx": ".docx", "pdf": ".pdf"}
TEMPLATES = {"weekly": "weekly-report-template.docx", "client": "client-report-template.docx", "minutes": "minutes-template.docx"}
WORD_EL = re.compile(r"<w:p(?: [^>]*)?/>|<w:p(?: [^>]*)?>.*?</w:p>|<w:tbl>.*?</w:tbl>", re.S)
WORD_TEXT = re.compile(r"<w:t(?: [^>]*)?>([^<]*)</w:t>")
FRONT_DROP = ("{{HEALTH_LINE}}", "{{ATTENDEES}}")     # the template's health and attendees lines: the document's sections instead
CHROME_SECONDS = 90


FILE_BESIDE = {"weekly": (None, True), "client": (None, True),
               "minutes": ("file_minutes_exports_beside", True)}     # kind: (its setting under "reports" or None, its default)


def file_beside_default(kind):
    """Whether an export of a document of this kind is filed beside it, unless Alan ticks otherwise: for minutes the setting "File minutes
    exports beside them" (reports.file_minutes_exports_beside, on by default, BL-338) for minutes. A weekly or client report
    export is always saved into the report's folder (#220): no setting, so the answer is always True."""
    if kind not in FILE_BESIDE:
        raise ValueError(f"creaite documents are weekly, client or minutes; not {kind!r}.")
    key, default = FILE_BESIDE[kind]
    if key is None:
        return default
    try:
        value = (paths.load_settings().get("reports") or {}).get(key)
    except (OSError, ValueError):
        value = None
    return default if value is None else bool(value)


def export(path, fmt, *, out_dir=None, file_beside=True, open_after=True, page=None, kind=None, doc=None):
    """Export the document at `path` as "html", "docx" or "pdf", made from its data. Written to system/staging/drafts/; with
    `file_beside` also filed beside the document through filechange.py (a create, never overwriting), or in `out_dir` (a stored
    folder) when given. `open_after` is passed back for the live server to open the export (/api/open). See the contract.
    #226: for "html" and "pdf", `page` (the report page's own exported view; export_page.build checks it against the report) is
    what is written and printed; with none, or one that fails the check, the plain renderer below is, and the answer says
    `plain: True` (and `plain_why` when a page was refused).
    v2.5.1 (#239): `doc` is the document the caller has already read and checked (the client export route, under its lock): it is
    the one rendered, the file is not read again. A client report is gated here too (client_leak.findings on the document
    rendered), a posted page is never used for one (the server renders it from the report), and the made file is checked again
    (client_output_findings): any finding and nothing is kept."""
    def fail(message, **extra):
        """The answer when nothing was exported."""
        return {"ok": False, "format": fmt, "message": message, **extra}
    if fmt not in EXPORTS:
        return fail(f"creaite exports to HTML, Word or PDF; not {fmt!r}.")
    try:
        # v2.5.0 audience bypass (`kind`: what the route expects; another kind is refused): a client report exported as one, however
        # its file was edited
        doc = _export_doc(path, kind, doc)
        _check_baseline(doc)
        gate = _client_gate(doc)
        if gate:
            return fail("Not exported: possible internal content in the client report: " + "; ".join(gate), findings=gate)
        built, why = _posted_page(doc, page, fmt)
        draft, made = _make_export(doc, fmt, real(path).stem, built)
    except DocError as e:
        return fail(str(e))
    found = client_output_findings(doc, fmt, draft, made)
    if found:
        return fail("Not exported: the file made held possible internal content: " + "; ".join(found), findings=found)
    out = {"ok": True, "format": fmt, "path": paths.rel(draft), "draft": paths.rel(draft), "filed": False,
           "open_after": bool(open_after)}
    if fmt in ("html", "pdf") and built is None:
        out["plain"] = True
        if why:
            out["plain_why"] = why
    folder = real(out_dir) if out_dir else real(path).parent if file_beside else None
    if folder is None or folder.resolve() == paths.DRAFTS.resolve():
        return {**out, "message": f"Exported {paths.rel(draft)}."}
    return _file_export(out, draft, folder / _export_name(doc, path, fmt), fail)


def _posted_page(doc, page, fmt):
    """(the posted page as export_page.build checked it, or None; why it wasn't used, or None). #226: an HTML or PDF export of a
    weekly report or minutes may be the page posted. v2.5.1 (#239, f): a client report's never is: it is made from the report."""
    if page is None:
        return None, None
    if doc.get("kind") == "client":
        return None, "a client report is always made from the saved report, never from the page on the screen"
    if fmt not in ("html", "pdf"):
        return None, None
    import export_page
    try:
        return export_page.build(doc, page, page_title(doc)), None
    except export_page.PageRefused as e:
        return None, str(e)


REPORT_NAME = re.compile(r"\b(?:client|weekly)\s+report\b", re.I)
REPORT_META = ("period_start", "period_end", "facts_week", "facts_on", "locked", "client_facts", "health_diff")
REPORT_HEADER = ("logos", "facts_week", "period_start", "period_end", "week_ending")


def _in_reports_folder(p):
    """Whether a file sits in any project's weekly or client reports folder (where only reports are filed)."""
    import tracker
    try:
        with tracker.connect() as con:
            codes = [r[0] for r in con.execute("SELECT code FROM projects")]
    except BaseException:  # noqa: BLE001  no tracker: fail closed, every folder named Reports counts
        return Path(p).parent.name.lower() == "reports"
    here = Path(p).resolve().parent
    for code in codes:
        for kind in ("weekly_reports", "client_reports"):
            try:
                if paths.folder(code, kind).resolve() == here:
                    return True
            except (LookupError, OSError, KeyError, ValueError):
                continue        # a project with no folder has no reports folder
    return False


def _report_data(doc):
    """Whether a document holds a report's data: its period, facts week or lock in meta, or logos or a period in its header."""
    meta = doc.get("meta") if isinstance(doc.get("meta"), dict) else {}
    header = [s.get("data") for s in doc.get("sections") or [] if isinstance(s, dict) and isinstance(s.get("data"), dict)
              and s.get("type") == "header"]
    return any(k in meta for k in REPORT_META) or any(k in d for d in header for k in REPORT_HEADER)


def report_signs(path, doc):
    """v2.5.1 (#239, e): why a file opened as minutes is a report (a client report edited to say minutes most of all): [] when none.
    Any sign counts: a report's kind, a client audience, a report's file name or title, a reports folder, or a report's data (its
    period, facts week or lock in meta, logos or a period in its header)."""
    signs = []
    if doc.get("kind") in ("weekly", "client") or doc.get("audience") == "client":
        signs.append("its data says it is a report")
    if REPORT_NAME.search(real(path).name) or REPORT_NAME.search(str(doc.get("title") or "")):
        signs.append("its name is a report's")
    if _report_data(doc):
        signs.append("it holds a report's period, facts or logos")
    if _in_reports_folder(real(path)):
        signs.append("it is in a Reports folder")
    return signs


def _export_doc(path, kind, doc=None):
    """The document an export renders: `doc` as the caller checked it (a client report read again as one), else the file at `path`
    (read_report). Raises DocError for a kind the route doesn't expect."""
    if doc is None:
        doc = read_report(path, kind)
        if kind in (None, "minutes") and report_signs(path, doc):
            raise DocError("That file is a report, not minutes (" + "; ".join(report_signs(path, doc)) + "), so it isn't exported "
                           "here. Export a report from the Reporting hub.")
        return doc
    check(doc)
    if kind is not None and doc.get("kind") != kind:
        raise DocError("That file isn't this report (its kind was changed), so nothing was done. Open the report again from creaite.")
    return force_client_audience(copy.deepcopy(doc))


def _client_gate(doc):
    """v2.5.1 (#239): the client gate's findings on the document an export renders ([] for any other kind)."""
    if doc.get("kind") != "client":
        return []
    import client_leak
    return client_leak.findings(doc)


def _export_name(doc, path, fmt):
    """The file name an export is filed under. Minutes and other documents: the stem, and ' (read only)' for HTML. A weekly or client
    report's HTML (Alan, 18-10-2026) takes its plain name, as the dashboard's export does; the plain name belongs to the filed report, so
    a report not filed yet leaves it free for the filing and its export is numbered (a taken name is numbered by the filing)."""
    stem = real(path).stem
    if fmt != "html" or doc.get("kind") not in ("weekly", "client"):
        return stem + (" (read only)" if fmt == "html" else "") + EXPORTS[fmt]
    try:
        filing = real(target(doc["kind"], doc.get("project"), doc.get("date"), client=doc.get("client")))
    except (DocError, LookupError, OSError, KeyError, TypeError):
        filing = None
    name = filing.stem if filing is not None else stem
    if filing is None or real(path).resolve() != filing.resolve():
        name += " (2)"
    return name + EXPORTS[fmt]


def _check_baseline(doc):
    """A client view or distributed minutes is exported only once the internal document it is based on is approved."""
    if not is_client(doc):
        return
    base = doc.get("based_on") or {}
    try:
        approved = bool(base.get("path")) and read(base["path"]).get("state") == "approved"
    except DocError:
        approved = False
    if not approved:
        what = "Distributed minutes are" if doc.get("kind") == "minutes" else "A client report is"
        raise DocError(f"{what} exported only after the internal {'minutes are' if doc.get('kind') == 'minutes' else 'report is'} "
                       "approved.")


def _make_export(doc, fmt, stem, built=None):
    """Write the export into system/staging/drafts/: (its path, {page: the HTML a PDF was printed from, drawn: the hashes of the
    pictures a Word export drew}). Raises DocError."""
    paths.DRAFTS.mkdir(parents=True, exist_ok=True)
    # An HTML export never takes the document's own draft path (drafts/<name>.html): a plain page there would stand in for the draft.
    draft = paths.free_path(paths.DRAFTS, stem + (" (read only)" if fmt == "html" else ""), EXPORTS[fmt])
    made = {"page": None, "drawn": set()}
    if fmt == "html":
        draft.write_text(built or render(doc, editing=False), encoding="utf-8")
    elif fmt == "docx":
        made["drawn"] = word_export(doc, draft) or set()
    else:
        made["page"] = built or render(doc, editing=False)
        page = paths.free_path(paths.DRAFTS, f"{stem} print", ".html")
        page.write_text(made["page"], encoding="utf-8")
        try:
            print_pdf(page, draft)
        finally:
            page.unlink()
    return draft, made


def client_output_findings(doc, fmt, draft, made):
    """v2.5.1 (#239, c): the check of a client report's made file (client_output.check); any finding (or a check that can't run)
    deletes the file. [] for a document that isn't a client report."""
    if doc.get("kind") != "client":
        return []
    import client_output
    try:
        found = client_output.check(doc, fmt, draft, page=made.get("page"), drawn=made.get("drawn") or ())
    except Exception as e:  # noqa: BLE001  fails closed: an output that can't be checked is never kept
        found = [f"the made file couldn't be checked ({type(e).__name__})"]
    if found:
        Path(draft).unlink(missing_ok=True)
    return found


def _file_export(out, draft, target, fail):
    """File the draft at `target` through filechange.py (a create: a taken name gets a number). The draft goes once it is filed;
    when the change needs Alan's approval it stays for his card."""
    import filechange
    ch = {"op": "create", "path": stored(target), "data": draft.read_bytes(), "from": paths.rel(draft),
          "why": f"{out['format'].upper()} export of {target.stem}"}
    code, msg = filechange.perform(ch, None, "cli")
    if code == filechange.NEEDS:
        filechange.record_request(ch, msg[len("Needs approval: "):].rstrip("."))
        return fail(msg, needs_approval=True, draft=out["draft"])
    if code != 0:
        return fail(msg, draft=out["draft"])
    draft.unlink()
    final = re.match(r"Created (.+?) \(change", msg)
    return {**out, "path": final.group(1) if final else ch["path"], "draft": None, "filed": True, "message": msg}


# ── Word: the firm's template, filled by docx_tools.py ───────────────────────
# #227: the Word writer stays a separate writer (the firm's template, native tables, real pictures) and follows the screen's sheet:
# one title block, the report's logos, health with its six-week strip, At a glance as a table, the milestone timeline as a picture
# and its list as a table, tables with every column the screen shows, DD-MM-YYYY dates, an empty section as its sentence or not at all.

TONE_HEX = {"g": "2E7D32", "a": "D68910", "r": "C0392B", "n": "5E6270"}
EMPTY_SENTENCE = {"asks": "Nothing is needed from anyone this week.", "risks": "No open risks or issues.",
                  "overdue": "Nothing is overdue.", "decisions": "No decisions were made this week."}
PRIORITY_TONE = {"urgent": "r", "high": "r", "medium": "a", "low": "g"}
LOGO_HEIGHT = 40            # px in Word (96 to the inch)
STRIP = (360, 34)
TIMELINE_WIDTH = 640
IMG_EXT = (".png", ".jpg", ".jpeg")
INTERNAL_TIMELINE_DRAWS_ALL = True       # the sheet's timeline always shows every milestone (Alan may change this for internal reports)


def _nobraces(text):
    """Text that can't be read as a {{PLACEHOLDER}} by the fill."""
    return str(text if text is not None else "").replace("{{", "{​{").replace("}}", "}​}")


def _word_text(el):
    """A Word element's text."""
    import docx_tools
    return docx_tools.unesc("".join(WORD_TEXT.findall(el)))


def _dmy(iso):
    """A stored date as DD-MM-YYYY (anything else as it is)."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return f"{m[3]}-{m[2]}-{m[1]}" if m else str(iso or "")


def _dm(iso):
    """A stored date as DD-MM."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return f"{m[3]}-{m[2]}" if m else ""


def _day(iso):
    """A stored date as a day number, or None."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return datetime(int(m[1]), int(m[2]), int(m[3])).toordinal() if m else None


def _tone(flag):
    """The tone a health flag is drawn in (the sheet's wkTone): g, a, r or n."""
    f = str(flag or "")
    for tone, pattern in (("r", "off"), ("a", "risk"), ("g", "on track|achieved")):
        if re.search(pattern, f, re.I):
            return tone
    return "n"


def _ms_state(m):
    """A milestone's state word and tone (the sheet's wkMsState)."""
    st, base = m.get("state"), m.get("baseline_date") or m.get("due_date")
    fc = m.get("forecast_date") or base
    if m.get("status") == "Done" or st == "Achieved":
        return "ACHIEVED", "g"
    if m.get("status") == "Cancelled":
        return "CANCELLED", "n"
    if st == "Overdue":
        return "OVERDUE", "r"
    if st == "Slipped" or (_day(fc) and _day(base) and _day(fc) > _day(base)):
        return "SLIPPED", "a"
    if st == "At risk":
        return "AT RISK", "a"
    return "ON TRACK", "g"


def picture_png(markup, width, height, scale=2):
    """A transparent PNG of the HTML/SVG `markup` drawn in a `width` x `height` pixel window by headless Chrome (`scale` times as many
    pixels, so it stays sharp in Word). One small drawing, a throwaway profile; raises DocError when Chrome is missing or fails."""
    import os
    import shutil
    import signal
    import subprocess
    import tempfile
    import launch
    chrome = launch.find_chrome()
    if not chrome:
        raise DocError("Chrome wasn't found, so the pictures weren't drawn.")
    work = tempfile.mkdtemp(prefix="creaite-pic-")
    try:
        page, out = Path(work) / "p.html", Path(work) / "p.png"
        page.write_text('<!doctype html><meta charset="utf-8"><style>html,body{margin:0;padding:0;background:transparent}'
                        'svg,img{display:block}</style>' + markup, encoding="utf-8")
        cmd = [chrome, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--disable-extensions",
               f"--user-data-dir={Path(work) / 'profile'}", "--hide-scrollbars", "--default-background-color=00000000",
               f"--force-device-scale-factor={scale}", f"--window-size={int(width)},{int(height)}", f"--screenshot={out}",
               page.resolve().as_uri()]
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                start_new_session=True)
        try:
            proc.wait(timeout=CHROME_SECONDS)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        if not (out.is_file() and out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"):
            raise DocError("Chrome didn't draw a picture.")
        return out.read_bytes()
    finally:
        shutil.rmtree(work, ignore_errors=True)


class _Word:
    """What one Word export shares: the document, its items, the project's folder and a work folder for the pictures."""

    def __init__(self, doc, work):
        """The export's state."""
        self.doc, self.items, self.work, self.n = doc, doc.get("items") or {}, Path(work), 0
        self.drawn = set()          # v2.5.1 (#239, c): the hashes of the pictures this export drew itself (client_output.check)
        try:
            self.folder = paths.project_dir(doc.get("project"))
        except Exception:                      # an unknown project: pictures then need absolute paths
            self.folder = Path(".")

    def picture(self, markup, width, height, show_w=None, caption=""):
        """A fill entry for a picture drawn from `markup`, or [] when it can't be drawn (the text beside it still tells the story)."""
        try:
            data = picture_png(markup, width, height)
        except (DocError, OSError):
            return []
        self.n += 1
        f = self.work / f"pic{self.n}.png"
        f.write_bytes(data)
        import client_output
        self.drawn.add(client_output.pic_hash(data))
        return [{"image": str(f), "caption": caption, "width": show_w or width}]

    # ── text ──
    def md(self, text):
        """Markdown as fill entries: text between pictures, each picture where it was placed; a picture that can't be found is named."""
        import docx_tools
        out, chunk = [], []

        def flush():
            """The text so far as one Markdown entry."""
            if "\n".join(chunk).strip():
                out.append({"md": _nobraces("\n".join(chunk))})
            chunk.clear()
        for line in str(text or "").splitlines():
            m = docx_tools.IMAGE_LINE.match(line)
            if not m:
                chunk.append(line)
                continue
            flush()
            f = self.picture_file(m.group(2))
            if f is None:                       # v2.5.0 leak fix: a reference it won't follow is never named, only its words
                out += self.refused(m.group(1).strip(), m.group(2))
            elif f.is_file() and f.suffix.lower() in IMG_EXT and _too_big(f):
                out.append({"md": _nobraces(f"*Picture too large to include: {m.group(2)}*")})
            elif f.is_file() and f.suffix.lower() in IMG_EXT and not _picture_ok(f):
                out.append({"md": _nobraces(f"*Picture not included: {m.group(2)}*")})
            elif f.is_file() and f.suffix.lower() in IMG_EXT:
                out.append({"image": str(f), "caption": m.group(1).strip()})
            else:
                out.append({"md": _nobraces(f"*Picture not found: {m.group(2)}*")})
        flush()
        return out

    def refused(self, alt, ref):
        """The words for a picture line md won't draw: "not found" for a safe internal reference, else only its alt text."""
        if self.internal() and paths.safe_image_ref(ref):
            return [{"md": _nobraces(f"*Picture not found: {ref}*")}]
        return [{"md": _nobraces(f"*Picture not included: {alt}*")}] if alt else []

    def picture_file(self, ref):
        """The file a Markdown picture line may draw, or None (v2.5.0 leak fix): the document's own picture store
        (`_images/<name>`, text_image) for every document; an internal one also reads `images/<name>` from the project's own images
        folder (paths.image_file: relative, no `..`, no symlink). An absolute path, `..`, a URL or a drive letter is never read."""
        f = text_image(self.doc, ref)
        if f is not None:
            return f
        if not self.internal():
            return None
        return paths.image_file(self.folder, ref)

    def internal(self):
        """Whether project pictures may be read: an internal audience and not a client report (a client kind is client whatever its
        audience says, as for_client reads it)."""
        return (self.doc.get("audience") or "internal") == "internal" and self.doc.get("kind") != "client"

    # ── the logos ──
    def logo_files(self, s):
        """v2.5.1 (#239, b): the logo files this export may draw, in order. A client report draws the logos the project ticks now
        (report_doc.client_logos), never a stored list; any report draws only a file that is one of the project's own logos
        (report_doc.logos, the logos folder), never another path a draft stored."""
        import report_doc
        code = str(self.doc.get("project") or "")
        if not report_doc.CODE.match(code):
            return []
        allowed = {paths.resolve(x["path"]).resolve() for x in report_doc.logos(code)}
        wanted = report_doc.client_logos(code, self.doc.get("layout")) if self._client() else (s.get("data") or {}).get("logos") or []
        out = []
        for lg in wanted:
            raw = str(lg.get("path") or "") if isinstance(lg, dict) else ""
            f = paths.resolve(Path(raw).as_posix()) if raw else None
            if f is not None and not f.is_symlink() and f.is_file() and f.resolve() in allowed:
                out.append(f)
        return out

    def logos(self, s):
        """The header's chosen logos (logo_files) as one fill entry (side by side); an SVG becomes a PNG, a PNG or JPEG is used as it
        is."""
        one = []
        for f in self.logo_files(s):
            try:                                    # p240-leakfix LOGO 1: a bad logo file is skipped, it never fails the export
                one += self._logo_entry(f)
            except Exception:           # a damaged or unreadable logo is left out of the file; the report is still made
                continue
        return [{"images": one}] if one else []

    def _logo_entry(self, f):
        """[one fill entry] for a logo file, or [] when it isn't a picture that can be drawn (a bad size, a damaged file)."""
        import docx_tools
        if f.suffix.lower() == ".svg":
            head = f.read_text(encoding="utf-8", errors="replace")[:2000]
            box = re.search(r'viewBox="[\d.\-]+[ ,]+[\d.\-]+[ ,]+([\d.]+)[ ,]+([\d.]+)"', head)
            wh = (re.search(r'\swidth="([\d.]+)', head), re.search(r'\sheight="([\d.]+)', head))
            w, h = ((float(box[1]), float(box[2])) if box else (float(wh[0][1]), float(wh[1][1])) if all(wh) else (160.0, 48.0))
            if not (w > 0 and h > 0):
                return []
            width = max(8, min(160, round(LOGO_HEIGHT * w / h)))
            made = self.picture(f'<img src="{f.resolve().as_uri()}" style="width:{width}px;height:{LOGO_HEIGHT}px">',
                                width, LOGO_HEIGHT, width)
            return [{"image": made[0]["image"], "width": width}] if made else []
        if f.suffix.lower() in IMG_EXT:
            w, h = docx_tools.image_size(f.read_bytes())
            if not (0 < w <= 20000 and 0 < h <= 20000):
                return []
            return [{"image": str(f), "width": max(8, min(160, round(LOGO_HEIGHT * w / h)))}]
        return []

    # ── sections: each gives parts, ("e", entries) or ("t", columns, rows, styler); none means the section is left out ──
    def parts(self, s):
        """A shown section's parts for its type."""
        make = {"health": self.health, "figures": self.figures, "panes": self.panes, "timeline": self.timeline,
                "table": self.table, TEXT_TYPE: self.freetext}.get(s.get("type"), self.text)
        return make(s)

    def freetext(self, s):
        """A text section (H5, #218) from the blocks text_blocks reads: paragraphs, lists, checklists and quotes as Markdown entries
        (inline code in a fixed-width font), headings and code blocks as paragraphs of their own, a table as a Word table, a picture
        placed from its file in `_images/` (any other address is named, never read)."""
        lines = str(s.get("text") or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
        parts, run = [], []

        def flush():
            """The paragraphs, lists and quotes so far, as one Markdown entry."""
            if run:
                parts.append(("e", [{"md": _nobraces("\n\n".join(run)), "code": True}]))
                run.clear()
        for b in text_blocks("\n".join(lines)):
            if b.kind in ("p", "list", "quote"):
                run.append("\n".join(lines[b.lo:b.hi]))
                continue
            flush()
            if b.kind == "h":
                parts.append(("h", b.data[0], _nobraces(_plain_inline(b.data[1]))))
            elif b.kind == "code":
                parts.append(("c", _nobraces(b.data[1])))
            elif b.kind == "table":
                head, rows = b.data
                width = len(head)
                parts.append(("t", [{"header": _nobraces(_plain_inline(c))} for c in head],
                              [[_nobraces(_plain_inline(c)) for c in (r + [""] * width)[:width]] for r in rows], lambda r, c: None))
            elif b.kind == "img":
                parts.append(("e", self.picture_entry(b.data[0], b.data[1])))
        flush()
        return parts

    def picture_entry(self, alt, ref):
        """A text section's picture as Word entries: the picture, or a sentence saying it is missing or over the 2 MB cap."""
        f = text_image(self.doc, ref)
        if f and _too_big(f):
            return [{"md": _nobraces(f"*Picture too large to include: {alt or ref}*")}]
        if f and not _picture_ok(f):
            return [{"md": _nobraces(f"*Picture not included: {alt or ref}*")}]
        return [{"image": str(f), "caption": alt}] if f else [{"md": _nobraces(f"*Picture not found: {alt or ref}*")}]

    def text(self, s):
        """A text section: its Markdown, or nothing."""
        e = self.md(s.get("text"))
        return [("e", e)] if e else []

    def panes(self, s):
        """Current state: each pane's title (when it has one), then its text."""
        e = []
        for p in s.get("panes") or []:
            e += (self.md(f"**{p['title']}**") if str(p.get("title") or "").strip() else []) + self.md(p.get("text"))
        return [("e", e)] if e else []

    def health(self, s):
        """Health: one coloured label, the six-week strip as a picture, the reason, and last week's flag."""
        import docx_tools
        d = s.get("data") or {}
        flag = str(d.get("flag") or "")
        e = [{"flag": flag.upper(), "text": ""}] if flag.upper() in docx_tools.FLAGS else self.md(f"**{flag}**" if flag else "")
        weeks = [t for t in d.get("trend") or [] if t.get("date") != self.doc.get("date")][-5:] + \
            [{"date": self.doc.get("date"), "flag": flag}]
        if flag or len(weeks) > 1:
            w, h = STRIP
            bw = (w - 2 * (len(weeks) - 1)) / len(weeks)
            bars = "".join(f'<rect x="{i * (bw + 2):.1f}" y="0" width="{bw:.1f}" height="10" fill="#{TONE_HEX[_tone(k.get("flag"))]}"/>'
                           for i, k in enumerate(weeks))
            svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{bars}'
                   f'<text x="0" y="26" font-family="Arial,sans-serif" font-size="9.5" fill="#5E6270">{esc(_dm(weeks[0]["date"]))}</text>'
                   f'<text x="{w}" y="26" text-anchor="end" font-family="Arial,sans-serif" font-size="9.5" fill="#5E6270">'
                   f'{esc(_dm(weeks[-1]["date"]))}</text></svg>')
            e += self.picture(svg, w, h)
        e += self.md(s.get("text"))
        lw = d.get("last_week") or {}
        if lw.get("flag"):
            e += self.md(f"Last week: {lw['flag']}" + (f" ({_dm(lw['date'])})" if lw.get("date") else ""))
        return [("e", e)] if e else []

    def figures(self, s):
        """At a glance: the shown figures as one small table, overdue in red."""
        figs = [f for f in s.get("figures") or [] if f.get("shown", True)]
        if not figs:
            return []
        cols = [{"header": _nobraces(f.get("label")), "width": 1} for f in figs]
        row = [_nobraces(f"{f.get('value') or ''}" + (f"\n{f['note']}" if f.get("note") else "")) for f in figs]
        red = {i for i, f in enumerate(figs) if f.get("key") == "overdue" and str(f.get("value")) not in ("0", "")}
        return [("t", cols, [row], lambda r, c: TONE_HEX["r"] if c in red else None)]

    def _heads(self, s, cols):
        """The columns shown: the section's own, then the ones the screen works out from the item (Response, Late)."""
        keys = [c.get("key") for c in cols]
        extra = [("response", "Response")] if s.get("id") == "risks" and "response" not in keys else \
            [("late", "Late")] if s.get("id") == "overdue" and "late" not in keys else []
        return [(c.get("key"), c.get("label")) for c in cols] + extra

    def _cell(self, key, cells, item):
        """One cell's words and its tone (or None): Response and Late come from the item as the screen draws them."""
        if key == "response" and key not in cells:
            return item.get("response_action") or item.get("response") or "", None
        if key == "late" and key not in cells:
            a, b = _day(item.get("due_date")), _day(self.doc.get("date"))
            n = max(0, b - a) if a and b else 0
            return (f"{n} day{'' if n == 1 else 's'}", "r") if n else ("", None)
        v = cells.get(key)
        if key == "priority" and v:
            return str(v).upper(), PRIORITY_TONE.get(str(v).lower(), "n")
        return v, None

    def table(self, s):
        """A table section: its intro text, then the table with every column the screen shows, or the screen's sentence when empty."""
        cols = list(s.get("columns") or [])
        rows = [r for r in s.get("rows") or [] if r.get("shown", True)]
        intro = self.md(s.get("text"))
        parts = [("e", intro)] if intro else []
        if not rows or not cols:
            return parts + [("e", [{"md": EMPTY_SENTENCE.get(s.get("id"), "Nothing to show.")}])]
        heads = self._heads(s, cols)
        body, tone = [], {}
        for ri, r in enumerate(rows, start=1):
            item, cells, line = self.items.get(r.get("ref") or "") or {}, r.get("cells") or {}, []
            for ci, (k, _l) in enumerate(heads):
                v, t = self._cell(k, cells, item)
                tone[(ri, ci)] = t
                line.append(_nobraces(v))
            body.append(line)
        return parts + [("t", [{"header": _nobraces(lab)} for _k, lab in heads], body,
                         lambda r, c: TONE_HEX[tone[(r, c)]] if tone.get((r, c)) else None)]

    def _client(self):
        """True for a client report."""
        return self.doc.get("audience") == "client" or self.doc.get("kind") == "client"

    def _drawn(self, s, every):
        """The milestones the timeline picture draws: every one the section's timeline names, as the sheet does (leaving one out of
        the list tidies the list only). A client report never draws one that isn't client-safe (not client-visible, or cancelled),
        even if a document still names it: the gate drops those from the timeline, and this is a second line that FAILS CLOSED
        (p240-leakfix LEAK 3): the saved items hold no client_visible flag, so a milestone is drawn only when the tracker says it is
        one of the client-safe set (`tracker.client_milestones`: client-visible, not cancelled, with its client wording, and no
        label keeping it out); a tracker that can't be read draws none. Internal reports: flip INTERNAL_TIMELINE_DRAWS_ALL to draw
        only the listed ones."""
        if self._client():
            safe = client_safe_ids(self.doc.get("project"))
            return [m for m in every if m.get("id") in safe and int(m.get("client_visible", 1) or 0) == 1
                    and m.get("status") != "Cancelled"]
        listed = set((s.get("data") or {}).get("milestones") or [])
        return every if INTERNAL_TIMELINE_DRAWS_ALL else [m for m in every if not listed or m["id"] in listed]

    def _milestones(self, s):
        """Every milestone the timeline names, with its id, by agreed date."""
        d = s.get("data") or {}
        refs = [r for r in (d.get("timeline") or d.get("milestones") or []) if self.items.get(r)]
        every = [dict(self.items[r], id=r, baseline_date=self.items[r].get("baseline_date") or self.items[r].get("due_date"))
                 for r in refs if self.items[r].get("table", "milestones") == "milestones"]
        every.sort(key=lambda m: _day(m.get("baseline_date") or m.get("forecast_date")) or 0)
        return every

    def timeline(self, s):
        """Milestones: the timeline as a picture, then the chosen milestones as a table (Milestone, Agreed, Expected, Progress, State)."""
        every = self._drawn(s, self._milestones(s))
        parts = [("e", self.md(s.get("text")))] if str(s.get("text") or "").strip() else []
        if not every:
            return parts + [("e", [{"md": "No milestones are set for this project."}])]
        pic = self.picture(*self._timeline_svg(every))
        if pic:
            parts.append(("e", pic))
        listed = set((s.get("data") or {}).get("milestones") or [])
        rows, tone = [], {}
        for m in (m for m in every if not listed or m["id"] in listed):
            row, tones = self._ms_row(m)
            tone.update({(len(rows) + 1, c): t for c, t in tones.items()})
            rows.append(row)
        if rows:
            parts.append(("t", [{"header": h} for h in ("Milestone", "Agreed", "Expected", "Progress", "State")], rows,
                          lambda r, c: TONE_HEX[tone[(r, c)]] if tone.get((r, c)) else None))
        return parts

    def _ms_row(self, m):
        """One milestone's table row and the tones of its cells: the screen's Agreed, Expected (+days, or achieved) and State. A client
        file names the milestone by its title only: an item ID never reaches a client (p240-leakfix LEAK 2)."""
        word, t = _ms_state(m)
        base = m.get("baseline_date")
        fc = m.get("forecast_date") or base
        late = bool(_day(fc) and _day(base) and _day(fc) > _day(base))
        if m.get("actual_date"):
            exp = f"achieved {_dm(m['actual_date'])}"
        else:
            exp = _dmy(fc) + (f" (+{_day(fc) - _day(base)})" if late else "")
        pc = m.get("percent_complete")
        name = f"{'' if self._client() else (m.get('id') or '')} {m.get('title') or m.get('name') or ''}".strip()
        row = [_nobraces(name),
               _dmy(base), _nobraces(exp), f"{pc}%" if pc is not None else "", word]
        return row, {2: "r" if late and not m.get("actual_date") else None, 4: t}

    @staticmethod
    def _tl_ticks(lo, hi, px, width):
        """The timeline's line and its month ticks."""
        names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        g = [f'<line x1="10" y1="44" x2="{width - 10}" y2="44" stroke="#D9DCE6" stroke-width="2"/>']
        for t in range(lo, hi + 1):
            dt = datetime.fromordinal(t)
            if dt.day == 1:
                x = 20 + (t - lo) * px
                g.append(f'<line x1="{x:.1f}" y1="38" x2="{x:.1f}" y2="50" stroke="#D9DCE6" stroke-width="2"/>'
                         f'<text x="{x + 3:.1f}" y="86" font-size="10.5" fill="#5E6270">{names[dt.month - 1]}'
                         f'{(" " + str(dt.year)) if dt.month == 1 else ""}</text>')
        return g

    @staticmethod
    def _tl_marker(i, m, X, today):
        """One milestone on the timeline: its circle, its slip from agreed to expected, its label."""
        t = _ms_state(m)[1]
        col = "#" + TONE_HEX[t]
        base, fc = m.get("baseline_date") or m.get("forecast_date"), m.get("forecast_date")
        done = (t == "g" and m.get("status") == "Done") or _day(base) < _day(today)
        x = X(base)
        slip = bool(fc and fc != base and _day(fc) > _day(base))
        fx, ly = (X(fc) if slip else x), (28 if i % 2 else 68)
        g = f'<circle cx="{x:.1f}" cy="44" r="6" fill="{col if done else "#F8F8FF"}" stroke="{col}" stroke-width="2"/>'
        if slip:
            g += (f'<line x1="{x + 7:.1f}" y1="44" x2="{fx - 8:.1f}" y2="44" stroke="#C0392B" stroke-width="2"/>'
                  f'<circle cx="{fx:.1f}" cy="44" r="7" fill="none" stroke="#C0392B" stroke-width="2" stroke-dasharray="3 2"/>')
        words = (m.get("title") or m.get("name") or "") + " · " + _dm(fc if slip else base)
        return g + f'<text x="{fx:.1f}" y="{ly}" text-anchor="middle" font-size="10.5" fill="#1E1F1E">{esc(words)}</text>'

    def _timeline_svg(self, ms):
        """The sheet's timeline drawing (Timeline.jsx Drawing) as SVG sized to the page: the line, month ticks, today, each milestone
        and its slip. Returns (svg, width, height)."""
        import report                                          # today on creaite's clock (CREAITE_NOW fixes it for tests)
        today = self.doc.get("date") if self.doc.get("state") == "approved" else report.today().isoformat()
        days = [_day(x) for m in ms for x in (m.get("baseline_date"), m.get("forecast_date"), m.get("actual_date")) if _day(x)]
        days.append(_day(today))
        lo, hi = min(days) - 14, max(days) + 21
        px = max(1.5, min(6.0, (TIMELINE_WIDTH - 40) / max(1, hi - lo)))
        width, height = round(40 + (hi - lo) * px), 92
        tx = 20 + (_day(today) - lo) * px
        g = self._tl_ticks(lo, hi, px, width)
        g.append(f'<line x1="{tx:.1f}" y1="10" x2="{tx:.1f}" y2="56" stroke="#1E1F1E" stroke-dasharray="3 3"/>'
                 f'<text x="{tx + 4:.1f}" y="14" font-size="10.5" fill="#1E1F1E">Today</text>')
        g += [self._tl_marker(i, m, lambda iso: 20 + (_day(iso) - lo) * px, today) for i, m in enumerate(ms)]
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
               f'font-family="Arial,sans-serif">{"".join(g)}</svg>')
        return svg, width, height


def _plain_inline(t):
    """Inline Markdown as the words Word shows (marks gone, a link as 'words (address)'), a backslash escape as its character."""
    import docx_tools
    return docx_tools.plain(str(t or ""), True)


def _rpr(para, bold=False, italic=False, mono=False, size=None):
    """The paragraph with its runs' properties set (bold, italic, a fixed-width font, a size in half-points), in the order Word reads."""
    import docx_tools
    fonts = f'<w:rFonts w:ascii="{docx_tools.MONO}" w:hAnsi="{docx_tools.MONO}" w:cs="{docx_tools.MONO}"/>' if mono else ""
    sized = f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>' if size else ""
    props = fonts + ("<w:b/>" if bold else "") + ("<w:i/>" if italic else "") + sized

    def run(m):
        """One run with its properties replaced."""
        inner = re.sub(r"<w:(?:rFonts|b|i|sz|szCs)\b[^>]*/>", "", m.group(2) or "")
        return f"{m.group(1)}<w:rPr>{props}{inner}</w:rPr>"
    return re.sub(r"(<w:r(?: [^>]*)?>)(?:<w:rPr>(.*?)</w:rPr>)?", run, para, flags=re.S)


HEADING_SIZES = {1: 28, 2: 26, 3: 24}                   # half-points: a text section's heading levels 1 to 3 (14, 13 and 12 pt)


def _heading_para(para, level, text):
    """A text section's heading inside its body: the template paragraph, bold, sized by its level, kept with what follows."""
    import docx_tools
    p = _rpr(docx_tools.put_text(para, text), bold=True, italic=level >= 3, size=HEADING_SIZES.get(level, 24))
    return p.replace("<w:pPr>", "<w:pPr><w:keepNext/>", 1)


def _code_paras(para, text):
    """A code block: one paragraph per line in a fixed-width font on a light ground, its indentation kept, close together."""
    import docx_tools
    lines = str(text).expandtabs(4).split("\n") or [""]
    out = []
    for n, line in enumerate(lines):
        p = _rpr(docx_tools.put_text(para, line or " "), mono=True, size=18)
        after = 160 if n == len(lines) - 1 else 0
        ppr = ('<w:pPr><w:shd w:val="clear" w:color="auto" w:fill="F3F4F7"/>'
               f'<w:spacing w:before="0" w:after="{after}" w:line="240" w:lineRule="auto"/><w:ind w:left="144" w:right="144"/></w:pPr>')
        p = re.sub(r"<w:pPr>.*?</w:pPr>", "", p, count=1, flags=re.S)
        at = re.match(r"<w:p(?: [^>]*)?>", p).end()                 # the paragraph's properties go straight after its opening tag
        out.append(p[:at] + ppr + p[at:])
    return "".join(out)


def client_safe_ids(code):
    """The ids of the project's milestones a client may be shown, read from the tracker now (p240-leakfix LEAK 3); an empty set when
    the tracker can't be read (fail closed). A test replaces it."""
    try:
        import client_leak
        import report
        import tracker
        with tracker.connect() as con:
            blocking = client_leak.blocking_labels(con)
            return {m["id"] for m in tracker.client_milestones(report.milestones(con, code))
                    if not client_leak.item_problem(con, m["id"], blocking)}
    except Exception:
        return set()


def _colour_table(tbl, styler):
    """The table with the text of each body cell the styler names (row, column; row 0 is the header) bold and in its colour."""
    for r, row in enumerate(re.findall(r"<w:tr>.*?</w:tr>", tbl, re.S)):
        if r == 0:
            continue
        new = row
        for c, cell in enumerate(re.findall(r"<w:tc>.*?</w:tc>", row, re.S)):
            hexv = styler(r, c)
            if hexv:
                new = new.replace(cell, re.sub(r"<w:rPr>", f'<w:rPr><w:b/><w:color w:val="{hexv}"/>', cell), 1)
        tbl = tbl.replace(row, new, 1)
    return tbl


def _status_line(doc):
    """The title block's status: the audience, then Draft and its version, or Approved and when."""
    import tracker
    label = {"internal": "Internal", "client": "Client", "distributed": "Distributed"}[doc.get("audience") or "internal"]
    if doc.get("state") != "approved":
        return f"{label} · Draft, version {doc.get('version') or 0}"
    when = tracker.long_date(str(doc["approved_at"])[:10]) if doc.get("approved_at") else ""
    return f"{label} · Approved{' ' + when if when else ''}"


def _front_values(doc):
    """The title block's placeholders, from the document."""
    import tracker
    d, meta = doc.get("date") or "", doc.get("meta") or {}
    return {"PROJECT_NAME": doc.get("project_name") or doc.get("title"), "MEETING_TITLE": doc.get("title"),
            "STATUS_LINE": _status_line(doc), "WEEK_ENDING": tracker.long_date(d), "CLIENT_NAME": doc.get("client") or "",
            "PERIOD_START": tracker.long_date(meta.get("period_start") or d), "PERIOD_END": tracker.long_date(d),
            "MEETING_WHEN": meta.get("when") or tracker.long_date(d), "REPORT_DATE": tracker.long_date(d)}


def _front(els, doc):
    """The template's title block, filled: the project or meeting, the status line and the date. Health and attendees lines go
    (they are sections)."""
    import docx_tools
    values, has_start = _front_values(doc), bool((doc.get("meta") or {}).get("period_start"))
    out = []
    for el in els:
        text = _word_text(el)
        if any(p in text for p in FRONT_DROP):
            continue
        if "{{" in text:
            text = text if has_start else text.replace("{{PERIOD_START}} to {{PERIOD_END}}", "week ending {{PERIOD_END}}")
            text = re.sub(r"\{\{(\w+)\}\}", lambda m: _nobraces(values.get(m.group(1), "")), text).strip(" ·")
            el = docx_tools.put_text(el, text)
        out.append(el)
    return out


def _section_blocks(ctx, n, s, heading, para, table, total):
    """One section as Word blocks (its heading, then a paragraph per text part and a table per table part) and the fill's values;
    none when there is nothing to show (no empty heading)."""
    import docx_tools
    parts = ctx.parts(s)
    if not parts:
        return [], {}
    out, values = [docx_tools.put_text(heading, _nobraces(s.get("heading")))] if str(s.get("heading") or "").strip() else [], {}
    for k, part in enumerate(parts):
        if part[0] == "e":
            out.append(docx_tools.replace_in(para, {"SUMMARY": "{{CX_%d_%d}}" % (n, k)}))
            values[f"CX_{n}_{k}"] = part[1]
        elif part[0] == "h":
            out.append(_heading_para(para, part[1], part[2]))
        elif part[0] == "c":
            out.append(_code_paras(para, part[1]))
        else:
            _, cols, rows, styler = part
            out += [_colour_table(docx_tools.adhoc_table({"table": table}, cols, rows, total), styler), "<w:p/>"]
    return out, values


def _logos_front(ctx, shown, out, para):
    """The report's chosen logos as a line under the template's wordmark (added to `out`); the fill's value for it."""
    import docx_tools
    header = next((s for s in shown["sections"] if s.get("type") == "header" and not s.get("hidden")), None)
    logos = ctx.logos(header) if header else []
    if not (logos and out):
        return {}
    out.insert(1, docx_tools.replace_in(para, {"SUMMARY": "{{CX_LOGOS}}"}))
    return {"CX_LOGOS": logos}


def _word_body(doc, els, work):
    """The derived template's body (the title block, the logos, then each shown section in page order) and the fill's values."""
    import docx_tools
    texts = [_word_text(e) for e in els]
    at = next((i for i, t in enumerate(texts) if "{{SUMMARY}}" in t), None)
    table = next((e for e in els if e.startswith("<w:tbl>")), None)
    if not at or table is None:
        raise DocError("The Word template isn't one creaite can fill (no summary or table to copy).")
    heading, para = els[at - 1], els[at]
    total = sum(int(w) for w in re.findall(r'<w:gridCol w:w="(\d+)"', table)) or 9000
    out, values = _front(els[:at - 1], doc), {}
    out += [e for e, t in zip(els, texts) if "{{STYLE_" in t]              # the fill's style samples (topic headings)
    shown = clean(doc)
    ctx = _Word(shown, work)
    values.update(_logos_front(ctx, shown, out, para))
    for n, s in enumerate(shown["sections"]):
        if not s.get("hidden") and s.get("type") != "header":
            blocks, vals = _section_blocks(ctx, n, s, heading, para, table, total)
            out += blocks
            values.update(vals)
    return out, values, ctx.drawn


def word_export(doc, out):
    """Write the Word export of `doc` at `out` (inside system/staging/drafts/): the firm's template for its kind, its title block,
    then each shown section in page order, filled by docx_tools.py fill. Returns the hashes of the pictures it drew itself (v2.5.1,
    client_output.check). Raises DocError."""
    import contextlib
    import io
    import shutil
    import docx_tools
    tpl = paths.TEMPLATES / TEMPLATES[doc["kind"]]
    if not tpl.is_file():
        raise DocError(f"The Word template is missing: {paths.rel(tpl)}.")
    parts = docx_tools.read_parts(tpl)
    xml = next(raw for info, raw in parts if info.filename == "word/document.xml").decode("utf-8")
    start = xml.index("<w:body>") + len("<w:body>")
    sect = re.findall(r"<w:sectPr.*?</w:sectPr>", xml[start:], re.S)[-1]
    stamp = f"{out.stem} {datetime.now():%H%M%S}"
    work = paths.free_path(paths.DRAFTS, f"{stamp} pictures", "")
    work.mkdir(parents=True, exist_ok=True)
    tmp_tpl = paths.free_path(paths.DRAFTS, f"{stamp} template", ".docx")
    tmp_values = paths.free_path(paths.DRAFTS, f"{stamp} values", ".json")
    said = io.StringIO()
    try:
        body, values, drawn = _word_body(doc, WORD_EL.findall(xml[start:xml.rindex(sect)]), work)
        derived = xml[:start] + "".join(body) + sect + "</w:body></w:document>"
        docx_tools.write_parts([(i, derived.encode("utf-8") if i.filename == "word/document.xml" else raw) for i, raw in parts], tmp_tpl)
        tmp_values.write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8")
        with contextlib.redirect_stdout(said):
            code = docx_tools.cmd_fill(str(tmp_tpl), str(tmp_values), str(out))
    finally:
        for f in (tmp_tpl, tmp_values):
            f.unlink(missing_ok=True)
        shutil.rmtree(work, ignore_errors=True)
    if code != 0:
        raise DocError(f"The Word export couldn't be filled: {said.getvalue().strip()}")
    return {h for h in drawn if h}


# ── PDF: Chrome's print to PDF of the HTML export ────────────────────────────

def print_pdf(page, out):
    """Print the HTML `page` to the PDF `out` with Chrome, headless, in a throwaway profile. Raises DocError."""
    import os
    import shutil
    import signal
    import subprocess
    import tempfile
    import launch
    chrome = launch.find_chrome()
    if not chrome:
        raise DocError("Chrome wasn't found, so the PDF wasn't made. Install Google Chrome (creaite needs it) and try again.")
    profile = tempfile.mkdtemp(prefix="creaite-pdf-")
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--disable-extensions",
           f"--user-data-dir={profile}", "--no-pdf-header-footer", "--print-to-pdf-no-header", f"--print-to-pdf={out}",
           Path(page).resolve().as_uri()]
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    try:
        proc.wait(timeout=CHROME_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)       # its own session: Chrome and only its helpers
        proc.wait()
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    if not (Path(out).is_file() and Path(out).read_bytes()[:5] == b"%PDF-"):
        Path(out).unlink(missing_ok=True)
        raise DocError("Chrome didn't make the PDF. Try again; if it keeps failing, Settings › Diagnostics has the details.")
