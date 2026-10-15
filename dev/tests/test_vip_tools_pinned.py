"""The VIP check's tool flags are pinned: Microsoft 365 reading tools only, no built-in tool but ToolSearch (no Bash, Read, Edit or Write).

The check reads outside content (mail, Teams) with no guard hook, so the vault's .claude/settings.json allow rules (tracker.py,
review.py, propose.py, Edit projects/**) must never apply in it: it is started with no `--tools` flag (#116: `--tools ""` reached
no Microsoft 365 tool on laptop 1) and every built-in tool but ToolSearch denied by name (a deny beats an allow rule). ToolSearch
stays: it only loads the deferred Microsoft 365 tools' schemas. No --strict-mcp-config (it would drop the Microsoft 365 tools).
The other connectors (permissions.run_deny_extras(): Todoist, Docs, Slides, Linear, vscode, whole server) are denied by name too
(#116 review M1), on the real command line.

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
# The built-in tools of Claude Code 2.1.300 with no --tools (`claude -p --output-format stream-json --verbose "hi"`: the init
# event's "tools", the mcp__ ones left out). REFRESH this copy, and permissions.KNOWN_BUILTINS, when Claude Code adds one: a new
# built-in must be denied in the VIP check or named in ALLOWED_BUILTINS with a reason.
CLI_DEFAULT_BUILTINS_2_1_300 = [
    "Task", "Artifact", "ArtifactComments", "ArtifactData", "Bash", "CronCreate", "CronDelete", "CronList", "DesignSync", "Edit",
    "EnterWorktree", "ExitWorktree", "ListAgents", "ListMcpResourcesTool", "Monitor", "NotebookEdit", "PushNotification", "Read",
    "ReadMcpResourceDirTool", "ReadMcpResourceTool", "RemoteTrigger", "ReportFindings", "ScheduleWakeup", "SendMessage", "Skill",
    "TaskStop", "ToolSearch", "WebFetch", "WebSearch", "Workflow", "Write"]
OTHER_VERSIONS_BUILTINS = ["Grep", "Glob", "LS", "MultiEdit", "Agent"]
ALLOWED_BUILTINS = {"ToolSearch"}       # loads deferred tools' schemas so they can be called; reads, runs and writes nothing

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
        self.assertFalse(hasattr(live_server, "VIP_ARGS"))                # #116: no --tools flag at all
        deny = live_server.vip_deny()
        for t in BUILTIN:
            self.assertIn(t, deny)
        for t in live_server.DENY_TOOLS:
            self.assertIn(t, deny)
        self.assertNotIn("ToolSearch", deny)
        self.assertEqual(len(deny), len(set(deny)))                       # once each

    def test_run_deny_extras_are_in_vip_deny(self):
        import live_server
        import permissions
        deny = live_server.vip_deny()
        for t in permissions.run_deny_extras():                           # #116 review M1: other connectors, acting built-ins
            self.assertIn(t, deny)
        for server in permissions.NON_M365_MCP_DENY:
            self.assertFalse(server.startswith("mcp__claude_ai_Microsoft_365"), server)

    def test_every_cli_built_in_is_denied_or_explicitly_allowed(self):
        import live_server
        deny = set(live_server.vip_deny())
        for t in CLI_DEFAULT_BUILTINS_2_1_300 + OTHER_VERSIONS_BUILTINS:
            self.assertTrue(t in deny or t in ALLOWED_BUILTINS, f"{t}: neither denied in the VIP check nor allowed")
            self.assertFalse(t in deny and t in ALLOWED_BUILTINS, t)
        self.assertEqual(set(live_server.VIP_BUILTIN_ALLOWED), ALLOWED_BUILTINS)
        self.assertTrue(set(CLI_DEFAULT_BUILTINS_2_1_300 + OTHER_VERSIONS_BUILTINS) <= set(live_server.KNOWN_BUILTINS))


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

    def test_no_tools_flag(self):
        self.assertNotIn("--tools", self.args[:self.args.index("--")])     # #116: `--tools ""` hid the Microsoft 365 tools
        self.assertNotIn("--strict-mcp-config", self.args)

    def test_only_the_microsoft_365_reading_tools_are_allowed(self):
        allowed = flag(self.args, "--allowedTools").split(",")
        self.assertEqual(allowed, TOOLS)
        for t in BUILTIN:
            self.assertFalse(any(x == t or x.startswith(t + "(") for x in allowed), t)

    def test_every_built_in_tool_is_denied(self):
        denied = flag(self.args, "--disallowedTools").split(",")
        for t in CLI_DEFAULT_BUILTINS_2_1_300 + OTHER_VERSIONS_BUILTINS:
            self.assertTrue(t in denied or t in ALLOWED_BUILTINS, t)
        self.assertNotIn("ToolSearch", denied)
        self.assertFalse(set(TOOLS) & set(denied))

    def test_run_deny_extras_reach_the_real_command_line(self):
        import permissions
        denied = flag(self.args, "--disallowedTools").split(",")
        for t in permissions.run_deny_extras():                           # #116 review M1: Todoist, Docs, Slides, Linear, vscode
            self.assertIn(t, denied)
        for t in ("mcp__claude_ai_Todoist", "mcp__claude_ai_Claude_Docs", "mcp__claude_ai_Slides_AI", "mcp__claude_ai_Linear",
                  "mcp__claude-vscode", "Task", "Agent"):
            self.assertIn(t, denied)

    def test_no_extra_dirs_or_permission_skips(self):
        self.assertNotIn("--add-dir", self.args)
        self.assertNotIn("--dangerously-skip-permissions", self.args)
        self.assertNotIn("--permission-mode", self.args)


if __name__ == "__main__":
    unittest.main()
