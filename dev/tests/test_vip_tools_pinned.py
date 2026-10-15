"""The VIP check's tool flags are pinned: Microsoft 365 reading tools only, no built-in tool (no Bash, Read, Edit or Write).

The check reads outside content (mail, Teams) with no guard hook, so the vault's .claude/settings.json allow rules (tracker.py,
review.py, propose.py, Edit projects/**) must never apply in it: it is started with `--tools ""` (no built-in tools; the
Microsoft 365 connector's MCP tools stay, so no --strict-mcp-config) and every built-in tool denied by name as well.

Run: python3 dev/tests/test_vip_tools_pinned.py
A throwaway vault with fictional people and a stand-in `claude` (CREAITE_CLAUDE) that records its argv. No real Claude call.
"""
import json
import os
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
from test_live_server import free_port  # noqa: E402
from test_sweep_alerts import vip_vault  # noqa: E402

TOOLS = ["mcp__claude_ai_Microsoft_365__outlook_email_search", "mcp__claude_ai_Microsoft_365__chat_message_search",
         "mcp__claude_ai_Microsoft_365__outlook_calendar_search", "mcp__claude_ai_Microsoft_365__read_resource"]
BUILTIN = ["Bash", "Read", "Grep", "Glob", "Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch", "Task", "Agent"]

FAKE = r'''#!/usr/bin/env python3
import json, sys
from pathlib import Path
here = Path(__file__).parent
n = len(list(here.glob("vip-argv-*.json"))) + 1
(here / f"vip-argv-{n}.json").write_text(json.dumps(sys.argv[1:]))
print(json.dumps({"type": "result", "result": "[]"}))
'''


def flag(args, name):
    """The one value after an option (the command passes each option once)."""
    before = args[:args.index("--")]
    assert before.count(name) == 1, f"{name} appears {before.count(name)} times"
    return before[before.index(name) + 1]


class Pinned(unittest.TestCase):
    def test_the_constants(self):
        import live_server
        self.assertEqual(live_server.VIP_TOOLS, TOOLS)
        self.assertEqual(live_server.VIP_ARGS, ["--tools", ""])
        self.assertNotIn("--strict-mcp-config", live_server.VIP_ARGS)     # it would drop the Microsoft 365 tools
        deny = live_server.vip_deny()
        for t in BUILTIN:
            self.assertIn(t, deny)
        for t in live_server.DENY_TOOLS:
            self.assertIn(t, deny)


class ServerCommand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = vip_vault()
        cfg = v.root / "system/config/settings.json"
        d = json.loads(cfg.read_text())
        d.setdefault("vip", {})["check_minutes"] = 0.02
        cfg.write_text(json.dumps(d, indent=2))
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        port = free_port()
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], cwd=v.root,
                                    env={**os.environ, "CREAITE_PORT": str(port), "CREAITE_CLAUDE": str(fake),
                                         "CREAITE_NOW": "2026-10-08 09:30"},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        f = v.root / "vip-argv-1.json"
        for _ in range(200):
            if f.exists() and f.read_text():
                break
            time.sleep(0.1)
        cls.args = json.loads(f.read_text())

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def test_exactly_one_prompt_after_dashdash(self):
        a = self.args
        self.assertEqual(a.count("--"), 1)
        self.assertEqual(a.index("--"), len(a) - 2)
        self.assertTrue(a[-1].startswith("creaite VIP check."))

    def test_no_built_in_tools(self):
        self.assertEqual(flag(self.args, "--tools"), "")
        self.assertNotIn("--strict-mcp-config", self.args)

    def test_only_the_microsoft_365_reading_tools_are_allowed(self):
        allowed = flag(self.args, "--allowedTools").split(",")
        self.assertEqual(allowed, TOOLS)
        for t in BUILTIN:
            self.assertFalse(any(x == t or x.startswith(t + "(") for x in allowed), t)

    def test_every_built_in_tool_is_denied(self):
        denied = flag(self.args, "--disallowedTools").split(",")
        for t in BUILTIN:
            self.assertIn(t, denied)
        self.assertFalse(set(TOOLS) & set(denied))

    def test_no_extra_dirs_or_permission_skips(self):
        self.assertNotIn("--add-dir", self.args)
        self.assertNotIn("--dangerously-skip-permissions", self.args)
        self.assertNotIn("--permission-mode", self.args)


if __name__ == "__main__":
    unittest.main()
