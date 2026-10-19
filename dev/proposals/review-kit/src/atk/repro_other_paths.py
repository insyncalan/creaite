"""Other client-output paths (filed client page, HTML export, Word) for the image-set / escaped-url / data-svg forms.
python3 -I repro_other_paths.py <checkout>. Fictional data only."""
import sys, base64, json, zipfile, tempfile, unittest
from pathlib import Path
ROOT = Path(sys.argv.pop(1))
sys.path.insert(0, str(ROOT / "dev" / "tests")); sys.path.insert(0, str(ROOT / "system" / "scripts"))
import test_report_text_section as T  # noqa
import creaite_doc  # noqa
W = "Walrus budget cut"
SVG = f'<svg xmlns="http://www.w3.org/2000/svg"><text x="1" y="9">{W}</text></svg>'
B64 = base64.b64encode(SVG.encode()).decode()
FORMS = [
    f'<p style="background-image:image-set(\\"data: image/svg+xml;base64,{B64}\\" 1x)">x</p>',
    '<p style="background:u\\72l(https://beacon.example/a.png)">x</p>',
    '<style>.page{background-image:image-set("https://beacon.example/a.png" 1x)}</style>',
    f'<img src="data: image/svg+xml;base64,{B64}">',
    '![x](https://beacon.example/a.png)',
    '[y](https://beacon.example/click)',
]
BAD = ("<p style=", "<style>.page", "<img src=\"data:", "<img src=\"https://beacon", "url(", "<a href=\"https://beacon")
class P(T.Tmp):
    def test_all(self):
        for f in FORMS:
            d = self.doc(*T.base_sections(T.freetext(text=f"before\n\n{f}\n\nafter", audience="client")), kind="client", audience="client")
            page = creaite_doc.render(d, editing=False)
            body = page.split("</style>", 1)[-1]; hits = ([b for b in BAD if b in body] if "before" in body else "SECTION NOT RENDERED")
            out = Path(tempfile.mkdtemp()) / "x.docx"
            try:
                creaite_doc.word_export(d, out)
                z = zipfile.ZipFile(out); allb = b"".join(z.read(n) for n in z.namelist())
                wh = [b for b in ("<w:drawing", "beacon.example/a.png") if b.encode() in allb and "beacon" in f]
            except Exception as e:
                wh = f"word error {type(e).__name__}"
            print(f"\n### {f[:60]!r}: html-hits={hits} word-hits={wh}", flush=True)
if __name__ == "__main__":
    unittest.main(argv=["x", "P.test_all"], verbosity=0)
