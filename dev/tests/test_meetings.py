"""Tests for the meetings sprint: meetings in the Inbox (BL-42 phase 2).

Run: python3 dev/tests/test_meetings.py
Each class builds a throwaway vault with a fictional calendar and runs the real scripts there. No Microsoft 365.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import today as _cx_today  # noqa: E402
from test_tracker import Vault  # noqa: E402

NOW = "2026-10-08 09:30"          # a Thursday: the window starts Monday 05-10-2026


def sweep(v, *args, now=NOW):
    return subprocess.run([sys.executable, str(v.root / "system/scripts/sweep.py"), *args], cwd=v.root,
                          capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": now})


SPEC = {"days": {
    "2026-10-02": [{"id": "ev-old", "start": "10:00", "end": "11:00", "title": "Last week", "teams": True}],
    "2026-10-05": [{"id": "ev-1", "start": "09:00", "end": "10:00", "title": "ABC Steering", "where": "Teams",
                    "teams": True, "organiser": True, "attendees": ["Sara <sara@client.com>"],
                    "body": "Agenda: secret", "joinUrl": "https://teams.example/join/1"},
                   {"id": "ev-2", "start": "14:00", "end": "14:30", "title": "1:1 with Omar", "private": True,
                    "teams": True, "organiser": "Omar Ali"}],
    "2026-10-07": [{"id": "ev-3", "start": "11:00", "end": "12:00", "title": "Vendor walk-through", "where": "Room 4",
                    "teams": False, "organiser": "Jane Doe"},
                   {"start": "13:00", "end": "13:30", "title": "No ID here", "teams": True}],
    "2026-10-12": [{"id": "ev-4", "start": "09:00", "end": "09:30", "title": "Next week", "teams": True}]}}


class CalendarTests(unittest.TestCase):
    """Item 1: the saved calendar keeps the week back to Monday, IDs and Teams, never attendees or bodies."""

    def setUp(self):
        self.v = v = Vault()
        v.run("init")
        self.spec = v.root / "system/staging/drafts/calendar.json"
        self.spec.write_text(json.dumps(SPEC))

    def tearDown(self):
        self.v.cleanup()

    def saved(self):
        return json.loads((self.v.root / "system/staging/calendar.json").read_text())

    def calendar(self):
        """The command deletes its input once the calendar is saved (BL-118), so each run gets a fresh copy."""
        self.spec.write_text(json.dumps(SPEC))
        return sweep(self.v, "calendar", str(self.spec))

    def test_window_ids_teams_and_nothing_else(self):
        self.assertEqual(json.loads(sweep(self.v, "calendar-window").stdout), {"from": "2026-10-05", "to": "2026-10-15", "keep_from": "2026-10-05"})   # #146: nothing saved yet, so the whole window
        out = self.calendar().stdout
        self.assertIn("Calendar saved: 4 meetings over 3 days", out)
        self.assertIn("Ignored 1: Anything marked private 1", out)                             # BL-97: the private 1:1
        days = self.saved()["days"]
        self.assertEqual(sorted(days), ["2026-10-05", "2026-10-07", "2026-10-12"])           # last week dropped
        steering = days["2026-10-05"][0]
        self.assertEqual(steering, {"id": "ev-1", "start": "09:00", "end": "10:00", "all_day": False,
                                    "title": "ABC Steering", "where": "Teams", "teams": True, "private": False,
                                    "organiser": True, "sensitivity": "normal", "body": "Agenda: secret",
                                    "attendees": [{"name": "Sara Example", "email": "sara@client.com", "registered": True,
                                                   "type": "required", "response": "none"}]})   # mapped to the register        # BL-98: the invite for prep; nothing else
        self.assertNotIn("join", json.dumps(days))                                            # never the join link
        vendor = days["2026-10-07"][0]
        self.assertEqual((vendor["teams"], vendor["organiser"]), (False, "Jane Doe"))
        self.assertNotIn("id", days["2026-10-07"][1])                                         # no ID given, none kept

    def test_private_meeting_is_dropped_or_busy_with_the_rule_off(self):
        self.calendar()                                             # BL-97: dropped
        self.assertEqual([e["title"] for e in self.saved()["days"]["2026-10-05"]], ["ABC Steering"])
        cfg = self.v.root / "system/config/settings.json"
        d = json.loads(cfg.read_text())
        d["sweep"]["ignore"][0]["on"] = False                                                 # the private rule off
        cfg.write_text(json.dumps(d))
        (self.v.root / "system/staging/calendar.json").unlink()          # #146: past days already held are kept, so start afresh
        self.calendar()
        private = self.saved()["days"]["2026-10-05"][1]
        self.assertEqual(private, {"id": "ev-2", "start": "14:00", "end": "14:30", "all_day": False, "title": "Busy",
                                   "where": "", "teams": True, "private": True, "organiser": False})

    def test_window_as_a_number_of_days(self):
        cfg = self.v.root / "system/config/settings.json"
        d = json.loads(cfg.read_text())
        d["inbox"]["meetings_from"] = 7
        cfg.write_text(json.dumps(d))
        self.assertEqual(json.loads(sweep(self.v, "calendar-window").stdout)["keep_from"], "2026-10-01")
        self.calendar()
        self.assertIn("2026-10-02", self.saved()["days"])

    def test_past_days_already_held_are_kept_unchanged(self):
        """#146: a sweep reads today forward; the past days the saved calendar holds are not replaced or lost."""
        self.calendar()
        before = self.saved()["days"]["2026-10-05"]
        later = {"days": {"2026-10-05": [{"id": "x", "start": "08:00", "end": "08:30", "title": "Changed"}],
                          "2026-10-08": [{"id": "ev-5", "start": "10:00", "end": "10:30", "title": "Today", "teams": True}]}}
        self.spec.write_text(json.dumps(later))
        sweep(self.v, "calendar", str(self.spec))
        days = self.saved()["days"]
        self.assertEqual(days["2026-10-05"], before)                      # unchanged
        self.assertIn("2026-10-07", days)                                 # held past day not lost
        self.assertEqual(days["2026-10-08"][0]["title"], "Today")
        self.assertNotIn("2026-10-12", days)                              # future days are what the new read says


class SweepFromTodayTests(unittest.TestCase):
    """#146: a sweep re-reads today and later days only; a gap (nothing saved, or a week stale) is filled."""

    def setUp(self):
        self.v = v = Vault()
        v.run("init")
        self.cal = v.root / "system/staging/calendar.json"
        self.spec = v.root / "system/staging/drafts/calendar.json"
        self.cal.write_text(json.dumps({"fetched": "2026-10-07 08:00", "days": {
            "2026-10-05": [{"id": "ev-1", "start": "09:00", "end": "10:00", "all_day": False, "title": "Kept as saved",
                            "where": "", "teams": True, "private": False, "organiser": True}],
            "2026-10-08": [{"id": "ev-old", "start": "16:00", "end": "17:00", "all_day": False, "title": "Cancelled since",
                            "where": "", "teams": True, "private": False, "organiser": True}]}}))

    def tearDown(self):
        self.v.cleanup()

    def window(self, now=NOW):
        return json.loads(sweep(self.v, "calendar-window", now=now).stdout)

    def test_window_starts_today_not_monday(self):
        self.assertEqual(self.window(), {"from": "2026-10-08", "to": "2026-10-15", "keep_from": "2026-10-05"})

    def test_a_gap_is_filled_from_the_window_start(self):
        # last fetched more than a week ago: from the day after what it reached; nothing saved: the whole window
        self.assertEqual(self.window(now="2026-10-16 09:00")["from"], "2026-10-15")
        self.cal.unlink()
        self.assertEqual(self.window()["from"], "2026-10-05")

    def test_a_new_user_still_gets_past_days(self):
        self.cal.unlink()
        self.spec.write_text(json.dumps({"days": {"2026-10-06": [{"id": "p", "start": "09:00", "end": "10:00", "title": "Tuesday"}],
                                                  "2026-10-08": [{"id": "t", "start": "09:00", "end": "10:00", "title": "Today"}]}}))
        out = sweep(self.v, "calendar", str(self.spec)).stdout
        self.assertIn("filling a gap", out)
        self.assertEqual(sorted(json.loads(self.cal.read_text())["days"]), ["2026-10-06", "2026-10-08"])

    def test_past_days_are_kept_unchanged_and_today_is_replaced(self):
        self.spec.write_text(json.dumps({"days": {
            "2026-10-05": [{"id": "ev-1", "start": "09:00", "end": "10:00", "title": "Changed title"}],
            "2026-10-04": [{"id": "ev-x", "start": "09:00", "end": "10:00", "title": "Before the window"}],
            "2026-10-08": [{"id": "ev-new", "start": "11:00", "end": "12:00", "title": "Today's meeting"}],
            "2026-10-09": [{"id": "ev-n2", "start": "11:00", "end": "12:00", "title": "Tomorrow"}]}}))
        out = sweep(self.v, "calendar", str(self.spec)).stdout
        self.assertIn("Calendar from today (past days kept as saved).", out)
        days = json.loads(self.cal.read_text())["days"]
        self.assertEqual(sorted(days), ["2026-10-05", "2026-10-08", "2026-10-09"])
        self.assertEqual(days["2026-10-05"][0]["title"], "Kept as saved")
        self.assertEqual([e["title"] for e in days["2026-10-08"]], ["Today's meeting"])

    def test_a_recent_past_meeting_with_a_new_transcript_still_reaches_the_check(self):
        self.spec.write_text(json.dumps({"days": {"2026-10-08": [{"id": "ev-new", "start": "11:00", "end": "12:00", "title": "Today", "teams": True}]}}))
        sweep(self.v, "calendar", str(self.spec))
        todo = sweep(self.v, "transcripts", "todo", now="2026-10-08 18:00").stdout
        self.assertIn("ev-1", todo)


class LookbackCapTests(unittest.TestCase):
    """#146: mail and Teams read from the last sweep, never further back than sweep.max_lookback_days (3)."""

    def setUp(self):
        self.v = v = Vault()
        v.run("init")

    def tearDown(self):
        self.v.cleanup()

    def last(self, stamp):
        (self.v.root / "system/staging/last-sweep.txt").write_text(stamp + "\n")

    def window(self, *args, now="2026-10-08 09:30"):
        return json.loads(sweep(self.v, "window", *args, now=now).stdout)

    def test_a_five_day_gap_reads_three_days_and_says_so(self):
        self.last("2026-10-03 08:00")
        w = self.window()
        self.assertEqual(w["start"], "2026-10-05 09:30")
        self.assertEqual(w["capped"]["days"], 3)
        self.assertEqual(w["capped"]["not_read_days"], 2)
        self.assertEqual(w["capped"]["note"], "Read the last 3 days; 2 older days not read. Say 'sweep the last 7 days' to include them.")
        self.assertTrue(w["advances_timestamp"])

    def test_a_one_day_gap_reads_one_day(self):
        self.last("2026-10-07 08:00")
        w = self.window()
        self.assertEqual(w["start"], "2026-10-07 08:00")
        self.assertNotIn("capped", w)

    def test_an_explicit_last_n_days_overrides_the_cap(self):
        self.last("2026-10-03 08:00")
        w = self.window("--days", "7")
        self.assertEqual(w["start"], "2026-10-01 09:30")
        self.assertNotIn("capped", w)
        self.assertFalse(w["advances_timestamp"])

    def test_the_cap_is_a_setting(self):
        cfg = self.v.root / "system/config/settings.json"
        d = json.loads(cfg.read_text())
        d["sweep"]["max_lookback_days"] = 10
        cfg.write_text(json.dumps(d))
        self.last("2026-10-03 08:00")
        self.assertEqual(self.window()["start"], "2026-10-03 08:00")

    def test_the_first_run_keeps_its_own_lookback(self):
        w = self.window()
        self.assertEqual(w["kind"], "first run")
        self.assertNotIn("capped", w)

    def test_the_daily_catch_up_respects_it(self):
        self.last("2026-10-01 08:00")
        due = json.loads(sweep(self.v, "due", now="2026-10-08 09:30").stdout)
        self.assertTrue(due["due"])
        self.assertEqual(self.window()["capped"]["days"], 3)       # cx-sweep, run because it is due, reads this window


def page_data(v):
    import re
    html = (v.root / "dashboard.html").read_text(encoding="utf-8")
    return json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))


def week_calendar(v, with_ids=True, today=None):
    """A calendar for one week: Monday, today, the day before Monday and the day after today. `today` defaults to the
    real date (the build then uses the real clock); a test that pins the clock with CREAITE_NOW passes the same day."""
    from datetime import timedelta
    if today is None:
        today = _cx_today()                               # the build's clock: CREAITE_NOW's day, else the real date
    mon = today - timedelta(days=today.weekday())
    d = lambda x: x.isoformat()  # noqa: E731
    ev = lambda i, **k: ({"id": f"ev-{i}"} if with_ids else {}) | k  # noqa: E731
    days = {}
    add = lambda day, *evs: days.setdefault(d(day), []).extend(evs)  # noqa: E731   on a Monday, Monday and today are one day
    add(mon - timedelta(days=1), ev(0, start="10:00", end="11:00", title="Last Sunday", teams=True))
    add(mon, ev(1, start="09:00", end="10:00", title="ABC Steering", teams=True, organiser=True),
        ev(2, start="15:00", end="15:30", title="Weekly sync 12", teams=True, organiser="Jane Doe"),
        ev(5, start="", end="", all_day=True, title="Office closed"))
    add(today, ev(3, start="08:30", end="09:00", title="Busy", teams=False, private=True))
    add(today + timedelta(days=1), ev(4, start="09:00", end="10:00", title="Tomorrow", teams=True))
    cal = {"fetched": f"{d(today)} 07:00", "days": days}
    (v.root / "system/staging/calendar.json").write_text(json.dumps(cal))
    return mon, today


class MeetingsDataTests(unittest.TestCase):
    """Item 2: each meeting in the window with its likely project and processed state (by event ID)."""

    def setUp(self):
        self.v = v = Vault()
        v.run("init")

    def tearDown(self):
        self.v.cleanup()

    def test_window_project_and_processed(self):
        v = self.v
        mon, today = week_calendar(v)
        with open(v.root / "system/processed.txt", "a") as f:
            f.write(f"{mon.isoformat()} | calendar:ev-1 | projects/ABC Example Programme/minutes/x.docx | 3\n")
        cfg = v.root / "system/config/settings.json"
        d = json.loads(cfg.read_text())
        d.setdefault("prep", {})["series"] = {"weekly sync": "ABC"}
        cfg.write_text(json.dumps(d))
        v.run(script="build_dashboard.py")
        m = page_data(v)["meetings"]
        self.assertEqual(m["from"], mon.isoformat())
        got = [(r["day"], r["start"], r["title"], r["id"], r["p"], r["how"], r["processed"], r["teams"], r["private"])
               for r in m["rows"]]
        expect = [(today.isoformat(), "08:30", "Busy", "ev-3", None, "private", None, False, True)] if today != mon else []
        expect += [(mon.isoformat(), "09:00", "ABC Steering", "ev-1", "ABC", "matched", mon.isoformat(), True, False),
                   (mon.isoformat(), "15:00", "Weekly sync 12", "ev-2", "ABC", "remembered", None, True, False)]
        if today == mon:
            expect = sorted(expect + [(mon.isoformat(), "08:30", "Busy", "ev-3", None, "private", None, False, True)],
                            key=lambda r: r[1])
        self.assertEqual(got, expect)                       # newest day first; before Monday, all-day and tomorrow left out
        self.assertEqual(next(r for r in m["rows"] if r["title"] == "Weekly sync 12")["organiser"], "Jane Doe")

    def test_an_older_calendar_without_ids_still_loads(self):
        week_calendar(self.v, with_ids=False)
        self.v.run(script="build_dashboard.py")
        rows = page_data(self.v)["meetings"]["rows"]
        self.assertTrue(rows)
        self.assertTrue(all(r["id"] is None and r["processed"] is None for r in rows))

    def test_no_calendar_yet(self):
        self.v.run(script="build_dashboard.py")
        self.assertEqual(page_data(self.v)["meetings"]["rows"], [])
        self.assertIsNone(page_data(self.v)["meetings"]["fetched"])


PAGE_SCRIPT = r"""
<script>
(async()=>{ const out={errors:[]}, wait=ms=>new Promise(r=>setTimeout(r,ms)); window.ASKED=[];
  const until=async(f,ms=30000)=>{ const t=Date.now(); while(!f()){ if(Date.now()-t>ms) return false; await wait(25); } return true; };   /* the state, not a fixed time */
  // the run engine is stubbed (BL-119: Process selected loads, then processes the saved file). ev-1's transcript is already in the inbox
  // (loaded earlier), so it goes straight to cx-minutes; ev-2 is loaded first, and the stub finds nothing to save for it. A process request
  // leaves a draft waiting in Review as cx-minutes would.
  window.LOADED=[]; window.ASKED=[];
  jobLive=async(url,body)=>{ window.LOADED.push([url,body.id]); };
  /* #264: a loaded transcript is processed through Process's own route (processLive), not an ask message */
  processLive=async(files)=>{ window.ASKED.push(files);
    if(files.some(f=>/ABC Steering/.test(f.path))) await api("/api/fs",{op:"write",path:"system/staging/proposed-test-mtg.json",text:JSON.stringify({created:"2026-10-08T09:00:00",source_run:"cx-minutes",files:[],items:[],meeting:{key:"calendar:ev-1",title:"ABC Steering",date:"2026-10-05",projects:["ABC"],draft:null,transcript:null,minutes_decision:"pending",file_ops:[]}})});
    return {ok:true,files:files.map(f=>({path:f.path,state:"staged"})),staged:files.length,needs:0}; };
  askLive=async(q,c)=>{ window.ASKED.push([q,c]); };
  try{
    nowHM=()=>"23:59";                                          // late in the day: today's meetings have all ended
    await checkLive(); go("inbox"); await wait(50);
    const rows=()=>[...document.querySelectorAll("#mtgBody tr[data-mid]")].map(tr=>[tr.querySelector("td.title").innerText,
      tr.querySelector("input").disabled, tr.cells[6].innerText.trim(), tr.cells[3].innerText.trim(), tr.cells[4].innerText.trim()]);
    out.read=document.getElementById("mtgRead").textContent; out.days=[...document.querySelectorAll("#mtgBody .mtgday")].map(r=>r.innerText);
    out.before=rows(); out.transcript=document.querySelector("#mtgBody tr[data-mid]").cells[7].innerText;
    // earlier in the day, today's 08:30 to 09:00 meeting is in progress: greyed and not selectable until it ends
    nowHM=()=>"08:45"; renderMeetings(); const bz=[...document.querySelectorAll("#mtgBody tr[data-mid]")].find(tr=>tr.querySelector("td.title").innerText.startsWith("Busy"));
    out.early={later:bz.classList.contains("mtglater"),disabled:bz.querySelector("input").disabled,state:bz.cells[6].innerText.trim()};
    nowHM=()=>"08:00"; renderMeetings(); out.before0800=[...document.querySelectorAll("#mtgBody tr[data-mid]")].find(tr=>tr.querySelector("td.title").innerText.startsWith("Busy")).cells[6].innerText.trim();
    nowHM=()=>"23:59"; renderMeetings();
    document.getElementById("mtgNew").click(); await wait(10);
    out.picked=[...MSEL];
    out.ck=ckItems("process meeting").map(i=>i.l).filter(l=>l.startsWith("Intake:"));
    document.getElementById("mtgGo").click(); await wait(10); out.during=rows().map(r=>r[2]);
    /* dev-test-steadiness: the page now runs in real time, so wait for the run to end and both rows to show their outcome
       (the draft from the server, the skip), not for fixed times that assumed virtual time */
    const state=t=>{ const r=rows().find(x=>x[0]===t); return r?r[2]:""; };
    await until(()=>RUN===null&&!Object.values(MRUN).some(v=>v==="processing"||v==="loading")
      &&state("ABC Steering")==="Draft ready in Review"&&state("Weekly sync 12").startsWith("Skipped"));
    out.asked=ASKED.slice(); out.loaded=LOADED.slice(); out.after=rows();
    window.ASKED=[]; document.getElementById("mtgRefresh").click(); await until(()=>ASKED.length>0,10000); out.refresh=ASKED.slice();
  }catch(e){ out.errors.push(String(e&&e.stack||e)); }
  const pre=document.createElement("pre"); pre.id="result"; pre.textContent=JSON.stringify(out); document.body.appendChild(pre);
})();
</script>
"""


class InboxPageTests(unittest.TestCase):
    """Item 3 in headless Chrome, served live: the Meetings section, Select new, Process selected one by one
    (stubbed run engine) and Refresh."""

    @classmethod
    def setUpClass(cls):
        import socket
        import time
        import urllib.request
        from test_dashboard import CHROME
        if not CHROME.exists():
            raise unittest.SkipTest("Google Chrome not installed")
        from test_live_server import FAKE_CLAUDE
        cls.v = v = Vault()
        v.run("init")
        # the page's TODAY is the browser's own clock, which CREAITE_NOW cannot pin: use the real date for the calendar and
        # keep the pin out of the server, so the page and the data agree on today whatever the caller has set
        from datetime import date
        cls.mon, cls.today = week_calendar(v, today=date.today())
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(0o755)
        (v.root / "inbox" / f"{cls.mon.isoformat()} ABC Steering.vtt").write_text("WEBVTT\n\nEvent ID: ev-1\n\n00:00:01.000 --> 00:00:05.000\nHello\n")
        (v.root / "inject.html").write_text(PAGE_SCRIPT)
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        env = {**{k: x for k, x in os.environ.items() if k != "CREAITE_NOW"}, "CREAITE_PORT": str(port), "CREAITE_CLAUDE": str(fake),
               "CREAITE_TEST_INJECT": str(v.root / "inject.html")}
        server = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.time() + 30          # dev-test-steadiness: it was 5 s, and the page then loaded nothing
            while True:
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
                    break
                except OSError:
                    if time.time() > deadline or server.poll() is not None:
                        raise
                    time.sleep(0.1)
            # dev-test-steadiness: in real time, waiting for the result. Under virtual time the page's clock ran on while the
            # server worked (the stand-in claude, the file writes), the budget ran out and the dump had no result.
            from page_result import page_result
            cls.r = json.loads(page_result(f"http://127.0.0.1:{port}/", pin_clock=False))
        finally:
            server.terminate()
            server.wait(timeout=10)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_section_rows_and_selection(self):
        r = self.r
        self.assertEqual(r["errors"], [])
        self.assertIn("Calendar read", r["read"])
        self.assertIn(f"{self.today:%d-%m-%Y}", r["days"][0])                       # newest day first
        titles = [row[0] for row in r["before"]]
        self.assertIn("ABC Steering", titles)
        self.assertNotIn("Tomorrow", titles)
        busy = next(row for row in r["before"] if row[0].startswith("Busy"))
        self.assertFalse(busy[1])                                                              # private: pickable by hand
        steering = next(row for row in r["before"] if row[0] == "ABC Steering")
        self.assertEqual((steering[2], steering[3], steering[4]), ("Loaded in the inbox, not processed yet", "Teams", "You"))      # ev-1 has its transcript in the inbox (BL-137: its state is on the row)
        self.assertIn("Not checked yet", r["transcript"])                                      # BL-42 phase 3: nothing looked up yet
        self.assertEqual(r["early"], {"later": True, "disabled": True,
                                      "state": "In progress: a transcript comes after it ends"})   # not ended yet
        self.assertEqual(r["before0800"], "Not happened yet")
        self.assertEqual(sorted(r["picked"]), ["ev-1", "ev-2"])                                # Select new leaves the private one
        self.assertEqual(sorted(r["ck"]), sorted(["Intake: process meeting ABC Steering", "Intake: process meeting Weekly sync 12",
                                                  "Intake: process meeting Busy"]))

    def test_process_selected_one_by_one_then_refresh(self):
        r = self.r
        self.assertTrue(any(s.startswith(("Loading", "Processing")) for s in r["during"]))  # progress shows on the rows
        self.assertEqual([i for _, i in r["loaded"]], ["ev-2"])                                # ev-1 was loaded already; ev-2 is loaded first (BL-119)
        self.assertTrue(all(u == "/api/transcripts/load" for u, _ in r["loaded"]))
        asked = r["asked"]
        self.assertEqual(len(asked), 1)                                                        # only a loaded transcript goes to cx-minutes
        self.assertEqual(len(asked[0]), 1)
        self.assertRegex(asked[0][0]["path"], r"^inbox/\d{4}-\d{2}-\d{2} ABC Steering\.vtt$")  # the saved file, not a search of Teams
        # #264: through Process's own route (the click is the go-ahead to stage), never a confirmed ask message
        after = {row[0]: row[2] for row in r["after"]}
        self.assertEqual(after["ABC Steering"], "Draft ready in Review")
        self.assertTrue(after["Weekly sync 12"].startswith("Skipped"))                         # nothing to load: the reason is on its row
        self.assertIn("No transcript could be loaded", after["Weekly sync 12"])
        self.assertEqual(r["refresh"], [["refresh calendar", None]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
