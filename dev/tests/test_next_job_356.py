"""#356 (empty states point at the next job): irNextJob (src/core/irFold.js) under Node, and the line on the Intake page and Today's
Week ahead in a browser. Intent measured against the page's own boxes; desktop and 900 px.

Run: python3 dev/tests/test_next_job_356.py   (the browser part needs Google Chrome)
"""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

FOLD = Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/core/irFold.js"
EMPTY = "{v:1,meetings:[],mail:{needs:[],routine:[]},other:{needs:[],routine:[]},later:[],not_needed:[],counts:{}}"


@unittest.skipUnless(shutil.which("node"), "needs Node")
class NextJobRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        js = """const f = await import(%s); const z = {ready: 0, to_approve: 0}, T = "2026-10-24";
        const j = (...a) => f.irNextJob(...a); const o = {};
        o.busy = [j({ready: 1, to_approve: 0}, "2026-10-24 08:00", T, true, true), j({ready: 0, to_approve: 3}, "2026-10-24 08:00", T, true, true), j(null, "", T, false, false)];
        o.never = j(z, null, T, true, true).job; o.old = j(z, "2026-10-23 17:00", T, true, true).job; o.today_mail = j(z, "2026-10-24 08:00", T, true, true).job;
        o.tomorrow = j(z, "2026-10-24 08:00", T, false, true).job; o.none = j(z, "2026-10-24 08:00", T, false, false);
        o.words = [j(z, null, T, false, false), j(z, "2026-10-24 08:00", T, true, false), j(z, "2026-10-24 08:00", T, false, true)].map(x => x.text + "|" + x.button);
        console.log(JSON.stringify(o));""" % json.dumps(FOLD.as_uri())
        r = subprocess.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        cls.o = json.loads(r.stdout)

    def test_nothing_while_there_is_something_to_do(self):
        self.assertEqual(self.o["busy"], [None, None, None])

    def test_the_job_follows_state_and_never_loops(self):
        o = self.o
        self.assertEqual((o["never"], o["old"]), ("refresh", "refresh"))         # no calendar, or read before today: refresh it
        self.assertEqual(o["today_mail"], "mail")                                # read today, mail due: check mail
        self.assertEqual(o["tomorrow"], "tomorrow")                              # read today, mail done: tomorrow
        self.assertEqual(o["none"]["job"], "none")                               # nothing left: the sentence alone, no button
        self.assertNotIn("button", o["none"])

    def test_plain_words(self):
        for w in self.o["words"]:
            for bad in ("sweep", "stage", "triage", "proposal", "VIP"):
                self.assertNotIn(bad.lower(), w.lower())
        self.assertIn("Next: refresh the calendar.", self.o["words"][0])


class NextJobPage(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 900

    def intake(self, w):
        b = self.b
        b.resize(w, 900)
        b.eval("go('intake-review')")
        b.pump(0.8)                                                                                # opening the page reloads its data; set ours after
        b.eval("REV.splice(0); D.inbox=[]; D.intake_review=%s; D.meetings=Object.assign({},D.meetings,{fetched:'2000-01-01 08:00'}); shared.BUSY=false; shared.RUN=null; irTick.value++" % EMPTY)
        b.wait("document.querySelector('[data-irnext]')")

    def test_clear_intake_says_so_and_has_one_button_that_fits(self):
        for w in (1400, 900):
            self.intake(w)
            b = self.b
            self.assertEqual(b.eval("document.querySelectorAll('[data-irnext]').length"), 1)
            self.assertEqual(b.eval("document.querySelector('[data-irnext]').dataset.irnext"), "refresh")
            self.assertEqual(b.eval("document.querySelectorAll('[data-irnext] button').length"), 1)
            fits = b.eval("(()=>{const l=document.querySelector('[data-irnext]'),p=document.querySelector('#v-intake-review').getBoundingClientRect(),r=l.getBoundingClientRect();return r.right<=p.right+1&&document.scrollingElement.scrollWidth<=innerWidth})()")
            self.assertTrue(fits, w)
            self.assertFalse(b.eval("document.querySelector('[data-irnext] button').getBoundingClientRect().height<24"))

    def test_the_button_says_why_when_it_cannot_act(self):
        self.intake(1400)
        b = self.b
        b.eval("window.__live=shared.LIVE; shared.LIVE=false; irTick.value++")
        b.wait("document.querySelector('[data-irnext] button').disabled")
        self.assertIn("isn", b.eval("document.querySelector('[data-irnext] button').title"))
        b.eval("shared.LIVE=window.__live")

    def tomorrow_job(self, ahead=1, bare=False):
        """Intake with nothing to do, the calendar read today, mail checked, and a saved day `ahead` days on (bare: no saved days at all)."""
        b = self.b
        b.resize(1400, 900)
        b.eval("window.plusDays=n=>{const d=new Date(TODAY+'T12:00:00');d.setDate(d.getDate()+n);return d.toISOString().slice(0,10)}")
        b.eval("go('intake-review')")
        b.pump(0.8)                                                                                # opening the page reloads its data; set ours after
        b.eval("REV.splice(0); D.inbox=[]; D.dev=false; D.calendar=D.calendar||{days:{}}; D.sweep_due={due:false}; D.intake_review=%s; D.meetings=Object.assign({},D.meetings,{fetched:TODAY+' 08:00'}); D.days={days:[synthDay(TODAY)%s]}; S.srcCalendar=true; shared.BUSY=false; shared.RUN=null; irTick.value++" % (EMPTY, "" if bare else ",synthDay(plusDays(%d))" % ahead))
        b.pump(0.5)

    def test_next_is_disabled_while_ask_creaite_is_busy_and_says_why(self):
        self.intake(1400)
        b = self.b
        for flag in ("shared.BUSY=true", "shared.RUN={}"):
            b.wait("(shared.BUSY=false, shared.RUN=null, irTick.value++, !document.querySelector('[data-irnext] button').disabled)")
            b.wait("(%s, irTick.value++, document.querySelector('[data-irnext] button').disabled)" % flag)      # set on each poll: a data refresh may clear it
            self.assertIn("busy", b.eval("document.querySelector('[data-irnext] button').title"), flag)
        b.eval("shared.BUSY=false; shared.RUN=null")

    def test_open_tomorrow_only_when_tomorrow_itself_is_saved_and_busy_never_blocks_it(self):
        b = self.b
        self.tomorrow_job(1)
        self.assertEqual(b.eval("(document.querySelector('[data-irnext]')||{dataset:{}}).dataset.irnext"), "tomorrow")
        b.eval("shared.BUSY=true; irTick.value++")
        b.pump(0.3)
        self.assertFalse(b.eval("document.querySelector('[data-irnext] button').disabled"))      # it only moves to another page
        b.eval("shared.BUSY=false")
        self.tomorrow_job(3)                                                                      # a day three ahead is not tomorrow
        self.assertEqual(b.eval("document.querySelectorAll('[data-irnext] button').length"), 0)
        self.assertNotIn("tomorrow", b.eval("document.querySelector('[data-irnext]').textContent"))
        self.tomorrow_job(bare=True)                                                              # no saved day: it says nothing about tomorrow
        self.assertEqual(b.eval("document.querySelectorAll('[data-irnext] button').length"), 0)
        self.assertNotIn("tomorrow", b.eval("document.querySelector('[data-irnext]').textContent"))

    def test_nothing_is_shown_while_there_is_work(self):
        b = self.b
        b.eval("go('intake-review')")
        b.pump(1)
        self.assertEqual(b.eval("document.querySelectorAll('[data-irnext]').length"), 0)       # the demo has meetings to process

    def test_mutant_the_line_goes_when_there_is_work_to_do_again(self):
        self.intake(1400)
        b = self.b
        b.eval("D.intake_review=Object.assign({},D.intake_review,{meetings:[{id:'mX',src:'calendar',title:'Sample sync',day:'2026-10-05',start:'15:00',p:null,stage:'arrived',state:'ready',age:0,stale:False_,groups:{needs:[],routine:[]}}]}); irTick.value++".replace("False_","false"))
        b.wait("!document.querySelector('[data-irnext]')")
    def test_week_ahead_with_nothing_offers_tomorrow_only_when_the_calendar_has_one(self):
        b = self.b
        b.eval("window.plusDays=n=>{const d=new Date(TODAY+'T12:00:00');d.setDate(d.getDate()+n);return d.toISOString().slice(0,10)}")      # tomorrow from the page's own today, never a fixed date
        EMPTYWEEK = "D.week=Object.assign({},D.week,{items:[],groups:[],undated:[],further:[],days:[]}); go('cockpit','ABC'); go('today')"
        for w in (1400, 900):
            b.resize(w, 900)
            b.eval("go('today'); D.calendar=D.calendar||{days:{}}; D.days={days:[synthDay(TODAY),synthDay(plusDays(1))]}; " + EMPTYWEEK)
            b.wait("document.querySelector('[data-wknext]')")
            self.assertIn("Next: look at tomorrow.", b.eval("document.querySelector('#weekList').textContent"))
            self.assertTrue(b.eval("document.scrollingElement.scrollWidth<=innerWidth"))
        b.eval("D.days={days:[synthDay(TODAY)]}; go('cockpit','ABC'); go('today')")          # mutant: no tomorrow in the calendar
        b.pump(0.5)
        self.assertFalse(b.eval("!!document.querySelector('[data-wknext]')"))
        self.assertNotIn("look at tomorrow", b.eval("document.querySelector('#weekList').textContent"))


if __name__ == "__main__":
    unittest.main()
