"""#238: the live-server wiring proposal (dev/proposals/usage-monitor/live_server.diff) applied to a throwaway vault's own copy of
live_server.py (never committed): the daily job records what every run loads, once a day, counts only; nothing is recorded in the
development repository; the route is read only. Quick tier: no Chrome.

Run: python3 dev/tests/test_usage_wiring.py
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault  # noqa: E402

PROPOSAL = Path(__file__).resolve().parents[1] / "proposals" / "usage-monitor" / "live_server.diff"
CALL = """
import sys, json
sys.path.insert(0, {scripts!r})
import live_server
print(json.dumps({{"job": live_server.backup_daily_job(), "again": live_server.usage_context_job()}}))
"""


class Wiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.addClassCleanup(cls.v.cleanup)
        cls.target = cls.v.root / "system" / "scripts" / "live_server.py"
        r = subprocess.run(["patch", "--no-backup-if-mismatch", "-p0", str(cls.target), str(PROPOSAL)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        cls.file = cls.v.root / "system" / "staging" / "context-size.jsonl"

    def run_job(self):
        r = subprocess.run([sys.executable, "-c", CALL.format(scripts=str(self.v.root / "system" / "scripts"))], capture_output=True,
                           text=True, cwd=str(self.v.root), env={**__import__("os").environ, "CREAITE_NOW": "2026-10-19 09:00"})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_the_daily_job_records_the_four_files_once_and_only_counts(self):
        out = self.run_job()
        self.assertIn("context sizes recorded: 4 files", out["job"])
        self.assertIsNone(out["again"])                                   # the same day: nothing more
        rows = [json.loads(x) for x in self.file.read_text().splitlines()]
        self.assertEqual([r["file"] for r in rows], ["rules", "claude_md", "memory", "skills"])
        self.assertEqual({tuple(sorted(r)) for r in rows}, {("bytes", "date", "file", "tokens")})
        self.assertGreater(rows[0]["bytes"], 1000)                       # the rules file is read for its size, never kept

    def test_nothing_is_recorded_in_the_development_repository(self):
        (self.v.root / ".creaite-dev").write_text("")
        self.file.unlink(missing_ok=True)
        self.addCleanup((self.v.root / ".creaite-dev").unlink)
        out = self.run_job()
        self.assertEqual(out["job"], ["skipped: the development repository"])
        self.assertFalse(self.file.exists())

    def test_the_route_is_read_only_and_get(self):
        src = self.target.read_text()
        self.assertIn('"/api/usage": self.usage_get', src)
        self.assertNotIn('"/api/usage"', src.split("def do_POST")[1].split("\n    def ")[0])     # not a POST route


if __name__ == "__main__":
    unittest.main()
