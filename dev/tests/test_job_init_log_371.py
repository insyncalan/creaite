"""#371: a run's startup is logged as counts only (the MCP servers the init event lists, by status, and its tool count; a
ToolSearch result's Microsoft 365 tool names counted). Probed 26-10-2026 with the real claude binary: a check or load start lists no
MCP server and only ToolSearch, so the line says "listed at start" and never claims the connector is absent. Skipped until
dev/proposals/371/live_server-371.diff has landed. Run: python3 dev/tests/test_job_init_log_371.py"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import live_server  # noqa: E402

LANDED = hasattr(live_server, "init_summary")
INIT = {"type": "system", "subtype": "init", "mcp_servers": [
    {"name": "secret-client-server", "status": "failed"}, {"name": "other", "status": "connected"},
    {"name": "third", "status": "connected"}], "tools": ["Read", "ToolSearch", "mcp__other__x"]}
REAL = {"type": "system", "subtype": "init", "mcp_servers": [], "tools": ["ToolSearch"]}     # what the real binary printed

HARNESS = r'''
import io, json, sys, threading, time
sys.path.insert(0, "system/scripts")
import live_server as L
spec = json.loads(sys.stdin.read())
logged = []
class Log:
    def info(self, a, m): logged.append(m)
    def debug(self, a, m): pass
    def warn(self, a, m): pass
    def error(self, a, m): pass
    def clean(self, t, n=0): return t
L.debuglog = Log()
class Proc:
    def __init__(self, lines):
        self.stdout, self.stderr, self.returncode, self.pid = io.StringIO(lines), io.StringIO(""), None, 0
    def poll(self): return self.returncode
    def wait(self, timeout=None):
        self.returncode = 0
        return 0
    def terminate(self): self.returncode = 0
    kill = terminate
run = L.Run.__new__(L.Run)
attrs = {"id": "r-1", "message": "m", "session": None, "chat": None, "confirmed": False, "kind": "ask", "images": [],
         "job": None, "label": "m", "tooluse": {}, "events": [], "cond": threading.Condition(), "watchers": 0,
         "pending": {}, "said": [], "steps": [], "stop": False, "deferred": False, "done": False, "seen": False,
         "started": time.time(), "guarded": False}
for k, v in attrs.items():
    setattr(run, k, v)
run.proc = Proc("".join(json.dumps(e) + "\n" for e in spec["events"]))
L.Run.read(run)
print(json.dumps(logged))
'''


@unittest.skipUnless(LANDED, "live_server-371.diff has not landed")
class InitLog(unittest.TestCase):
    def test_counts_only(self):
        line = live_server.init_summary(INIT)
        self.assertIn("listed at start: connected 2, failed 1", line)
        self.assertIn("tools at start: 3", line)
        for name in ("secret-client-server", "other", "third", "Microsoft", "Read"):
            self.assertNotIn(name, line)

    def test_the_real_start_does_not_claim_the_connector_is_absent(self):
        line = live_server.init_summary(REAL)
        self.assertIn("listed at start: none", line)
        self.assertIn("tools at start: 1", line)
        self.assertNotIn("absent", line)
        self.assertNotIn("microsoft365", line)

    def test_other_events_and_malformed_ones(self):
        self.assertIsNone(live_server.init_summary({"type": "system", "subtype": "other"}))
        self.assertIsNone(live_server.init_summary("x"))
        self.assertIn("tools at start: 0", live_server.init_summary({"subtype": "init", "tools": None}))
        self.assertIn("listed at start: unknown 1", live_server.init_summary({"subtype": "init", "mcp_servers": ["x"]}))

    def test_tool_search_names_counted(self):
        m = "mcp__claude_ai_Microsoft_365__"
        text = f"{m}outlook_calendar_search {m}read_resource {m}read_resource mcp__x__y"
        self.assertEqual(live_server.m365_names_seen(text), 2)
        self.assertEqual(live_server.m365_names_seen(None), 0)

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
        self.assertTrue(logged[0][1].startswith("r1 start: "))

    def test_a_tool_search_result_logs_its_count_only(self):         # the emission in job_observe
        logged = []

        class Log:
            def info(self, area, msg):
                logged.append((area, msg))

            def debug(self, area, msg):
                pass

        class Job:
            def observe(self, *a):
                pass
        m = "mcp__claude_ai_Microsoft_365__"
        old = live_server.debuglog
        live_server.debuglog = Log()
        try:
            run = live_server.Run.__new__(live_server.Run)
            run.id, run.kind, run.job = "r1", "load", Job()
            run.tooluse = {"t1": ("ToolSearch", {"query": "secret title"}), "t2": ("Bash", {})}
            body = f"secret title {m}outlook_calendar_search {m}read_resource"
            run.job_observe({"tool_use_id": "t1", "content": body})
            run.job_observe({"tool_use_id": "t2", "content": body})       # another tool: no tool-search line
        finally:
            live_server.debuglog = old
        lines = [m_ for _, m_ in logged if "tool search" in m_]
        self.assertEqual(lines, ["r1 load tool search: 2 Microsoft 365 tool names in the result"])
        self.assertFalse(any("secret" in m_ or "outlook_calendar" in m_ for _, m_ in logged))

    def test_run_read_calls_it_for_the_init_event_only(self):        # M7: the call inside Run.read
        from test_tracker import Vault
        v = Vault()
        try:
            v.run("init")
            events = [INIT, {"type": "system", "subtype": "other"}, {"type": "result", "session_id": "s", "result": "ok",
                                                                    "permission_denials": []}]
            r = subprocess.run([sys.executable, "-c", HARNESS], input=json.dumps({"events": events}), cwd=v.root,
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = json.loads(r.stdout.strip().splitlines()[-1])
            starts = [x for x in lines if " start: " in x]
            self.assertEqual(len(starts), 1, lines)
            self.assertIn("mcp servers listed at start: connected 2, failed 1", starts[0])
        finally:
            v.cleanup()


if __name__ == "__main__":
    unittest.main()
