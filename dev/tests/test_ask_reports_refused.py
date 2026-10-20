"""v2.5.1 (Alan, 19-10-2026): ask creaite never writes reports. A direct Edit or Write of a weekly or client report file or draft, a
report.py weekly-stage or client-stage run and a Bash call naming a report file are refused; reading a report (Read) and writing other
drafts stay allowed."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import paths  # noqa: E402
import reach  # noqa: E402


class ReportsAreTheUsers(unittest.TestCase):
    def draft(self, name):
        return str(paths.DRAFTS / name)

    def test_a_direct_write_of_a_report_draft_is_refused(self):
        for name in ("2026-10-16 Example Programme Client report.json", "2026-10-16 Example Programme Weekly report.html",
                     "client_report_ABC.json", "Weekly-Report ABC.md"):
            ok, why = reach.hook_decision("Write", {"file_path": self.draft(name)}, "chat", "run-x")
            self.assertFalse(ok, name)
            self.assertIn("reports are the user's", why)

    def test_other_drafts_stay_allowed(self):
        ok, why = reach.hook_decision("Write", {"file_path": self.draft("notes-for-the-meeting.md")}, "chat", "run-x")
        self.assertTrue(ok, why)

    def test_report_stage_commands_are_refused(self):
        for cmd in ("python3 system/scripts/report.py weekly-stage system/staging/drafts/x.json",
                    "system/scripts/run report.py client-stage system/staging/drafts/x.json"):
            self.assertIn("reports are the user's", reach.report_command_refusal(cmd) or "", cmd)

    def test_read_commands_and_other_scripts_are_not_affected(self):
        for cmd in ("python3 system/scripts/report.py weekly-data ABC", "system/scripts/run tracker.py show ABC"):
            self.assertIsNone(reach.report_command_refusal(cmd), cmd)

    def test_a_bash_argument_that_is_a_report_draft_is_refused(self):
        cmd = f"cp {self.draft('x.json')} '{self.draft('2026-10-16 ABC Client report.json')}'"
        self.assertIn("reports are the user's", reach.report_command_refusal(cmd) or "")

    def test_reading_a_report_with_the_read_tool_is_allowed(self):
        ok, why = reach.hook_decision("Read", {"file_path": self.draft("2026-10-16 ABC Client report.json")}, "chat", "run-x")
        self.assertTrue(ok, why)


if __name__ == "__main__":
    unittest.main()
