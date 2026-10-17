"""BL-104 clear (Sprint 4a), now Not needed with a reason (#179): set meetings aside in Intake, in a real browser against the real
live server, plus the data rules behind it.

Run: python3 dev/tests/test_clear_day.py   (the page tests need Google Chrome; skipped otherwise)

Cleared is not processed: processed.txt and the tracker are never touched. The meetings come back with Restore.

The clock is pinned (CREAITE_NOW for the scripts and the live server, a Date shim in the page) and every test runs on a
Monday (Monday is today), a Thursday and a Sunday (the last day of the window), so the result never depends on the real
weekday.
"""
import json
import os
import subprocess
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_meetings import page_data, week_calendar  # noqa: E402
from test_tracker import Vault  # noqa: E402


def keys_of(rows):
    return sorted(r["key"] for r in rows)


# Each day at 18:00, so today's meetings have all ended. 05-10-2026 is a Monday.
MONDAY, THURSDAY, SUNDAY = "2026-10-05 18:00", "2026-10-08 18:00", "2026-10-11 18:00"


def pinned_day(now):
    return datetime.strptime(now, "%Y-%m-%d %H:%M").date()


class ClearData:
    """The file, the window and the rows the dashboard is built from."""
    NOW = None

    def setUp(self):
        old = os.environ.get("CREAITE_NOW")
        os.environ["CREAITE_NOW"] = self.NOW                         # the scripts below inherit it
        self.addCleanup(lambda: os.environ.pop("CREAITE_NOW") if old is None else os.environ.update(CREAITE_NOW=old))
        self.v = v = Vault()
        v.run("init")
        self.mon, self.today = week_calendar(v, today=pinned_day(self.NOW))

    def tearDown(self):
        self.v.cleanup()

    def cleared_file(self):
        p = self.v.root / "system/staging/intake-cleared.json"
        return json.loads(p.read_text()) if p.exists() else None

    def py(self, code):
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0,'system/scripts'); import build_dashboard as b\n" + code],
                           cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_cleared_meetings_leave_the_rows_and_are_listed_apart(self):
        v = self.v
        self.py(f"b.clear_meetings([{{'key':'ev-1','day':'{self.mon}','start':'09:00','title':'ABC Steering'}}])")
        v.run(script="build_dashboard.py")
        m = page_data(v)["meetings"]
        self.assertNotIn("ev-1", [r["id"] for r in m["rows"]])
        self.assertIn("ev-2", [r["id"] for r in m["rows"]])                       # only what was listed
        self.assertEqual([r["id"] for r in m["cleared"]], ["ev-1"])
        self.assertEqual(self.cleared_file()["cleared"][0]["key"], "ev-1")
        self.assertEqual(self.cleared_file()["cleared"][0]["cleared"], self.today.isoformat())

    def test_a_meeting_without_an_id_is_kept_by_day_time_and_title(self):
        week_calendar(self.v, with_ids=False, today=self.today)
        self.v.run(script="build_dashboard.py")
        row = next(r for r in page_data(self.v)["meetings"]["rows"] if r["title"] == "ABC Steering")
        self.assertEqual(row["key"], f"{self.mon}|09:00|ABC Steering")
        self.py(f"b.clear_meetings([{{'key':{row['key']!r},'day':'{self.mon}','start':'09:00','title':'ABC Steering'}}])")
        self.v.run(script="build_dashboard.py")
        self.assertNotIn("ABC Steering", [r["title"] for r in page_data(self.v)["meetings"]["rows"]])

    def test_a_meeting_added_later_is_new_and_old_entries_are_dropped(self):
        v = self.v
        self.py(f"b.clear_meetings([{{'key':'ev-1','day':'{self.mon}','start':'09:00','title':'ABC Steering'}}, "
                f"{{'key':'ev-old','day':'2020-01-01','start':'09:00','title':'Ancient'}}])")
        cal = json.loads((v.root / "system/staging/calendar.json").read_text())
        cal["days"][self.mon.isoformat()].append({"id": "ev-new", "start": "16:00", "end": "16:30", "title": "Added later", "teams": True})
        (v.root / "system/staging/calendar.json").write_text(json.dumps(cal))        # as if the next sweep re-read the calendar
        v.run(script="build_dashboard.py")
        m = page_data(v)["meetings"]
        self.assertIn("ev-new", [r["id"] for r in m["rows"]])
        self.assertNotIn("ev-1", [r["id"] for r in m["rows"]])
        self.assertEqual([r["id"] for r in m["cleared"]], ["ev-1"])
        self.assertEqual([e["key"] for e in json.loads(self.py("import json; print(json.dumps(b.cleared_load()))"))], ["ev-1"])   # the old entry is dropped

    def test_restore_by_key_and_by_day_and_nothing_else_is_touched(self):
        v = self.v
        before = (v.root / "system/processed.txt").read_text() if (v.root / "system/processed.txt").exists() else None
        self.py(f"b.clear_meetings([{{'key':'ev-1','day':'{self.mon}','start':'09:00','title':'a'}},"
                f"{{'key':'ev-2','day':'{self.mon}','start':'15:00','title':'b'}}])")
        self.assertEqual(self.py("print(b.restore_meetings(keys=['ev-1']))").strip(), "1")
        self.assertEqual([e["key"] for e in self.cleared_file()["cleared"]], ["ev-2"])
        self.assertEqual(self.py(f"print(b.restore_meetings(day='{self.mon}'))").strip(), "1")
        self.assertEqual(self.cleared_file()["cleared"], [])
        after = (v.root / "system/processed.txt").read_text() if (v.root / "system/processed.txt").exists() else None
        self.assertEqual(before, after)                                                  # cleared is not processed

    def test_a_bad_day_is_refused(self):
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0,'system/scripts'); import build_dashboard as b\n"
                            "b.clear_meetings([{'key':'x','day':'nonsense','start':'','title':''}])"],
                           cwd=self.v.root, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIsNone(self.cleared_file())


class ClearDayPage:
    """Real clicks on the live page (#179: Not needed, with a reason, replaced Clear day and the per-row cross). The vault has a
    fictional calendar for the pinned week; none of its meetings has a transcript status yet, so they are rows under Waiting."""
    NOW = None

    @classmethod
    def load(cls, v):
        populate(v)
        cls.mon, cls.today = week_calendar(v, today=pinned_day(cls.NOW))

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": cls.NOW}

    def setUp(self):
        super().setUp()
        pin_page_clock(self.b, self.NOW)                              # the page's TODAY and "not happened yet" too
        self.assertEqual(self.b.eval("TODAY"), self.today.isoformat())

    def go_intake(self):
        b = self.b
        b.eval("go('inbox')")
        b.wait("document.querySelector('#mtgBody .inrow[data-mid]')")
        return b

    def titles(self):
        return self.b.eval("[...document.querySelectorAll('#mtgBody .inrow[data-mid] .int')].map(t=>t.textContent.trim())")

    def mon_day(self):
        return self.mon.isoformat()

    def cleared_file(self):
        p = self.v.root / "system/staging/intake-cleared.json"
        return json.loads(p.read_text())["cleared"] if p.exists() else []

    def not_needed(self, mid, reason="No decisions"):
        """Not needed on a row, a reason from the menu; waits for the message that is the last thing it does."""
        b = self.b
        b.eval("document.getElementById('snackT').textContent=''")
        b.click(f'#mtgBody [data-mid="{mid}"] [data-ia=not]')
        b.wait("document.getElementById('inNotMenu')")
        b.eval("[...document.querySelectorAll('#inNotMenu [role=menuitem]')].find(x=>x.textContent.trim()==%s).click()" % json.dumps(reason))
        b.wait("/^Not needed/.test(document.getElementById('snackT').textContent)", 20)
        b.wait(f"!document.querySelector('#mtgBody [data-mid=\"{mid}\"]')")

    def test_not_needed_removes_the_meeting_and_it_stays_gone(self):
        b = self.go_intake()
        n = len(self.titles())
        self.assertIn("ABC Steering", self.titles())
        processed = self.v.root / "system/processed.txt"
        before = processed.read_text() if processed.exists() else None
        self.not_needed("ev-1")
        self.assertNotIn("ABC Steering", self.titles())
        self.assertEqual(len(self.titles()), n - 1)
        self.assertIn("Not needed: No decisions", b.eval("document.getElementById('snackT').textContent"))
        self.assertTrue(b.eval("document.getElementById('snackU').offsetParent!==null"))          # Undo is offered
        self.assertEqual(keys_of(self.cleared_file()), ["ev-1"])
        self.assertEqual(before, processed.read_text() if processed.exists() else None)            # not processed
        # after a refresh of the page and after the sweep re-reads the calendar, it is still gone
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('inbox')")
        b.wait("document.getElementById('mtgBody').textContent.length>0")
        self.assertNotIn("ABC Steering", self.titles())
        cal = json.loads((self.v.root / "system/staging/calendar.json").read_text())
        (self.v.root / "system/staging/calendar.json").write_text(json.dumps(cal))
        b.eval("reloadData()")
        b.wait("!D.meetings.rows.some(r=>r.id==='ev-1')")
        self.assertNotIn("ABC Steering", self.titles())

    def test_a_meeting_added_to_a_cleared_day_shows_as_new(self):
        b = self.go_intake()
        day = self.mon_day()
        self.not_needed("ev-1")
        self.not_needed("ev-2")
        cal = json.loads((self.v.root / "system/staging/calendar.json").read_text())
        cal["days"][day].append({"id": "ev-late", "start": "17:00", "end": "17:30", "title": "Late invite", "teams": True})
        (self.v.root / "system/staging/calendar.json").write_text(json.dumps(cal))
        b.eval("reloadData()")
        b.wait("D.meetings.rows.some(r=>r.id==='ev-late')")
        self.assertIn("Late invite", self.titles())
        self.assertNotIn("ABC Steering", self.titles())

    def test_undo_brings_it_back(self):
        b = self.go_intake()
        n = len(self.titles())
        self.not_needed("ev-1")
        b.click("#snackU")
        b.wait("document.querySelector('#mtgBody [data-mid=\"ev-1\"]')")
        self.assertEqual(len(self.titles()), n)
        self.assertEqual(self.cleared_file(), [])

    def test_cleared_list_restore_and_restore_day(self):
        b = self.go_intake()
        n = len(self.titles())
        self.not_needed("ev-2", "Informal chat")
        self.assertEqual(len(self.titles()), n - 1)
        self.assertEqual(b.eval("document.querySelector('#mtgBody .mtgcleared .clrlink').textContent"), "Cleared (1)")
        # the list: grouped by day, each with Restore, and the reason it was set aside
        b.click("#mtgBody .mtgcleared .clrlink")
        b.wait("document.querySelector('#mtgBody .mtgclrlist')")
        row = b.eval("[...document.querySelectorAll('#mtgBody .clrrow')].map(r=>r.textContent)")[0]
        self.assertEqual(row.count("Weekly sync 12"), 1)
        self.assertIn("Informal chat", row)
        b.click('#mtgBody .mtgclr[data-clr="restore"]')
        b.wait("document.querySelector('#mtgBody [data-mid=\"ev-2\"]')")
        self.assertEqual(len(self.titles()), n)
        self.assertFalse(b.eval("!!document.querySelector('#mtgBody .mtgcleared')"))              # nothing cleared: no link
        # Restore day
        self.not_needed("ev-1")
        self.not_needed("ev-2")
        b.click("#mtgBody .mtgcleared .clrlink")
        b.wait("document.querySelector('#mtgBody .mtgclrlist')")
        b.click('#mtgBody .mtgclr[data-clr="restoreday"]')
        b.wait("document.querySelector('#mtgBody [data-mid=\"ev-1\"]') && document.querySelector('#mtgBody [data-mid=\"ev-2\"]')")
        self.assertEqual(len(self.titles()), n)

    def test_cleared_meetings_are_not_ready(self):
        """A meeting with a transcript that is set aside leaves Ready, Process all ready and the badge."""
        b = self.go_intake()
        b.eval("D.meetings.rows.forEach(r=>{ if(r.id==='ev-1'||r.id==='ev-2') r.transcript='available'; }); renderMeetings()")
        self.assertEqual(b.eval("readyList().filter(r=>r.kind==='m').map(r=>r.m.id).sort()"), ["ev-1", "ev-2"])
        self.not_needed("ev-1")
        b.eval("D.meetings.rows.forEach(r=>{ if(r.id==='ev-2') r.transcript='available'; }); renderMeetings()")
        self.assertEqual(b.eval("readyList().filter(r=>r.kind==='m').map(r=>r.m.id)"), ["ev-2"])
        self.assertEqual(b.eval("document.getElementById('inboxBadge').textContent"), str(b.eval("readyCount()")))


class ClearDataMonday(ClearData, unittest.TestCase):
    NOW = MONDAY


class ClearDataThursday(ClearData, unittest.TestCase):
    NOW = THURSDAY


class ClearDataSunday(ClearData, unittest.TestCase):
    NOW = SUNDAY


class ClearDayPageMonday(ClearDayPage, LiveBrowserCase):
    NOW = MONDAY


class ClearDayPageThursday(ClearDayPage, LiveBrowserCase):
    NOW = THURSDAY


class ClearDayPageSunday(ClearDayPage, LiveBrowserCase):
    NOW = SUNDAY


if __name__ == "__main__":
    unittest.main()
