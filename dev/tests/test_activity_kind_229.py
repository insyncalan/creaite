"""#229 (UX review #172, finding 16): Activity has no Kind button beside the funnel (it read as two controls). The kind filter is
the funnel's field list (the shared FilterBar) with its applied chip; every row keeps its tick box.

Run: python3 dev/tests/test_activity_kind_229.py   (needs Google Chrome; skipped otherwise). Desktop width only.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402


class ActivityKind(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    def test_no_kind_button_and_the_funnel_filters_by_kind(self):
        b = self.b
        b.eval("go('activity')")
        b.wait("!!document.querySelector('#actFunnel')&&!!document.querySelector('#actTbl tr[data-row]')")
        self.assertFalse(b.eval("!!document.getElementById('actTypeBtn')"), "the Kind button is still there")
        total = b.eval("document.querySelectorAll('#actTbl tbody tr').length")
        b.click("#actFunnel")
        b.wait("!!document.querySelector('#actPick [role=option]')")
        b.click('#actPick [role=option]:has(input[value="Risk"])')
        b.wait("(shared.ACTF.types||[]).includes('Risk')")
        rows = b.eval("[...document.querySelectorAll('#actTbl tbody tr')].map(r=>(r.querySelector('.acticon')||{getAttribute:()=>''}).getAttribute('aria-label'))")
        self.assertTrue(rows)
        self.assertLess(len(rows), total)
        self.assertTrue(all(r == "Risk" for r in rows), rows)
        self.assertIn("type=Risk", b.eval("location.hash"))
        self.assertIn("Risk", b.eval("document.getElementById('actCount').textContent+document.getElementById('actFbar').textContent"))
        n, boxes = b.eval("[document.querySelectorAll('#actTbl tbody tr').length,document.querySelectorAll('#actTbl tbody tr td.actck input[type=checkbox]').length]")
        self.assertEqual(n, boxes)

    def test_funnel_keeps_the_row_even(self):
        b = self.b
        b.eval("go('activity')")
        b.wait("!!document.querySelector('#actFunnel')")
        q, f = b.eval("[...['#actQ','#actFunnel'].map(s=>{const r=document.querySelector(s).getBoundingClientRect(); return [r.top,r.height];})]")
        self.assertGreater(f[1], 0)
        self.assertAlmostEqual(f[1], 32, delta=2)


if __name__ == "__main__":
    unittest.main()
