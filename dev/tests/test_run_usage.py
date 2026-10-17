"""#197 run usage monitor, plain code: usage_log.py appends counts-only lines, usage_report.py sums them. Fixed dates only.

Run: python3 dev/tests/test_run_usage.py
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import usage_log  # noqa: E402
import usage_report  # noqa: E402

RESULT = {"type": "result", "subtype": "success", "result": "SECRET REPLY TEXT about Jane Doe", "num_turns": 3, "duration_ms": 4200,
          "total_cost_usd": 0.0102529, "usage": {"input_tokens": 2, "output_tokens": 40, "cache_read_input_tokens": 649,
                                                  "cache_creation_input_tokens": 2536},
          "modelUsage": {"claude-sonnet-5-5": {"costUSD": 0.01}}}
ASSISTANT = {"type": "assistant", "message": {"usage": {"input_tokens": 2, "cache_read_input_tokens": 649, "cache_creation_input_tokens": 2536}}}


class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        self.file = self.root / "system" / "staging" / "run-usage.jsonl"
        os.environ["CREAITE_NOW"] = "2026-10-12 09:30"

    def tearDown(self):
        os.environ.pop("CREAITE_NOW", None)
        self.t.cleanup()

    def lines(self):
        return [json.loads(x) for x in self.file.read_text().splitlines()]


class UsageLog(Base):
    def test_run_usage_line_has_counts_only(self):
        usage_log.record("ask", RESULT, label="Chat", start_tokens=usage_log.start_tokens_of(ASSISTANT), seconds=4.2, root=self.root)
        (ln,) = self.lines()
        self.assertEqual(ln, {"at": "2026-10-12T09:30:00", "kind": "ask", "label": "Chat", "model": "claude-sonnet-5-5", "seconds": 4.2,
                              "turns": 3, "input": 2, "output": 40, "cache_read": 649, "cache_create": 2536, "cost_usd": 0.010253,
                              "start_tokens": 3187, "stopped": False})

    def test_run_usage_appended_for_each_kind(self):
        for k in usage_log.KINDS:
            usage_log.record(k, RESULT, root=self.root)
        self.assertEqual([x["kind"] for x in self.lines()], list(usage_log.KINDS))

    def test_stopped_run_still_recorded(self):
        usage_log.record("sweep", None, seconds=12, stopped=True, root=self.root)
        (ln,) = self.lines()
        self.assertTrue(ln["stopped"])
        self.assertEqual((ln["input"], ln["cost_usd"], ln["seconds"]), (0, 0.0, 12.0))

    def test_vip_cost_and_tokens_recorded(self):
        vip = {"type": "result", "result": "text", "total_cost_usd": 0.02, "num_turns": 2, "duration_ms": 3000,
               "usage": {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 100, "cache_creation_input_tokens": 0}}
        usage_log.record("vip", vip, root=self.root)
        (ln,) = self.lines()
        self.assertEqual((ln["kind"], ln["input"], ln["cache_read"], ln["cost_usd"], ln["seconds"]), ("vip", 10, 100, 0.02, 3.0))

    def test_no_text_in_the_file(self):
        usage_log.record("ask", RESULT, root=self.root)
        raw = self.file.read_text()
        self.assertNotIn("SECRET", raw)
        self.assertNotIn("Jane", raw)

    def test_not_written_in_the_dev_repo(self):
        (self.root / ".creaite-dev").write_text("")
        self.assertIsNone(usage_log.record("ask", RESULT, root=self.root))
        self.assertFalse(self.file.exists())

    def test_model_of_init_event(self):
        self.assertEqual(usage_log.model_of({"type": "system", "subtype": "init", "model": "claude-sonnet-5-5"}), "claude-sonnet-5-5")


class UsageReport(Base):
    def test_report_sums_by_day_and_kind(self):
        rows = [{"at": "2026-10-12T08:00:00", "kind": "ask", "input": 1, "output": 9, "cache_read": 90, "cache_create": 0, "cost_usd": 0.1, "start_tokens": 40},
                {"at": "2026-10-12T09:00:00", "kind": "ask", "input": 1, "output": 9, "cache_read": 190, "cache_create": 0, "cost_usd": 0.2, "start_tokens": 80},
                {"at": "2026-10-11T09:00:00", "kind": "sweep", "input": 5, "output": 5, "cache_read": 0, "cache_create": 0, "cost_usd": 0.5, "start_tokens": 5},
                {"at": "2026-09-01T09:00:00", "kind": "ask", "input": 1, "output": 1, "cache_read": 0, "cache_create": 0, "cost_usd": 9, "start_tokens": 1}]
        out = usage_report.summarise(rows, days=7)
        self.assertEqual([(s["day"], s["kind"], s["runs"]) for s in out], [("2026-10-12", "ask", 2), ("2026-10-11", "sweep", 1)])
        a = out[0]
        self.assertEqual((a["tokens"], a["avg_tokens"], a["cost_usd"], a["start_min"], a["start_median"], a["start_max"]), (300, 150, 0.3, 40, 60, 80))
        self.assertEqual(a["start_share"], round(120 / 282, 2))


if __name__ == "__main__":
    unittest.main()
