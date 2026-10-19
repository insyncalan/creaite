#!/usr/bin/env python3
"""Seeded generator sketch for the client-report export properties (#239). Stdlib only, no repo imports, fictional data.
Shape only: Team Stark wires `cases()` to the live routes (save/approve/export/match-check/minutes) and `leaks()` to the outputs.

    python3 -I gen_sketch.py [seed] [n]        # prints the seed, then each case's mutation list; seed also from PROP_SEED
    smoke: n=50   full: n=2000   (the seed is printed first and again on any failure: rerun with it to replay)

HYPOTHESIS SKETCH (optional; the stdlib generator below is the reference, a strategy gives shrinking for free):
    from hypothesis import given, settings, strategies as st
    FIELD  = st.sampled_from(sorted(POOLS))                      # one field name per mutation
    MUT    = st.tuples(FIELD, st.integers(0, 10_000), st.sampled_from(("file", "request", "raw")))
    CASE   = st.lists(MUT, min_size=1, max_size=2)               # one or two mutations at a time
    @settings(max_examples=50, derandomize=True, deadline=None)  # smoke; 2000 for full; derandomize = fixed seed
    @given(CASE)
    def test_p1(case): d = apply(base(), case); assert not leaks(run_all_surfaces(d), NEEDLES)
    # shrink target = the shortest mutation list that still leaks; print it with the seed.
"""
import copy
import hashlib
import json
import os
import random
import sys
import unicodedata
from urllib.parse import quote

# ---- fictional world ------------------------------------------------------------------------------------------------------------
H = {"id": "ABC-A-007", "title": "Renegotiate the walrus supplier rebate quietly", "owner": "Omar Ali"}   # hidden item of ABC
X = {"id": "DEF-A-090", "title": "Quietly drop the narwhal escrow clause", "owner": "Petra Quill"}        # another project's item
VIS = {"id": "ABC-A-001", "title": "Confirm tester names", "owner": "Sara Khan"}                           # client-visible item
NEEDLES = [H["id"], H["title"], H["owner"], X["id"], X["title"], X["owner"], "confidential", "Internal only", "INTWALRUS",
           "ZEBRAPAY", "SECRETFIELD", "creaite:item"]
WEEK = "2026-10-09"
CODE, NAME, CLIENT = "ABC", "Example Programme", "Example Client Ltd"


def base(rng):
    """A clean client draft of the shape report_doc.client_doc builds (sections in the client default order)."""
    def sec(i, t, h, **k): return {"id": i, "type": t, "heading": h, "default_heading": h, "hidden": False, **k}
    row = lambda it, shown=True: {"ref": it["id"], "shown": shown, "cells": {"what": it["title"], "owner": it["owner"]}}
    return {"format": "creaite-doc", "schema": 1, "kind": "client", "audience": "client", "project": CODE, "project_name": NAME,
            "title": f"Client report - {NAME}", "date": WEEK, "client": CLIENT, "version": 1, "state": "draft", "based_on": None,
            "layout": {"order": [], "hidden": [], "headings": {}, "logos": ["firm", "client"], "rows": {}},
            "sections": [
                sec("header", "header", "Client report", data={"label": "Client report", "week_ending": WEEK, "client": CLIENT,
                                                               "logos": [{"kind": "firm"}, {"kind": "client"}]}),
                sec("health", "health", "Health", text="On plan.", data={"flag": "Green"}),
                sec("glance", "figures", "At a glance", figures=[{"key": "overdue", "value": 0, "shown": True}]),
                sec("summary", "text", "Summary", text="Quincebrook is on plan for the week."),
                sec("milestones", "timeline", "Milestones", data={"milestones": ["ABC-M-001"]}),
                sec("asks", "table", "What we need from you", columns=[{"key": "what"}, {"key": "owner"}],
                    rows=[row(VIS), row(H, shown=False)], tags=[{"ref": VIS["id"], "label": "decision"}]),
                sec("current_state", "panes", "Current state", panes=[{"text": "Testing starts Monday."}, {"text": "No risks."}]),
                sec("free_a", "freetext", "Notes", text="Plain words.", audience="client"),
                sec("free_b", "freetext", "Vendor notes", text="Plain internal words.", audience="internal"),
            ],
            "items": {VIS["id"]: {"title": VIS["title"], "owner": VIS["owner"]}},
            "sources": [{"ref": "tracker", "label": "creaite tracker"}], "meta": {"locked": True, "facts_week": WEEK}}


# ---- text encoders: one payload, every form the gate must catch like the plain one (P15) --------------------------------------------
ZW = "\u200b\u200d\u2060\ufeff\u00ad"
def f_plain(s, r): return s
def f_pct(s, r): return quote(s, safe="")
def f_pct2(s, r): return quote(quote(s, safe=""), safe="")
def f_ent(s, r): return "".join(f"&#{ord(c)};" if c.isalnum() and r.random() < .4 else c for c in s)
def f_zw(s, r): return "".join(c + (r.choice(ZW) if r.random() < .3 else "") for c in s)
def f_full(s, r): return "".join(chr(ord(c) + 0xFEE0) if "!" <= c <= "~" and r.random() < .5 else c for c in s)
def f_cyr(s, r): return s.translate(str.maketrans({"a": "\u0430", "e": "\u0435", "o": "\u043e", "c": "\u0441", "A": "\u0410"}))
def f_md(s, r): return r.choice(["[x](%s)", "![x](%s)", "**%s**", "`%s`", "> %s", "- %s", "<a href='u'>%s</a>", "[%s](creaite:item/" + H["id"] + ")"]) % s
def f_json(s, r): return json.dumps(s)[1:-1].replace("a", "\\u0061", 1)
def f_case(s, r): return r.choice([s.upper(), s.lower(), s.swapcase()])
def f_space(s, r): return s.replace("-", r.choice([" ", "\u2011", "\u2010", "_", "\u00a0"])).replace(" ", r.choice(["  ", "\n", "\t", "\u00a0"]), 1)
FORMS = [f_plain, f_pct, f_pct2, f_ent, f_zw, f_full, f_cyr, f_md, f_json, f_case, f_space]


def payload(r):
    """Hidden material in some form: id, title, owner, marker, other-project wording, a creaite link, or a mix."""
    pieces = [H["id"], H["title"], H["owner"], "This is confidential", "Internal only: keep", X["title"], X["owner"], X["id"],
              f"[the plan](creaite:item/{H['id']})", "INTWALRUS", "ZEBRAPAY"]
    s = " ".join(r.sample(pieces, r.randint(1, 3)))
    return r.choice(FORMS)(s, r)


# ---- value pools per field (hostile values seen in the probes) --------------------------------------------------------------------------
KIND = ["weekly", "minutes", "Client", " client", "client\u200b", ["client"], {"k": "client"}, 1, "clent", "distributed", None, "__missing__"]
AUD = ["internal", "distributed", "weekly", "Client", None, ["client"], "__missing__"]
PATHS = ["../../../.ssh/id_rsa", "/etc/hosts", "_images/../x.png", "C:\\x.png", "file:///etc/hosts", "https://beacon.example/a.png",
         "_images/internal-raid-screenshot.png", "../documents/vault.png", "documents/secret.png", "\\\\host\\share\\a.png"]
NAMES = ["CON", "NUL", "COM1", "COM\u00b9", "CONIN$", "aux.docx", "a<b>.docx", 'a"b.docx', "a|b?.docx", "a:b.docx", "a*b", ".hidden",
         "x" * 151, "..", "a/b", "a\\b", "a\x00b", "2026-10-09 Client report - Example Programme (Example Client Ltd)",
         "2026-10-09 Weekly report - Example Programme", "weekly report", "CLIENT   REPORT", "client\u00a0report", "Client report (2)"]
UNKNOWN_KEYS = ["ref", "milestones", "timeline", "note", "comment", "html", "style", "href", "src", "path", "internal", "owner", "x-raw"]
SVG = ["<svg xmlns='http://www.w3.org/2000/svg'><text>SECRETWORD</text></svg>", "<svg xmlns='http://www.w3.org/2000/svg'><style>@import url(https://e.invalid/a.css)</style></svg>",
       "<?xml version='1.0'?><!DOCTYPE svg [<!ENTITY s 'SECRETWORD'>]><svg xmlns='http://www.w3.org/2000/svg'><text>&s;</text></svg>",
       "<svg xmlns='http://www.w3.org/2000/svg'><foreignObject><div>SECRETWORD</div></foreignObject></svg>",
       "<svg xmlns='http://www.w3.org/2000/svg'><rect aria-label='SECRETWORD' id='SECRETWORD'/></svg>"]
PIC_REFS = ["_images/internal-raid.png", "_images/../../x.png", "/etc/hosts", "documents/vault.png", "_images/a b.png", "_images/other-projects.jpg"]
RAW = ["dupkind_badlast", "dupkind_badfirst", "dupaud_badlast", "dupproj_badlast", "bom", "crlf", "trailing_comma", "second_block",
       "comment_first", "huge_padding", "raw_html_in_block"]


def pick(r, pool):
    return r.choice(pool)


# ---- mutations: name -> fn(doc, rng) -> bool (False = does not apply to this doc, e.g. no table) ---------------------------------------
def top(key, pool):
    def m(d, r):
        v = pick(r, pool)
        d.pop(key, None) if v == "__missing__" else d.__setitem__(key, v() if callable(v) else v)
        return True
    return m


def txt_field(sec_id, key):
    def m(d, r):
        s = next((x for x in d["sections"] if x["id"] == sec_id), None)
        if not s: return False
        s[key] = payload(r); return True
    return m


def m_header(d, r):
    h = d["sections"][0]["data"]
    h.update(title=payload(r), partners=[payload(r)], logos=[{"kind": pick(r, ["firm", "client", "partner:zzz", "other"]), "path": pick(r, PATHS)}])
    return True


def m_rows(d, r):
    t = next((s for s in d["sections"] if s.get("rows")), None)
    if not t: return False
    it = pick(r, [H, X]); t["rows"].append({"ref": it["id"], "shown": True, "cells": {"what": payload(r)}}); return True


def m_items(d, r):
    d["items"][pick(r, [H["id"], X["id"], VIS["id"]])] = {"title": payload(r), "owner": H["owner"], "id": H["id"]}; return True


def m_sec_flags(d, r):
    s = next(x for x in d["sections"] if x["id"] == "free_b")
    k = r.choice(["audience=client", "audience=__missing__", "internal=True", "hidden=True", "audience=None"])
    key, _, v = k.partition("=")
    s.pop(key, None) if v == "__missing__" else s.__setitem__(key, {"client": "client", "True": True, "None": None}[v]); return True


def m_pic(d, r):
    d["sections"].append({"id": f"free_p{r.randint(0, 99)}", "type": "freetext", "heading": "Pic", "default_heading": "", "hidden": False,
                          "text": f"before\n\n![chart]({pick(r, PIC_REFS)})\n\nafter", "audience": "client"}); return True


def m_unknown(d, r):
    tgt = r.choice([d, d["layout"], d["meta"], d["sections"][r.randrange(len(d["sections"]))], d["items"].setdefault(VIS["id"], {})])
    tgt[pick(r, UNKNOWN_KEYS) + str(r.randint(0, 9))] = payload(r); return True


def m_proj(d, r):
    d["project"] = pick(r, ["DEF", ["ABC"], "abc", "ABC\n", "", None]); return True


def m_date(d, r):
    d["date"] = pick(r, ["2026-10-16", "2026-13-45", "2027-01-01", ["2026-10-09"], "2026-10-9"]); return True


def m_meta(d, r):
    d["meta"].update(note=payload(r), period_start="2026-10-03", when=payload(r))
    d["sources"] = d["sources"] + [{"ref": H["id"], "label": payload(r)}]
    d["layout"]["note"] = payload(r); return True


MUTATIONS = {
    "kind": top("kind", KIND), "audience": top("audience", AUD), "project": m_proj, "date": m_date,
    "project_name": top("project_name", [lambda: payload(random.Random(1)), NAME + " X", None]),
    "client": top("client", ["Other Client Ltd", None, "SECRETFIELD", "Omar Ali"]), "title": top("title", ["SECRETFIELD plain", H["title"]]),
    "header": m_header, "meta_sources_layout": m_meta, "items": m_items, "rows": m_rows, "section_flags": m_sec_flags,
    "text_summary": txt_field("summary", "text"), "heading": txt_field("summary", "heading"), "notes_text": txt_field("free_a", "text"),
    "picture_ref": m_pic, "unknown_key": m_unknown,
}
WHERE = ["file", "request", "raw"]       # file = written into the draft on disk; request = in the POST body; raw = a transform of the file's text


def walk(x, path=()):
    """Every field path of a document (P5: the schema's fields enumerated from a sample, not from the cases we know)."""
    yield path
    if isinstance(x, dict):
        for k, v in x.items(): yield from walk(v, path + (k,))
    elif isinstance(x, list):
        for i, v in enumerate(x): yield from walk(v, path + (i,))


def mutate_path(d, path, value):
    t = d
    for p in path[:-1]: t = t[p]
    t[path[-1]] = value


def cases(seed, n):
    """n cases: each is one or two mutations (and where each lands) on a fresh clean draft; deterministic for the seed."""
    r = random.Random(seed)
    for i in range(n):
        doc = base(r)
        names = r.sample(sorted(MUTATIONS), r.choice([1, 1, 2]))
        done = []
        for nm in names:
            if MUTATIONS[nm](doc, r): done.append({"mutation": nm, "where": r.choice(WHERE),
                                                   "raw": r.choice(RAW) if r.random() < .15 else None})
        yield {"i": i, "seed": seed, "mutations": done, "doc": doc, "name": pick(r, NAMES), "svg": pick(r, SVG), "fmt": pick(r, ["html", "docx", "pdf"]),
               "page": r.random() < .3, "on_clash": pick(r, ["number", "rename", "overwrite", None])}


def completeness_cases(seed):
    """P5: one case per field path of the clean draft, set to a hostile string."""
    r = random.Random(seed); d = base(r)
    for path in walk(d):
        if not path: continue
        c = base(r)
        try: mutate_path(c, path, payload(r))
        except (KeyError, IndexError, TypeError): continue
        yield {"path": path, "doc": c}


# ---- oracle sketch: needles in any decoded form of any output byte -----------------------------------------------------------------
CONFUSABLES = str.maketrans({"\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0441": "c", "\u0410": "A", "\u0440": "p", "\u0445": "x"})   # extend: full table


def fold(s):
    s = unicodedata.normalize("NFKC", s).translate(CONFUSABLES)
    s = "".join(c for c in s if c not in ZW)
    return "".join(c for c in s.lower() if c.isalnum())


def leaks(blobs, needles=NEEDLES):
    """blobs: {surface name: bytes or str} (filed html + data block, html/docx xml+rels+media names/hashes, pdf text, page, file names).
    A needle is found when its folded form is in the folded text (percent/entity/JSON escapes undone first, up to 3 levels)."""
    import html, re
    from urllib.parse import unquote
    out = {}
    for k, b in blobs.items():
        t = b.decode("utf-8", "ignore") if isinstance(b, bytes) else b
        for _ in range(3): t = unquote(html.unescape(re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), t)))
        f = fold(t)
        hit = [n for n in needles if fold(n) in f]
        if hit: out[k] = hit
    return out


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PROP_SEED", 239))
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    print(f"seed={seed} n={n}")
    h = hashlib.sha256()
    for c in cases(seed, n):
        h.update(json.dumps(c["doc"], sort_keys=True, default=str).encode())
        ml = ", ".join(f"{m['mutation']}@{m['where']}" + (f"+{m['raw']}" if m["raw"] else "") for m in c["mutations"])
        print(f"#{c['i']:03d} [{ml or 'control'}] fmt={c['fmt']} name={c['name'][:30]!r} page={c['page']} clash={c['on_clash']}")
    print("digest", h.hexdigest()[:16], "(same seed, same digest)")
    r = random.Random(seed)       # oracle self-test: every encoder form of the hidden id/title is found, a clean text is not
    bad = [f.__name__ for f in FORMS if not leaks({"x": f(H["id"] + " " + H["title"], r)})]
    print("oracle misses:", bad or "none", "| clean text found:", bool(leaks({"x": base(r)["sections"][3]["text"]})))
    print("completeness paths:", sum(1 for _ in completeness_cases(seed)))
