"""#334: the weekly budget for creaite's own AI runs (ai_budget.py): the week boundary, 80% and 100%, what is never held, and that no
text is read or kept. Plain code, no network, no live server (the server's side is test_ai_budget_gate_334.py).

Run: python3 dev/tests/test_ai_budget.py
"""
import json
import sys
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system/scripts"))
import ai_budget  # noqa: E402
import settings_catalogue  # noqa: E402

WED = datetime(2026, 10, 21, 12, 0)           # a Wednesday; its week is 19-10-2026 to 25-10-2026


def row(at, cost=1.0, **kw):
    return dict({"at": at, "kind": "ask", "label": "SECRET-LABEL", "cost_usd": cost, "input": 10, "output": 5,
                 "cache_read": 100, "cache_create": 20}, **kw)


class Week(unittest.TestCase):
    def test_the_week_runs_monday_to_sunday(self):
        first, last, nxt = ai_budget.week_of(WED)
        self.assertEqual((first.isoformat(), last.isoformat(), nxt.isoformat()), ("2026-10-19", "2026-10-25", "2026-10-26"))
        self.assertEqual(ai_budget.week_of(datetime(2026, 10, 19, 0, 0))[0].isoformat(), "2026-10-19")      # Monday 00:00 is in
        self.assertEqual(ai_budget.week_of(datetime(2026, 10, 25, 23, 59))[0].isoformat(), "2026-10-19")    # Sunday night too
        self.assertEqual(ai_budget.week_of(datetime(2026, 10, 26, 0, 0))[0].isoformat(), "2026-10-26")      # Monday starts a new week

    def test_only_this_weeks_lines_count(self):
        rows = [row("2026-10-18T23:59:59", 10), row("2026-10-19T00:00:00", 2), row("2026-10-25T23:59:59", 3), row("2026-10-26T00:00:00", 10)]
        self.assertEqual(ai_budget.used(rows, WED), 5.0)

    def test_tokens_add_input_output_and_both_cache_counts(self):
        self.assertEqual(ai_budget.used([row("2026-10-20T09:00:00")], WED, "tokens"), 135)

    def test_bad_lines_count_nothing(self):
        rows = [row("not a date"), {"at": "2026-10-20T09:00:00", "cost_usd": "lots"}, {"at": "2026-10-20", "cost_usd": float("nan")},
                {"at": "2026-10-20", "cost_usd": -5}, {"at": "2026-10-20", "cost_usd": True}, "junk", None, {"cost_usd": 3}]
        self.assertEqual(ai_budget.used(rows, WED), 0.0)


class States(unittest.TestCase):
    CFG = ai_budget.settings({"weekly_dollars": 100})

    def st(self, spent, **cfg):
        c = ai_budget.settings(dict({"weekly_dollars": 100}, **cfg))
        return ai_budget.status([row("2026-10-20T09:00:00", spent)], c, WED)

    def test_ok_warn_over_at_the_edges(self):
        self.assertEqual(self.st(79.99)["state"], "ok")
        self.assertEqual(self.st(80)["state"], "warn")          # 80% exactly warns
        self.assertEqual(self.st(99.99)["state"], "warn")
        self.assertEqual(self.st(100)["state"], "over")         # 100% exactly is over
        self.assertEqual(self.st(250)["percent"], 250.0)

    def test_off_never_warns_or_holds(self):
        st = self.st(500, enabled=False)
        self.assertEqual(st["state"], "off")
        self.assertEqual(ai_budget.warning(st), "")
        self.assertIsNone(ai_budget.gate("ask", st))

    def test_warning_words(self):
        self.assertEqual(ai_budget.warning(self.st(10)), "")
        w = ai_budget.warning(self.st(85))
        self.assertIn("$85.00 of $100.00", w)
        self.assertIn("25-10-2026", w)                          # DD-MM-YYYY, the week's last day
        self.assertIn("Over this week's AI budget", ai_budget.warning(self.st(120)))

    def test_a_new_week_starts_empty(self):
        rows = [row("2026-10-20T09:00:00", 500)]
        nxt = ai_budget.status(rows, ai_budget.settings({}), datetime(2026, 10, 26, 8, 0))
        self.assertEqual((nxt["used"], nxt["state"]), (0.0, "ok"))

    def test_missing_log_is_nothing_used_and_never_holds(self):
        st = ai_budget.status([], ai_budget.settings({}), WED)
        self.assertEqual((st["used"], st["state"], st["counted"]), (0.0, "ok", True))
        broken = dict(self.st(500), counted=False)               # the file could not be read
        self.assertIsNone(ai_budget.gate("ask", broken))


class Gate(unittest.TestCase):
    def over(self, **cfg):
        return ai_budget.status([row("2026-10-20T09:00:00", 60)], ai_budget.settings(dict({"weekly_dollars": 50}, **cfg)), WED)

    def test_confirm_mode_asks_then_runs_anyway(self):
        held = ai_budget.gate("ask", self.over())
        self.assertIs(held["ok"], False)
        self.assertTrue(held["budget"]["can_continue"])
        self.assertIn("Run this request anyway?", held["message"])
        self.assertIn("26-10-2026", held["message"])
        self.assertIn("The buttons in the dashboard still work.", held["message"])
        self.assertNotIn("Apply", held["message"])
        self.assertIsNone(ai_budget.gate("ask", self.over(), over_budget=True))
        self.assertIsNotNone(ai_budget.gate("ask", self.over(), over_budget="yes"))       # only the boolean is a click

    def test_stop_mode_refuses_even_with_the_click(self):
        held = ai_budget.gate("ask", self.over(at_limit="stop"), over_budget=True)
        self.assertFalse(held["budget"]["can_continue"])
        self.assertNotIn("anyway", held["message"])

    def test_never_held(self):
        for kind in ("sweep", "vip", "draft", "generate", "prep", "process", "calendar", "reextract", "check", "load"):
            self.assertIsNone(ai_budget.gate(kind, self.over(at_limit="stop")), kind)     # unattended and draft runs go on
        self.assertIsNone(ai_budget.gate("ask", self.over(at_limit="stop"), confirmed="Apply these"))   # a change in flight goes on

    def test_a_fault_holds_nothing(self):
        self.assertIsNone(ai_budget.gate("ask", {"state": "over"}))                          # a broken status
        self.assertIsNone(ai_budget.gate("ask", object()))


class CountsOnly(unittest.TestCase):
    def test_no_text_from_the_log_reaches_the_output(self):
        rows = [row("2026-10-20T09:00:00", 60, label="Mia Hale budget", model="SECRET-MODEL", skills=["SECRET-SKILL"])]
        st = ai_budget.status(rows, ai_budget.settings({"weekly_dollars": 50}), WED)
        out = json.dumps([st, ai_budget.gate("ask", st), ai_budget.warning(st)])
        for word in ("SECRET", "Mia", "budget\"}"):
            self.assertNotIn(word, out)

    def test_status_values_are_numbers_dates_and_fixed_words(self):
        st = ai_budget.status([], ai_budget.settings({}), WED)
        for k, v in st.items():
            if k != "line":
                self.assertIsInstance(v, (int, float, bool, str), k)

    def test_module_never_writes(self):
        src = (ROOT / "system/scripts/ai_budget.py").read_text(encoding="utf-8")
        for bad in ("open(", "write_text", "write_bytes", "subprocess", "unlink"):
            self.assertNotIn(bad, src)


class Corrupt(unittest.TestCase):
    """A corrupt usage line counts nothing, never spend (each case has a mutant in the review notes: drop the check and it fails)."""
    def cost(self, v, at="2026-10-20T09:00:00"):
        return ai_budget.used([{"at": at, "cost_usd": v}], WED)

    def test_not_finite_counts_nothing(self):
        for v in (float("inf"), float("-inf"), float("nan"), 1e999, "1e999", "Infinity"):
            self.assertEqual(self.cost(v), 0.0, repr(v))
        self.assertEqual(self.cost(-3), 0.0)
        self.assertEqual(ai_budget._num(float("inf")), 0.0)

    def test_a_text_cost_counts_nothing(self):
        for v in ("999", "1.5", " 2 ", b"3", [4], {"a": 1}, None, True):
            self.assertEqual(self.cost(v), 0.0, repr(v))
        self.assertEqual(self.cost(2), 2.0)
        self.assertEqual(self.cost(2.5), 2.5)
        self.assertEqual(ai_budget.used([{"at": "2026-10-20T09:00:00", "input": "5"}], WED, "tokens"), 0.0)

    def test_a_number_is_not_a_date(self):
        for at in (20261020, 20261020.0, True, None, ["2026-10-20"]):
            self.assertEqual(self.cost(5, at), 0.0, repr(at))
        self.assertEqual(self.cost(5, "2026-10-20T09:00:00"), 5.0)

    def test_an_infinite_line_never_locks_a_typed_ask(self):
        rows = [{"at": "2026-10-20T09:00:00", "cost_usd": 1e999}]
        st = ai_budget.status(rows, ai_budget.settings({"at_limit": "stop"}), WED)
        self.assertEqual(st["state"], "ok")
        self.assertIsNone(ai_budget.gate("ask", st))


class Settings(unittest.TestCase):
    def test_a_limit_of_zero_or_below_or_not_a_number_is_the_default(self):
        for v in (0, -5, 0.0, -0.0, "ten", None, float("inf"), float("nan"), True):
            self.assertEqual(ai_budget.settings({"weekly_dollars": v})["weekly_dollars"], 50, repr(v))
            self.assertEqual(ai_budget.settings({"weekly_tokens": v})["weekly_tokens"], 50000000, repr(v))

    def test_defaults_and_hand_edits(self):
        d = ai_budget.settings({})
        self.assertEqual((d["enabled"], d["unit"], d["at_limit"]), (True, "dollars", "confirm"))
        s = ai_budget.settings({"enabled": "no", "unit": "pounds", "at_limit": "ignore", "weekly_dollars": "lots", "weekly_tokens": True})
        self.assertEqual(s, d)                                   # junk falls back to the defaults
        self.assertEqual(ai_budget.settings({"weekly_dollars": 0.5})["weekly_dollars"], 1)           # held between its limits
        self.assertEqual(ai_budget.settings({"weekly_dollars": 10 ** 9})["weekly_dollars"], 10000)
        self.assertEqual(ai_budget.settings({"weekly_dollars": float("nan")})["weekly_dollars"], 50)

    def test_catalogue_has_every_key_in_advanced_with_a_reason(self):
        defaults = settings_catalogue.flatten(settings_catalogue.defaults())
        keys = [k for k in defaults if k.startswith("ai_budget.")]
        self.assertEqual(sorted(keys), sorted(f"ai_budget.{k}" for k in ai_budget.DEFAULTS))
        for k in keys:
            group, label, line, reason = settings_catalogue.CATALOGUE[k]
            self.assertEqual(settings_catalogue.tier_of(k), settings_catalogue.ADVANCED)
            self.assertTrue(label and line and reason, k)
        for k, v in ai_budget.DEFAULTS.items():
            self.assertEqual(defaults[f"ai_budget.{k}"], v)         # one default, in settings-defaults.json


class Wiring(unittest.TestCase):
    def test_usage_report_carries_the_budget(self):
        import tempfile
        import usage_report
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "u.jsonl"
            f.write_text(json.dumps(row("2026-10-20T09:00:00", 3)) + "\nnot json\n", encoding="utf-8")
            out = usage_report.json_report(7, str(f), str(Path(d) / "none.jsonl"), reviews_root=d)
        self.assertIn("budget", out)
        self.assertEqual(set(out["budget"]) & {"label", "model", "skills"}, set())

    def test_the_page_has_the_setting_controls_the_bar_and_the_prompt(self):
        src = ROOT / "system/templates/dashboard/src"
        self.assertIn("ai_budget.at_limit", (src / "components/settings/MoreSettings.jsx").read_text(encoding="utf-8"))
        self.assertIn("BudgetBar", (src / "components/activity/UsagePanel.jsx").read_text(encoding="utf-8"))
        ask = (src / "ask.js").read_text(encoding="utf-8")
        self.assertIn("over_budget:true", ask)
        self.assertIn("res.status===429", ask)


if __name__ == "__main__":
    unittest.main()
