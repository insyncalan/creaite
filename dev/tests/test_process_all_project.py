"""#328 (Alan, Jarvis, 26-10-2026): Process all ready runs only Matched or remembered meetings; Likely and Not sure ones are skipped
and listed (titles only) until a project is picked. Process on the row itself still works on any row; a private or confidential
meeting stays left out by count, never named.

Run: python3 dev/tests/test_process_all_project.py   (source checks; the browser case needs Google Chrome and is skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
from ir_intake_support import IntakeBase  # noqa: E402

ACT = Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/components/intakeReview/actions.js"
src = ACT.read_text()


class Source(unittest.TestCase):
    def test_the_rule_is_in_the_ready_list_not_in_single_process(self):
        self.assertIn('m.src === "calendar" && !m.private && !m.confidential && (m.p === "_portfolio" ? m.how !== "remembered" : m.level !== "matched")', src)
        self.assertIn("!irNeedsProject(m)", src.split("export const irReady")[1].split("\n")[0])
        self.assertNotIn("irNeedsProject", src.split("export const irCanProcess")[1].split("\n")[0])      # single Process unchanged
        self.assertNotIn("irNeedsProject", src.split("export async function irProcess(m)")[1].split("\n}")[0])

    def test_the_words_name_titles_and_no_project(self):
        w = src.split("export const irSkippedWords")[1].split("\n")[0]
        self.assertIn("until you pick a project", w)
        self.assertNotIn("pName", w)
        self.assertNotIn(".p ", w)


class ProcessAll(IntakeBase):
    shared_server = True

    def test_matched_runs_likely_and_not_sure_are_skipped_and_listed(self):
        b = self.b
        self.stage_stub()
        label = lambda: b.eval("document.querySelector('[data-ira=processall]').textContent")  # noqa: E731
        self.patch("ABC Steering", level="matched", reason="Named in the title")
        self.patch("Weekly sync 12", level="likely", reason="Fits the project's register entry")
        b.wait("document.querySelector('[data-irheld]')")
        self.assertEqual(b.eval("document.querySelector('[data-irheld]').textContent"),
                         "Skipped 1 meeting until you pick a project: Weekly sync 12.")
        n = label()
        self.patch("Weekly sync 12", level="unsure", cands=["ABC"])
        self.assertEqual(label(), n)                                                  # Not sure is skipped the same way
        self.assertIn("Weekly sync 12", b.eval("document.querySelector('[data-irheld]').textContent"))
        b.click('[data-ira="processall"]')
        b.wait("irBusy.value.length===0", 40)
        asked = [q for q, _ in b.eval("ASKED")]
        self.assertFalse(any("Weekly sync" in q for q in asked), asked)               # skipped
        self.assertTrue(any("ABC Steering" in q or ".vtt" in q for q in asked), asked)  # the matched one and the files ran
        b.wait("/until you pick a project: Weekly sync 12/.test(document.getElementById('snackT').textContent)")

    def test_a_row_with_no_level_is_skipped_too(self):
        """Fails closed (security review): a calendar row the matcher gave no level needs a project like a Likely one."""
        b = self.b
        self.stage_stub()
        self.patch("ABC Steering", level="matched")
        self.patch("Weekly sync 12", level="matched")
        n = b.eval("irReady().length")
        b.eval("(()=>{ D.intake_review={...D.intake_review, meetings: D.intake_review.meetings.map(m=>m.title==='Weekly sync 12'?{...m,level:undefined}:m)}; irTick.value++; })()")
        self.assertEqual(b.eval("irReady().length"), n - 1)
        self.assertEqual(b.eval("irSkipped().map(m=>m.title)"), ["Weekly sync 12"])

    def test_an_explicit_process_on_a_likely_row_still_works(self):
        b = self.b
        self.stage_stub()
        self.patch("Weekly sync 12", level="likely")
        b.click(self.sel("Weekly sync 12", ' [data-ira="process"]'))
        b.wait("ASKED.length>=1", 40)
        self.assertTrue(any("Weekly sync" in q for q, _ in b.eval("ASKED")))

    def test_a_confidential_meeting_is_counted_never_named(self):
        b = self.b
        self.stage_stub()
        self.patch("Weekly sync 12", confidential=True, p=None, level="likely")
        b.wait("document.querySelector('[data-irleft]')")
        self.assertFalse(b.eval("!!document.querySelector('[data-irheld]') && /Weekly sync/.test(document.querySelector('[data-irheld]').textContent)"))
        self.assertNotIn("Weekly sync", b.eval("document.querySelector('[data-irleft]').textContent"))


if __name__ == "__main__":
    unittest.main()
