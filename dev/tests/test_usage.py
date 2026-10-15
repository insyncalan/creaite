"""Tests for dev/tools/usage.py (BL-343): dedupe, roles, prices and the digest summary.

Run: python3 dev/tests/test_usage.py
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import usage  # noqa: E402

DAY = "2026-10-15"
TS = DAY + "T12:00:00"  # no zone: read as local time, so the day never shifts


def assistant(msg_id, model="claude-opus-5-5", inp=0, cw=0, cr=0, out=0, sidechain=False, ts=TS):
    """One assistant log record."""
    return {"type": "assistant", "isSidechain": sidechain, "timestamp": ts,
            "message": {"id": msg_id, "model": model, "role": "assistant",
                        "usage": {"input_tokens": inp, "cache_creation_input_tokens": cw,
                                  "cache_read_input_tokens": cr, "output_tokens": out}}}


def prompt(text):
    """One typed user prompt record."""
    return {"type": "user", "timestamp": TS, "message": {"role": "user", "content": text}}


class UsageCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.proj = self.root / "-home-dev-creaite"
        self.proj.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, records):
        path = self.proj / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r) + "\n" for r in records) + "{torn line\n")

    def run_cli(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            usage.main(["--root", str(self.root), "--laptop", "laptop-1", "--day", DAY, *args])
        return buf.getvalue()

    def report(self, *args):
        return json.loads(self.run_cli("--json", *args))

    def test_dedupe_keeps_one_message(self):
        # streamed blocks repeat the id; the fuller usage wins
        self.write("aaaa1111.jsonl", [assistant("m1", inp=10, out=5), assistant("m1", inp=10, out=50),
                                      assistant("m2", inp=1, out=1)])
        rows = self.report()["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["input"], rows[0]["output"]), (11, 51))

    def test_roles(self):
        self.write("lead0001.jsonl", [prompt("You are the lead; Jarvis, the Head of Product, decides."),
                                      assistant("a", out=1_000_000)])
        self.write("jarv0001.jsonl", [prompt("You are Jarvis, running the board."), assistant("b", out=1_000_000)])
        self.write("name0001.jsonl", [{"type": "agent-name", "agentName": "Head of Product"},
                                      assistant("c", out=1_000_000)])
        self.write("lead0001/subagents/agent-abc123.jsonl", [assistant("d", out=1_000_000, sidechain=True)])
        by_role = {}
        for r in self.report()["rows"]:
            by_role[r["role"]] = by_role.get(r["role"], 0) + r["output"]
        self.assertEqual(by_role, {"lead": 1_000_000, "Jarvis": 2_000_000, "agent": 1_000_000})
        forced = {r["role"] for r in self.report("--role", "lead0001=Jarvis", "--role", "jarv=lead")["rows"]}
        self.assertEqual(forced, {"Jarvis", "lead", "agent"})
        sessions = {s["session"] for s in self.report()["sessions"]}
        self.assertTrue(all(len(s) <= usage.SHORT for s in sessions))

    def test_prices(self):
        m = 1_000_000
        self.assertAlmostEqual(usage.cost("claude-opus-5-5", {"input": m, "output": m}), 24.0)
        self.assertAlmostEqual(usage.cost("claude-opus-5-5", {"cache_write": m, "cache_read": m}), 5.0 + 0.2)
        self.assertAlmostEqual(usage.cost("claude-sonnet-5-5", {"input": m, "cache_write": m, "cache_read": m,
                                                                "output": m}), 2 + 2.5 + 0.2 + 10)
        self.assertAlmostEqual(usage.cost("claude-haiku-5-5", {"input": m, "cache_read": m, "output": m}),
                               0.10 + 0.01 + 0.50)
        self.assertEqual(usage.cost("other-model", {"output": m}), 0.0)

    def test_day_range_and_synthetic(self):
        self.write("aaaa2222.jsonl", [assistant("x", out=1, ts="2026-10-14T12:00:00"),
                                      assistant("y", out=2), assistant("z", model="<synthetic>", out=9)])
        self.assertEqual(sum(r["output"] for r in self.report()["rows"]), 2)
        self.assertEqual(sum(r["output"] for r in self.report("--since", "2026-10-14")["rows"]), 3)

    def test_summary(self):
        self.write("lead0002.jsonl", [assistant("a", model="claude-opus-5-5", cr=10_000_000, out=50_000)])
        self.write("lead0002/subagents/agent-def456.jsonl", [assistant("b", model="claude-sonnet-5-5", out=50_000)])
        lines = self.run_cli("--summary").strip().splitlines()
        self.assertEqual(len(lines), 4)
        self.assertIn("$3.50 total", lines[0])  # 10M cache reads $2 + 50k Opus output $1 + 50k Sonnet output $0.50
        self.assertIn("laptop-1", lines[0])
        self.assertTrue(lines[1].startswith("By role: lead $3.00, agent $0.50"))
        self.assertIn("claude-opus-5-5 $3.00", lines[2])
        self.assertTrue(lines[3].startswith("Top driver: cache reads (57% of cost); biggest session lead lead0002"))

    def test_empty_and_table(self):
        self.assertEqual(len(self.run_cli("--summary").strip().splitlines()), 1)
        self.write("aaaa3333.jsonl", [assistant("q", model="mystery", out=5)])
        out = self.run_cli()
        self.assertIn("model not in the price table", out)


if __name__ == "__main__":
    unittest.main()
