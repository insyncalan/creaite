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

    def settled(self, sel):
        """Wait until the element has stopped moving (the chat panel slides in): a click on its middle while it is still sliding
        lands beside it, and a click outside the chat closes it with focus left on <body> (the CI flake)."""
        self.b.eval("""new Promise(res=>{ const el=document.querySelector(%r); let last=null, same=0;
          const tick=()=>{ const r=el.getBoundingClientRect(), k=[r.left,r.top,r.width,r.height].join();
            same = k===last ? same+1 : 0; last=k; if(same>=5) res(true); else requestAnimationFrame(tick); };
          tick(); })""" % sel)

    def row_case(self, close, redraw=False):
        """Open the chat from the first Work row, optionally redraw the list, close the chat with `close()`, and check focus is back
        on that row (found by its key). The page also reloads its data on its own now and then (`refreshAll`, driven by the server's
        pulse) and redraws the Work list, which drops the focus that was just returned: that is not what this checks, so when
        the row was redrawn after the chat closed the case is run again (the CI flake)."""
        b = self.b
        for _ in range(8):
            row = self.open_from_work_row()
            if redraw:
                b.eval("renderWork()")                                   # the list is drawn again while the chat is open
            b.eval("window.__after = document.querySelector('#workTbl tr[data-row]')")
            close()
            b.wait(f"!{CHAT_ON}")
            got = b.wait(f"document.activeElement.dataset.row==={row!r} ? 'back' : (!window.__after.isConnected ? 'redrawn' : false)", 30)
            if got == "back":
                self.assertEqual(b.eval("document.activeElement.dataset.row||document.activeElement.tagName"), row)
                return
        self.fail("the Work list was drawn again after every close")

    def open_from_work_row(self):
        """Open the chat from the first Work row and return that row's key.

        The Work list can be drawn again by a late render after the row was picked (a slow machine): the focus then drops to
        <body> and the chat opens with no opener. So the row is marked, focused and checked to still be the focused, connected
        row; after the chat opens the mark must still be on a connected row, else the chat is closed and the whole thing retried."""
        b = self.b
        for _ in range(6):
            b.eval("go('work')")
            b.wait("document.querySelector('#workTbl tr[data-row]')")
            row = b.eval("(()=>{ const r=document.querySelector('#workTbl tr[data-row]'); if(!r.hasAttribute('tabindex')) r.tabIndex=-1;"
                         " r.focus(); r.__mark=1; return document.activeElement===r ? r.dataset.row : null; })()")
            if not row:
                b.pump(0.2)
                continue
            self.open_with_slash()
            if b.eval("(()=>{ const r=document.querySelector(`#workTbl tr[data-row=\"${CSS.escape(%r)}\"]`); return !!(r&&r.__mark); })()" % row):
                return row
            b.key("Escape")                                              # drawn again before the chat opened: no opener was kept
            b.wait(f"!{CHAT_ON}")
        self.fail("the Work list kept being drawn again")

    def test_people_rail_button_slash_esc(self):
        b = self.b
        b.eval("document.querySelector('.rail button[data-v=\"people\"]').focus()")
        self.open_with_slash()
        b.key("Escape")
        b.wait(f"!{CHAT_ON}")
        b.wait("document.activeElement.matches('.rail button[data-v=\"people\"]')")      # focus comes back a moment after the panel closes
        self.assertTrue(b.eval("document.activeElement.matches('.rail button[data-v=\"people\"]')"))

    def test_a_work_row_and_the_close_button(self):
        def close():
            self.settled("#chatClose")
            self.b.click("#chatClose")
        self.row_case(close)

    def test_a_row_drawn_again_is_found_by_its_key(self):
        def close():
            self.b.key("Escape")
        self.row_case(close, redraw=True)

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
