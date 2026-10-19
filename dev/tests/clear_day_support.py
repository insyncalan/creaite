"""Shared fixture for the BL-104 Clear day tests (test_clear_day.py, test_clear_day_thursday.py, test_clear_day_sunday.py): the data and page mixins, run on three pinned days."""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import pin_page_clock  # noqa: E402
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
    """Real clicks on the live page. The vault has a fictional calendar for the pinned week."""
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
        b.eval("go('inbox',null,{legacy:true})")
        b.wait("document.querySelector('#mtgBody tr[data-mid]')")
        return b

    def titles(self):
        return self.b.eval("[...document.querySelectorAll('#mtgBody tr[data-mid] td.title')].map(t=>t.firstChild.textContent.trim())")

    def mon_day(self):
        return self.mon.isoformat()

    def day_titles(self, day):
        """Titles of the rows under one day's heading."""
        return self.b.eval("""(day=>{ const out=[]; let on=false; for(const tr of document.querySelectorAll('#mtgBody tbody tr')){
          if(tr.classList.contains('mtgday')){ on=!!tr.querySelector('[data-day="'+day+'"]'); continue; }
          if(on) out.push(tr.querySelector('td.title').firstChild.textContent.trim()); } return out; })(%s)""" % json.dumps(day))

    def clear_button(self, day):
        return f'#mtgBody .mtgclr[data-clr="day"][data-day="{day}"]'

    def cleared_file(self):
        p = self.v.root / "system/staging/intake-cleared.json"
        return json.loads(p.read_text())["cleared"] if p.exists() else []

    def clear(self, selector, day=None):
        """Click a Clear control and wait until the clearing has finished: its "Cleared …" message is the last thing it does.
        dev-test-steadiness: the day's rows and its button go when the page reloads its data, before that message and its
        Undo; under load a test that went on when the button went found no message, or an Undo with no size."""
        b = self.b
        b.eval("document.getElementById('snackT').textContent=''")
        b.click(selector)
        self.wait_cleared(day)

    def wait_cleared(self, day=None):
        self.b.wait("/^Cleared /.test(document.getElementById('snackT').textContent)", 20)
        if day:
            self.b.wait(f"!document.querySelector('{self.clear_button(day)}')")

    def test_clear_day_removes_the_days_meetings_and_they_stay_gone(self):
        b = self.go_intake()
        day = self.mon_day()
        n = len(self.day_titles(day))
        self.assertGreaterEqual(n, 2)
        self.assertEqual(b.eval(f"document.querySelector('{self.clear_button(day)}').textContent"), f"Clear day · {n}")
        processed = self.v.root / "system/processed.txt"
        before = processed.read_text() if processed.exists() else None
        self.clear(self.clear_button(day), day)
        self.assertEqual(self.day_titles(day), [])
        self.assertIn("Cleared", b.eval("document.getElementById('snackT').textContent"))
        self.assertTrue(b.eval("document.getElementById('snackU').offsetParent!==null"))          # Undo is offered
        self.assertEqual(sorted(e["key"] for e in self.cleared_file()), ["ev-1", "ev-2"] + (["ev-3"] if self.today == self.mon else []))
        self.assertEqual(before, processed.read_text() if processed.exists() else None)            # not processed
        # after a refresh of the page and after the sweep re-reads the calendar, they are still gone
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('inbox',null,{legacy:true})")
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
        self.clear(self.clear_button(day), day)
        cal = json.loads((self.v.root / "system/staging/calendar.json").read_text())
        cal["days"][day].append({"id": "ev-late", "start": "17:00", "end": "17:30", "title": "Late invite", "teams": True})
        (self.v.root / "system/staging/calendar.json").write_text(json.dumps(cal))
        b.eval("reloadData()")
        b.wait("D.meetings.rows.some(r=>r.id==='ev-late')")
        self.assertEqual(self.day_titles(day), ["Late invite"])

    def test_undo_brings_them_back(self):
        b = self.go_intake()
        day = self.mon_day()
        n = len(self.day_titles(day))
        self.clear(self.clear_button(day), day)
        b.click("#snackU")
        b.wait(f"document.querySelector('{self.clear_button(day)}')")
        self.assertEqual(len(self.day_titles(day)), n)
        self.assertEqual(self.cleared_file(), [])

    def test_cleared_list_restore_and_restore_day_and_per_meeting_x(self):
        b = self.go_intake()
        day = self.mon_day()
        n = len(self.day_titles(day))
        # the per-meeting ×
        self.clear('#mtgBody tr[data-mid="ev-2"] .mtgx')
        b.wait("!document.querySelector('#mtgBody tr[data-mid=\"ev-2\"]')")
        self.assertEqual(len(self.day_titles(day)), n - 1)
        self.assertEqual(b.eval("document.querySelector('#mtgBody .mtgcleared .clrlink').textContent"), "Cleared (1)")
        # the list: grouped by day, each with Restore
        b.click("#mtgBody .mtgcleared .clrlink")
        b.wait("document.querySelector('#mtgBody .mtgclrlist')")
        self.assertEqual(b.eval("[...document.querySelectorAll('#mtgBody .clrrow')].map(r=>r.textContent)")[0].count("Weekly sync 12"), 1)
        b.click('#mtgBody .mtgclr[data-clr="restore"]')
        b.wait("document.querySelector('#mtgBody tr[data-mid=\"ev-2\"]')")
        self.assertEqual(len(self.day_titles(day)), n)
        self.assertFalse(b.eval("!!document.querySelector('#mtgBody .mtgcleared')"))              # nothing cleared: no link
        # Restore day
        self.clear(self.clear_button(day), day)
        b.click("#mtgBody .mtgcleared .clrlink")
        b.wait("document.querySelector('#mtgBody .mtgclrlist')")
        b.click('#mtgBody .mtgclr[data-clr="restoreday"]')
        b.wait(f"document.querySelector('{self.clear_button(day)}')")
        self.assertEqual(len(self.day_titles(day)), n)

    def test_cleared_meetings_are_not_selectable(self):
        b = self.go_intake()
        self.clear('#mtgBody tr[data-mid="ev-1"] .mtgx')
        b.wait("!document.querySelector('#mtgBody tr[data-mid=\"ev-1\"]')")
        b.click("#mtgNew")
        picked = b.eval("[...MSEL]")
        self.assertNotIn("ev-1", picked)
        self.assertIn("ev-2", picked)
        # the rail's one Intake and Review entry (#232; the Intake entry and #inboxBadge went with it) counts proposals, never a cleared meeting
        self.assertEqual(b.eval("document.getElementById('revBadge').textContent"), str(b.eval("REV.filter(r=>!r.done).length")))
        self.assertFalse(b.eval("D.intake_review.meetings.some(m=>m.key==='ev-1')"))                   # and the new page's model has no row for it either

    def test_safeguard_asks_before_clearing_an_unprocessed_transcript(self):
        b = self.go_intake()
        day = self.mon_day()
        n = len(self.day_titles(day))
        # the sweep's transcript check (BL-42 phase 3) isn't built yet: give two rows a sample status
        b.eval("D.meetings.rows.filter(r=>r.id==='ev-1'||r.id==='ev-2').forEach(r=>r.transcript='available'); renderMeetings()")
        b.click(self.clear_button(day))
        b.wait("document.querySelector('#mtgBody .mtgconfirm')")
        self.assertEqual(b.eval("document.querySelector('#mtgBody .mtgconfirm span').textContent"),
                         "2 of these have transcripts you haven't processed. Clear anyway?")
        self.assertEqual(self.cleared_file(), [])                                                  # nothing cleared yet
        b.click('#mtgBody [data-clr="no"]')
        b.wait("!document.querySelector('#mtgBody .mtgconfirm')")
        self.assertEqual(len(self.day_titles(day)), n)
        b.click(self.clear_button(day))
        b.wait("document.querySelector('#mtgBody .mtgconfirm')")
        self.clear('#mtgBody [data-clr="yes"]', day)
        self.assertEqual(self.day_titles(day), [])
        # a processed transcript doesn't trigger it
        self.assertTrue(len(self.cleared_file()) >= 2)

    def test_a_processed_transcript_clears_without_asking(self):
        b = self.go_intake()
        day = self.mon_day()
        b.eval("D.meetings.rows.filter(r=>r.id==='ev-1'||r.id==='ev-2').forEach(r=>{ r.transcript='available'; r.processed='%s'; }); renderMeetings()" % day)
        self.clear(self.clear_button(day), day)
        self.assertFalse(b.eval("!!document.querySelector('#mtgBody .mtgconfirm')"))
