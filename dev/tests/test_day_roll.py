"""#171: a dashboard window left open past midnight rolls to the new day, in a real browser against the real live server.

Run: python3 dev/tests/test_day_roll.py   (needs Google Chrome; skipped otherwise)

The page opens on Thursday 08-10-2026 09:30 (CREAITE_NOW for the server, a movable Date shim in the page). Thursday's 16:00 meeting
has not happened (Intake offers no Check again for it) and Today shows Thursday. The page clock then moves to Friday 00:05 (the window left open overnight): the day roll (a visibilitychange,
or the minute check) moves TODAY, Intake reads Thursday's meeting as happened (Check again is offered) and Today's day moves to Friday. With an
editor open and unsaved, nothing is redrawn and the snack says "It's a new day: reload"; the day rolls once the edit is dropped.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_meetings import week_calendar  # noqa: E402
from datetime import date  # noqa: E402

NOW = "2026-10-08 09:30"     # a Thursday
THURSDAY, FRIDAY = "2026-10-08", "2026-10-09"
SHIM = """(()=>{ const R=Date, base=new R(2026,9,8,9,30).getTime()-R.now(); window.__clockOff=base;
  class D extends R{ constructor(...a){ if(a.length) super(...a); else super(R.now()+window.__clockOff); } static now(){ return R.now()+window.__clockOff; } }
  window.Date=D; })();"""
ROW = """(()=>{ const tr=[...document.querySelectorAll('#v-intake-review tr[data-irm]')].find(t=>t.textContent.includes('Late call')); return tr?{check:!!tr.querySelector('[data-ira=check]')}:null; })()"""


class DayRollTests(LiveBrowserCase):
    shared_server = False

    @classmethod
    def load(cls, v):
        populate(v)
        week_calendar(v, today=date(2026, 10, 8))
        p = v.root / "system/staging/calendar.json"
        cal = json.loads(p.read_text())
        cal["days"][THURSDAY].append({"id": "ev-late", "start": "16:00", "end": "17:00", "title": "Late call", "teams": True, "organiser": True})
        p.write_text(json.dumps(cal))

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW}

    def setUp(self):
        super().setUp()
        b = self.b
        b.call("Page.addScriptToEvaluateOnNewDocument", source=SHIM)
        b.reload("typeof go==='function' && LIVE")
        self.assertEqual(b.eval("TODAY"), THURSDAY)

    def to_friday_early(self):
        # Friday 00:05, expressed as an offset from the real clock
        self.b.eval("window.__clockOff = new Date(2026,9,9,0,5).getTime() - (Date.now() - window.__clockOff)")

    def open_intake(self):
        b = self.b
        b.eval("go('intake-review')")
        b.wait("document.querySelector('#v-intake-review tr[data-irm]')")

    def test_the_new_day_makes_yesterdays_meeting_happened_and_moves_today(self):
        b = self.b
        self.open_intake()
        self.assertEqual(b.eval(ROW), {"check": False})                        # 16:00 has not happened yet: nothing to check
        b.eval("go('today')")
        b.wait("document.querySelector('#v-today')")
        self.assertEqual(b.eval("dayShown()"), THURSDAY)
        self.to_friday_early()
        b.eval("document.dispatchEvent(new Event('visibilitychange'))")      # headless Chrome reports "visible"
        b.wait("TODAY==='2026-10-09'", 20)
        b.wait("dayShown()==='2026-10-09'", 20)
        self.open_intake()
        b.wait(f"(({ROW})||{{}}).check===true", 15)                            # it has happened: its transcript can be looked up (the page draws again a moment after go())
        self.assertEqual(b.eval(ROW), {"check": True})
        self.assertEqual(b.eval("WEEKSTART"), "2026-10-05")
        self.assertEqual(b.eval("[...document.querySelectorAll('.snack,#snackT')].map(e=>e.textContent).join('|').includes('new day')"), False)

    def test_unsaved_edits_get_a_snack_not_a_redraw(self):
        b = self.b
        b.eval("PK.dirty = true")                                              # an unsaved proposal edit
        self.to_friday_early()
        b.eval("document.dispatchEvent(new Event('visibilitychange'))")
        b.wait("/new day: reload/.test(document.getElementById('snackT').textContent)", 20)
        self.assertEqual(b.eval("TODAY"), THURSDAY)                            # nothing changed under the user
        b.eval("PK.dirty = false")
        b.eval("document.dispatchEvent(new Event('visibilitychange'))")
        b.wait("TODAY==='2026-10-09'", 20)


FRI = "2026-10-16"
FRI_NOW = FRI + " 23:39"


class ZoneTests(LiveBrowserCase):
    """#173: Friday 23:39 local, a 13:30-14:00 meeting that nobody has looked up yet offers Check again on the Intake page (a 23:50
    meeting that has not ended does not), in zones either side of UTC (the page must use local day and time everywhere, never UTC)."""

    @classmethod
    def load(cls, v):
        populate(v)
        st = v.root / "system/staging"
        (st / "calendar.json").write_text(json.dumps({"fetched": FRI + " 22:06", "days": {FRI: [
            {"id": "ev-a", "start": "13:30", "end": "14:00", "title": "Afternoon one", "teams": True, "organiser": True},
            {"id": "ev-b", "start": "15:30", "end": "16:30", "title": "Afternoon two", "teams": True, "organiser": True},
            {"id": "ev-c", "start": "23:50", "end": "23:59", "title": "Not yet ended", "teams": True, "organiser": True}]}}))
        (st / "transcripts.json").write_text(json.dumps({"checked": {}}))        # nothing looked up: each is waiting

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": FRI_NOW}

    def rows(self, zone):
        b = self.b
        b.call("Emulation.setTimezoneOverride", timezoneId=zone)
        b.call("Page.addScriptToEvaluateOnNewDocument", source=SHIM.replace("new R(2026,9,8,9,30)", "new R(2026,9,16,23,39)"))
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('intake-review')")
        b.wait("document.querySelector('#v-intake-review tr[data-irm]')")
        return b.eval("""[...document.querySelectorAll('#v-intake-review tr[data-irm]')].map(t=>({t:t.textContent,
          check:!!t.querySelector('[data-ira=check]')}))""")

    def check(self, zone):
        rows = self.rows(zone)
        self.assertEqual(self.b.eval("TODAY"), FRI)
        for title in ("Afternoon one", "Afternoon two"):
            r = next(x for x in rows if title in x["t"])
            self.assertTrue(r["check"], zone)                      # ended: its transcript can be looked up
        self.assertFalse(next(x for x in rows if "Not yet ended" in x["t"])["check"], zone)      # 23:59 has not come

    def test_los_angeles(self):
        self.check("America/Los_Angeles")

    def test_kolkata(self):
        self.check("Asia/Kolkata")


if __name__ == "__main__":
    unittest.main()
