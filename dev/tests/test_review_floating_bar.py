"""#114: Review's multi-select bar floats at the bottom edge of the window while rows are selected.

Run: python3 dev/tests/test_review_floating_bar.py   (needs Google Chrome; skipped otherwise)
Fixed at the bottom edge at 1400 and 900 px, still in the window after scrolling to the end, never over the last row, nothing in the
list moves when it appears or goes, keyboard reach, and Approve still follows the bulk rule.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_review_triage import load_queue  # noqa: E402

BAR = "(r=>({top:r.top,bottom:r.bottom,left:r.left,right:r.right}))(document.getElementById('rvbar').getBoundingClientRect())"


class FloatingBar(LiveBrowserCase):
    shared_server = False
    width, height = 1400, 640

    @classmethod
    def load(cls, v):
        populate(v)
        load_queue(v)

    def open_review(self, width):
        b = self.b
        b.resize(width, 640)
        b.eval("go('review')")
        b.wait("document.querySelector('#reviewBody tr[data-n]')")
        return b

    def select(self, ns):
        self.b.eval(f"RHL.clear(); {json.dumps(ns)}.forEach(n=>RHL.add(n)); rvSyncChk(); renderReview()")

    def check(self, width):
        b = self.open_review(width)
        top = b.eval("document.querySelector('#reviewBody tr[data-n]').getBoundingClientRect().top")
        ns = b.eval("REV.filter(r=>!r.done&&rvBulkOK(r)).map(r=>r.n)")
        self.assertGreater(len(ns), 8)
        last_n = b.eval("[...document.querySelectorAll('#reviewBody tr[data-n]')].pop().dataset.n")
        self.select([ns[0]])
        self.assertFalse(b.eval("document.getElementById('rvbar').hidden"))
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('rvbar')).position"), "fixed")
        self.assertEqual(top, b.eval("document.querySelector('#reviewBody tr[data-n]').getBoundingClientRect().top"))   # nothing moved
        # at the bottom edge, inside the window, at the top of the page and after scrolling to the end
        for scroll in ("0", "document.getElementById('v-review').scrollHeight"):
            b.eval(f"document.getElementById('v-review').scrollTop={scroll}")
            bar = b.eval(BAR)
            self.assertGreater(bar["bottom"], b.eval("innerHeight") - 40)
            self.assertLessEqual(bar["bottom"], b.eval("innerHeight"))
            self.assertGreaterEqual(bar["left"], 0)
            self.assertLessEqual(bar["right"], b.eval("innerWidth"))
        # the last row clears the bar
        last = b.eval("[...document.querySelectorAll('#reviewBody tr[data-n]')].pop().getBoundingClientRect().bottom")
        self.assertLessEqual(last, b.eval(BAR)["top"])
        # a row far down can be ticked and the bar is still there
        b.eval(f"document.querySelector('#reviewBody tr[data-n=\"{last_n}\"]').scrollIntoView()")
        self.assertGreater(b.eval(BAR)["bottom"], b.eval("innerHeight") - 40)
        # 24px targets, and the bar is reachable from the keyboard
        self.assertGreaterEqual(b.eval("document.getElementById('bulkApprove').getBoundingClientRect().height"), 24)
        self.assertTrue(b.eval("(()=>{ const a=document.getElementById('bulkApprove'); a.focus(); return document.activeElement===a; })()"))
        # clearing the selection hides it and gives the padding back
        self.select([])
        self.assertTrue(b.eval("document.getElementById('rvbar').hidden"))
        self.assertFalse(b.eval("document.getElementById('v-review').classList.contains('rvfloat')"))
        self.assertEqual(b.errors, [])

    def test_desktop(self):
        self.check(1400)

    def test_900(self):
        self.check(900)

    def test_approve_still_follows_the_bulk_rule(self):
        b = self.open_review(1400)
        info = b.eval("REV.filter(r=>!r.done).map(r=>({n:r.n,t:r.rec.t,ok:rvBulkOK(r)}))")
        routine = next(i for i in info if i["ok"])
        risk = next(i for i in info if i["t"].startswith("Scope creep"))
        self.select([routine["n"], risk["n"]])
        self.assertIn("1 can be approved together", b.eval("document.getElementById('rvSplit').textContent"))
        self.assertIn("Approve (1)", b.eval("document.getElementById('bulkApprove').textContent"))


if __name__ == "__main__":
    unittest.main()
