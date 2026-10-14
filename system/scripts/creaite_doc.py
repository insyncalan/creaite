"""creaite's own document format (v2.1.0 P1; BL-335, BL-336, BL-338). Standard library only. A library: no command line.

A weekly report, a client report or a meeting's minutes is one .html file: a self-contained A4 page rendered from the data (inline
CSS, no script but the data block, nothing loaded from anywhere, so it opens in any browser) and a
<script type="application/json" id="creaite-data"> block holding the data. The data is the record; the page is always rendered from
it, so the filed page and every export match. The data block's shape is in dev/sprints/v210-contract.md.

Saving goes through filechange.py: a new file is a create, a later save an edit (the earlier version backed up, logged and
undoable). Hidden sections, rows and figures never reach the page, an export or the file (clean). Search reads every shown section
(search_text, called by tracker.text_of).
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

def new(kind, project, title, date, sections=(), *, audience="internal", client=None, layout=None, items=None, sources=None,
        meta=None):
    """A schema-1 document, version 0 and a draft; nothing is written. Raises DocError for a kind, audience or date it can't hold."""
    doc = {"format": FORMAT, "schema": SCHEMA, "kind": kind, "audience": audience, "project": project,
           "project_name": project_name(project) if project != "_portfolio" else "", "title": title, "date": date,
           "client": client, "version": 0, "saved_at": None, "state": "draft", "approved_at": None, "based_on": None,
           "layout": dict(layout or {}), "sections": [dict(s) for s in sections], "items": dict(items or {}),
           "sources": list(sources or []), "meta": dict(meta or {})}
    check(doc)
    return doc


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


def _stub_row(row):
    """A hidden row as it is kept: its reference only."""
    return {"ref": row.get("ref"), "shown": False}


def _clean_section(s):
    """A section with its hidden content dropped (a hidden section keeps only its place and heading)."""
    if s.get("hidden"):
        return {k: s[k] for k in HIDDEN_KEEP if k in s}
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


def clean(doc):
    """A copy with hidden sections, rows and figures emptied, and the items only they named dropped. check()s it first."""
    check(doc)
    out = copy.deepcopy(doc)
    hidden = _hidden_refs(out.get("sections") or [])
    out["sections"] = [_clean_section(s) for s in out.get("sections") or []]
    visible = _visible_text(out["sections"])
    out["items"] = {k: v for k, v in (out.get("items") or {}).items() if k not in hidden or k in visible}
    return out


# ── The file ─────────────────────────────────────────────────────────────────

def data_json(doc):
    """The data block's JSON, safe inside a <script> element: every '<' written as \\u003c, which JSON reads back as it was."""
    return json.dumps(doc, ensure_ascii=False, indent=1).replace("<", "\\u003c")


def dumps(doc):
    """The whole file: the page with the data block."""
    return render(doc, editing=True)


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
@media print{body{background:#fff}.page{margin:0;box-shadow:none;width:auto;min-height:0;padding:0}@page{size:A4;margin:16mm}}
"""


def esc(t):
    """Text escaped for HTML; None becomes ''."""
    return html.escape(str(t if t is not None else ""), quote=True)


def md_html(text):
    """Markdown (as the one editor writes it) as safe HTML: paragraphs, lists and bold; links keep their text only."""
    import prep_page
    return prep_page.blocks_html(prep_page.md_blocks(text))


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


def section_html(s, items):
    """One shown section's HTML; an unknown type renders its text only."""
    kind = s.get("type")
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


def render(doc, editing=True):
    """The page for the document; with `editing` the data block is included (the filed file), without it not (the HTML export).
    Hidden content is never rendered; source tags never are."""
    doc = clean(doc)
    items = doc.get("items") or {}
    body = "".join(section_html(s, items) for s in doc["sections"] if not s.get("hidden"))
    label = {"internal": "Internal", "client": "Client", "distributed": "Distributed"}[doc.get("audience") or "internal"]
    head = (f'<header class="doc"><div><h1>{esc(doc.get("title"))}</h1><div class="sub">{esc(doc.get("project_name"))}'
            f'{(" · " + esc(doc["client"])) if doc.get("client") else ""}</div></div><div class="sub">{esc(label)}</div></header>')
    data = f'\n<script type="application/json" id="{DATA_ID}">{data_json(doc)}</script>' if editing else ""
    return (f'<!doctype html>\n<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            f"<title>{esc(page_title(doc))}</title><style>{CSS}</style></head>\n"
            f'<body><main class="page">{head}{body}</main>{data}\n</body></html>\n')


# ── Search ───────────────────────────────────────────────────────────────────

def _plain(md):
    """Markdown as plain words."""
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", str(md or ""))
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
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
        out = clean(doc)
    except DocError as e:
        return _refusal(str(e))
    if base_version is not None and int(base_version) != was:
        return _refusal(f"It was saved elsewhere since you opened it (now version {was}).", conflict=True)
    out.update(version=was + 1, saved_at=now())
    data = dumps(out).encode("utf-8")
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
