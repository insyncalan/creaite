"""#250 (#181 C2): fetch meeting transcripts as they appear, as a sweep step.

Run: python3 dev/tests/test_fetch_transcripts.py
Microsoft 365 is never called: the reads a sweep makes are stubbed with fixture results (fictional meetings), saved where Claude
Code saves a large tool result (CREAITE_TOOL_RESULTS stands in for its folder), or handed to the live server's observer.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_meetings import week_calendar  # noqa: E402
from test_tracker import REPO, Vault  # noqa: E402
from test_transcripts import DAY, NOW, VTT, event, transcript_result  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import permissions  # noqa: E402
import transcripts as T  # noqa: E402

URI = event()["meetingTranscriptUrl"]


class Fetch(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        self.v.run("init")
        week_calendar(self.v)
        self.spool = Path(tempfile.mkdtemp())
        self.env = {**os.environ, "CREAITE_NOW": NOW, "CREAITE_TOOL_RESULTS": str(self.spool)}
        self.before = self.v.snapshot()[0]

    def set_on(self, on=True):
        cfg = self.v.root / "system/config/settings.json"
        d = json.loads(cfg.read_text())
        d.setdefault("sweep", {})["fetch_transcripts"] = on
        cfg.write_text(json.dumps(d))

    def sweep(self, *args):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/sweep.py"), *args], cwd=self.v.root,
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        return r.stdout

    def saved_result(self, name="mcp-read_resource-1.txt", result=None):
        p = self.spool / "tool-results" / name
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps([{"type": "text", "text": json.dumps(result or transcript_result())}]), encoding="utf-8")
        return p

    def record(self, *facts):
        f = self.v.root / "system/staging/drafts/transcripts.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"results": list(facts)}))
        return json.loads(self.sweep("transcripts", "record", str(f)))

    def fact(self, eid="ev-1", **kw):
        return {"id": eid, "online": True, "uri": URI, "count": 1, "error": None, **kw}

    def inbox(self):
        return sorted(p.name for p in (self.v.root / "inbox").iterdir() if p.suffix in (".vtt", ".txt"))

    def state(self):
        return json.loads((self.v.root / "system/staging/transcripts.json").read_text())["checked"]

    def tracker_untouched(self):
        self.assertEqual(self.v.snapshot()[0], self.before)                       # nothing reached the tracker
        self.assertEqual(list((self.v.root / "system/staging").glob("proposed-*.json")), [])   # and nothing was staged

    # ── off by default, and off means nothing happens ──
    def test_the_setting_is_off_by_default(self):
        defaults = json.loads((REPO / "system/templates/settings-defaults.json").read_text())
        self.assertIs(defaults["sweep"]["fetch_transcripts"], False)
        self.assertIs(json.loads((REPO / "system/config/settings.json").read_text())["sweep"]["fetch_transcripts"], False)
        import settings_catalogue
        self.assertEqual(settings_catalogue.CATALOGUE["sweep.fetch_transcripts"][1], "Fetch transcripts as they appear")
        self.assertFalse(T.fetch_on({"sweep": {}}))                                # a vault without the key: off
        self.assertFalse(T.fetch_on({"sweep": {"fetch_transcripts": "yes"}}))     # only exactly true turns it on

    def test_off_nothing_is_fetched(self):
        todo = json.loads(self.sweep("transcripts", "todo"))
        self.assertFalse(todo["fetch_transcripts"])
        self.assertTrue(all("fetch" not in m for m in todo["look_up"]))
        out = self.record(self.fact(result_file=str(self.saved_result())))
        self.assertEqual(out["recorded"], {"ev-1": "available"})                  # the status is kept, as today
        self.assertNotIn("fetch", out)
        self.assertEqual(self.inbox(), [])                                         # fetched on Process only
        self.assertNotIn("fetched", self.state()["ev-1"])
        self.assertFalse((self.v.root / "system/staging/sweep-fetched.json").exists())
        self.assertNotIn("Fetched", self.sweep("done", "--started", NOW, "--normal"))
        self.tracker_untouched()

    # ── on: fetched once, into inbox/, as Load writes it ──
    def test_on_an_ended_meeting_is_fetched_once(self):
        self.set_on()
        todo = json.loads(self.sweep("transcripts", "todo"))
        self.assertTrue(todo["fetch_transcripts"])
        listed = {m["id"]: m for m in todo["look_up"]}
        self.assertTrue(listed["ev-1"]["fetch"])
        out = self.record(self.fact(result_file=str(self.saved_result())))
        self.assertEqual(out["fetch"], {"ev-1": "fetched"})
        files = self.inbox()
        self.assertEqual(files, [f"{DAY} ABC Steering.vtt"])
        text = (self.v.root / "inbox" / files[0]).read_text(encoding="utf-8")
        self.assertIn("Event ID: ev-1", text)                                      # Intake reads it as loaded
        self.assertIn("UAT starts 12-11-2026", text)                               # every word, from Microsoft 365's own result
        kept = (self.v.root / "system/staging/transcripts.json").read_text()
        self.assertNotIn("WEBVTT", kept)                                           # transcripts.json: status, URL and dates only
        self.assertNotIn("Welcome", kept)
        self.assertEqual(set(self.state()["ev-1"]) - set(T.KEEP), set())
        self.assertTrue(self.state()["ev-1"]["fetched"])
        self.assertIn("Fetched 1 transcript", self.sweep("done", "--started", NOW, "--normal"))
        # a second sweep: not listed for a fetch again, and a second record doesn't fetch it again
        again = {m["id"]: m for m in json.loads(self.sweep("transcripts", "todo"))["look_up"]}
        self.assertNotIn("ev-1", again)
        out = self.record(self.fact(result_file=str(self.saved_result("mcp-read_resource-2.txt"))))
        self.assertNotIn("fetch", out)
        self.assertEqual(self.inbox(), files)
        self.assertNotIn("Fetched", self.sweep("done", "--started", NOW, "--normal"))
        # a later look-up keeps when it was fetched
        code = ("import sys; sys.path.insert(0,'system/scripts'); import transcripts as T; "
                "T.keep('ev-1', {'status':'available','uri':'meeting-transcript:///x','count':1})")
        subprocess.run([sys.executable, "-c", code], cwd=self.v.root, check=True, env=self.env)
        self.assertTrue(self.state()["ev-1"]["fetched"])
        self.tracker_untouched()

    def test_confidential_meetings_are_never_fetched(self):
        self.set_on()
        cal_p = self.v.root / "system/staging/calendar.json"
        cal = json.loads(cal_p.read_text())
        for ev in cal["days"][DAY]:
            if ev.get("id") == "ev-1":
                ev["sensitivity"] = "confidential"
        cal_p.write_text(json.dumps(cal))
        listed = {m["id"]: m for m in json.loads(self.sweep("transcripts", "todo"))["look_up"]}
        self.assertFalse(listed["ev-1"]["fetch"])                                  # its status is still looked up
        self.assertTrue(listed["ev-2"]["fetch"])                                   # and nothing else is skipped
        out = self.record(self.fact(result_file=str(self.saved_result())))
        self.assertNotIn("fetch", out)
        self.assertEqual(self.inbox(), [])

    def test_processed_cleared_and_loaded_meetings_are_left_alone(self):
        self.set_on()
        with open(self.v.root / "system/processed.txt", "a") as f:
            f.write(f"{DAY} | calendar:ev-1 | projects/x | 1\n")
        (self.v.root / "inbox" / "Already.vtt").write_text(T.tidy_vtt(VTT, {"title": "Weekly sync 12", "day": DAY, "id": "ev-2"}))
        listed = {m["id"]: m for m in json.loads(self.sweep("transcripts", "todo"))["look_up"]}
        self.assertNotIn("ev-1", listed)
        self.assertFalse(listed.get("ev-2", {}).get("fetch", False))
        out = self.record(self.fact(result_file=str(self.saved_result())), self.fact("ev-2", result_file=str(self.saved_result("b.txt"))))
        self.assertNotIn("fetch", out)
        self.assertEqual(self.inbox(), ["Already.vtt"])

    def test_a_failure_is_reported_and_tried_next_time(self):
        self.set_on()
        out = self.record(self.fact(count=None, error="other"))
        self.assertEqual(out["fetch"], {"ev-1": "failed"})
        self.assertEqual(self.inbox(), [])
        said = self.sweep("done", "--started", NOW, "--normal")
        self.assertIn("Fetched 0 transcripts", said)
        self.assertIn("couldn't be reached", said)
        self.assertTrue(json.loads(self.sweep("transcripts", "todo"))["look_up"][0]["fetch"])

    def test_an_inline_result_is_left_for_process_and_a_file_elsewhere_is_never_read(self):
        self.set_on()
        out = self.record(self.fact())                                             # no saved file: never re-typed
        self.assertEqual(out["fetch"], {"ev-1": "left"})
        elsewhere = Path(tempfile.mkdtemp()) / "x.txt"
        elsewhere.write_text(json.dumps(transcript_result()))
        out = self.record(self.fact(result_file=str(elsewhere)))
        self.assertEqual(out["fetch"], {"ev-1": "left"})
        self.assertEqual(self.inbox(), [])
        self.assertIn("1 left to fetch on Process", self.sweep("done", "--started", NOW, "--normal"))

    # ── the live server's copy of a sweep run's reads ──
    def observe(self):
        steps = [("calendar:///events/ev-1", event()), (URI, transcript_result())]
        code = ("import json, sys; sys.path.insert(0,'system/scripts'); import transcripts as T; j = T.SweepFetch(); "
                f"steps = json.loads({json.dumps(json.dumps(steps))}); "
                "[j.observe(T.M365 + 'read_resource', {'uri': u}, json.dumps(r)) for u, r in steps]; "
                "j.observe(T.M365 + 'outlook_send_mail', {}, '{}'); print(json.dumps(j.outcomes))")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_the_servers_observer_fetches_only_when_on(self):
        self.assertEqual(self.observe(), {})
        self.assertEqual(self.inbox(), [])
        self.set_on()
        self.assertEqual(self.observe(), {"ev-1": "fetched"})
        self.assertEqual(self.inbox(), [f"{DAY} ABC Steering.vtt"])
        self.assertEqual(self.observe(), {})                                       # a repeat run: not fetched again
        self.assertIn("Fetched 1 transcript", self.sweep("done", "--started", NOW, "--normal"))
        self.tracker_untouched()


class Guard(unittest.TestCase):
    """Read only: the fetch uses Microsoft 365 reading tools only, and the sweep run's tool list holds no action tool."""

    def test_the_fetch_tools_are_reading_tools(self):
        self.assertEqual(set(T.FETCH_TOOLS), {"mcp__claude_ai_Microsoft_365__outlook_calendar_search",
                                              "mcp__claude_ai_Microsoft_365__read_resource"})
        self.assertTrue(set(T.FETCH_TOOLS) <= set(permissions.m365_read_tools()))
        self.assertFalse(set(T.FETCH_TOOLS) & set(permissions.m365_action_tools()))

    def test_the_sweep_runs_tool_list_has_no_write_tool(self):
        import live_server
        tools = live_server.KIND_TOOLS["sweep"]
        self.assertTrue(set(T.FETCH_TOOLS) <= set(tools))                         # nothing new needs allowing
        actions = set(permissions.m365_action_tools())
        self.assertFalse(actions & set(tools))
        self.assertFalse([t for t in tools if t.startswith("mcp__") and t not in permissions.m365_read_tools()])
        self.assertTrue(actions <= set(live_server.DENY_TOOLS))                    # and every action stays denied
        self.assertFalse([t for t in tools if t.startswith(("Write(", "Edit(")) and "system/staging/drafts/" not in t])


if __name__ == "__main__":
    unittest.main()
