"""#241 acceptance (Alan, 19-10-2026): resizing and the board features keep working with Work items v2 on the 2.6.1 line.
A list column resized by drag keeps its width across a reload, in Compact and in Comfortable rows; a board column resized by its
separator keeps its width across a reload; after the reload the board still opens the peek from a card, a list row still takes
the keys (O opens the owner's cell editor) and Draft email's C still opens inside the peek. A real browser, the real live server.

Run: python3 dev/tests/test_work_resize_reload.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import work_data as W  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

READY = "typeof go==='function' && LIVE"


class ResizeAndReload(LiveBrowserCase):
    width, height = 1500, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        W.load(v)

    def setUp(self):
        super().setUp()
        self.b.eval("localStorage.clear()")
        self.b.reload(READY)

    def open_tab(self, t):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr, #workTbl .empty, #workBoard .bcol')")
        if b.eval("WT") != t:
            b.click(f'#wtabs button[data-t="{t}"]')
            b.wait(f"WT==='{t}'")
        b.wait("document.querySelector('#workTbl tbody tr[data-row], #workBoard .bcol')")

    def th(self, col):
        return round(self.b.eval(f"document.querySelector('#workTbl thead th[data-col=\"{col}\"]').getBoundingClientRect().width"))

    def drag(self, sel, dx):
        b = self.b
        pos = b.box(sel)
        for kind, x in (("mouseMoved", pos["x"]), ("mousePressed", pos["x"]), ("mouseMoved", pos["x"] + dx / 2), ("mouseMoved", pos["x"] + dx),
                        ("mouseReleased", pos["x"] + dx)):
            b.call("Input.dispatchMouseEvent", type=kind, x=x, y=pos["y"], button="left", clickCount=1)
        b.pump(0.2)

    def test_a_list_column_width_survives_a_reload_in_both_densities(self):
        b = self.b
        for dens in ("cmp", "cmf"):
            b.eval(f"localStorage.setItem('creaite-density', JSON.stringify({dens!r})); localStorage.removeItem('creaite-colwidths')")
            b.reload(READY)
            self.open_tab("actions")
            rz = '#workTbl thead th[data-col="o"] .colrz'
            w0 = self.th("o")
            self.drag(rz, 40)
            self.assertEqual(self.th("o"), w0 + 40, dens)
            b.reload(READY)
            self.open_tab("actions")
            self.assertEqual(self.th("o"), w0 + 40, dens)                              # the width survives the reload
            self.assertTrue(b.eval(f"document.getElementById('workWrap').classList.contains({dens!r})"), dens)   # and so does the density

    def test_a_board_column_width_survives_a_reload_and_the_board_still_works(self):
        b = self.b
        self.open_tab("raid")
        if b.eval("layoutOf('raid')") != "board":
            b.click('#wlay [data-lay="board"]')
            b.wait("layoutOf('raid')==='board'")
        b.wait("document.querySelector('#workBoard .bcol .bcrz')")
        col = b.eval("document.querySelector('#workBoard .bcol .bcrz').closest('.bcol').dataset.col")
        w0 = round(b.eval(f"document.querySelector('#workBoard .bcol[data-col=\"{col}\"]').getBoundingClientRect().width"))
        self.drag(f'#workBoard .bcol[data-col="{col}"] .bcrz', 50)
        w1 = round(b.eval(f"document.querySelector('#workBoard .bcol[data-col=\"{col}\"]').getBoundingClientRect().width"))
        self.assertGreater(w1, w0)
        b.reload(READY)
        self.open_tab("raid")
        b.wait("document.querySelector('#workBoard .bcol')")
        self.assertEqual(round(b.eval(f"document.querySelector('#workBoard .bcol[data-col=\"{col}\"]').getBoundingClientRect().width")), w1)
        b.click("#workBoard .bcard[data-row] .bid")                                      # a card's ID still opens the peek
        b.wait("pkOn()&&CUR&&CUR.mode==='record'")

    def test_after_a_reload_the_row_keys_and_draft_email_still_work(self):
        b = self.b
        self.open_tab("actions")
        rz = '#workTbl thead th[data-col="due"] .colrz'
        self.drag(rz, 30)
        b.reload(READY)
        self.open_tab("actions")
        ids = b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>r.dataset.row)")
        row = f'#workTbl tr[data-row="{ids[0]}"]'
        b.click(row + " td.title", inset=3)
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("o")
        b.wait(f"document.querySelector('{row} td.editing[data-f=\"o\"]')")                # the row keys work
        b.key("Escape")
        for i in [i for i in ids if b.eval(f"REC('actions',{i!r}).st") == "Open"]:
            b.eval(f"openRecord('actions',{i!r})")
            b.wait(f"pkOn()&&CUR&&CUR.id==={i!r}")
            if b.eval("!document.getElementById('pkChaseBtn').hidden"):
                break
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("c")
        b.wait("!!document.querySelector('#chSubj')", 20)                                  # C is Draft email while the peek is open


if __name__ == "__main__":
    unittest.main()
