"""Defect #237 (v2.5.1): Today's Needs attention, when nothing waits, says only "Nothing needs your attention."

Alan: "I do not need a 'how today works' note here all the time". The permanent grey box with the "How Today works" link
is gone from the empty state; Today's help stays one key away: the ? key opens the ? panel (helpscreen.js) with its
"How Today works" link.

#284 (v2.5.4, Alan 21-10-2026): the quiet "?" button in the Today header (left of the Close the day door, below the
meetings' "Organised by") is gone; the door button is unchanged.

Run: python3 dev/tests/test_today_empty_help.py   (Chrome tier; skipped without Chrome)
An empty vault: no projects, no items, so nothing needs attention.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402


class EmptyNeedsAttention(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        v.run("init")                                    # an empty vault: nothing to attend to
        cfg = v.root / "system/config/settings.json"      # the sample project would bring the report reminders
        data = json.loads(cfg.read_text())
        data.setdefault("reminders", {})["enabled"] = False
        cfg.write_text(json.dumps(data))
        v.run(script="build_dashboard.py")

    def today(self):
        self.b.eval("go('today'); renderToday()")
        self.b.wait("document.getElementById('attnList')")

    def test_the_empty_state_is_only_the_sentence(self):
        self.today()
        o = self.b.eval("""(()=>({rows:document.querySelectorAll('#attnList>li').length, none:document.querySelectorAll('#attnList .none').length,
          text:document.getElementById('attnList').textContent.trim(),
          box:document.querySelectorAll('#attnSec .hhow, #attnSec [data-hhow]').length,
          anywhere:document.querySelectorAll('#v-today .hhow, #v-today [data-hhow]').length}))()""")
        self.assertEqual([o["rows"], o["none"]], [1, 1], o["text"])
        self.assertEqual(o["text"], "Nothing needs your attention.")
        self.assertEqual(o["box"], 0, "no How Today works box in Needs attention")
        self.assertEqual(o["anywhere"], 0, "no How Today works box anywhere on Today")

    def press_help(self):
        self.b.eval("document.activeElement&&document.activeElement.blur&&document.activeElement.blur()")
        self.b.call("Input.dispatchKeyEvent", type="keyDown", key="?", code="Slash", text="?", windowsVirtualKeyCode=191, modifiers=8)
        self.b.call("Input.dispatchKeyEvent", type="keyUp", key="?", code="Slash", windowsVirtualKeyCode=191, modifiers=8)
        self.b.wait("document.getElementById('helpPanel').classList.contains('on')")

    def test_no_help_question_mark_in_the_header(self):
        """#284: no ? button in Today's header (the meeting header); nothing in the band reads "?" or "Help for Today"."""
        self.today()
        o = self.b.eval("""(()=>{ const band=document.querySelector('#v-today .dayband');
          const q=[...band.querySelectorAll('button,a,[role=button]')].filter(e=>e.textContent.trim()==='?'
            ||/^help/i.test(e.getAttribute('aria-label')||'')||/^help/i.test(e.dataset.tip||''));
          return {q:q.length, thelp:document.querySelectorAll('[data-thelp], .dhelp').length}; })()""")
        self.assertEqual(o, {"q": 0, "thelp": 0}, "no help ? in the Today header")

    def test_the_door_button_is_unchanged(self):
        self.today()
        o = self.b.eval("""(()=>{ const b=document.getElementById('dayClose'), cs=getComputedStyle(b);
          return {inBand:!!b.closest('.dayband'), dclose:b.dataset.dclose, popup:b.getAttribute('aria-haspopup'),
            door:!!b.querySelector('svg'), right:cs.right, bottom:cs.bottom, w:cs.width, h:cs.height}; })()""")
        self.assertEqual(o, {"inBand": True, "dclose": "1", "popup": "dialog", "door": True,
                             "right": "24px", "bottom": "14px", "w": "32px", "h": "32px"})

    def test_todays_help_is_one_key_away(self):
        self.today()
        self.press_help()
        p = self.b.eval("""(()=>({title:document.getElementById('hpnT').textContent,
          how:[...document.querySelectorAll('#helpPanel [data-hpn]')].map(a=>a.textContent).filter(t=>t==='How Today works').length}))()""")
        self.assertEqual(p["title"], "Help · Today")
        self.assertEqual(p["how"], 1, "the panel carries the How Today works link")

if __name__ == "__main__":
    unittest.main()
