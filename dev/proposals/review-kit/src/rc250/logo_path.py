"""Does a client report's Word export take a header logo from any path the saved doc names? Fictional data only."""
import sys, zipfile, tempfile, unittest, hashlib
from pathlib import Path
ROOT = Path(sys.argv.pop(1))
sys.path.insert(0, str(ROOT / "dev" / "tests")); sys.path.insert(0, str(ROOT / "system" / "scripts"))
import test_report_text_section as T
import creaite_doc
class P(T.Tmp):
    def test_all(self):
        secret = self.tmp / "outside" / "internal-screenshot.png"
        secret.parent.mkdir()
        img = T.png(30, 12, (200, 0, 0, 255))
        secret.write_bytes(img)
        hdr = {"id": "header", "type": "header", "heading": "", "hidden": False, "text": "",
               "data": {"label": "Client report", "week_ending": "2026-10-16", "client": "Northwind",
                        "logos": [{"kind": "partner:acme", "path": str(secret)}]}}
        d = self.doc(hdr, *T.base_sections(), kind="client", audience="client")
        out = Path(tempfile.mkdtemp()) / "x.docx"
        creaite_doc.word_export(d, out)
        z = zipfile.ZipFile(out)
        media = [n for n in z.namelist() if n.startswith("word/media/")]
        h = hashlib.sha1(img).hexdigest()
        hits = [n for n in media if hashlib.sha1(z.read(n)).hexdigest() == h or len(z.read(n)) == len(img)]
        print("\n### media:", media, "| arbitrary path embedded:", bool(hits) or [len(z.read(n)) for n in media])
        import re
        x = z.read("word/document.xml").decode()
        print("### docPr names:", re.findall(r'<wp:docPr[^>]*>', x)[:5], re.findall(r'<pic:cNvPr[^>]*>', x)[:5])
        print("### html render has secret path:", str(secret) in creaite_doc.render(d, editing=False))
if __name__ == "__main__":
    unittest.main(argv=["x", "P.test_all"], verbosity=0)
