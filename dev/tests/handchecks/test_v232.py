"""creaite 2.3.2's hand checks (dev/handchecks/v2.3.2.md), automated against a vault made from the release zip.

Run them all, fill the Results table and make the screenshot sheet:  python3 dev/tools/handcheck.py v2.3.2
Run this file on its own (it makes the vault itself):                 python3 dev/tests/handchecks/test_v232.py

One method per check, `test_cNN_…`, its docstring quoting the check. One class per group, so the groups can be written in
parallel without touching the same lines.
  TodayDefects   1, 2   the shared vault, nothing changed on disk (a hover card; a column width kept in the browser only)
  RailMore       3      a vault of its own: the check turns Labels when collapsed off and on in Customise sidebar
All three are scriptable in real Chrome; none is live only. Desktop (1400 px) only.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hcbase import NOTES, HandcheckCase  # noqa: E402,F401  (NOTES: read by handcheck.py)

KIND = {1: "scriptable", 2: "scriptable", 3: "scriptable"}

LIVE_ONLY = {}

PF = "#pfTbl"
EVID = f'{PF} th[data-col="evidence"]'


class TodayDefects(HandcheckCase):
    """Checks 1 and 2: Today's hover card, and the Portfolio table's Evidence column."""

    # ── helpers ──

    def mouse(self, x, y):
        self.b.call("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y, button="none")

    def drag(self, col, dx):
        """Drag a Portfolio column's resize handle by `dx` px with real mouse events, in steps of ten."""
        b = self.b
        h = b.box(f'{PF} th[data-col="{col}"] .colrz')
        self.assertTrue(h, f"the {col} column has a resize handle")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=h["x"], y=h["y"])
        b.call("Input.dispatchMouseEvent", type="mousePressed", x=h["x"], y=h["y"], button="left", buttons=1, clickCount=1)
        step = 10 if dx > 0 else -10
        for i in range(1, abs(dx) // 10 + 1):
            b.call("Input.dispatchMouseEvent", type="mouseMoved", x=h["x"] + step * i, y=h["y"], button="left", buttons=1)
        b.call("Input.dispatchMouseEvent", type="mouseReleased", x=h["x"] + dx, y=h["y"], button="left", buttons=0, clickCount=1)
        b.pump(0.2)

    def evidence(self, row):
        """The Evidence column's width and, for `row`'s Evidence text: its height, how far it overhangs the cell, its white-space."""
        return self.b.eval(f"""(()=>{{ const e=document.querySelector({json.dumps(row)}+' .ev'), td=e.closest('td'), th=document.querySelector('{EVID}');
          const r=e.getBoundingClientRect(), t=th.getBoundingClientRect();
          return {{w:t.width, h:r.height, over:Math.max(e.scrollWidth-td.clientWidth, r.right-t.right), ws:getComputedStyle(e).whiteSpace,
                  text:e.textContent.length}}; }})()""")

    # ── the checks ──

    def test_c01_no_hover_card_left_open_after_prep_and_back(self):
        """1. Hover a meeting on Today, choose Prep, then go back to Today → no hover card, peek or popup is left open, and no
        refresh is needed."""
        b = self.b
        b.eval("go('today')")
        b.wait("document.querySelectorAll('#dayMeets .dmti').length>0", 15)
        b.pump(0.3)
        leftover = "document.querySelectorAll('.dmpop, .prpeek, .tip, [role=dialog][open]').length"
        self.assertEqual(b.eval(leftover), 0, "nothing open before the hover")
        c = b.box("#dayMeets .dmti")
        self.assertTrue(c, "today's meeting title is on the day line")
        self.mouse(c["x"] - 40, c["y"] - 40)
        self.mouse(c["x"], c["y"])
        b.wait("document.querySelector('#dayMeets .dmpop')", 10)          # the hover card (the peek) is open
        b.click("#dayMeets .dmpop .btn.primary")                           # Open the prep page
        b.wait("location.hash.startsWith('#prep=')||decodeURIComponent(location.hash).startsWith('#prep=')", 10)
        b.pump(0.5)
        b.eval("history.back()")                                           # back to Today, as the browser's Back does
        b.wait("!location.hash.startsWith('#prep=')", 10)
        b.eval("go('today')")                                              # (Back from the prep page lands here too)
        b.wait("document.querySelectorAll('#dayMeets .dmti').length>0 && !document.getElementById('v-today').hidden", 15)
        self.mouse(5, 5)                                                   # the pointer is away from every trigger
        b.pump(1.0)                                                        # longer than the close delay
        self.assertEqual(b.eval(leftover), 0, "no hover card, peek, tooltip or dialog is left open, and the page was not refreshed")
        self.assertEqual(b.errors, [], "page errors")
        self.note(1, "hovered today's FAL Steering committee, chose Open the prep page, Back to Today: no .dmpop, .prpeek, .tip or open dialog")

    def test_c02_evidence_column_follows_its_width_and_keeps_it(self):
        """2. On Today's Portfolio table, drag the Evidence column wider and narrower → its text wraps to the new width, and the
        width is kept after a reload."""
        b = self.b
        b.eval("go('today')")
        b.wait(f"document.querySelector('{PF} tr[data-cock]')", 15)
        b.pump(0.3)
        row = b.eval(f"""(()=>{{ const r=[...document.querySelectorAll('{PF} tr[data-cock]')].filter(x=>x.querySelector('.ev'))
            .sort((a,c)=>c.querySelector('.ev').textContent.length-a.querySelector('.ev').textContent.length)[0];
          return r&&('{PF} tr[data-cock="'+r.dataset.cock+'"]'); }})()""")
        self.assertTrue(row, "a project row has Evidence text")
        start = b.eval(f"document.querySelector('{EVID}').getBoundingClientRect().width")
        self.drag("evidence", -max(40, int((start - 140) // 10 * 10)))     # narrower, to about 140 px (the header text stops a narrower one)
        n = self.evidence(row)
        self.assertNotEqual(n["ws"], "nowrap", f"the text is not held to one line {n}")
        self.assertLessEqual(n["over"], 1, f"narrow: the text is not clipped or overhanging {n}")
        saved = b.eval("JSON.parse(localStorage.getItem('creaite-colwidths')||'{}')['portfolio|evidence']")
        self.assertAlmostEqual(saved, n["w"], delta=6, msg="the narrow width is remembered")
        self.drag("evidence", 400)                                         # wider
        w = self.evidence(row)
        self.assertGreater(w["w"], n["w"] + 200, "the column grew")
        self.assertLessEqual(w["over"], 1, f"wide: the text is not overhanging {w}")
        self.assertLess(w["h"], n["h"], f"wider: the text takes fewer lines (narrow {n['h']:.0f} px, wide {w['h']:.0f} px)")
        saved = b.eval("JSON.parse(localStorage.getItem('creaite-colwidths')||'{}')['portfolio|evidence']")
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('today')")
        b.wait(f"document.querySelector({json.dumps(row)})", 15)
        b.pump(0.3)
        r = self.evidence(row)
        self.assertAlmostEqual(r["w"], saved, delta=2, msg="the width is kept after a reload")
        self.assertEqual(r["ws"], "normal", "and the text still wraps")
        b.eval("localStorage.removeItem('creaite-colwidths')")            # leave the browser as found
        self.assertEqual(b.errors, [], "page errors")
        self.note(2, f"narrow {n['w']:.0f} px = {n['h']:.0f} px of text, wide {w['w']:.0f} px = {w['h']:.0f} px; {r['w']:.0f} px after a reload")


class RailMore(HandcheckCase):
    """Check 3: the rail's More menu. A vault of its own, as the check turns Labels when collapsed off and on."""
    own_vault = True

    def settings(self):
        return json.loads((self.vault / "system/config/settings.json").read_text(encoding="utf-8"))

    def rail_w(self):
        return self.b.eval("Math.round(document.querySelector('.rail').getBoundingClientRect().width)")

    def wait_w(self, w):
        self.b.wait(f"Math.round(document.querySelector('.rail').getBoundingClientRect().width)==={w}", 5)

    def open_more(self):
        b = self.b
        b.click("#railMore")
        b.wait("!document.getElementById('railMoreMenu').hidden", 5)

    def test_c03_more_menu_without_the_duplicate(self):
        """3. Open the rail's More menu → it does not list "Labels when collapsed"; Customise sidebar still has it and it still
        works."""
        b = self.b
        b.eval("go('today')")
        b.wait("document.getElementById('railMore')", 15)
        self.open_more()
        items = b.eval("[...document.querySelectorAll('#railMoreMenu [role^=menuitem]')].map(x=>x.textContent.trim())")
        self.assertTrue(items, "the More menu lists its pages")
        self.assertFalse([x for x in items if "Labels when collapsed" in x], f"More lists Labels when collapsed: {items}")
        self.assertNotIn("Labels when collapsed", b.eval("document.getElementById('railMoreMenu').textContent"))
        self.assertFalse(b.eval("!!document.getElementById('railLabelsSw')"), "no switch for it in More")
        self.assertTrue([x for x in items if x.startswith("Customise sidebar")], f"Customise sidebar is still in More: {items}")
        # Customise sidebar still has it, on, and it works: collapsed, the labels go (56 px) and come back (76 px)
        b.click("#railCustBtn")
        b.wait("document.getElementById('railCust').open", 5)
        self.assertIn("Labels when collapsed", b.eval("document.getElementById('railCust').textContent"))
        self.assertTrue(b.eval("document.getElementById('railCustLabels').checked"), "on by default")
        b.click("#railCustDone")
        b.wait("!document.getElementById('railCust').open", 5)
        if self.rail_w() > 100:
            b.click("#railTog")
            self.wait_w(76)                                                # collapsed, with labels under the icons
        self.open_more()
        b.click("#railCustBtn")
        b.wait("document.getElementById('railCust').open", 5)
        b.click("#railCustLabels")                                         # off
        b.click("#railCustDone")
        b.wait("!document.getElementById('railCust').open", 5)
        self.wait_w(56)                                                    # icons only
        self.assertFalse(self.settings()["dashboard"]["rail_labels"], "saved off")
        self.open_more()
        b.click("#railCustBtn")
        b.wait("document.getElementById('railCust').open", 5)
        self.assertFalse(b.eval("document.getElementById('railCustLabels').checked"))
        b.click("#railCustLabels")                                         # on again
        b.click("#railCustDone")
        b.wait("!document.getElementById('railCust').open", 5)
        self.wait_w(76)
        self.assertTrue(self.settings()["dashboard"]["rail_labels"], "saved on again")
        self.assertEqual(b.errors, [], "page errors")
        self.note(3, "More lists no Labels when collapsed; Customise sidebar has it: off → 56 px rail and saved, on → 76 px and saved")


if __name__ == "__main__":
    unittest.main()
