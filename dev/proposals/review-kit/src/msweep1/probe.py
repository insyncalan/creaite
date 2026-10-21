"""Mutation sweep 1: a clean client draft saved through the route, then its RAW file text mutated on disk (fictional data),
then draft / export (html, docx, pdf) / approve (force, with and without doc) and the filed report scanned for needles.
Usage: python probe.py <tree root> <mut>[,<mut>...]  (or 'all')"""
import sys, json, zipfile, sqlite3, html, re, unittest, zlib, os, shutil
from pathlib import Path
ROOT = Path(sys.argv.pop(1)); MUTS = sys.argv.pop(1)
sys.path.insert(0, str(ROOT / "dev" / "tests"))
import test_report_export_save as S
import subprocess as _sp
_P = _sp.Popen
def _pop(*a, **k):
    if "stderr" in k and k["stderr"] is _sp.DEVNULL: k["stderr"] = open(os.environ.get("ERRLOG", "/dev/null"), "a")
    return _P(*a, **k)
_sp.Popen = _pop

WEEK, WEEK2 = "2026-10-09", "2026-10-16"
BLOCK = re.compile(r'(<script type="application/json" id="creaite-data">)(.*?)(</script>)', re.S)
DO_PDF = os.environ.get("PDF", "1") == "1"


def pdf_text(b):
    out = [b]
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", b, re.S):
        try: out.append(zlib.decompress(m.group(1)))
        except Exception: pass
    return b"\n".join(out)


def enc(d):
    return json.dumps(d, ensure_ascii=False, indent=1).replace("<", "\\u003c")


class P(S.ExportSave):
    def db(self):
        c = sqlite3.connect(self.v.root / "system/tracker.db"); c.row_factory = sqlite3.Row; return c

    def hidden(self):
        return dict(self.db().execute("SELECT id, description, owner FROM actions WHERE client_visible=0 AND project='ABC' AND owner<>'' LIMIT 1").fetchone())

    def add_def(self):
        con = self.db()
        if con.execute("SELECT 1 FROM projects WHERE code='DEF'").fetchone(): return
        p = dict(con.execute("SELECT * FROM projects WHERE code='ABC'").fetchone()); p.update(code="DEF", name="Second Programme")
        con.execute(f"INSERT INTO projects ({','.join(p)}) VALUES ({','.join('?' * len(p))})", list(p.values())); con.commit()

    def scan_bytes(self, p):
        b = p.read_bytes()
        if p.suffix == ".docx":
            with zipfile.ZipFile(p) as z:
                b = b"".join(z.read(n) for n in z.namelist() if n.endswith(".xml") or n.endswith(".rels"))
        if p.suffix == ".pdf": b = pdf_text(b)
        return html.unescape(b.decode("utf-8", "ignore")).lower()

    def hits(self, p, needles):
        t = self.scan_bytes(p) + "\n" + p.name.lower()
        return [n for n in needles if n.lower() in t]

    def drafts(self): return self.v.root / "system/staging/drafts"

    def reset(self):
        for f in list(self.reports.glob("*")):
            if (f.is_file() or f.is_symlink()) and "Weekly report" not in f.name: f.unlink()
        for f in list(self.drafts().glob("*")):
            if (f.is_file() or f.is_symlink()) and "Client report" in f.name: f.unlink()

    # ---- the mutations: (doc dict) -> (doc, raw-transform or None, needles) ----
    def build(self, m, d):
        h = self.hidden()
        pay = f"{h['owner']} owns {h['id']}: {h['description']}. This is confidential. Internal only: keep. [x](creaite:item/{h['id']})"
        needles = [h["id"], h["description"], h["owner"], "confidential", "internal only", "walrus", "SECRETFIELD", "RAWHTML", "Other Client Ltd", "Second Programme"]
        parts = m.split("+")
        add_payload = "nopay" not in parts and "intonly" not in parts
        if "intonly" in parts:
            d["sections"].append({"id": "free_int", "type": "freetext", "heading": "Vendor notes", "default_heading": "", "hidden": False,
                                  "text": "INTERNAL walrus words.", "audience": "internal"})
        if add_payload:
            d["sections"].append({"id": "free_x", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": False,
                                  "text": pay, "audience": "client"})
            d["sections"].append({"id": "free_int", "type": "freetext", "heading": "Vendor notes", "default_heading": "", "hidden": False,
                                  "text": "INTERNAL walrus words.", "audience": "internal"})
            d.setdefault("layout", {})["order"] = [s["id"] for s in d["sections"]]
        raw = []
        S_ = "SECRETFIELD " + h["id"]
        for p in parts:
            k, _, v = p.partition("=")
            if k in ("control", "nopay", "intonly", "withdoc"): continue
            if k == "kind":
                val = {"weekly": "weekly", "minutes": "minutes", "Client": "Client", "sp": " client", "zw": "client​",
                       "list": ["client"], "dict": {"k": "client"}, "num": 1, "clent": "clent", "distributed": "distributed",
                       "null": None}.get(v)
                if v == "missing": d.pop("kind")
                else: d["kind"] = val
            elif k == "aud":
                val = {"internal": "internal", "null": None, "list": ["client"], "distributed": "distributed", "Client": "Client",
                       "weekly": "weekly"}.get(v)
                if v == "missing": d.pop("audience")
                else: d["audience"] = val
            elif k == "client":
                if v == "missing": d.pop("client", None)
                else: d["client"] = {"null": None, "other": "Other Client Ltd", "hidden": S_}[v]
                needles += ["Other Client Ltd", "SECRETFIELD"]
            elif k == "pname":
                self.add_def()
                d["project_name"] = {"hidden": S_, "other": "Second Programme"}[v]; needles += ["SECRETFIELD", "Second Programme"]
            elif k == "project":
                self.add_def()
                if v == "missing": d.pop("project")
                else: d["project"] = {"other": "DEF", "list": ["ABC"]}[v]
            elif k == "date":
                d["date"] = {"other": WEEK2, "bad": "2026-13-45", "future": "2027-01-01", "list": [WEEK]}[v]
            elif k == "title":
                d["title"] = {"": S_, "plain": "SECRETFIELD plain words", "desc": h["description"]}[v]; needles.append("SECRETFIELD")
            elif k == "metaplain":
                d.setdefault("meta", {})["note"] = "SECRETFIELD m"; d.setdefault("layout", {})["note"] = "SECRETFIELD l"
                d["sources"] = (d.get("sources") or []) + [{"ref": "tracker", "label": "SECRETFIELD s"}]
                d["sections"][0].setdefault("data", {}).update(partners=["SECRETFIELD p"])
            elif k == "items":
                d.setdefault("items", {})[h["id"]] = {"title": h["description"], "owner": h["owner"], "id": h["id"]}
                vis = next(iter(d["items"]), None)
                if vis and vis != h["id"]: d["items"][vis] = dict(d["items"][vis], note="Internal only: " + S_)
                needles.append("SECRETFIELD")
            elif k in ("meta", "sources", "layout"):
                if k == "sources": d["sources"] = (d.get("sources") or []) + [{"ref": h["id"], "label": S_}]
                else: d.setdefault(k, {})["note"] = S_
                needles.append("SECRETFIELD")
            elif k == "header":
                hs = d["sections"][0]; hs.setdefault("data", {}).update(title=S_, partners=[S_], logos=["../../../.ssh/id_rsa"])
                needles.append("SECRETFIELD")
            elif k == "secaud":   # an internal text section's audience flipped to client, or the internal flag
                for s in d["sections"]:
                    if s["id"] == "free_int":
                        if v == "client": s["audience"] = "client"
                        elif v == "missing": s.pop("audience")
                        elif v == "internalflag": s["internal"] = True; s["audience"] = "client"
            elif k == "picup":
                import base64
                png = __import__("test_dashboard").png(40, 20, (1, 2, 3))
                r = self.post("/api/report/image", {"code": "ABC", "name": "internal-raid-screenshot", "data": base64.b64encode(png).decode()})
                d["sections"].append({"id": "free_p", "type": "freetext", "heading": "Pic", "default_heading": "", "hidden": False,
                                      "text": f"![chart]({r.get('ref')})", "audience": "client"})
                needles += [base64.b64encode(png).decode()[:40], "internal-raid-screenshot"]
            elif k == "pic":
                d["sections"].append({"id": "free_p", "type": "freetext", "heading": "Pic", "default_heading": "", "hidden": False,
                                      "text": {"img": "![chart](_images/internal-raid.png)", "up": "![c](../../_images/../x.png)",
                                               "abs": "![c](/etc/hosts)"}[v], "audience": "client"})
                needles.append("PICMARKER")
            elif k == "raw":
                raw.append(v)
        return d, raw, needles

    def write_raw(self, f, d, raws):
        text = f.read_text(encoding="utf-8")
        mo = BLOCK.search(text)
        js = enc(d)
        for r in raws:
            if r == "dupkind_badlast": js = js.replace('"kind": "client"', '"kind": "client", "kind": "weekly"', 1)
            elif r == "dupkind_badfirst": js = js.replace('"kind": "client"', '"kind": "weekly", "kind": "client"', 1)
            elif r == "dupaud_badlast": js = js.replace('"audience": "client"', '"audience": "client", "audience": "internal"', 1)
            elif r == "dupproj_badlast": js = js.replace('"project": "ABC"', '"project": "ABC", "project": "DEF"', 1)
            elif r == "trailing": js = js.rstrip().rstrip("}") + ',\n}'
        out = text[:mo.start(2)] + js + text[mo.end(2):]
        for r in raws:
            if r == "bom": out = "﻿" + out
            elif r == "crlf": out = out.replace("\n", "\r\n")
            elif r == "huge": out = out.replace("</main>", "</main>" + ("<!-- pad -->" * 900000), 1)
            elif r == "second":   # a second block after: carries kind weekly
                d2 = dict(d, kind="weekly", audience="internal")
                out = out.replace("</body>", f'<script type="application/json" id="creaite-data">{enc(d2)}</script></body>', 1)
            elif r == "second_before":   # a clean-looking block first, the payload one second
                pass
            elif r == "comment_first":    # an HTML comment holding a data block BEFORE the real one, with kind weekly
                d2 = dict(d, kind="weekly", audience="internal")
                out = out.replace("<body>", f'<body><!-- <script type="application/json" id="creaite-data">{enc(d2)}</script> -->', 1)
            elif r == "rawhtml":
                out = out.replace("</main>", "<p>RAWHTML SECRETFIELD confidential</p></main>", 1)
        f.write_text(out, encoding="utf-8", newline="")

    def post(self, path, body):
        try:
            return S.ExportSave.post(self, path, body)
        except Exception as e:  # noqa
            return {"ok": False, "message": "HTTP-EXC " + repr(e)[:60]}

    def run_routes(self, m, needles, week=WEEK, extra_routes=True):
        res = {}
        d2 = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": week})
        res["draft"] = ("REF " + str(d2.get("message"))[:40]) if not d2.get("ok") else f"ok f={len(d2.get('findings') or [])} k={d2['doc'].get('kind')!r} a={d2['doc'].get('audience')!r}"
        for fmt in (("html", "docx", "pdf") if DO_PDF else ("html", "docx")):
            e = self.post("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": week, "fmt": fmt, "on_clash": "number"})
            if e.get("ok") and e.get("path"):
                hh = self.hits(self.v.root / e["path"], needles)
                res[fmt] = ("LEAK " + str(hh)) if hh else "clean"
            else:
                res[fmt] = "REF:" + str(e.get("message"))[:50]
        body = {"kind": "client", "code": "ABC", "week_ending": week, "force": True}
        if "withdoc" in m and d2.get("ok"):
            body.update(doc=d2["doc"], base_version=d2.get("version"))
        a = self.post("/api/report/approve", body)
        if a.get("ok"):
            fl = list(self.reports.glob("*Client report*.html"))
            hh = sorted({x for f in fl for x in self.hits(f, needles)})
            if hh and os.environ.get("SHOW"):
                for f in fl:
                    t = f.read_text(encoding="utf-8")
                    for mm in re.finditer("SECRETFIELD|walrus", t): print("CTX", f.name[-20:], repr(t[max(0, mm.start()-150):mm.end()+40]))
            res["approve"] = ("LEAK " + str(hh)) if hh else "filed clean " + str([f.name[-60:] for f in fl])
        else:
            res["approve"] = "REF:" + str(a.get("message"))[:60].replace("\n", " ")
        # anything filed anywhere under the project with a needle?
        stray = []
        for f in (self.v.root).rglob("*"):
            if f.is_file() and "system" not in f.parts and f.suffix in (".html", ".docx", ".pdf") and "Client" in f.name:
                hh = self.hits(f, needles)
                if hh: stray.append((f.name[-50:], hh))
        res["stray"] = stray
        return res

    def fresh_clean(self, week=WEEK):
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": week, "fresh": True})
        sv = self.post("/api/report/save", {"doc": r["doc"]})
        assert sv.get("ok"), sv
        return self.v.root / sv["path"]

    def test_e2e(self):
        self.client()
        # approve the internal week 2 as well, for the 'other week' tests
        muts = MUTS.split(",") if MUTS != "all" else ALL
        for m in muts:
            self.reset()
            try:
                f = self.fresh_clean()
                d = json.loads(BLOCK.search(f.read_text(encoding="utf-8")).group(2))
                special = m.split(":")[0] if m.startswith("mv:") else None
                if special:
                    res = self.move(m, f, d)
                else:
                    d, raws, needles = self.build(m, d)
                    self.write_raw(f, d, raws)
                    res = self.run_routes(m, needles)
                    res["needles"] = needles[:1]
            except Exception as ex:   # noqa
                res = {"EXC": repr(ex)[:200]}
            print(f"@@ {m} :: {json.dumps(res)}", flush=True)

    def move(self, m, f, d):
        h = self.hidden()
        pay = f"{h['owner']} owns {h['id']}: {h['description']}. This is confidential. Internal only: keep."
        needles = [h["id"], h["description"], h["owner"], "confidential", "internal only"]
        d["sections"].append({"id": "free_x", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": False,
                              "text": pay, "audience": "client"})
        what = m.split(":")[1]
        text = f.read_text(encoding="utf-8"); mo = BLOCK.search(text)
        def put(path, dd):
            path.write_text(text[:mo.start(2)] + enc(dd) + text[mo.end(2):], encoding="utf-8")
        if what.startswith("to_weekly"):
            target = self.drafts() / "2026-10-09 Weekly report - Example Programme.html"
            dd = dict(d)
            if what == "to_weekly_kw": dd.update(kind="weekly")
            if what == "to_weekly_dist": dd.update(kind="weekly", audience="distributed")
            if what == "to_weekly_cl": dd.update(kind="weekly", audience="client")
            put(target, dd); f.unlink()
            out = {}
            for fmt in ("html", "docx"):
                e = self.post("/api/report/export", {"kind": "weekly", "code": "ABC", "week_ending": WEEK, "fmt": fmt, "on_clash": "number"})
                hh = self.hits(self.v.root / e["path"], needles) if e.get("ok") and e.get("path") else None
                lab = None
                if e.get("ok") and fmt == "html":
                    t = (self.v.root / e["path"]).read_text(encoding="utf-8"); mm = re.search(r'</h1>.{0,300}?<div class="sub">([^<]*)</div></header>', t, re.S)
                    lab = mm and mm.group(1)
                out["weekly_" + fmt] = e.get("ok"), str(e.get("message") or e.get("name"))[:70], hh, lab
            a = self.post("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": WEEK, "force": True})
            out["weekly_approve"] = a.get("ok"), str(a.get("message"))[:80]
            target.unlink(missing_ok=True)
            return out
        if what == "to_weekly_old":   # the client draft (kind client, payload) as the weekly draft: then approve/export weekly
            wk = next(self.drafts().glob("*Weekly report*.html"), None)
            target = wk or (self.drafts() / f.name.replace("Client report", "Weekly report"))
            put(target, d); f.unlink()
            out = {}
            e = self.post("/api/report/export", {"kind": "weekly", "code": "ABC", "week_ending": WEEK, "fmt": "html", "on_clash": "number"})
            out["weekly_export"] = e.get("ok"), str(e.get("message") or e.get("path"))[:80]
            a = self.post("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": WEEK, "force": True})
            out["weekly_approve"] = a.get("ok"), str(a.get("message"))[:80]
            target.unlink(missing_ok=True)
            return out
        if what == "weekly_as_client":   # a weekly-kind doc (audience client) in the client draft's place
            d2 = dict(d, kind="weekly", audience="client"); put(f, d2)
            return self.run_routes(m, needles)
        if what == "race":
            import threading, time as _t
            clean_txt = f.read_text(encoding="utf-8")
            dirty_txt = text[:mo.start(2)] + enc(d) + text[mo.end(2):]
            stop = [False]; tmp = f.with_name(".race.tmp")
            def flip():
                i = 0
                while not stop[0]:
                    tmp.write_text(dirty_txt if i % 2 else clean_txt, encoding="utf-8"); os.replace(tmp, f); i += 1
                    _t.sleep(0.0005)
            th = threading.Thread(target=flip, daemon=True); th.start()
            out = {"exp_ok": 0, "exp_leak": 0, "exp_ref": 0, "appr": None}
            t0 = _t.time()
            while _t.time() - t0 < float(os.environ.get("RACE_S", "90")):
                e = self.post("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": "html", "on_clash": "number"})
                if e.get("ok") and e.get("path"):
                    out["exp_ok"] += 1
                    if self.hits(self.v.root / e["path"], needles): out["exp_leak"] += 1; out["leakfile"] = e["path"][-60:]
                    (self.v.root / e["path"]).unlink()
                else: out["exp_ref"] += 1
                if os.environ.get("RACE_APPROVE") and out["appr"] is None:
                    a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
                    if a.get("ok"):
                        fl = list(self.reports.glob("*Client report*.html"))
                        out["appr"] = sorted({x for ff in fl for x in self.hits(ff, needles)})
                        break
            stop[0] = True; th.join()
            return out
        if what == "otherweek_name":   # the week-1 draft renamed to week 2's name
            n2 = f.name.replace("2026-10-09", "2026-10-16")
            put(self.drafts() / n2, d); f.unlink()
            return self.run_routes(m, needles, week=WEEK2)
        if what == "otherweek_content":   # name week 1, content week 2
            put(f, dict(d, date=WEEK2)); return self.run_routes(m, needles)
        if what == "defname":   # ABC's draft placed under DEF's name
            self.add_def()
            n2 = f.name.replace(S.ABC.split("/")[-1].split(" ", 1)[-1] if False else "Example", "Second") if False else None
            tgt = self.drafts() / "2026-10-09 Client report - Second Programme.html"
            put(tgt, d); f.unlink()
            out = {}
            for fmt in ("html", "docx"):
                e = self.post("/api/report/export", {"kind": "client", "code": "DEF", "week_ending": WEEK, "fmt": fmt, "on_clash": "number"})
                out[fmt] = e.get("ok"), str(e.get("message") or e.get("path"))[:80]
            a = self.post("/api/report/approve", {"kind": "client", "code": "DEF", "week_ending": WEEK, "force": True})
            out["approve"] = a.get("ok"), str(a.get("message"))[:80]
            tgt.unlink(missing_ok=True)
            return out
        if what.startswith("symlink"):
            ext = self.v.root / "elsewhere.html"
            put(ext, d); f.unlink(); f.symlink_to(ext)
            return self.run_routes(m, needles)
        if what == "symlink_nopay":
            pass
        return {"?": what}


ALL = []

if __name__ == "__main__":
    unittest.main(argv=["x", "P.test_e2e"], verbosity=0)
