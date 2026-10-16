"""#138 and #147: which days Today's day line lists, in the browser.

Run: python3 dev/tests/test_day_band_ui.py   (Chrome tier; skipped without Chrome)
#138: a weekend day (settings work.weekend_days) is a tab only when something is planned on it (a meeting on the saved
calendar, or an open action, RAID item or milestone dated that day); today on a weekend always is; a changed work.weekend_days is
followed; the arrows, [ ], the tab keys and the saved choice cross the gap. Every case runs at desktop width and at 900 px.
Over test_today_days's fixture (Tuesday 13-10-2026 11:05; Saturday 17th holds only an all-day entry, Sunday 18th a meeting and a
DEF action due that day) with the calendar, the tracker or the clock changed per class.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_today_days as fx  # noqa: E402  (fixes CREAITE_NOW and the fixture's TODAY on import)
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402
from test_tracker import action  # noqa: E402

TABS = "[...document.querySelectorAll('#todayDate [role=tab]')]"
SEL = "document.querySelector('#todayDate [aria-selected=\"true\"]')"
MON_TO_TUE = ["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16"]


class Band(LiveBrowserCase):
    """The fixture's vault and server; a subclass says what to change (`tweak`) and the clock (`now`)."""
    shared_server = True
    now = fx.NOW

    @classmethod
    def tweak(cls, v):
        pass

    @classmethod
    def load(cls, v):
        fx.world(v)
        cls.tweak(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": cls.now}

    def setUp(self):
        super().setUp()
        pin_page_clock(self.b, self.now)
        self.b.eval("go('today')")
        self.b.wait(f"{TABS}.length>1")

    def dates(self):
        return self.b.eval(f"{TABS}.map(t=>t.dataset.tab)")

    def chosen(self):
        return self.b.eval(f"{SEL}.dataset.tab")


def write_calendar(v, days, fetched=fx.CALENDAR["fetched"]):
    (v.root / "system/staging/calendar.json").write_text(json.dumps({"fetched": fetched, "days": days}))


def set_weekend(v, names):
    p = v.root / "system/config/settings.json"
    s = json.loads(p.read_text())
    s.setdefault("work", {})["weekend_days"] = names
    p.write_text(json.dumps(s))


def clear_the_weekend(v):
    """The fixture's DEF action due on the Sunday is moved to the Monday: nothing is then dated on the weekend."""
    v.propose("move", [{"n": 1, "op": "update", "table": "actions", "id": "DEF-A-001", "changes": {"due_date": "2026-10-19"},
                        "decision": "approved"}])
    v.run("apply")


class WeekendDays:
    """#138 over the fixture as it is: Saturday out, Sunday in (a meeting and a DEF action), the gap crossed by every way of moving."""

    def test_saturday_with_only_an_all_day_entry_is_out_and_sunday_with_a_meeting_is_in(self):
        self.assertEqual(self.dates(), MON_TO_TUE + ["2026-10-18", "2026-10-19", "2026-10-20"])
        self.assertEqual(self.b.eval("document.querySelectorAll('#todayDate .daysep').length"), 6)    # the line closed up: no gap marker

    def test_the_gap_is_crossed_by_the_arrows_the_brackets_and_the_tab_keys(self):
        b = self.b
        b.click('#todayDate [data-tab="2026-10-16"]')
        b.eval("document.querySelector('.dayedge.r').click()")
        self.assertEqual(self.chosen(), "2026-10-18")                        # Friday › Sunday
        b.eval("document.querySelector('.dayedge.l').click()")
        self.assertEqual(self.chosen(), "2026-10-16")
        b.key("]")
        self.assertEqual(self.chosen(), "2026-10-18")
        b.key("[")
        self.assertEqual(self.chosen(), "2026-10-16")
        b.eval(f"{SEL}.focus()")
        b.key("ArrowRight")
        self.assertEqual((self.chosen(), b.eval("document.activeElement.dataset.tab")), ("2026-10-18", "2026-10-18"))
        b.key("ArrowLeft")
        self.assertEqual(self.chosen(), "2026-10-16")

    def test_a_day_that_is_not_in_the_line_cannot_be_chosen_and_the_choice_holds(self):
        b = self.b
        b.click('#todayDate [data-tab="2026-10-18"]')
        self.assertEqual(self.chosen(), "2026-10-18")                        # the weekend day with a plan can be chosen
        self.assertEqual(b.eval("goDay('2026-10-17')"), False)               # Saturday has nothing: not offered
        self.assertEqual(self.chosen(), "2026-10-18")
        b.eval("go('work')")
        b.eval("go('today')")
        self.assertEqual(self.chosen(), "2026-10-18")                        # the choice is kept across a visit elsewhere

    def test_nothing_scrolls_sideways(self):
        self.assertEqual(self.b.eval("document.scrollingElement.scrollWidth-document.scrollingElement.clientWidth"), 0)


class TestWeekendDesktop(WeekendDays, Band):
    pass


class TestWeekend900(WeekendDays, Band):
    width, height = 900, 900


class SaturdayItem:
    """A weekend day with only a dated item shows; one dated item per kind is enough to be planned for."""

    @classmethod
    def tweak(cls, v):
        days = dict(fx.CALENDAR["days"])
        days.pop("2026-10-18")                                              # no Sunday meeting: its DEF action is what plans it
        write_calendar(v, days)
        v.propose("sat", [action(20, description="Hand over the cutover pack", due_date="2026-10-17")])
        v.run("apply")

    def test_a_saturday_with_an_open_action_due_and_a_sunday_with_one_due_both_show(self):
        self.assertEqual(self.dates(), MON_TO_TUE + ["2026-10-17", "2026-10-18", "2026-10-19", "2026-10-20"])
        self.b.click('#todayDate [data-tab="2026-10-17"]')
        self.assertEqual(self.chosen(), "2026-10-17")
        self.assertEqual(self.b.eval(f"{SEL}.textContent"), "Saturday 17th October")


class TestSaturdayItemDesktop(SaturdayItem, Band):
    pass


class TestSaturdayItem900(SaturdayItem, Band):
    width, height = 900, 900


class NoWeekendPlan:
    """No meeting and nothing due on either weekend day: both are left out, and the line closes up."""

    @classmethod
    def tweak(cls, v):
        days = dict(fx.CALENDAR["days"])
        days.pop("2026-10-18")
        write_calendar(v, days)
        clear_the_weekend(v)

    def test_neither_weekend_day_is_in_the_line_or_the_key_order(self):
        b = self.b
        self.assertEqual(self.dates(), MON_TO_TUE + ["2026-10-19", "2026-10-20"])
        b.click('#todayDate [data-tab="2026-10-16"]')
        b.key("]")
        self.assertEqual(self.chosen(), "2026-10-19")                        # Friday › Monday, straight across
        b.key("[")
        self.assertEqual(self.chosen(), "2026-10-16")


class TestNoWeekendPlanDesktop(NoWeekendPlan, Band):
    pass


class TestNoWeekendPlan900(NoWeekendPlan, Band):
    width, height = 900, 900


class TodayOnASaturday:
    """Today is Saturday 17-10-2026 with nothing planned: it shows, as Today; Sunday does not."""
    now = "2026-10-17 11:05"

    @classmethod
    def tweak(cls, v):
        write_calendar(v, {"2026-10-19": fx.CALENDAR["days"]["2026-10-19"]}, fetched="2026-10-17 07:00")
        clear_the_weekend(v)

    def test_today_on_a_weekend_is_always_a_tab(self):
        tabs = self.b.eval(f"{TABS}.map(t=>[t.dataset.tab,t.textContent,t.getAttribute('aria-current')])")
        self.assertIn(["2026-10-17", "Saturday 17th October", "date"], tabs)
        self.assertNotIn("2026-10-18", self.dates())
        self.assertEqual(self.chosen(), "2026-10-17")


class TestTodayOnASaturdayDesktop(TodayOnASaturday, Band):
    pass


class TestTodayOnASaturday900(TodayOnASaturday, Band):
    width, height = 900, 900


class ChangedWeekend:
    """work.weekend_days is Thursday and Saturday: Thursday (nothing on it) drops out, the Sunday is a working day, so it stays."""

    @classmethod
    def tweak(cls, v):
        write_calendar(v, {**fx.CALENDAR["days"], "2026-10-18": []})
        set_weekend(v, ["Thursday", "Saturday"])

    def test_the_days_off_follow_the_setting(self):
        self.assertEqual(self.b.eval("S.weekendDays"), [3, 5])
        self.assertEqual(self.dates(), ["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-16", "2026-10-18", "2026-10-19", "2026-10-20"])
        self.b.click('#todayDate [data-tab="2026-10-14"]')
        self.b.key("]")
        self.assertEqual(self.chosen(), "2026-10-16")                        # Wednesday › Friday, over the Thursday


class TestChangedWeekendDesktop(ChangedWeekend, Band):
    pass


class TestChangedWeekend900(ChangedWeekend, Band):
    width, height = 900, 900


if __name__ == "__main__":
    unittest.main()
