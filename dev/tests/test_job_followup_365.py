"""#365 follow-up (Cap's three MEDIUMs): a check or load starts without the vault's CLAUDE.md, the event is chosen by its id, and the
search is bounded. Skipped until dev/proposals/365/live_server-365-followup.diff has landed. Run: python3 dev/tests/test_job_followup_365.py"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import live_server  # noqa: E402

LANDED = hasattr(live_server, "CONTEXTLESS_JOBS")


@unittest.skipUnless(LANDED, "live_server-365-followup.diff has not landed")
class Followup(unittest.TestCase):
    def test_the_job_runs_start_without_the_vault_context(self):
        for kind in ("check", "load"):
            args, env, cwd = live_server.launch_context(kind)
            self.assertEqual(args[args.index("--setting-sources") + 1], "")           # no CLAUDE.md, no vault allow rules
            self.assertIn("--no-session-persistence", args)
            self.assertEqual(env.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY"), "1")
            root = str(live_server.paths.ROOT.resolve())
            self.assertFalse(str(Path(cwd).resolve()).startswith(root))
            self.assertEqual(live_server.run_dirs(kind, False), [])                   # no --add-dir either

    def test_no_extra_dirs_even_when_a_projects_root_is_outside_the_vault(self):     # M1: extra_dirs() was empty in the tests
        orig = live_server.extra_dirs
        live_server.extra_dirs = lambda: ["/somewhere/else"]
        try:
            self.assertEqual(live_server.run_dirs("ask", False), ["/somewhere/else"])      # the stand-in works
            for kind in ("check", "load"):
                self.assertEqual(live_server.run_dirs(kind, False), [])
                self.assertEqual(live_server.run_dirs(kind, True), [])
        finally:
            live_server.extra_dirs = orig

    def test_the_model_is_not_named_for_these_jobs(self):       # #382: Claude Code's own default, as before; not Sonnet
        for kind in ("check", "load"):
            args, _, _ = live_server.launch_context(kind)
            self.assertNotIn("--model", args)
            self.assertNotIn("sonnet", args)
        args, _, _ = live_server.launch_context("edit-ai")           # the tool-less kinds still name it
        self.assertEqual(args[args.index("--model") + 1], "sonnet")

    def test_the_prompt_does_not_say_the_vault(self):
        self.assertNotIn("headless in the vault", live_server.KIND_PROMPTS["load"])
        self.assertIn("outside the vault", live_server.KIND_PROMPTS["check"])

    def test_other_kinds_are_unchanged(self):
        args, _, cwd = live_server.launch_context("ask")
        self.assertEqual((args, cwd), ([], live_server.paths.ROOT))

    def test_the_event_is_chosen_by_its_id_and_the_search_is_bounded(self):
        p = live_server.TRANSCRIPT_PROMPT.format(title="T", day="2026-10-23", start="16:00", end="16:30", eid="EV-ID-1", chat="")
        self.assertIn("whose id is exactly EV-ID-1", p)
        self.assertIn("never one with a similar title or time", p)
        self.assertIn("one hour either side of 16:00 to 16:30", p)
        self.assertIn("whole day", p)
        self.assertIn("Never more than three searches", p)
        self.assertNotIn("title on that day", p)


if __name__ == "__main__":
    unittest.main()
