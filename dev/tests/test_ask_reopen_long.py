"""#148: a long past reply is on screen in full at the first paint when ask creaite is reopened; a live reply still streams.
Real Chrome against the real live server, with a stand-in `claude` that answers "long <name>" with a long reply.

Run: python3 dev/tests/test_ask_reopen_long.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_ask_reopen as base

WORDS = 120    # under the 400-word cap, so a live reply's words do fade in
FAKE = base.FAKE.replace(
    'else:\n    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Reply to: " + message}]}})',
    'elif message.startswith("long"):\n    text = " ".join("word%d" % i for i in range(@N@)) + " END-" + name\n'
    '    out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})\n'
    '    out({"type": "result", "result": "ok", "session_id": session})\n'
    'else:\n    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Reply to: " + message}]}})').replace("@N@", str(WORDS))
assert "elif message.startswith" in FAKE

# Every change to the log: how many bubbles were added with their text already whole, and how often text grew afterwards.
WATCH = base.WATCH


class AskReopenLong(base.AskReopen):
    @classmethod
    def load(cls, v):
        super().load(v)
        (v.root / "fake_claude.py").write_text(FAKE)

    def whole(self, name):
        return self.b.eval(f"[...document.querySelectorAll('#chLog .msg.a')].filter(m=>m.textContent.includes('END-{name}')&&m.textContent.includes('word{WORDS - 1}')&&m.textContent.includes('word0 ')).length")

    def test_a_long_saved_reply_is_whole_on_open_with_no_animation(self):
        t, _ = self.ask_in_background("long a", "r-test-long-a")
        self.until_history_has("END-a")
        t.join(30)
        self.reload_watched()
        b = self.b
        b.eval("openChat()")
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('END-a'))", 20)
        self.assertEqual(self.whole("a"), 1, "the reply was not whole when it first appeared")
        b.pump(1.0)
        seen = b.eval("SEEN")
        self.assertEqual((seen["mw"], seen["typed"], seen["working"]), (0, 0, 0), "the saved reply was animated or typed")
        self.assertEqual(self.whole("a"), 1)

    def test_a_finished_run_replayed_without_history_is_not_animated(self):
        t, _ = self.ask_in_background("long b", "r-test-long-b")
        self.until_history_has("END-b")
        t.join(30)
        self.reload_watched()
        b = self.b
        b.eval("openChat()")
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('END-b'))", 20)
        b.eval("$('#chLog').textContent=''; SHOWN=null; window.SEEN.mw=0")
        b.eval("attachRun({id:'r-test-long-b',kind:'ask',done:true,message:'long b',confirmed:false})", wait=False)
        b.wait("!RUN", 20)
        self.assertEqual(self.whole("b"), 1)
        self.assertEqual(b.eval("SEEN.mw"), 0, "a finished run's reply faded in word by word")

    def test_a_live_long_reply_still_streams(self):
        b = self.b
        b.eval("openChat()")
        b.eval("$('#chIn').value='long c'; send()", wait=False)
        b.wait("!RUN && [...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('END-c'))", 20)
        self.assertGreater(b.eval("document.querySelectorAll('#chLog .mw').length"), 0, "a live reply no longer fades in")


# the inherited tests would run again here
for _n in [n for n in dir(base.AskReopen) if n.startswith("test_")]:
    setattr(AskReopenLong, _n, None)

if __name__ == "__main__":
    unittest.main()
