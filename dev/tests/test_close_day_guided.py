"""BL-295 (sprint-close-day-server): Close the day as a guided shutdown, the server and Python side.

Run: python3 dev/tests/test_close_day_guided.py      (quick tier: no Chrome)
Covers the catch-up decision (stale, recent, off, busy, a sweep running, the development repository, ask first, Sweep again),
the settings defaults and update.py adding them, Loose ends and their three places (Review now, First thing tomorrow, Leave),
day-closed.json written with references only and read the next day by Today's brief, the catch-up sweep through the run engine
(it waits for a run already going, runs guarded in the "sweep" mode and only stages), a close that waits for the sweep, and the
prep queue (two pages, one at a time). The clock is fixed on Tuesday 13-10-2026 at 17:30; a stand-in Claude is used, so no model
is called, nothing is sent and Microsoft 365 is never read.
"""
import json
import os
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "system" / "scripts"))
import test_dashboard  # noqa: E402
from test_tracker import Vault  # noqa: E402
import close_day  # noqa: E402  (the repository's copy, for the pure functions only)

FIXED = date(2026, 10, 13)                              # a Tuesday
test_dashboard.TODAY = FIXED
NOW = f"{FIXED} 17:30"
os.environ["CREAITE_NOW"] = NOW
FAKE = r'''#!/usr/bin/env python3
import json, sys, time
from pathlib import Path
args = sys.argv[1:]
prompt = args[args.index("--") + 1] if "-p" in args else ""
root = Path.cwd()
with (root / "fake-calls.jsonl").open("a") as f:
    f.write(json.dumps({"prompt": prompt[:20], "args": args}) + "\n")
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-x"})
if prompt.startswith("slow"):
    time.sleep(3)
    reply = "Done slowly."
elif prompt == "sweep":
    if (root / "slow-sweep").exists():
        time.sleep(3)
    st = root / "system/staging"
    item = {"n": 1, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
            "values": {"project": "ABC", "description": "Tom to share the UAT plan", "owner": "Alan Carter", "raised": "2026-10-13",
                       "source": "Email · From: Tom <tom@abc.example> · Subject: UAT · Sent: 2026-10-13 17:20"}}
    (st / f"proposed-2026-10-13-1731-sweep-{time.time_ns()}.json").write_text(json.dumps(
        {"created": "2026-10-13T17:31:00", "source_run": "cx-sweep", "files": [], "items": [item]}))
    (st / "last-sweep.txt").write_text("2026-10-13 17:31\n")
    reply = "Sweep: 1 item."
else:
    reply = json.dumps({"about": "The steering committee.", "notes": [], "questions": ["Is UAT booked?"], "m365": "searched"})
out({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}})
out({"type": "result", "result": reply, "session_id": "sess-x"})
'''


def ev(eid, start, end, title, **more):
    return {"id": eid, "start": start, "end": end, "title": title, "where": "Teams", "teams": True, "all_day": False,
            "private": False, "organiser": "Jane Doe", "sensitivity": "normal", "body": "Agenda", "attendees": [], **more}


CALENDAR = {"fetched": f"{FIXED} 07:00", "days": {
    "2026-10-13": [ev("e1", "11:00", "12:00", "ABC design chat")],
    "2026-10-14": [ev("m1", "10:00", "11:00", "ABC steering"), ev("m2", "14:00", "14:30", "DEF sync"),
                   ev("m3", "15:00", "15:30", "ABC board", sensitivity="confidential", body=""),
                   {"id": "m4", "start": "16:00", "end": "16:30", "title": "Busy", "where": "", "teams": False, "all_day": False,
                    "private": True, "organiser": False}]}}


def world(v):
    """populate's portfolio, an action due today, a pending proposal, a file in inbox/, a transcript ready, tomorrow's calendar."""
    test_dashboard.populate(v)
    st = v.root / "system/staging"
    v.propose("due", [{"n": 1, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "approved",
                       "values": {"project": "ABC", "description": "Send the cutover checklist", "owner": "Alan Carter",
                                  "due_date": "2026-10-13", "raised": "2026-10-12", "source": "s"}}])
    v.run("apply")
    v.propose("waiting", [{"n": 1, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
                           "values": {"project": "DEF", "description": "Draft the pilot charter", "owner": "Omar Ali",
                                      "raised": "2026-10-13", "source": "s"}}])
    (st / "calendar.json").write_text(json.dumps(CALENDAR))
    (st / "transcripts.json").write_text(json.dumps({"checked": {"e1": {"status": "available", "checked": "2026-10-13 13:00"}}}))
    (st / "last-sweep.txt").write_text("2026-10-13 09:00\n")
    (v.root / "inbox").mkdir(exist_ok=True)
    (v.root / "inbox" / "Recording 2026-10-13.vtt").write_text("WEBVTT\n")


def py(v, code, env=None):
    """Run Python in the vault with its scripts on the path; its stdout's last line as JSON."""
    r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); " + code], cwd=v.root,
                       capture_output=True, text=True, timeout=120, env={**os.environ, **(env or {})})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


class CatchupDecision(unittest.TestCase):
    """close_day.catchup_decision: when the card's catch-up sweep starts, and why not."""
    now = datetime(2026, 10, 13, 17, 30)

    def say(self, last, mode="start", **kw):
        return close_day.catchup_decision(self.now, last, mode, 30, **kw)

    def test_stale_starts_and_recent_says_when(self):
        self.assertEqual(self.say(datetime(2026, 10, 13, 9, 0))["status"], "start")
        self.assertEqual(self.say(None)["status"], "start")                                  # never swept
        recent = self.say(datetime(2026, 10, 13, 17, 10))
        self.assertEqual((recent["status"], recent["message"]), ("recent", "Caught up at 17:10."))
        self.assertEqual(self.say(datetime(2026, 10, 12, 18, 0))["last_shown"], "12-10-2026 18:00")

    def test_off_offer_busy_sweeping_and_the_development_repository(self):
        old = datetime(2026, 10, 13, 9, 0)
        self.assertEqual(self.say(old, "off")["status"], "off")
        self.assertEqual(self.say(old, "offer")["status"], "offer")
        self.assertEqual(self.say(old, busy=True)["status"], "busy")
        self.assertEqual(self.say(old, sweeping=True)["status"], "sweeping")
        self.assertEqual(self.say(old, dev=True)["status"], "cant")
        self.assertEqual(self.say(datetime(2026, 10, 13, 17, 10), busy=True)["status"], "recent")   # nothing to wait for

    def test_sweep_again_passes_recent_off_and_offer_but_never_busy_or_the_dev_repo(self):
        recent = datetime(2026, 10, 13, 17, 20)
        for mode in ("start", "offer", "off"):
            self.assertEqual(self.say(recent, mode, force=True)["status"], "start")
        self.assertEqual(self.say(recent, force=True, busy=True)["status"], "busy")
        self.assertEqual(self.say(recent, force=True, dev=True)["status"], "cant")


class Settings(unittest.TestCase):
    def test_defaults_and_odd_values(self):
        defaults = json.loads((REPO / "system/templates/settings-defaults.json").read_text())
        self.assertEqual((defaults["day"]["catchup_sweep"], defaults["day"]["catchup_after_minutes"]), ("start", 30))
        self.assertEqual(close_day.catchup_settings({}), ("start", 30))
        self.assertEqual(close_day.catchup_settings({"day": {"catchup_sweep": "offer", "catchup_after_minutes": "45"}}), ("offer", 45))
        self.assertEqual(close_day.catchup_settings({"day": {"catchup_sweep": False, "catchup_after_minutes": "x"}}), ("off", 30))
        self.assertEqual(close_day.catchup_settings({"day": {"catchup_sweep": "sometimes"}})[0], "start")

    def test_an_update_adds_them_and_keeps_alans_values(self):
        import update
        defaults = json.loads((REPO / "system/templates/settings-defaults.json").read_text())
        mine = {"day": {"close_from": "17:00"}, "sweep": {"due_from": "06:30"}}
        added = update.merge_new(mine, defaults)
        self.assertIn("day.catchup_sweep", added)
        self.assertIn("day.catchup_after_minutes", added)
        self.assertEqual((mine["day"]["close_from"], mine["sweep"]["due_from"]), ("17:00", "06:30"))
        again = {"day": {"catchup_sweep": "off"}}
        update.merge_new(again, defaults)
        self.assertEqual(again["day"]["catchup_sweep"], "off")


class LooseEndsShape(unittest.TestCase):
    """The pure part of Loose ends and the plan."""

    def test_rows_new_first_and_the_plan_keeps_references_only(self):
        d = {"projects": [{"code": "ABC", "name": "Example Programme"}],
             "review": [{"file": "proposed-a.json", "ref": 1, "kind": "actions", "p": "ABC", "rec": {"t": "Old thing"}},
                        {"file": "proposed-s.json", "ref": 2, "kind": "raid", "p": "ABC", "rec": {"t": "New risk", "type": "Risk"}},
                        {"file": "proposed-a.json", "ref": "meeting", "kind": "draft", "p": "ABC", "rec": {"t": "Minutes: x"}}],
             "inbox": [{"path": "inbox/a.vtt", "name": "a.vtt", "state": "new"}, {"path": "inbox/b.vtt", "name": "b.vtt", "state": "processed"}],
             "meetings": {"rows": [{"id": "e1", "title": "ABC chat", "transcript": "available", "p": "ABC"},
                                   {"id": "e2", "title": "Done", "transcript": "available", "processed": "2026-10-13"}]},
             "actions": [{"id": "ABC-A-009", "due": "2026-10-13", "st": "Open", "t": "Due now", "p": "ABC"},
                         {"id": "ABC-A-010", "due": "2026-10-13", "st": "Closed", "t": "Done", "p": "ABC"},
                         {"id": "ABC-A-012", "due": "2026-10-09", "st": "Delayed", "t": "Late", "p": "ABC"},
                         {"id": "ABC-A-013", "due": "2026-10-20", "st": "Open", "t": "Later", "p": "ABC"}],
             "raid": [{"id": "ABC-011", "due": "2026-10-13", "st": "Open", "t": "Risky", "p": "ABC", "type": "Risk"}]}
        rows = close_day.loose_ends(d, FIXED, ["proposed-s.json"])
        self.assertEqual([r["ref"] for r in rows], ["p:proposed-s.json#2", "p:proposed-a.json#1", "p:proposed-a.json#meeting",
                                                    f"f:{close_day.fingerprint('inbox/a.vtt')}", "t:e1", "i:ABC-A-009", "i:ABC-011", "i:ABC-A-012"])
        self.assertEqual([r["type"] for r in rows], ["Risk", "Action", "Minutes", "File in Intake", "Transcript ready",
                                                     "Action due today", "Risk due today", "Action overdue"])
        self.assertTrue(all(r["place"] == "first" and r["project"] == "Example Programme" for r in rows if r["p"]))
        plan = close_day.make_plan({rows[0]["ref"]: "review", rows[1]["ref"]: "first", rows[5]["ref"]: "review",
                                    rows[3]["ref"]: "leave", "not a ref": "first"}, prep=2)
        self.assertEqual(plan, {"first": ["p:proposed-a.json#1"], "review": ["p:proposed-s.json#2", "i:ABC-A-009"], "left": 1,
                                "prep": 2, "swept": None})
        self.assertEqual(close_day.open_lists(plan), {"review": [{"file": "proposed-s.json", "ref": 2}], "work": ["ABC-A-009"],
                                                      "intake": False})
        self.assertEqual(close_day.counts(plan), {"review": 2, "first": 1, "left": 1, "prep": 2})


class SweepGuard(unittest.TestCase):
    """The guard hook's "sweep" mode: a plain chat's rules plus mapping names in its own draft."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def decide(self, tool, inp, mode="sweep"):
        return py(self.v, f"import reach; print(json.dumps(reach.hook_decision({tool!r}, {inp!r}, {mode!r}, 'r1')))")

    def test_record_commands_are_refused_and_staging_allowed(self):
        bash = lambda c: self.decide("Bash", {"command": c})[0]  # noqa: E731
        self.assertFalse(bash("system/scripts/run tracker.py apply"))
        self.assertFalse(bash("system/scripts/run review.py approve 1"))
        self.assertFalse(bash("system/scripts/run propose.py people map system/staging/proposed-x.json"))
        self.assertTrue(bash("system/scripts/run propose.py people map system/staging/drafts/sweep.json"))
        self.assertTrue(bash("system/scripts/run sweep.py stage system/staging/drafts/sweep.json"))
        self.assertTrue(bash("python3 system/scripts/sweep.py lock"))
        self.assertFalse(self.decide("Bash", {"command": "system/scripts/run propose.py people map system/staging/drafts/sweep.json"},
                                     "ask")[0])                                                 # a plain chat: unchanged
        self.assertTrue(self.decide("Write", {"file_path": str(self.v.root / "system/staging/drafts/sweep.json")})[0])
        self.assertFalse(self.decide("Write", {"file_path": str(self.v.root / "system/staging/proposed-x.json")})[0])
        self.assertFalse(self.decide("Write", {"file_path": str(self.v.root / "CLAUDE.md")})[0])


class ThroughTheServer(unittest.TestCase):
    """The routes, in order: the card, the catch-up (off, the dev repo, busy then started, recent), closing, a close that waits
    for the sweep, the prep queue, and the next day's First thing tomorrow."""

    @classmethod
    def setUpClass(cls):
        from test_live_server import free_port
        cls.v = v = Vault()
        world(v)
        fake = v.root / "fake_claude.py"
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
        import re
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body=None, raw=False):
        req = urllib.request.Request(self.base + path, data=json.dumps(body or {}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                text = r.read().decode()
        except urllib.error.HTTPError as e:
            with e:
                return {"status": e.code, **json.loads(e.read().decode())}
        return text if raw else json.loads(text)

    def until(self, test, seconds=25):
        end = time.time() + seconds
        while time.time() < end:
            got = test()
            if got:
                return got
            time.sleep(0.2)
        self.fail("timed out")

    def settings(self, **day):
        p = self.v.root / "system/config/settings.json"
        s = json.loads(p.read_text())
        s.setdefault("day", {}).update(day)
        p.write_text(json.dumps(s, indent=2))

    def calls(self):
        f = self.v.root / "fake-calls.jsonl"
        return [json.loads(ln) for ln in f.read_text().splitlines()] if f.exists() else []

    def snapshot(self):
        return [self.v.rows(t) for t in ("actions", "raid", "decisions")]

    def test_1_the_card_lists_loose_ends_and_tomorrow(self):
        card = self.post("/api/day/card")
        refs = {r["ref"]: r for r in card["loose"]}
        due = next(r for r in card["loose"] if r["t"] == "Send the cutover checklist")
        self.assertEqual((due["type"], due["place"]), ("Action due today", "first"))
        self.assertIn("t:e1", refs)
        self.assertTrue(any(r["type"] == "File in Intake" and r["t"] == "Recording 2026-10-13.vtt" for r in card["loose"]))
        self.assertTrue(any(r["t"] == "Draft the pilot charter" and r["project"] == "Digital Enablement" for r in card["loose"]))
        tm = card["tomorrow"]
        self.assertEqual((tm["day"], tm["day_shown"], tm["long"]), ("2026-10-14", "14-10-2026", "Wednesday 14th October"))
        self.assertEqual([(m["title"], m["make"]) for m in tm["meetings"]],
                         [("ABC steering", True), ("DEF sync", True), ("ABC board", True)])   # the private one is left out
        board = tm["meetings"][2]
        self.assertTrue(board["confidential"])
        self.assertNotIn("p", board)
        self.assertIsNone(card["catchup"]["state"])
        self.assertIsNone(card["day"]["first"])
        self.assertEqual(card["day"]["catchup"], {"mode": "start", "after": 30})

    def test_2_off_and_the_development_repository_start_nothing(self):
        self.settings(catchup_sweep="off")
        try:
            self.assertEqual(self.post("/api/day/catchup")["status"], "off")
        finally:
            self.settings(catchup_sweep="start")
        marker = self.v.root / ".creaite-dev"
        marker.write_text("")
        try:
            out = self.post("/api/day/catchup")
            self.assertEqual(out["status"], "cant")
            self.assertIn("never reads Microsoft 365", out["message"])
        finally:
            marker.unlink()
        self.assertFalse(any(c["prompt"] == "sweep" for c in self.calls()))

    def test_3_a_busy_run_makes_it_wait_then_the_guarded_sweep_runs_and_lists_what_it_found(self):
        before = self.snapshot()
        t = threading.Thread(target=self.post, args=("/api/ask", {"message": "slow please"}), kwargs={"raw": True}, daemon=True)
        t.start()
        self.until(lambda: (self.post("/api/ask/running").get("run") or {}).get("done") is False)
        out = self.post("/api/day/catchup")
        self.assertEqual((out["status"], out["catchup"]["state"]), ("busy", "waiting"))
        self.assertIn("one run at a time", out["message"])
        st = self.until(lambda: (lambda s: s if s["state"] == "done" else None)(self.post("/api/day/catchup/status")))
        self.assertEqual([(f["type"], f["t"], f["project"]) for f in st["found"]],
                         [("Action", "Tom to share the UAT plan", "Example Programme")])
        sweep = next(c["args"] for c in self.calls() if c["prompt"] == "sweep")
        allowed = sweep[sweep.index("--allowedTools") + 1]
        self.assertIn("--settings", sweep)                                       # the guard hook (BL-141)
        self.assertIn("--mode sweep", sweep[sweep.index("--settings") + 1])
        self.assertIn("sweep.py *", allowed)
        self.assertNotIn("tracker.py apply", allowed)
        self.assertNotIn("filechange.py *)", allowed)                         # no file changes, only its read commands
        self.assertIn("catch-up sweep", sweep[sweep.index("--append-system-prompt") + 1])
        self.assertEqual(self.snapshot(), before)                                # it only staged
        card = self.post("/api/day/card")
        self.assertTrue(card["loose"][0]["new"] and card["loose"][0]["t"] == "Tom to share the UAT plan")

    def test_4_swept_recently_says_caught_up(self):
        out = self.post("/api/day/catchup")
        self.assertEqual((out["status"], out["message"]), ("recent", "Caught up at 17:31."))

    def test_5_closing_keeps_ids_only_and_approves_nothing(self):
        card = self.post("/api/day/card")
        staged = {p.name: p.read_text() for p in (self.v.root / "system/staging").glob("proposed-*.json")}
        before = self.snapshot()
        due = next(r["ref"] for r in card["loose"] if r["type"] == "Action due today")
        new = card["loose"][0]["ref"]
        charter = next(r["ref"] for r in card["loose"] if r["t"] == "Draft the pilot charter")
        keys = [m["key"] for m in card["tomorrow"]["meetings"][:2]]
        out = self.post("/api/day/close", {"choices": {new: "review", charter: "first", due: "first", "t:e1": "leave"}, "prep": keys})
        self.assertEqual((out["ok"], out["pending"], out["at"]), (True, False, "17:30"))
        self.assertEqual(out["counts"], {"review": 1, "first": 2, "left": 1, "prep": 2})
        self.assertEqual(out["open"]["review"][0]["ref"], 1)
        rec = json.loads((self.v.root / "system/staging/day-closed.json").read_text())
        self.assertEqual(rec["days"]["2026-10-13"], "17:30")
        self.assertEqual(rec["plans"]["2026-10-13"]["first"], [charter, due])
        text = json.dumps(rec)
        for words in ("cutover", "charter", "Tom", "steering", "ABC design chat"):
            self.assertNotIn(words, text)                                        # references only, never text
        self.assertEqual(self.snapshot(), before)
        self.assertEqual({p.name: p.read_text() for p in (self.v.root / "system/staging").glob("proposed-*.json")}, staged)
        self.assertEqual(self.post("/api/day/close", {"choices": {"p:../x.json#1": "first"}})["status"], 400)
        self.assertEqual(self.post("/api/day/close", {"choices": {due: "approve"}})["status"], 400)

    def test_6_the_prep_queue_makes_both_pages_one_at_a_time(self):
        q = self.until(lambda: (lambda s: s if s["items"] and all(i["state"] in ("made", "failed", "stopped") for i in s["items"])
                                else None)(self.post("/api/day/prep", {"op": "list"})), 40)
        self.assertEqual([i["state"] for i in q["items"]], ["made", "made"], q)
        for i in q["items"]:
            self.assertTrue((self.v.root / i["path"]).is_file() or i["path"].startswith("projects/"))
        tm = self.post("/api/day/card")["tomorrow"]["meetings"]
        self.assertEqual([m["make"] for m in tm[:2]], [False, False])                 # each now has its page
        self.assertEqual(self.post("/api/day/prep", {"op": "add", "keys": ["not a key"]})["status"], 400)

    def test_7_closing_while_the_sweep_runs_closes_when_it_ends(self):
        (self.v.root / "slow-sweep").write_text("")
        try:
            started = self.post("/api/day/catchup", {"force": True})                  # Sweep again
            self.assertEqual(started["status"], "start")
            out = self.post("/api/day/close", {"choices": {}})
            self.assertTrue(out["pending"])
            self.until(lambda: self.post("/api/day/catchup/status")["state"] == "done")
            plan = self.until(lambda: json.loads((self.v.root / "system/staging/day-closed.json").read_text())["plans"]
                              .get("2026-10-13", {}).get("first"))
        finally:
            (self.v.root / "slow-sweep").unlink()
        self.assertEqual(len(plan), 1)                                                 # what it found, unplaced: first thing
        self.assertRegex(plan[0], r"^p:proposed-2026-10-13-1731-sweep-\d+\.json#1$")
        self.assertEqual(json.loads((self.v.root / "system/staging/day-closed.json").read_text())["plans"]["2026-10-13"]["swept"],
                         "17:30")

    def test_8_tomorrows_brief_reads_first_thing_and_closing_tomorrow_clears_it(self):
        p = self.v.root / "system/staging/day-closed.json"
        rec = json.loads(p.read_text())
        due_id = next(a["id"] for a in self.v.rows("actions") if a["description"] == "Send the cutover checklist")
        rec["plans"]["2026-10-13"]["first"] = ["p:proposed-waiting.json#1", f"i:{due_id}", "t:e1",       # one of each kind
                                               f"f:{close_day.fingerprint('inbox/Recording 2026-10-13.vtt')}"]
        p.write_text(json.dumps(rec))
        env = {"CREAITE_NOW": "2026-10-14 08:00"}
        first = py(self.v, "import build_dashboard; print(json.dumps(build_dashboard.collect()['day']['first']))", env)
        self.assertEqual((first["day"], first["day_shown"]), ("2026-10-13", "13-10-2026"))
        self.assertEqual([(i["type"], i["open"]) for i in first["items"]],
                         [("Action", True), ("Action", True), ("Transcript ready", True), ("File in Intake", True)])
        self.assertEqual(first["items"][0]["t"], "Draft the pilot charter")
        self.assertIn("Send the cutover checklist", first["items"][1]["t"])
        self.assertEqual(first["items"][2]["t"], "ABC design chat")
        # Alan, 13-10-2026: the session-start line lists it too
        said = py(self.v, "import session, sweep; f = session.first_thing(sweep.now()); print(json.dumps([f, session.first_line(f)]))", env)
        self.assertEqual(len(said[0]["items"]), 4)
        self.assertTrue(said[1].startswith("First thing (from Close the day on 13-10-2026): 4 open — Action: Draft the pilot charter;"),
                        said[1])
        py(self.v, "import build_dashboard; print(json.dumps(build_dashboard.close_day('2026-10-14', '18:00')))", env)
        later = py(self.v, "import build_dashboard; print(json.dumps(build_dashboard.collect()['day']['first']))",
                   {"CREAITE_NOW": "2026-10-15 08:00"})
        self.assertIsNone(later)
        self.assertEqual(json.loads(p.read_text())["days"]["2026-10-13"], "17:30")       # BL-206's record is kept

    def test_9_the_log_has_counts_and_ids_only(self):
        logs = "".join(f.read_text() for f in (self.v.root / "system/logs").glob("debug-*.log"))
        lines = [ln for ln in logs.splitlines() if " day " in ln or "day:" in ln or "\tday\t" in ln or "catch-up" in ln]
        self.assertTrue(any("catch-up: started" in ln for ln in lines), lines[:5])
        for words in ("cutover", "charter", "Tom", "steering"):
            self.assertFalse(any(words in ln for ln in lines))


if __name__ == "__main__":
    unittest.main()
