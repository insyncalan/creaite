"""BL-42 phase 3: loading meeting transcripts (Sprint 4b, item 2).

Run: python3 dev/tests/test_transcripts.py
Microsoft 365 is never called. The calls a real run makes are replayed by a stand-in `claude` whose stream carries fixture tool
results in the shapes of dev/reference/spike-transcripts-2026-10-08.md, for fictional meetings.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import populate  # noqa: E402
from test_live_server import free_port  # noqa: E402
from test_meetings import page_data, week_calendar  # noqa: E402
from test_tracker import REPO, Vault  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import transcripts as T  # noqa: E402

M365 = "mcp__claude_ai_Microsoft_365__"
TODAY = date.today()
NOW = f"{TODAY.isoformat()} 23:30"                     # the whole day's meetings are over
THREAD = "19:meeting_AbCdEf123@thread.v2"
JOIN = f"https://teams.microsoft.com/l/meetup-join/{quote(THREAD, safe='')}/0?context=%7b%22Tid%22%3a%22t%22%7d"
DAY = (TODAY - __import__("datetime").timedelta(days=TODAY.weekday())).isoformat()   # Monday: where week_calendar puts ev-1

# a transcript as Teams returns it: CRLF line ends, cues out of start order, voice tags, odd spacing that must survive
VTT = ("WEBVTT\r\n\r\n"
       "00:00:01.000 --> 00:00:05.000\r\n<v Sara Example>Welcome everyone,  thanks for coming.</v>\r\n\r\n"
       "00:00:09.000 --> 00:00:10.000\r\n<v Omar Ali>Yeah.</v>\r\n\r\n"
       "00:00:06.000 --> 00:00:12.000\r\n<v Alan Carter>Let's start with the pilot plan: UAT starts 12-11-2026, ok?</v>\r\n")
CUE_TEXTS = ["<v Sara Example>Welcome everyone,  thanks for coming.</v>", "<v Alan Carter>Let's start with the pilot plan: UAT starts 12-11-2026, ok?</v>",
             "<v Omar Ali>Yeah.</v>"]            # in start-time order


def event(eid="ev-1", transcript=True, online=True, mine=True):
    start, end = f"{DAY}T08:00:00.0000000", f"{DAY}T09:00:00.0000000"
    ev = {"id": eid, "subject": "ABC Steering", "isOrganizer": mine, "isCancelled": False, "sensitivity": "normal",
          "organizer": {"name": "Alan Carter", "address": "alan@example.com"},
          "attendees": [{"name": "Sara Example", "address": "sara@client.example"}, {"name": "Omar Ali", "address": "omar@example.com"}],
          "start": {"dateTime": start, "timeZone": "UTC"}, "end": {"dateTime": end, "timeZone": "UTC"},
          "body": "Join passcode 123 456 PIN 7890# secret"}
    ev["onlineMeeting"] = {"joinUrl": JOIN} if online else None
    if online and transcript:
        ev["meetingTranscriptUrl"] = f"meeting-transcript:///events/{quote('b64joinurl')}?start={DAY}T08:00:00Z&end={DAY}T09:00:00Z"
    return ev


def transcript_result(contents=(VTT,)):
    return {"meeting": {"id": "m1", "subject": "ABC Steering"}, "transcripts": [
        {"id": f"tr{i}", "createdDateTime": f"{DAY}T08:00:30Z", "endDateTime": f"{DAY}T08:19:00Z", "content": c} for i, c in enumerate(contents)]}


def at(hm):
    return f"{DAY}T{hm}Z"


CHAT_LIST = {"truncated": False, "messages": [
    {"id": "c1", "messageType": "unknownFutureValue", "from": None, "createdDateTime": at("08:00:10"), "eventDetail": {"@odata.type": "#microsoft.graph.callStartedEventMessageDetail"}},
    {"id": "c2", "messageType": "message", "from": {"user": {"displayName": "Sara Example"}}, "createdDateTime": at("08:20:00"),
     "bodyPreview": "Here is the link to the pilot plan, which is long and gets cut at about three hun"},
    {"id": "c3", "messageType": "message", "from": {"user": {"displayName": "Omar Ali"}}, "createdDateTime": at("07:30:00"), "bodyPreview": "Running late (before the meeting)"},
    {"id": "c4", "messageType": "message", "from": {"user": {"displayName": "Omar Ali"}}, "createdDateTime": at("09:30:00"), "bodyPreview": "Thanks all (after the meeting)"},
    {"id": "c5", "messageType": "unknownFutureValue", "from": None, "createdDateTime": at("08:30:00"), "eventDetail": {"@odata.type": "#microsoft.graph.membersJoinedEventMessageDetail"}}]}
CHAT_FULL = {"c2": {"id": "c2", "messageType": "message", "from": {"user": {"displayName": "Sara Example"}}, "createdDateTime": at("08:20:00"),
                    "body": {"contentType": "html", "content": "<p>Here is the link to the pilot plan, <b>in full</b>: https://example.test/plan</p>"}}}

STUB = r'''#!/usr/bin/env python3
"""A stand-in `claude` for transcript runs: replays the steps in stub_script.json as a stream-json run."""
import json, sys
from pathlib import Path
args = sys.argv[1:]
here = Path(__file__).resolve().parent
(here / "fake_seen.json").write_text(json.dumps({"allowed": args[args.index("--allowedTools") + 1].split(","),
    "disallowed": args[args.index("--disallowedTools") + 1].split(","), "prompt": args[args.index("--") + 1]}))
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-t"})
for n, step in enumerate(json.loads((here / "stub_script.json").read_text())):
    out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"u{n}", "name": step["name"], "input": step["input"]}]}})
    out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"u{n}", "content": step["result"], "is_error": step.get("error", False)}]}})
out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Found it."}]}})
out({"type": "result", "result": "Found it.", "session_id": "sess-t"})
'''


def read(uri, result, error=False):
    return {"name": M365 + "read_resource", "input": {"uri": uri}, "result": result if isinstance(result, str) else json.dumps(result), "error": error}


def route_steps(ev=None, tr=None, chat=True, **kw):
    """The calls of a real run: find the event, read it, read its transcript, then the chat and each message in full."""
    ev = ev or event()
    steps = [{"name": M365 + "outlook_calendar_search", "input": {"query": "ABC Steering"}, "result": json.dumps({"events": [{"id": ev["id"], "uri": "calendar:///events/" + ev["id"]}]})},
             read("calendar:///events/" + ev["id"], ev)]
    if ev.get("meetingTranscriptUrl"):
        steps.append(tr if tr is not None else read(ev["meetingTranscriptUrl"], transcript_result()))
    if chat:
        steps.append(read(f"teams:///chats/{THREAD}/messages", CHAT_LIST))
        steps.append(read(f"teams:///chats/{THREAD}/messages/c2", CHAT_FULL["c2"]))
    return steps


# ── the pieces, with no server ──
class Pieces(unittest.TestCase):
    def test_statuses(self):
        c = T.classify
        self.assertEqual(c(online=True, uri="u", count=1, error=None, past=True), "available")
        self.assertEqual(c(online=True, uri="u", count=0, error=None, past=True), "not_transcribed")           # an online meeting that took place, empty list
        self.assertEqual(c(online=False, uri=None, count=None, error=None, past=True), "none")                 # in person
        self.assertEqual(c(online=True, uri=None, count=None, error=None, past=True), "none")                  # no transcript URL
        self.assertEqual(c(online=True, uri="u", count=None, error="permission", past=True), "no_access")
        self.assertEqual(c(online=True, uri="u", count=None, error="notfound", past=True), "no_access")
        self.assertIsNone(c(online=True, uri="u", count=None, error="other", past=True))                       # a dropped connection: not decided
        self.assertIsNone(c(online=True, uri="u", count=0, error=None, past=False))                            # not over yet: look again later
        self.assertEqual(c(online=True, uri="u", count=2, error=None, past=True), "available")

    def test_what_an_event_and_a_url_tell_us(self):
        f = T.event_facts(event())
        self.assertEqual((f["id"], f["join_url"] == JOIN, f["organiser_me"], f["organiser"], f["attendees"]),
                         ("ev-1", True, True, "Alan Carter", ["Sara Example", "Omar Ali"]))
        self.assertNotIn("body", f)                                                    # never the invite's text, passcode or PIN
        self.assertEqual(T.thread_id(JOIN), THREAD)
        self.assertEqual(T.uri_window(f["uri"]), (f"{DAY}T08:00:00Z", f"{DAY}T09:00:00Z"))      # this occurrence's start and end, kept in the URL
        self.assertIsNone(T.thread_id("https://example.test"))

    def test_the_vtt_is_tidied_and_every_word_survives(self):
        tidy = T.tidy_vtt(VTT, {"title": "ABC Steering", "day": DAY, "start": "09:00", "organiser": "Alan Carter", "id": "ev-1",
                                "attendees": ["Sara Example", "Omar Ali"]})
        self.assertNotIn("\r", tidy)                                                   # LF line ends
        self.assertTrue(tidy.startswith("WEBVTT\n\nNOTE\nMeeting: ABC Steering\nDate: " + DAY))
        for line in ("Start: 09:00", "Organiser: Alan Carter", "Attendees: Sara Example, Omar Ali", "Event ID: ev-1"):
            self.assertIn(line, tidy)
        body = [ln for ln in tidy.split("\n") if ln.startswith("<v ")]
        self.assertEqual(body, CUE_TEXTS)                                              # cues in start-time order, text byte for byte
        starts = re.findall(r"^(\d\d:\d\d:\d\d\.\d{3}) -->", tidy, re.M)
        self.assertEqual(starts, sorted(starts))
        self.assertNotIn("passcode", tidy)

    def test_several_transcripts_stay_apart_as_parts(self):
        tidy = T.tidy_vtt([VTT, VTT], {"title": "T", "day": DAY, "id": "x"})
        self.assertIn("Part 1 of 2", tidy)
        self.assertIn("Part 2 of 2", tidy)
        self.assertEqual(tidy.count("Yeah."), 2)

    def test_minutes_reads_the_tidied_file_as_before(self):
        v = Vault()
        self.addCleanup(v.cleanup)
        v.run("init")
        raw, tidy = v.root / "inbox" / "raw.vtt", v.root / "inbox" / "tidy.vtt"
        raw.write_text(VTT.replace("\r\n", "\n"), encoding="utf-8")
        tidy.write_text(T.tidy_vtt(VTT, {"title": "ABC Steering", "day": DAY, "start": "09:00", "organiser": "Alan Carter", "id": "ev-1",
                                         "attendees": ["Sara Example"]}), encoding="utf-8")
        said_raw = v.run("transcript", "inbox/raw.vtt", script="minutes.py").stdout
        said_tidy = v.run("transcript", "inbox/tidy.vtt", script="minutes.py").stdout
        self.assertEqual(said_tidy.splitlines()[0], "Sara Example: Welcome everyone,  thanks for coming.")
        self.assertIn("Alan Carter: Let's start with the pilot plan", said_tidy)
        self.assertNotIn("ABC Steering", said_tidy)                                    # the NOTE header isn't speech
        self.assertNotIn("Event ID", said_tidy)
        self.assertEqual(sorted(said_raw.splitlines()), sorted(said_tidy.splitlines()))       # the same turns, whichever order the cues came in

    def test_chat_keeps_only_the_meeting_window_and_full_bodies(self):
        text, n = T.chat_text(CHAT_LIST, CHAT_FULL, (at("08:00:00"), at("09:00:00")), {"title": "ABC Steering", "day": DAY, "id": "ev-1"})
        self.assertEqual(n, 1)
        self.assertIn("Event ID: ev-1", text)
        self.assertIn("Sara Example: Here is the link to the pilot plan, in full: https://example.test/plan", text)    # the full body, HTML removed
        for gone in ("Running late", "Thanks all", "callStarted", "gets cut at about"):
            self.assertNotIn(gone, text)                                               # outside the window, system events, the cut preview

    def test_what_is_kept_is_only_status_fields(self):
        v = Vault()
        self.addCleanup(v.cleanup)
        v.run("init")
        code = ("import sys; sys.path.insert(0,'system/scripts'); import transcripts as T; "
                "T.keep('ev-9', {'status':'available','uri':'meeting-transcript:///x','count':1,'body':'Join passcode 123','pin':'7890#','content':'WEBVTT secret'}); "
                "print(open(T.paths.TRANSCRIPTS).read())")
        out = subprocess.run([sys.executable, "-c", code], cwd=v.root, capture_output=True, text=True).stdout
        for secret in ("passcode", "7890", "WEBVTT", "secret"):
            self.assertNotIn(secret, out)
        self.assertEqual(json.loads(out)["checked"]["ev-9"]["status"], "available")

    def test_a_tool_result_spooled_to_a_file_is_read_from_there_and_only_from_claudes_own_folders(self):
        with tempfile.TemporaryDirectory() as d:
            spool = Path(d) / "tool-results" / "mcp-read_resource-1.txt"
            spool.parent.mkdir()
            payload = json.dumps(transcript_result())
            spool.write_text(json.dumps([{"type": "text", "text": payload}]), encoding="utf-8")
            note = f"Error: result (180,000 characters) exceeds maximum allowed tokens. Output has been saved to {spool}.\nFormat: JSON array"
            os.environ["CREAITE_TOOL_RESULTS"] = d
            try:
                found = T.transcripts_in(T.as_json(note))
                self.assertEqual(found[0]["content"], VTT)                             # byte for byte, CRLF and all
                other = Path(tempfile.mkdtemp()) / "x.txt"
                other.write_text(payload)
                self.assertIsNone(T.read_spooled(f"saved to {other}"))                 # not Claude Code's folder: never read
            finally:
                del os.environ["CREAITE_TOOL_RESULTS"]


# ── the meetings still to look up ──
class Lookups(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        self.v.run("init")
        self.env = {**os.environ, "CREAITE_NOW": NOW}
        week_calendar(self.v)

    def sweep(self, *args):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/sweep.py"), "transcripts", *args], cwd=self.v.root,
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        return json.loads(r.stdout)

    def test_new_online_meetings_are_looked_up_and_in_person_ones_recorded_at_once(self):
        cal = json.loads((self.v.root / "system/staging/calendar.json").read_text())
        cal["days"][DAY].append({"id": "ev-room", "start": "13:00", "end": "14:00", "title": "Room 4 workshop", "teams": False, "all_day": False})
        (self.v.root / "system/staging/calendar.json").write_text(json.dumps(cal))
        out = self.sweep("todo")
        ids = [m["id"] for m in out["look_up"]]
        self.assertIn("ev-1", ids)
        self.assertNotIn("ev-room", ids)
        self.assertEqual(out["recorded_without_lookup"], ["ev-room"])
        self.assertEqual(self.sweep("show")["checked"]["ev-room"]["status"], "none")

    def test_only_new_and_not_transcribed_ones_are_looked_up_again(self):
        facts = {"results": [{"id": "ev-1", "online": True, "uri": "meeting-transcript:///a", "count": 0, "error": None},
                             {"id": "ev-2", "online": True, "uri": "meeting-transcript:///b", "count": 1, "error": None}]}
        f = self.v.root / "facts.json"
        f.write_text(json.dumps(facts))
        r = self.sweep("record", str(f))
        self.assertEqual(r["recorded"], {"ev-1": "not_transcribed", "ev-2": "available"})
        ids = [m["id"] for m in self.sweep("todo")["look_up"]]
        self.assertIn("ev-1", ids)                                                     # Not transcribed: a transcript can appear later
        self.assertNotIn("ev-2", ids)                                                  # has one: done

    def test_processed_cleared_future_and_private_meetings_are_left_alone(self):
        with open(self.v.root / "system/processed.txt", "a") as f:
            f.write(f"{DAY} | calendar:ev-1 | projects/x | 1\n")
        out = self.sweep("todo")
        self.assertNotIn("ev-1", [m["id"] for m in out["look_up"]])                    # processed
        cal = json.loads((self.v.root / "system/staging/calendar.json").read_text())
        late = {"id": "ev-late", "start": "23:40", "end": "23:55", "title": "Late call", "teams": True, "all_day": False}
        cal["days"][TODAY.isoformat()] = cal["days"].get(TODAY.isoformat(), []) + [late]
        (self.v.root / "system/staging/calendar.json").write_text(json.dumps(cal))
        self.assertNotIn("ev-late", [m["id"] for m in self.sweep("todo")["look_up"]])   # not over at 23:30
        code = f"import sys; sys.path.insert(0,'system/scripts'); import build_dashboard as b; b.clear_meetings([{{'key':'ev-2','day':'{DAY}','start':'15:00','title':'x'}}])"
        subprocess.run([sys.executable, "-c", code], cwd=self.v.root, check=True)
        self.assertNotIn("ev-2", [m["id"] for m in self.sweep("todo")["look_up"]])     # cleared

    def test_the_dashboard_row_carries_the_status(self):
        f = self.v.root / "facts.json"
        f.write_text(json.dumps({"results": [{"id": "ev-1", "online": True, "uri": "meeting-transcript:///a", "count": 1, "error": None}]}))
        self.sweep("record", str(f))
        self.v.run(script="build_dashboard.py")
        rows = {r["id"]: r for r in page_data(self.v)["meetings"]["rows"]}
        self.assertEqual(rows["ev-1"]["transcript"], "available")
        self.assertIsNone(rows["ev-2"]["transcript"])                                  # not checked yet

    def test_a_loaded_files_header_is_its_meetings_key(self):
        (self.v.root / "inbox" / f"{DAY} ABC Steering.vtt").write_text(T.tidy_vtt(VTT, {"title": "ABC Steering", "day": DAY, "id": "ev-1"}), encoding="utf-8")
        out = json.loads(self.v.run("key", "--date", DAY, "--title", "ABC Steering", "--transcript", f"inbox/{DAY} ABC Steering.vtt", script="minutes.py").stdout)
        self.assertEqual(out["key"], "calendar:ev-1")                                  # never processed twice
        info = json.loads(self.v.run("filedate", f"inbox/{DAY} ABC Steering.vtt", script="minutes.py").stdout)
        self.assertEqual(info["event_id"], "ev-1")
        with open(self.v.root / "system/processed.txt", "a") as f:
            f.write(f"{DAY} | calendar:ev-1 | x | 1\n")
        out = json.loads(self.v.run("key", "--date", DAY, "--title", "ABC Steering", "--transcript", f"inbox/{DAY} ABC Steering.vtt", script="minutes.py").stdout)
        self.assertEqual(out["processed_on"], DAY)


# ── a run through the live server ──
class Runs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        week_calendar(v)
        cls.spool_dir = Path(tempfile.mkdtemp(prefix="creaite-spool-"))
        fake = v.root / "fake_claude.py"
        fake.write_text(STUB)
        fake.chmod(0o755)
        port = free_port()
        cls.base = f"http://127.0.0.1:{port}"
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")],
                                    env={**os.environ, "CREAITE_PORT": str(port), "CREAITE_CLAUDE": str(fake), "CREAITE_NOW": NOW,
                                         "CREAITE_TOOL_RESULTS": str(cls.spool_dir)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
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
        shutil.rmtree(cls.spool_dir, ignore_errors=True)     # BL-172 (sprint-polish-2)

    def setUp(self):
        for f in (self.v.root / "inbox").glob("*"):
            f.unlink()
        for f in ("system/staging/transcripts.json", "fake_seen.json"):
            (self.v.root / f).unlink(missing_ok=True)
        (self.v.root / "system/processed.txt").write_text("")

    def run_job(self, mode, steps, eid="ev-1"):
        (self.v.root / "stub_script.json").write_text(json.dumps(steps))
        req = urllib.request.Request(self.base + f"/api/transcripts/{mode}", data=json.dumps({"id": eid}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        events = []
        with urllib.request.urlopen(req, timeout=60) as r:
            for raw in r:
                line = raw.decode().strip()
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
        return events

    def outcome(self, events):
        return next(e for e in events if e["type"] == "transcript")

    def inbox(self):
        return sorted(p.name for p in (self.v.root / "inbox").iterdir())

    def status(self, eid="ev-1"):
        p = self.v.root / "system/staging/transcripts.json"
        return (json.loads(p.read_text())["checked"].get(eid) or {}).get("status") if p.exists() else None

    def test_a_check_records_the_status_and_loads_nothing(self):
        ev = self.run_job("check", route_steps(chat=False))
        self.assertEqual(self.outcome(ev)["status"], "available")
        self.assertEqual((self.status(), self.inbox()), ("available", []))
        kept = json.loads((self.v.root / "system/staging/transcripts.json").read_text())["checked"]["ev-1"]
        self.assertEqual(sorted(kept), ["checked", "count", "end", "start", "status", "thread", "uri"])
        self.assertNotIn("passcode", json.dumps(kept))                                 # the invite's passcode and PIN are never kept
        self.assertEqual(ev[-1]["session"], None)                                      # a job isn't a chat: the page's chat session is left alone

    def test_a_load_writes_the_transcript_and_the_chat_from_the_tool_results(self):
        ev = self.run_job("load", route_steps())
        out = self.outcome(ev)
        stem = f"{DAY} ABC Steering"
        self.assertEqual(out["files"], [f"inbox/{stem}.vtt", f"inbox/{stem} - chat.txt"])
        self.assertEqual(self.inbox(), [f"{stem} - chat.txt", f"{stem}.vtt"])
        vtt = (self.v.root / "inbox" / f"{stem}.vtt").read_text(encoding="utf-8")
        self.assertEqual([ln for ln in vtt.split("\n") if ln.startswith("<v ")], CUE_TEXTS)       # exactly what the tool returned
        self.assertIn("Event ID: ev-1", vtt)
        self.assertNotIn("passcode", vtt)
        chat = (self.v.root / "inbox" / f"{stem} - chat.txt").read_text(encoding="utf-8")
        self.assertIn("Event ID: ev-1", chat)
        self.assertIn("in full: https://example.test/plan", chat)
        self.assertNotIn("Running late", chat)                                         # before the meeting
        self.assertEqual(self.status(), "available")

    def test_a_spooled_result_gives_the_same_file(self):
        inline = self.run_job("load", route_steps(chat=False))
        want = (self.v.root / "inbox" / Path(self.outcome(inline)["files"][0]).name).read_bytes()
        self.setUp()
        spool = self.spool_dir / "tool-results" / "mcp-read_resource-7.txt"
        spool.parent.mkdir(exist_ok=True)
        spool.write_text(json.dumps([{"type": "text", "text": json.dumps(transcript_result())}]), encoding="utf-8")
        big = {**read(event()["meetingTranscriptUrl"], ""), "result": f"Error: result (190,431 characters) exceeds maximum allowed tokens. Output has been saved to {spool}\nFormat: JSON array of content blocks"}
        out = self.outcome(self.run_job("load", route_steps(tr=big, chat=False)))
        self.assertEqual((self.v.root / out["files"][0]).read_bytes(), want)           # byte for byte, inline or spooled

    def test_not_transcribed_and_no_access_load_nothing(self):
        empty = read(event()["meetingTranscriptUrl"], {"meeting": {"id": "m1"}, "transcripts": []})
        out = self.outcome(self.run_job("load", route_steps(tr=empty, chat=False)))
        self.assertEqual((out["status"], out["files"], self.inbox()), ("not_transcribed", [], []))
        denied = read(event()["meetingTranscriptUrl"], "Error 403: Forbidden - insufficient permissions to read the transcript", error=True)
        out = self.outcome(self.run_job("load", route_steps(tr=denied, chat=False)))
        self.assertEqual((out["status"], out["files"], self.status()), ("no_access", [], "no_access"))

    def test_an_in_person_meeting_is_no_transcript(self):
        ev = event(online=False)
        out = self.outcome(self.run_job("check", route_steps(ev=ev, chat=False)))
        self.assertEqual((out["status"], self.status()), ("none", "none"))

    def test_the_wrong_event_is_never_loaded(self):
        out = self.outcome(self.run_job("load", route_steps(ev=event(eid="ev-OTHER"), chat=False)))
        self.assertEqual((out["files"], self.inbox()), ([], []))
        self.assertIn("wasn't the one asked for", out["message"] + " ".join(out.get("files", [])) or "")

    def test_a_meeting_already_in_the_inbox_or_processed_is_not_loaded_again(self):
        first = self.outcome(self.run_job("load", route_steps(chat=False)))
        again = self.outcome(self.run_job("load", route_steps(chat=False)))
        self.assertEqual((again["files"], again["message"]), (first["files"], "Already in the inbox."))
        self.assertEqual(len(self.inbox()), 1)
        for f in (self.v.root / "inbox").glob("*"):
            f.unlink()
        with open(self.v.root / "system/processed.txt", "a") as f:
            f.write(f"{DAY} | calendar:ev-1 | projects/x | 1\n")
        done = self.outcome(self.run_job("load", route_steps(chat=False)))
        self.assertEqual((done["files"], self.inbox()), ([], []))
        self.assertIn("Already processed on", done["message"])

    def test_the_run_reads_everything_and_writes_nothing_itself(self):
        self.run_job("load", route_steps(chat=False))
        seen = json.loads((self.v.root / "fake_seen.json").read_text())
        for tool in ("read_resource", "outlook_calendar_search"):      # #365 M2: the two the prompt names (more before the tools delta)
            self.assertIn(M365 + tool, seen["allowed"])
        self.assertFalse([t for t in seen["allowed"] if t.startswith(("Write", "Edit"))])        # the server writes the files, not Claude
        self.assertIn(M365 + "outlook_send_mail", seen["disallowed"])
        self.assertIn("exactly as returned", seen["prompt"])
        self.assertIn("Do not search SharePoint", seen["prompt"])
        self.assertIn("ev-1", seen["prompt"])

    def test_an_unknown_meeting_is_refused(self):
        req = urllib.request.Request(self.base + "/api/transcripts/load", data=json.dumps({"id": "nope"}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req, timeout=20)
        self.assertEqual(cm.exception.code, 400)


class NoEventSaysWhy(unittest.TestCase):
    """#365: a load that never got the calendar event said the same sentence whatever happened, and logged nothing. It now says
    which of three things happened (no Microsoft 365 call at all, the event never read, the event read failed) and the debug
    log gets the counts of the tool results (names, error or ok, lengths), never text."""

    def finish(self, *calls):
        job = T.Job("ev-1", "ABC Steering", DAY, "08:00", "09:00", "load")
        for name, uri, text, err in calls:
            job.observe(M365 + name, {"uri": uri} if uri else {}, text, err)
        return job, job.finish()["message"]

    def test_no_call_at_all(self):
        job, msg = self.finish()
        self.assertIn("made no Microsoft 365 call", msg)
        self.assertEqual(job.diagnosis(), "0 tool results (none); event read: none")

    def test_search_only_never_read_the_event(self):
        job, msg = self.finish(("outlook_calendar_search", None, "boom", True))
        self.assertIn("never read the meeting's calendar event", msg)
        self.assertIn("outlook_calendar_search error 4", job.diagnosis())
        self.assertNotIn("boom", job.diagnosis())

    def test_event_read_failing_keeps_the_old_sentence(self):
        job, msg = self.finish(("read_resource", "calendar:///events/ev-1", "Error: 500", True))
        self.assertEqual(msg, "The meeting's calendar event couldn't be read, so nothing was loaded.")
        self.assertTrue(job.diagnosis().endswith("event read: error"))

    def test_an_event_that_is_not_json_is_unreadable(self):
        job, msg = self.finish(("read_resource", "calendar:///events/ev-1", "plain words", False))
        self.assertTrue(job.diagnosis().endswith("event read: unreadable"))

    def test_a_neighbour_read_first_does_not_fail_the_asked_event(self):      # M1: the day-window search lists the whole day
        other = dict(event(), id="ev-2", subject="Another meeting")
        job, msg = self.finish(("read_resource", "calendar:///events/ev-2", json.dumps(other), False),
                               ("read_resource", "calendar:///events/ev-1", json.dumps(event()), False))
        self.assertIsNotNone(job.event)
        self.assertFalse(job.wrong)
        self.assertNotIn("wasn't the one asked for", msg)

    def test_a_neighbour_read_after_it_changes_nothing(self):
        other = dict(event(), id="ev-2", subject="Another meeting")
        job, msg = self.finish(("read_resource", "calendar:///events/ev-1", json.dumps(event()), False),
                               ("read_resource", "calendar:///events/ev-2", json.dumps(other), False))
        self.assertIsNotNone(job.event)
        self.assertFalse(job.wrong)
        self.assertNotIn("wasn't the one asked for", msg)

    def test_only_a_neighbour_is_still_wrong(self):
        other = dict(event(), id="ev-2", subject="Another meeting")
        job, msg = self.finish(("read_resource", "calendar:///events/ev-2", json.dumps(other), False))
        self.assertIn("wasn't the one asked for", msg)

    def test_a_good_event_is_unchanged(self):
        job, msg = self.finish(("read_resource", "calendar:///events/ev-1", json.dumps(event()), False))
        self.assertIsNotNone(job.event)
        self.assertNotIn("nothing was loaded: try again", msg)


if __name__ == "__main__":
    unittest.main()
