"""#108: closing a peek leaves nothing on the page highlighted. The peek is opened from a Today panel (a real click on its link) and
from a Work row; after Esc, the Close button and navigation, no opener keeps focus (the ring and the row's icons) and no row is selected.

Run: python3 dev/tests/test_peek_esc_highlight.py   (Chrome tier; skipped without Chrome)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_today_days as fx  # noqa: E402  (fixes CREAITE_NOW and the fixture's TODAY on import)
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402

LEFT = """(()=>{ const a=document.activeElement, p=document.getElementById('panel');
  return {panel:p.classList.contains('on'), focusOnOpener:!!(a&&a!==document.body&&a.closest('[data-open],tr[data-row],.bcard[data-row]')),
    marked:document.querySelectorAll('tr.sel,.bcard.sel,[data-open].sel,#tBrief .sel').length, hl:[...document.querySelectorAll('tr.hl')].filter(e=>e.offsetParent).length}; })()"""


class PeekCloseHighlight(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        fx.world(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": fx.NOW}

    def setUp(self):
        super().setUp()
        pin_page_clock(self.b, fx.NOW)

    def from_today(self):
        b = self.b
        b.eval("go('today'); renderToday()")
        b.wait("document.querySelector('#tBrief [data-open]')")
        b.click("#tBrief [data-open]")
        b.wait("document.getElementById('panel').classList.contains('on')")

    def from_work(self):
        b = self.b
        b.eval("WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        b.click("#workTbl tbody tr[data-row] a.rowid")
        b.wait("document.getElementById('panel').classList.contains('on')")

    def clean(self, o, how):
        self.assertFalse(o["panel"], how)
        self.assertFalse(o["focusOnOpener"], how)
        self.assertEqual((o["marked"], o["hl"]), (0, 0), how)

    def test_esc_after_a_peek_from_a_today_panel(self):
        self.from_today()
        self.b.key("Escape")
        self.b.pump(0.3)
        self.clean(self.b.eval(LEFT), "Esc, Today")

    def test_esc_after_a_peek_from_a_work_row(self):
        self.from_work()
        self.b.key("Escape")
        self.b.pump(0.3)
        self.clean(self.b.eval(LEFT), "Esc, Work")           # one Esc closes the peek and clears the row

    def test_the_close_button_and_navigation(self):
        self.from_today()
        self.b.click("#pkClose")
        self.b.pump(0.3)
        self.clean(self.b.eval(LEFT), "Close, Today")
        self.from_work()
        self.b.eval("go('today')")
        self.b.pump(0.3)
        self.clean(self.b.eval(LEFT), "navigation, Work")

    def test_a_click_outside(self):
        self.from_today()
        self.b.eval("document.querySelector('#v-today .dayband').dispatchEvent(new MouseEvent('mousedown',{bubbles:true}))")
        self.b.pump(0.3)
        self.clean(self.b.eval(LEFT), "click outside, Today")
        self.from_work()
        self.b.eval("document.querySelector('#v-work').dispatchEvent(new MouseEvent('mousedown',{bubbles:true}))")
        self.b.pump(0.3)
        self.clean(self.b.eval(LEFT), "click outside, Work")

    # ── Alan, 15-10-2026: a click outside clears a bulk selection too ──
    BULK = """(()=>{ const bar=document.getElementById('wbulk'); return {n:HL.size, hl:[...document.querySelectorAll('tr.hl,.bcard.hl')].filter(e=>e.offsetParent).length,
      bar:!!(bar&&!bar.hidden&&bar.offsetParent), panel:document.getElementById('panel').classList.contains('on')}; })()"""

    def bulk(self):
        b = self.b
        b.eval("WT='actions'; go('work')")
        b.wait("document.querySelectorAll('#workTbl tbody tr[data-row]').length>1")
        b.eval("(()=>{ const r=[...document.querySelectorAll('#workTbl tbody tr[data-row]')]; hlOnly('actions',r[0].dataset.row); hlToggle('actions',r[1].dataset.row); })()")
        b.pump(0.4)
        o = b.eval(self.BULK)
        self.assertEqual((o["n"], o["bar"]), (2, True), "two rows selected, the bulk bar shown")

    def test_a_click_outside_clears_a_bulk_selection(self):
        self.bulk()
        self.b.eval("document.querySelector('#v-work').dispatchEvent(new MouseEvent('mousedown',{bubbles:true}))")
        self.b.pump(0.4)
        o = self.b.eval(self.BULK)
        self.assertEqual((o["n"], o["hl"], o["bar"]), (0, 0, False))

    def test_the_bulk_bar_and_a_row_tick_keep_the_selection(self):
        self.bulk()
        self.b.eval("document.querySelector('#wbulk').dispatchEvent(new MouseEvent('mousedown',{bubbles:true}))")
        self.b.eval("document.querySelector('#wbulk button, #wbulk select').dispatchEvent(new MouseEvent('mousedown',{bubbles:true}))")
        self.b.eval("document.querySelector('#workTbl tbody tr[data-row]').dispatchEvent(new MouseEvent('mousedown',{bubbles:true}))")
        self.b.pump(0.3)
        o = self.b.eval(self.BULK)
        self.assertEqual((o["n"], o["bar"]), (2, True))

    def test_esc_clears_a_bulk_selection(self):
        self.bulk()
        self.b.key("Escape")
        self.b.pump(0.3)
        o = self.b.eval(self.BULK)
        self.assertEqual((o["n"], o["hl"], o["bar"], o["panel"]), (0, 0, False, False))
        self.from_work()
        self.b.key("Escape")                                   # and Esc still closes a peek together with its row
        self.b.pump(0.3)
        self.clean(self.b.eval(LEFT), "Esc, Work")


if __name__ == "__main__":
    unittest.main()
