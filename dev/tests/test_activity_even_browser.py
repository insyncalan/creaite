"""#191 (UX review finding 16): Activity's Kind button and filter funnel are the same height and share a row's centre line,
and every row has a tick box (a row that cannot be undone has one too, disabled), so the list reads evenly.

Run: python3 dev/tests/test_activity_even_browser.py   (needs Google Chrome; skipped otherwise). Desktop width only.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

BOX = "(s=>{const r=document.querySelector(s).getBoundingClientRect(); return [r.top,r.height,r.width];})"


class ActivityEven(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    def test_kind_button_and_funnel_are_even(self):
        b = self.b
        b.eval("go('activity')")
        b.wait("!!document.querySelector('#actTypeBtn')&&!!document.querySelector('#actFunnel')")
        k, f = b.eval(f"[{BOX}('#actTypeBtn'),{BOX}('#actFunnel')]")
        self.assertAlmostEqual(k[1], f[1], delta=0.5, msg=f"heights differ: Kind {k[1]}, funnel {f[1]}")
        self.assertAlmostEqual(k[0], f[0], delta=0.5, msg=f"tops differ: Kind {k[0]}, funnel {f[0]}")

    def test_every_row_has_a_tick_box(self):
        b = self.b
        b.eval("go('activity')")
        b.wait("!!document.querySelector('#actTbl tr[data-row]')")
        b.eval("ACT.unshift({at:ACT[0].at,what:'Weekly update',change:'Weekly update',by:'creaite'}); renderActivity()")
        b.wait("document.querySelector('#actTbl tr:not([data-row]) td.actck')")
        rows, boxes = b.eval("[document.querySelectorAll('#actTbl tbody tr').length,"
                             "document.querySelectorAll('#actTbl tbody tr td.actck input[type=checkbox]').length]")
        self.assertGreater(rows, 1)
        self.assertEqual(rows, boxes)


if __name__ == "__main__":
    unittest.main()
