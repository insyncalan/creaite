"""BL-330: a remembered chat that's gone. A real browser against the real live server.

- A remembered chat the server no longer has (removed, BL-32, or another vault's) is asked for once and then forgotten:
  a reload doesn't ask for it again.
- The remembered chat is kept per vault: under a key made from the vault's path (never the path itself), so another vault's
  remembered chat on the same address is never read.

Run: python3 dev/tests/test_ask_gone_chat.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_ask_reopen import FAKE  # noqa: E402   (a stand-in `claude`)

# Every /api/chat the page asks for, counted across reloads (sessionStorage outlives a reload).
COUNT = r'''(()=>{ const f=window.fetch; window.fetch=function(u,o){ try{ if(String(u)==="/api/chat"){ const c=JSON.parse(o.body).chat;
  const n=JSON.parse(sessionStorage.getItem("asked")||"{}"); n[c]=(n[c]||0)+1; sessionStorage.setItem("asked",JSON.stringify(n)); } }catch(e){}
  return f.apply(this,arguments); }; })();'''

# The page's own fingerprint of the vault's path, worked out here independently.
KEY = r'''(()=>{ let h=5381; for(const c of String(D.vault_path)) h=(Math.imul(h,33)^c.charCodeAt(0))>>>0; return "creaite-ask-chat:"+h.toString(36); })()'''


class AskGoneChat(LiveBrowserCase):
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

    def remember(self, key, chat):
        self.b.eval(f"localStorage.setItem({json.dumps(key)},JSON.stringify({json.dumps(chat)}))")

    def asked(self):
        return self.b.eval("JSON.parse(sessionStorage.getItem('asked')||'{}')")

    def test_a_gone_chat_is_asked_for_once_then_forgotten(self):
        b = self.b
        key = b.eval(KEY)
        self.remember(key, "ask-20260101-000000-gone")
        b.call("Page.addScriptToEvaluateOnNewDocument", source=COUNT)
        b.reload("typeof go==='function' && LIVE")
        b.eval("openChat()")
        b.wait("ASKCHAT===null && document.querySelector('#chLog .msg.a')", 10)           # a fresh chat, greeted
        self.assertIsNone(b.eval(f"JSON.parse(localStorage.getItem({json.dumps(key)}))"))  # forgotten at once
        b.reload("typeof go==='function' && LIVE")
        b.eval("openChat()")
        b.pump(0.6)
        self.assertIsNone(b.eval("ASKCHAT"))
        self.assertEqual(self.asked().get("ask-20260101-000000-gone"), 1, "the gone chat was asked for again")
        log = "".join(p.read_text(encoding="utf-8") for p in (self.v.root / "system/logs").glob("debug-*.log"))
        self.assertRegex(log, r"INFO  server\s+POST /api/chat 404")
        self.assertNotRegex(log, r"WARN\s+server\s+POST /api/chat")

    def test_the_remembered_chat_is_kept_per_vault(self):
        b = self.b
        key = b.eval(KEY)
        self.assertNotIn(b.eval("D.vault_path"), key)                       # a fingerprint, never the path
        self.remember("creaite-ask-chat:othervault", "ask-other-vaults-chat")   # another vault on the same address
        self.remember(key, None)
        b.reload("typeof go==='function' && LIVE")
        self.assertIsNone(b.eval("ASKCHAT"))
        b.eval("$('#chIn').value='hello'; send()", wait=False)
        b.wait(f"JSON.parse(localStorage.getItem({json.dumps(key)})||'null')", 20)        # this vault's chat, under its own key
        chat = b.eval(f"JSON.parse(localStorage.getItem({json.dumps(key)}))")
        self.assertEqual(chat, b.eval("ASKCHAT"))
        self.assertEqual(b.eval("JSON.parse(localStorage.getItem('creaite-ask-chat:othervault'))"), "ask-other-vaults-chat")
        self.assertIsNone(b.eval("localStorage.getItem('creaite-ask-chat')"))   # the old shared key is no longer written


if __name__ == "__main__":
    unittest.main()
