"""Mutation sweep 2: documents accepted from a REQUEST (throwaway vault, fictional data). Usage: python req.py <tree root> [group,...]"""
import sys, json, zipfile, sqlite3, html, re, unittest, base64, zlib, copy, urllib.request, threading
from pathlib import Path
ROOT = Path(sys.argv.pop(1)); GROUPS = sys.argv.pop(1).split(",") if len(sys.argv) > 1 else ["all"]
sys.path.insert(0, str(ROOT / "dev" / "tests")); sys.path.insert(0, str(ROOT / "system" / "scripts"))
import test_report_export_save as S

WEEK = "2026-10-09"
LINK = ""
OUT = []


def say(*a):
    line = " ".join(str(x) for x in a)
    OUT.append(line)
    print(line, flush=True)


def pdf_text(b):
    out = [b]
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", b, re.S):
        try:
            out.append(zlib.decompress(m.group(1)))
        except Exception:
            pass
    return b"\n".join(out)


class P(S.ExportSave):
    def db(self):
        c = sqlite3.connect(self.v.root / "system/tracker.db"); c.row_factory = sqlite3.Row; return c

    def raw(self, path, data, ctype="application/json"):
        req = urllib.request.Request(self.base + path, data=data, method="POST",
                                     headers={"Content-Type": ctype, "X-Creaite-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, r.read().decode()[:200]
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()[:200]

    def P(self, path, body):
        try:
            return self.post(path, body)
        except urllib.error.HTTPError as e:
            return {"ok": False, "http": e.code, "message": e.read().decode()[:160]}

    def setup_once(self):
        con = self.db()
        if not con.execute("SELECT 1 FROM projects WHERE code='DEF'").fetchone():
            p = dict(con.execute("SELECT * FROM projects WHERE code='ABC'").fetchone())
            p.update(code="DEF", name="Digital Enablement")
            con.execute(f"INSERT INTO projects ({','.join(p)}) VALUES ({','.join('?' * len(p))})", list(p.values()))
        base = dict(con.execute("SELECT * FROM actions WHERE project='ABC' LIMIT 1").fetchone())
        r = dict(base, id="DEF-A-090", project="DEF", description="Renegotiate the walrus supplier rebate quietly", owner="Petra Quill",
                 client_visible=0)
        con.execute(f"INSERT OR REPLACE INTO actions ({','.join(r)}) VALUES ({','.join('?' * len(r))})", list(r.values()))
        con.commit()
        h = dict(con.execute("SELECT id, description, owner FROM actions WHERE project='ABC' AND client_visible=0 AND owner<>'' "
                             "ORDER BY length(description) DESC").fetchone())
        con.commit()
        self.h = h
        self.needles = [h["id"], h["description"], h["owner"], "confidential", "Internal only", "INTWALRUS", "ZEBRAPAY",
                        "walrus supplier rebate", "Petra Quill", "DEF-A-", "creaite:item"]

    def scan_file(self, p):
        p = Path(p)
        if not p.is_absolute():
            p = self.v.root / p
        b = p.read_bytes()
        if p.suffix == ".docx":
            with zipfile.ZipFile(p) as z:
                b = b"".join(z.read(n) for n in z.namelist() if n.endswith(".xml") or n.endswith(".rels"))
        if p.suffix == ".pdf":
            b = pdf_text(b)
        t = html.unescape(b.decode("utf-8", "ignore")).lower()
        return [n for n in self.needles if n.lower() in t]

    def outputs(self):
        """Every client-facing file now in ABC/DEF Reports (filed + exports), with needles found."""
        res = {}
        for proj in ("ABC*", "DEF*"):
            for f in (self.v.root / "projects").glob(f"{proj}/reports/*"):
                if f.is_file() and "Client" in f.name:
                    hit = self.scan_file(f)
                    if True:
                        res[f.parent.parent.name[:3] + "/" + f.name[-70:]] = hit
        return res

    def reset(self):
        for proj in ("ABC*", "DEF*"):
            for f in (self.v.root / "projects").glob(f"{proj}/reports/*"):
                if f.is_file() and "Weekly" not in f.name:
                    f.unlink()
                elif f.is_file() and f.suffix != ".html":
                    f.unlink()
                elif f.is_file() and "(" in f.name:
                    f.unlink()
        for f in (self.v.root / "system/staging/drafts").glob("*Client report*"):
            f.unlink()
        r = self.P("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fresh": True})
        s = self.P("/api/report/save", {"doc": r["doc"]})
        assert s.get("ok"), s
        return self.P("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})

    def dirty(self, doc):
        h = self.h
        doc = copy.deepcopy(doc)
        payload = (f"{h['owner']} owns {h['id']}: {h['description']}. This is confidential. Internal only: keep. "
                   f"{LINK}Petra Quill will renegotiate the walrus supplier rebate quietly DEF-A-090.")
        doc["sections"].append({"id": "free_x", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": False,
                                "text": payload, "audience": "client"})
        doc["sections"].append({"id": "free_int", "type": "freetext", "heading": "Vendor notes", "default_heading": "",
                                "hidden": False, "text": "INTWALRUS internal words.", "audience": "internal"})
        doc["layout"]["order"] = [s["id"] for s in doc["sections"]]
        return doc

    def finish(self, label, extra=None, approve=True):
        """Approve (force) and export the ABC client report by the route; report what reached client files."""
        extra = extra or {}
        res = []
        if approve:
            a = self.P("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True, **extra})
            res.append(f"approve={'OK' if a.get('ok') else 'REF'}")
            if not a.get("ok"):
                res.append("(" + str(a.get("message"))[:70].replace("\n", " ") + ")")
        for fmt in ("html", "docx", "pdf"):
            e = self.P("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": fmt, "on_clash": "number",
                                              **extra})
            res.append(f"{fmt}={'OK' if e.get('ok') else 'REF'}")
        outs = self.outputs()
        leaks = {k: v for k, v in outs.items() if v}
        say(f"[{label}]", " ".join(res), "| LEAK" if leaks else "| clean", json.dumps(leaks)[:300] if leaks else "")
        return leaks

    # ───────────────────────────────────────────────────────────────────────────────────────────────
    def test_all(self):
        self.client()
        self.setup_once()
        g = lambda name: "all" in GROUPS or name in GROUPS
        base = self.reset()
        say("CONTROL")
        self.finish("control clean")
        if g("hot"):
            self.hot()
        if g("fields"):
            self.fields()
        if g("approve"):
            self.approve_doc()
        if g("export"):
            self.export_params()
        if g("page"):
            self.page()
        if g("misc"):
            self.misc()
        say("==== DONE")

    def hot(self):
        h = self.h
        for k, v in (("client", f"{h['owner']} {h['id']} confidential ZEBRAPAY"), ("project_name", f"ZEBRAPAY {h['description']}")):
            d = self.reset()
            doc = copy.deepcopy(d["doc"]); doc[k] = v
            s = self.P("/api/report/save", {"doc": doc})
            say(f"  hot {k}: save={s.get('ok')} path={str(s.get('path'))[-70:]}")
            self.finish(f"clean body, {k}=hidden")
        d = self.reset()
        doc = self.dirty(d["doc"]); doc["project"] = "DEF"
        a = self.P("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True, "doc": doc})
        drafts = [f.name for f in (self.v.root / "system/staging/drafts").glob("*.html")]
        say(f"[approve ABC route + dirty DEF doc] {a.get('ok')} {str(a.get('message'))[:80]!r} drafts={drafts}")
        self.finish("after ABC route+DEF doc", approve=False)
        self.page()
        e = self.P("/api/report/export", {"kind": "weekly", "code": "ABC", "week_ending": WEEK, "fmt": "html", "on_clash": "rename",
                                          "new_name": "2026-10-16 Client report - Example Programme (Example Client Ltd).html"})
        say(f"  [weekly export renamed to a client filing name] {'OK' if e.get('ok') else 'REF'} {e.get('name') or e.get('message')}")

    def save_then(self, label, mut, route_extra=None):
        d = self.reset()
        doc = self.dirty(d["doc"])
        mut(doc)
        s = self.P("/api/report/save", {"doc": doc})
        msg = "save=" + ("OK" if s.get("ok") else "REF(" + str(s.get("message"))[:60] + ")")
        say(f"  {label}: {msg} removed={len(s.get('removed') or [])} path={str(s.get('path'))[-60:]}")
        # stored drafts scan
        for f in (self.v.root / "system/staging/drafts").glob("*.html"):
            pass
        return self.finish(label, route_extra)

    def fields(self):
        say("FIELDS via /api/report/save then approve+export by the ABC client route")
        def setk(k, v):
            def m(doc):
                if v is KeyError:
                    doc.pop(k, None)
                else:
                    doc[k] = v
            return m
        global LINK
        LINK = f"[the plan](creaite:item/{self.h['id']}) "
        self.save_then("creaite:item link", lambda d: None)
        LINK = ""
        self.save_then("dirty text only (no field change)", lambda d: None)
        for v in ("weekly", "minutes", KeyError, "clinet", ["client"], {"k": "client"}):
            self.save_then(f"kind={v if v is not KeyError else 'missing'}", setk("kind", v))
        for v in ("internal", KeyError, None, ["client"], "Client", "distributed"):
            self.save_then(f"audience={v if v is not KeyError else 'missing'}", setk("audience", v))
        h = self.h
        for v in (None, "Other Client Ltd", f"{h['owner']} {h['id']} confidential ZEBRAPAY", "../../x", "a\x00b", "CON", "🦭" * 50,
                  "x" * 5000):
            self.save_then(f"client={str(v)[:20]!r}", setk("client", v))
        for v in (f"ZEBRAPAY {h['description']}", "Digital Enablement", "../evil"):
            self.save_then(f"project_name={v[:20]!r}", setk("project_name", v))
        for v in (f"ZEBRAPAY {h['description']} / ../ x", "CON"):
            self.save_then(f"title={v[:20]!r}", setk("title", v))
        self.save_then("project=DEF (ABC route)", setk("project", "DEF"))
        self.save_then("project=DEF route=DEF", setk("project", "DEF"),
                       route_extra={"code": "DEF"})
        self.save_then("date=2026-10-16", setk("date", "2026-10-16"))
        self.save_then("date=2026-10-16 route=10-16", setk("date", "2026-10-16"), route_extra={"week_ending": "2026-10-16"})
        self.save_then("date=bad", setk("date", "2026-10-09/../../x"))

    def approve_doc(self):
        say("APPROVE with doc in request")
        h = self.h
        # stored clean, request dirty
        for label, mut, extra in (
                ("ABC route + dirty ABC doc", lambda d: None, {}),
                ("ABC route + dirty DEF doc", lambda d: d.update(project="DEF"), {}),
                ("DEF route + dirty ABC doc", lambda d: None, {"code": "DEF"}),
                ("client route + doc kind weekly aud internal", lambda d: d.update(kind="weekly", audience="internal"), {}),
                ("client route + doc kind minutes", lambda d: d.update(kind="minutes"), {}),
                ("route week 10-16 + doc 10-09", lambda d: None, {"week_ending": "2026-10-16"}),
                ("doc aud internal", lambda d: d.update(audience="internal"), {}),
                ("doc + name both", lambda d: None, {"name": "../../projects/ABC/reports/x.html"}),
                ("force='false' str", lambda d: None, {"force": "false"}),
        ):
            d = self.reset()
            doc = self.dirty(d["doc"])
            mut(doc)
            a = self.P("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True,
                                               "doc": doc, "base_version": d["version"], **extra})
            outs = self.outputs()
            leaks = {k: v for k, v in outs.items() if v}
            drafts = [f.name for f in (self.v.root / "system/staging/drafts").glob("*.html") if any(
                n.lower() in f.read_text().lower() for n in self.needles[:5])]
            say(f"[approve: {label}] {'OK' if a.get('ok') else 'REF'} {str(a.get('message'))[:80]!r} | dirty drafts={drafts} |",
                "LEAK " + json.dumps(leaks)[:200] if leaks else "clean")
            self.finish(label + " -> then export", approve=False)
        # request clean, stored dirty (stored via disk write)
        d = self.reset()
        import creaite_doc
        f = self.v.root / d["path"]
        dd = creaite_doc.read(f)
        dd = self.dirty(dd)
        f.write_text(creaite_doc.dumps(dd, keep_text=True), encoding="utf-8")
        a = self.P("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True,
                                           "doc": d["doc"], "base_version": d["version"]})
        say(f"[approve: stored dirty, request clean] {'OK' if a.get('ok') else 'REF'} {str(a.get('message'))[:90]!r}")
        self.finish("stored dirty/request clean -> export", approve=False)
        # stale base_version / concurrent
        d = self.reset()
        doc = self.dirty(d["doc"])
        res = {}
        def go(k, body, path):
            res[k] = self.P(path, body)
        t1 = threading.Thread(target=go, args=("save", {"doc": doc, "base_version": d["version"]}, "/api/report/save"))
        t2 = threading.Thread(target=go, args=("appr", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True,
                                                        "doc": d["doc"], "base_version": d["version"]}, "/api/report/approve"))
        t1.start(); t2.start(); t1.join(); t2.join()
        say(f"[concurrent save(dirty)+approve(stale clean)] save={res['save'].get('ok')} {str(res['save'].get('message'))[:50]!r} "
            f"approve={res['appr'].get('ok')} {str(res['appr'].get('message'))[:60]!r}")
        self.finish("concurrent -> export", approve=False)
        st = self.P("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True,
                                            "doc": self.dirty(d["doc"]), "base_version": 0})
        say(f"[approve stale base_version=0] {st.get('ok')} {str(st.get('message'))[:80]!r}")
        # bodies
        for label, data in (("list body", b"[1,2]"), ("string body", b'"x"'), ("oversized", b'{"a":"' + b"x" * 30_000_000 + b'"}'),
                            ("doc=list", json.dumps({"kind": "client", "code": "ABC", "week_ending": WEEK, "doc": [1]}).encode()),
                            ("doc=str", json.dumps({"kind": "client", "code": "ABC", "week_ending": WEEK, "doc": "x"}).encode())):
            for path in ("/api/report/save", "/api/report/approve", "/api/report/export", "/api/report/match-check", "/api/report/pick"):
                code, body = self.raw(path, data)
                say(f"  [{label} -> {path}] HTTP {code} {body[:70]!r}")
        self.finish("after bad bodies", approve=False)

    def export_params(self):
        say("EXPORT params")
        self.reset()
        a = self.P("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        say("  approved clean:", a.get("ok"))
        cases = [
            ("fmt=../x", {"fmt": "../x"}), ("fmt=html/..", {"fmt": "html/.."}), ("fmt=[html]", {"fmt": ["html"]}),
            ("kind=weekly code=ABC", {"kind": "weekly"}), ("kind=Client", {"kind": "Client"}), ("kind=list", {"kind": ["client"]}),
            ("kind=minutes", {"kind": "minutes"}), ("code=DEF", {"code": "DEF"}), ("code=../ABC", {"code": "../ABC"}),
            ("code=abc", {"code": "abc"}), ("week=2026-10-16", {"week_ending": "2026-10-16"}),
            ("week=../", {"week_ending": "../../x"}), ("client=Other", {"client": "Other Client"}),
            ("name/path/doc/draft params", {"name": "../../system/staging/drafts/x.html", "path": "projects/DEF Digital Enablement/reports/x",
                                            "draft": "/etc/passwd", "doc": {"kind": "weekly"}}),
            ("rename ../", {"on_clash": "rename", "new_name": "../../x.html"}),
            ("rename abs", {"on_clash": "rename", "new_name": "/tmp/x.html"}),
            ("rename NUL", {"on_clash": "rename", "new_name": "a\x00b.html"}),
            ("rename long", {"on_clash": "rename", "new_name": "x" * 200}),
            ("rename emoji", {"on_clash": "rename", "new_name": "🦭 report"}),
            ("rename CON", {"on_clash": "rename", "new_name": "CON"}),
            ("rename to weekly filed", {"on_clash": "rename", "new_name": f"{WEEK} Weekly report - Example Programme.html"}),
            ("overwrite own filed", {"on_clash": "overwrite"}),
            ("force strings", {"force": "yes", "on_clash": "number"}),
        ]
        for label, extra in cases:
            body = {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": "html", "on_clash": "number"}
            body.update(extra)
            e = self.P("/api/report/export", body)
            hit = self.scan_file(e["path"]) if e.get("ok") and e.get("path") else None
            say(f"  [export {label}] {'OK' if e.get('ok') else 'REF'} name={str(e.get('name') or e.get('message'))[:80]!r} "
                f"path={str(e.get('path'))[-50:]} needles={hit}")
        # weekly route export renamed to the client filing name of another week (internal content under a client name)
        e = self.P("/api/report/export", {"kind": "weekly", "code": "ABC", "week_ending": WEEK, "fmt": "html", "on_clash": "rename",
                                          "new_name": "2026-10-16 Client report - Example Programme (Example Client Ltd).html"})
        say(f"  [weekly export renamed to a client filing name] {'OK' if e.get('ok') else 'REF'} {e.get('name') or e.get('message')}")
        if e.get("ok"):
            d = self.P("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-16"})
            x = self.P("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": "2026-10-16", "fmt": "docx"})
            say(f"     then client draft 10-16: {d.get('ok')} {str(d.get('message'))[:60]!r}; client export: {x.get('ok')} "
                f"{str(x.get('message'))[:60]!r}")
        say("  outputs:", json.dumps({k: v for k, v in self.outputs().items() if v})[:300])

    def page(self):
        say("POSTED PAGE (client html/pdf)")
        d = self.reset()
        a = self.P("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        say("  approved clean:", a.get("ok"))
        import creaite_doc
        filed = self.v.root / a["path"]
        doc = creaite_doc.read(filed)
        ver = int(doc.get("version") or 0)
        shown = [s for s in creaite_doc.clean(doc)["sections"] if not s.get("hidden")]
        sid = shown[0]["id"]
        sid2 = next((s["id"] for s in shown if s["id"] != sid), sid)
        h = self.h

        def pg(inner, version=ver):
            m = (f'<div class="export-view"><div class="page"><section data-id="{sid}"><h2>Report</h2><p>{inner}</p></section>'
                 f'</div></div>')
            return {"html": m, "css": ".page{color:#123}", "palette": "creaite", "version": version}
        cases = [
            ("control plain", "All on schedule."),
            ("hidden ABC id", f"See {h['id']} now."),
            ("hidden ABC desc", h["description"]),
            ("hidden ABC owner", f"{h['owner']} leads this."),
            ("confidential", "This is confidential."),
            ("Internal only", "Internal only: keep it."),
            ("creaite link", f'<a href="creaite:item/{h["id"]}">plan</a>'),
            ("DEF hidden wording", "Petra Quill will renegotiate the walrus supplier rebate quietly."),
            ("DEF id", "DEF-A-090 is moving."),
            ("internal section text", "INTWALRUS internal words."),
            ("ZEBRAPAY header-like", "ZEBRAPAY Example Client Ltd header."),
        ]
        for label, inner in cases:
            for fmt in ("html",):
                e = self.P("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": fmt, "on_clash": "number",
                                                  "page": pg(inner)})
                hit = self.scan_file(e["path"]) if e.get("ok") else None
                say(f"  [page {label} {fmt}] {'OK' if e.get('ok') else 'REF'} plain={e.get('plain')} why={str(e.get('plain_why'))[:50]!r} "
                    f"needles={hit}")
        e = self.P("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": "html", "on_clash": "number",
                                          "page": dict(pg("x"), version=str(ver))})
        say(f"  [page version as string] {e.get('ok')} plain={e.get('plain')}")
        # page with a section id of the weekly report's sections not in the client doc
        e = self.P("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": "html", "on_clash": "number",
                                          "page": {"html": '<div class="page"><section data-id="current_state"><p>ZEBRAPAY state</p></section></div>',
                                                   "css": "", "version": ver}})
        say(f"  [page foreign section id] {e.get('ok')} plain={e.get('plain')} why={str(e.get('plain_why'))[:60]!r}")

    def misc(self):
        say("MATCH-CHECK / PICK / LOGOS / IMAGES")
        d = self.reset()
        doc = self.dirty(d["doc"])
        for label, mut in (("clean", None), ("dirty aud client", lambda x: None), ("dirty aud internal", lambda x: x.update(audience="internal")),
                           ("dirty aud missing", lambda x: x.pop("audience")), ("dirty kind weekly", lambda x: x.update(kind="weekly")),
                           ("dirty kind missing", lambda x: x.pop("kind")), ("dirty aud list", lambda x: x.update(audience=["client"])),
                           ("dirty project DEF", lambda x: x.update(project="DEF"))):
            x = copy.deepcopy(d["doc"] if mut is None else doc)
            if mut:
                mut(x)
            r = self.P("/api/report/match-check", {"docs": [x], "kind": "weekly", "audience": "internal"})
            say(f"  [match-check {label}] ok={r.get('ok')} n={[len(f) for f in r.get('findings') or []]} {str(r.get('message'))[:60]!r}")
        for label, x in (("client ABC", d["doc"]), ("client project=DEF", dict(d["doc"], project="DEF")),
                         ("kind weekly ABC", dict(d["doc"], kind="weekly"))):
            r = self.P("/api/report/pick", {"doc": x})
            refs = sorted({c["ref"] for v in (r.get("sections") or {}).values() for c in v})
            say(f"  [pick {label}] ok={r.get('ok')} refs={refs[:12]}")
        r = self.P("/api/report/reshow", {"doc": d["doc"]})
        say(f"  [reshow] {r}")
        for body in ({"code": "ABC", "paths": ["projects/DEF Digital Enablement/CLAUDE.md", "system/branding/logos/DEF-client.png",
                                               "../../etc/passwd"]},
                     {"code": "../ABC"}, {"code": "DEF"}):
            r = self.P("/api/report/logo", body)
            say(f"  [logo {str(body)[:60]}] ok={r.get('ok')} logos={list((r.get('logos') or {}).keys())[:4]} {str(r.get('message'))[:50]!r}")
        png = __import__("test_dashboard").png(40, 20, (1, 2, 3))
        b64 = base64.b64encode(png).decode()
        for kind in ("partner:../x", "partner:def-partner", "../client", "client/../../x", "partner:" + "a" * 60, "firm"):
            r = self.P("/api/report/logo/save", {"code": "ABC", "kind": kind, "ext": "png", "original": b64})
            say(f"  [logo/save kind={kind[:20]!r}] ok={r.get('ok')} {str(r.get('message'))[:60]!r}")
        for kind in ("partner:../x", "../client", "client"):
            r = self.P("/api/report/logo/remove", {"code": "DEF" if kind == "client" else "ABC", "kind": kind})
            say(f"  [logo/remove kind={kind!r}] ok={r.get('ok')} {str(r.get('message'))[:60]!r}")
        for name in ("../../x", "/etc/x", "a\x00b", "CON", "🦭"):
            r = self.P("/api/report/image", {"code": "ABC", "name": name, "data": b64})
            say(f"  [image name={name!r}] ok={r.get('ok')} ref={r.get('ref')}")
        r = self.P("/api/report/image", {"code": "DEF", "name": "defpic", "data": b64})
        ref = r.get("ref")
        r2 = self.P("/api/report/images", {"code": "ABC", "refs": [ref, "_images/../../CLAUDE.md", "../DEF Digital Enablement/reports/" + str(ref)]})
        say(f"  [images ABC asking DEF's {ref}] got={list((r2.get('images') or {}).keys())}")
        # a DEF picture in an ABC client report text
        d = self.reset()
        x = copy.deepcopy(d["doc"])
        x["sections"].append({"id": "free_p", "type": "freetext", "heading": "Pic", "default_heading": "", "hidden": False,
                              "text": f"![c]({ref})\n\n![d](../../DEF Digital Enablement/reports/{ref})\n\n![e](/etc/x.png)", "audience": "client"})
        x["layout"]["order"] = [s["id"] for s in x["sections"]]
        s = self.P("/api/report/save", {"doc": x})
        say(f"  [save with DEF/outside picture refs] ok={s.get('ok')} removed={s.get('removed')}")
        self.needles.append(b64[:40])
        self.finish("pictures -> approve/export")
        self.needles.pop()


if __name__ == "__main__":
    unittest.main(argv=["x", "P.test_all"], verbosity=0)
