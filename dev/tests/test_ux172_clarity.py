"""#233 (UX review #172, findings 3 and 9): Review's bulk button is not a second Approve, and Intake's Process selected says why it is off.

Run: python3 dev/tests/test_ux172_clarity.py   (needs Google Chrome; skipped otherwise). Desktop width only.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402


class Clarity(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    def test_bulk_button_is_distinct_and_names_what_it_affects(self):
        b = self.b
        b.eval("go('review')")
        b.wait("document.querySelector('tr.mparent [data-act=ga]')")
        ga, ap = b.eval("(r=>[r.querySelector('[data-act=ga]'),r.querySelector('[data-act=a]')].map(e=>[e.className,e.textContent.trim()]))(document.querySelector('tr.mparent'))")
        self.assertNotIn("ok", ga[0].split(), "the bulk button wears the same green as Approve")
        self.assertNotEqual(ga[1], "Approve all from these minutes")
        self.assertRegex(ga[1], r"\d+ routine")                      # names what it affects: a count of routine items
        self.assertIn("ok", ap[0].split())

    def test_process_selected_says_why_it_is_off(self):
        b = self.b
        b.eval("go('inbox')")
        b.wait("document.getElementById('inboxGo')&&document.getElementById('mtgGo')")
        for i in ("inboxGo", "mtgGo"):
            off, title = b.eval(f"[document.getElementById('{i}').disabled,document.getElementById('{i}').title]")
            self.assertTrue(off)
            self.assertRegex(title, r"(?i)tick .*first", f"{i}: no hint while nothing is ticked")


if __name__ == "__main__":
    unittest.main()
