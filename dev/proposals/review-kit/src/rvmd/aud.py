import sys, json
from pathlib import Path
ROOT = Path(sys.argv.pop(1))
sys.path.insert(0, str(ROOT / "dev" / "tests")); sys.path.insert(0, str(ROOT / "system" / "scripts"))
import unittest
from test_report_exports import ABC, ITEMS, Base
from test_word_export_227 import png
import zipfile, docx_tools
def sizes(p):
    with zipfile.ZipFile(p) as z: return [list(docx_tools.image_size(z.read(n))) for n in z.namelist() if n.startswith("word/media/")]
class A(Base):
    def test(self):
        (self.v.root / ABC / "images").mkdir(parents=True, exist_ok=True)
        (self.v.root / ABC / "images" / "own.png").write_bytes(png(31, 17))
        secs = [{"id": "summary", "type": "text", "heading": "Summary", "default_heading": "Summary", "hidden": False, "text": "W.\n\n![a](images/own.png)"}]
        r = self.py("from pathlib import Path\nimport paths, report_doc, client_check\n"
                    f"doc = creaite_doc.new('client', 'ABC', 'Client report', '2026-10-16', {secs!r}, items={ITEMS!r}, audience='internal')\n"
                    "p = report_doc.draft_path('client','ABC','2026-10-16', None)\n"
                    "f = paths.resolve(p); f.parent.mkdir(parents=True, exist_ok=True); f.write_text(creaite_doc.dumps(doc), encoding='utf-8')\n"
                    "lo = client_check.left_out(creaite_doc.read(p))\n"
                    "out = creaite_doc.export(p, 'docx', file_beside=False, open_after=False)\n"
                    "print(json.dumps([str(p), lo.get('ready'), lo.get('findings'), out]))")
        print("\n###", r[:3], r[3].get("ok"), r[3].get("message"))
        if r[3].get("ok"):
            print("### sizes", sizes(self.v.root / r[3]["path"]))
if __name__ == "__main__":
    unittest.main(verbosity=1)
