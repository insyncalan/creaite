"""#371: a run's startup is logged as counts only (MCP servers by status, Microsoft 365 connected or not, its tool count). Skipped
until dev/proposals/371/live_server-371.diff has landed. Run: python3 dev/tests/test_job_init_log_371.py"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import live_server  # noqa: E402

LANDED = hasattr(live_server, "init_summary")
INIT = {"type": "system", "subtype": "init", "mcp_servers": [
    {"name": "claude_ai_Microsoft_365", "status": "connected"}, {"name": "secret-client-server", "status": "failed"},
    {"name": "other", "status": "needs-auth"}],
    "tools": ["Read", "ToolSearch", "mcp__claude_ai_Microsoft_365__outlook_calendar_search",
              "mcp__claude_ai_Microsoft_365__read_resource", "mcp__other__x"]}


@unittest.skipUnless(LANDED, "live_server-371.diff has not landed")
class InitLog(unittest.TestCase):
    def test_counts_only(self):
        line = live_server.init_summary(INIT)
        self.assertIn("connected 1, failed 1, needs-auth 1", line)
        self.assertIn("microsoft365: connected", line)
        self.assertIn("m365 tools: 2 of 5", line)
        for name in ("secret-client-server", "claude_ai", "outlook_calendar_search", "other"):
            self.assertNotIn(name, line)

    def test_absent_and_other_events(self):
        self.assertIn("microsoft365: absent", live_server.init_summary({"subtype": "init"}))
        self.assertIn("m365 tools: 0 of 0", live_server.init_summary({"subtype": "init", "tools": None}))
        self.assertIsNone(live_server.init_summary({"type": "system", "subtype": "other"}))
        self.assertIsNone(live_server.init_summary("x"))

    def test_the_run_logs_one_info_line_and_never_raises(self):
        logged = []

        class Log:
            def info(self, area, msg):
                logged.append((area, msg))

            def debug(self, area, msg):
                pass
        old = live_server.debuglog
        live_server.debuglog = Log()
        try:
            run = live_server.Run.__new__(live_server.Run)
            run.id = "r1"
            run._init_log(INIT)
            run._init_log({"subtype": "init", "mcp_servers": 5})      # malformed: swallowed
        finally:
            live_server.debuglog = old
        self.assertEqual(len(logged), 1)
        self.assertEqual(logged[0][0], "run")
        self.assertTrue(logged[0][1].startswith("r1 start: "))


if __name__ == "__main__":
    unittest.main()
