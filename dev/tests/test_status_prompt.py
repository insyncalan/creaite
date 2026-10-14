"""BL-106: the material and prompts a Current state draft is written from (no model is called).

Run: python3 dev/tests/test_status_prompt.py
The clock is fixed (CREAITE_NOW) to Friday 09-10-2026 13:00; the data is fictional.
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
from test_reports import NOW, ReportVault, populate  # noqa: E402
from test_tracker import ABC  # noqa: E402

PERIOD = ("--from", "2026-10-01", "--to", "2026-10-09")


class Material(unittest.TestCase):
    def setUp(self):
        self.v = ReportVault()
        populate(self.v)
        for rel in ("minutes/2026-10-05 Steering.docx", "reports/2026-10-05 Client report.docx", "reports/2026-10-05 Weekly report.docx"):
            (self.v.root / ABC / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.v.root / ABC / rel).write_bytes(b"x")

    def tearDown(self):
        self.v.cleanup()

    def context(self, *extra, ok=True):
        return self.v.at("current-context", "ABC", *PERIOD, *extra, script="report.py", ok=ok)

    def test_it_opens_with_the_guide_the_audience_and_the_facts_then_the_reference(self):
        out = self.context().stdout
        order = [out.index(h) for h in ("## Writing guide (follow it)", "## Audience and length", "## Facts (ranked",
                                          "## Reference material", "## Current state now: the left pane", "## Open actions")]
        self.assertEqual(order, sorted(order))
        self.assertIn("# The executive voice", out)
        self.assertIn("## Position", out)
        self.assertIn("Audience: internal.", out)
        self.assertIn("Length: Standard, about 150 words.", out)

    def test_the_length_is_named(self):
        self.assertIn("Length: Short, about 40 words.", self.context("--length", "short").stdout)
        self.assertIn("Length: Fuller, about 250 words.", self.context("--length", "fuller").stdout)

    def test_a_wrong_audience_or_length_is_refused(self):
        for opt in (("--audience", "press"), ("--length", "huge")):
            r = self.context(*opt, ok=False)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("must be", r.stdout + r.stderr)

    def test_internal_keeps_the_open_lists_and_every_report(self):
        out = self.context().stdout
        self.assertIn("Vendor exits the market before go-live", out)
        self.assertIn("## Open actions", out)
        self.assertIn("2026-10-05 Steering.docx", out)
        self.assertIn("2026-10-05 Weekly report.docx", out)

    def test_client_safe_holds_nothing_internal(self):
        out = self.context("--audience", "client").stdout
        self.assertIn("Audience: client-safe.", out)
        self.assertIn("Test licences are not yet ordered.", out)                       # the client wording
        for internal in ("Vendor exits the market", "Escalate data access", "## Open actions", "## Milestones", "## Tracker changes",
                         "Steering.docx", "Weekly report.docx", "Weekly updates", "swept", "Early warning", "## Trend"):
            self.assertNotIn(internal, out, internal)
        self.assertIn("2026-10-05 Client report.docx", out)                               # only client reports are listed

    def test_the_generate_prompt_fills_with_the_servers_placeholders(self):
        """live_server.generate formats the template with exactly these names; a new placeholder would break it."""
        template = (self.v.root / "system/templates/current-state-prompt.md").read_text(encoding="utf-8")
        prompt = template.format(code="ABC", name="Example", start="01-10-2026", end="09-10-2026", context="MATERIAL TEXT {braces}", note="")
        self.assertIn("MATERIAL TEXT {braces}", prompt)
        self.assertIn("SOURCES:", prompt)
        self.assertIn("never write the pane marker", prompt)

    def prompt(self, code):
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'system/scripts'); import status_prompt as s; "
                            "print(s.rewrite_prompt('ABC', 'Go-live is 20-11-2026. Sara Khan owes the data by 16-10-2026.', " + code + ", '2026-10-01', '2026-10-09'))"],
                           env={**os.environ, "CREAITE_NOW": NOW}, cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_the_rewrite_prompt_carries_alans_text_the_guide_and_the_facts(self):
        out = self.prompt("'internal', 'short'")
        for need in ("Go-live is 20-11-2026. Sara Khan owes the data by 16-10-2026.", "# The executive voice", "## Position",
                     "Audience: internal.", "Length: Short, about 40 words.", "Keep every fact Alan wrote", "--- ALAN'S TEXT ---"):
            self.assertIn(need, out)

    def test_the_client_rewrite_prompt_has_only_client_facts(self):
        out = self.prompt("'client', 'standard'")
        self.assertIn("Audience: client-safe.", out)
        self.assertNotIn("Vendor exits the market", out)
        self.assertIn("Test licences are not yet ordered.", out)


class Skills(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[2]

    def test_the_weekly_and_client_skills_read_the_guide_and_the_facts(self):
        weekly = (self.ROOT / ".claude/skills/cx-weekly-report/SKILL.md").read_text(encoding="utf-8")
        client = (self.ROOT / ".claude/skills/cx-client-report/SKILL.md").read_text(encoding="utf-8")
        for text in (weekly, client):
            self.assertIn("system/templates/executive-style.md", text)
            self.assertIn("report.py facts <CODE>", text)
        self.assertIn("--audience client", client)
        self.assertTrue((self.ROOT / "system/templates/executive-style.md").is_file())


class Helpers(unittest.TestCase):
    def test_split_reply(self):
        import status_prompt
        self.assertEqual(status_prompt.split_reply("**Headline.**\n\n- one\n\nSOURCES:\n- ABC-A-001\n- a file.md\n"),
                         ("**Headline.**\n\n- one", "- ABC-A-001\n- a file.md"))
        self.assertEqual(status_prompt.split_reply("Only a draft."), ("Only a draft.", ""))
        self.assertEqual(status_prompt.split_reply(""), ("", ""))

    def test_a_rewrite_that_keeps_the_facts_has_no_notes(self):
        import status_checks
        a = "Go-live is 20-11-2026 and handling time is down 11%. Sara Khan owes data by 16-10-2026."
        self.assertEqual(status_checks.kept(a, "**On track for 20-11-2026.** Handling time fell 11%; we need Sara Khan by 16-10-2026."), [])

    def test_a_rewrite_that_loses_or_adds_a_figure_is_noted(self):
        import status_checks
        notes = {n["id"]: n["note"] for n in status_checks.kept("Go-live is 20-11-2026; down 11%.", "Go-live is 27-11-2026; down 11%.")}
        self.assertIn("20-11-2026", notes["kept"])
        self.assertIn("27-11-2026", notes["added"])


if __name__ == "__main__":
    unittest.main()
