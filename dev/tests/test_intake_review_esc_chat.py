"""#232-B review fix (v2.5.0): Esc with focus in the ask creaite panel leaves the page's peek and meeting state alone (panel.js
pkEscBusy's `#chat` clause, read by the page's two Esc listeners): irPeek and irOpen keep their values. (The shared Esc handler in
core/keys.js still hides the peek's panel itself; that is not this rule.) With focus outside the chat the same Esc clears irPeek
(the control), so the test fails if the clause is removed and not merely because Esc does nothing.

Run: python3 dev/tests/test_intake_review_esc_chat.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intake_review_support as S  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

ROW = "#v-intake-review tr.irprop"
PANEL_ON = "document.getElementById('panel').classList.contains('on')"


class EscWithChat(LiveBrowserCase):
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        S.load(v)

    def open_peek(self):
        b = self.b
        mid = S.open_meeting(b)
        b.eval(f"document.querySelectorAll('{ROW}')[1].focus()")
        b.key("Enter")
        b.wait(PANEL_ON)
        b.wait("irPeek.value!=null")
        return mid

    def test_esc_in_the_ask_panel_keeps_the_peek_and_the_meeting_state(self):
        b = self.b
        mid = self.open_peek()
        b.eval("openChat()")
        b.wait("document.getElementById('chat').classList.contains('on')")
        b.eval("document.getElementById('chIn').focus()")
        b.wait("!!document.activeElement.closest('#chat')")
        peek = b.eval("irPeek.value")
        b.key("Escape")
        b.pump(0.5)
        self.assertEqual(b.eval("irPeek.value"), peek, "Esc in the ask panel cleared the peek")
        self.assertEqual(b.eval("irOpen.value"), mid, "Esc in the ask panel closed the meeting")

    def test_control_esc_outside_the_chat_still_closes_the_peek(self):
        b = self.b
        self.open_peek()
        b.eval("document.activeElement.blur()")
        b.key("Escape")
        b.wait(f"!({PANEL_ON})")
        self.assertIsNone(b.eval("irPeek.value"))


if __name__ == "__main__":
    unittest.main()
