"""#370 (D4): Health says so when detailed logging (logging.level "debug") has been on for more than 7 days, from the last logged
change in settings-log.jsonl. It informs only: nothing is changed. No record, no row.

Run: python3 dev/tests/test_log_level_health_370.py
"""
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "system/scripts"))
import health  # noqa: E402

NOW = datetime(2026, 10, 27, 12, 0, 0)
DEBUG = {"logging": {"level": "debug"}}


def log(tmp, *rows):
    p = Path(tmp) / "settings-log.jsonl"
    p.write_text("".join((r if isinstance(r, str) else json.dumps(r)) + "\n" for r in rows), encoding="utf-8")
    return p


def change(at, new="debug", key="logging.level"):
    return {"at": at, "key": key, "old": "info", "new": new}


class Row(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def check(self, settings, *rows, now=NOW):
        return health.detailed_logging_check(settings, log(self.tmp.name, *rows), now)

    def test_a_row_when_debug_has_been_on_over_a_week(self):
        c = self.check(DEBUG, change("2026-10-19 09:00:00"))
        self.assertEqual((c["id"], c["status"]), ("detailed_logging", "warn"))
        self.assertIn("19-10-2026", c["detail"])
        self.assertIn("Settings", c["detail"])

    def test_no_row_at_six_days(self):
        self.assertIsNone(self.check(DEBUG, change("2026-10-21 13:00:00")))

    def test_no_row_at_exactly_seven_days_and_a_row_just_after(self):
        self.assertIsNone(self.check(DEBUG, change("2026-10-20 12:00:00")))
        self.assertIsNotNone(self.check(DEBUG, change("2026-10-20 11:59:59")))

    def test_no_row_at_info(self):
        self.assertIsNone(self.check({"logging": {"level": "info"}}, change("2026-09-01 09:00:00")))
        self.assertIsNone(self.check({}, change("2026-09-01 09:00:00")))

    def test_no_row_when_there_is_no_record(self):
        self.assertIsNone(self.check(DEBUG))
        self.assertIsNone(self.check(DEBUG, change("2026-09-01 09:00:00", key="logging.keep_days")))
        self.assertIsNone(health.detailed_logging_check(DEBUG, Path(self.tmp.name) / "none.jsonl", NOW))

    def test_the_last_change_counts_and_a_later_change_away_from_debug_means_no_guess(self):
        self.assertIsNone(self.check(DEBUG, change("2026-09-01 09:00:00"), change("2026-10-26 09:00:00", "info"), change("2026-10-26 10:00:00")))
        self.assertIsNone(self.check(DEBUG, change("2026-09-01 09:00:00"), change("2026-10-26 09:00:00", "info")))

    def test_a_damaged_line_or_time_says_nothing_and_does_not_raise(self):
        self.assertIsNotNone(self.check(DEBUG, "{not json", change("2026-10-01 09:00:00")))
        self.assertIsNone(self.check(DEBUG, change("yesterday")))
        self.assertIsNone(self.check(DEBUG, {"key": "logging.level", "new": "debug"}))

    def test_health_lists_it_in_plain_words_dismissible_and_changes_no_setting(self):
        row = health.detailed_logging_check(DEBUG, log(self.tmp.name, change("2026-10-01 09:00:00")), NOW)
        with mock.patch.object(health, "detailed_logging_check", return_value=row), mock.patch.object(health, "autostart_check", return_value=None), \
                mock.patch.object(health, "stopped_errors", return_value=[]):
            h = health.health({"checks": [], "passed": 0, "failed": 0}, dismissed=[])
        p = [x for x in h["problems"] if x["id"] == "detailed_logging"]
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]["title"], "Detailed logging has been on for over a week")
        self.assertTrue(p[0]["dismissable"])
        self.assertFalse(p[0]["fix"]["built"])
        self.assertEqual(p[0]["fix"]["button"], "Open Settings")

    def test_it_reads_and_writes_nothing_else(self):
        p = log(self.tmp.name, change("2026-10-01 09:00:00"))
        before = p.read_bytes()
        self.check(DEBUG, change("2026-10-01 09:00:00"))
        self.assertEqual(p.read_text(encoding="utf-8").count("\n"), 1)
        self.assertEqual(before, p.read_bytes())


class Mutants(unittest.TestCase):
    """A change to the rule must fail the cases above: the same cases run against a copy with one line altered."""

    def run_mutant(self, old, new):
        src = (HERE.parents[1] / "system/scripts/health.py").read_text(encoding="utf-8")
        self.assertIn(old, src)
        ns = {"__name__": "health_mutant", "__file__": str(HERE.parents[1] / "system/scripts/health.py")}
        exec(compile(src.replace(old, new, 1), "health_mutant", "exec"), ns)
        return ns["detailed_logging_check"]

    def test_each_mutant_is_caught(self):
        with tempfile.TemporaryDirectory() as t:
            cases = [(DEBUG, change("2026-10-19 09:00:00"), True), (DEBUG, change("2026-10-21 13:00:00"), False),
                     ({"logging": {"level": "info"}}, change("2026-09-01 09:00:00"), False), (DEBUG, None, False)]

            def ok(fn):
                for settings, row, want in cases:
                    p = log(t, row) if row else log(t)
                    if (fn(settings, p, NOW) is not None) != want:
                        return False
                return True
            self.assertTrue(ok(self.run_mutant("DETAILED_LOGGING_DAYS = 7", "DETAILED_LOGGING_DAYS = 7")), "the unaltered copy passes")
            for old, new in (("DETAILED_LOGGING_DAYS = 7", "DETAILED_LOGGING_DAYS = 5"), ("DETAILED_LOGGING_DAYS = 7", "DETAILED_LOGGING_DAYS = 9"),
                             ('.lower() != "debug":', '.lower() == "debug":'), ("<= timedelta(days=DETAILED_LOGGING_DAYS)", ">= timedelta(days=DETAILED_LOGGING_DAYS)")):
                self.assertFalse(ok(self.run_mutant(old, new)), new)


if __name__ == "__main__":
    unittest.main()
