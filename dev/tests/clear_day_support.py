"""Shared fixture for the BL-104 Clear day tests (test_clear_day.py, test_clear_day_thursday.py, test_clear_day_sunday.py): the data mixin, run on three pinned days. (#232 C2: the page mixin, ClearDayPage, went with Calendar import's Clear day; the Intake page sets meetings aside one at a time, Not needed and Later: test_intake_review_intake.)"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
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
