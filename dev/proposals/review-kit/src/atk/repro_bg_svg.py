"""Repro: a hidden item's title reaches a client file through a CSS background picture.
Run from a checkout of the branch under test:
  python3 -I repro_bg_svg.py <checkout>
Fictional data only (the test fixture's demo vault)."""
import sys, base64, urllib.parse, unittest
from pathlib import Path
T = Path(sys.argv.pop(1)) / "dev" / "tests"
sys.path.insert(0, str(T))
from test_export_page import LeakFix, page  # noqa
W = "Walrus budget cut"
SVG = f'<svg xmlns="http://www.w3.org/2000/svg"><text x="1" y="9">{W}</text></svg>'
B64 = "data:image/svg+xml;base64," + base64.b64encode(SVG.encode()).decode()
PCT = "data:image/svg+xml," + urllib.parse.quote(SVG)

class Atk(LeakFix):
    def chk(self, label, pg):
        res = {}
        if not hasattr(self, "_b"):
            self._b = (("internal", self.saved(date="2026-10-09")), ("client", self.client()))
        for kind, path in self._b:
            out, why = self.build(path, pg)
            kept = out is not None and (B64[30:60] in out or PCT[25:60] in out)
            res[kind] = why or ("KEPT (LEAK: picture with the hidden title is in the file)" if kept else "dropped")
        print(f"\n### {label}: {res}", flush=True)

    def test_all(self):
        C = self.wrap
        self.chk("style attr, base64", page(C(f'<p style="background:url({B64})">x</p>')))
        self.chk("style attr, percent", page(C(f"<p style=\"background:url('{PCT}')\">x</p>")))
        self.chk("stylesheet, base64", page(css=f".page{{background:url({B64})}}"))
        self.chk("stylesheet, percent", page(css=f'.page{{background:url("{PCT}")}}'))

if __name__ == "__main__":
    unittest.main(argv=["x", "Atk.test_all"], verbosity=1)
