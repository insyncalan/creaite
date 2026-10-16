"""BL-293 (sprint-today-days-server): Today moves between the calendar's days, the server and Python side.

Run: python3 dev/tests/test_today_days.py      (quick tier: no Chrome)
Covers prep refused or allowed by day (a past day, today, three days out, a day beyond the saved calendar, a calendar saved days
ago, no calendar), a prep page made for a meeting three days out (BL-98's rules: Alan's edited page is never overwritten), the
day data across a fixture calendar spanning a weekend and next week, the follow-up states (Minutes made, Transcript ready, No
transcript), confidential and private meetings, and the routes (/api/today/days, /api/prep/page's refusal). The clock is fixed on
Tuesday 13-10-2026 at 11:05; a stand-in Claude is used, so no model is called and nothing is sent.
"""
import json
import os
import re
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_dashboard  # noqa: E402
import test_decisions_prep  # noqa: E402
from test_tracker import Vault  # noqa: E402

FIXED = date(2026, 10, 13)                              # a Tuesday
for _m in (test_dashboard, test_decisions_prep):        # the fixture's dates are d(n) from each module's TODAY
    _m.TODAY = FIXED
NOW = f"{FIXED} 11:05"
os.environ["CREAITE_NOW"] = NOW                         # the scripts' clock (sweep.now, build_dashboard.clock)
DEF = "projects/DEF Digital Enablement"
FRIDAY = "2026-10-16|10:00|ABC steering"
REPLY = {"about": "The steering committee.", "notes": [], "questions": ["Is UAT booked?"], "m365": "searched"}
FAKE = r'''#!/usr/bin/env python3
import json, sys
out = lambda o: print(json.dumps(o), flush=True)
reply = json.dumps({"about": "The steering committee.", "notes": [], "questions": ["Is UAT booked?"], "m365": "searched"})
out({"type": "system", "subtype": "init", "session_id": "sess-p"})
out({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}})
out({"type": "result", "result": reply, "session_id": "sess-p"})
'''


def ev(eid, start, end, title, **more):
    return {"id": eid, "start": start, "end": end, "title": title, "where": "Teams", "teams": True, "all_day": False,
            "private": False, "organiser": "Jane Doe", "sensitivity": "normal", "body": "Agenda", "attendees": [], **more}


CALENDAR = {"fetched": f"{FIXED} 07:00", "days": {
    "2026-10-12": [ev("e1", "09:30", "10:00", "ABC weekly"), ev("e2", "11:00", "12:00", "ABC steering committee"),
                   ev("e3", "15:00", "15:30", "ABC design chat"), ev("e4", "16:00", "16:30", "DEF sync"),
                   {"id": "e5", "start": "17:00", "end": "17:30", "title": "Busy", "where": "", "teams": False, "all_day": False,
                    "private": True, "organiser": False}],
    "2026-10-13": [{"id": "a1", "start": "", "end": "", "title": "Sara Khan on leave", "all_day": True, "private": False},
                   ev("t1", "09:00", "09:30", "DEF stand-up"), ev("t2", "14:00", "15:00", "ABC risk review")],
    "2026-10-14": [ev("c1", "10:00", "11:00", "ABC board", sensitivity="confidential", where="Room 7", organiser=True, body="")],
    "2026-10-16": [ev("f1", "10:00", "11:00", "ABC steering")],
    "2026-10-17": [{"id": "s0", "start": "", "end": "", "title": "Family day", "all_day": True, "private": False}],
    "2026-10-18": [ev("s1", "10:00", "10:30", "ABC weekend cutover")],
    "2026-10-19": [ev("n1", "13:00", "14:00", "ABC weekly")],
    "2026-10-20": [ev("n2", "10:00", "10:30", "DEF sync")],
    "2026-10-21": [ev("x1", "09:00", "10:00", "Beyond the calendar")]}}


def world(v):
    """populate's portfolio (ABC, DEF), the fixture calendar, and what the follow-up reads: processed.txt (e1), transcripts.json
    (e2 available, e3 none; e4 not checked yet) and DEF's minutes filed for today's stand-up (t1)."""
    test_dashboard.populate(v)
    st = v.root / "system/staging"
    st.mkdir(parents=True, exist_ok=True)
    (st / "calendar.json").write_text(json.dumps(CALENDAR))
    (v.root / "system/processed.txt").write_text("2026-10-12 | calendar:e1 | ABC weekly\n")
    (st / "transcripts.json").write_text(json.dumps({"checked": {"e2": {"status": "available", "checked": "2026-10-12 13:00"},
                                                                 "e3": {"status": "none", "checked": "2026-10-12 16:00"}}}))
    m = v.root / DEF / "minutes" / "2026-10-13 DEF stand-up.md"
    m.parent.mkdir(parents=True, exist_ok=True)
    m.write_text("# DEF stand-up\n")


def py(v, code, env=None):
    """Run Python in the vault with its scripts on the path; its stdout's last line as JSON."""
    r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); " + code], cwd=v.root,
                       capture_output=True, text=True, timeout=120, env={**os.environ, **(env or {})})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def context(v, key):
    return py(v, f"import prep_page; print(json.dumps(prep_page.context({key!r})))")


def days(v):
    return py(v, "import build_dashboard; print(json.dumps(build_dashboard.collect()['days']))")


class PrepByDay(unittest.TestCase):
    """prep_page.context (and so cx-prep and the live server's Prep page) accepts any day the saved calendar holds from today."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        world(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_three_days_out_is_allowed(self):
        ctx = context(self.v, FRIDAY)
        self.assertNotIn("error", ctx)
        self.assertEqual((ctx["key"], ctx["day"], ctx["project"]), (FRIDAY, "2026-10-16", "ABC"))
        self.assertEqual(ctx["meeting"]["title"], "ABC steering")

    def test_today_and_tomorrow_still_work_and_a_dated_today_key_is_the_briefs(self):
        self.assertEqual(context(self.v, "14:00|ABC risk review")["day"], "2026-10-13")
        self.assertEqual(context(self.v, "2026-10-13|14:00|ABC risk review")["key"], "14:00|ABC risk review")
        self.assertEqual(context(self.v, "2026-10-14|10:00|ABC board")["day"], "2026-10-14")       # tomorrow, confidential

    def test_a_past_day_is_refused(self):
        self.assertEqual(context(self.v, "2026-10-12|11:00|ABC steering committee")["error"],
                         "That meeting was on 12-10-2026, which has passed: prep is for today and the days ahead.")

    def test_a_day_beyond_the_saved_calendar_is_refused(self):
        self.assertEqual(context(self.v, "2026-10-21|09:00|Beyond the calendar")["error"],
                         "21-10-2026 is beyond the saved calendar, which runs to 20-10-2026; refresh the calendar.")

    def test_a_meeting_not_in_the_calendar_says_so_with_its_day(self):
        self.assertEqual(context(self.v, "2026-10-16|09:00|No such meeting")["error"],
                         "That meeting isn't in the saved calendar for 16-10-2026 any more; refresh the calendar.")

    def test_a_calendar_saved_days_ago_holds_only_its_own_week(self):
        f = self.v.root / "system/staging/calendar.json"
        f.write_text(json.dumps({**CALENDAR, "fetched": "2026-10-08 07:00"}))
        try:
            self.assertIn("beyond the saved calendar, which runs to 15-10-2026", context(self.v, FRIDAY)["error"])
            self.assertEqual(days(self.v)["last"], "2026-10-15")
        finally:
            f.write_text(json.dumps(CALENDAR))

    def test_no_calendar_is_refused(self):
        f = self.v.root / "system/staging/calendar.json"
        f.rename(f.with_suffix(".away"))
        try:
            self.assertEqual(context(self.v, FRIDAY)["error"], "There is no saved calendar yet; refresh the calendar.")
            self.assertEqual(days(self.v)["days"], [])
        finally:
            f.with_suffix(".away").rename(f)

    def test_the_cli_refuses_a_past_day_with_the_reason(self):
        r = self.v.run("context", "2026-10-12|09:30|ABC weekly", script="prep_page.py", ok=False)
        self.assertIn("which has passed", r.stdout)


class PrepPageThreeDaysOut(unittest.TestCase):
    """A prep page for Friday's meeting: written into the Agendas folder by the server's own write, listed on its day, and a page
    Alan edited is never overwritten (BL-98)."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        world(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def build(self):
        return py(self.v, f"import prep_page; rel, page = prep_page.build({FRIDAY!r}, {REPLY!r}); "
                          "print(json.dumps([rel, 'Internal' in page]))")

    def test_page_is_built_listed_and_never_overwrites_alans_edits(self):
        rel, internal = self.build()
        self.assertTrue(rel.endswith("/2026-10-16 Prep - ABC steering.html"), rel)
        self.assertTrue(internal)
        friday = next(x for x in days(self.v)["days"] if x["date"] == "2026-10-16")["meetings"][0]
        self.assertEqual(friday["prep"]["key"], FRIDAY)
        self.assertEqual(friday["prep"]["page"], rel)
        self.assertTrue(friday["prep"]["stored"])                                  # BL-286's content, for the in-app page
        real = self.v.root / rel
        real.write_text(real.read_text() + "<!-- Alan's note -->")                  # Alan edits it
        again, _ = self.build()
        self.assertNotEqual(again, rel)
        self.assertIn("(2)", again)
        self.assertIn("Alan's note", real.read_text())


class DayData(unittest.TestCase):
    """build_dashboard.calendar_days (D.days and /api/today/days) over the fixture calendar."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        world(cls.v)
        cls.d = days(cls.v)
        cls.by = {x["date"]: x for x in cls.d["days"]}

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def meeting(self, day, title):
        return next(m for m in self.by[day]["meetings"] if m["title"] == title)

    def test_every_working_day_from_monday_to_the_last_day_and_a_weekend_day_only_with_a_meeting(self):
        self.assertEqual((self.d["first"], self.d["last"], self.d["today"]), ("2026-10-12", "2026-10-20", "2026-10-13"))
        self.assertEqual(list(self.by), ["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-18",
                                         "2026-10-19", "2026-10-20"])          # Saturday (all day only) out, Sunday in
        self.assertEqual(self.by["2026-10-15"]["meetings"], [])                 # a working day with no meetings stays
        sun = self.by["2026-10-18"]
        self.assertTrue(sun["weekend"])
        self.assertEqual([x["week"] for x in self.d["days"]], [0, 0, 0, 0, 0, 0, 1, 1])
        tue = self.by["2026-10-13"]
        self.assertEqual((tue["today"], tue["past"], tue["date_shown"], tue["short"], tue["long"]),
                         (True, False, "13-10-2026", "Tue 13", "Tuesday 13th October"))
        self.assertTrue(self.by["2026-10-12"]["past"])
        self.assertEqual(tue["all_day"], ["Sara Khan on leave"])
        self.assertEqual([m["start"] for m in tue["meetings"]], ["09:00", "14:00"])

    def test_follow_up_states_on_a_past_day(self):
        self.assertEqual(self.meeting("2026-10-12", "ABC weekly")["follow"]["state"], "minutes")              # processed.txt
        ready = self.meeting("2026-10-12", "ABC steering committee")["follow"]
        self.assertEqual(ready["state"], "transcript")                                                       # transcripts.json
        self.assertEqual(ready["process"], {"id": "e2", "loaded": None, "day": "2026-10-12", "start": "11:00",
                                            "title": "ABC steering committee"})
        none = self.meeting("2026-10-12", "ABC design chat")["follow"]
        self.assertEqual((none["state"], none["why"], none["checked"]), ("none", "No transcript for this meeting", True))
        unchecked = self.meeting("2026-10-12", "DEF sync")["follow"]
        self.assertEqual((unchecked["state"], unchecked["checked"]), ("none", False))
        for m in self.by["2026-10-12"]["meetings"]:
            self.assertNotIn("prep", m)                                                                      # no Prep on a past day

    def test_today_ended_meetings_follow_up_and_later_ones_prep(self):
        standup = self.meeting("2026-10-13", "DEF stand-up")
        self.assertTrue(standup["ended"])
        self.assertEqual(standup["follow"]["state"], "minutes")                                           # filed minutes
        self.assertEqual(standup["follow"]["minutes"], f"{DEF}/minutes/2026-10-13 DEF stand-up.md")
        later = self.meeting("2026-10-13", "ABC risk review")
        self.assertFalse(later["ended"])
        self.assertNotIn("follow", later)
        self.assertEqual(later["prep"], {"key": "14:00|ABC risk review", "page": None, "page_at": None, "page_at_shown": "",
                                         "stored": False})
        self.assertEqual(later["plan"], "a steering or review meeting")
        self.assertEqual(later["project_name"], "Example Programme")                                      # projects by name
        fri = self.meeting("2026-10-16", "ABC steering")
        self.assertEqual(fri["prep"]["key"], FRIDAY)

    def test_a_confidential_meeting_keeps_only_its_title_and_times(self):
        board = self.meeting("2026-10-14", "ABC board")
        self.assertTrue(board["confidential"])
        self.assertEqual(set(board), {"start", "end", "title", "private", "confidential", "ended", "id", "prep", "plan"})
        self.assertIsNone(board["plan"])                                     # not even "you organise it"
        self.assertEqual((board["start"], board["end"]), ("10:00", "11:00"))

    def test_a_private_meeting_is_busy_with_its_times_only(self):
        busy = self.by["2026-10-12"]["meetings"][-1]
        self.assertEqual(busy, {"start": "17:00", "end": "17:30", "title": "Busy", "private": True, "confidential": False,
                                "ended": True})

    def test_the_dashboard_data_carries_it_and_prep_meetings_stay_today_and_tomorrow(self):
        out = py(self.v, "import build_dashboard; d = build_dashboard.collect(); "
                         "print(json.dumps([len(d['days']['days']), sorted(d['prep']['meetings'])]))")
        self.assertEqual(out[0], 8)
        self.assertEqual(out[1], ["09:00|DEF stand-up", "14:00|ABC risk review", "2026-10-14|10:00|ABC board",
                                  "|Sara Khan on leave"])                  # unchanged: today's and tomorrow's only


sys.path.insert(0, str(HERE.parent.parent / "system/scripts"))


class WeekendRule(unittest.TestCase):
    """#138 (Alan, 16-10-2026): a weekend day is in the day line only when something is planned on it: a timed meeting, or an open
    action, RAID item or milestone due that day. Today always shows. work.weekend_days is followed."""

    LOOK = {"today": "2026-10-13", "weekend": {5, 6}, "due": set(), "names": {}, "projects": [], "remembered": {}, "hot": {}, "hm": "11:05",
            "by_id": {}, "by_time": {}, "minutes": {}, "pages": {}, "monday": date(2026, 10, 12)}

    def rec(self, day, events=None, **look):
        import build_dashboard
        return build_dashboard.day_record(day, events or [], {**self.LOOK, **look})

    def test_a_weekend_day_with_nothing_planned_is_left_out(self):
        self.assertIsNone(self.rec(date(2026, 10, 17)))
        self.assertIsNone(self.rec(date(2026, 10, 17), [{"title": "Family day", "all_day": True}]))     # an all-day note is not a plan

    def test_a_meeting_or_work_due_that_day_brings_it_in(self):
        self.assertEqual(self.rec(date(2026, 10, 17), [ev("m", "10:00", "11:00", "Offsite")])["date"], "2026-10-17")
        rec = self.rec(date(2026, 10, 17), due={"2026-10-17"})
        self.assertEqual((rec["date"], rec["weekend"], rec["meetings"]), ("2026-10-17", True, []))
        self.assertIsNone(self.rec(date(2026, 10, 18), due={"2026-10-17"}))                              # another day's work does not

    def test_today_on_a_weekend_always_shows(self):
        self.assertEqual(self.rec(date(2026, 10, 17), today="2026-10-17")["today"], True)

    def test_a_changed_weekend_is_followed_and_a_working_day_is_never_left_out(self):
        self.assertIsNone(self.rec(date(2026, 10, 16), weekend={4, 5}))                                  # Friday made a weekend day
        self.assertEqual(self.rec(date(2026, 10, 17), weekend={6})["date"], "2026-10-17")                # Saturday made a working day
        self.assertEqual(self.rec(date(2026, 10, 15))["date"], "2026-10-15")

    def test_the_planned_days_are_open_actions_raid_items_and_milestones(self):
        import build_dashboard
        items = [{"due": "2026-10-17"}, {"due": None}]
        proj = {"ms": [["UAT", "2026-10-18", "", "ABC-M-001", None, None, "Planned"], ["Done", "2026-10-24", "done", "ABC-M-002", None, None, "Done"],
                       ["Cancelled", "2026-10-25", "", "ABC-M-003", None, None, "Cancelled"]]}
        self.assertEqual(build_dashboard.planned_days({"projects": [proj]}, items), {"2026-10-17", "2026-10-18"})


class ThroughTheServer(unittest.TestCase):
    """POST /api/today/days, and the Prep page run's day check."""

    @classmethod
    def setUpClass(cls):
        from test_live_server import free_port
        cls.v = v = Vault()
        world(v)
        fake = v.root / "fake_prep.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], cwd=v.root,
                                    env={**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": str(fake)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body, stream=False):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read().decode()
        except urllib.error.HTTPError as e:
            with e:
                return {"status": e.code, **json.loads(e.read().decode())}
        if stream:
            return [json.loads(ln[6:]) for ln in raw.splitlines() if ln.startswith("data: ")]
        return json.loads(raw)

    def test_1_days_route_gives_every_day_or_one(self):
        out = self.post("/api/today/days", {})
        self.assertTrue(out["ok"])
        self.assertEqual(len(out["days"]), 8)
        one = self.post("/api/today/days", {"day": "2026-10-16"})
        self.assertEqual([x["date"] for x in one["days"]], ["2026-10-16"])
        self.assertEqual(self.post("/api/today/days", {"day": "Friday"})["status"], 400)
        logs = "".join(f.read_text() for f in (self.v.root / "system/logs").glob("debug-*.log"))
        line = next(ln for ln in logs.splitlines() if "days:" in ln)
        self.assertIn("8 day(s), 12 meeting(s)", line)
        self.assertNotIn("ABC", line)                                       # counts only, never a title

    def test_2_prep_page_run_refuses_a_past_day_and_builds_three_days_out(self):
        refused = self.post("/api/prep/page", {"key": "2026-10-12|11:00|ABC steering committee"})
        self.assertEqual((refused["ok"], refused["message"]),
                         (False, "That meeting was on 12-10-2026, which has passed: prep is for today and the days ahead."))
        beyond = self.post("/api/prep/page", {"key": "2026-10-21|09:00|Beyond the calendar"})
        self.assertIn("beyond the saved calendar", beyond["message"])
        self.post("/api/prep/page", {"key": FRIDAY, "run": "p-friday-1"}, stream=True)
        for _ in range(50):
            built = self.post("/api/prep/build", {"run": "p-friday-1"})
            if built.get("ok") or "isn't there" in built.get("message", "") or "Stopped" in built.get("message", ""):
                break
            time.sleep(0.1)
        self.assertTrue(built["ok"], built)
        self.assertTrue(built["path"].endswith("/2026-10-16 Prep - ABC steering.html"))
        friday = self.post("/api/today/days", {"day": "2026-10-16"})["days"][0]["meetings"][0]
        self.assertEqual(friday["prep"]["page"], built["path"])


if __name__ == "__main__":
    unittest.main()
