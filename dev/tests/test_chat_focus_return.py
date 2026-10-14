"""BL-211: ask creaite returns focus to where you were when it closes.

Run: python3 dev/tests/test_chat_focus_return.py   (needs Google Chrome; skipped otherwise)
A real browser and server on the sample data: the People rail button, `/`, Esc: focus is back on it; a Work row, `/`, the close
button: back on that row; the opener removed meanwhile: focus goes to the page's heading, never <body>; #askBtn by pointer.
BL-312: with no opener (⌘J from nowhere) or one that is gone, focus goes quietly to the page (.content, no ring), never the h1.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

CHAT_ON = "document.getElementById('chat').classList.contains('on')"


class ChatFocusReturn(LiveBrowserCase):
    shared_server = True

    def setUp(self):
        super().setUp()
        self.b.call("Emulation.setFocusEmulationEnabled", enabled=True)

    def open_with_slash(self):
        self.b.key("/")
        self.b.wait(CHAT_ON)
        self.b.wait("document.getElementById('chat').contains(document.activeElement)")

    def test_people_rail_button_slash_esc(self):
        b = self.b
        b.eval("document.querySelector('.rail button[data-v=\"people\"]').focus()")
        self.open_with_slash()
        b.key("Escape")
        b.wait(f"!{CHAT_ON}")
        self.assertTrue(b.eval("document.activeElement.matches('.rail button[data-v=\"people\"]')"))

    def test_a_work_row_and_the_close_button(self):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tr[data-row]')")
        row = b.eval("(()=>{ const r=document.querySelector('#workTbl tr[data-row]'); if(!r.hasAttribute('tabindex')) r.tabIndex=-1; r.focus(); return r.dataset.row; })()")
        self.open_with_slash()
        b.click("#chatClose")
        b.wait(f"!{CHAT_ON}")
        self.assertEqual(b.eval("document.activeElement.dataset.row"), row)

    def test_a_row_drawn_again_is_found_by_its_key(self):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tr[data-row]')")
        row = b.eval("(()=>{ const r=document.querySelector('#workTbl tr[data-row]'); if(!r.hasAttribute('tabindex')) r.tabIndex=-1; r.focus(); return r.dataset.row; })()")
        self.open_with_slash()
        b.eval("renderWork()")                                           # the list is drawn again while the chat is open
        b.key("Escape")
        b.wait(f"!{CHAT_ON}")
        self.assertEqual(b.eval("document.activeElement.dataset.row||document.activeElement.tagName"), row)

    def test_the_opener_gone_goes_quietly_to_the_page(self):          # BL-312: was the heading (BL-211)
        b = self.b
        b.eval("go('today')")
        b.wait("VIEW==='today'")
        b.eval("(()=>{ const x=document.createElement('button'); x.id='tmpOpener'; x.textContent='x'; document.querySelector('#v-today').prepend(x); x.focus(); })()")
        self.open_with_slash()
        b.eval("document.getElementById('tmpOpener').remove()")
        b.key("Escape")
        b.wait(f"!{CHAT_ON}")
        self.assertTrue(b.eval("document.activeElement.matches('.content')"))
        self.assertFalse(b.eval("document.activeElement.matches('h1')"))

    def test_cmd_j_from_nowhere_then_esc_leaves_no_ring(self):         # BL-312
        b = self.b
        b.eval("go('today')")
        b.wait("VIEW==='today'")
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.wait("document.activeElement===document.body")
        b.key("j", modifiers=4)                                         # ⌘J
        b.wait(CHAT_ON)
        b.wait("document.getElementById('chat').contains(document.activeElement)")
        b.key("Escape")
        b.wait(f"!{CHAT_ON}")
        self.assertTrue(b.eval("document.activeElement.matches('.content')"))
        self.assertFalse(b.eval("!!document.querySelector('h1:focus')"))
        self.assertEqual(b.eval("getComputedStyle(document.activeElement).outlineStyle"), "none")

    def test_a_button_opener_cmd_j_esc_returns_to_it(self):            # BL-312: with an opener, as before
        b = self.b
        b.eval("document.querySelector('.rail button[data-v=\"work\"]').focus()")
        b.key("j", modifiers=4)
        b.wait(CHAT_ON)
        b.wait("document.getElementById('chat').contains(document.activeElement)")
        b.key("Escape")
        b.wait(f"!{CHAT_ON}")
        self.assertTrue(b.eval("document.activeElement.matches('.rail button[data-v=\"work\"]')"))

    def test_ask_button_by_pointer(self):
        b = self.b
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.click("#askBtn")
        b.wait(CHAT_ON)
        b.wait("document.getElementById('chat').contains(document.activeElement)")
        b.key("Escape")
        b.wait(f"!{CHAT_ON}")
        self.assertEqual(b.eval("document.activeElement.id"), "askBtn")

    def test_a_click_elsewhere_keeps_its_own_focus(self):
        b = self.b
        b.eval("go('work')")
        b.wait("document.getElementById('workQ')")
        b.eval("document.querySelector('.rail button[data-v=\"people\"]').focus()")
        self.open_with_slash()
        b.click("#workQ")                                                # the click outside closes the chat
        b.wait(f"!{CHAT_ON}")
        self.assertEqual(b.eval("document.activeElement.id"), "workQ")


if __name__ == "__main__":
    unittest.main(verbosity=2)
