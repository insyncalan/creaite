"""BL-309 (sprint-panel-sweep): "sweep" typed in the ask creaite panel is its own confirmation.

Run: python3 dev/tests/test_panel_sweep.py      (quick tier: no Chrome)
Covers the server's recogniser (cx-sweep's own words, and nothing more), and, through the live server with a stand-in Claude,
that a typed sweep starts under BL-295's guarded "sweep" mode and stages, that in that same run the real guard hook still refuses
tracker.py apply, undo, review.py approve and reject, propose.py stage and a direct write outside drafts, and that a mixed request
("sweep and apply") is a plain chat under today's rules. No model is called, nothing is sent and Microsoft 365 is never read.
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
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "system" / "scripts"))
import test_dashboard  # noqa: E402
from test_tracker import Vault  # noqa: E402

# The stand-in Claude: records its arguments; for a request that starts with "sweep" or "refresh" it asks the run's own guard
# hook (from --settings, exactly as Claude Code would) about a set of calls and records each verdict, then stages one proposal.
FAKE = r'''#!/usr/bin/env python3
import json, subprocess, sys, time
from pathlib import Path
args = sys.argv[1:]
prompt = args[args.index("--") + 1] if "-p" in args else ""
root = Path.cwd()
verdicts = {}
if "--settings" in args and prompt.lower().startswith(("sweep", "refresh")):
    hook = json.loads(args[args.index("--settings") + 1])["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    calls = {
        "stage": ("Bash", {"command": "system/scripts/run sweep.py stage system/staging/drafts/sweep.json"}),
        "map": ("Bash", {"command": "system/scripts/run propose.py people map system/staging/drafts/sweep.json"}),
        "apply": ("Bash", {"command": "system/scripts/run tracker.py apply"}),
        "undo": ("Bash", {"command": "system/scripts/run tracker.py undo"}),
        "approve": ("Bash", {"command": "system/scripts/run review.py approve 1"}),
        "reject": ("Bash", {"command": "system/scripts/run review.py reject 1"}),
        "propose_stage": ("Bash", {"command": "system/scripts/run propose.py stage system/staging/drafts/x.json"}),
        "write_drafts": ("Write", {"file_path": str(root / "system/staging/drafts/sweep.json")}),
        "write_staging": ("Write", {"file_path": str(root / "system/staging/proposed-x.json")}),
        "write_root": ("Write", {"file_path": str(root / "CLAUDE.md")}),
    }
    for name, (tool, inp) in calls.items():
        r = subprocess.run(hook, shell=True, cwd=root, input=json.dumps({"tool_name": tool, "tool_input": inp}),
                           capture_output=True, text=True, timeout=60)
        verdicts[name] = r.returncode
with (root / "fake-calls.jsonl").open("a") as f:
    f.write(json.dumps({"prompt": prompt, "args": args, "verdicts": verdicts}) + "\n")
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-p"})
if prompt.lower().startswith(("sweep", "refresh")) and "--mode sweep" in " ".join(args):
    st = root / "system/staging"
    item = {"n": 1, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
            "values": {"project": "ABC", "description": "Tom to share the UAT plan", "owner": "Alan Carter", "raised": "2026-10-13",
                       "source": "Email · From: Tom <tom@abc.example> · Subject: UAT · Sent: 2026-10-13 17:20"}}
    (st / f"proposed-2026-10-13-1731-sweep-{time.time_ns()}.json").write_text(json.dumps(
        {"created": "2026-10-13T17:31:00", "source_run": "cx-sweep", "files": [], "items": [item]}))
    reply = "Sweep: 1 item. 1 item staged for Review."
else:
    reply = "Plain chat."
out({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}})
out({"type": "result", "result": reply, "session_id": "sess-p"})
'''


class Recogniser(unittest.TestCase):
    """live_server.panel_sweep: the server, never the model, decides from the words."""

    @classmethod
    def setUpClass(cls):
        import live_server
        cls.ls = live_server

    def test_cx_sweep_triggers_are_sweeps(self):
        for m in ("sweep", "Sweep.", "sweep mail", "sweep mail for ABC", "sweep mail for the last 7 days",
                  "sweep the last 7 days", "sweep the UAT plan thread", "refresh calendar", "Refresh the calendar",
                  "please sweep", "sweep now"):
            self.assertTrue(self.ls.panel_sweep(m), m)

    @unittest.skipUnless("check (?:my )?(?:mail" in open(REPO / "system/scripts/live_server.py").read(),
                         "needs dev/proposals/291/live_server.py.diff applied")
    def test_the_plain_words_are_sweeps(self):
        """#291: Today's Check now and the panel chip send these; they are the same as "sweep"."""
        for m in ("check my mail", "check my mail and Teams", "check mail for ABC", "check my mail the last 7 days",
                  "check my mail for the last 7 days", "Check my email.", "check mail for abc", "check my mail for ORX2C"):
            self.assertTrue(self.ls.panel_sweep(m), m)
        for m in ("check my mail and apply", "check my mail then approve", "check email for invoices", "check my mail for urgent",
                  "check my mail for all", "sweep for today", "check the last 7 days"):
            self.assertFalse(self.ls.panel_sweep(m), m)       # an ordinary word is never read as a project code

    def test_anything_more_is_a_plain_chat(self):
        for m in ("sweep and apply", "sweep then approve everything", "sweep, then apply", "sweep; apply", "apply",
                  "sweep mail for ABC and mark ABC-A-003 done", "sweep the budget and apply thread",
                  "sweep the x thread then undo", "what did the sweep find?", "undo last apply", "sweep " + "x" * 130, ""):
            self.assertFalse(self.ls.panel_sweep(m), m)

    def test_an_image_or_a_confirmed_request_is_never_a_sweep(self):
        self.assertFalse(self.ls.panel_sweep("sweep", ["a1b2c3"]))
        self.assertFalse(self.ls.panel_sweep("sweep", (), "Sweep"))

    def test_the_sweep_run_uses_the_sweep_modes_rules(self):
        tools, deny, guarded = self.ls.run_policy("sweep", None)
        self.assertTrue(guarded)
        self.assertEqual(self.ls.guard_mode("sweep", None), "sweep")
        self.assertFalse(any("tracker.py apply" in t or "filechange.py *" in t or "review.py *" in t for t in tools))


class ThroughTheServer(unittest.TestCase):
    """A typed sweep stages under the guarded "sweep" mode; the same run is refused the record; a mixed request is a chat."""

    @classmethod
    def setUpClass(cls):
        from test_live_server import free_port
        cls.v = v = Vault()
        test_dashboard.populate(v)
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
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def ask(self, message):
        req = urllib.request.Request(self.base + "/api/ask", data=json.dumps({"message": message}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read().decode()

    def call(self, message):
        f = self.v.root / "fake-calls.jsonl"
        return [c for c in (json.loads(ln) for ln in f.read_text().splitlines()) if c["prompt"] == message][-1]

    def staged(self):
        return sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*sweep*.json"))

    def snapshot(self):
        return [self.v.rows(t) for t in ("actions", "raid", "decisions")]

    def test_1_a_typed_sweep_stages_under_the_sweep_mode_and_the_record_is_refused(self):
        before, rows = self.staged(), self.snapshot()
        stream = self.ask("sweep")
        self.assertIn("Sweeping (stages proposals only)", stream)
        self.assertIn("1 item staged for Review", stream)
        c = self.call("sweep")
        a = c["args"]
        self.assertIn("--mode sweep", a[a.index("--settings") + 1])                       # BL-295's guarded mode
        allowed = a[a.index("--allowedTools") + 1]
        self.assertIn("sweep.py *", allowed)
        for absent in ("tracker.py apply", "review.py *", "filechange.py *", "Write(system/staging/**)"):
            self.assertNotIn(absent, allowed)
        self.assertIn("BL-309", a[a.index("--append-system-prompt") + 1])
        v = c["verdicts"]
        self.assertEqual((v["stage"], v["map"], v["write_drafts"]), (0, 0, 0))                # it may stage
        for refused in ("apply", "undo", "approve", "reject", "propose_stage", "write_staging", "write_root"):
            self.assertEqual(v[refused], 2, refused)                                          # the record stays Alan's
        self.assertEqual(len(self.staged()), len(before) + 1)
        self.assertEqual(self.snapshot(), rows)                                               # nothing applied
        run = json.loads(self.post_raw("/api/ask/running")).get("run") or {}
        self.assertTrue(run.get("sweep"))
        self.assertEqual(run.get("kind"), "ask")                                              # still a chat, with its history

    def test_2_refresh_calendar_and_a_project_sweep_are_sweeps_too(self):
        for m in ("refresh calendar", "sweep mail for ABC"):
            self.ask(m)
            a = self.call(m)["args"]
            self.assertIn("--mode sweep", a[a.index("--settings") + 1], m)

    def test_3_a_mixed_request_is_a_plain_chat(self):
        before = self.staged()
        stream = self.ask("sweep and apply")
        self.assertNotIn("Sweeping (stages proposals only)", stream)
        c = self.call("sweep and apply")
        a = c["args"]
        self.assertIn("--mode ask", a[a.index("--settings") + 1])
        self.assertNotIn("sweep.py *", a[a.index("--allowedTools") + 1])
        self.assertNotIn("BL-309", a[a.index("--append-system-prompt") + 1])
        v = c["verdicts"]                                                                      # the plain chat's guard
        self.assertEqual((v["apply"], v["approve"], v["propose_stage"], v["map"]), (2, 2, 2, 2))
        self.assertEqual(self.staged(), before)

    def post_raw(self, path):
        req = urllib.request.Request(self.base + path, data=b"{}", method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode()
        except urllib.error.HTTPError as e:
            with e:
                return e.read().decode()


if __name__ == "__main__":
    unittest.main(verbosity=2)
