"""#370 slice 3 (B1, B2): a run creaite starts says what today is and which commands it may run, and the refusals the guard
hook made are counted per run. Skips unless the guarded patch (dev/proposals/370/live_server-370s3.diff) is applied.
Run: python3 dev/tests/test_job_prompts_370.py"""
import os
import sys
import unittest
from unittest import mock
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import live_server  # noqa: E402

APPLIED = hasattr(live_server, "RUN_LIMITS_370")


@unittest.skipUnless(APPLIED, "the #370 slice 3 patch is not applied")
class RunLimits(unittest.TestCase):
    def setUp(self):
        self._now = os.environ.get("CREAITE_NOW")
        os.environ["CREAITE_NOW"] = "2026-11-03 09:30"

    def tearDown(self):
        os.environ.pop("CREAITE_NOW", None)
        if self._now:
            os.environ["CREAITE_NOW"] = self._now

    def test_every_kind_states_the_date_and_forbids_the_usual_strays(self):
        for kind in live_server.RUN_LIMITS_370:
            with self.subTest(kind):
                text = live_server.run_limits(kind)
                self.assertIn("2026-11-03", text)
                self.assertIn("Never grep, tail or date", text)

    def test_allowed_commands_are_the_kinds_own_rules(self):
        process = live_server.run_limits("process")
        for c in ("minutes.py stage", "propose.py people map", "docx_tools.py fill", "search.py enrich set"):
            self.assertIn(c, process)
        self.assertNotIn("tracker.py", process)
        self.assertIn("sweep.py calendar-window", live_server.run_limits("calendar"))
        self.assertIn("sweep.py …", live_server.run_limits("sweep"))

    def test_a_kind_without_scripts_has_no_shell(self):
        for kind in ("check", "load"):
            self.assertIn("You have no shell", live_server.run_limits(kind))

    def test_a_run_is_started_with_the_paragraph(self):
        import inspect
        self.assertIn("run_prompt(kind, confirmed) + run_limits(kind)", inspect.getsource(live_server.Run._start))

    def test_other_kinds_get_nothing(self):
        self.assertEqual(live_server.run_limits("ask"), "")


@unittest.skipUnless(APPLIED, "the #370 slice 3 patch is not applied")
class RefusalCount(unittest.TestCase):
    def test_only_the_guards_refusals_are_counted(self):
        run = object.__new__(live_server.Run)
        for part in ({"is_error": True, "content": "creaite refused this: only one script"},
                     {"is_error": True, "content": "creaite refused this: no"},
                     {"is_error": True, "content": "No such file"},
                     {"is_error": False, "content": "creaite refused this"}):
            run._count_refusal(part)
        self.assertEqual(run.refusals, 2)

    def fresh_run(self):
        run = object.__new__(live_server.Run)
        run.job, run.tooluse, run.pending, run.steps, run.id, run.kind = None, {}, {}, [], "r1", "ask"
        return run

    def test_the_result_path_counts_and_the_run_end_logs_it(self):
        run = self.fresh_run()
        run._on_tool_result({"is_error": True, "tool_use_id": "a", "content": "creaite refused this: grep"})
        run._on_tool_result({"is_error": True, "tool_use_id": "b", "content": "creaite refused this: tail"})
        self.assertEqual(run.refusals, 2)
        run.stop = False
        with mock.patch.object(live_server, "debuglog") as log, mock.patch.object(live_server, "release_sweep_lock"), \
                mock.patch.object(live_server, "queue_after", return_value=None), mock.patch.object(live_server, "EVENTS"), \
                mock.patch.object(live_server.Run, "_usage_record"):
            run.cond, run.events = live_server.threading.Condition(), []
            run.session = run.chat = None
            run._done()
        self.assertIn("ask refusals: 2", log.info.call_args_list[0][0][1])


if __name__ == "__main__":
    unittest.main()
