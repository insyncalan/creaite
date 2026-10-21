"""Attacks on v240-leak2 export_page client CSS. python3 -I repro_imageset.py <checkout>. Fictional data only."""
import sys, base64, urllib.parse, unittest
from pathlib import Path
T = Path(sys.argv.pop(1)) / "dev" / "tests"
sys.path.insert(0, str(T))
from test_export_page import LeakFix, page  # noqa
W = "Walrus budget cut"
SVG = f'<svg xmlns="http://www.w3.org/2000/svg"><text x="1" y="9">{W}</text></svg>'
b64 = base64.b64encode(SVG.encode()).decode()
MARK = b64[10:50]
class Atk(LeakFix):
    def chk(self, label, pg):
        res = {}
        if not hasattr(self, "_b"):
            self._b = (("internal", self.saved(date="2026-10-09")), ("client", self.client()))
        for kind, path in self._b:
            out, why = self.build(path, pg)
            kept = out is not None and (MARK in out or "beacon.example" in out)
            res[kind] = why or ("KEPT (LEAK)" if kept else "dropped")
        print(f"\n### {label}: {res}", flush=True)
    def test_all(self):
        C = self.wrap
        sp = "data: image/svg+xml;base64," + b64
        tab = r"data:ima\9 ge/svg+xml;base64," + b64
        self.chk("css image-set string, space after data:", page(css=f'.page{{background-image:image-set("{sp}" 1x)}}'))
        self.chk("css image-set string, \\9 tab escape", page(css=f'.page{{background-image:image-set("{tab}" 1x)}}'))
        self.chk("style attr image-set, space", page(C(f"<p style='background-image:image-set(\"{sp}\" 1x)'>x</p>")))
        self.chk("css image-set external", page(css='.page{background-image:image-set("https://beacon.example/a.png" 1x)}'))
        self.chk("css u\\72l external", page(css=r'.page{background:u\72l(https://beacon.example/a.png)}'))
        self.chk("css url( tab escape quoted", page(css=f'.page{{background:url("{tab}")}}'))
        self.chk("css -webkit-image-set space", page(css=f'.page{{background-image:-webkit-image-set("{sp}" 1x)}}'))
        self.chk("img src space", page(C(f'<img src="{sp}">')))
if __name__ == "__main__":
    unittest.main(argv=["x", "Atk.test_all"], verbosity=1)
