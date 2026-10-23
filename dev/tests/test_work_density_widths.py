"""#241 a (Alan, 19-10-2026): the Compact row is one line with the ID beside the title, and the density changes row height
only. With column widths saved (creaite-colwidths) for several columns, switching Compact and Comfortable never changes a
column's width, order or visibility, at 1400 and at 900 px, on every tab, and never writes a width; the Board is the same in
both densities. A real browser against the real live server.

Run: python3 dev/tests/test_work_density_widths.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import work_data as W  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

READY = "typeof go==='function' && LIVE"
WIDTHS = {"actions|o": 210, "actions|due": 140, "actions|st": 120, "raid|t": 420, "raid|o": 180, "decisions|by": 190}


class DensityWidths(LiveBrowserCase):
    width, height = 1400, 1000
    shared_server = True            # nothing here changes the data

    @classmethod
    def load(cls, v):
        populate(v)
        W.load(v)

    def setUp(self):
        super().setUp()
        b = self.b
        b.resize(1400, 1000)
        b.eval("localStorage.clear()")
        b.eval(f"localStorage.setItem('creaite-colwidths', {json.dumps(json.dumps(WIDTHS))})")
        b.reload(READY)

    def tab(self, t):
        b = self.b
        if b.eval("VIEW") != "work":
            b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr, #workTbl .empty, #workBoard .bcol')")
        if b.eval("WT") != t:
            b.click(f'#wtabs button[data-t="{t}"]')
            b.wait(f"WT==='{t}'")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")

    def density(self, d):
        b = self.b
        b.click(f'#wdens [data-dens="{d}"]')
        b.wait(f"document.getElementById('workWrap').classList.contains('{d}')")
        b.frames(3)                                                                    # the one-line placement runs on a frame

    def columns(self):
        """Each heading: its key and width (to a hundredth of a pixel), in order, and the table's width."""
        return self.b.eval("""({cols:[...document.querySelectorAll('#workTbl thead th[data-col]')].map(t=>[t.dataset.col,
          Math.round(t.getBoundingClientRect().width*100)/100]), table:Math.round(document.getElementById('workTbl').getBoundingClientRect().width*100)/100})""")

    def heights(self):
        return self.b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].slice(0,10).map(r=>Math.round(r.getBoundingClientRect().height))")

    def stored(self, k):
        v = self.b.eval(f"localStorage.getItem({k!r})")
        return None if v is None else json.loads(v)

    def test_switching_density_changes_row_height_only_at_1400_and_900(self):
        b = self.b
        for width in (1400, 900):
            b.resize(width, 1000)
            for t in ("actions", "raid", "decisions"):
                with self.subTest(width=width, tab=t):
                    self.tab(t)
                    self.density("cmp")
                    compact, ch = self.columns(), self.heights()
                    saved = [c for c in compact["cols"] if f"{t}|{c[0]}" in WIDTHS]
                    self.assertTrue(saved, compact)                                       # the saved widths are in play
                    for col, w in saved:
                        self.assertGreaterEqual(w, WIDTHS[f"{t}|{col}"] - 0.5, (col, w))  # and honoured
                    self.density("cmf")
                    comfortable, fh = self.columns(), self.heights()
                    self.assertEqual(comfortable, compact)                                # no width, order or column changed
                    # only the height did: 40 and 57 px rows (a title that wraps at 900 px grows in both, less in Compact)
                    self.assertTrue(all(c < f and f >= 57 and (c <= 41 or f > 57) for c, f in zip(ch, fh)), (ch, fh))
                    self.assertTrue(any(c <= 41 for c in ch), ch)
                    self.density("cmp")
                    self.assertEqual(self.columns(), compact)
        self.assertEqual(self.stored("creaite-colwidths"), WIDTHS)                        # no width written
        self.assertIsNone(self.stored("creaite-colorder"))
        self.assertIsNone(self.stored("creaite-cols"))

    def test_the_one_line_row_moves_the_id_only_by_a_translate(self):
        # the ID's line keeps its place in the layout (so its width counts the same); only a translate puts it beside the title
        self.tab("actions")
        self.density("cmp")
        r = self.b.eval("""(()=>{ const x=document.querySelector('#workTbl tr[data-row] td.title > .x.xup'), cs=getComputedStyle(x);
          return {display:cs.display, position:cs.position, translate:cs.translate!=='none', height:x.getBoundingClientRect().height}; })()""")
        self.assertEqual(r, {"display": "block", "position": "static", "translate": True, "height": 0})

    def test_the_board_is_the_same_in_both_densities(self):
        b = self.b
        board = {}
        for d in ("cmp", "cmf"):
            b.eval(f"localStorage.setItem('creaite-density', {json.dumps(json.dumps(d))})")
            b.reload(READY)
            self.tab("actions")
            b.click('#wlay [data-lay="board"]')
            b.wait("!document.getElementById('workBoard').hidden && document.querySelector('#workBoard .bcol')")
            b.frames(3)
            board[d] = b.eval("""({cols:[...document.querySelectorAll('#workBoard .bcol')].map(c=>{ const r=c.getBoundingClientRect();
              return [c.dataset.col||c.getAttribute('data-k')||c.querySelector('h3,.bch')?.textContent||'', Math.round(r.width*100)/100, c.classList.contains('coll')]; }),
              cards:[...document.querySelectorAll('#workBoard .bcard')].map(c=>[c.dataset.row, Math.round(c.getBoundingClientRect().height*100)/100]),
              html:document.getElementById('workBoard').innerHTML.length, dens:document.getElementById('wdens').hidden,
              marks:document.querySelectorAll('#workBoard .cmp, #workBoard .cmf, #workBoard .xup, #workBoard .wkm').length})""")
            b.click('#wlay [data-lay="list"]')                                            # leave the layout as it was
            b.wait("document.getElementById('workBoard').hidden")
        self.assertTrue(board["cmp"]["cards"], board)
        self.assertEqual(board["cmp"], board["cmf"])
        self.assertTrue(board["cmp"]["dens"])                                              # the density switch hides on the Board
        self.assertEqual(board["cmp"]["marks"], 0)


if __name__ == "__main__":
    unittest.main()
