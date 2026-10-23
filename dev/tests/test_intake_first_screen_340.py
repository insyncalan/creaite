"""#340: the work to decide leads Intake. At 1400 and 900 px wide the first Approve (or, with none open, the first Check them) is inside
the first screen of the page scroller (section.view, not the window), the Arrived / Drafted / Approved / Show all strip is visible, and
the Arrived list comes after the work to decide. Group by, ticks and the right-click menu still work on the reordered list.

Run: python3 dev/tests/test_intake_first_screen_340.py   (needs Google Chrome; skipped otherwise)"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ir_intake_support import IntakeBase  # noqa: E402

FIRST = """(()=>{ const v=document.querySelector('#v-intake-review').closest('section.view')||document.querySelector('section.view.on'), vr=v.getBoundingClientRect();
  const ctl=document.querySelector('#v-intake-review tr.irprop [data-ira=approve]')||document.querySelector('#v-intake-review [data-ira=open]'), cr=ctl&&ctl.getBoundingClientRect();
  const strip=document.querySelector('#v-intake-review [data-irstage=all]').getBoundingClientRect();
  return {ctl: !!ctl, ctlBottom: cr?cr.bottom:null, viewBottom: Math.min(vr.bottom, innerHeight), stripBottom: strip.bottom, stripTop: strip.top, viewTop: vr.top, scroll: v.scrollHeight}; })()"""


class FirstScreen(IntakeBase):
    shared_server = True

    def check(self, width):
        b = self.b
        b.resize(width, 900)
        b.wait("!!document.querySelector('#v-intake-review [data-irstage=all]')")
        r = b.eval(FIRST)
        self.assertTrue(r["ctl"], r)
        self.assertLessEqual(r["ctlBottom"], r["viewBottom"], f"first approval below the first screen at {width}: {r}")
        self.assertGreaterEqual(r["stripTop"], r["viewTop"] - 1, r)
        self.assertLessEqual(r["stripBottom"], r["viewBottom"], r)

    def test_first_approval_in_the_first_screen_at_1400(self):
        self.check(1400)

    def test_first_approval_in_the_first_screen_at_900(self):
        self.check(900)

    def test_arrived_rows_come_after_the_work_to_decide(self):
        b = self.b
        order = b.eval("[...document.querySelectorAll('#v-intake-review tr.irmeet')].map(r=>r.dataset.stage)")
        ranks = {"drafted": 0, "approved": 1, "arrived": 2}
        self.assertEqual(order, sorted(order, key=lambda s: ranks[s]))
        self.assertTrue(b.eval("(()=>{ const m=document.querySelector('#v-intake-review [data-irsec=mail]'), a=document.querySelector('#v-intake-review [data-irpart=arrived]'); return !a || !m || !!(m.compareDocumentPosition(a) & Node.DOCUMENT_POSITION_FOLLOWING); })()"))

    def test_ticks_and_menu_still_work_when_reordered(self):
        b = self.b
        b.click(self.sel("Busy", " input.irtick"))
        b.wait("irTicked.value.length===1")
        b.eval(f"{self.row('Busy')}.dispatchEvent(new MouseEvent('contextmenu',{{bubbles:true,cancelable:true,clientX:200,clientY:200}}))")
        b.wait("!!document.querySelector('.cxmenu')")
        self.assertTrue(b.eval("[...document.querySelectorAll('.cxmenu .pkopt')].some(x=>/^Later/.test(x.innerText.trim()))"))


if __name__ == "__main__":
    unittest.main()
