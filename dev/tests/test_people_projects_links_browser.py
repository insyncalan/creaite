"""#224: on the People page the project names in the Projects column read as links (link colour, the table's text size, weight 500).

Run: python3 dev/tests/test_people_projects_links_browser.py   (needs Google Chrome; skipped otherwise), at 1400 px.
Light and dark, creaite and Brightwater: colour is the link colour (not the muted one), size is the table's body size, weight 500,
contrast at least 4.5:1; the other columns' computed styles are the ones the cell had before; a click opens the project's page.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from handchecks import measure  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

PROBE = """(()=>{
  const q=s=>[...document.querySelectorAll(s)], cs=e=>getComputedStyle(e);
  const probe=document.createElement('span'); probe.style.color='var(--accent)'; document.body.appendChild(probe);
  const link=cs(probe).color, muted=(probe.style.color='var(--muted)', cs(probe).color); probe.remove();
  const links=q('#peopleTbl td .pcode.plink'), tds=q('#peopleTbl tbody tr:first-child td');
  return {n:links.length, link, muted, body:cs(q('#peopleTbl tbody td')[1]).fontSize,
    links:links.map(e=>({color:cs(e).color, size:cs(e).fontSize, weight:cs(e).fontWeight, text:e.textContent})),
    others:tds.slice(0,3).map(td=>{const s=cs(td); return [s.fontSize,s.fontWeight,s.color]})}})()"""


class PeopleProjectLinks(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        from test_dashboard import populate
        populate(v)

    def test_projects_column_links(self):
        b = self.b
        b.eval("go('people')")
        b.wait("document.querySelectorAll('#peopleTbl td .pcode.plink').length>0", 15)
        base = None
        for palette in ("creaite", "Brightwater"):
            for mode in ("light", "dark"):
                measure.theme(b, palette, mode)
                r = b.eval(PROBE)
                tag = (palette, mode)
                self.assertGreater(r["n"], 0, tag)
                self.assertNotEqual(r["link"], r["muted"], tag)
                for l in r["links"]:
                    self.assertEqual(l["color"], r["link"], (tag, l))              # the link colour, not the muted one
                    self.assertEqual(l["size"], r["body"], (tag, l))               # the table's body size
                    self.assertEqual(l["weight"], "500", (tag, l))
                for row in measure.contrast(b, "#peopleTbl td .pcode.plink"):
                    self.assertGreaterEqual(row["ratio"], 4.5, (tag, row))
                if palette == "creaite" and mode == "light":
                    base = r["others"]
                self.assertEqual([x[:2] for x in r["others"]], [x[:2] for x in base], tag)   # other columns: size and weight unchanged
        measure.theme(b, "creaite", "light")
        code = b.eval("document.querySelector('#peopleTbl .pcode.plink').dataset.proj")
        b.click("#peopleTbl .pcode.plink")
        b.wait("location.hash.indexOf('cockpit=')>=0", 10)
        self.assertEqual(b.eval("location.hash.indexOf(%s)>=0" % json.dumps(code)), True)


if __name__ == "__main__":
    unittest.main()
