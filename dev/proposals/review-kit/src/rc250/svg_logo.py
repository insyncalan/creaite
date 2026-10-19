"""Does an SVG logo's metadata (comment, desc, metadata, editor paths) reach the client HTML export? Fictional data only."""
import sys, base64, unittest
from pathlib import Path
ROOT = Path(sys.argv.pop(1))
sys.path.insert(0, str(ROOT / "dev" / "tests")); sys.path.insert(0, str(ROOT / "system" / "scripts"))
from test_export_page import LeakFix, page
import logo_check
SVG = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" '
       'sodipodi:docname="/Users/pat/Clients/Harbour/DROP-HARBOUR-Q3-pitch.svg" width="40" height="20">'
       '<!-- internal: pricing uplift 30 percent next renewal -->'
       '<title>Harbour exit plan draft</title><desc>Not for Harbour Board: renewal at risk</desc>'
       '<metadata><rdf>Author Pat Example, internal</rdf></metadata>'
       '<text x="0" y="10" opacity="0">margin squeeze</text><rect width="40" height="20" fill="#06c"/></svg>')
class A(LeakFix):
    def test_a(self):
        print("\n### logo_check accepts:", logo_check.inspect(SVG.encode()))
        uri = "data:image/svg+xml;base64," + base64.b64encode(SVG.encode()).decode()
        out, why = self.build(self.client(), page(self.wrap(f'<div class="wr-logos"><span class="wr-logo"><img src="{uri}"></span></div>')))
        kept = out is not None and uri[40:90] in out
        print("### client export:", why or "built", "| svg logo with its comment/desc/metadata kept in client file:", kept)
if __name__ == "__main__":
    unittest.main(argv=["x", "A.test_a"], verbosity=0)
