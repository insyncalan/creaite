"""#334: declining the "Run anyway" card for the weekly AI budget says where things stand once, not the question a second time.
A real browser against the real live server; the ask request is answered by the page's own stand-in with the server's 429 reply.

Run: python3 dev/tests/test_ai_budget_decline.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

MSG = "This week's AI budget is used up ($52.10 of $50.00 used). It starts again on Monday 26-10-2026. The buttons in the dashboard still work. Run this request anyway?"


class Decline(LiveBrowserCase):
    width, height = 1400, 900

    def test_declining_does_not_repeat_the_question(self):
        b = self.b
        b.eval("openChat()")
        b.eval("""(()=>{ const real=window.fetch; window.fetch=function(u,o){ if(String(u).includes('/api/ask')&&!String(u).includes('/api/ask/')) return Promise.resolve(new Response(JSON.stringify({ok:false,
          budget:{can_continue:true},message:%r}),{status:429,headers:{'Content-Type':'application/json'}})); return real.apply(this,arguments); }; })()""" % MSG)
        b.eval("$('#chIn').value='tell me something'; send()", wait=False)
        b.wait("!!document.querySelector('#chLog .confirm button')", 20)
        self.assertEqual(b.eval("document.querySelector('#chLog .confirm').textContent.split('Run this request anyway?').length-1"), 1)
        b.eval("document.querySelector('#chLog .confirm button').click()")                       # Cancel
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('still work.'))", 20)
        b.pump(4)                                                                                  # the reply is typed out; let it finish
        log = b.eval("document.getElementById('chLog').textContent")
        self.assertEqual(log.count("Run this request anyway?"), 1, "the question is asked once, on the card")
        self.assertIn("starts again on Monday 26-10-2026", b.eval("[...document.querySelectorAll('#chLog .msg.a')].filter(m=>m.textContent.includes('used up')).pop().textContent"))
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
