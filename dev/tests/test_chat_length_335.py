"""#335: the chat length warning. A real browser against the real live server.

- Under the limit nothing shows; at the limit (assistant.long_chat_turns, default 30) the panel offers "Continue fresh with a summary".
- Not now hides it for that chat. Continue fresh starts a new chat, puts a summary in the message box and sends nothing.
- The setting is in the catalogue with its default.

Run: python3 dev/tests/test_chat_length_335.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_ask_reopen import FAKE  # noqa: E402

FILL = '''(n=>{ for(let i=0;i<n;i++){ addEl("msg u","question number "+i); addEl("msg a md","answer number "+i); } chatLengthSync(); })'''


class ChatLength(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        from test_dashboard import populate
        populate(v)
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}

    def setUp(self):
        super().setUp()
        b = self.b
        b.reload("typeof go==='function' && LIVE")
        b.eval("openChat()")
        b.pump(0.5)
        b.eval("setChat('ask-20260101-000000-long','sess-1'); $('#chLog').textContent=''")

    def shown(self):
        self.b.pump(0.4)
        return self.b.eval("!document.querySelector('#chLong').hidden")

    def test_default_limit_is_thirty(self):
        self.b.pump(1)
        self.assertEqual(self.b.eval("longLimit()"), 30)

    def test_shows_at_the_limit_not_before(self):
        b = self.b
        b.eval(FILL + "(29)")
        self.assertFalse(self.shown())
        b.eval(FILL + "(1)")
        self.assertTrue(self.shown())
        self.assertIn("30 messages", b.eval("$('#chLongText').textContent"))

    def test_not_now_hides_it_for_that_chat(self):
        b = self.b
        b.eval(FILL + "(30)")
        self.assertTrue(self.shown())
        b.eval("$('#chLongNo').click()")
        self.assertFalse(self.shown())

    def test_continue_fresh_puts_a_summary_in_the_box_and_sends_nothing(self):
        b = self.b
        b.eval(FILL + "(30)")
        b.eval("$('#chLongGo').click()")
        b.pump(0.4)
        self.assertIsNone(b.eval("ASKCHAT"))
        box = b.eval("$('#chIn').value")
        self.assertIn("Continuing from an earlier chat of 30 messages", box)
        self.assertIn("question number 0", box)
        self.assertIn("answer number 29", box)
        self.assertNotIn("question number 10\n", box)       # only the first few and the last few
        self.assertLessEqual(len(box), 1800)
        self.assertEqual(b.eval("$$('#chLog .msg.u').length"), 0)   # nothing was sent
        self.assertFalse(self.shown())


if __name__ == "__main__":
    unittest.main()
