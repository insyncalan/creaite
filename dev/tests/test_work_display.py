"""BL-128: the Work page's Display menu (layout, grouping, order, properties, show), in a real browser against the real live server.

Run: python3 dev/tests/test_work_display.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import work_data as W  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

PRIOS = ["Urgent", "High", "Medium", "Low"]


class Display(LiveBrowserCase):
    width, height = 1500, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        W.load(v)

    def setUp(self):
        super().setUp()
        self.b.eval("localStorage.clear()")
        self.b.reload("typeof go==='function' && LIVE")

    def open_work(self, tab="actions", lay="list"):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr, #workTbl .empty, #workBoard .bcol')")
        if tab != "actions":
            b.click(f'#wtabs button[data-t="{tab}"]')
            b.wait(f"WT==='{tab}'")
        b.click(f'#wlay [data-lay="{lay}"]')
        b.pump(0.2)
        return b

    def change(self, sel, value):
        self.b.eval(f"(()=>{{ const s=document.querySelector({sel!r}); s.value={value!r}; s.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
        self.b.pump(0.2)

    def test_opens_with_d_and_focus_returns_to_the_button(self):
        b = self.open_work()
        b.key("d")
        b.wait("document.getElementById('dispMenu').classList.contains('on')")
        self.assertEqual(b.eval("document.getElementById('dispBtn').getAttribute('aria-expanded')"), "true")
        self.assertTrue(b.eval("document.getElementById('dispMenu').contains(document.activeElement)"))
        self.assertEqual(b.eval("document.getElementById('dispMenu').getAttribute('role')"), "dialog")
        self.assertEqual(b.eval("document.getElementById('dispMenu').getAttribute('aria-label')"), "Display")
        b.key("Escape")
        b.wait("!document.getElementById('dispMenu').classList.contains('on')")
        self.assertEqual(b.eval("document.activeElement.id"), "dispBtn")
        self.assertEqual(b.eval("document.getElementById('dispBtn').getAttribute('aria-expanded')"), "false")
        b.click("#dispBtn")
        b.wait("document.getElementById('dispMenu').classList.contains('on')")
        b.click("#dispDone")
        b.wait("!document.getElementById('dispMenu').classList.contains('on')")
        self.assertEqual(b.eval("document.activeElement.id"), "dispBtn")
        b.click("#dispBtn")
        b.click("#v-work h1")                                         # a click outside closes it
        b.wait("!document.getElementById('dispMenu').classList.contains('on')")
        # every select in the menu has a label a screen reader reads
        b.click("#dispBtn")
        self.assertTrue(b.eval("[...document.querySelectorAll('#dispMenu select')].every(s=>s.labels.length||s.getAttribute('aria-label'))"))
        self.assertEqual(b.eval("document.getElementById('wordRev').getAttribute('aria-label')"), "Reverse the order")

    def test_order_by_and_reverse_update_the_list_and_the_address(self):
        b = self.open_work()
        b.click("#dispBtn")
        self.change("#wbsort", "pr")
        prios = b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row] td[data-f=pr]')].map(t=>t.firstChild.textContent.trim())")
        self.assertEqual([PRIOS.index(p) for p in prios], sorted(PRIOS.index(p) for p in prios))
        self.assertIn("&s=pr.asc", b.eval("location.hash"))
        self.assertTrue(b.eval("document.getElementById('dispMenu').classList.contains('on')"))       # stays open while choosing
        b.click("#wordRev")
        b.pump(0.2)
        prios = b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row] td[data-f=pr]')].map(t=>t.firstChild.textContent.trim())")
        self.assertEqual([PRIOS.index(p) for p in prios], sorted((PRIOS.index(p) for p in prios), reverse=True))
        self.assertIn("&s=pr.desc", b.eval("location.hash"))
        self.assertEqual(b.eval("document.getElementById('wordRev').getAttribute('aria-pressed')"), "true")
        # the default order can be reversed too
        self.change("#wbsort", "")
        first = b.eval("document.querySelector('#workTbl tbody tr[data-row]').dataset.row")
        b.click("#wordRev")
        b.pump(0.2)
        self.assertEqual(b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].pop().dataset.row"), first)
        b.reload("typeof go==='function' && LIVE")                    # the address keeps it
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        self.assertEqual(b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].pop().dataset.row"), first)

    def test_properties_are_columns_and_card_fields(self):
        b = self.open_work()
        b.click("#dispBtn")
        b.click("#dprop-ms")                                          # Milestone, which had no column
        b.wait("document.querySelector('#workTbl th[data-col=ms]')")
        self.assertTrue(b.eval("!!document.querySelector('#workTbl td[data-f=ms]')"))
        b.click("#dprop-upd")
        b.wait("document.querySelector('#workTbl th[data-col=upd]')")
        b.click("#dprop-pr")                                          # take Priority off
        b.wait("!document.querySelector('#workTbl th[data-col=pr]')")
        # the board card shows the first four in that order: owner, due, status, milestone
        b.eval("closeDisp()")
        b.click('#wlay [data-lay="board"]')
        b.wait("document.querySelector('#workBoard .bcard')")
        self.assertFalse(b.eval("!!document.querySelector('#workBoard .bcard .bpri')"))
        self.assertTrue(b.eval("!!document.querySelector('#workBoard .bcard .bown')"))
        self.assertTrue(b.eval("!!document.querySelector('#workBoard .bcard .bprop[data-p=st]')"))
        self.assertFalse(b.eval("!!document.querySelector('#workBoard .bcard .bprop[data-p=upd]')"))   # the fifth isn't on a card
        # moving a property earlier changes the column order
        b.click("#dispBtn")
        b.click('#dispMenu [data-mv="ms"][data-d="-1"]')
        b.pump(0.2)
        cols = b.eval("orderedCols().map(c=>c[0])")
        self.assertLess(cols.index("ms"), cols.index("st"))
        self.assertEqual(b.eval("document.activeElement.dataset.mv"), "ms")       # focus stays on the control

    def test_board_options_and_reset(self):
        b = self.open_work("actions", "board")
        b.eval("applyFilters({}); workChanged()")                     # closed items too
        b.click("#dispBtn")
        self.change("#wgrp", "status")
        b.wait("document.querySelector('#workBoard .bcol[data-col=Open]')")
        self.assertIn("&g=status", b.eval("location.hash"))
        self.change("#wclosed", "all")
        n_all = b.eval("document.querySelectorAll('#workBoard .bcol[data-col=Closed] .bcard').length")
        self.assertEqual(n_all, len([r for r in self.v.rows("actions") if r["status"] == "Closed"]))
        self.assertFalse(b.eval("!!document.querySelector('#workBoard .bcol[data-col=Closed] .bshow')"))
        b.click("#wshowempty")
        b.pump(0.2)
        self.assertEqual(b.eval("BHIDE.actions"), True)
        b.click("#dispReset")
        b.pump(0.3)
        self.assertEqual(b.eval("groupOf('actions')"), "due")             # the setting's default
        self.assertEqual(b.eval("[!!BHIDE.actions, BCLALL.has('actions'), SORT.actions]"), [False, False, None])
        self.assertEqual(b.eval("layoutOf('actions')"), "board")          # the layout stays
        self.assertTrue(b.eval("document.getElementById('dispMenu').contains(document.activeElement)"))

    def test_layout_from_the_toolbar_and_options_per_tab(self):
        for tab in ("actions", "raid", "decisions"):
            b = self.open_work(tab, "list")
            b.click("#dispBtn")
            self.assertEqual(b.eval("document.querySelector('#wgrp option').value"), "none", tab)          # BL-129: the List groups, none by default
            self.assertTrue(b.eval("!!document.querySelector('#wsub').closest('[hidden]')"), tab)         # no sub-group without a group
            self.assertEqual(b.eval("[...document.querySelectorAll('#wbsort option')].some(o=>o.value==='date')"), tab == "decisions")
            self.assertEqual(b.eval("!!document.getElementById('dprop-ms')"), tab != "decisions")
            self.assertFalse(b.eval("!!document.querySelector('#dispMenu [data-dlay]')"))           # BL-159: List and Board only on the toolbar
            b.eval("closeDisp()")
            b.click('#wlay [data-lay="board"]')
            b.wait("layoutOf(WT)==='board'")
            b.click("#dispBtn")
            self.assertFalse(b.eval("!!document.querySelector('#wgrp').closest('[hidden]')"))
            self.assertIn("lay=board", b.eval("location.hash"))
            b.eval("closeDisp()")
            b.click('#wlay [data-lay="list"]')
            b.wait("layoutOf(WT)==='list'")

    def test_a_saved_view_keeps_its_order(self):
        b = self.open_work()
        b.click("#dispBtn")
        self.change("#wbsort", "t")
        b.eval("closeDisp()")
        b.eval("(async()=>{ await saveView('By title'); })()")
        b.wait("SAVED.actions.some(v=>v.name==='By title')")
        self.assertEqual(b.eval("SAVED.actions.find(v=>v.name==='By title').o"), {"col": "t", "dir": "asc"})
        self.change("#wbsort", "due")
        b.click('#wviews [data-wv="saved:By title"]')
        b.wait("SORT.actions && SORT.actions.col==='t'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
