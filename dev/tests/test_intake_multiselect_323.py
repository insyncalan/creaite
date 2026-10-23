"""#323: Intake's tick boxes, the right-click menu for several meetings (Later, Not needed because ... with one Undo), Group by and the
Show choice (Alan, 23-10-2026: filter to just the meetings Waiting for the transcript). Real browser, live server.

Run: python3 dev/tests/test_intake_multiselect_323.py   (needs Google Chrome; skipped otherwise)"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ir_intake_support import IntakeBase  # noqa: E402


class MultiSelect(IntakeBase):
    shared_server = True

    def setUp(self):
        super().setUp()
        self.b.eval("irClearTicks(); irSetGroup('none'); irSetStateFilter('all'); 0")

    def ctx(self, title):
        self.b.eval(f"{self.row(title)}.dispatchEvent(new MouseEvent('contextmenu',{{bubbles:true,cancelable:true,clientX:200,clientY:200}}))")
        self.b.wait("!!document.querySelector('.cxmenu')")

    def menu_words(self):
        return self.b.eval("[...document.querySelectorAll('.cxmenu .pkopt')].map(x=>x.innerText.replace(/\\s+/g,' ').trim())")

    def tick(self, title):
        self.b.click(self.sel(title, " input.irtick"))

    def test_ticks_show_a_bar_and_a_right_click_on_a_ticked_row_acts_on_all(self):
        b = self.b
        self.tick("ABC Steering")
        self.tick("Busy")
        b.wait("document.querySelector('[data-irtickbar]') && /2 selected/.test(document.querySelector('[data-irtickbar]').innerText)")
        self.ctx("ABC Steering")
        words = self.menu_words()
        self.assertTrue(any(w.startswith("Later") and "2 meetings" in w for w in words), words)
        self.assertTrue(any(w.startswith("Not needed because") and "2 meetings" in w for w in words), words)
        self.assertFalse(any(w.startswith("Process") for w in words), words)          # Process is one meeting at a time

    def test_right_click_on_an_unticked_row_acts_on_that_row_alone(self):
        self.tick("ABC Steering")
        self.ctx("Weekly sync 12")
        words = self.menu_words()
        self.assertTrue(any(w.startswith("Process") for w in words), words)
        self.assertFalse(any("meetings" in w for w in words), words)

    def test_not_needed_with_a_reason_for_two_meetings_in_one_call_with_one_undo(self):
        b = self.b
        self.tick("ABC Steering")
        self.tick("Weekly sync 12")
        self.ctx("Weekly sync 12")
        b.eval("[...document.querySelectorAll('.cxmenu .pkopt')].find(x=>/^Not needed because/.test(x.innerText.trim())).click()")
        b.wait("[...document.querySelectorAll('.cxmenu .pkopt')].some(x=>x.innerText.trim()==='No decisions')")
        b.eval("[...document.querySelectorAll('.cxmenu .pkopt')].find(x=>x.innerText.trim()==='No decisions').click()")
        b.wait("D.intake_review.not_needed.length===2", 20)
        cleared = self.cleared()
        self.assertEqual(len(cleared), 2)
        self.assertEqual({c.get("reason") for c in cleared}, {"No decisions"})
        self.assertEqual(b.eval("irTicked.value.length"), 0)
        b.wait("!D.intake_review.meetings.some(m=>m.title==='Weekly sync 12')", 20)
        b.wait("/Not needed: 2 meetings/.test(document.getElementById('snackT').textContent)")
        b.click("#snackU")                                                                 # one Undo brings both back
        b.wait("D.intake_review.not_needed.length===0 && D.intake_review.meetings.some(m=>m.title==='Weekly sync 12')", 20)
        self.assertEqual(self.cleared(), [])

    def test_group_by_day_state_and_show_waiting_for_the_transcript(self):
        b = self.b
        b.eval("irSetGroup('state')")
        b.wait("!!document.querySelector('[data-irgroup=waiting]')")
        heads = b.eval("[...document.querySelectorAll('tr.icgrouphd')].map(x=>x.innerText.replace(/\\s+/g,' ').trim())")
        self.assertTrue(heads[0].startswith("Waiting for the transcript"), heads)
        self.assertTrue(any(h.startswith("Transcript ready") for h in heads), heads)
        b.eval("irSetGroup('day')")
        b.wait("!!document.querySelector('tr.icgrouphd[data-irgroup]')")
        self.assertTrue(b.eval("document.querySelectorAll('tr.icgrouphd').length") >= 1)
        b.eval("irSetGroup('none')")
        b.wait("!document.querySelector('tr.icgrouphd')")
        b.eval("irSetStateFilter('waiting')")
        b.wait("document.querySelectorAll('#v-intake-review tr.irmeet').length===1")
        self.assertEqual(b.eval("document.querySelector('#v-intake-review tr.irmeet').dataset.state"), "waiting")
        self.assertEqual(b.eval("document.querySelector('[data-irshow]').value"), "waiting")


if __name__ == "__main__":
    unittest.main()
