"""BL-228 (sprint-debt-safety), parts A and C.

A: the client-safe label check fails closed: it is skipped only for a database without the labels tables; any other
   failure is a finding (client report and client-safe one-pager at review) or stops the one-pager's build.
C: the narrowed exception handlers carry on for the errors they expect and log (debug level, name only) the rest;
   tracker.connect_or_raise raises a normal error.

Run: python3 dev/tests/test_debt_safety.py
Each test builds a throwaway vault with fictional data (test_steerco.Base) and runs the real scripts there.
"""
import json
import os
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_steerco import NOW, Base  # noqa: E402

LABEL_CHECK = "Couldn't check the label exclusions"


class LabelCheckFailsClosed(Base):
    """Part A."""

    def db(self, *sql):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            for s in sql:
                con.execute(s)
            con.commit()

    def findings(self, text):
        """review.client_findings on a draft whose text is `text` (the docx reader replaced; the rest is the real code)."""
        code = ("import json, sys; sys.path.insert(0, 'system/scripts'); import review\n"
                f"review.draft_lines = lambda p: {text!r}.splitlines()\n"
                "print(json.dumps(review.client_findings({'draft': 'x.docx', 'project': 'ABC'})))")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, env={**os.environ, "CREAITE_NOW": NOW},
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_a_database_without_the_labels_tables_still_passes(self):
        self.db("DROP TABLE item_labels", "DROP TABLE labels")
        self.assertEqual(self.findings("A plain client update."), [])

    def test_a_broken_labels_view_is_a_finding(self):
        self.db("DROP TABLE item_labels", "CREATE VIEW item_labels AS SELECT item_id, label FROM gone_table")
        found = self.findings("A plain client update.")       # "no such table", but labels and item_labels are both there
        self.assertTrue(any(f.startswith(LABEL_CHECK) and "check before sending" in f for f in found), found)

    def test_any_other_labels_error_is_a_finding(self):
        self.db("DROP TABLE labels", "CREATE VIEW labels AS SELECT name FROM item_labels")     # no behaviour column
        found = self.findings("A plain client update.")
        self.assertTrue(any(f.startswith(LABEL_CHECK) and "OperationalError" in f for f in found), found)

    def test_an_excluded_item_is_still_found_by_id_and_by_wording(self):
        self.label("ABC-D-014")
        self.assertIn("ABC-D-014 is labelled Sensitive but its ID appears", self.findings("See ABC-D-014."))
        found = self.findings("The proposal no longer includes the pricing option.")
        self.assertTrue(any(f.startswith("ABC-D-014 is labelled Sensitive but its wording appears") for f in found), found)
        self.assertFalse(any(f.startswith(LABEL_CHECK) for f in found), found)

    def test_a_failed_label_check_stops_client_approval(self):
        self.stage(version="client")
        self.db("DROP TABLE labels", "CREATE VIEW labels AS SELECT name FROM item_labels")
        self.script("review.py", "list")
        out = self.script("review.py", "approve", "1").stdout
        self.assertIn("not approved — possible internal content in the client report", out)
        self.assertIn(LABEL_CHECK, out)

    def test_the_one_pager_without_the_labels_tables_still_builds(self):
        self.db("DROP TABLE item_labels", "DROP TABLE labels")
        self.assertEqual(self.data("--version", "client")["labelled_but_excluded"], [])

    def test_the_one_pager_stops_when_the_labels_cant_be_read(self):
        self.db("DROP TABLE labels", "CREATE VIEW labels AS SELECT name FROM item_labels")
        for version in ("client", "internal"):
            r = self.script("report.py", "steerco-data", "ABC", "--version", version, ok=False)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("couldn't read the labels", r.stderr)


PRELUDE = """
import json, sys, time
sys.path.insert(0, 'system/scripts')
from datetime import date, datetime
"""


class SwallowedExceptions(unittest.TestCase):
    """Part C: each narrowed block goes on for the error it expects (nothing logged) and logs, by name only, the one it
    did not (still going on)."""

    def setUp(self):
        from test_tracker import Vault
        self.v = Vault()
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data.setdefault("logging", {})["level"] = "debug"
        cfg.write_text(json.dumps(data, indent=2))

    def tearDown(self):
        self.v.cleanup()

    def py(self, code):
        r = subprocess.run([sys.executable, "-c", PRELUDE + code], cwd=self.v.root, env={**os.environ, "CREAITE_NOW": NOW},
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout.strip()

    def log(self):
        return "".join(f.read_text() for f in (self.v.root / "system/logs").glob("debug-*.log")) \
            if (self.v.root / "system/logs").is_dir() else ""

    def test_connect_or_raise_raises_a_normal_error(self):
        out = self.py("import tracker\n"
                      "try:\n    tracker.connect_or_raise()\nexcept tracker.NoDatabase as e:\n    print('NoDatabase', e)\n")
        self.assertTrue(out.startswith("NoDatabase"), out)
        self.v.run("init")
        self.assertEqual(self.py("import tracker; print(tracker.connect_or_raise().execute('SELECT 1').fetchone()[0])"), "1")

    def test_update_parts_without_a_database_shows_the_change(self):
        out = self.py("import review; print(review.update_parts({'table': 'actions', 'id': 'ABC-A-001', 'changes': {'status': 'Closed'}})[1])")
        self.assertEqual(out, "status — → Closed")
        self.assertNotIn("update_parts", self.log())

    def test_update_parts_logs_an_unexpected_error_and_goes_on(self):
        out = self.py("import review, tracker\n"
                      "def boom(*a): raise ZeroDivisionError('secret text')\n"
                      "tracker.connect_or_raise = boom\n"
                      "print(review.update_parts({'table': 'actions', 'id': 'ABC-A-001', 'changes': {'status': 'Closed'}})[1])")
        self.assertEqual(out, "status — → Closed")
        self.assertIn("update_parts ABC-A-001: ZeroDivisionError ignored", self.log())
        self.assertNotIn("secret text", self.log())

    def dashboard_case(self, patch_module, patch_name, call, where):
        for err, logged in (("KeyError", False), ("ZeroDivisionError", True)):
            out = self.py(f"import build_dashboard, {patch_module}\n"
                          f"def boom(*a, **k): raise {err}('secret text')\n"
                          f"{patch_module}.{patch_name} = boom\n"
                          f"print(type({call}).__name__)")
            self.assertIn(out, ("list", "dict"), out)                                     # the page part is still built
            self.assertEqual(f"{where}: {err} ignored" in self.log(), logged, self.log())
        self.assertNotIn("secret text", self.log())

    def test_reminders_go_on_and_log_only_the_unexpected(self):
        self.dashboard_case("sweep", "vip_state", "build_dashboard.reminders({}, [], [], date(2026, 10, 9), datetime(2026, 10, 9, 13))",
                            "reminders")

    def test_prep_goes_on_and_logs_only_the_unexpected(self):
        self.dashboard_case("propose", "vip_people", "build_dashboard.prep({}, [], [], date(2026, 10, 9))", "prep")

    def test_observe_goes_on_and_logs_only_the_unexpected(self):
        for err, logged in (("ValueError", False), ("ZeroDivisionError", True)):
            self.py("import live_server, reach\n"
                    f"def boom(*a, **k): raise {err}('secret text')\n"
                    "reach.outside_reason = boom\n"
                    "class R: id = 'run1'\n"
                    "live_server.Run.observe(R(), 'Read', {'file_path': 'x'})\n")
            self.assertEqual(f"observe: {err} ignored" in self.log(), logged, self.log())
        self.assertNotIn("secret text", self.log())

    def test_the_run_reader_goes_on_and_logs_only_the_unexpected(self):
        fake = self.v.root / "fake_claude.py"
        fake.write_text("#!/usr/bin/env python3\nimport json\n"
                        "print(json.dumps({'type': 'assistant', 'session_id': 's1', 'message': {'content': [\n"
                        "    {'type': 'tool_use', 'id': 't1', 'name': 'mcp__m365__read_resource', 'input': {'uri': 'x'}}]}}))\n"
                        "print(json.dumps({'type': 'user', 'message': {'content': [\n"
                        "    {'type': 'tool_result', 'tool_use_id': 't1', 'content': 'ok'}]}}))\n"
                        "print(json.dumps({'type': 'result', 'result': 'done'}))\n")
        fake.chmod(0o755)
        for err, logged in (("KeyError", False), ("ZeroDivisionError", True)):
            out = self.py("import os, live_server\n"
                          f"os.environ['CREAITE_CLAUDE'] = {str(fake)!r}\n"
                          "class Job:\n"
                          f"    def observe(self, *a): raise {err}('secret text')\n"
                          "    def finish(self): return {'status': 'none', 'files': [], 'message': 'finished'}\n"
                          "r = live_server.Run('run1', 'check', None, None, None, kind='check', job=Job())\n"
                          "end = time.time() + 30\n"
                          "while not r.done and time.time() < end: time.sleep(0.1)\n"
                          "print(r.done, [e['type'] for e in r.events][-1])\n")
            self.assertEqual(out, "True done")                                            # the run still finished
            self.assertEqual(f"read: {err} ignored" in self.log(), logged, self.log())
        self.assertNotIn("secret text", self.log())


if __name__ == "__main__":
    unittest.main()
