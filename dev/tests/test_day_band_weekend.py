"""#138: a weekend day is in Today's day line only when something is planned on it.

Run: python3 dev/tests/test_day_band_weekend.py      (quick tier: no Chrome)
A weekend day (settings work.weekend_days, Saturday and Sunday by default) is listed by build_dashboard.calendar_days only when it
holds a timed meeting on the saved calendar, or an open action, an open RAID item or a milestone not yet done dated that day
(Alan, 16-10-2026: work due on a weekend counts as planned for it; the Week ahead's own move of such items to Monday is not
used here). Today is always listed. It follows a changed work.weekend_days. Unit cases over day_record, dated_work and
weekend_set, then the whole path through collect() over a small vault with the clock fixed on a Tuesday and on a Saturday.
"""
import json
import os
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "system" / "scripts"))
from test_tracker import Vault, action  # noqa: E402

import build_dashboard  # noqa: E402

SAT, SUN = date(2026, 10, 17), date(2026, 10, 18)
MEET = {"id": "m", "start": "10:00", "end": "10:30", "title": "ABC weekend cutover", "all_day": False, "private": False}
ALLDAY = {"id": "a", "start": "", "end": "", "title": "Family day", "all_day": True, "private": False}


def look(due=(), weekend=(5, 6), today="2026-10-13"):
    return {"today": today, "weekend": set(weekend), "due": set(due), "monday": date(2026, 10, 12), "hm": "11:05",
            "projects": [], "remembered": {}, "names": {}, "hot": {}, "by_id": {}, "by_time": {}, "minutes": {}, "pages": {}}


class DayRecord(unittest.TestCase):
    """day_record: the one rule."""

    def listed(self, day, events, **kw):
        return build_dashboard.day_record(day, events, look(**kw)) is not None

    def test_a_weekend_day_with_nothing_planned_is_left_out(self):
        self.assertFalse(self.listed(SAT, []))
        self.assertFalse(self.listed(SAT, None))
        self.assertFalse(self.listed(SAT, [ALLDAY]))                     # an all-day entry alone is not a plan

    def test_a_weekend_day_with_a_timed_meeting_is_listed(self):
        self.assertTrue(self.listed(SUN, [MEET]))

    def test_a_weekend_day_with_an_item_dated_that_day_is_listed(self):
        self.assertTrue(self.listed(SAT, [], due={"2026-10-17"}))
        self.assertFalse(self.listed(SUN, [], due={"2026-10-17"}))       # only the day it is dated

    def test_today_on_a_weekend_is_always_listed(self):
        self.assertTrue(self.listed(SAT, [], today="2026-10-17"))
        self.assertFalse(self.listed(SUN, [], today="2026-10-17"))

    def test_a_working_day_is_always_listed(self):
        self.assertTrue(self.listed(date(2026, 10, 15), []))

    def test_it_follows_a_changed_weekend(self):
        fri = date(2026, 10, 16)
        self.assertFalse(self.listed(fri, [], weekend=(4, 5)))           # Friday and Saturday off
        self.assertTrue(self.listed(SUN, [], weekend=(4, 5)))            # Sunday is a working day then
        self.assertTrue(self.listed(fri, [MEET], weekend=(4, 5)))
        self.assertTrue(self.listed(fri, [], due={"2026-10-16"}, weekend=(4, 5)))
        self.assertTrue(build_dashboard.day_record(SUN, [], look(weekend=(4, 5)))["weekend"] is False)
        self.assertTrue(build_dashboard.day_record(SAT, [MEET], look(weekend=(4, 5)))["weekend"])
        self.assertTrue(self.listed(SAT, [], weekend=()))                # no weekend at all: every day is a working day


class DatedWork(unittest.TestCase):
    """dated_work and weekend_set: what counts as planned, and the days off."""

    def data(self, **more):
        return {"actions": [], "raid": [], "projects": [], "settings": {}, **more}

    def test_open_work_counts_closed_work_does_not(self):
        d = self.data(actions=[{"st": "Open", "due": "2026-10-17"}, {"st": "Delayed", "due": "2026-10-24"},
                               {"st": "Closed", "due": "2026-10-31"}, {"st": "Open", "due": None}],
                      raid=[{"st": "Open", "due": "2026-10-18"}, {"st": "Closed", "due": "2026-11-01"}])
        self.assertEqual(build_dashboard.dated_work(d), {"2026-10-17", "2026-10-24", "2026-10-18"})

    def test_a_milestone_counts_until_it_is_done_or_cancelled(self):
        ms = [["Go-live", "2026-10-17", "", "ABC-M-001", None, None, "Planned"],
              ["Pilot", "2026-10-18", "done", "ABC-M-002", None, None, "Done"],
              ["Old", "2026-10-24", "", "ABC-M-003", None, None, "Cancelled"],
              ["Next one", "", "", None, None, None]]                     # the short row of a project with a next milestone only
        d = self.data(projects=[{"code": "ABC", "ms": ms}])
        self.assertEqual(build_dashboard.dated_work(d), {"2026-10-17"})
        short = self.data(projects=[{"code": "ABC", "ms": [["Next", "2026-10-17", "", None, None, None]]}])
        self.assertEqual(build_dashboard.dated_work(short), {"2026-10-17"})   # no sixth field: no error

    def test_the_days_off_come_from_the_page_settings(self):
        self.assertEqual(build_dashboard.weekend_set(self.data()), {5, 6})
        self.assertEqual(build_dashboard.weekend_set(self.data(settings={"weekendDays": [4, 5]})), {4, 5})
        self.assertEqual(build_dashboard.weekend_set(self.data(settings={"weekendDays": []})), set())


def collect_days(v, now, tweak=""):
    """The day line's dates over vault `v` with the clock on `now`, through build_dashboard.collect()."""
    code = ("import sys, json; sys.path.insert(0, 'system/scripts'); import build_dashboard; "
            "print(json.dumps([x['date'] for x in build_dashboard.collect()['days']['days']]))")
    r = subprocess.run([sys.executable, "-c", code], cwd=v.root, capture_output=True, text=True, timeout=180,
                       env={**os.environ, "CREAITE_NOW": now})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def save_calendar(v, fetched, days):
    st = v.root / "system" / "staging"
    st.mkdir(parents=True, exist_ok=True)
    (st / "calendar.json").write_text(json.dumps({"fetched": fetched, "days": days}))


def set_weekend(v, names):
    p = v.root / "system" / "config" / "settings.json"
    s = json.loads(p.read_text())
    s.setdefault("work", {})["weekend_days"] = names
    p.write_text(json.dumps(s))


class ThroughCollect(unittest.TestCase):
    """The whole path: the saved calendar, the tracker's open work, the setting and the clock."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_1_nothing_planned_the_weekend_is_out_and_the_line_closes_up(self):
        save_calendar(self.v, "2026-10-13 07:00", {"2026-10-13": [MEET | {"title": "ABC risk review"}], "2026-10-17": [ALLDAY]})
        self.assertEqual(collect_days(self.v, "2026-10-13 11:05"),
                         ["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20"])

    def test_2_a_meeting_or_an_item_dated_on_the_weekend_brings_that_day_back(self):
        save_calendar(self.v, "2026-10-13 07:00", {"2026-10-18": [MEET]})
        self.assertEqual(collect_days(self.v, "2026-10-13 11:05"),
                         ["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-18", "2026-10-19", "2026-10-20"])
        save_calendar(self.v, "2026-10-13 07:00", {})
        self.v.propose("sat", [action(1, description="Hand over the cutover pack", due_date="2026-10-17")])
        self.v.run("apply")
        self.assertEqual(collect_days(self.v, "2026-10-13 11:05"),
                         ["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-17", "2026-10-19", "2026-10-20"])

    def test_3_a_changed_weekend_moves_the_gap(self):
        save_calendar(self.v, "2026-10-13 07:00", {})
        set_weekend(self.v, ["Friday", "Sunday"])                        # Saturday is a working day now; Friday is off
        days = collect_days(self.v, "2026-10-13 11:05")
        self.assertIn("2026-10-17", days)                               # the Saturday is a working day
        self.assertNotIn("2026-10-16", days)                            # Friday: off, nothing planned
        self.assertNotIn("2026-10-18", days)
        set_weekend(self.v, ["Saturday", "Sunday"])

    def test_4_today_on_a_weekend_always_shows(self):
        save_calendar(self.v, "2026-10-17 07:00", {})
        days = collect_days(self.v, "2026-10-17 11:05")
        self.assertIn("2026-10-17", days)                               # today, a Saturday, nothing else planned
        self.assertNotIn("2026-10-18", days)


if __name__ == "__main__":
    unittest.main()
