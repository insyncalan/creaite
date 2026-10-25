"""#232 (2.6) review fix F1: a file dropped in inbox/ while Intake is open gets its row at once, not only after a full reload.

The quick file refresh (refreshFiles) brings D.inbox but not the Intake model, so the header, the rail badge and Process all ready
counted the file while the list did not. Now irModelBehind() counts a waiting file the model lacks, refreshFiles() and opening
Intake (go) and the window's focus on Intake all read the inbox again, and the page reloads the data when the model is behind.

Run: python3 dev/tests/test_intake_review_fresh_files.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ir_intake_support import IntakeBase  # noqa: E402

NAME = "Dropped notes.vtt"
VTT = "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nHello\n"
ROWS = "document.querySelectorAll('#v-intake-review [data-irm]').length"
HAS = "(D.intake_review.meetings||[]).some(m=>m.path==='inbox/Dropped notes.vtt')"


class FreshFile(IntakeBase):
    shared_server = True

    def setUp(self):
        super().setUp()
        self.b.eval("evClose()")           # the server's change events would also refresh the files: these tests are about the page's own reads
        self.b.wait("!shared.FBUSY")       # opening Intake read the file list once already: let that finish

    def tearDown(self):
        (self.v.root / "inbox" / NAME).unlink(missing_ok=True)
        super().tearDown()

    def drop(self):
        (self.v.root / "inbox" / NAME).write_text(VTT)

    def numbers(self):
        return self.b.eval("""(()=>{ const c=irLiveCounts(); return {badge:c.badge, ready:c.ready, rows:%s, rail:document.getElementById('revBadge').textContent.trim(),
          all:[...document.querySelectorAll('#v-intake-review button')].map(x=>x.textContent.trim()).find(t=>/^Process all ready/.test(t))||''}; })()""" % ROWS)

    def test_refreshing_the_files_on_intake_draws_the_new_row(self):
        b = self.b
        before = self.numbers()
        self.drop()
        b.eval("refreshFiles(true)")
        b.wait(f"{HAS} && !!document.querySelector('#v-intake-review [data-irm]')")
        after = self.numbers()
        self.assertEqual(after["rows"], before["rows"] + 1, (before, after))                  # the row, not only the counts
        self.assertEqual(after["ready"], before["ready"] + 1)
        self.assertEqual(after["badge"], before["badge"] + 1)
        self.assertEqual(after["rail"], str(after["badge"]))
        skipped = b.eval("irSkipped().length")                                                   # #328: a meeting with only a guessed project waits for a pick
        self.assertIn(str(after["ready"] - skipped), after["all"])                               # the button counts it too

    def test_the_model_is_behind_while_a_file_waits_and_not_once_it_is_drawn(self):
        b = self.b
        self.assertFalse(b.eval("irModelBehind()"))
        self.drop()
        b.eval("refreshFiles(true)")
        b.wait(HAS)
        self.assertFalse(b.eval("irModelBehind()"))                                              # the model has it: no reload loop
        b.eval("D.intake_review={...D.intake_review, meetings: D.intake_review.meetings.filter(m=>m.path!=='inbox/Dropped notes.vtt')}")
        self.assertTrue(b.eval("irModelBehind()"))                                               # without its row the model is behind

    def test_opening_intake_reads_the_inbox_again(self):
        b = self.b
        b.eval("go('today')")
        self.drop()
        b.eval("go('intake-review')")
        b.wait(f"{HAS} && !!document.querySelector('#v-intake-review [data-irm]')")
        self.assertEqual(b.eval("irModelBehind()"), False)
        self.assertGreaterEqual(b.eval(ROWS), 1)

    def test_focusing_the_window_on_intake_reads_the_inbox_again(self):
        b = self.b
        b.eval("window.__asked=0; const of=window.fetch; window.fetch=(u,...a)=>{ if(String(u).includes('/api/files')) window.__asked++; return of(u,...a); }")   # counts the file list reads as they start
        b.eval("shared.FLAST=0")                                                                # past the ten-second pause
        self.drop()
        b.eval("window.dispatchEvent(new Event('focus'))")
        self.assertEqual(b.eval("window.__asked"), 1)                                           # the focus itself started the read, not something later
        b.wait(HAS)

    def test_a_loaded_meetings_transcript_is_not_a_fresh_file(self):
        b = self.b
        self.assertEqual(b.eval("irFreshFiles().fresh.length"), 0)
        b.eval("D.inbox=[...D.inbox,{state:'new',name:'x.vtt',path:'inbox/x.vtt',ft:'transcript',event:'ev-9'}]")
        self.assertEqual(b.eval("irFreshFiles().fresh.length"), 0)


if __name__ == "__main__":
    unittest.main()
