"""BL-157: the fixes the one-off UX sweep made (each under an hour): an empty Activity and an empty Projects page say what to do
next, Quick capture's unsent note survives a reload, and Activity no longer sends Alan to Claude Code for an older apply. Also
checks the UX baseline is written down in dev/BUILD.md. A real browser against the real live server.

Run: python3 dev/tests/test_ux_sweep_fixes.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


class UxSweepFixes(LiveBrowserCase):
    def test_empty_pages_say_what_to_do_next(self):
        b = self.b
        b.eval("ACT.length=0; go('activity')")
        self.assertIn("Nothing has changed yet", b.eval("$('#actTbl').textContent"))
        b.eval("P.length=0; go('projects')")
        self.assertTrue(b.eval("!!document.querySelector('#projTbl [data-setup=\"proj\"]')"))
        self.assertIn("No projects yet", b.eval("$('#projTbl').textContent"))

    def test_activity_never_sends_alan_to_claude_code(self):
        b = self.b
        b.eval("go('activity')")
        self.assertNotIn("Claude Code", b.eval("$('#actTbl').textContent"))
        self.assertNotIn("undo last apply", b.eval("$('#actTbl').textContent"))

    def test_quick_capture_keeps_an_unsent_note(self):
        b = self.b
        b.eval("openCapture()")
        b.pump(0.2)
        b.eval("$('#qcNotes').focus()")
        b.type("Agreed with Sara: UAT booked by Friday")
        b.pump(0.5)
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        b.eval("go('inbox')")
        b.pump(0.3)
        self.assertEqual(b.eval("$('#qcNotes').value"), "Agreed with Sara: UAT booked by Friday")
        b.eval("$('#qcCancel').click()")                                       # Clear forgets it
        b.pump(0.2)
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        self.assertEqual(b.eval("$('#qcNotes').value"), "")

    def test_the_baseline_is_written_down(self):
        build = (ROOT / "dev/BUILD.md").read_text(encoding="utf-8")
        self.assertIn("### UX baseline", build)
        for n in range(1, 11):
            self.assertIn(f"\n{n}. ", build[build.index("### UX baseline"):])
        self.assertIn("UX baseline", (ROOT / "dev/sprints/TEMPLATE.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
