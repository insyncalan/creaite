"""Defect #237 (v2.5.1): Today's Needs attention, when nothing waits, says only "Nothing needs your attention."

Alan: "I do not need a 'how today works' note here all the time". The permanent grey box with the "How Today works" link
is gone from the empty state; Today's help stays one click away from a quiet "?" button in the Today header, which opens
the same ? panel (helpscreen.js) with its "How Today works" link.

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

    def test_todays_help_is_one_click_from_the_header(self):
        self.today()
        o = self.b.eval("""(()=>{ const b=document.querySelector('#v-today .dayband [data-thelp]');
          return {found:!!b, label:b&&b.getAttribute('aria-label'), inBand:!!(b&&b.closest('.dayband')), type:b&&b.type}; })()""")
        self.assertTrue(o["found"], "a Help control in the Today header")
        self.assertEqual(o["label"], "Help for Today")
        self.assertEqual(o["type"], "button")
        self.b.eval("document.querySelector('#v-today .dayband [data-thelp]').click()")
        p = self.b.eval("""(()=>({on:document.getElementById('helpPanel').classList.contains('on'),
          title:document.getElementById('hpnT').textContent,
          how:[...document.querySelectorAll('#helpPanel [data-hpn]')].map(a=>a.textContent).filter(t=>t==='How Today works').length}))()""")
        self.assertTrue(p["on"])
        self.assertEqual(p["title"], "Help · Today")
        self.assertEqual(p["how"], 1, "the panel carries the How Today works link")


if __name__ == "__main__":
    unittest.main()
