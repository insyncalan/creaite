"""insyncalan/creaite-plan#85: a click is not lost while the page redraws its data.

Run: python3 dev/tests/test_lost_click.py   (needs Google Chrome; skipped otherwise)
A real mouse press on a Work row, then the list is redrawn (as a data refresh does, BL-327's boot refresh, BL-253's events),
then the real release. The browser sends the click to the nearest ancestor the two share when the pressed node has gone, so
the row's handler used to see no row and the click was lost. The click must act on the row by its key (data-row).
Also: a plain click still selects once, and a press on one row released on another is not a click on either.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ROW = '#workTbl tr[data-row="ABC-A-002"] td[data-f="t"]'
REDRAW = "renderWork()"


class LostClick(LiveBrowserCase):
    width, height = 1640, 1000

    def open_list(self):
        b = self.b
        b.eval("WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tr[data-row]')")
        b.click('#wlay [data-lay="list"]')
        b.eval("setOf('st').clear(); workChanged()")
        b.wait("document.querySelector(%r)" % ROW)
        b.eval("HL.clear(); hlPaint()")
        return b

    def press_redraw_release(self, redraw=REDRAW):
        b = self.b
        pos = b.box(ROW)
        for kind in ("mouseMoved", "mousePressed"):
            b.call("Input.dispatchMouseEvent", type=kind, x=pos["x"], y=pos["y"], button="left", buttons=1, clickCount=1)
        b.eval("window.__old=document.querySelector(%r)" % ROW)
        b.eval(redraw)
        gone = b.eval("!document.contains(window.__old)")
        b.call("Input.dispatchMouseEvent", type="mouseReleased", x=pos["x"], y=pos["y"], button="left", buttons=0, clickCount=1)
        b.pump(0.1)
        return gone

    def test_click_during_redraw_lands_on_the_row(self):
        b = self.open_list()
        self.assertTrue(self.press_redraw_release(), "the redraw should replace the pressed row")
        self.assertTrue(b.eval("HL.has('ABC-A-002')"), "the click on the row was lost by the redraw")

    def test_click_during_a_second_redraw_still_lands_once(self):
        b = self.open_list()
        self.press_redraw_release(REDRAW + ";" + REDRAW)
        self.assertEqual(b.eval("[...HL.keys()]"), ["ABC-A-002"])

    def test_plain_click_unchanged(self):
        b = self.open_list()
        b.click(ROW)
        self.assertEqual(b.eval("[...HL.keys()]"), ["ABC-A-002"])

    def test_press_on_one_row_release_on_another_is_not_a_click(self):
        b = self.open_list()
        other_id = b.eval("[...document.querySelectorAll('#workTbl tr[data-row]')].map(r=>r.dataset.row).find(i=>i!=='ABC-A-002')")
        other = '#workTbl tr[data-row="%s"] td[data-f="t"]' % other_id
        a, o = b.box(ROW), b.box(other)
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=a["x"], y=a["y"], button="none")
        b.call("Input.dispatchMouseEvent", type="mousePressed", x=a["x"], y=a["y"], button="left", buttons=1, clickCount=1)
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=o["x"], y=o["y"], button="left", buttons=1)
        b.eval(REDRAW)
        b.call("Input.dispatchMouseEvent", type="mouseReleased", x=o["x"], y=o["y"], button="left", buttons=0, clickCount=1)
        b.pump(0.1)
        self.assertEqual(b.eval("[...HL.keys()]"), [])


if __name__ == "__main__":
    unittest.main()
