"""Audience-bypass probe on the live server (throwaway vault, fictional data). A client report saved with a tampered `audience`,
approved and exported through the routes, with hidden item IDs/titles, an owner name, 'confidential' and the internal marker.
Usage: python route_aud.py <tree root> <variant>"""
import sys, json, zipfile, sqlite3, subprocess, html, re, unittest
from pathlib import Path
ROOT = Path(sys.argv.pop(1)); VARIANT = sys.argv.pop(1)
sys.path.insert(0, str(ROOT / "dev" / "tests")); sys.path.insert(0, str(ROOT / "system" / "scripts"))
import test_report_export_save as S

WEEK = "2026-10-09"


class P(S.ExportSave):
    def hidden_item(self):
        con = sqlite3.connect(self.v.root / "system/tracker.db")
        return con.execute("SELECT id, description, owner FROM actions WHERE client_visible=0 AND owner<>'' LIMIT 1").fetchone()

    def scan(self, path, needles):
        p = self.v.root / path
        b = p.read_bytes()
        if p.suffix == ".docx":
            with zipfile.ZipFile(p) as z:
                b = b"".join(z.read(n) for n in z.namelist() if n.endswith(".xml"))
        if p.suffix == ".pdf":
            b = subprocess.run(["/usr/bin/strings", str(p)], capture_output=True).stdout + b
        t = html.unescape(b.decode("utf-8", "ignore")).lower()
        return [n for n in needles if n.lower() in t]

    def test_e2e(self):
        self.client()
        hid, title, owner = self.hidden_item()
        needles = [hid, title, owner, "confidential", "Internal only", "walrus"]
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        doc = r["doc"]
        payload = f"{owner} owns {hid} {title}. This is confidential. Internal only: keep. [the plan](creaite:item/{hid})"
        doc["sections"].append({"id": "free_x", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": False,
                                "text": payload, "audience": "client"})
        doc["sections"].append({"id": "free_int", "type": "freetext", "heading": "Vendor notes", "default_heading": "",
                                "hidden": False, "text": "INTERNAL walrus words.", "audience": "internal"})
        doc["layout"]["order"] = [s["id"] for s in doc["sections"]]
        draft_file = None
        if VARIANT == "internal": doc["audience"] = "internal"
        elif VARIANT == "missing": doc.pop("audience")
        elif VARIANT == "Client": doc["audience"] = "Client"
        elif VARIANT == "weekly": doc["audience"] = "weekly"
        elif VARIANT == "distributed": doc["audience"] = "distributed"
        elif VARIANT == "none": doc["audience"] = None
        if VARIANT == "file":
            # ask creaite's way: save a clean client draft, then edit the file in system/staging/drafts/ directly
            next(x for x in doc["sections"] if x["id"] == "free_x")["text"] = "Plain words."
            sv = self.post("/api/report/save", {"doc": doc, "base_version": r["version"]})
            print("### save (control, audience client):", sv.get("ok"), "removed:", sv.get("removed"))
            draft_file = self.v.root / sv["path"]
            import creaite_doc
            d = creaite_doc.read(draft_file)
            for s in d["sections"]:
                if s["id"] == "free_x":
                    s["text"] = payload
            d["sections"].append({"id": "free_int", "type": "freetext", "heading": "Vendor notes", "default_heading": "",
                                  "hidden": False, "text": "INTERNAL walrus words.", "audience": "internal"}) if not any(
                s["id"] == "free_int" for s in d["sections"]) else None
            txt = creaite_doc.dumps(d, keep_text=True)
            import os
            aud = os.environ.get("AUD", "internal")
            rep = {"internal": '"audience": "internal"', "missing": '"audience_x": "client"', "list": '"audience": ["client"]',
                   "dup": '"audience": "client", "audience": "internal"', "kindsp": '"audience": "internal"', "kindweekly": '"audience": "internal"', "kindweeklyc": '"audience": "client"', "kindmin": '"audience": "internal"', "kwc": '"audience": "internal"'}[aud]
            assert '"audience": "client"' in txt
            txt = txt.replace('"audience": "client"', rep, 1)
            if aud in ("kindweekly", "kindweeklyc"): txt = txt.replace('"kind": "client"', '"kind": "weekly"', 1)
            if aud == "kwc":
                import re as _re
                txt = txt.replace('"kind": "client"', '"kind": "weekly"', 1)
                print("### DBG client in block:", _re.findall(r'"client": [^,]*', txt)[:2])
                txt = txt.replace('"client": null', '"client": "Example Client Ltd"', 1)
            if aud == "kindmin": txt = txt.replace('"kind": "client"', '"kind": "minutes"', 1)
            if aud == "kindsp": txt = txt.replace('"kind": "client"', '"kind": "Client"', 1)
            draft_file.write_text(txt, encoding="utf-8")   # a plain Write of the file
            print("### draft file now audience:", creaite_doc.read(draft_file).get("audience"), "| holds payload:",
                  hid in draft_file.read_text())
        else:
            sv = self.post("/api/report/save", {"doc": doc, "base_version": r["version"]})
            print("### save:", sv.get("ok"), str(sv.get("message"))[:120], "removed:", sv.get("removed"))
        d2 = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        print("### draft route: audience", d2["doc"].get("audience"), "findings", len(d2.get("findings") or []),
              "| stored text holds", [n for n in needles if n.lower() in json.dumps(d2["doc"]).lower()])
        if draft_file is not None:
            import creaite_doc, report_doc, paths
            dd = creaite_doc.read(draft_file)
            print("### DBG kind", dd.get("kind"), "client", dd.get("client"), "draft", draft_file.name,
                  "dp", report_doc.draft_path("client", dd["project"], dd["date"], dd.get("client")))
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        print("### approve:", a.get("ok"), str(a.get("message"))[:160].replace("\n", " "))
        if a.get("ok"):
            print("### filed holds:", self.scan(a["path"], needles))
        for fmt in ("html", "docx", "pdf"):
            e = self.export(fmt, "client", on_clash="number")
            print(f"### export {fmt}:", e.get("ok"), (e.get("path") or str(e.get("message"))[:140]),
                  "findings:", len(e.get("findings") or []))
            if e.get("ok"):
                print(f"###   {fmt} file holds:", self.scan(e["path"], needles))


if __name__ == "__main__":
    unittest.main(argv=["x", "P.test_e2e"], verbosity=0)
