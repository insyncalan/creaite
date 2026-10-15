"""Search's answer (kind "search") is pinned to the three reading built-ins: no Bash, no writer, no web, no delegation.

The answer run has no guard hook (#60: like ask creaite), so the vault's .claude/settings.json allow rules (tracker.py, review.py,
propose.py, filechange.py, Edit projects/**, Edit system/config/settings.json) must never apply in it: it is started with
`--tools "Read,Grep,Glob"` and every tool that runs, writes, delegates or reaches the web denied by name as well. It still reads
the vault (Read, Grep, Glob) and keeps the Microsoft 365 reading tools it had.

Run: python3 dev/tests/test_search_tools_pinned.py
A throwaway vault and a stand-in `claude` (CREAITE_CLAUDE) that records its argv. No real Claude call.
"""
import json
import os
import re
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
from test_dashboard import populate  # noqa: E402
from test_live_server import free_port  # noqa: E402
from test_search import put  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402

READERS = ["Read", "Grep", "Glob"]
NEVER = ["Bash", "Write", "Edit", "MultiEdit", "NotebookEdit", "WebFetch", "WebSearch", "Task", "Agent", "Skill"]
VAULT_ALLOWS = ["tracker.py", "review.py", "propose.py", "filechange.py", "sweep.py", "Edit(", "Write("]

FAKE = r'''#!/usr/bin/env python3
import json, sys
from pathlib import Path
(Path(__file__).parent / "search-argv.json").write_text(json.dumps(sys.argv[1:]))
print(json.dumps({"type": "system", "subtype": "init", "session_id": "sess-pin"}), flush=True)
print(json.dumps({"type": "result", "result": "The vault doesn't say.", "session_id": "sess-pin"}), flush=True)
'''


def flag(args, name):
    """The one value after an option (each is passed once, before `--`)."""
    before = args[:args.index("--")]
    assert before.count(name) == 1, f"{name} appears {before.count(name)} times"
    return before[before.index(name) + 1]


class Policy(unittest.TestCase):
    def test_the_constants(self):
        import live_server as L
        import permissions
        tools, deny, guarded = L.run_policy("search", None)
        self.assertFalse(guarded)
        self.assertEqual(tools, READERS + permissions.m365_read_tools())
        for t in NEVER:
            self.assertIn(t, deny)
        for t in L.DENY_TOOLS:                                         # Microsoft 365 actions and the rest, as before
            self.assertIn(t, deny)
        self.assertEqual(L.KIND_ARGS["search"], ["--tools", "Read,Grep,Glob"])
        self.assertFalse(any(t.startswith(("Bash", "Write", "Edit")) for t in tools))
        self.assertFalse(L.held_run("search", None, None, False, tools))   # #60: like ask creaite, confidential notes unchanged

    def test_other_kinds_unchanged(self):
        import live_server as L
        self.assertEqual(L.run_policy("ask", None)[0][:4], ["Read", "Grep", "Glob", "Skill"])
        self.assertNotIn("Bash", L.run_policy("prep", None)[1])
        self.assertNotIn("prep", L.KIND_ARGS)


class ServerCommand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        put(v, f"{ABC}/minutes/2026-09-25 Steering.md", "# Decisions\nGo-live moves because data access slipped.")
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        port = free_port()
        base = f"http://127.0.0.1:{port}"
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], cwd=v.root,
                                    env={**os.environ, "CREAITE_PORT": str(port), "CREAITE_CLAUDE": str(fake)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(base + "/").read().decode()
        token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
        req = urllib.request.Request(base + "/api/search/ask", data=json.dumps({"q": "why did go-live move?"}).encode(),
                                     method="POST", headers={"Content-Type": "application/json", "X-Creaite-Token": token})
        with urllib.request.urlopen(req, timeout=60) as r:
            r.read()
        cls.args = json.loads((v.root / "search-argv.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def test_only_the_reading_built_ins(self):
        self.assertEqual(flag(self.args, "--tools"), "Read,Grep,Glob")
        self.assertNotIn("--strict-mcp-config", self.args)           # the Microsoft 365 reading tools stay

    def test_allowed_has_no_command_or_writer(self):
        allowed = flag(self.args, "--allowedTools").split(",")
        self.assertEqual(allowed[:3], READERS)
        self.assertTrue(all(t in READERS or t.startswith("mcp__claude_ai_Microsoft_365__") for t in allowed), allowed)
        for t in VAULT_ALLOWS:
            self.assertFalse(any(t in x for x in allowed), t)

    def test_every_runner_writer_and_web_tool_is_denied(self):
        denied = flag(self.args, "--disallowedTools").split(",")
        for t in NEVER:
            self.assertIn(t, denied)
        self.assertFalse(set(READERS) & set(denied))

    def test_no_guard_hook_and_no_permission_skips(self):
        self.assertNotIn("--settings", self.args)                     # #60: Search's answer is like ask creaite
        self.assertNotIn("--dangerously-skip-permissions", self.args)
        self.assertNotIn("--permission-mode", self.args)
        self.assertEqual(self.args.count("--"), 1)
        self.assertEqual(self.args.index("--"), len(self.args) - 2)


if __name__ == "__main__":
    unittest.main()
