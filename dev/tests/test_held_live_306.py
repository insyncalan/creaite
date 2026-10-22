"""#306 live (real headless Chrome): the two buttons for minutes whose transcript has gone.

Intake row "Approve without the transcript": the row leaves Intake, the counts move, the success words and Undo show; a failure
says "Not saved because ..." on the row and in a message. Minutes editor: Approve minutes says why in plain words with a
"File without the transcript copy" button; it says what was saved (with Undo), or why it was not.
Run: python3 dev/tests/test_held_live_306.py      (needs Google Chrome)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
import test_minutes_editor as me  # noqa: E402

ROW = '#v-intake-review tr.irprop[data-irn="%s"]'


def toast(b):
    return b.eval("(document.getElementById('toastHost')||{innerText:''}).innerText")


class IntakeHeld(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        cls.proposal = me.stage_meeting(v)
        (v.root / "inbox" / f"{me.DAY} Steering committee.vtt").unlink()

    def open_row(self):
        b = self.b
        b.wait("REV.some(x=>x.kind==='draft'&&!!x.held)", timeout=15)
        n = b.eval("REV.find(x=>x.kind==='draft'&&!!x.held).n")
        b.eval(f"go('intake-review', {n})")
        b.wait(f"!!document.querySelector('{ROW % n} [data-ira=held-approve]')", timeout=10)
        return n

    def test_a_failure_is_said_on_the_row(self):
        b = self.b
        n = self.open_row()
        b.eval("window.api=(p,o)=>Promise.resolve(p==='/api/review'?{ok:false,message:\"2: not approved — the minutes are open in Word\"}:{ok:true,message:''})")
        b.click(f"{ROW % n} [data-ira=held-approve]")
        b.wait("(document.getElementById('toastHost')||{innerText:''}).innerText.includes('Not saved because')", timeout=15)
        b.pump(0.5)
        b.wait("!!document.querySelector('#v-intake-review [data-ira=held-error]')", timeout=10)
        self.assertIn("Not saved because the minutes are open in Word", b.eval("document.querySelector('#v-intake-review [data-ira=held-error]').innerText"))
        self.assertTrue(b.eval("REV.some(x=>x.kind==='draft'&&!!x.held)"), "still on Intake, and it says why")

    def test_success_leaves_intake_and_says_what_was_saved(self):
        b = self.b
        n = self.open_row()
        b.click(f"{ROW % n} [data-ira=held-approve]")
        b.wait("(document.getElementById('toastHost')||{innerText:''}).innerText.includes('Approved without the transcript')", timeout=20)
        self.assertRegex(toast(b), r"Approved without the transcript: \d+ items? saved")
        self.assertIn("Undo", toast(b))
        b.wait("!REV.some(x=>x.kind==='draft'&&!!x.held)", timeout=10)
        self.assertFalse(b.eval(f"!!document.querySelector('{ROW % n}')"), "the row has left Intake")
        b.click("#toastHost button")
        b.wait("(document.getElementById('toastHost')||{innerText:''}).innerText.includes('Undone')", timeout=15)


class EditorHeld(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        cls.proposal = me.stage_meeting(v)
        (v.root / "inbox" / f"{me.DAY} Steering committee.vtt").unlink()

    def open(self):
        b = self.b
        b.eval(f"go('minutes',{{file:{json.dumps(self.proposal)}}})")
        b.wait("document.querySelector('#v-minutes tr.mi')", 15)
        b.pump(0.3)
        b.eval("document.getElementById('mnApproveBtn').click()")
        b.pump(0.5)
        if b.eval("!!document.getElementById('mnApproveGo')"):             # the Before approving box: approve anyway
            b.eval("document.getElementById('mnApproveGo').click()")
        b.wait("(document.getElementById('toastHost')||{innerText:''}).innerText.includes('File without the transcript copy')", timeout=20)
        t = toast(b)
        self.assertIn("the transcript is no longer in your inbox", t)
        for jargon in ("staged", "proposal", "inbox/", ".vtt"):
            self.assertNotIn(jargon, t)

    def test_file_without_the_transcript_copy_says_what_was_saved(self):
        b = self.b
        self.open()
        b.click("#toastHost button")
        b.wait("(document.getElementById('toastHost')||{innerText:''}).innerText.includes('Filed without the transcript copy')", timeout=25)
        self.assertRegex(toast(b), r"Filed without the transcript copy: \d+ items? saved")
        self.assertIn("Undo", toast(b))
        self.assertTrue(list(self.v.root.glob("projects/*/minutes/*Steering committee*")), "the minutes are filed")
        b.click("#toastHost button")
        b.wait("(document.getElementById('toastHost')||{innerText:''}).innerText.includes('Undone')", timeout=15)

    def test_a_failure_says_why(self):
        b = self.b
        self.open()
        (self.v.root / "system/staging" / self.proposal).unlink()          # nothing left to file
        b.click("#toastHost button")
        b.wait("(document.getElementById('toastHost')||{innerText:''}).innerText.includes('Not saved because')", timeout=20)


if __name__ == "__main__":
    unittest.main()
