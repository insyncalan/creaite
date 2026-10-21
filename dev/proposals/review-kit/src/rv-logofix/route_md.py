"""E2E on the live server (throwaway vault): a client draft saved through /api/report/save with a Markdown picture line naming
a file outside the vault, then exported as Word via /api/report/export. Also: a foreign logo path through save. Fictional data."""
import sys, json, zipfile, tempfile, shutil, unittest
from pathlib import Path
ROOT = Path(sys.argv.pop(1))
sys.path.insert(0, str(ROOT / "dev" / "tests")); sys.path.insert(0, str(ROOT / "system" / "scripts"))
import test_report_export_save as S
import docx_tools
from test_report_exports import tiny_png

class P(S.ExportSave):
    def test_e2e(self):
        out = Path(tempfile.mkdtemp(prefix="e2e-")); self.addCleanup(shutil.rmtree, out, True)
        (out / "secret.png").write_bytes(tiny_png(77, 13))
        self.client()
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09"})
        doc = r["doc"]
        print("\n### sections:", [(s["id"], s["type"], s.get("hidden")) for s in doc["sections"]])
        hits = []
        for s in doc["sections"]:
            if s.get("hidden"): continue
            if s["type"] == "panes" and s.get("panes"):
                s["panes"][0]["text"] = (s["panes"][0].get("text") or "") + f"\n\n![p]({out}/secret.png)"; hits.append(s["id"])
            elif s["type"] in ("health", "text", "table", "timeline"):
                s["text"] = (s.get("text") or "Plain words.") + f"\n\n![t]({out}/secret.png)"; hits.append(s["id"])
            if s["type"] == "header":
                s.setdefault("data", {})["logos"] = [{"kind": "firm", "path": str(out / "secret.png")},
                                                     {"kind": "partner:zzz", "path": str(out / "secret.png")}]
        print("### planted in:", hits)
        sv = self.post("/api/report/save", {"doc": doc, "base_version": r["version"]})
        print("### save ok:", sv.get("ok"), sv.get("message"), "removed:", sv.get("removed"))
        d2 = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09"})["doc"]
        print("### stored logos:", [s.get("data", {}).get("logos") for s in d2["sections"] if s["type"] == "header"])
        print("### path still in saved text:", str(out) in json.dumps(d2))
        e = self.export("docx", "client")
        print("### export:", e.get("ok"), e.get("message"), (e.get("findings") or [])[:4])
        if e.get("ok"):
            z = zipfile.ZipFile(self.v.root / e["path"])
            sizes = [tuple(docx_tools.image_size(z.read(n))) for n in z.namelist() if n.startswith("word/media/")]
            print("### media:", sizes, "| OUTSIDE FILE EMBEDDED:", (77, 13) in sizes)
if __name__ == "__main__":
    unittest.main(argv=["x", "P.test_e2e"], verbosity=0)
