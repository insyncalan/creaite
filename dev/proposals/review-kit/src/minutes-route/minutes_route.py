"""Kit probe (written for the #239 review, rule 15): a client report's file must never be opened or exported as MINUTES.
A throwaway vault, fictional data. Saves a clean client draft, then edits the FILE on disk (kind -> minutes, audience internal, payload
naming a hidden item) in the places a client report lives (the draft in system/staging/drafts, the filed report in Reports, the filed
report under a neutral name in Reports, and under its client file name in another folder), and calls /api/minutes/export (html, docx)
and, for the draft, the minutes record route. Every call must be REFUSED; an export that is made and holds a needle is a LEAK.
Usage: python minutes_route.py <tree root>"""
import sys, json, zipfile, sqlite3, html, re, unittest, shutil
from pathlib import Path
ROOT = Path(sys.argv.pop(1))
sys.path.insert(0, str(ROOT / "dev" / "tests")); sys.path.insert(0, str(ROOT / "system" / "scripts"))
import test_report_export_save as S

WEEK = "2026-10-09"
BLOCK = re.compile(r'(<script type="application/json" id="creaite-data">)(.*?)(</script>)', re.S)


def enc(d):
    return json.dumps(d, ensure_ascii=False, indent=1).replace("<", "\\u003c")


class P(S.ExportSave):
    def hidden(self):
        con = sqlite3.connect(self.v.root / "system/tracker.db"); con.row_factory = sqlite3.Row
        return dict(con.execute("SELECT id, description, owner FROM actions WHERE client_visible=0 AND project='ABC' AND owner<>'' LIMIT 1").fetchone())

    def scan(self, path, needles):
        p = self.v.root / path
        b = p.read_bytes()
        if p.suffix == ".docx":
            with zipfile.ZipFile(p) as z:
                b = b"".join(z.read(n) for n in z.namelist() if n.endswith(".xml") or n.endswith(".rels"))
        t = html.unescape(b.decode("utf-8", "ignore")).lower()
        return [n for n in needles if n.lower() in t]

    def dirty_text(self, f, h):
        """The file's text with kind minutes, audience internal and the payload in a new text section."""
        text = f.read_text(encoding="utf-8")
        mo = BLOCK.search(text)
        d = json.loads(mo.group(2))
        d["kind"] = "minutes"; d["audience"] = "internal"
        pay = f"{h['owner']} owns {h['id']}: {h['description']}. This is confidential. Internal only: keep."
        d["sections"].append({"id": "free_x", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": False,
                              "text": pay, "audience": "client"})
        d.setdefault("layout", {})["order"] = [s["id"] for s in d["sections"]]
        return text[:mo.start(2)] + enc(d) + text[mo.end(2):]

    def attempt(self, label, rel, needles, versions=("internal", "distributed")):
        leaked = []; refused = 0; made = 0
        for ver in versions:
            for fmt in ("html", "docx"):
                try:
                    r = self.post("/api/minutes/export", {"path": rel, "format": fmt, "file_beside": True, "version": ver})
                except Exception as e:   # noqa
                    r = {"ok": False, "message": "HTTP-EXC " + repr(e)[:50]}
                if r.get("ok") and r.get("path"):
                    made += 1
                    hh = self.scan(r["path"], needles)
                    if hh:
                        leaked.append((ver, fmt, hh))
                else:
                    refused += 1
        print(f"### {label}: exports made={made} refused={refused} | " + ("LEAK " + json.dumps(leaked) if leaked else "clean"), flush=True)
        return made, leaked

    def test_minutes(self):
        self.client()
        h = self.hidden()
        needles = [h["id"], h["description"], h["owner"], "confidential", "Internal only"]
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fresh": True})
        sv = self.post("/api/report/save", {"doc": r["doc"]})
        draft = self.v.root / sv["path"]
        before = {p for p in self.v.root.rglob("*") if p.is_file()}
        print("### clean draft saved:", sv.get("ok"), draft.name, flush=True)
        # 1: the draft (client file name, staging drafts folder), kind -> minutes
        draft.write_text(self.dirty_text(draft, h), encoding="utf-8")
        self.attempt("draft in system/staging/drafts, kind=minutes", sv["path"], needles)
        rec = self.post("/api/minutes/followup", {"path": sv["path"], "version": "internal"})
        print(f"### followup on the draft: ok={rec.get('ok')} {str(rec.get('message'))[:80]!r}", flush=True)
        # 2: a clean approve, then the filed report edited the same way
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fresh": True})
        self.post("/api/report/save", {"doc": r["doc"]})
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        print("### clean approve:", a.get("ok"), str(a.get("path"))[-70:], flush=True)
        if not a.get("ok"):
            return
        filed = self.v.root / a["path"]
        dirty = self.dirty_text(filed, h)
        filed.write_text(dirty, encoding="utf-8")
        self.attempt("filed client report in Reports, kind=minutes", a["path"], needles)
        neutral = filed.with_name("2026-10-09 Project notes.html")
        neutral.write_text(dirty, encoding="utf-8")
        self.attempt("filed copy under a neutral name in Reports, kind=minutes", str(neutral.relative_to(self.v.root)), needles)
        other = self.v.root / "inbox"; other.mkdir(exist_ok=True)
        moved = other / filed.name
        moved.write_text(dirty, encoding="utf-8")
        self.attempt("client file name in inbox/, kind=minutes", str(moved.relative_to(self.v.root)), needles)
        mine = {filed, neutral, moved, draft}
        stray = [str(p.relative_to(self.v.root.resolve() if False else self.v.root))[:60] for p in self.v.root.rglob("*")
                 if p.is_file() and p.suffix in (".html", ".docx", ".pdf") and "system" not in p.relative_to(self.v.root).parts and p not in before and p not in mine
                 and self.scan(str(p.relative_to(self.v.root)), needles)]
        print("### new files holding needles:", stray, flush=True)


if __name__ == "__main__":
    unittest.main(argv=["x", "P.test_minutes"], verbosity=0)
