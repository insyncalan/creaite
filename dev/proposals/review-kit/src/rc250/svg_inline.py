import sys, base64, unittest
from pathlib import Path
ROOT = Path(sys.argv.pop(1))
sys.path.insert(0, str(ROOT / "dev" / "tests")); sys.path.insert(0, str(ROOT / "system" / "scripts"))
from test_export_page import LeakFix, page
X = "https://beacon.example/a.png"
def u(s): return "data:image/svg+xml;base64," + base64.b64encode(s.encode()).decode()
F = {
 "inline use href ext": f'<svg viewBox="0 0 9 9"><use href="{X}#a"/></svg>',
 "inline use xlink:href": f'<svg viewBox="0 0 9 9" xmlns:xlink="http://www.w3.org/1999/xlink"><use xlink:href="{X}#a"/></svg>',
 "inline style elem": f'<svg viewBox="0 0 9 9"><style>rect{{fill:url({X})}}</style><rect width="9" height="9"/></svg>',
 "inline image elem": f'<svg viewBox="0 0 9 9"><image href="{X}"/></svg>',
 "inline fill url ext": f'<svg viewBox="0 0 9 9"><rect fill="url({X})" width="9" height="9"/></svg>',
 "inline style attr url": f'<svg viewBox="0 0 9 9"><rect style="fill:url({X})" width="9" height="9"/></svg>',
 "inline mask url ext": f'<svg viewBox="0 0 9 9"><rect mask="url({X}#m)" width="9" height="9"/></svg>',
 "img svg with use ext": f'<img src="{u(f"<svg xmlns=\'http://www.w3.org/2000/svg\'><use href=\'{X}#a\'/></svg>")}">',
 "img svg with style import": f'<img src="{u(f"<svg xmlns=\'http://www.w3.org/2000/svg\'><style>@import url({X});</style></svg>")}">',
}
class A(LeakFix):
    def test_a(self):
        c = self.client()
        for k, f in F.items():
            out, why = self.build(c, page(self.wrap(f)))
            print(f"### {k}: {why or ('KEPT beacon' if out and 'beacon.example' in out else 'built, beacon gone')}", flush=True)
if __name__ == "__main__":
    unittest.main(argv=["x", "A.test_a"], verbosity=0)
