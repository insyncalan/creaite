"""BL-106: the live server's Generate options, the check route and the rewrite route.

Run: python3 dev/tests/test_status_live.py
Starts the real live server in a throwaway vault with fictional data. Claude is a stand-in (CREAITE_CLAUDE) that writes the
prompt it was given to a file and prints a fixed reply, so no real call is made and the prompt can be checked.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import populate  # noqa: E402
from test_live_server import free_port  # noqa: E402
from test_tracker import Vault  # noqa: E402

FAKE = r'''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
message = args[args.index("--") + 1]
open(__file__ + ".prompt", "w", encoding="utf-8").write(message)
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-x"})
reply = "**On track for 20-11-2026.**\n\n- **Ask.** We need Jane Doe by 16-10-2026." if message.startswith("Rewrite") \
    else "**At risk: UAT data is late.**\n\nSOURCES:\n- ABC-003"
out({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}})
out({"type": "result", "result": reply, "session_id": "sess-x"})
'''


class ExecLive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        cls.fake = v.root / "fake_claude.py"
        cls.fake.write_text(FAKE)
        cls.fake.chmod(0o755)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        env = {**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": str(cls.fake), "CREAITE_NOW": "2026-10-09 13:00"}
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
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

    def post(self, path, body, token=None):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": token or self.token})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read().decode()
                return r.status, (json.loads(raw) if r.headers.get_content_type() == "application/json" else raw)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def stream(self, path, body):
        """POST a streaming route; the events, and the prompt Claude was given."""
        st, raw = self.post(path, body)
        self.assertEqual(st, 200, raw)
        events = [json.loads(ln[6:]) for ln in raw.splitlines() if ln.startswith("data: ")]
        self.post("/api/ask/ack", {"run": body["run"]})
        return events, Path(str(self.fake) + ".prompt").read_text(encoding="utf-8")

    GEN = {"code": "ABC", "from": "2026-10-01", "to": "2026-10-09", "sources": ["tracker", "minutes"]}

    # ── generate ──
    def test_generate_defaults_to_internal_and_standard(self):
        events, prompt = self.stream("/api/current/generate", {**self.GEN, "run": "gen-def-1"})
        self.assertTrue(any(e["type"] == "text" and "UAT data is late" in e["text"] for e in events))
        self.assertIn("Audience: internal.", prompt)
        self.assertIn("Length: Standard, about 150 words.", prompt)
        self.assertIn("## Writing guide (follow it)", prompt)
        self.assertIn("Data access delayed", prompt)
        self.assertIn("Draft the Current state for ABC Example Programme, covering 01-10-2026 to 09-10-2026", prompt)

    def test_generate_client_short_holds_nothing_internal(self):
        events, prompt = self.stream("/api/current/generate", {**self.GEN, "audience": "client", "length": "short", "run": "gen-cli-1"})
        self.assertIn("Audience: client-safe.", prompt)
        self.assertIn("Length: Short, about 40 words.", prompt)
        self.assertNotIn("Data access delayed", prompt)                           # internal items
        self.assertNotIn("Escalate data access", prompt)
        self.assertNotIn("Book UAT environment", prompt)

    def test_generate_refuses_a_bad_audience_or_length(self):
        for bad in ({"audience": "press"}, {"length": "huge"}, {"audience": 3}):
            st, r = self.post("/api/current/generate", {**self.GEN, **bad})
            self.assertEqual(st, 400, bad)
            self.assertFalse(r["ok"])

    # ── check ──
    DRAFT = "**Progress is good overall.**\n\n- ABC-A-001 is overdue.\n"

    def test_check_gives_notes_and_the_facts(self):
        st, r = self.post("/api/current/check", {"code": "ABC", "text": self.DRAFT, "sources": "- ABC-A-001\n- ABC-A-099\n",
                                                 "from": "2026-10-01", "to": "2026-10-09"})
        self.assertEqual(st, 200)
        ids = {n["id"] for n in r["notes"]}
        self.assertTrue({"position", "ids", "sources"} <= ids, ids)
        self.assertIn("## Position", r["facts"])
        self.assertIn("ABC-003", r["sources"])
        self.assertNotIn("kept", ids)                                          # no original: no comparison

    def test_check_with_the_original_notes_a_lost_figure(self):
        st, r = self.post("/api/current/check", {"code": "ABC", "text": "**On track.** Go-live is on 27-11-2026.",
                                                 "original": "Go-live is on 20-11-2026.", "audience": "client", "length": "short"})
        self.assertEqual(st, 200)
        notes = {n["id"]: n["note"] for n in r["notes"]}
        self.assertIn("20-11-2026", notes["kept"])
        self.assertIn("27-11-2026", notes["added"])
        self.assertNotIn("Data access delayed", r["facts"])                           # the client sheet

    def test_check_and_rewrite_refuse_bad_input(self):
        for path in ("/api/current/check", "/api/current/rewrite"):
            for body in ({"code": "abc", "text": "x"}, {"code": "ABC", "text": ""}, {"code": "ABC", "text": "x", "audience": "press"},
                         {"code": "ABC", "text": "x", "length": "huge"}, {"code": "ABC", "text": "x", "from": "01-10-2026"},
                         {"code": "ABC", "text": ["x"]}, {"code": "ABC", "text": "x" * 60001}):
                self.assertEqual(self.post(path, body)[0], 400, (path, str(body)[:60]))

    def test_the_new_routes_need_the_token(self):
        for path in ("/api/current/check", "/api/current/rewrite"):
            self.assertEqual(self.post(path, {"code": "ABC", "text": "x"}, token="nope")[0], 403)

    # ── rewrite ──
    def test_rewrite_streams_a_draft_and_the_prompt_carries_the_text_the_guide_and_the_facts(self):
        events, prompt = self.stream("/api/current/rewrite", {
            "code": "ABC", "text": "Sara said go-live is 20-11-2026 and Jane owes the data by 16-10-2026.", "audience": "internal",
            "length": "short", "from": "2026-10-01", "to": "2026-10-09", "run": "rew-1"})
        self.assertTrue(any(e["type"] == "text" and e["text"].startswith("**On track for 20-11-2026.**") for e in events), events)
        for need in ("Sara said go-live is 20-11-2026 and Jane owes the data by 16-10-2026.", "# The executive voice", "## Position",
                     "Length: Short, about 40 words.", "Keep every fact Alan wrote"):
            self.assertIn(need, prompt)

    def test_a_client_rewrite_is_given_only_client_facts(self):
        events, prompt = self.stream("/api/current/rewrite", {"code": "ABC", "text": "Go-live is 20-11-2026.", "audience": "client",
                                                              "run": "rew-2"})
        self.assertIn("Audience: client-safe.", prompt)
        self.assertNotIn("Data access delayed", prompt)


if __name__ == "__main__":
    unittest.main()
