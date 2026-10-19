"""Does a typical 20-60 kB logo survive the posted-page export (client and internal)? Fictional."""
import sys, base64, re, os, struct, zlib, unittest
from pathlib import Path
ROOT = Path(sys.argv.pop(1))
sys.path.insert(0, str(ROOT / "dev" / "tests")); sys.path.insert(0, str(ROOT / "system" / "scripts"))
from test_export_page import SvgLogoClean, page
def png(w, h):
    def chunk(k, b): return struct.pack(">I", len(b)) + k + b + struct.pack(">I", zlib.crc32(k + b) & 0xFFFFFFFF)
    rows = b"".join(b"\x00" + os.urandom(4 * w) for _ in range(h))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")
SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="100" viewBox="0 0 400 100">' + "".join(
    f'<path d="M{i} {i%90} l3 4 l-2 5 z" fill="#0{i%9}c"/>' for i in range(150)) + '</svg>'
class C(SvgLogoClean):
    def test_cap(self): self.run_for("client")
    def test_int(self): self.run_for("internal")
    def run_for(self, which):
        for name, mime, raw in (("svg", "image/svg+xml", SVG.encode()),):
            uri = f"data:{mime};base64," + base64.b64encode(raw).decode()
            for who, doc in [(which, self.client() if which == "client" else self.saved())]:
                out, why = self.build(doc, page(self.wrap(f'<div class="wr-logos"><span class="wr-logo"><img src="{uri}"></span></div>')))
                body = (out or "").split("</style>", 2)[-1]
                srcs = re.findall(r'<img src="([^"]*)"', body)
                ok = []
                for s in srcs:
                    try: base64.b64decode(s.split(",", 1)[1], validate=True); ok.append(len(s))
                    except Exception: ok.append(f"BROKEN len={len(s)}")
                print(f"\n### {name} ({len(uri)} chars) {who}: {why or 'built'} img srcs {ok}")
if __name__ == "__main__":
    unittest.main(argv=["x", "C.test_cap", "C.test_int"], verbosity=0)
