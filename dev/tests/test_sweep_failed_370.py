"""#370 slice 1: a mail and Teams check that didn't run is recorded and shown, in Alan's approved words.

`sweep.py fail` writes system/staging/sweep-failed.json ({at, retry_at, day}: times only) and `sweep.py done` removes it. The
build's sweep_due gains `failed` while today's file stands and no check has passed today's sweep.due_from since; another day's
file is ignored. Health lists "A mail and Teams check didn't run" with a Check now Fix it, and Today's page has its one line.
Throwaway vault, pinned clock (CREAITE_NOW), fictional data only.

Run: python3 dev/tests/test_sweep_failed_370.py     (quick tier: no Chrome)
"""
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
TITLE = "A mail and Teams check didn't run"
DETAIL = "creaite couldn't reach Microsoft 365 when it started."
TODAY_LINE = "Today's mail and Teams check didn't run."


class Base(unittest.TestCase):
    NOW = "2026-10-26 08:15"

    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.state = self.v.root / "system/staging/sweep-failed.json"
        self.last = self.v.root / "system/staging/last-sweep.txt"

    def tearDown(self):
        self.v.cleanup()

    def sweep(self, *args, now=None):
        env = {**os.environ, "CREAITE_NOW": now or self.NOW}
        return subprocess.run([sys.executable, str(self.v.root / "system/scripts/sweep.py"), *args], cwd=self.v.root,
                              capture_output=True, text=True, env=env)

    def fail(self, now=None):
        r = self.sweep("fail", "--message", "the connector was missing", now=now)
        self.assertEqual(r.returncode, 0, r.stderr)

    def due(self, now=None):
        env = {**os.environ, "CREAITE_NOW": now or self.NOW}
        code = ("import sys; sys.path.insert(0, 'system/scripts'); import build_dashboard as b, json; "
                "print(json.dumps(b.sweep_due_info()))")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def health_row(self, now=None):
        env = {**os.environ, "CREAITE_NOW": now or self.NOW}
        code = ("import sys; sys.path.insert(0, 'system/scripts'); import health, json; "
                "print(json.dumps([p for p in health.health()['problems'] if p['id'] == 'sweep_failed']))")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])


class StateFile(Base):
    def test_fail_writes_exactly_three_keys_of_times(self):
        self.fail()
        d = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(d, {"at": "2026-10-26 08:15", "retry_at": None, "day": "2026-10-26"})

    def test_the_file_holds_no_name_path_or_message(self):
        self.fail()
        text = self.state.read_text(encoding="utf-8")
        for bad in ("connector", "/", "\\", "message", "@"):
            self.assertNotIn(bad, text)

    def test_done_removes_it(self):
        self.fail()
        r = self.sweep("done", "--started", "2026-10-26 09:00", "--normal")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.state.exists())

    def test_done_with_no_file_is_fine(self):
        r = self.sweep("done", "--started", "2026-10-26 09:00", "--normal")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_mutant_a_done_that_left_the_file_would_be_caught(self):
        """Mutant: put the file back after done, as a done that kept it would; the build then reports a failure again."""
        self.fail()
        self.sweep("done", "--started", "2026-10-26 08:30")           # not --normal: last-sweep.txt stays old, so only the file decides
        self.assertFalse(self.state.exists())
        self.assertNotIn("failed", self.due())
        self.state.write_text(json.dumps({"at": "2026-10-26 08:15", "retry_at": None, "day": "2026-10-26"}), encoding="utf-8")
        self.assertIn("failed", self.due())                           # the mutant's state is visible, so the assertion above bites


class BuildFlag(Base):
    def test_failed_flag_present_today(self):
        self.fail()
        d = self.due()
        self.assertTrue(d["due"])
        self.assertEqual(d["failed"], {"at": "08:15", "retry": None})

    def test_no_flag_without_a_failure(self):
        self.assertNotIn("failed", self.due())

    def test_a_file_from_another_day_is_ignored(self):
        self.fail(now="2026-10-25 08:15")
        self.assertNotIn("failed", self.due("2026-10-26 08:15"))

    def test_cleared_once_a_check_has_passed_due_from(self):
        self.fail()
        self.last.write_text("2026-10-26 08:40\n", encoding="utf-8")
        d = self.due("2026-10-26 09:00")
        self.assertFalse(d["due"])
        self.assertNotIn("failed", d)

    def test_a_check_before_due_from_does_not_clear_it(self):
        self.fail()
        self.last.write_text("2026-10-25 17:00\n", encoding="utf-8")
        self.assertIn("failed", self.due())

    def test_retry_time_is_shown_as_hh_mm(self):
        self.state.write_text(json.dumps({"at": "2026-10-26 08:15", "retry_at": "2026-10-26 08:20", "day": "2026-10-26"}),
                              encoding="utf-8")
        self.assertEqual(self.due()["failed"], {"at": "08:15", "retry": "08:20"})


class HealthRow(Base):
    def test_exact_title_detail_and_button(self):
        self.fail()
        rows = self.health_row()
        self.assertEqual(len(rows), 1)
        p = rows[0]
        self.assertEqual(p["title"], TITLE)
        self.assertEqual(p["detail"], DETAIL)
        self.assertEqual(p["fix"]["button"], "Check now")
        self.assertTrue(p["fix"]["built"])
        self.assertEqual(p["fix"]["call"], "/api/day/catchup")

    def test_detail_with_a_retry(self):
        self.state.write_text(json.dumps({"at": "2026-10-26 08:15", "retry_at": "2026-10-26 08:20", "day": "2026-10-26"}),
                              encoding="utf-8")
        self.assertEqual(self.health_row()[0]["detail"], DETAIL + " It tried again at 08:20.")

    def test_no_row_when_nothing_failed_or_after_a_check(self):
        self.assertEqual(self.health_row(), [])
        self.fail()
        self.last.write_text("2026-10-26 08:40\n", encoding="utf-8")
        self.assertEqual(self.health_row("2026-10-26 09:00"), [])

    def test_no_vendor_words_or_paths_in_the_row(self):
        self.fail()
        p = self.health_row()[0]
        text = " ".join([p["title"], p["detail"], p["fix"]["button"], p["fix"]["does"]]).lower()
        for bad in ("connector", "session", "tool", "sweep", "/", "json"):
            self.assertNotIn(bad, text)


class TodayLine(unittest.TestCase):
    def test_the_exact_line_is_in_the_source_and_the_built_page(self):
        src = (REPO / "system/templates/dashboard/src/today.js").read_text(encoding="utf-8")
        page = (REPO / "system/templates/dashboard.html").read_text(encoding="utf-8")
        self.assertIn(TODAY_LINE, src)
        self.assertIn(TODAY_LINE, page)

    def test_the_failed_line_has_no_dismiss_and_calls_the_catchup_route(self):
        src = (REPO / "system/templates/dashboard/src/today.js").read_text(encoding="utf-8")
        line = next(ln for ln in src.splitlines() if TODAY_LINE in ln)
        self.assertNotIn("sweepX", line)
        self.assertIn('id="sweepFailedRun"', line)
        self.assertIn("Check now", line)
        self.assertRegex(src, r'api\("/api/day/catchup",\{force:true\}\)')
        self.assertRegex(src, r"sweepFailed\(\)\|\|!sweepDueDismissed\(\)")      # a dismissal doesn't hide it while it holds


if __name__ == "__main__":
    unittest.main()
