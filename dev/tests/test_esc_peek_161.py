"""#161: one Esc closes an item's peek and clears its row highlight together (List, Board, a person's page, Review); with two or more rows
highlighted (which closes the peek) one Esc clears them; every other Esc layer (dialog, menu, calendar, editor, chat) still goes first.
Real Chrome against the real live server, real key events.

Run: python3 dev/tests/test_esc_peek_161.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

META = 4
STATE = """(()=>({panel:document.getElementById('panel').classList.contains('on'), hl:HL.size,
  marked:[...document.querySelectorAll('tr.hl,.bcard.hl')].filter(e=>e.offsetParent).length}))()"""


class EscClosesThePeek(LiveBrowserCase):
    width, height = 1500, 1000

    def state(self):
        return self.b.eval(STATE)

    def opened(self):
        self.b.wait("document.getElementById('panel').classList.contains('on')")
        self.b.pump(0.6)

    def closed_clean(self, how):
        self.b.pump(0.3)
        o = self.state()
        self.assertEqual((o["panel"], o["hl"], o["marked"]), (False, 0, 0), how)

    def work(self, layout):
        b = self.b
        b.eval("WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tr[data-row], #workBoard .bcard')")
        b.click(f'#wlay [data-lay="{layout}"]')
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.pump(0.4)
        return b

    def test_list_one_esc_after_the_id_a_double_click_and_enter(self):
        b = self.work("list")
        ids = b.eval("[...document.querySelectorAll('#workTbl tr[data-row]')].map(r=>r.dataset.row)")
        row = lambda i: f'#workTbl tr[data-row="{i}"]'  # noqa: E731
        b.click(row(ids[0]) + " a.rowid")
        self.opened()
        b.key("Escape")
        self.closed_clean("List, ID")
        b.click(row(ids[1]) + " td.title", count=2)
        self.opened()
        b.key("Escape")
        self.closed_clean("List, double-click")
        b.click(row(ids[2]) + " td.title")
        b.key("Enter")
        self.opened()
        b.key("Escape")
        self.closed_clean("List, Enter")

    def test_list_a_click_on_another_row_while_open_then_one_esc(self):
        b = self.work("list")
        ids = b.eval("[...document.querySelectorAll('#workTbl tr[data-row]')].map(r=>r.dataset.row)")
        b.click(f'#workTbl tr[data-row="{ids[0]}"] a.rowid')
        self.opened()
        b.click(f'#workTbl tr[data-row="{ids[1]}"] td.title')
        b.wait(f"CUR&&CUR.id=={ids[1]!r}")
        self.assertEqual(self.state()["hl"], 1)
        b.key("Escape")
        self.closed_clean("List, another row")

    def test_board_one_esc_after_the_id_and_a_double_click(self):
        b = self.work("board")
        ids = b.eval("[...document.querySelectorAll('#workBoard .bcard')].map(c=>c.dataset.row)")
        card = lambda i: f'#workBoard .bcard[data-row="{i}"]'  # noqa: E731
        b.click(card(ids[0]) + " .bid")
        self.opened()
        b.key("Escape")
        self.closed_clean("Board, ID")
        b.click(card(ids[1]) + " .bct", count=2)
        self.opened()
        b.key("Escape")
        self.closed_clean("Board, double-click")

    def test_two_highlighted_close_the_peek_and_one_esc_clears_them(self):
        b = self.work("list")
        ids = b.eval("[...document.querySelectorAll('#workTbl tr[data-row]')].map(r=>r.dataset.row)")
        b.click(f'#workTbl tr[data-row="{ids[0]}"] a.rowid')
        self.opened()
        b.click(f'#workTbl tr[data-row="{ids[1]}"] td.title', modifiers=META)
        b.pump(0.4)
        self.assertEqual(self.state()["hl"], 2)
        b.key("Escape")
        self.closed_clean("two rows")

    def test_person_page_one_esc(self):
        b = self.b
        b.eval("go('person','Sara Example')")
        b.wait("document.querySelector('#v-person table.ptbl tr[data-row]')")
        i = b.eval("document.querySelector('#v-person table.ptbl tr[data-row]').dataset.row")
        b.click(f'#v-person table.ptbl tr[data-row="{i}"] a.rowid')
        self.opened()
        b.key("Escape")
        self.closed_clean("person page")

    def test_review_one_esc(self):
        """#232 C2: Intake's proposal rows; one Esc closes the peek (test_intake_review_peek has the meeting-closes-next half)."""
        b = self.b
        n = b.eval("REV.find(r=>!r.done&&['actions','raid','decisions'].includes(r.kind)).n")
        b.eval(f"go('intake-review', {n})")
        b.wait(f"document.querySelector('#v-intake-review tr.irprop[data-irn=\"{n}\"]')")
        b.click(f'#v-intake-review tr.irprop[data-irn="{n}"] td.title')
        self.opened()
        b.key("Escape")
        b.pump(0.3)
        o = self.state()
        self.assertEqual((o["panel"], o["marked"]), (False, 0), "Intake")

    # ── the other layers still go first ──
    def open_peek(self):
        b = self.work("list")
        i = b.eval("document.querySelector('#workTbl tr[data-row]').dataset.row")
        b.click(f'#workTbl tr[data-row="{i}"] a.rowid')
        self.opened()

    def test_a_dialog_a_menu_and_the_chat_go_first(self):
        b = self.b
        self.open_peek()
        b.eval("openChat()")
        b.pump(0.4)
        b.key("Escape")
        b.pump(0.3)
        self.assertTrue(self.state()["panel"], "the first Esc closes the chat, not the peek")
        self.assertFalse(b.eval("document.getElementById('chat').classList.contains('on')"))
        b.key("Escape")
        self.closed_clean("then the peek")

    def test_the_palette_takes_its_own_esc(self):
        b = self.b
        self.open_peek()
        b.eval("openCk()")
        b.wait("document.getElementById('cmdk').open")
        b.key("Escape")
        b.pump(0.3)
        self.assertFalse(b.eval("document.getElementById('cmdk').open"))
        self.assertTrue(self.state()["panel"], "the palette closes first; the peek stays")
        b.key("Escape")
        self.closed_clean("then the peek")

    def test_the_calendar_goes_first(self):
        b = self.b
        self.open_peek()
        b.eval("(()=>{ const i=document.createElement('input'); i.value='01-01-2026'; document.body.appendChild(i); openCal(i,i); })()")
        b.wait("!!document.querySelector('.cal')")
        b.key("Escape")
        b.pump(0.3)
        self.assertFalse(b.eval("!!document.querySelector('.cal')"))
        self.assertTrue(self.state()["panel"], "the calendar closes first; the peek stays")
        b.key("Escape")
        self.closed_clean("then the peek")


if __name__ == "__main__":
    unittest.main()
