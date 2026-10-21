"""Reviewer repros on v2.4.1 (c91cd53d). python3 -I repro_v241.py <checkout>. Fictional data only.
Every row should say a refusal or 'dropped' for the CLIENT file."""
import sys, base64, struct
from pathlib import Path
T = Path(sys.argv.pop(1)) / "dev" / "tests"
sys.path.insert(0, str(T))
import unittest
from test_export_page import LeakFix, page  # noqa
W = "Walrus budget cut"
SVG = f'<svg xmlns="http://www.w3.org/2000/svg"><text x="1" y="9">{W}</text></svg>'
b64 = base64.b64encode(SVG.encode()).decode()
MARK = b64[10:50]
# a 1x1 GIF with a comment extension holding the hidden title
GIF = (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff" + b"\x21\xfe" + bytes([len(W)]) + W.encode() + b"\x00"
       + b"\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b")
GIF64 = base64.b64encode(GIF).decode()
GMARK = base64.b64encode(GIF[12:40]).decode()[4:30]


class Atk(LeakFix):
    def chk(self, label, pg, marks=(MARK, "beacon.example")):
        if not hasattr(self, "_b"):
            self._b = (("internal", self.saved(date="2026-10-09")), ("client", self.client()))
        res = {}
        for kind, path in self._b:
            out, why = self.build(path, pg)
            body = (out or "")
            kept = out is not None and any(m in body for m in marks)
            res[kind] = why or ("KEPT (LEAK)" if kept else "dropped")
        print(f"\n### {label}: {res}", flush=True)

    def test_all(self):
        C = self.wrap
        self.chk("stylesheet ends in an unclosed url( to an outside address",
                 page(css='.page{color:#123} .page{background:url(https://beacon.example/a.png'))
        self.chk("stylesheet ends in an unclosed url(\" to an outside address",
                 page(css='.page{color:#123} .page{background:url("https://beacon.example/a.png'))
        self.chk("style attribute with an unclosed url(", page(C('<p style="background:url(https://beacon.example/a.png">x</p>')))
        self.chk("inline svg fill= SVG data address", page(C(f'<svg viewBox="0 0 9 9"><rect width="9" height="9" fill="url(data:image/svg+xml;base64,{b64}#p)"/></svg>')))
        self.chk("inline svg stroke= outside address", page(C('<svg viewBox="0 0 9 9"><rect width="9" height="9" stroke="url(https://beacon.example/a.svg#p)"/></svg>')))
        self.chk("img GIF with a comment extension", page(C(f'<img src="data:image/gif;base64,{GIF64}">')), marks=(GIF64[20:60],))
        self.chk("css GIF with a comment extension", page(css=f'.page{{background:url(data:image/gif;base64,{GIF64})}}'), marks=(GIF64[20:60],))


if __name__ == "__main__":
    unittest.main(argv=["x", "Atk.test_all"], verbosity=1)
