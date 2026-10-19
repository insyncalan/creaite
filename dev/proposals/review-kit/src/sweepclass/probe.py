"""Same-input-class sweep probe (throwaway vault, fictional data). A client report (audience "client", the normal value) carrying a
hostile field, saved, approved (force) and exported through the live routes; each client output scanned for the needles.
Usage: python probe.py <tree root> <variant>[,<variant>...]   (variant 'file:<v>' = written into the draft file on disk instead)"""
import sys, json, zipfile, sqlite3, subprocess, html, re, unittest, base64, zlib
from pathlib import Path
ROOT = Path(sys.argv.pop(1)); VARIANTS = sys.argv.pop(1).split(",")
sys.path.insert(0, str(ROOT / "dev" / "tests")); sys.path.insert(0, str(ROOT / "system" / "scripts"))
import test_report_export_save as S

WEEK = "2026-10-09"


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

    def hidden(self):
        return dict(self.db().execute("SELECT id, description, owner FROM actions WHERE client_visible=0 AND owner LIKE 'Omar%'").fetchone())

    def add_def(self):
        """A second project DEF in the throwaway tracker: one hidden action, one client-visible action (fictional)."""
        con = self.db()
        if con.execute("SELECT 1 FROM projects WHERE code='DEF'").fetchone():
            return
        p = dict(con.execute("SELECT * FROM projects WHERE code='ABC'").fetchone())
        p.update(code="DEF", name="Second Programme")
        con.execute(f"INSERT INTO projects ({','.join(p)}) VALUES ({','.join('?' * len(p))})", list(p.values()))
        base = dict(con.execute("SELECT * FROM actions WHERE id LIKE 'ABC-%' LIMIT 1").fetchone())
        for n, desc, owner, cv in ((1, "Renegotiate the walrus supplier rebate quietly", "Petra Quill", 0),
                                   (2, "Publish the narwhal migration runbook", "Petra Quill", 1)):
            r = dict(base, id=f"DEF-A-{n:03d}", project="DEF", description=desc, owner=owner, client_visible=cv,
                     client_message=("What it is: Narwhal runbook published.\nWhat it means for you: none.\nWhat is being done: done." if cv else ""))
            con.execute(f"INSERT INTO actions ({','.join(r)}) VALUES ({','.join('?' * len(r))})", list(r.values()))
        con.commit()

    def scan(self, path, needles):
        p = self.v.root / path
        b = p.read_bytes()
        if p.suffix == ".docx":
            with zipfile.ZipFile(p) as z:
                b = b"".join(z.read(n) for n in z.namelist() if n.endswith(".xml") or n.endswith(".rels"))
        if p.suffix == ".pdf":
            b = pdf_text(b)
        t = html.unescape(b.decode("utf-8", "ignore")).lower()
        return [n for n in needles if n.lower() in t]

    def mutate(self, v, doc, needles):
        h = self.hidden()
        payload = f"{h['owner']} owns {h['id']}: {h['description']}. confidential. Internal only: keep"
        needles += [h["id"], h["description"], h["owner"], "confidential", "Internal only"]
        if v == "project_name":
            doc["project_name"] = payload
        elif v == "client":
            doc["client"] = f"{h['owner']} {h['id']} confidential"
        elif v == "meta":
            doc.setdefault("meta", {})["note"] = payload
            doc["sources"] = (doc.get("sources") or []) + [{"ref": h["id"], "label": payload}]
            doc.setdefault("layout", {})["note"] = payload
        elif v == "xproj":
            self.add_def()
            needles[:] = ["walrus supplier rebate", "Petra Quill", "narwhal", "DEF-A-002"]
            doc["sections"].append({"id": "free_x", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": False,
                                    "text": "Petra Quill will renegotiate the walrus supplier rebate quietly.", "audience": "client"})
            t = next(s for s in doc["sections"] if s.get("type") == "table" and s.get("columns"))
            col = t["columns"][0]["key"]
            t["rows"] = (t.get("rows") or []) + [{"ref": "DEF-A-002", "shown": True, "cells": {col: "Publish the narwhal migration runbook"}}]
        elif v == "rowshown":
            t = next(s for s in doc["sections"] if s.get("type") == "table" and s.get("columns"))
            t["rows"] = (t.get("rows") or []) + [{"ref": h["id"], "shown": True, "cells": {t["columns"][0]["key"]: "Tester names"}}]
            needles[:] = [h["id"]]
        elif v == "itemstore":
            t = next(s for s in doc["sections"] if s.get("type") == "table" and s.get("columns") and s.get("rows"))
            vis = t["rows"][0]["ref"]
            doc["items"][vis] = {"title": h["description"], "owner": h["owner"], "response_action": "Internal only: shh"}
            doc["items"][h["id"]] = {"title": "Confirm tester names", "owner": h["owner"]}
        elif v == "textflag":
            doc["sections"].append({"id": "free_x", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": False,
                                    "text": payload, "audience": "client"})
        elif v == "pic":
            png = (ROOT / "dev/tests").exists() and __import__("test_dashboard").png(40, 20, (1, 2, 3))
            r = self.post("/api/report/image", {"code": "ABC", "name": "internal-raid-screenshot", "data": base64.b64encode(png).decode()})
            print("### image upload (as the internal weekly editor does):", r)
            doc["sections"].append({"id": "free_x", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": False,
                                    "text": f"![chart]({r['ref']})", "audience": "client"})
            needles[:] = [base64.b64encode(png).decode()[:40], "internal-raid-screenshot"]
        elif v == "title":
            doc["title"] = payload
        elif v == "heading":
            doc["sections"][1]["heading"] = payload
        elif v == "health":
            hs = next((s for s in doc["sections"] if s.get("type") == "health"), None)
            if hs:
                hs.setdefault("data", {})["last_week"] = {"flag": payload, "date": "2026-10-02"}
        elif v == "periodstart":
            doc.setdefault("meta", {})["period_start"] = "2026-10-03"
            doc.setdefault("meta", {})["when"] = payload
        doc["layout"]["order"] = [s["id"] for s in doc["sections"]]

    def test_e2e(self):
        self.client()
        for raw in VARIANTS:
            ondisk = raw.startswith("file:")
            v = raw[5:] if ondisk else raw
            for f in self.reports.glob("*Client report*"):
                if f.is_file(): f.unlink()
            for f in (self.v.root / "system/staging/drafts").glob("*Client report*"): f.unlink()
            print(f"\n======== {raw}")
            r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fresh": True})
            doc, needles = r["doc"], []
            req_client = None
            if ondisk:
                sv = self.post("/api/report/save", {"doc": doc})
                import creaite_doc
                f = self.v.root / sv["path"]
                d = creaite_doc.read(f)
                self.mutate(v, d, needles)
                f.write_text(creaite_doc.dumps(d, keep_text=True), encoding="utf-8")
                print("### control save ok:", sv.get("ok"), "| file now holds needles:", [n for n in needles if n.lower() in f.read_text().lower()])
            else:
                self.mutate(v, doc, needles)
                if v == "client":
                    req_client = doc["client"]
                sv = self.post("/api/report/save", {"doc": doc})
                print("### save:", sv.get("ok"), str(sv.get("message"))[:140], "removed:", sv.get("removed"))
                if not sv.get("ok"):
                    continue
            extra = {"client": req_client} if req_client else {}
            d2 = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK, **extra})
            print("### draft route findings:", len(d2.get("findings") or []), (d2.get("findings") or [])[:3])
            a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True, **extra})
            print("### approve:", a.get("ok"), str(a.get("message"))[:200].replace("\n", " "))
            if a.get("ok"):
                fl = [f for f in self.reports.glob("*Client report*.html")]
                for f in fl:
                    print("### FILED holds:", self.scan(str(f.relative_to(self.v.root)), needles), "|", f.name[-110:])
            for fmt in ("html", "docx", "pdf"):
                e = self.post("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": fmt,
                                                    "on_clash": "number", **extra})
                print(f"### export {fmt}:", e.get("ok"), (e.get("name") or str(e.get("message"))[:160]), "findings:", len(e.get("findings") or []))
                if e.get("ok"):
                    print(f"###   {fmt} holds:", self.scan(e["path"], needles))


if __name__ == "__main__":
    unittest.main(argv=["x", "P.test_e2e"], verbosity=0)
