"""#339 A0 and #338 N1, N2: start_tokens_report.py, dev/tools/compare_start_tokens.py and dev/tools/size_report.py on synthetic data.

Run: python3 dev/tests/test_start_tokens_report.py
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system" / "scripts"))
sys.path.insert(0, str(ROOT / "dev" / "tools"))
import compare_start_tokens as cmp  # noqa: E402
import size_report  # noqa: E402
import start_tokens_report as st  # noqa: E402

TODAY = date(2026, 10, 24)


def row(day, kind, start, **more):
    return dict({"at": f"2026-10-{day:02d}T09:00:00", "kind": kind, "start_tokens": start, "label": "SECRET TEXT"}, **more)


class Percentiles(unittest.TestCase):
    def test_nearest_rank(self):
        self.assertEqual(st.percentile([10, 20, 30, 40, 50, 60, 70, 80, 90, 100], 90), 90)
        self.assertEqual(st.percentile([5], 90), 5)
        self.assertEqual(st.percentile([], 90), 0)

    def test_baseline_constants(self):
        self.assertEqual((st.BASELINE_ASK_START_MIN, st.BASELINE_ASK_START_MAX), (366_000, 503_000))
        self.assertEqual((st.BASELINE_SWEEP_FLOOR_TOKENS, st.BASELINE_SWEEP_FLOOR_USD), (60_000, 1.50))


class Report(unittest.TestCase):
    def test_per_kind_median_and_p90(self):
        rows = [row(20, "ask", v) for v in (100, 200, 300, 400, 1000)] + [row(21, "sweep", 60)]
        k = {x["kind"]: x for x in st.summarise(rows)}
        self.assertEqual((k["ask"]["n"], k["ask"]["median"], k["ask"]["p90"]), (5, 300, 1000))
        self.assertEqual((k["sweep"]["n"], k["sweep"]["median"]), (1, 60))

    def test_stopped_and_odd_runs_left_out(self):
        rows = [row(20, "ask", 0), row(20, "ask", "x"), row(20, "ask", -5), row(20, "ask", True), row(20, "ask", 500)]
        self.assertEqual(st.summarise(rows)[0]["n"], 1)

    def test_resumed_split_only_where_the_field_exists(self):
        rows = [row(20, "ask", 900, resumed=True), row(20, "ask", 100, resumed=False), row(20, "ask", 120, resumed=False),
                row(20, "sweep", 60)]
        out = st.summarise(rows)
        ask = [(x["resumed"], x["n"], x["median"]) for x in out if x["kind"] == "ask"]
        self.assertEqual(ask, [(None, 3, 120), (True, 1, 900), (False, 2, 110)])
        self.assertEqual([x for x in out if x["kind"] == "sweep"][0]["resumed"], None)
        self.assertEqual(len([x for x in out if x["kind"] == "sweep"]), 1)

    def test_window_days(self):
        rows = [row(10, "ask", 1), row(18, "ask", 2), row(24, "ask", 3)]
        self.assertEqual(len(st.window(rows, 7, TODAY)), 2)
        self.assertEqual(len(st.window(rows, 1, TODAY)), 1)

    def test_table_and_json_hold_no_text(self):
        rep = st.report([row(24, "ask", 400_000, resumed=True)], 7, TODAY)
        text = st.table(rep) + json.dumps(rep)
        self.assertNotIn("SECRET", text)
        self.assertIn("2.6.3 baseline", text)
        self.assertIn("400000", text)

    def test_empty(self):
        self.assertEqual(st.report([], 7, TODAY)["kinds"], [])


class Compare(unittest.TestCase):
    def test_change_and_low_n(self):
        before = [row(1, "ask", 400)] * 6
        after = [row(2, "ask", 300)] * 6 + [row(2, "sweep", 50)]
        out = {r["kind"]: r for r in cmp.compare(before, after)}
        self.assertEqual(out["ask"]["median_change_pct"], -25)
        self.assertFalse(out["ask"]["low_n"])
        self.assertTrue(out["sweep"]["low_n"])
        self.assertIsNone(out["sweep"]["median_change_pct"])

    def test_change_pct_edges(self):
        self.assertIsNone(cmp.change_pct(0, 10))
        self.assertIsNone(cmp.change_pct(None, 10))
        self.assertEqual(cmp.change_pct(100, 150), 50)

    def test_files_and_windows(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "u.jsonl"
            f.write_text("\n".join(json.dumps(r) for r in [row(1, "ask", 400), row(20, "ask", 200)]) + "\nnot json\n")
            every = cmp.read(f)
            self.assertEqual(len(every), 2)
            a, b = cmp.between(every, "2026-10-01", "2026-10-05"), cmp.between(every, "2026-10-15", "2026-10-24")
            self.assertEqual(cmp.compare(a, b)[0]["median_change_pct"], -50)
            self.assertIn("-50%", cmp.table(cmp.compare(a, b)))
            self.assertIn("low n", cmp.table(cmp.compare(a, b)))


class Sizes(unittest.TestCase):
    def test_sizes_in_a_scratch_tree(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "system" / "templates").mkdir(parents=True)
            (root / ".claude" / "skills" / "cx-demo").mkdir(parents=True)
            (root / "CLAUDE.md").write_text("a" * 40)
            (root / "system" / "creaite-rules.md").write_text("b" * 401)
            (root / ".claude" / "skills" / "cx-demo" / "SKILL.md").write_text("c" * 8)
            rows = {r["group"]: r for r in size_report.measure(root)}
            self.assertEqual((rows["claude_md"]["bytes"], rows["claude_md"]["tokens"]), (40, 10))
            self.assertEqual(rows["rules"]["tokens"], 101)
            self.assertEqual(rows["skill"]["tokens"], 2)
            self.assertNotIn("memory", rows)

    def test_real_tree_has_rules_and_skills(self):
        groups = {r["group"] for r in size_report.measure(ROOT)}
        self.assertTrue({"rules", "skill"} <= groups)


if __name__ == "__main__":
    os.environ.pop("CREAITE_NOW", None)
    unittest.main()
