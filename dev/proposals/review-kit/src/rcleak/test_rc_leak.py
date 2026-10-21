"""Scratch review probes for v2.5.0 rc-a (13ab1ca4). Fictional data only (the test vault's ABC fixture)."""
import json, sqlite3, sys, unittest, zipfile, re, html
from pathlib import Path
sys.path.insert(0, __import__("os").environ["KIT_CK"] + "/dev/tests")
import test_sbs_matchgate as M
INT, CLI, WEEK = M.INT, M.CLI, M.WEEK


class Probe(M.Base):
    def ids(self):
        con = sqlite3.connect(self.v.root / "system/tracker.db")
        out = {}
        for t, col in (("actions", "description"), ("raid", "description"), ("decisions", "decision")):
            for i, d, cv in con.execute(f"SELECT id, {col}, client_visible FROM {t}"):
                out[i] = (d, cv)
        return out

    def check_docs(self, docs):
        return self.api("/api/report/match-check", {"docs": docs})

    def test_a_gate_variants(self):
        self.open_hub()
        ids = self.ids()
        print("ITEMS", ids)
        hid_a = next(i for i, (d, cv) in ids.items() if d == "Confirm tester names")
        hid_r = next(i for i, (d, cv) in ids.items() if d.startswith("Vendor exits"))
        base = self.client_draft()
        print("SECTIONS", [(s["id"], s["type"]) for s in base["sections"]])
        p, x, n = hid_a.split("-")
        variants = {
            "marker": "Internal only: keep this.", "marker-nbh": "Internal‑only: keep this.",
            "marker-ent": "Internal&#45;only: keep this.", "marker-zw": "Inter​nal only: keep.",
            "marker-bracket": "[internal only] keep.", "marker-INTERNAL": "INTERNAL: keep this from them.",
            "id": f"See {hid_a}.", "id-lower": f"see {hid_a.lower()}.", "id-nbh": f"See {p}‑{x}‑{n}.",
            "id-ent": f"See {p}&#45;{x}&#45;{n}.", "id-pct": f"See {p}%2D{x}%2D{n}.", "id-space": f"See {p} {x} {n}.",
            "id-cyr": f"See {p.replace('A', chr(0x410))}-{x}-{n}.", "id-fullwidth": "See " + "".join(chr(ord(c) + 0xFEE0) if c.isalnum() else c for c in hid_a) + ".",
            "id-link": f"[the plan](creaite:item/{hid_a})", "id-https": f"[x](https://example.com/{hid_a})",
            "title": "Vendor exits the market before go-live", "title-quote": "“Vendor exits the market before go‑live”",
            "title-nl": "Vendor exits the\nmarket before go-live", "title-md": "Vendor **exits** the market before go-live",
            "title-partial": "the vendor exits the market", "title-case": "VENDOR EXITS THE MARKET BEFORE GO-LIVE",
            "conf": "This is confidential.", "conf-upper": "CONFIDENTIAL", "conf-shy": "confi­dential",
            "conf-cyr": "cоnfidential", "conf-ent": "conf&#105;dential", "conf-split": "confi dential", "conf-md": "confi**dential**",
            "owner": "Omar Ali", "owner-rev": "Ali, Omar", "owner-email": "omar.ali@example.com", "owner-init": "O. Ali",
            "owner-upper": "OMAR ALI", "owner-first": "Omar will do it", "owner-nbsp": "Omar Ali",
            "decision-title": "Absorb the phase one overrun internally", "memory": "Budget overrun on phase one is being absorbed",
            "clean": "Quincebrook is on plan for the week.",
        }
        docs = []
        for k, t in variants.items():
            d = json.loads(json.dumps(base))
            next(s for s in d["sections"] if s["id"] == "summary")["text"] = t
            docs.append(d)
        # structural: heading, hidden section, items dict, shown:false row text
        d = json.loads(json.dumps(base)); next(s for s in d["sections"] if s["id"] == "summary")["heading"] = "Omar Ali confidential"; docs.append(d); variants["heading"] = "(heading)"
        d = json.loads(json.dumps(base)); s = next(s for s in d["sections"] if s["id"] == "summary"); s["hidden"] = True; s["text"] = "Omar Ali confidential"; docs.append(d); variants["hidden-sec"] = "(hidden section)"
        d = json.loads(json.dumps(base)); d["items"] = {**(d.get("items") or {}), hid_r: {"id": hid_r, "description": "Vendor exits the market before go-live"}}; docs.append(d); variants["items-inject"] = "(items)"
        d = json.loads(json.dumps(base)); d["title"] = "Omar Ali confidential"; docs.append(d); variants["doc-title"] = "(title)"
        d = json.loads(json.dumps(base)); d["client"] = "Omar Ali"; docs.append(d); variants["client-field"] = "(client)"
        d = json.loads(json.dumps(base)); d["sources"] = [{"ref": "x", "label": "Omar Ali confidential"}]; docs.append(d); variants["sources"] = "(sources)"
        d = json.loads(json.dumps(base)); d["meta"] = {**(d.get("meta") or {}), "note": "Omar Ali confidential"}; docs.append(d); variants["meta"] = "(meta)"
        d = json.loads(json.dumps(base)); d["project_name"] = "Omar Ali confidential"; docs.append(d); variants["project_name"] = "(project_name)"
        r = self.check_docs(docs)
        print("ROUTE ok", r.get("ok"), r.get("message"))
        for k, f in zip(variants, r.get("findings") or []):
            print(f"VAR {k:16s} {'CAUGHT' if f else 'PASSES'} {[c['code'] for c in f]}")

    def test_b_slash_on_client_sheet(self):
        self.open_side()
        self.b.click("#v-reporting .sheet-pair > .sheet-fit + .sheet-fit [data-addtext]")
        self.b.wait(f"{CLI} section[data-id^=free_] .sheet-ft.ProseMirror", 10) if False else self.b.wait(f"!!document.querySelector('{CLI} section[data-id^=free_] .sheet-ft.ProseMirror')", 10)
        sec = self.q(f"document.querySelector('{CLI} section[data-id^=free_]').dataset.id")
        self.q(f"document.querySelector('{CLI} section[data-id={sec}] .sheet-ft').focus()")
        self.b.click(f"{CLI} section[data-id={sec}] .sheet-ft")
        self.b.type(" /")
        self.b.pump(0.6)
        rows = self.q("[...document.querySelectorAll('.slashmenu [data-slash]')].map(e=>e.dataset.slash)")
        print("SLASH rows on client sheet:", rows)
        for q in ("item", "work", "note", "person"):
            self.b.type(q); self.b.pump(0.4)
            print("SLASH query", q, self.q("[...document.querySelectorAll('.slashmenu [data-slash]')].map(e=>e.dataset.slash)"))
            for _ in q: self.b.key("Backspace") if hasattr(self.b, "key") else None
        self.q("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")
        # other pickers: # and [[ and @
        for trig in (" #ABC", " [[", " @Om"):
            self.b.type(trig); self.b.pump(0.6)
            print("TRIGGER", repr(trig), "popups:", self.q("[...document.querySelectorAll('.slashmenu, .itempick, .hashpick, [role=listbox]')].filter(e=>e.offsetParent).map(e=>e.className)"))
        # paste an internal item link as HTML
        hid = next(i for i, (d, cv) in self.ids().items() if d == "Confirm tester names")
        self.q(f"""(()=>{{const el=document.querySelector('{CLI} section[data-id={sec}] .sheet-ft');const dt=new DataTransfer();dt.setData('text/html','<p>Pasted <a href="creaite:item/{hid}">Confirm tester names</a> by Omar Ali, confidential. Internal only: x</p>');dt.setData('text/plain','Pasted');el.dispatchEvent(new ClipboardEvent('paste',{{clipboardData:dt,bubbles:true,cancelable:true}}));}})()""")
        self.b.pump(3.5)
        print("CHIPS in client pane:", self.q(f"document.querySelectorAll('{CLI} .chip, {CLI} [data-item], {CLI} .itemchip').length"))
        doc = self.client_draft()
        t = next((s.get("text") for s in doc["sections"] if s["id"] == sec), None)
        print("SAVED client text section:", repr(t))
        print("SAVE findings via route:", [f["code"] for f in self.check_docs([doc])["findings"][0]])
        c = self.client_draft()
        r = self.api("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "doc": c, "base_version": c.get("version"), "force": True})
        print("APPROVE ok:", r.get("ok"), str(r.get("message"))[:200])
        r = self.api("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": "html", "on_clash": "number"})
        print("EXPORT html ok:", r.get("ok"), str(r.get("message"))[:200])


if __name__ == "__main__":
    unittest.main(verbosity=2)


NEEDLES = ["ABC-A-001", "ABC-A-004", "ABC-005", "ABC-D-008", "Escalate data access", "Confirm tester names", "Vendor exits the market",
           "Absorb the phase one overrun", "Omar", "onfidential", "walrus", "Internal only", "Budget overrun", "Pelicanhidden",
           "Test licences not ordered", "ABC-006", "UAT start slipped two weeks"]


class E2E(M.Base):
    def blobs(self):
        out = {}
        for p in self.v.root.rglob("*"):
            if not p.is_file() or "backups" in p.parts or p.suffix not in (".html", ".docx", ".pdf", ".json", ".md"):
                continue
            rel = str(p.relative_to(self.v.root))
            if "lient" not in rel:
                continue
            b = p.read_bytes()
            if p.suffix == ".docx":
                with zipfile.ZipFile(p) as z:
                    b = b"".join(z.read(n) for n in z.namelist() if n.endswith((".xml", ".rels")))
            if p.suffix == ".pdf":
                import subprocess
                r = subprocess.run(["/usr/bin/strings", str(p)], capture_output=True)
                b = b + r.stdout
            out[rel] = b.decode("utf-8", "ignore")
        return out

    def scan(self, label):
        for rel, t in self.blobs().items():
            low = html.unescape(t.replace("\\u003c", "<")).lower()
            hits = [n for n in NEEDLES if n.lower() in low]
            print(f"SCAN {label} {rel}: {hits}")

    def approve_internal(self):
        doc = self.api("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})["doc"]
        next(s for s in doc["sections"] if s["id"] == "health")["text"] = "UAT start slipped two weeks."
        at = next(i for i, s in enumerate(doc["sections"]) if s["id"] == "summary") + 1
        doc["sections"].insert(at, {"id": "free_int", "type": "freetext", "heading": "Vendor notes", "default_heading": "", "hidden": False,
                                    "text": "INTERNAL walrus words. Internal only: keep.", "audience": "internal"})
        doc["layout"]["order"] = [s["id"] for s in doc["sections"]]
        print("int save", self.api("/api/report/save", {"doc": doc, "base_version": doc.get("version")}).get("ok"))
        r = self.api("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": WEEK, "force": True})
        print("int approve", r.get("ok"), str(r.get("message"))[:150])

    def test_c_end_to_end(self):
        self.open_side()
        self.approve_internal()
        self.open_side()
        self.press("[data-crmatchall]") if self.q("!!document.querySelector('[data-crmatchall]')") else None
        self.b.pump(3)
        print("held dialog:", self.held_dialog()[:300].replace("\n", " | "))
        c = self.client_draft()
        for s in c["sections"]:
            if s["id"] == "risks":
                for r in s.get("rows") or []:
                    if r.get("ref") == "ABC-006":
                        r["shown"] = False
            if s["id"] == "this_week":
                s["hidden"] = True; s["text"] = "Pelicanhidden words"
        print("client save", self.api("/api/report/save", {"doc": c, "base_version": c.get("version")}).get("ok"))
        self.scan("draft")
        for fmt in ("html", "docx", "pdf"):
            r = self.api("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": fmt, "on_clash": "number"})
            print("EXPORT", fmt, r.get("ok"), r.get("path") or str(r.get("message"))[:160])
        c = self.client_draft()
        r = self.api("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "doc": c, "base_version": c.get("version")})
        print("CLIENT APPROVE", r.get("ok"), r.get("path") or str(r.get("message"))[:200])
        self.scan("after")
        # file names
        print("FILES", sorted(str(p.relative_to(self.v.root)) for p in self.v.root.rglob("*lient*") if "backups" not in p.parts))
        # flag flow: ABC-A-002 visible -> hidden again, then export
        self.v.propose("flip", [{"n": 1, "op": "update", "table": "actions", "id": "ABC-A-002", "match": "strong", "flags": [],
                                 "decision": "approved", "changes": {"client_visible": 0}}])
        self.v.run("apply")
        r = self.api("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": "html", "on_clash": "number"})
        print("EXPORT after flip", r.get("ok"), str(r.get("message"))[:200], r.get("findings"))
        d = self.api("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        print("DRAFT after flip where", d.get("where"), "findings", d.get("findings"), "holds A-002:", "ABC-A-002" in json.dumps(d.get("doc")))
        # hand-typed hostile text into the client pane, then approve/export
        hostile = " Omar Ali confirms; this is confidential. Internal only: ABC-A-004 Vendor exits the market before go-live"
        try:
            self.open_side()
            self.write(CLI, hostile)
            self.b.pump(3)
            print("### hostile text typed into the client pane")
        except Exception as e:      # noqa: BLE001  the pane is read-only once the report is approved (the editor is gone): same text, through the route
            print(f"### client pane not editable here ({type(e).__name__}): the same text goes in through /api/report/save")
            c0 = self.client_draft()
            s0 = next(x for x in c0["sections"] if x["id"] == "summary")
            s0["text"] = (s0.get("text") or "") + hostile
            print("HOSTILE save", self.api("/api/report/save", {"doc": c0, "base_version": c0.get("version")}).get("ok"))
        c = self.client_draft()
        r = self.api("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "doc": c, "base_version": c.get("version"), "force": True})
        print("HOSTILE APPROVE", r.get("ok"), str(r.get("message"))[:200])
        for fmt in ("html", "docx", "pdf"):
            r = self.api("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": fmt, "on_clash": "number"})
            print("HOSTILE EXPORT", fmt, r.get("ok"), str(r.get("message"))[:120])
        self.scan("hostile")


from test_workstreams import add_project


class Race(M.Base):
    @classmethod
    def load(cls, v):
        M.H.R.populate(v)
        add_project(v, "DEF", "Quiet Project")
        v.run("init")

    def test_d_match_lands_in_another_project(self):
        self.open_side()
        self.write(INT, " Zebracrossing plan for the other client only.")
        self.b.pump(2.5)
        self.q("""(()=>{const f=window.fetch.bind(window); let n=0; window.__mc=0; window.fetch=(u,o)=>{ if(String(u).endsWith('/api/report/match-check')){ window.__mc++; if(n++===0) return new Promise(r=>setTimeout(()=>r(f(u,o)),5000)); } return f(u,o); };})()""")
        self.q("document.querySelector('[data-crmatchall]').click()")
        self.b.pump(0.3)
        self.q("(()=>{ const p=P.find(p=>p.code==='DEF'); if(p) p.cr=true; go('reporting','DEF'); })()")
        self.b.pump(2)
        print("hash now", self.q("location.hash"), "client pane:", (self.q(f"(document.querySelector('{CLI}')||{{innerText:''}}).innerText") or "")[:200].replace("\n", " | "))
        self.b.pump(8)
        print("match-check calls", self.q("window.__mc"))
        pane = self.q(f"(document.querySelector('{CLI}')||{{innerText:''}}).innerText") or ""
        print("DEF client pane holds Zebracrossing:", "Zebracrossing" in pane, "| hash", self.q("location.hash"))
        print("held dialog:", self.held_dialog()[:300].replace("\n", " | "))
        self.b.pump(4)
        for code in ("DEF", "ABC"):
            r = self.api("/api/report/draft", {"kind": "client", "code": code, "week_ending": WEEK})
            print(code, "client draft where", r.get("where"), "holds Zebracrossing:", "Zebracrossing" in json.dumps(r.get("doc")))
        files = [str(p.relative_to(self.v.root)) for p in (self.v.root / "system/staging/drafts").glob("*") if "Zebracrossing" in p.read_text(errors="ignore")] if (self.v.root / "system/staging/drafts").exists() else []
        print("staging files with Zebracrossing:", files)
        d = self.api("/api/report/draft", {"kind": "client", "code": "DEF", "week_ending": WEEK})["doc"]
        print("DEF summary:", repr(next((x.get("text") for x in d["sections"] if x["id"] == "summary"), None))[:200])
        print("DEF route findings:", self.api("/api/report/match-check", {"docs": [d]}))
        w = self.api("/api/report/draft", {"kind": "weekly", "code": "DEF", "week_ending": WEEK})["doc"]
        next(x for x in w["sections"] if x["id"] == "health")["text"] = "Quiet week."
        print("DEF int save", self.api("/api/report/save", {"doc": w, "base_version": w.get("version")}).get("ok"))
        r = self.api("/api/report/approve", {"kind": "weekly", "code": "DEF", "week_ending": WEEK, "force": True})
        print("DEF int approve", r.get("ok"), str(r.get("message"))[:150])
        for fmt in ("html", "docx"):
            r = self.api("/api/report/export", {"kind": "client", "code": "DEF", "week_ending": WEEK, "fmt": fmt, "on_clash": "number"})
            print("DEF EXPORT", fmt, r.get("ok"), r.get("path") or str(r.get("message"))[:200])
            if r.get("ok"):
                f = self.v.root / r["path"]
                b = f.read_bytes()
                if f.suffix == ".docx":
                    with zipfile.ZipFile(f) as z: b = z.read("word/document.xml")
                print("  file holds Zebracrossing:", b"Zebracrossing" in b)
