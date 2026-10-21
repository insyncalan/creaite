"""The property runner for test_client_output_properties.py (#239): seeded hostile client reports, run inside the test's throwaway
vault (its own scripts imported), one property at a time. Standard library only. Not a test file itself.

    python3 dev/tests/client_output_props.py <vault root> <property P1..P25> <seed> <cases> [mutant]

prints one JSON line {"property", "seed", "cases", "stats", "failures": [...]}; a failure names its case and its mutations, so a
run can be replayed with the same seed. `mutant` switches one guard off in this process (MUTANTS), for the mutation proofs.

The generator follows Team Cap's property list (dev/proposals/props239/PROPERTIES.md on origin/v251-properties) and its sketch
(gen_sketch.py): the same value pools, text encoders and mutations, on the vault's real clean client draft (its own hidden item H,
another project's hidden item X, a client-visible item VIS), with an internal text section (free_b) in the clean draft.
"""
import contextlib
import copy
import hashlib
import html
import json
import os
import random
import re
import subprocess
import sys
import threading
import zipfile
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(sys.argv[1]).resolve()
SCRIPTS = ROOT / "system" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import client_leak  # noqa: E402
import client_output  # noqa: E402
import confusables  # noqa: E402
import creaite_doc  # noqa: E402
import minutes_record  # noqa: E402
import paths  # noqa: E402
import report_doc  # noqa: E402
import report_server  # noqa: E402

WEEK, OTHER_WEEK, CODE = "2026-10-09", "2026-10-16", "ABC"
STEM = "2026-10-09 Client report - Example Programme (Example Client Ltd)"
DRAFT = f"system/staging/drafts/{STEM}.html"
REPORTS = ROOT / "projects/ABC Example Programme/reports"
DRAFTS = ROOT / "system/staging/drafts"
LOCK = threading.Lock()


APPLY_PREAMBLE = []          # mutants only: lines run in the tracker.py process before it starts (apply_check_off)


def run_script(script, *args):
    """The live server's run(): one creaite script from the vault root."""
    cmd = [sys.executable, str(SCRIPTS / script), *args]
    if APPLY_PREAMBLE and script == "tracker.py":
        cmd = [sys.executable, "-c", "import runpy, sys\n" + "\n".join(APPLY_PREAMBLE)
               + f"\nsys.argv = [{str(SCRIPTS / script)!r}] + sys.argv[1:]\nrunpy.run_path(sys.argv[0], run_name='__main__')", *args]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


report_server.routes(LOCK, run_script, lambda: None)
REAL_SHAPE = creaite_doc.client_shape          # the allow-list as the code has it, kept before any mutant switches it off


# ── the world: H, X, VIS and the needles ─────────────────────────────────────
def _world():
    import sqlite3
    from contextlib import closing
    with closing(sqlite3.connect(ROOT / "system/tracker.db")) as con:
        alan = {client_leak.person(n).lower() for n in client_leak.alans_names() if n}        # Alan is named in his client reports
        rows = con.execute("SELECT id, description, owner FROM actions WHERE project='ABC' AND client_visible=0 AND owner<>'' "
                           "ORDER BY id").fetchall()
        h = next((x for x in rows if client_leak.person(x[2]).lower() not in alan), None) or (rows[0][0], rows[0][1], None)
        x = con.execute("SELECT id, description, owner FROM actions WHERE project='DEF' AND client_visible=0 AND owner<>'' "
                        "ORDER BY id LIMIT 1").fetchone()
    return ({"id": h[0], "title": h[1], "owner": h[2]}, {"id": x[0], "title": x[1], "owner": x[2]})


H, X = _world()
NEEDLES = [x for x in (H["id"], H["title"], H["owner"]) if x] + [X["id"], X["title"], X["owner"], "confidential", "Internal only", "INTWALRUS",
           "ZEBRAPAY", "SECRETFIELD", "creaite:item"]


# ── text encoders (gen_sketch FORMS) ─────────────────────────────────────────
ZW = "\u200b\u200d\u2060\ufeff\u00ad"
def f_plain(s, r): return s
def f_pct(s, r): return quote(s, safe="")
def f_pct2(s, r): return quote(quote(s, safe=""), safe="")
def f_ent(s, r): return "".join(f"&#{ord(c)};" if c.isalnum() and r.random() < .4 else c for c in s)
def f_zw(s, r): return "".join(c + (r.choice(ZW) if r.random() < .3 else "") for c in s)
def f_full(s, r): return "".join(chr(ord(c) + 0xFEE0) if "!" <= c <= "~" and r.random() < .5 else c for c in s)
def f_cyr(s, r): return s.translate(str.maketrans({"a": "\u0430", "e": "\u0435", "o": "\u043e", "c": "\u0441", "A": "\u0410",
                                                   "s": "\u0455", "d": "\u0501", "y": "\u0443"}))
def f_md(s, r):
    return r.choice(["[x](%s)", "![x](%s)", "**%s**", "`%s`", "> %s", "- %s", "<a href='u'>%s</a>",
                     "[%s](creaite:item/" + H["id"] + ")"]) % s
def f_json(s, r): return json.dumps(s)[1:-1].replace("a", "\\u0061", 1)
def f_case(s, r): return r.choice([s.upper(), s.lower(), s.swapcase()])
def f_space(s, r):
    return s.replace("-", r.choice([" ", "\u2011", "\u2010", "_", "\u00a0"])).replace(" ", r.choice(["  ", "\n", "\t", "\u00a0"]), 1)


FORMS = [f_plain, f_pct, f_pct2, f_ent, f_zw, f_full, f_cyr, f_md, f_json, f_case, f_space]
PIECES = [x for x in (H["id"], H["title"], H["owner"]) if x] + ["This is confidential", "Internal only: keep", X["title"], X["owner"], X["id"],
          f"[the plan](creaite:item/{H['id']})"]


EXTRA = ["ZEBRAPAY", "SECRETFIELD", "INTWALRUS"]      # words no gate knows: hidden only where they are put (a derived or unknown field)


def payload(r, form=None, extra=False):
    """Hidden material in some form (gen_sketch.payload): what the gate knows (the hidden item, another project's, the markers, a
    creaite link); with `extra`, also the words only their place makes hidden (header-only words), for fields that never show."""
    s = " ".join(r.sample(PIECES + (EXTRA if extra else []), r.randint(1, 3)))
    return (form or r.choice(FORMS))(s, r)


# ── the oracle O1 (gen_sketch.leaks, our confusables skeleton as the fold) ───
def fold(s):
    return "".join(c for c in confusables.skeleton(s).lower() if c.isalnum())


def undo_escapes(t):
    for _ in range(3):
        t = unquote(html.unescape(re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), t)))
    return t


def leaks(blobs, needles=None):
    """{surface: [needle]} of the needles whose folded form is in a surface's folded, unescaped text."""
    out = {}
    for k, b in blobs.items():
        t = b.decode("utf-8", "ignore") if isinstance(b, bytes) else str(b)
        f = fold(undo_escapes(t))
        hit = [n for n in (needles or NEEDLES) if fold(n) in f]
        if hit:
            out[k] = hit
    return out


def blobs_of(p):
    """The surfaces of one output file: html bytes; every docx part, media names and hashes; pdf text and raw strings; its name."""
    p = Path(p)
    out = {f"name:{p.name}": p.name}
    if p.suffix == ".docx":
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                data = z.read(n)
                out[f"{p.name}:{n}"] = data if n.endswith((".xml", ".rels")) else n + " " + hashlib.sha1(data).hexdigest()
        out[f"{p.name}:text"] = client_output.docx_text(p)
    elif p.suffix == ".pdf":
        out[f"{p.name}:text"] = client_output.pdf_text(p)
        out[f"{p.name}:raw"] = p.read_bytes()
    else:
        out[p.name] = p.read_bytes()
    return out


# ── the base draft and how a case lands ──────────────────────────────────────
def sec(i, t, h, **k):
    return {"id": i, "type": t, "heading": h, "default_heading": h, "hidden": False, **k}


def clean_base():
    d = creaite_doc.read(ROOT / DRAFT)
    d["sections"] = [s for s in d["sections"] if not str(s["id"]).startswith("free_")]
    d["sections"] += [sec("free_a", "freetext", "Notes", text="Plain words.", audience="client"),
                      sec("free_b", "freetext", "Vendor notes", text="INTWALRUS internal words.", audience="internal")]
    d["layout"]["order"] = [s["id"] for s in d["sections"]]
    return d


def vis_row(d):
    """The first shown table row of the base (a client-visible item) and its section, or (None, None)."""
    for s in d["sections"]:
        for r in s.get("rows") or []:
            if r.get("shown", True) and r.get("ref"):
                return s, r
    return None, None


KIND = ["weekly", "minutes", "Client", " client", "client\u200b", ["client"], {"k": "client"}, 1, "clent", "distributed", None,
        "__missing__"]
AUD = ["internal", "distributed", "weekly", "Client", None, ["client"], "__missing__"]
PATHS = ["../../../.ssh/id_rsa", "/etc/hosts", "_images/../x.png", "C:\\x.png", "file:///etc/hosts", "https://beacon.example/a.png",
         "_images/internal-raid-screenshot.png", "../documents/vault.png", "documents/secret.png", "\\\\host\\share\\a.png"]
NAMES = ["CON", "NUL", "COM1", "COM\u00b9", "CONIN$", "aux.docx", "a<b>.docx", 'a"b.docx', "a|b?.docx", "a:b.docx", "a*b", ".hidden",
         "x" * 151, "..", "a/b", "a\\b", "a\x00b", STEM, "2026-10-09 Weekly report - Example Programme", "weekly report",
         "CLIENT   REPORT", "client\u00a0report", "Client report (2)", "plain name", "trailing dot.", "trailing space "]
UNKNOWN_KEYS = ["ref", "milestones", "timeline", "note", "comment", "html", "style", "href", "src", "path", "internal", "owner", "x-raw"]
PIC_REFS = ["_images/../../x.png", "/etc/hosts", "documents/vault.png", "_images/a b.png", "images/internal-org-chart.png",
            "../images/internal-org-chart.png", "https://beacon.example/a.png"]
RAW = ["dupkind_badlast", "dupkind_badfirst", "dupaud_badlast", "dupproj_badlast", "bom", "crlf", "trailing_comma", "second_block",
       "comment_first", "huge_padding", "raw_html_in_block"]


def top(key, pool):
    def m(d, r):
        v = r.choice(pool)
        if v == "__missing__":
            d.pop(key, None)
        else:
            d[key] = v(r, extra=True) if callable(v) else v
        return True
    m.__name__ = f"top_{key}"
    return m


def txt_field(sec_id, key):
    def m(d, r):
        s = next((x for x in d["sections"] if x["id"] == sec_id), None)
        if not s:
            return False
        s[key] = payload(r)
        return True
    m.__name__ = f"{sec_id}_{key}"
    return m


def m_header(d, r):
    h = next(s for s in d["sections"] if s.get("type") == "header").setdefault("data", {})
    h.update(title=payload(r, extra=True), partners=[payload(r, extra=True)],
             logos=[{"kind": r.choice(["firm", "client", "partner:zzz", "other"]), "path": r.choice(PATHS)}])
    return True


def m_rows(d, r):
    t, _row = vis_row(d)
    if not t:
        return False
    it = r.choice([H, X])
    t["rows"].append({"ref": it["id"], "shown": True, "cells": {k: payload(r) for k in list(t["rows"][0].get("cells") or {"x": 1})[:1]}})
    return True


def m_items(d, r):
    _s, row = vis_row(d)
    d.setdefault("items", {})[r.choice([H["id"], X["id"], (row or {}).get("ref") or H["id"]])] = {
        "title": payload(r), "owner": X["owner"], "id": H["id"]}
    return True


def m_sec_flags(d, r):
    s = next(x for x in d["sections"] if x["id"] == "free_b")
    k = r.choice(["audience=client", "audience=__missing__", "internal=True", "hidden=True", "audience=None", "audience=Client",
                  "audience= client", "audience=internal", "type=text"])
    key, _, v = k.partition("=")
    if v == "__missing__":
        s.pop(key, None)
    else:
        s[key] = {"True": True, "None": None}.get(v, v)
    return True


def m_pic(d, r):
    d["sections"].append(sec(f"free_p{r.randint(0, 99)}", "freetext", "Pic", text=f"before\n\n![chart]({r.choice(PIC_REFS)})\n\nafter",
                             audience="client"))
    return True


def _inner_places(d, row):
    """v2.5.3 (#259, P7): the inner dicts a stored key can hide in: a row's cells, a column, a tag, a figure, a pane, the header's
    data, the layout's headings and row rules, based_on."""
    s, _row = vis_row(d)
    tw = next((x for x in d["sections"] if x["id"] == "this_week"), None) or {}
    if row and not tw.get("tags"):
        tw["tags"] = [{"ref": row["ref"], "text": "x"}]
    lay = d.setdefault("layout", {})
    out = [row.setdefault("cells", {})] if row else []
    out += ((s or {}).get("columns") or [])[:1] + (tw.get("tags") or [])[:1] + _figure_and_pane(d)
    out += [next(x for x in d["sections"] if x.get("type") == "header").setdefault("data", {})]
    out += [lay.setdefault("headings", {}), lay.setdefault("rows", {}).setdefault("risks", {"top": 5})]
    return out + ([d["based_on"]] if isinstance(d.get("based_on"), dict) else [])


def _figure_and_pane(d):
    """The first figure and the first pane of the document (where there are any)."""
    figures = [f for s in d["sections"] for f in s.get("figures") or []]
    panes = [p for s in d["sections"] for p in s.get("panes") or []]
    return figures[:1] + panes[:1]


def m_unknown(d, r):
    _s, row = vis_row(d)
    tgt = r.choice([d, d.setdefault("layout", {}), d.setdefault("meta", {}), r.choice(d["sections"]),
                    d.setdefault("items", {}).setdefault((row or {}).get("ref") or "ABC-A-002", {})] + ([row] if row else [])
                   + _inner_places(d, row))
    # v2.5.3 (#259, P7): half the time only words no gate knows, which nothing but the allow-list keeps out
    tgt[r.choice(UNKNOWN_KEYS) + str(r.randint(0, 9))] = payload(r, extra=True) if r.random() < .5 else r.choice(EXTRA)
    return True


def m_proj(d, r):
    d["project"] = r.choice(["DEF", ["ABC"], "abc", "ABC\n", "", None])
    return True


def m_date(d, r):
    d["date"] = r.choice([OTHER_WEEK, "2026-13-45", "2027-01-01", [WEEK], "2026-10-9"])
    return True


def m_meta(d, r):
    d.setdefault("meta", {}).update(note=payload(r, extra=True), when=payload(r, extra=True))
    d["sources"] = list(d.get("sources") or []) + [{"ref": H["id"], "label": payload(r, extra=True)}]
    d.setdefault("layout", {})["note"] = payload(r, extra=True)
    return True


MUTATIONS = {
    "kind": top("kind", KIND), "audience": top("audience", AUD), "project": m_proj, "date": m_date,
    "project_name": top("project_name", [payload, "Example Programme X", None]),
    "client": top("client", ["Other Client Ltd", None, "SECRETFIELD", X["owner"]]), "title": top("title", ["SECRETFIELD plain", H["title"]]),
    "header": m_header, "meta_sources_layout": m_meta, "items": m_items, "rows": m_rows, "section_flags": m_sec_flags,
    "text_summary": txt_field("summary", "text"), "heading": txt_field("summary", "heading"), "notes_text": txt_field("free_a", "text"),
    "picture_ref": m_pic, "unknown_key": m_unknown,
}
WHERE = ["file", "request", "raw"]


def raw_transform(text, kind, r):
    """One raw transform of the draft file's text (gen_sketch RAW)."""
    m = creaite_doc.BLOCK.search(text)
    block = m.group(1)
    if kind.startswith("dup"):
        key = {"dupkind": "kind", "dupaud": "audience", "dupproj": "project"}[kind.split("_")[0]]
        bad = json.dumps({"kind": "minutes", "audience": "internal", "project": "DEF"}[key])
        extra = f'"{key}": {bad}, '
        block = ("{" + extra + block.lstrip()[1:]) if kind.endswith("first") else block.rstrip()[:-1] + f', "{key}": {bad}' + "}"
    elif kind == "bom":
        return "\ufeff" + text
    elif kind == "crlf":
        return text.replace("\n", "\r\n")
    elif kind == "trailing_comma":
        block = block.rstrip()[:-1] + ",}"
    elif kind == "second_block":
        d = json.loads(block)
        d["sections"].append(sec("free_z", "freetext", "Z", text=payload(r), audience="client"))
        return text + f'<script type="application/json" id="creaite-data">{creaite_doc.data_json(d)}</script>'
    elif kind == "comment_first":
        return "<!-- " + payload(r) + " -->" + text
    elif kind == "huge_padding":
        return text.replace("<body>", "<body>" + " " * 5_000_000, 1)
    elif kind == "raw_html_in_block":
        block = block.replace('"Plain words."', json.dumps("<b>Plain</b> words <script>x</script>"), 1)
    return text[:m.start(1)] + block + text[m.end(1):]


def write_block(d):
    """The draft file with this data block, as is (no normalising: a hand edit on disk)."""
    f = ROOT / DRAFT
    text = f.read_text(encoding="utf-8")
    m = creaite_doc.BLOCK.search(text)
    f.write_text(text[:m.start(1)] + creaite_doc.data_json(d) + text[m.end(1):], encoding="utf-8")


class Handler:
    def send(self, code, body):
        self.code, self.body = code, body


def route(fn, req):
    h = Handler()
    report_server.guarded(fn)(h, req)
    return h.body


def save(doc):
    return route(report_server.save_route, {"doc": doc, "base_version": None})


def land(case):
    """Put a case's mutated document where its mutations say (file, request or a raw transform of the file)."""
    d = case["doc"]
    wheres = {m["where"] for m in case["mutations"]} or {"file"}
    if "request" in wheres:
        save(copy.deepcopy(d))
    if "file" in wheres or "raw" in wheres:
        try:
            write_block(d)
        except (TypeError, ValueError):
            pass            # a value JSON can't hold: the file stays as it was
    for m in case["mutations"]:
        if m.get("raw"):
            f = ROOT / DRAFT
            f.write_text(raw_transform(f.read_text(encoding="utf-8"), m["raw"], random.Random(case["i"])), encoding="utf-8")


def cases(seed, n, base):
    """n cases of one or two mutations each (gen_sketch.cases), deterministic for the seed."""
    r = random.Random(seed)
    for i in range(n):
        doc = copy.deepcopy(base)
        done = []
        for nm in r.sample(sorted(MUTATIONS), r.choice([1, 1, 2])):
            if MUTATIONS[nm](doc, r):
                done.append({"mutation": nm, "where": r.choice(WHERE), "raw": r.choice(RAW) if r.random() < .15 else None})
        yield {"i": i, "seed": seed, "mutations": done, "doc": doc, "name": r.choice(NAMES), "fmt": r.choice(["html", "docx", "pdf"]),
               "page": r.random() < .3, "on_clash": r.choice(["number", "rename", "overwrite", None])}


# ── surfaces ─────────────────────────────────────────────────────────────────
def listing():
    out = {}
    for folder in (REPORTS, DRAFTS):
        for p in folder.rglob("*") if folder.is_dir() else []:
            if p.is_file() and "props" not in p.name:
                out[paths.rel(p)] = hashlib.sha1(p.read_bytes()).hexdigest()
    return out


def tree():
    """A hash of everything a route may write: the projects folder and system/staging (logs and backups aside)."""
    h = hashlib.sha256()
    for base in (ROOT / "projects", ROOT / "system/staging"):
        for p in sorted(base.rglob("*")):
            if p.is_file() and "props" not in p.name and p.suffix not in (".log", ".jsonl"):
                h.update(paths.rel(p).encode() + hashlib.sha1(p.read_bytes()).digest())
    return h.hexdigest()


def export(fmt, page=None, **more):
    req = {"kind": "client", "code": CODE, "week_ending": WEEK, "fmt": fmt, "on_clash": "number", **more}
    if page is not None:
        req["page"] = page
    return route(report_server.export_route, req)


def a_page(r, version=0):
    words = payload(r) if r.random() < .6 else "Vendor shortlist cut to two after the pricing review"   # words the report never had
    return {"html": r.choice([f'<div class="page"><p>{words}</p></div>', f'<div id="v-client"><div class="page"><p>{words}</p></div></div>', f'<div class="page" title="{words}"><p>x</p></div>',
                              f'<style>.a::after{{content:"{words}"}}</style><div class="page"></div>',
                              f'<div class="page"><!-- {words} --><section data-id="zz">{words}</section></div>',
                              f'<div class="page"><svg><text>{words}</text></svg></div>']),
            "css": r.choice([".page{color:#123}", ".page{color:#123}", f".x{{background:url(https://e.invalid/{quote(words)})}}"]),
            "palette": "creaite", "version": version}


def filed_content():
    """What Approve would file for the draft now (report_doc._file_ops's write), or None when Approve's own checks refuse it."""
    try:
        doc = creaite_doc.read_report(DRAFT, "client")
        report_doc.same_report(doc, "client", CODE, WEEK)
        if client_leak.findings(doc):
            return None
        ops = report_doc._file_ops("client", CODE, WEEK, doc.get("client"), DRAFT)
    except (creaite_doc.DocError, report_doc.ReportError, ValueError, TypeError, KeyError):
        return None
    return next(o["content"] for o in ops if o["op"] == "write")


def surfaces(fmts, page=None):
    """Run the exports and the filing for the draft as it is now: (blobs, made formats, refused formats, files left by refusals)."""
    blobs, made, refused, left = {}, [], [], []
    for fmt in fmts:
        before = listing()
        r = export(fmt, page if fmt != "docx" else None)
        new = {k for k in listing() if k not in before}
        if r.get("ok"):
            made.append(fmt)
            for k in new:
                blobs.update(blobs_of(paths.resolve(k)))
        else:
            refused.append(fmt)
            left += sorted(new)
        for k in new:
            paths.resolve(k).unlink(missing_ok=True)
    filed = stage_content()
    if filed is not None:
        blobs["filed"] = filed
        made.append("filed")
    return blobs, made, refused, left


def fmts_for(i, full):
    """html every case; docx every case (smoke) or every 5th (full); pdf every 20th, with Chrome."""
    import launch
    out = ["html"] + (["docx"] if not full or i % 5 == 0 else [])
    return out + (["pdf"] if i % 20 == 0 and launch.find_chrome() else [])


def reset(clean_text):
    (ROOT / DRAFT).write_text(clean_text, encoding="utf-8")
    for p in REPORTS.glob("*Client report*"):
        p.unlink()


def strip_dates(b):
    """O2's mask: timestamps (saved_at, approved_at, docx core dates, pdf dates)."""
    t = b.decode("utf-8", "ignore") if isinstance(b, bytes) else b
    t = re.sub(r'"(saved_at|approved_at)": ?"[^"]*"', r'"\1": ""', t)
    t = re.sub(r"<dcterms:(created|modified)[^>]*>[^<]*<", r"<dcterms:\1><", t)
    return re.sub(r"/(CreationDate|ModDate) ?\([^)]*\)", r"/\1()", t)


def docx_parts(p):
    with zipfile.ZipFile(p) as z:
        return {n: strip_dates(z.read(n)) if n.endswith((".xml", ".rels")) else hashlib.sha1(z.read(n)).hexdigest()
                for n in sorted(z.namelist())}


# ── the properties (PROPERTIES.md P1..P25; each returns (stats, failures)) ──
class Ctx:
    """What every property shares: the clean base draft and its file text, and the planted hostile pictures."""

    def __init__(self, full):
        self.full = full
        self.base = clean_base()
        write_block(self.base)
        self.clean_text = (ROOT / DRAFT).read_text(encoding="utf-8")
        self.bad_pics = json.loads((ROOT / "system/staging/props-pictures.json").read_text())
        from docx_tools import strip_image_metadata
        raw = [Path(x if Path(x).is_absolute() else ROOT / x).read_bytes() for x in self.bad_pics]
        self.bad_bytes = {b for x in raw for b in (x, strip_image_metadata(x))}

    def reset(self):
        reset(self.clean_text)


def named(case):
    return "+".join(f"{m['mutation']}@{m['where']}" + (f"/{m['raw']}" if m.get("raw") else "") for m in case["mutations"]) or "control"


def p1(ctx, seed, n):
    """P1 gate-or-clean: whatever a case's mutations, no output that is made holds a needle (O1), and a refusal leaves no file."""
    fails, stats = [], {"made": 0, "refused": 0}
    for c in cases(seed, n, ctx.base):
        ctx.reset()
        land(c)
        page = a_page(random.Random(c["i"])) if c["page"] else None
        blobs, made, refused, left = surfaces(fmts_for(c["i"], ctx.full), page)
        stats["made"] += len(made)
        stats["refused"] += len(refused)
        hit = leaks(blobs)
        if hit or left:
            fails.append({"case": c["i"], "mutations": named(c), "leaks": hit, "left": left})
    return stats, fails


@contextlib.contextmanager
def counting_reads():
    """Count the reads of the draft file (creaite_doc.read and Path.read_text/read_bytes on it)."""
    seen = [0]
    target = (ROOT / DRAFT).resolve()
    real_text, real_bytes = Path.read_text, Path.read_bytes

    def text(self, *a, **k):
        if Path(self).resolve() == target:
            seen[0] += 1
        return real_text(self, *a, **k)

    def raw(self, *a, **k):
        if Path(self).resolve() == target:
            seen[0] += 1
        return real_bytes(self, *a, **k)
    Path.read_text, Path.read_bytes = text, raw
    try:
        yield seen
    finally:
        Path.read_text, Path.read_bytes = real_text, real_bytes


def expected_html():
    """render(the one parsed object) of the draft as it is now, or None when it can't be read as this client report."""
    try:
        d = creaite_doc.read_report(DRAFT, "client")
        report_doc.same_report(d, "client", CODE, WEEK)
        return creaite_doc.render(d, editing=False)
    except (creaite_doc.DocError, report_doc.ReportError, ValueError, TypeError, KeyError, AttributeError):
        return None


def p2(ctx, seed, n):
    """P2 one read: an HTML export is byte-equal to render(the one object parsed from the bytes read), and the draft file is read
    once per export."""
    fails, stats = [], {"made": 0}
    for c in cases(seed, n, ctx.base):
        ctx.reset()
        land(c)
        want = expected_html()
        with counting_reads() as seen:
            r = export("html", a_page(random.Random(c["i"])) if c["page"] else None)
        if not r.get("ok"):
            continue
        stats["made"] += 1
        got = paths.resolve(r["path"]).read_text(encoding="utf-8")
        paths.resolve(r["path"]).unlink()
        if got != want or seen[0] != 1:
            fails.append({"case": c["i"], "mutations": named(c), "same": got == want, "reads": seen[0]})
    return stats, fails


DERIVED_MUTATIONS = ("audience", "project_name", "client", "title", "header")


def derived_ok(d):
    """The derived fields of a cleaned client report hold their derived values (P3's model)."""
    return (d.get("audience") == "client" and d.get("project_name") == creaite_doc.project_name(CODE)
            and d.get("client") == creaite_doc.project_client(CODE) and d.get("title") == "Client report"
            and all(s.get("data", {}).get("logos") == report_doc.client_logos(CODE, d.get("layout")) for s in d["sections"]
                    if s.get("type") == "header"))


def masked_block(f):
    b = json.loads(creaite_doc.BLOCK.search(Path(f).read_text(encoding="utf-8")).group(1))
    b.update(saved_at=None, version=None)
    return b


def p3(ctx, seed, n):
    """P3 derived fields are fixed points: clean(clean(D)) == clean(D) with every derived field at its derived value, and
    save(save(D)) == save(D) (masked: saved_at, version)."""
    fails, r = [], random.Random(seed)
    for i in range(n):
        d = copy.deepcopy(ctx.base)
        for nm in r.sample(DERIVED_MUTATIONS, r.randint(1, 2)):
            MUTATIONS[nm](d, r)
        d["kind"] = "client"
        try:
            c1 = creaite_doc.clean(d)
        except creaite_doc.DocError:
            continue
        c2 = creaite_doc.clean(c1)
        ctx.reset()
        d2 = dict(d, audience="client")
        try:
            s1 = report_doc.save_draft(d2)
            b1 = masked_block(ROOT / DRAFT) if s1.get("ok") else None
            s2 = report_doc.save_draft(creaite_doc.read(ROOT / DRAFT)) if s1.get("ok") else {}
            b2 = masked_block(ROOT / DRAFT) if s2.get("ok") else None
        except (report_doc.ReportError, creaite_doc.DocError):
            b1 = b2 = None               # refused: nothing saved, nothing to compare
        if c1 != c2 or not derived_ok(c1) or b1 != b2:
            fails.append({"case": i, "clean_fixed": c1 == c2, "derived": derived_ok(c1), "save_fixed": b1 == b2})
    return {}, fails


UNDERIVED = ("project_name", "client", "title", "header_data", "stored_logos", "meta_extra", "sources_extra", "layout_extra",
             "saved_at", "version", "based_on")
POOL = ["", None, [], {}, "x" * 5000, "SECRETFIELD ZEBRAPAY"]


def set_underived(d, field, v):
    h = next(s for s in d["sections"] if s.get("type") == "header").setdefault("data", {})
    if field in ("project_name", "client", "title", "saved_at", "version", "based_on"):
        d[field] = v
    elif field == "header_data":
        h[random.Random(str(v)).choice(("label", "client", "title", "x"))] = v
    elif field == "stored_logos":
        h["logos"] = [{"kind": "client", "path": p} for p in PATHS[:3]] if v else v
    else:
        d.setdefault({"meta_extra": "meta", "sources_extra": "sources", "layout_extra": "layout"}[field],
                     [] if field == "sources_extra" else {})
        if field == "sources_extra":
            d["sources"] = list(d["sources"]) + [{"ref": "x", "label": v}]
        else:
            d[field.split("_")[0]]["zz_extra"] = v


def p4(ctx, seed, n):
    """P4 underived fields change nothing: changing only one stored, underived field (project_name, client, title, header data,
    stored logos, meta/sources/layout extras, saved_at, version, based_on) never changes a byte of the HTML export (O2); based_on
    may only make the export refuse (it must name the approved internal week)."""
    ctx.reset()
    first = export("html")
    want = strip_dates(paths.resolve(first["path"]).read_bytes())
    paths.resolve(first["path"]).unlink()
    fails, r = [], random.Random(seed)
    for i in range(n):
        field, v = r.choice(UNDERIVED), r.choice(POOL + [payload(r)])
        d = copy.deepcopy(ctx.base)
        set_underived(d, field, v)
        ctx.reset()
        write_block(d)
        e = export("html")
        if not e.get("ok"):
            if field != "based_on":
                fails.append({"case": i, "field": field, "refused": e.get("message")})
            continue
        got = strip_dates(paths.resolve(e["path"]).read_bytes())
        paths.resolve(e["path"]).unlink()
        if got != want:
            fails.append({"case": i, "field": field, "value": str(v)[:40]})
    return {}, fails


def walk(x, path=()):
    yield path
    if isinstance(x, dict):
        for k, v in x.items():
            yield from walk(v, path + (k,))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from walk(v, path + (i,))


def p5(ctx, seed, n):
    """P5 every field path: each field path of the clean draft (walked from a sample, not from the cases we know), set to a hostile
    string, is re-derived, dropped or gated: no output holds a needle. (The renderer-access spy of the list is not built: the
    allow-list is enforced by client_shape before any renderer reads, see P7 and P20.)"""
    fails, r = [], random.Random(seed)
    every = [p for p in walk(ctx.base) if p]
    for i, path in enumerate(every):
        d = copy.deepcopy(ctx.base)
        t = d
        try:
            for p in path[:-1]:
                t = t[p]
            t[path[-1]] = payload(r, f_plain if i % 2 else None)
        except (KeyError, IndexError, TypeError):
            continue
        ctx.reset()
        try:
            write_block(d)
        except (TypeError, ValueError):
            continue
        blobs, _m, _r, left = surfaces(["html"] + (["docx"] if i % 5 == 0 else []))
        hit = leaks(blobs)
        if hit or left:
            fails.append({"path": "/".join(map(str, path)), "leaks": hit, "left": left})
    return {"paths": len(every)}, fails


def p6(ctx, seed, n):
    """P6 another project or week: a draft whose project or date names another project or week than the route (or another week's
    content under this week's name) is refused by approve and export, and nothing is written (the vault tree is unchanged)."""
    fails, r = [], random.Random(seed)
    other = ROOT / "system/staging/drafts" / STEM.replace(WEEK, OTHER_WEEK).__add__(".html")
    for i in range(n):
        ctx.reset()
        d = copy.deepcopy(ctx.base)
        week = WEEK
        how = r.choice(("project", "date", "renamed"))
        if how == "project":
            m_proj(d, r)
        elif how == "date":
            m_date(d, r)
        if how == "renamed":
            other.write_text(ctx.clean_text, encoding="utf-8")
            week = OTHER_WEEK
        else:
            write_block(d)
        before = tree()
        a = route(report_server.approve_route, {"kind": "client", "code": CODE, "week_ending": week, "force": True})
        e = route(report_server.export_route, {"kind": "client", "code": CODE, "week_ending": week, "fmt": "html", "on_clash": "number"})
        if a.get("ok") or e.get("ok") or tree() != before:
            fails.append({"case": i, "how": how, "approve": a.get("ok"), "export": e.get("ok"), "tree_same": tree() == before})
        other.unlink(missing_ok=True)
    return {}, fails


def keys_ok(block):
    """Whether a filed data block's keys are a subset of the allow-list at every level (creaite_doc.client_shape leaves it as is)."""
    return REAL_SHAPE(block) == block


def stage_content():
    """What Approve files for the draft now: report_doc.stage_client's proposal's write (the proposal itself is removed), or None
    when Approve refuses."""
    try:
        prop = report_doc.stage_client(DRAFT, force=True, code=CODE, fri=WEEK)
    except (report_doc.ReportError, creaite_doc.DocError, ValueError, TypeError, KeyError, AttributeError):
        return None
    try:
        data = json.loads(Path(prop).read_text(encoding="utf-8"))
        return next(o["content"] for o in data["report"]["file_ops"] if o["op"] == "write")
    finally:
        Path(prop).unlink(missing_ok=True)


def p7(ctx, seed, n):
    """P7 unknown keys: a key outside the schema at any depth (top, section, row, cell, data, item, layout, meta, source), holding
    hidden words, is in no output, and the filed data block's keys are a subset of the allow-list."""
    fails, r = [], random.Random(seed)
    for i in range(n):
        d = copy.deepcopy(ctx.base)
        for _ in range(r.randint(1, 3)):
            m_unknown(d, r)
        if r.random() < .3:
            s = r.choice(d["sections"])
            s[r.choice(("ref", "milestones", "timeline"))] = r.choice((payload(r), [payload(r)]))
        ctx.reset()
        (save(copy.deepcopy(d)) if r.random() < .3 else write_block(d))
        blobs, _m, _r, left = surfaces(["html"] + (["docx"] if i % 5 == 0 else []))
        filed = stage_content()
        ok_keys = True
        if filed is not None:
            blobs["filed (Approve)"] = filed
            ok_keys = keys_ok(json.loads(creaite_doc.BLOCK.search(filed).group(1)))
        hit = leaks(blobs)
        if hit or left or not ok_keys:
            fails.append({"case": i, "leaks": hit, "left": left, "keys_ok": ok_keys})
    return {}, fails


P8_KINDS = ["weekly", "client", "minutes", "Client", " client", "client​", ["client"], {}, 1, "clent", None, "__missing__"]
P8_AUD = ["internal", "client", "distributed", "weekly", "Client", None, "__missing__", ["client"]]


def set_ka(d, kind, aud):
    for k, v in (("kind", kind), ("audience", aud)):
        if v == "__missing__":
            d.pop(k, None)
        else:
            d[k] = v
    return d


def weekly_text():
    """The weekly report the weekly route exports (its draft, else the filed one) and its text."""
    for f in (DRAFTS / "2026-10-09 Weekly report - Example Programme.html", REPORTS / "2026-10-09 Weekly report - Example Programme.html"):
        if f.is_file():
            return f, f.read_text(encoding="utf-8")
    return None, None


def p8_client(ctx, kind, aud, src):
    """P8's client route: (outcome, problem or None)."""
    d = set_ka(copy.deepcopy(ctx.base), kind, aud)
    if src == "request":
        s = save(d)
        if s.get("ok") and kind == "client" and aud != "client":
            return "saved", "the save route accepted a client report whose audience isn't client"   # (another kind saves as that kind)
    else:
        write_block(d)
    e = export("html")
    if not e.get("ok"):
        return "refused", ("a client report on disk was refused (its audience is forced to client)" if src == "file" and kind == "client"
                           else None)
    f = paths.resolve(e["path"])
    text = f.read_text(encoding="utf-8")
    f.unlink()
    if src == "file" and kind != "client":
        return "accepted", "a stored kind that isn't client was exported on the client route"
    bad = leaks({"html": text})
    return "accepted", (f"needles {bad}" if bad else None)


def p8_weekly(kind, aud):
    """P8's weekly route: (outcome, problem or None); a weekly report is always labelled Internal."""
    f, text = weekly_text()
    if text is None:
        return "skipped", None
    m = creaite_doc.BLOCK.search(text)
    d = set_ka(json.loads(m.group(1)), kind, aud)
    try:
        f.write_text(text[:m.start(1)] + creaite_doc.data_json(d) + text[m.end(1):], encoding="utf-8")
        e = route(report_server.export_route, {"kind": "weekly", "code": CODE, "week_ending": WEEK, "fmt": "html", "on_clash": "number"})
    finally:
        f.write_text(text, encoding="utf-8")
    if not e.get("ok"):
        return "refused", None
    out = paths.resolve(e["path"]).read_text(encoding="utf-8")
    paths.resolve(e["path"]).unlink()
    if kind != "weekly":
        return "accepted", "a stored kind that isn't weekly was exported on the weekly route"
    label = re.search(r'</h1><div class="sub">.*?</div></div><div class="sub">([^<]*)</div>', out)
    return "accepted", (None if label and label.group(1) == "Internal" else f"a weekly report labelled {label and label.group(1)!r}")


MINUTES_NAMED = f"system/staging/drafts/{WEEK} Steering minutes - Example Programme.html"


def p8_minutes(ctx, kind, aud, src="file"):
    """P8's minutes route on a client report (any kind and audience): always refused. Source "file": the client report's own draft
    (its file name is a report's); "renamed": the same file copied to a minutes name in drafts (no report name, no Reports folder),
    so only the report's other signs (its data says client, its period or logos: creaite_doc.report_signs) can refuse it."""
    write_block(set_ka(copy.deepcopy(ctx.base), kind, aud))
    path = DRAFT
    if src == "renamed":
        (ROOT / MINUTES_NAMED).write_text((ROOT / DRAFT).read_text(encoding="utf-8"), encoding="utf-8")
        path = MINUTES_NAMED
    try:
        r = minutes_record.export(path, "html", file_beside=False)
    except minutes_record.RecordError:
        return "refused", None
    finally:
        (ROOT / MINUTES_NAMED).unlink(missing_ok=True)
    if r.get("ok"):
        paths.resolve(r["path"]).unlink(missing_ok=True)
        return "accepted", "the minutes route exported a client report"
    return "refused", None


def p8_cell(ctx, kind, aud, rt, src):
    """(outcome, problem or None) of one cell of P8's table."""
    ctx.reset()
    if rt == "client":
        return p8_client(ctx, kind, aud, src)
    return p8_weekly(kind, aud) if rt == "weekly" else p8_minutes(ctx, kind, aud, src)


def p8(ctx, seed, n):
    """P8 kind x audience x route x source: a stored kind other than the route's is refused; weekly is always Internal (never
    labelled Client); a client report is forced to audience client and gated; the minutes route refuses a client report by any
    sign, also under a minutes file name outside Reports (source "renamed"), where only the report's data gives it away. Smoke: the
    whole table once (it is fast); full: the table, then n random cells. (The minutes route's request source is the live server's
    minutes save route, guarded: only the file sources are run for it.)"""
    table = [(k, a, rt, src) for k in P8_KINDS for a in P8_AUD for rt in ("client", "weekly", "minutes")
             for src in {"client": ("file", "request"), "minutes": ("file", "renamed")}.get(rt, ("file",))]
    r = random.Random(seed)
    picked = table + ([r.choice(table) for _ in range(n)] if ctx.full else [])
    fails, stats = [], {}
    for k, a, rt, src in picked:
        out, problem = p8_cell(ctx, k, a, rt, src)
        stats[out] = stats.get(out, 0) + 1
        if problem:
            fails.append({"kind": repr(k), "audience": repr(a), "route": rt, "source": src, "problem": problem})
    return stats, fails


RESERVED = re.compile(r"^(con|prn|aux|nul|com[0-9¹²³]|lpt[0-9¹²³]|conin\$|conout\$)(\..*)?$", re.I)


def name_problem(name):
    """Why a saved file name breaks P9's rules, or None."""
    stem = name.rsplit(".", 1)[0]
    if RESERVED.match(stem) or RESERVED.match(name) or re.search(r'[<>:"|?*\\/\x00-\x1f]', name) or name.startswith("."):
        return "a reserved or forbidden name"
    if stem != stem.rstrip(". ") or len(name) > 150:
        return "a trailing dot or space, or too long"
    f = fold(name)
    if "weeklyreport" in f or ("clientreport" in f and not name.startswith(STEM)):
        return "it names another report's filing"
    return None


def plant_link(r, name, clash, outside):
    """Sometimes a symbolic link at the export's target, to a file outside the vault; the link or None."""
    if r.random() >= .2:
        return None
    outside.write_text("keep")
    link = REPORTS / (STEM + ".html" if clash != "rename" else name + ("" if name.endswith(".html") else ".html"))
    with contextlib.suppress(OSError, ValueError):
        link.symlink_to(outside)
    return link if link.is_symlink() else None


def reports_files():
    return {p.name: hashlib.sha1(p.read_bytes()).hexdigest() for p in REPORTS.iterdir() if p.is_file() and not p.is_symlink()}


def p9_problem(e, name, before, after, outside):
    """Why one P9 case breaks the property, or None."""
    changed = [k for k in after if before.get(k) != after[k]]
    if outside.is_file() and outside.read_text() != "keep":
        return "wrote through a symbolic link"
    if not e.get("ok"):
        return "a refusal changed files" if changed else None
    p = paths.resolve(e["path"])
    if p.parent.resolve() != REPORTS.resolve():
        return "not in Reports"
    if name_problem(p.name):
        return name_problem(p.name)
    if len(changed) != 1:
        return f"{len(changed)} files changed"
    return None if p.name not in before or p.name.startswith(STEM) else "replaced another file"


def p9(ctx, seed, n):
    """P9 file names: whatever name is typed and whatever is chosen for a taken name (number, rename, overwrite), the saved file is
    one name inside the project's Reports folder, never reserved or forbidden, never another report's filing name, and only this
    report's own file is ever replaced; a symbolic link planted at the target is never written through."""
    import tempfile
    fails, r = [], random.Random(seed)
    outside = Path(tempfile.mkdtemp()) / "outside.txt"
    outside.write_text("keep")
    for i in range(n):
        ctx.reset()
        name = r.choice(NAMES)
        name = r.choice([name, name.upper(), name.replace(" ", "\u00a0"), name + " (2)"])
        clash = r.choice(["number", "rename", "overwrite", None])
        link = plant_link(r, name, clash, outside)
        before = reports_files()
        e = route(report_server.export_route, {"kind": "client", "code": CODE, "week_ending": WEEK, "fmt": "html", "on_clash": clash,
                                               "new_name": name})
        problem = p9_problem(e, name, before, reports_files(), outside)
        if problem:
            fails.append({"case": i, "name": name, "on_clash": clash, "problem": problem, "saved": e.get("name")})
        if link is not None:
            link.unlink()
    return {}, fails


def words(t):
    return set(re.findall(r"[^\W_]+", fold_keep(t)))


def fold_keep(t):
    return confusables.skeleton(undo_escapes(t)).lower()


def p10(ctx, seed, n):
    """P10 a posted page: whatever page is posted (words in text, attributes, style, comments, SVG, url(), a foreign section, any
    version), every word of the saved client HTML (tags and styles dropped) is a word of the server's render of the saved report,
    and no needle is in it."""
    import launch
    ctx.reset()
    allowed = words(client_output.html_text(creaite_doc.render(creaite_doc.read_report(DRAFT, "client"), editing=False)))
    fails, r = [], random.Random(seed)
    for i in range(n):
        fmt = "pdf" if i % 20 == 0 and launch.find_chrome() else "html"
        v = int(creaite_doc.read(ROOT / DRAFT).get("version") or 0)
        e = export(fmt, a_page(r, r.choice([v, v, v, 0, str(v), 99])))
        if not e.get("ok"):
            continue
        p = paths.resolve(e["path"])
        text = client_output.html_text(p.read_text(encoding="utf-8")) if fmt == "html" else client_output.pdf_text(p)
        extra = words(text) - allowed
        hit = leaks(blobs_of(p))
        p.unlink()
        if (extra and fmt == "html") or hit:
            fails.append({"case": i, "fmt": fmt, "extra_words": sorted(extra)[:8], "leaks": hit})
    return {}, fails


def p11(ctx, seed, n):
    """P11 a writer racing the export: while a thread replaces the draft file (os.replace) with a clean or a dirty version every
    0.1, 0.5 or 5 ms, each HTML export (and Approve, then undone) equals the clean render exactly or is refused: never the dirty
    one, never a mix."""
    import time
    ctx.reset()
    dirty = copy.deepcopy(ctx.base)
    next(s for s in dirty["sections"] if s["id"] == "free_a")["text"] = f"{X['owner']} owns {H['id']} {H['title']}. Confidential."
    write_block(dirty)
    dirty_text = (ROOT / DRAFT).read_text(encoding="utf-8")
    ctx.reset()
    want = strip_dates(creaite_doc.render(creaite_doc.read_report(DRAFT, "client"), editing=False))
    fails, stats, r = [], {"made": 0, "refused": 0, "approved": 0}, random.Random(seed)
    for i in range(n):
        period = r.choice([0.0001, 0.0005, 0.005])
        stop = threading.Event()

        def writer(stop=stop, period=period):
            k = 0
            while not stop.is_set():
                tmp = DRAFTS / f".props-swap-{k % 2}"
                tmp.write_text(dirty_text if k % 2 else ctx.clean_text, encoding="utf-8")
                os.replace(tmp, ROOT / DRAFT)
                k += 1
                time.sleep(period)
        t = threading.Thread(target=writer, daemon=True)
        t.start()
        try:
            if i % 10 == 9:
                a = route(report_server.approve_route, {"kind": "client", "code": CODE, "week_ending": WEEK, "force": True})
                got = None
                if a.get("ok"):
                    stats["approved"] += 1
                    got = strip_dates(creaite_doc.BLOCK.sub("", (ROOT / a["path"]).read_text(encoding="utf-8")).replace("\n\n", "\n"))
            else:
                e = export("html")
                got = None
                if e.get("ok"):
                    stats["made"] += 1
                    got = strip_dates(paths.resolve(e["path"]).read_text(encoding="utf-8"))
                    paths.resolve(e["path"]).unlink()
                else:
                    stats["refused"] += 1
        finally:
            stop.set()
            t.join()
        if i % 10 == 9 and got is not None:
            filed = (ROOT / a["path"]).read_text(encoding="utf-8")
            if leaks({"filed": filed}):
                fails.append({"case": i, "approve": "filed the dirty version"})
            run_script("tracker.py", "undo")
        elif got is not None and got != want:
            fails.append({"case": i, "period": period, "dirty": bool(leaks({"x": got}))})
        ctx.reset()
    return stats, fails


def p13(ctx, seed, n):
    """P13 pictures: whatever picture reference a text holds (a path, `..`, a URL, an absolute path, the project's internal images
    folder), only this report's own pictures are drawn: no planted internal or outside picture is in a Word or HTML export.
    (A picture uploaded for the internal report into the shared `_images/` store is the known gap C: see P13 shared.)"""
    fails, r = [], random.Random(seed)
    for i in range(n):
        d = copy.deepcopy(ctx.base)
        for _ in range(r.randint(1, 3)):
            m_pic(d, r)
        ctx.reset()
        write_block(d)
        for fmt in ("docx", "html"):
            e = export(fmt)
            if e.get("ok"):
                p = paths.resolve(e["path"])
                pics = [data for _n, data in client_output.docx_pictures(p)] if fmt == "docx" else \
                    [x for _n, x in client_output.html_pictures(p.read_text(encoding="utf-8"))[0]]
                p.unlink()
                if any(x in ctx.bad_bytes for x in pics):
                    fails.append({"case": i, "fmt": fmt})
    return {}, fails


def p13_shared(ctx, seed, n):
    """P13 shared store (known gap C, proposal 4 of dev/proposals/audience-bypass): a picture in the project's `_images/` store that
    was uploaded for the internal report is never drawn into a client report, even when the client text names it (step 2: a client
    report reads only `_images/client-<name>` pictures, as its snapshot's picture table records them)."""
    folder = creaite_doc.images_dir({"project": CODE}) / "_images"
    folder.mkdir(parents=True, exist_ok=True)
    pic = folder / "internal-raid.png"
    pic.write_bytes((ROOT / ctx.bad_pics[1]).read_bytes())
    fails = []
    try:
        for i in range(n):
            d = copy.deepcopy(ctx.base)
            d["sections"].append(sec("free_s", "freetext", "Pic", text="![raid](_images/internal-raid.png)", audience="client"))
            ctx.reset()
            write_block(d)
            e = export("docx")
            if e.get("ok"):
                p = paths.resolve(e["path"])
                if any(x in ctx.bad_bytes for _n, x in client_output.docx_pictures(p)):
                    fails.append({"case": i})
                p.unlink()
    finally:
        pic.unlink(missing_ok=True)
    return {}, fails


def p14(ctx, seed, n):
    """P14 logos: whatever the header's stored logos say (a path from PATHS, another project's logo, an internal or outside
    picture; kinds firm, client, partner:zzz, other), the Word export holds only the project's own logos and the template's and
    creaite's own pictures, and no picture's name or description names a path."""
    fails, r = [], random.Random(seed)
    for i in range(n):
        d = copy.deepcopy(ctx.base)
        h = next(s for s in d["sections"] if s.get("type") == "header").setdefault("data", {})
        h["logos"] = [{"kind": r.choice(["firm", "client", "partner:zzz", "other"]), "path": r.choice(PATHS + ctx.bad_pics)}
                      for _ in range(r.randint(1, 4))]
        if r.random() < .3:
            d["layout"]["logos"] = r.choice([["firm"], ["firm", "client", "partner:zzz"], [], "x", None])
        ctx.reset()
        write_block(d)
        e = export("docx")
        if not e.get("ok"):
            continue
        p = paths.resolve(e["path"])
        pics = [data for _n, data in client_output.docx_pictures(p)]
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        p.unlink()
        names = re.findall(r'(?:name|descr)="([^"]*)"', xml)
        if any(x in ctx.bad_bytes for x in pics) or any(("/" in nm or "\\" in nm or ".png" in nm) for nm in names):
            fails.append({"case": i, "logos": h["logos"]})
    return {}, fails


SVGS = ["<svg xmlns='http://www.w3.org/2000/svg' width='80' height='30'><text>SECRETWORD</text></svg>",
        "<svg xmlns='http://www.w3.org/2000/svg' width='80' height='30'><style>@import url(https://e.invalid/a.css)</style></svg>",
        "<?xml version='1.0'?><!DOCTYPE svg [<!ENTITY s 'SECRETWORD'>]><svg xmlns='http://www.w3.org/2000/svg'><text>&s;</text></svg>",
        "<svg xmlns='http://www.w3.org/2000/svg' width='80' height='30'><foreignObject><div>SECRETWORD</div></foreignObject></svg>",
        "<svg xmlns='http://www.w3.org/2000/svg' width='80' height='30'><rect width='80' height='30' aria-label='SECRETWORD' "
        "id='SECRETWORD'/></svg>"]


def png_with_text(word):
    import struct
    import zlib
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_dashboard import png
    raw = png(40, 16, (5, 6, 7))
    chunk = struct.pack(">I", len(word) + 8) + b"tEXt" + b"Comment\0" + word + struct.pack(">I", zlib.crc32(b"tEXt" + b"Comment\0" + word))
    i = raw.index(b"IDAT") - 4
    return raw[:i] + chunk + raw[i:]


def p15(ctx, seed, n):
    """P15 uploaded logos: an SVG or PNG logo uploaded through the logo route (hidden text, entities, foreignObject, @import, an
    aria-label, a PNG text chunk) reaches a Word export only rebuilt: no SECRETWORD in any part's bytes, no outside reference."""
    import base64
    fails, r = [], random.Random(seed)
    uploads = [("svg", s.encode()) for s in SVGS] + [("png", png_with_text(b"SECRETWORD"))]
    for i in range(n):
        ext, raw = uploads[i % len(uploads)] if i < len(uploads) else r.choice(uploads)
        ctx.reset()
        s = route(report_server.logo_save_route, {"code": CODE, "kind": "client", "ext": ext,
                                                   "original": base64.b64encode(raw).decode()})
        e = export("docx") if s.get("ok") else {}
        if e.get("ok"):
            p = paths.resolve(e["path"])
            with zipfile.ZipFile(p) as z:
                bad = [nm for nm in z.namelist() if b"SECRETWORD" in z.read(nm) or b"e.invalid" in z.read(nm)]
            p.unlink()
            if bad:
                fails.append({"case": i, "ext": ext, "parts": bad})
        route(report_server.logo_remove_route, {"code": CODE, "kind": "client"})
    return {}, fails


GATE_FIELDS = ("summary.text", "free_a.text", "summary.heading", "row.cell", "glance.note", "current_state.pane", "health.text",
               "item.title", "this_week.tag", "free_a.heading", "header.label", "decisions.cell")


def _put_cell(d, field, value):
    s, row = vis_row(d) if field == "row.cell" else (next((x for x in d["sections"] if x["id"] == "decisions"), None), None)
    row = row or ((s or {}).get("rows") or [None])[0]
    if row is None:
        return False
    row.setdefault("cells", {})[next(iter(row.get("cells") or {"x": 1}))] = value
    return True


def _put_item(d, field, value):
    if not d.get("items"):
        return False
    next(iter(d["items"].values()))["title"] = value
    return True


def _put_in(s, what, value, d):
    if what == "note":
        (s.get("figures") or [{}])[0]["note"] = value
    elif what == "pane":
        s.setdefault("panes", [{}])[0]["text"] = value
    elif what == "tag":
        s["tags"] = [{"ref": vis_row(d)[1]["ref"] if vis_row(d)[1] else "ABC-A-002", "text": value}]
    elif what == "label":
        s.setdefault("data", {})["label"] = value
    else:
        s[what] = value
    return True


def put(d, field, value):
    """The value in one of the fields the gate reads (P16's twelve)."""
    sid, _, what = field.partition(".")
    if sid in ("row", "decisions"):
        return _put_cell(d, field, value)
    if sid == "item":
        return _put_item(d, field, value)
    s = next((x for x in d["sections"] if x["id"] == sid or x.get("type") == sid), None)
    return False if s is None else _put_in(s, what, value, d)


def p16(ctx, seed, n, forms=None):
    """P16 every text form: for each encoder and the twelve gate-read fields, the gate refuses the encoded hidden words exactly when
    it refuses the plain ones (client_leak.findings on the cleaned document). Ten encoders here; the JSON-escaped form is P16json,
    which needs the guarded client_leak.py diff (dev/proposals/client-output-step1/client_leak.diff); until it is applied the
    output check (client_output.unescaped) keeps that form out of every file, as P1 shows."""
    forms = forms or [f for f in FORMS if f is not f_json]
    fails, r = [], random.Random(seed)
    con = client_leak.connect()
    for i in range(n):
        s = " ".join(r.sample(PIECES, r.randint(1, 3)))
        form, field = forms[i % len(forms)], r.choice(GATE_FIELDS)
        plain_doc, enc_doc = copy.deepcopy(ctx.base), copy.deepcopy(ctx.base)
        if not put(plain_doc, field, s):
            continue
        put(enc_doc, field, form(s, r))
        a = bool(client_leak.findings(creaite_doc.force_client_audience(plain_doc), con))
        b = bool(client_leak.findings(creaite_doc.force_client_audience(enc_doc), con))
        if a != b:
            fails.append({"case": i, "form": form.__name__, "field": field, "plain_refused": a, "encoded_refused": b})
    return {}, fails


ID_IN = re.compile(r"\b([A-Z][A-Z0-9]{2,6})-(?:([A-Z])-)?(\d{3})\b")


def f_loose_id(s, r):
    """v2.5.3 (#259, P16): every item ID written loosely: letters and digits spaced ("A B C - A - 0 0 1"), more zeros or none."""
    def one(m):
        code, letter, num = m.group(1), m.group(2), m.group(3)
        mid = f"{letter}-" if letter else ""
        return r.choice([" ".join(code) + " - " + (f"{letter} - " if letter else "") + " ".join(num), f"{code}-{mid}0{num}",
                         f"{code}-{mid}{int(num)}", f"{code.lower()}.{mid.replace('-', '.')}{num}",
                         # #259 round 3 (Cap's HIGH): a padded ID with a fraction, date or time mark after it is still the ID
                         f"{code}-{mid}0{num}/1", " ".join(code) + " - " + (f"{letter} - " if letter else "") + f"{num}.5",
                         f"{code}-{mid}{num}/2026", f"{code}-{mid}{num}:10"])
    return ID_IN.sub(one, s)


def f_hyphen(s, r):
    """v2.5.3 (#259, P16): a wording with hyphens, dots or underscores for its spaces, or spaces for its hyphens."""
    return r.choice([s.replace(" ", "-"), s.replace(" ", "."), s.replace(" ", "_"), s.replace("-", " ").replace(" ", ". ")])


def p16_out(ctx, seed, n):
    """P16 at the output check (v2.5.3, #259): for each encoder, the loose ID forms and a wording's separators changed, the check
    every client output passes (client_output.text_findings) refuses the encoded hidden words exactly when it refuses the plain.
    The forms are those that stand in an output's text as a reader sees it; %- and entity-encoding, Markdown and JSON escapes are
    the gate's to read in the document (P16, P16json), and an export draws them decoded."""
    forms = [f_plain, f_zw, f_full, f_cyr, f_case, f_space, f_loose_id, f_hyphen]
    fails, r = [], random.Random(seed)
    con = client_leak.connect()
    doc = {"project": CODE, "sections": []}
    for i in range(n):
        form = forms[i % len(forms)]
        if form is f_loose_id:                   # one ID alone: no other piece may give the refusal away
            s = r.choice([H["id"], X["id"]])
        elif form is f_hyphen:                   # one wording alone, likewise
            s = r.choice([H["title"], X["title"]])
        else:
            s = " ".join(r.sample(PIECES, r.randint(1, 3)))
        enc = form(s, r)
        a = bool(client_output.text_findings(doc, f"Plain words: {s}.", con))
        b = bool(client_output.text_findings(doc, f"Plain words: {enc}.", con))
        if a != b:
            fails.append({"case": i, "form": form.__name__, "plain": s[:80], "encoded": enc[:80], "plain_refused": a,
                          "encoded_refused": b})
    return {}, fails


STORED = ("item_title", "item_owner", "item_key", "tag_text", "row_source", "cell_key", "column", "heading", "based_on")


def p18_stored(d, r, what):
    """v2.5.3 (#259, K3): words no gate knows (SECRETFIELD) in one stored field no output draws, of a VISIBLE item."""
    t, row = vis_row(d)
    ref = row["ref"]
    it = d.setdefault("items", {}).setdefault(ref, {"id": ref})
    w = "SECRETFIELD " + r.choice(["ZEBRAPAY", "words", "plain"])
    if what in ("item_title", "item_owner"):
        it[what.split("_")[1]] = w
    elif what == "item_key":
        it["note"] = w
    elif what == "tag_text":
        next(s for s in d["sections"] if s["id"] == "this_week")["tags"] = [{"ref": ref, "text": w}]
    elif what == "row_source":
        row["source"] = w
    elif what == "cell_key":
        row.setdefault("cells", {})["zz"] = w
    elif what == "column":
        t["columns"] = list(t.get("columns") or []) + [{"key": "zz", "label": w}]
        row.setdefault("cells", {})["zz"] = "x"
    elif what == "heading":
        d.setdefault("layout", {}).setdefault("headings", {})["summary"] = w
    else:
        d["based_on"] = {"path": f"{w}/x.html", "version": 1}
    return ref


def p18_facts(ctx, seed, n):
    """P18's kept items (v2.5.3, #259, K3 / I19): plain words in a stored field no output draws (an item's values or unknown keys,
    a tag's text, a row's source or an unknown cell, a column, the layout's headings, based_on), on disk or sent to Save, reach
    no output; and a kept item in the filed data block equals the tracker's client-safe facts for it."""
    fails, r = [], random.Random(seed)
    by_id = report_doc.client_items(CODE, WEEK)
    for i in range(n):
        d = copy.deepcopy(ctx.base)
        what = STORED[i % len(STORED)]
        ref = p18_stored(d, r, what)
        ctx.reset()
        (save(copy.deepcopy(d)) if i % 3 == 0 else write_block(d))
        blobs, _m, _r, _l = surfaces(["html"] + (["docx"] if i % 4 == 0 else []))
        hit = leaks(blobs, ["SECRETFIELD", "ZEBRAPAY"])
        filed = blobs.get("filed")
        items = json.loads(creaite_doc.BLOCK.search(filed).group(1)).get("items") or {} if filed else {}
        same = all(v == by_id.get(k) for k, v in items.items())
        if hit or not same:
            fails.append({"case": i, "what": what, "ref": ref, "leaks": hit, "items_are_facts": same})
    return {}, fails


SECTION_TYPES = ("freetext", "text", "table", "panes", "health", "figures", "timeline", "header", "weird")


def p17_section(r):
    """One section that P17 generates: a type, an audience (or none), maybe an `internal` flag or hidden."""
    s = sec("free_b", r.choice(SECTION_TYPES), "Vendor notes", text="INTWALRUS internal words.")
    aud = r.choice(["internal", None, "__missing__", "Internal", " internal", "weekly", "Client", " client", ["client"], 1, "distributed",
                    "client"])
    if aud != "__missing__":
        s["audience"] = aud
    if r.random() < .3:
        s["internal"] = True
    if r.random() < .2:
        s["hidden"] = True
    return s


def p17_hidden(s):
    """P17's model: whether the section's words may show nowhere."""
    if s.get("hidden") or s.get("internal"):
        return True
    return (s["type"] == "freetext" or "audience" in s) and s.get("audience") != "client"


def p17(ctx, seed, n):
    """P17 internal sections: a section of any type and position that is a text section whose audience isn't exactly "client"
    (internal, missing, null, any other spelling or type), any section that carries an audience other than exactly "client", or
    one with an `internal` flag (or hidden), shows none of its words (INTWALRUS) in a client output. (A section of creaite's own
    client types with no audience key at all is one of the report's own sections and shows.)"""
    fails, r = [], random.Random(seed)
    for i in range(n):
        d = copy.deepcopy(ctx.base)
        d["sections"] = [s for s in d["sections"] if s["id"] != "free_b"]
        s = p17_section(r)
        d["sections"].insert(r.randrange(len(d["sections"]) + 1), s)
        ctx.reset()
        write_block(d)
        blobs, _m, _r, _l = surfaces(["html"] + (["docx"] if i % 3 == 0 else []))
        if p17_hidden(s) and leaks(blobs, ["INTWALRUS"]):
            fails.append({"case": i, "type": s["type"], "audience": repr(s.get("audience", "-")), "internal": s.get("internal")})
    return {}, fails


ID_FORMS = (lambda x: x, str.lower, lambda x: x.replace("-", "‑"), lambda x: x.replace("A", "А"),
            lambda x: "".join(chr(ord(c) + 0xFEE0) if "!" <= c <= "~" else c for c in x))


def p18_edit(d, r):
    """One hidden-row, item, tag or milestone edit naming H or X in some ID form; (what, ref)."""
    t, row = vis_row(d)
    it = r.choice([H, X])
    ref = r.choice(ID_FORMS)(it["id"])
    what = r.choice(("hidden_row", "item", "tag", "milestone", "hidden_vis_row"))
    if what == "hidden_row" and t:
        t["rows"].append({"ref": ref, "shown": False, "cells": {"x": it["title"] + " INTWALRUS"}})
    elif what == "hidden_vis_row" and row:
        row.update(shown=False, cells={k: "INTWALRUS" for k in (row.get("cells") or {"x": 1})})
    elif what == "item":
        d.setdefault("items", {})[ref] = {"id": ref, "title": it["title"], "owner": it["owner"]}
    elif what == "tag":
        next(s for s in d["sections"] if s["id"] == "this_week")["tags"] = [{"ref": ref, "text": it["title"]}]
    else:
        next(s for s in d["sections"] if s.get("type") == "timeline").setdefault("data", {})["milestones"] = [ref]
    return what, ref


def stubs_ok(filed):
    block = json.loads(creaite_doc.BLOCK.search(filed).group(1))
    return all(set(x) <= {"ref", "shown"} for s in block["sections"] for x in s.get("rows") or [] if x.get("shown") is False)


def p18(ctx, seed, n):
    """P18 hidden rows, items, tags and milestone lists: a hidden row, item, tag or milestone entry naming the hidden item or another
    project's (in any ID form), or a hidden row carrying internal words, reaches no output; a hidden row is a stub (ref and shown
    only) in the filed data block."""
    fails, r = [], random.Random(seed)
    for i in range(n):
        d = copy.deepcopy(ctx.base)
        what, ref = p18_edit(d, r)
        ctx.reset()
        write_block(d)
        blobs, _m, _r, _l = surfaces(["html"] + (["docx"] if i % 4 == 0 else []))
        filed = blobs.get("filed")
        ok = filed is None or stubs_ok(filed)
        hit = leaks(blobs)
        if hit or not ok:
            fails.append({"case": i, "what": what, "ref": ref, "leaks": hit, "stubs": ok})
    return {}, fails


def p19(ctx, seed, n):
    """P19 the post-render check on its own: with the document gate switched off (client_leak.findings answers nothing, as if a
    field class were missed), a client report holding hidden words in shown places is still never exported or filed: the check of
    the output (and of what Approve files) finds them and the made file is deleted."""
    real = client_leak.findings
    client_leak.findings = lambda doc, con=None: []
    try:
        fails, r = [], random.Random(seed)
        for i in range(n):
            d = copy.deepcopy(ctx.base)
            for _ in range(r.randint(1, 2)):
                put(d, r.choice(GATE_FIELDS), payload(r, r.choice([f_plain, f_cyr, f_zw, f_full, f_case])))
            ctx.reset()
            write_block(d)
            blobs, made, _r, left = surfaces(["html"] + (["docx"] if i % 3 == 0 else []))
            filed = stage_content()
            if filed is not None:
                blobs["filed (Approve)"] = filed
            hit = leaks(blobs)
            if hit or left:
                fails.append({"case": i, "made": made, "leaks": hit, "left": left})
    finally:
        client_leak.findings = real
    return {}, fails


def walk_dicts(x):
    """Every dict in a document."""
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from walk_dicts(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk_dicts(v)


def p20(ctx, seed, n):
    """P20 the filed data block: what Approve files decodes to an object that keeps only the allow-list's keys (client_shape(x) == x),
    holds no raw '<' (a `</script>` or `-->` in a string stays escaped) and reads back to the same object (loads of its dumps)."""
    fails, r = [], random.Random(seed)
    for i in range(n):
        d = copy.deepcopy(ctx.base)
        for _ in range(r.randint(1, 3)):
            m_unknown(d, r)
        for x in walk_dicts(d):                      # the unknown keys' values made harmless: P20 is about the keys, not the words
            for k in [k for k in x if any(k.startswith(u) for u in UNKNOWN_KEYS) and isinstance(x[k], str) and k[-1].isdigit()]:
                x[k] = "zz-unknown"
        put(d, "free_a.text", r.choice(["</script><b>x</b>", "--> <!-- ", "a < b", "Plain words."]))
        ctx.reset()
        write_block(d)
        filed = stage_content()
        if filed is None:
            continue
        m = creaite_doc.BLOCK.search(filed)
        block = json.loads(m.group(1))
        back = creaite_doc.loads(creaite_doc.dumps(creaite_doc.loads(filed)))
        if not keys_ok(block) or "<" in m.group(1) or back != creaite_doc.clean(block):
            fails.append({"case": i, "keys_ok": keys_ok(block), "raw_lt": "<" in m.group(1)})
    return {}, fails


def p21(ctx, seed, n):
    """P21 raw transforms: a draft file's text transformed (a BOM, CRLF, a trailing comma, a duplicate kind, audience or project,
    a second data block, a comment first, 5 MB of padding, raw HTML in the block) is read by one parser for the gate and the render:
    the export is refused, or equals render(that one parse) and that parse passes the gate."""
    fails, r = [], random.Random(seed)
    for i in range(n):
        ctx.reset()
        f = ROOT / DRAFT
        how = RAW[i % len(RAW)] if i < len(RAW) else r.choice(RAW)
        f.write_text(raw_transform(ctx.clean_text, how, r), encoding="utf-8")
        want = expected_html()
        e = export("html")
        if e.get("ok"):
            got = paths.resolve(e["path"]).read_text(encoding="utf-8")
            paths.resolve(e["path"]).unlink()
            gate = client_leak.findings(creaite_doc.read_report(DRAFT, "client")) if want is not None else ["unreadable"]
            if got != want or gate:
                fails.append({"case": i, "raw": how, "same": got == want, "gate": gate[:2]})
    return {}, fails


def p22(ctx, seed, n):
    """P22 read-only routes: draft, check, match-check and pick write nothing (the vault tree is unchanged), and match-check's findings
    are non-empty exactly when the export refuses the same document on its content."""
    fails = []
    for c in cases(seed, n, ctx.base):
        ctx.reset()
        d = copy.deepcopy(c["doc"])
        try:
            write_block(d)
        except (TypeError, ValueError):
            continue
        before = tree()
        route(report_server.draft_route, {"kind": "client", "code": CODE, "week_ending": WEEK})
        route(report_server.check_route, {"doc": d})
        # v2.5.3 (#259, K2): the draft is written on disk here (not by creaite's Save), so the export reads its text sections as
        # the internal report's; Match internal is sent the same document as that file reads (derive_sections, untrusted)
        sent = creaite_doc.derive_sections(copy.deepcopy(d), False) if isinstance(d, dict) else d
        m = route(report_server.match_check_route, {"docs": [sent]})
        route(report_server.pick_route, {"doc": d})
        same = tree() == before
        e = export("html")
        if e.get("ok"):
            paths.resolve(e["path"]).unlink()
        content_refused = not e.get("ok") and bool(e.get("findings"))
        flagged = bool(m.get("ok") and any(m.get("findings") or []))
        readable = m.get("ok") and expected_html() is not None
        if not same or (readable and flagged != content_refused):
            fails.append({"case": c["i"], "mutations": named(c), "tree_same": same, "match_check": flagged, "export_refused": content_refused})
    return {}, fails


def html_export_page():
    """The HTML export of the draft now, dates masked (removed after), or None when refused."""
    e = export("html")
    if not e.get("ok"):
        return None
    page = strip_dates(paths.resolve(e["path"]).read_text(encoding="utf-8"))
    paths.resolve(e["path"]).unlink()
    return page


def draft_bytes():
    return (ROOT / DRAFT).read_bytes() if (ROOT / DRAFT).is_file() else None


def p23_approved(a, page, reports_before, draft_before):
    """P23's checks of an Approve that was made, then Undo; the problem or None."""
    filed = (ROOT / a["path"]).read_text(encoding="utf-8")
    filed_page = strip_dates(creaite_doc.BLOCK.sub("", filed).replace("</main>\n\n</body>", "</main>\n</body>"))
    problem = None
    if page is not None and filed_page != page:
        problem = "the filed page differs from the HTML export"
    if leaks({"filed": filed}):
        problem = f"filed needles {leaks({'filed': filed})}"
    run_script("tracker.py", "undo")
    if listing() != reports_before or draft_bytes() != draft_before:
        problem = problem or "Undo didn't put the Reports folder and the draft back"
    return problem


def p23(ctx, seed, n):
    """P23 Approve: what Approve files is, page for page, the HTML export of the same gated object (O2, the data block aside); a refused
    Approve leaves no filed file and no new staged file holding hidden words; Approve then Undo puts the Reports folder and the draft
    back exactly."""
    fails = []
    for c in cases(seed, n, ctx.base):
        ctx.reset()
        land(c)
        page, draft_before, reports_before = html_export_page(), draft_bytes(), listing()
        staged_before = {p.name for p in (ROOT / "system/staging").glob("*") if p.is_file()}
        a = route(report_server.approve_route, {"kind": "client", "code": CODE, "week_ending": WEEK, "force": True})
        if a.get("ok"):
            problem = p23_approved(a, page, reports_before, draft_before)
        else:
            new = [p for p in (ROOT / "system/staging").glob("*") if p.is_file() and p.name not in staged_before]
            problem = "a refused Approve left a file" if [p for p in new if leaks({p.name: p.read_bytes()})] or \
                listing() != reports_before else None
        if problem:
            fails.append({"case": c["i"], "mutations": named(c), "problem": problem})
    return {}, fails


def p24(ctx, seed, n):
    """P24 repeat: the same export repeated two to five times without a change gives the same bytes (O2) and leaves the draft and the
    filed report as they were."""
    fails, r = [], random.Random(seed)
    for i in range(n):
        ctx.reset()
        fmt = r.choice(["html", "docx"])
        before = (ROOT / DRAFT).read_bytes()
        outs = []
        for _ in range(r.randint(2, 5)):
            e = export(fmt, a_page(r) if r.random() < .3 and fmt == "html" else None)
            if not e.get("ok"):
                outs.append(None)
                continue
            p = paths.resolve(e["path"])
            outs.append(docx_parts(p) if fmt == "docx" else strip_dates(p.read_bytes()))
            p.unlink()
        if len({json.dumps(o, sort_keys=True, default=str) for o in outs}) != 1 or (ROOT / DRAFT).read_bytes() != before:
            fails.append({"case": i, "fmt": fmt, "same": len({json.dumps(o, sort_keys=True, default=str) for o in outs}) == 1})
    return {}, fails


def p26(ctx, seed, n):
    """P26 exports twice (v2.5.3, #259 round 2, HIGH 1): an approved, filed client report edited on disk to hold a text section
    marked "client" (words no gate knows) is held on EVERY export, html and docx, in any order and however many: never only on the
    first, as an export's own rebuilt snapshot never vouches for the file it was built from. Each case's filing is then undone."""
    fails, r = [], random.Random(seed)
    for i in range(n):
        ctx.reset()
        a = route(report_server.approve_route, {"kind": "client", "code": CODE, "week_ending": WEEK, "force": True})
        if not a.get("ok"):
            fails.append({"case": i, "approve": a.get("message")})
            continue
        f = ROOT / a["path"]
        text = f.read_text(encoding="utf-8")
        d = creaite_doc.loads(text)
        sid = r.choice(["free_sneak", "free_a", "notes_x", "zz"])
        d["sections"] = [s for s in d["sections"] if s.get("id") != sid]
        d["sections"].insert(r.randint(0, len(d["sections"])), {
            "id": sid, "type": r.choice(["freetext", "freetext", "text"]), "heading": r.choice(["Notes", "Update", ""]),
            "default_heading": "", "hidden": False, "text": "ZEBRAPAY " + r.choice(["quiet words", "plain", "for the group"]),
            "audience": "client"})
        d.setdefault("layout", {})["order"] = [s["id"] for s in d["sections"]]
        m = creaite_doc.BLOCK.search(text)
        f.write_text(text[:m.start(1)] + creaite_doc.data_json(d) + text[m.end(1):], encoding="utf-8")
        order = [r.choice(["html", "docx"]) for _ in range(r.randint(2, 4))]
        for k, fmt in enumerate(order):
            e = export(fmt)
            if not e.get("ok"):
                continue
            p = paths.resolve(e["path"])
            hit = leaks(blobs_of(p), ["ZEBRAPAY"])
            p.unlink()
            if hit:
                fails.append({"case": i, "order": order, "export": k, "fmt": fmt, "leaks": hit})
        run_script("tracker.py", "undo")
        ctx.reset()
    return {}, fails


PROPERTIES = {"P1": p1, "P2": p2, "P3": p3, "P4": p4, "P5": p5, "P6": p6, "P7": p7, "P8": p8, "P9": p9, "P10": p10, "P11": p11,
              "P13": p13, "P13shared": p13_shared, "P14": p14, "P15": p15, "P16": p16, "P16json": lambda ctx, seed, n: p16(ctx, seed, n, [f_json]), "P17": p17, "P18": p18, "P18facts": p18_facts, "P16out": p16_out, "P19": p19, "P20": p20, "P21": p21, "P22": p22,
              "P23": p23, "P24": p24, "P26twice": p26}


# ── mutants: one guard switched off in this process, for the mutation proofs ─
def _logo_files_stored(self, s):
    """The old Word writer's logos: every stored path that is a file (the guard taken away)."""
    out = []
    for lg in (s.get("data") or {}).get("logos") or []:
        f = paths.resolve(str(lg.get("path") or "")) if isinstance(lg, dict) and lg.get("path") else None
        if f is not None and f.is_file():
            out.append(f)
    return out


def _gate_off():
    client_leak.findings = lambda doc, con=None: []
    _output_off()


def _output_off():
    creaite_doc.client_output_findings = lambda *a, **k: []
    client_output.filed_findings = lambda *a, **k: []


def _reread():
    real = creaite_doc._export_doc
    creaite_doc._export_doc = lambda path, kind, doc=None: real(path, kind, None)


POSTED = {}          # page_used only: the page the client export route was posted, for the export it makes


def _page_used():
    """A client report's posted page used, as before v2.5.1 step 3. That guard is three deep, so all three go: the client export
    route passes the posted page on to the export (step 3 sends none: client_snapshot.client_export has no page), _posted_page
    looks at it (it returns none for a client report) and export_page.build takes it (it refuses a client report, and the forced
    audience says client: the page is checked as an internal report's is, as the weekly route checks one)."""
    real_route, real_export, real_posted = report_server._client_export, creaite_doc.export, creaite_doc._posted_page

    def route_with_page(handler, req, which, fmt):
        POSTED["page"] = req.get("page") if isinstance(req.get("page"), dict) else None
        try:
            return real_route(handler, req, which, fmt)
        finally:
            POSTED.pop("page", None)

    def export_with_page(path, fmt, **k):
        if k.get("page") is None and POSTED.get("page") is not None:
            k["page"] = POSTED["page"]
        return real_export(path, fmt, **k)
    report_server._client_export = route_with_page
    creaite_doc.export = export_with_page
    creaite_doc._posted_page = lambda doc, page, fmt: real_posted(dict(doc, kind="weekly", audience="internal"), page, fmt)


def _decoder_off():
    import edit_ai
    edit_ai.LOOK_ALIKE = {k: v for k, v in edit_ai.LOOK_ALIKE.items() if k not in confusables.TABLE or k < 0x0410}


def _other_parser():
    """The render parses the file with another parser than the gate's (the last data block, not the first)."""
    def last(path, kind, doc=None):
        text = creaite_doc.real(path).read_text(encoding="utf-8", errors="replace")
        d = json.loads(creaite_doc.BLOCK.findall(text)[-1])
        if kind is not None and d.get("kind") != kind:
            raise creaite_doc.DocError("kind")
        return creaite_doc.force_client_audience(d)
    creaite_doc._export_doc = last


def _pictures_off():
    real = creaite_doc.text_image
    creaite_doc.text_image = lambda doc, ref: real(doc, ref) or paths.image_file(paths.project_dir((doc or {}).get("project")), ref)


def _gap_c_off():
    """v2.5.1 step 2's gap C rule taken away: any `_images/` picture is a client report's."""
    import client_snapshot
    creaite_doc.CLIENT_PICTURE = ""
    client_snapshot.CLIENT_PICTURE = ""


def _metadata_kept():
    """A picture's metadata kept (docx_tools.strip_image_metadata does nothing)."""
    import docx_tools
    docx_tools.strip_image_metadata = lambda data: data


def _match_raw():
    """Match internal's check reads the document as sent (not as the export reads it): v2.5.0's match-check."""
    def raw(handler, req):
        con = client_leak.connect()
        return report_server.answer(handler, {"ok": True, "findings": [client_leak.coded_findings(d, con) for d in req.get("docs") or []]})
    report_server.match_check_route = raw


def _audience_flip():
    creaite_doc._internal_text = lambda doc, s: (s.get("type") == creaite_doc.TEXT_TYPE and creaite_doc.is_client(doc)
                                                 and (s.get("audience") or "internal") == "internal")


def _launder_on():
    real = creaite_doc.creaite_wrote

    def old(path, raw):
        import client_snapshot
        d = hashlib.sha256(raw).hexdigest()
        return real(path, raw) or any(e.get("state") == "filed" and e.get("source_sha256") == d
                                      for e in client_snapshot.registry().values())
    creaite_doc.creaite_wrote = old


MUTANTS = {
    "gate_off": _gate_off, "output_off": _output_off, "reread": _reread, "page_used": _page_used, "decoder_off": _decoder_off,
    "audience_flip": _audience_flip, "other_parser": _other_parser, "pictures_off": _pictures_off,
    "metadata_kept": _metadata_kept, "match_raw": _match_raw, "gap_c_off": _gap_c_off,
    "derive_off": lambda: setattr(creaite_doc, "derive_client", lambda doc: doc),
    "allow_off": lambda: setattr(creaite_doc, "client_shape", lambda doc: copy.deepcopy(doc)),
    "signs_off": lambda: setattr(creaite_doc, "report_signs", lambda path, doc: []),
    "same_report_off": lambda: setattr(report_doc, "same_report", lambda *a, **k: None),
    "names_off": lambda: setattr(report_server, "_name_problem", lambda name, own=None: None),
    "logos_off": lambda: setattr(creaite_doc._Word, "logo_files", _logo_files_stored),
    "stub_off": lambda: setattr(creaite_doc, "_stub_row", lambda row: dict(row)),
    "facts_off": lambda: setattr(creaite_doc, "derive_facts", lambda doc: doc),                  # v2.5.3 (#259, K3)
    "loose_off": lambda: setattr(client_output, "loose_findings", lambda *a, **k: []),           # v2.5.3 (#259, P16)
    # v2.5.3 (#259, K2): every file read as creaite's own, so a text section written on disk as the client's shows again (the
    # properties that plant words there need it with their own guard off, as K2 is a second guard for them)
    "trust_on": lambda: setattr(creaite_doc, "creaite_wrote", lambda path, raw: True),
    # v2.5.3 (#259 round 2, HIGH 1): c25a28fe's trust put back: any registry entry of a filed state whose source hash matches
    "launder_on": lambda: _launder_on(),
    # v2.5.3 (#259): tracker.py apply's second check of a creaite-format client report switched off in its own process
    "apply_check_off": lambda: APPLY_PREAMBLE.append(f"sys.path.insert(0, {str(SCRIPTS)!r})\nimport review\n"
                                                     "review.creaite_client_problem = lambda blk: None"),
}


def _mutant(name):
    """Switch one guard off in this process (the mutation proofs); '' switches none."""
    if name:
        MUTANTS[name]()


def main():
    prop, seed, n = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    for m in (sys.argv[5] if len(sys.argv) > 5 else "").split("+"):
        _mutant(m)
    ctx = Ctx(full=os.environ.get("CREAITE_PROPS_FULL") == "1")
    stats, fails = PROPERTIES[prop](ctx, seed, n)
    ctx.reset()
    print(json.dumps({"property": prop, "seed": seed, "cases": n, "stats": stats, "failures": fails[:20], "failed": len(fails)},
                     default=str))


if __name__ == "__main__":
    main()
