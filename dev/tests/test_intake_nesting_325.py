"""#325: Intake's state chip (Waiting for the transcript, Suggestions to check, Done) and the work items nested under their minutes.
The chip and the stage boxes read one definition (irMeetingState); the nested rows keep their own file-plus-item key (#307); a held
parent says so on its children; the parent folds by mouse and keyboard, remembered for the session only.

Run: python3 dev/tests/test_intake_nesting_325.py   (needs Google Chrome; skipped otherwise)"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ir_intake_support import IntakeBase  # noqa: E402


class Nesting(IntakeBase):
    shared_server = True

    def setUp(self):
        super().setUp()
        self.b.eval("irKidsFold.value={}; irSetGroup('none'); irSetStateFilter('all'); 0")

    def chip(self, title):
        return self.b.eval(f"(()=>{{ const c={self.row(title)}.querySelector('[data-irchip]'); return c ? [c.dataset.irchip, c.innerText.trim()] : null; }})()")

    def test_each_meeting_has_one_chip_matching_the_stage_boxes(self):
        b = self.b
        self.assertEqual(self.chip("Busy")[0], "waiting")
        self.assertEqual(self.chip("Busy")[1], "Waiting for the transcript")
        self.assertIsNone(self.chip("Weekly sync 12"))                                  # transcript ready: its own words, no chip
        chips = b.eval("[...document.querySelectorAll('#v-intake-review tr.irmeet [data-irchip]')].map(c=>c.dataset.irchip)")
        counts = b.eval("irLiveCounts()")
        self.assertEqual(chips.count("check"), counts["drafted"])
        self.assertEqual(chips.count("done"), counts["approved"])
        self.assertEqual(b.eval("[...document.querySelectorAll('#v-intake-review tr.irmeet')].filter(r=>r.querySelectorAll('[data-irchip]').length>1).length"), 0)
        self.assertEqual(b.eval("irLiveCounts().arrived"), b.eval("D.intake_review.meetings.filter(m=>irStateOf(m,irDone)==='waiting'||irStateOf(m,irDone)==='ready').length"))
        word = b.eval("(()=>{ const c=document.querySelector('#v-intake-review [data-irchip=check]'); return c ? c.innerText.trim() : ''; })()")
        self.assertRegex(word, r"^Suggestions to check · \d+$")

    def test_the_chip_never_relies_on_colour_alone(self):
        b = self.b
        self.assertTrue(b.eval("(()=>{ const c=document.querySelector('#v-intake-review [data-irchip]'); return !!c.querySelector('svg') && c.innerText.trim().length>3; })()"))

    def test_work_items_are_nested_under_the_minutes_and_fold(self):
        b = self.b
        b.eval("document.querySelector('#v-intake-review [data-irm=\"' + D.intake_review.meetings.find(m=>m.stage==='drafted').id + '\"]').click()")
        b.wait("!!document.querySelector('#v-intake-review tr.irprop')")
        parents = b.eval("document.querySelectorAll('#v-intake-review tr.irparent').length")
        if not parents:
            self.skipTest("the fixture has no draft minutes to nest under")
        kids = b.eval("document.querySelectorAll('#v-intake-review tr.irkid.irprop').length")
        self.assertGreater(kids, 0)
        self.assertIn(f"{kids} item", b.eval("document.querySelector('#v-intake-review tr.irparent').innerText"))
        # each child keeps its own key (#307): its row number maps back to a distinct proposal
        ns = b.eval("[...document.querySelectorAll('#v-intake-review tr.irkid.irprop')].map(r=>r.dataset.irn)")
        self.assertEqual(len(ns), len(set(ns)))
        b.click("#v-intake-review tr.irparent [data-ira=kids]")
        b.wait("document.querySelectorAll('#v-intake-review tr.irkid').length===0")
        self.assertEqual(b.eval("document.querySelector('#v-intake-review tr.irparent').getAttribute('aria-expanded')"), "false")
        b.eval("(()=>{ const r=document.querySelector('#v-intake-review tr.irparent'); r.focus(); r.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true})); })()")
        b.wait("document.querySelectorAll('#v-intake-review tr.irkid.irprop').length>0")
        b.eval("(()=>{ const r=document.querySelector('#v-intake-review tr.irparent'); r.focus(); r.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowLeft',bubbles:true})); })()")
        b.wait("document.querySelectorAll('#v-intake-review tr.irkid').length===0")
        self.assertEqual(b.eval("Object.values(irKidsFold.value).filter(Boolean).length"), 1)    # kept for the session, in memory only
        self.assertIsNone(b.eval("localStorage.getItem('creaite-ir-kids')"))


if __name__ == "__main__":
    unittest.main()
