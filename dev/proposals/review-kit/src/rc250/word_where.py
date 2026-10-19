import sys, zipfile, tempfile, unittest, re
from pathlib import Path
ROOT = Path(sys.argv.pop(1))
sys.path.insert(0, str(ROOT / "dev" / "tests")); sys.path.insert(0, str(ROOT / "system" / "scripts"))
import test_report_text_section as T
import creaite_doc
FORMS = ['<p style="background:u\\72l(https://beacon.example/a.png)">x</p>', '![x](https://beacon.example/a.png)']
class P(T.Tmp):
    def test_all(self):
        for f in FORMS:
            d = self.doc(*T.base_sections(T.freetext(text=f"before\n\n{f}\n\nafter", audience="client")), kind="client", audience="client")
            out = Path(tempfile.mkdtemp()) / "x.docx"
            creaite_doc.word_export(d, out)
            z = zipfile.ZipFile(out)
            for n in z.namelist():
                b = z.read(n)
                for m in re.finditer(rb".{0,120}beacon\.example.{0,60}", b):
                    print(f, n, m.group(0)[:200])
if __name__ == "__main__":
    unittest.main(argv=["x", "P.test_all"], verbosity=0)
