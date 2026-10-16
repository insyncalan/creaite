"""#144: each Work board column resizes (drag, arrow keys, double-click reset), 260 to 640 px, and the width is remembered per
board (tab and grouping). A real browser against the real live server, in both colour modes.

Run: python3 dev/tests/test_work_board_resize.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from work_board_case import BoardCase  # noqa: E402

COL = '#workBoard .bcol[data-col="later"]'


class BoardResize(BoardCase):
    def width(self, sel=COL):
        return round(self.b.eval(f"document.querySelector({sel!r}).getBoundingClientRect().width"))

    def drag(self, dx):
        b = self.b
        pos = b.box(COL + " .bcrz")
        for kind, x in (("mouseMoved", pos["x"]), ("mousePressed", pos["x"]), ("mouseMoved", pos["x"] + dx / 2), ("mouseMoved", pos["x"] + dx), ("mouseReleased", pos["x"] + dx)):
            b.call("Input.dispatchMouseEvent", type=kind, x=x, y=pos["y"], button="left", clickCount=1)
        b.pump(0.2)

    def test_drag_keys_reset_limits_and_memory(self):
        b = self.open_board("actions", "due", view="open")
        self.assertEqual(self.width(), 270)
        self.drag(100)
        self.assertEqual(self.width(), 370)
        self.drag(-900)
        self.assertEqual(self.width(), 260)                                   # the minimum
        self.drag(2000)
        self.assertEqual(self.width(), 640)                                   # the maximum
        b.eval(f"document.querySelector({COL + ' .bcrz'!r}).focus()")
        b.key("ArrowLeft"); b.pump(0.1)
        self.assertEqual(self.width(), 624)
        self.assertEqual(b.eval(f"document.querySelector({COL + ' .bcrz'!r}).getAttribute('aria-valuenow')"), "624")
        self.assertEqual(self.width('#workBoard .bcol[data-col="week"]'), 270)  # the others are untouched
        b.reload("typeof go==='function' && LIVE")                             # remembered
        b.wait("document.querySelector('#workBoard .bcol')")
        self.assertEqual(self.width(), 624)
        self.group_change("owner")                                             # another board: its own widths
        b.wait("document.querySelector('#workBoard .bcol')")
        self.assertTrue(all(w == 270 for w in b.eval("[...document.querySelectorAll('#workBoard .bcol:not(.collapsed)')].map(c=>Math.round(c.getBoundingClientRect().width))")))
        self.group_change("due")
        b.wait(f"document.querySelector({COL!r})")
        self.assertEqual(self.width(), 624)
        b.eval(f"document.querySelector({COL + ' .bcrz'!r}).dispatchEvent(new MouseEvent('dblclick',{{bubbles:true}}))")
        b.pump(0.1)
        self.assertEqual(self.width(), 270)                                    # double-click puts it back
        self.assertEqual(b.eval("JSON.stringify(JSON.parse(localStorage.getItem('creaite-boardw')||'{}'))"), "{}")

    def test_no_card_text_clips_at_the_minimum_and_both_modes(self):
        b = self.open_board("actions", "due", view="open")
        self.drag(-900)
        self.assertEqual(self.width(), 260)
        self.assertEqual(b.eval(f"[...document.querySelectorAll({COL + ' .bcard'!r})].filter(c=>c.scrollWidth>c.clientWidth+1).length"), 0)
        for mode in ("light", "dark"):
            b.eval(f"document.documentElement.dataset.theme={mode!r}")
            self.assertEqual(b.eval(f"getComputedStyle(document.querySelector({COL + ' .bcrz'!r})).cursor"), "col-resize")

    def test_corrupt_remembered_widths_never_break_the_board(self):
        b = self.b
        bad = ['null', '"oops"', '[1,2]', '7', '{"actions|due":null}', '{"actions|due":"oops"}', '{"actions|due":[300]}',
               '{"actions|due":{"later":-50,"week":"abc","overdue":99999,"x":1e9,"y":0.5,"z":null,"s":"300px\\" onmouseover=\\"x"}}']
        for raw in bad:
            b.eval(f"localStorage.setItem('creaite-boardw', {raw!r})")
            b.reload("typeof go==='function' && LIVE")
            self.open_board("actions", "due", view="open")
            self.assertEqual(self.width(), 270, raw)
            self.assertEqual(b.eval("[...document.querySelectorAll('#workBoard .bcol:not(.collapsed)')].filter(c=>Math.round(c.getBoundingClientRect().width)!==270).length"), 0, raw)
            self.assertEqual(b.eval("document.querySelectorAll('#workBoard [onmouseover]').length"), 0, raw)
            self.drag(100)                                                     # and it still resizes
            self.assertEqual(self.width(), 370, raw)
        b.eval("localStorage.setItem('creaite-boardw', '{\"actions|due\":{\"later\":400,\"week\":9999}}')")
        b.reload("typeof go==='function' && LIVE")
        self.open_board("actions", "due", view="open")
        self.assertEqual(self.width(), 400)                                    # a good value survives, a bad one is dropped
        self.assertEqual(self.width('#workBoard .bcol[data-col="week"]'), 270)

    def group_change(self, name):
        self.group(name)


if __name__ == "__main__":
    unittest.main()
