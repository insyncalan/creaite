"""BL-199: ask creaite's suggestions never choose themselves. A real browser against the real live server, with a
stand-in `claude`: typing "apply" lists suggestions with none chosen, and Enter sends "apply" as typed; ↓ then Enter puts
the first suggestion in the box without sending; ↑ chooses the last; a click still picks; Esc closes; Tab completes the
first; the screen-reader state has no active option until one is chosen.

Run: python3 dev/tests/test_chat_suggestions.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

FAKE = r'''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
message = args[args.index("-p") + 1]
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-1"})
out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Reply to: " + message}]}})
out({"type": "result", "result": "ok", "session_id": "sess-1"})
'''

STATE = """(()=>({open:!$('#acMenu').hidden, items:[...document.querySelectorAll('#acMenu .aco span')].map(x=>x.textContent),
  act:document.querySelectorAll('#acMenu .aco.act').length, selected:[...document.querySelectorAll('#acMenu .aco')].map(o=>o.getAttribute('aria-selected')),
  active:$('#chIn').getAttribute('aria-activedescendant'), actText:(document.querySelector('#acMenu .aco.act span')||{}).textContent||null,
  value:$('#chIn').value, sent:document.querySelectorAll('#chLog .msg.u').length}))()"""


class ChatSuggestions(LiveBrowserCase):
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

    def typed(self, text):
        b = self.b
        b.eval("openChat()")
        b.pump(0.3)
        b.eval("$('#chIn').value=''; acClose(); $('#chIn').focus()")
        b.type(text)
        b.wait("!$('#acMenu').hidden", 5)
        return b.eval(STATE)

    def test_nothing_chosen_and_enter_sends_what_was_typed(self):
        b = self.b
        s = self.typed("apply")
        self.assertIn("undo last apply", s["items"])                       # the list is there…
        self.assertEqual(s["act"], 0)                                       # …with nothing highlighted
        self.assertTrue(all(x == "false" for x in s["selected"]))
        self.assertIsNone(s["active"])                                      # and no active option for a screen reader
        self.assertIn("Enter sends what you typed", b.eval("$('#acMenu .achint').textContent"))
        b.key("Enter")
        b.wait("document.querySelectorAll('#chLog .msg.u').length>0 && !RUN && !BUSY", 20)
        self.assertEqual(b.eval("[...document.querySelectorAll('#chLog .msg.u')].pop().firstChild.textContent.trim()"), "apply")   # not "undo last apply"
        self.assertTrue(b.eval("$('#acMenu').hidden"))

    def test_down_then_enter_fills_the_first_without_sending(self):
        b = self.b
        s = self.typed("apply")
        b.key("ArrowDown")
        s = b.eval(STATE)
        self.assertEqual(s["actText"], s["items"][0])                       # ↓ chooses the first
        self.assertEqual(s["active"], "aco0")
        self.assertIn("Enter puts this suggestion", b.eval("$('#acMenu .achint').textContent"))
        b.key("Enter")
        b.pump(0.3)
        s2 = b.eval(STATE)
        self.assertEqual(s2["value"], s["items"][0])                        # the box holds it…
        self.assertEqual(s2["sent"], 0)                                     # …and nothing was sent
        self.assertFalse(s2["open"])

    def test_up_chooses_the_last(self):
        b = self.b
        s = self.typed("weekly")
        self.assertGreater(len(s["items"]), 1)
        b.key("ArrowUp")
        s2 = b.eval(STATE)
        self.assertEqual(s2["actText"], s["items"][-1])
        self.assertEqual(s2["active"], f"aco{len(s['items']) - 1}")

    def test_click_still_picks(self):
        b = self.b
        s = self.typed("apply")
        b.click("#acMenu .aco[data-aci=\"0\"]")
        b.pump(0.3)
        s2 = b.eval(STATE)
        self.assertEqual(s2["value"], s["items"][0].rstrip("…").rstrip() + (" " if s["items"][0].endswith("…") else ""))
        self.assertEqual(s2["sent"], 0)

    def test_tab_completes_the_first_and_esc_closes(self):
        b = self.b
        s = self.typed("apply")
        b.key("Tab")
        b.pump(0.2)
        s2 = b.eval(STATE)
        self.assertEqual(s2["value"].strip(), s["items"][0].rstrip("…").strip())   # Tab completes, never sends
        self.assertEqual(s2["sent"], 0)
        self.typed("rev")
        b.key("Escape")
        b.pump(0.2)
        self.assertTrue(b.eval("$('#acMenu').hidden && $('#chat').classList.contains('on')"))

    def test_shift_enter_with_none_chosen_is_a_new_line(self):
        b = self.b
        self.typed("apply")
        b.key("Enter", modifiers=8)
        b.pump(0.2)
        s = b.eval(STATE)
        self.assertEqual(s["sent"], 0)                                     # nothing sent, no suggestion picked
        self.assertTrue(s["value"].startswith("apply"))


if __name__ == "__main__":
    unittest.main()
