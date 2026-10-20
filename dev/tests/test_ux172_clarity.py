"""#233 (UX review #172, findings 3 and 9), after #232 C2 retired the pages they were about.

Run: python3 dev/tests/test_ux172_clarity.py   (needs Google Chrome; skipped otherwise). Desktop width only.

Finding 3 (Review's bulk button named what it affects) was about the old page's "Approve n routine" button on the minutes' row; on the Intake
page Approve routine sits in its group's heading and names its count. (The old test also asserted the bulk button was not the Approve green;
the new page's two buttons share a style: see the report on #232 C2.) Finding 9 (Process selected said why it was off) was about Calendar
import's buttons, which went with the old Intake page; Process all ready says the same on the new one.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402


class Clarity(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    def test_approve_routine_names_what_it_affects(self):
        b = self.b
        b.eval("go('intake-review')")
        b.wait("!!document.querySelector('#v-intake-review [data-irsec]')")
        text = b.eval("(e=>e?e.textContent.trim():null)(document.querySelector('#v-intake-review [data-ira=routine]'))")
        if text is None:
            self.skipTest("the sample vault has no routine group on Intake")
        self.assertRegex(text, r"Approve routine \(\d+\)")                      # a count of routine items

    def test_process_all_ready_says_why_it_is_off(self):
        b = self.b
        b.eval("go('intake-review')")
        b.wait("!!document.querySelector('#v-intake-review [data-ira=processall]')")
        off, title = b.eval("[document.querySelector('#v-intake-review [data-ira=processall]').disabled, document.querySelector('#v-intake-review [data-ira=processall]').title]")
        if not off:
            self.skipTest("the sample vault has something ready to process")
        self.assertRegex(title, r"(?i)nothing is ready|busy")                  # a dead button says why


if __name__ == "__main__":
    unittest.main()
