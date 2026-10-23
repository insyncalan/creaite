"""#318: Today's day line always runs to the Friday of next calendar week.

Run: python3 dev/tests/test_day_line_318.py      (the browser part needs Chrome and is skipped without it)
The rule: the last day is always the Friday of next calendar week (Monday to Sunday): 11 days ahead on a Monday down to 5 on a
Sunday. Checked for every weekday of "today", across a month end and a year end; the saved
calendar's `to` (what it was read to) cuts what Prep may use and marks the days past it "not read yet" on the line; a calendar
saved before `to` existed counts as read to seven days after its fetch; the browser shows those days as "Not read yet" with
Refresh calendar, never as "no meetings".
"""
import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "system/scripts"))
import test_today_days as fx  # noqa: E402  (fixes CREAITE_NOW and the fixture's TODAY on import)
import paths  # noqa: E402
import sweep  # noqa: E402
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402

# (a Monday, its expected last day): every weekday of a week, then the same across a month end and a year end
WEEKS = [date(2026, 10, 19), date(2026, 10, 26), date(2026, 12, 28), date(2027, 2, 22)]
TABS = "[...document.querySelectorAll('#todayDate [role=tab]')]"


class Window(unittest.TestCase):

    def setUp(self):
        p = mock.patch.object(paths, "load_settings", return_value={})
        p.start()
        self.addCleanup(p.stop)

    def test_the_last_day_is_the_friday_of_next_calendar_week_every_day(self):
        for monday in WEEKS:
            for n in range(7):                                     # Monday to Sunday: 11, 10, 9, 8, 7, 6, 5 days ahead
                today = monday + timedelta(days=n)
                last = sweep.calendar_window(today)[1]
                self.assertEqual(last, monday + timedelta(days=11), today)
                self.assertEqual((last.weekday(), (last - today).days), (4, 11 - n), today)

    def test_the_start_is_unchanged(self):
        self.assertEqual(sweep.calendar_window(date(2026, 10, 22))[0], date(2026, 10, 19))
        with mock.patch.object(paths, "load_settings", return_value={"inbox": {"meetings_from": "3"}}):
            self.assertEqual(sweep.calendar_window(date(2026, 10, 22))[0], date(2026, 10, 19))

    def test_across_a_month_end_and_a_year_end(self):
        self.assertEqual(sweep.calendar_window(date(2026, 12, 30))[1], date(2027, 1, 8))    # a Wednesday
        self.assertEqual(sweep.calendar_window(date(2026, 12, 31))[1], date(2027, 1, 8))    # a Thursday
        self.assertEqual(sweep.calendar_window(date(2027, 1, 1))[1], date(2027, 1, 8))      # a Friday: +7
        self.assertEqual(sweep.calendar_window(date(2027, 1, 3))[1], date(2027, 1, 8))      # a Sunday: +5
        self.assertEqual(sweep.calendar_window(date(2026, 10, 24))[1], date(2026, 10, 30))  # a Saturday: +6


class Span(unittest.TestCase):

    def setUp(self):
        p = mock.patch.object(paths, "load_settings", return_value={})
        p.start()
        self.addCleanup(p.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cal = Path(self.tmp.name) / "calendar.json"
        q = mock.patch.object(paths, "CALENDAR", self.cal)
        q.start()
        self.addCleanup(q.stop)

    def span(self, data, today=date(2026, 10, 22)):
        self.cal.write_text(json.dumps(data))
        return tuple(d.isoformat() for d in sweep.calendar_span(today))

    def test_a_calendar_read_to_the_friday_holds_to_it(self):
        self.assertEqual(self.span({"fetched": "2026-10-22 07:00", "to": "2026-10-30", "days": {}}), ("2026-10-19", "2026-10-30"))

    def test_a_calendar_saved_before_the_read_to_day_counts_as_seven_days(self):
        self.assertEqual(self.span({"fetched": "2026-10-22 07:00", "days": {}}), ("2026-10-19", "2026-10-29"))

    def test_a_calendar_read_on_an_earlier_day_stops_where_it_was_read_to(self):
        self.assertEqual(self.span({"fetched": "2026-10-19 07:00", "to": "2026-10-30", "days": {}}, date(2026, 10, 26)),
                         ("2026-10-26", "2026-10-30"))                           # window from Monday 19th is the old week's
        self.assertEqual(self.span({"fetched": "2026-10-19 07:00", "to": "2026-10-30", "days": {}}, date(2026, 10, 22)),
                         ("2026-10-19", "2026-10-30"))

    def test_no_calendar_holds_nothing(self):
        self.cal.unlink(missing_ok=True)
        self.assertIsNone(sweep.calendar_span(date(2026, 10, 22)))

    def test_a_fetch_gap_is_worked_out_from_where_it_was_read_to(self):
        self.cal.write_text(json.dumps({"fetched": "2026-10-19 07:00", "to": "2026-10-30", "days": {}}))
        self.assertEqual(sweep.calendar_fetch_from(date(2026, 10, 22)), date(2026, 10, 22))     # still held: from today
        self.cal.write_text(json.dumps({"fetched": "2026-10-05 07:00", "to": "2026-10-16", "days": {}}))
        with mock.patch.object(paths, "load_settings", return_value={"inbox": {"meetings_from": "20"}}):
            self.assertEqual(sweep.calendar_fetch_from(date(2026, 10, 22)), date(2026, 10, 17))     # a gap: from the day after


class Saved(unittest.TestCase):
    """sweep.py calendar writes what it was read to."""

    def test_the_saved_calendar_names_its_last_day(self):
        v = fx.Vault()
        self.addCleanup(v.cleanup)
        fx.world(v)
        spec = v.root / "system/staging/drafts/calendar.json"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(json.dumps({"days": {"2026-10-13": [fx.ev("z1", "09:00", "09:30", "ABC check-in")]}}))
        out = fx.py(v, "import sweep; sweep.calendar('system/staging/drafts/calendar.json'); "
                       "print(json.dumps(json.load(open('system/staging/calendar.json'))['to']))")
        self.assertEqual(out, "2026-10-23")                                      # Tuesday 13-10-2026: the Friday of next calendar week


def unread_world(v):
    """The fixture calendar, read to Wednesday 21-10-2026: Thursday 22nd and Friday 23rd are not read yet."""
    fx.world(v)
    f = v.root / "system/staging/calendar.json"
    f.write_text(json.dumps({**fx.CALENDAR, "to": "2026-10-21"}))


class Days(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.v = fx.Vault()
        unread_world(cls.v)
        cls.d = fx.days(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_the_line_runs_to_next_week_s_friday_and_marks_the_unread_days(self):
        self.assertEqual((self.d["last"], self.d["read_to"]), ("2026-10-23", "2026-10-21"))
        got = {x["date"]: x.get("unread", False) for x in self.d["days"]}
        self.assertEqual(list(got)[-3:], ["2026-10-21", "2026-10-22", "2026-10-23"])
        self.assertEqual([k for k, u in got.items() if u], ["2026-10-22", "2026-10-23"])
        self.assertEqual([m["title"] for m in next(x for x in self.d["days"] if x["date"] == "2026-10-21")["meetings"]],
                         ["Beyond the calendar"])                                # read, so its meeting shows

    def test_an_unread_day_has_no_meetings_to_show(self):
        for x in self.d["days"]:
            if x.get("unread"):
                self.assertEqual((x["meetings"], x["all_day"]), ([], []))

    def test_prep_works_for_a_day_the_calendar_holds_and_is_refused_beyond_it(self):
        ok = fx.context(self.v, "2026-10-21|09:00|Beyond the calendar")
        self.assertNotIn("error", ok)
        self.assertEqual(fx.context(self.v, "2026-10-22|09:00|Anything")["error"],
                         "22-10-2026 is beyond the saved calendar, which runs to 21-10-2026; refresh the calendar.")


class UnreadDays(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        unread_world(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": fx.NOW}

    def setUp(self):
        super().setUp()
        self.b.call("Emulation.setFocusEmulationEnabled", enabled=True)
        pin_page_clock(self.b, fx.NOW)
        self.b.eval("go('today')")
        self.b.wait(f"{TABS}.length>1")

    def band(self):
        return self.b.eval("document.querySelector('#v-today .dayband').innerText")

    def test_the_line_reaches_friday_and_an_unread_day_says_so_with_refresh(self):
        b = self.b
        self.assertEqual(b.eval(f"{TABS}.map(t=>t.dataset.tab).slice(-3)"), ["2026-10-21", "2026-10-22", "2026-10-23"])
        b.click('#todayDate [data-tab="2026-10-22"]')
        self.assertEqual(b.eval("document.getElementById('dayHead').textContent"), "Thursday has not been read yet, Alan.")
        self.assertEqual(b.eval("document.querySelector('#dayMeets .daynone span').textContent"), "Not read yet")
        self.assertEqual(b.eval("document.querySelector('#dayMeets [data-refcal]').textContent"), "Refresh calendar")
        self.assertNotIn("No meetings", self.band())
        self.assertNotIn("day is yours", self.band())

    def test_a_read_day_past_next_week_s_monday_still_shows_its_meeting(self):
        b = self.b
        b.click('#todayDate [data-tab="2026-10-21"]')
        self.assertEqual(b.eval("document.getElementById('dayHead').textContent"), "One meeting, Alan, with the afternoon wide open.")
        self.assertEqual(b.eval("document.querySelectorAll('#dayMeets .dm').length"), 1)

    def test_the_keyboard_reaches_the_last_day(self):
        b = self.b
        b.eval(f"{TABS}[0].focus()")
        b.key("End")
        self.assertEqual((b.eval("document.querySelector('#todayDate [aria-selected=\"true\"]').dataset.tab"),
                          b.eval("document.activeElement.dataset.tab")), ("2026-10-23", "2026-10-23"))
        self.assertEqual(b.eval("document.querySelector('#dayMeets [data-refcal]').tagName"), "BUTTON")
        self.assertTrue(b.eval("document.querySelector('.dayedge.r').disabled"))

    def test_at_900_px_the_line_does_not_scroll_sideways(self):
        b = self.b
        b.resize(900, 800)
        b.pump(0.3)
        b.eval("goDay('2026-10-23')")
        self.assertEqual(b.eval("(()=>{ const d=document.scrollingElement; return d.scrollWidth-d.clientWidth; })()"), 0)


if __name__ == "__main__":
    unittest.main()
