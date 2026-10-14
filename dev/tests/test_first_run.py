"""BL-156: first run. On a vault that hasn't finished set-up, Today shows a short checklist (Connect Microsoft 365, Add a
project, Add people, Run the first sweep, Open Review), each with a button that does it or opens where it is done, ticked as it
is done; it goes when all are ticked or when dismissed (Settings › Reminders › Restore brings it back). Help and the first-day
guide offer the launcher first. A real browser against the real live server.

Run: python3 dev/tests/test_first_run.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
STEPS = "JSON.stringify([...document.querySelectorAll('#setupList li')].map(li=>[li.querySelector('.t').textContent,li.classList.contains('done'),(li.querySelector('[data-setup]')||{}).textContent||'']))"


class FirstRun(LiveBrowserCase):
    def test_the_checklist_ticks_and_its_buttons_go_where_it_is_done(self):
        b = self.b
        b.eval("go('today')")
        b.pump(0.3)
        steps = json.loads(b.eval(STEPS))
        self.assertEqual([s[0] for s in steps], ["Connect Microsoft 365", "Add a project", "Add people", "Run the first sweep", "Open Review"])
        done = {s[0]: s[1] for s in steps}
        self.assertFalse(done["Run the first sweep"])                          # no sweep yet in a new vault
        self.assertFalse(done["Connect Microsoft 365"])
        self.assertTrue(done["Add a project"])                                 # the sample vault has projects
        self.assertEqual(b.eval("document.querySelector('#tBrief').firstElementChild.id"), "setupList")
        self.assertFalse(b.eval("!!document.querySelector('#setupList [data-setup=\"proj\"]')"))   # a step done has no button
        b.click('#setupList [data-setup="help"]')
        b.pump(0.3)
        self.assertEqual(b.eval("VIEW"), "help")                               # Microsoft 365 is connected in Claude Code: Help says how
        b.eval("go('today')")
        b.click('#setupList [data-setup="review"]')
        b.pump(0.3)
        self.assertEqual(b.eval("VIEW"), "review")
        b.eval("go('today')")
        b.pump(0.2)
        self.assertTrue({s[0]: s[1] for s in json.loads(b.eval(STEPS))}["Open Review"])   # ticked as it is done
        b.eval("send=((orig)=>function(t){ window.SENT=t; })(send)")
        b.click('#setupList [data-setup="sweep"]')
        b.pump(0.2)
        self.assertEqual(b.eval("window.SENT"), "sweep")                       # the sweep goes through ask creaite
        b.eval("closeChat(); D.last_sweep='2026-10-10 07:00'; renderToday()")  # once everything is done it goes
        b.pump(0.2)
        self.assertFalse(b.eval("!!document.getElementById('setupList')"))

    def test_dismiss_is_for_good_and_restore_brings_it_back(self):
        b = self.b
        b.eval("go('today')")
        b.pump(0.3)
        b.click('#setupList [data-setup="dismiss"]')
        b.pump(0.6)
        self.assertFalse(b.eval("!!document.getElementById('setupList')"))
        cfg = json.loads((self.v.root / "system/config/settings.json").read_text())
        self.assertIn("setup:checklist", cfg["reminders"]["dismissed_forever"])
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        b.eval("go('today')")
        b.pump(0.3)
        self.assertFalse(b.eval("!!document.getElementById('setupList')"))
        b.eval("go('settings','reminders')")
        b.pump(0.3)
        b.click("#remRestore")
        b.pump(0.6)
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        b.eval("go('today')")
        b.pump(0.3)
        self.assertTrue(b.eval("!!document.getElementById('setupList')"))

    def test_help_and_the_first_day_guide_offer_the_launcher_first(self):
        help_md = (ROOT / "system/templates/help.md").read_text(encoding="utf-8")
        first = help_md[help_md.index("## Your first hour"):help_md.index("## Every day")]
        self.assertLess(first.index("launcher"), first.index("live_server.py"))     # the launcher, then Terminal as the fallback
        guide = (ROOT / "system/templates/guide-first-day.html").read_text(encoding="utf-8")
        self.assertIn("creaite</b> app", guide.replace("<strong>", "<b>").replace("</strong>", "</b>"))


if __name__ == "__main__":
    unittest.main()
