"""BL-148: ask creaite's conveniences. A real browser against the real live server, with a stand-in `claude`: Copy on a reply,
↑ and ↓ recall, Edit and send again, Try again after Stop, and the unsent draft back after a reload.

Run: python3 dev/tests/test_chat_conveniences.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

FAKE = r'''#!/usr/bin/env python3
import json, sys, time
args = sys.argv[1:]
message = args[args.index("-p") + 1]
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-1"})
if message.startswith("slow"):
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Started."}]}})
    time.sleep(30)
    sys.exit(0)
out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Reply to: " + message + "\n\n- one\n- two"}]}})
out({"type": "result", "result": "ok", "session_id": "sess-1"})
'''


class ChatConveniences(LiveBrowserCase):
    width, height = 1400, 900

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

    def open(self):
        b = self.b
        b.eval("openChat()")
        b.pump(0.3)
        b.eval("$('#chIn').focus()")
        return b

    def say(self, text):
        b = self.b
        b.eval("$('#chIn').focus()")
        b.type(text)
        b.key("Enter")
        b.wait("!RUN && !BUSY && document.querySelectorAll('#chLog .msg.a.md').length>0", 20)
        b.pump(0.3)

    def replies(self):
        return self.b.eval("document.querySelectorAll('#chLog .msg.a.md').length")

    def test_copy_on_every_reply_shown_on_hover_and_focus(self):
        b = self.open()
        self.say("first question")
        b.eval("window.COPIED=null; navigator.clipboard.writeText=t=>{ window.COPIED=t; return Promise.resolve(); }")
        sel = "#chLog .msg.a.md:last-of-type .msgcopy"
        self.assertTrue(b.eval(f"!!document.querySelector('{sel}')"))
        self.assertEqual(b.eval(f"getComputedStyle(document.querySelector('{sel}')).opacity"), "0")     # out of the way until wanted
        b.eval(f"document.querySelector('{sel}').focus()")
        b.pump(0.2)
        self.assertEqual(b.eval(f"getComputedStyle(document.querySelector('{sel}')).opacity"), "1")     # shown on focus
        b.click(sel)
        b.pump(0.2)
        got = b.eval("window.COPIED")
        self.assertIn("Reply to: first question", got)                      # the reply's text, plain
        self.assertIn("one", got)
        self.assertNotIn("Copy", got)                                       # not the button's own words
        self.assertNotIn("<", got)

    def test_up_and_down_recall_and_edit_and_resend(self):
        b = self.open()
        self.say("alpha")
        self.say("beta")
        b.eval("$('#chIn').value=''; $('#chIn').focus()")
        b.key("ArrowUp")
        self.assertEqual(b.eval("$('#chIn').value"), "beta")                # the last message sent
        b.key("ArrowUp")
        self.assertEqual(b.eval("$('#chIn').value"), "alpha")               # further back
        b.key("ArrowUp")
        self.assertEqual(b.eval("$('#chIn').value"), "alpha")               # the first stays
        b.key("ArrowDown")
        self.assertEqual(b.eval("$('#chIn').value"), "beta")
        b.key("ArrowDown")
        self.assertEqual(b.eval("$('#chIn').value"), "")                    # past the newest: empty again
        b.type("x")
        b.key("ArrowUp")
        self.assertEqual(b.eval("$('#chIn').value"), "x")                   # a box with text in it is left alone
        b.eval("$('#chIn').value=''")
        # Edit sits on Alan's last message only
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .msg.u .msgedit').length"), 1)
        self.assertTrue(b.eval("[...document.querySelectorAll('#chLog .msg.u')].pop().querySelector('.msgedit')!==null"))
        b.click("#chLog .msg.u .msgedit")
        b.pump(0.1)
        self.assertEqual(b.eval("$('#chIn').value"), "beta")
        self.assertTrue(b.eval("document.activeElement===$('#chIn')"))
        b.type(" again")
        n = self.replies()
        b.key("Enter")
        b.wait(f"!RUN && !BUSY && document.querySelectorAll('#chLog .msg.a.md').length>{n}", 20)
        b.pump(0.3)
        self.assertIn("Reply to: beta again", b.eval("[...document.querySelectorAll('#chLog .msg.a.md')].pop().textContent"))
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .msg.u').length"), 3)   # the chat continues, nothing removed

    def test_try_again_after_stop(self):
        b = self.open()
        b.type("slow job")
        b.key("Enter")
        b.wait("!!RUN", 10)
        b.wait("document.querySelector('#chLog .msg.a.md')!==null", 20)
        b.eval("stopAsk()")
        b.wait("!RUN && !!document.querySelector('#chLog .retry [data-retry]')", 30)
        self.assertIn("slow job", b.eval("document.querySelector('#chLog .retry').textContent"))
        b.eval("send=((orig)=>function(t){ window.RESENT=t; })(send)")       # what Try again sends, without a second slow run
        b.click("#chLog .retry [data-retry]")
        b.pump(0.1)
        self.assertEqual(b.eval("window.RESENT"), "slow job")
        self.assertFalse(b.eval("!!document.querySelector('#chLog .retry')"))

    def test_the_draft_comes_back_after_a_reload_and_goes_on_send(self):
        b = self.open()
        self.say("hello")
        chat = b.eval("ASKCHAT")
        b.eval("$('#chIn').focus()")
        b.type("an unsent draft")
        b.key("Enter", 8)
        b.type("second line")
        b.pump(0.5)
        b.eval("PIMG=[{name:'plan.png',id:'x',url:''}]; draftSave()")   # as if attached when the page went
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        self.assertEqual(b.eval("ASKCHAT"), chat)
        b.eval("openChat()")
        b.pump(0.5)
        self.assertEqual(b.eval("$('#chIn').value"), "an unsent draft\nsecond line")
        self.assertIn("plan.png", b.eval("$('#chDraftNote').textContent"))
        self.assertGreater(b.eval("$('#chIn').getBoundingClientRect().height"), 40)   # restored at its height (BL-146)
        self.assertNotIn("an unsent draft", b.eval("JSON.stringify(Object.keys(localStorage).filter(k=>!k.startsWith('creaite-ask-drafts')).map(k=>localStorage[k]))"))
        b.eval("$('#chIn').focus()")
        b.key("Enter")
        b.wait("!RUN && !BUSY", 20)
        b.pump(0.3)
        self.assertEqual(b.eval("JSON.stringify(store.get('creaite-ask-drafts',{}))"), "{}")   # cleared on send
        self.assertEqual(b.eval("$('#chDraftNote').textContent"), "")


if __name__ == "__main__":
    unittest.main()
