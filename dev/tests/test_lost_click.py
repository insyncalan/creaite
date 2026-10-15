"""Plan #85: a click that lands while the page redraws after a data refresh (BL-327's boot refresh, BL-253's events) is not
lost. The page waits for the pointer to come up (and the click to land) before it swaps in fresh data and redraws, so the
element under the pointer is still the one that was pressed.

Run: python3 dev/tests/test_lost_click.py
Drives headless Chrome against the real live server in a throwaway vault (skipped without Chrome).
"""
import os
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

SHOTS = os.environ.get("CREAITE_LOST_CLICK_SHOTS")     # a folder: before/after screenshots for a person to look at


class LostClick(LiveBrowserCase):
    shared_server = True

    def press(self, selector):
        """The mouse button goes down on the element's centre and stays down; returns where."""
        b = self.b
        pos = b.box(selector)
        self.assertIsNotNone(pos, selector)
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=pos["x"], y=pos["y"], button="none")
        b.call("Input.dispatchMouseEvent", type="mousePressed", x=pos["x"], y=pos["y"], button="left", buttons=1, clickCount=1)
        return pos

    def release(self, pos):
        self.b.call("Input.dispatchMouseEvent", type="mouseReleased", x=pos["x"], y=pos["y"], button="left", buttons=0, clickCount=1)
        self.b.pump(0.05)

    def refresh_mid_click(self, selector, shot=None):
        """Press on `selector`, start a full refresh, give it time to fetch and redraw, then release."""
        b = self.b
        b.eval("window.__el=document.querySelector(%r); window.__rl=0; reloadData().then(()=>{ window.__rl=1; }); 1" % selector, wait=False)
        b.pump(0.02)
        pos = self.press(selector)
        b.eval("window.__el2=document.querySelector(%r); 1" % selector)
        b.eval("window.__rl2=0; reloadData().then(()=>{ window.__rl2=1; }); 1", wait=False)   # one started with the button down
        b.pump(1.0)                                    # the fetch is local: long done, so a redraw would have happened by now
        if shot:
            b.screenshot(os.path.join(SHOTS, shot + "-held.png"))
        self.release(pos)
        b.wait("window.__rl===1 && window.__rl2===1 && PULSE.reloads===0", timeout=10)
        if shot:
            b.screenshot(os.path.join(SHOTS, shot + "-after.png"))

    def test_row_click_during_refresh_opens_the_row(self):
        b = self.b
        b.eval("go('work'); 1")
        b.wait("document.querySelector('#workTbl tr[data-row] .rowid')")
        rid = b.eval("document.querySelector('#workTbl tr[data-row]').dataset.row")
        sel = '#workTbl tr[data-row="%s"] .rowid' % rid
        self.refresh_mid_click(sel, shot="row" if SHOTS else None)
        self.assertEqual(b.eval("CUR&&CUR.id"), rid, "the click on the row's ID was lost in the redraw")
        self.assertFalse(b.eval("document.contains(window.__el2)"), "the refresh still redrew the table, after the click")

    def test_refresh_with_no_click_is_not_held(self):
        b = self.b
        b.eval("go('work'); 1")
        b.wait("document.querySelector('#workTbl tr[data-row]')")
        t = time.monotonic()
        b.eval("window.__rl=0; reloadData().then(()=>{ window.__rl=1; }); 1", wait=False)
        b.wait("window.__rl===1", timeout=5)
        self.assertLess(time.monotonic() - t, 3.0)

    def test_held_button_does_not_hold_the_refresh_for_ever(self):
        b = self.b
        b.eval("go('work'); 1")
        b.wait("document.querySelector('#workTbl tr[data-row] .rowid')")
        pos = self.press("#workTbl tr[data-row] .rowid")
        b.eval("window.__rl=0; reloadData().then(()=>{ window.__rl=1; }); 1", wait=False)
        b.wait("window.__rl===1", timeout=10)           # a button held down (or a lost pointerup) is given up on after a few seconds
        self.release(pos)


if __name__ == "__main__":
    unittest.main()
