"""v1.9.5 hand checks 8 and 19 (creaite-plan#81).

8: on the People page a sortable column heading is a button inside the columnheader. Enter sorts, and the table is drawn
   again; focus stays on the same heading's button (not <body>), so a screen reader reads the new aria-sort and Enter
   again reverses the order.
19: a toast is over everything: over an open menu (Work's More views, a .ddmenu.pop) as well as the peek and popovers.

Run: python3 dev/tests/test_focus_layers.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

HEAD = """(()=>{ const a=document.activeElement, th=a&&a.closest('#peopleTbl th[data-psort]');
  return [a?a.tagName:null, a?a.className:null, th?th.dataset.psort:null, th?th.getAttribute('aria-sort'):null,
    [...document.querySelectorAll('#peopleTbl tbody tr')].map(tr=>tr.cells[0].textContent.replace(/\\s+/g,' ').trim())]; })()"""


class FocusAndLayers(LiveBrowserCase):
    shared_server = True        # it only reads

    def setUp(self):
        super().setUp()
        self.b.call("Emulation.setFocusEmulationEnabled", enabled=True)

    def test_enter_on_a_people_heading_sorts_and_keeps_focus_on_it(self):
        b = self.b
        b.eval("go('people')")
        b.wait("document.querySelectorAll('#peopleTbl th[data-psort] button.thsort').length>1")
        b.eval("document.querySelector('#peopleTbl th[data-psort=\"name\"] button.thsort').focus()")
        b.key("Tab")                                                     # Tab on to the next heading: Organisation
        tag, cls, col, sort0, rows0 = b.eval(HEAD)
        self.assertEqual((tag, cls, col, sort0), ("BUTTON", "thsort", "org", "none"))
        b.key("Enter")
        tag, cls, col, sort1, rows1 = b.eval(HEAD)
        self.assertEqual((tag, cls, col), ("BUTTON", "thsort", "org"))   # focus kept on the same heading, not <body>
        self.assertEqual(sort1, "ascending")
        b.key("Enter")                                                   # Enter again reverses, focus still there
        tag, cls, col, sort2, rows2 = b.eval(HEAD)
        self.assertEqual((tag, cls, col, sort2), ("BUTTON", "thsort", "org", "descending"))
        self.assertEqual(len(rows1), len(rows2))
        self.assertTrue(len(rows1) < 2 or rows1 != rows2 or len(set(rows1)) == 1)

    def test_a_toast_is_over_an_open_menu(self):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr, #workTbl .empty') && document.getElementById('vmore')")
        b.click("#vmore")
        b.wait("document.querySelector('#vmoreMenu.pop') && getComputedStyle(document.getElementById('vmoreMenu')).display!=='none'")
        b.eval("snack('Saved ABC-A-001','Undo',()=>{})")
        b.wait("document.getElementById('snack').classList.contains('on')")
        hit = b.eval("""(()=>{ const s=document.getElementById('snack'), r=s.getBoundingClientRect(), m=document.getElementById('vmoreMenu');
          m.style.top=(r.top-40)+'px'; m.style.left=(r.left-20)+'px'; m.style.height=(r.height+80)+'px'; m.style.width=Math.min(r.width+40,340)+'px';  /* the open menu across the toast */
          const x=r.left+r.width/2, y=r.top+r.height/2, e=document.elementFromPoint(x,y);
          return [m.matches(':not([hidden])'), !!(e&&e.closest('#vmoreMenu')), !!(e&&e.closest('#snack'))]; })()""")
        self.assertEqual(hit, [True, False, True])


if __name__ == "__main__":
    unittest.main()
