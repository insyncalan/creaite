"""#264 in real Chrome, on 2.6's one Intake page (#232): Process stages the files and they reach Review, with no go-ahead and
without opening ask creaite; a question the run couldn't answer is on its row ("Needs you"), and "ask creaite about this" opens
the panel with the question filled in, not sent. (2.5.3 drove the old Intake page's upload table, retired in 2.6.0 C2.)

Run: python3 dev/tests/test_intake_process_ui.py     (needs Google Chrome; skipped otherwise)
The real live server with test_intake_process's stand-in Claude (it stages through the real minutes.py stage, under the real
guard hook's mode "process").
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_intake_process import BUDGET, DAY, FAKE, PILOT, SUPPLIER, VTT, needs_diff, put_samples  # noqa: E402

UNCLEAR = f"inbox/{DAY} Unclear call.vtt"
SAMPLES = [f"inbox/{n}" for n in (PILOT, SUPPLIER, BUDGET)]


class IntakeProcessPage(LiveBrowserCase):
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        for f in (v.root / "inbox").glob("*"):
            f.unlink()                       # only the three sample files and the unclear call are ready rows
        put_samples(v)
        (v.root / UNCLEAR).write_text(VTT.format(title="Unclear call"), encoding="utf-8")
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}

    def open_intake(self):
        self.b.eval("irSetView('list'); irStage.value='all'; reloadData().then(()=>go('intake-review'))")
        self.b.wait("VIEW==='intake-review' && " + " && ".join(
            f"D.intake_review.meetings.some(m=>m.path==={json.dumps(p)})" for p in [*SAMPLES, UNCLEAR]), 20)
        # the stand-in drafts minutes from each file, so the minutes-looking sample is processed as a transcript here
        self.b.eval(f"irSetFileKind(D.intake_review.meetings.find(m=>m.path==={json.dumps(SAMPLES[2])}),'transcript'); irTick.value++; 0")

    def row(self, path):
        return ("document.querySelector('#v-intake-review [data-irm=\"' + D.intake_review.meetings.find(m=>m.path==="
                + json.dumps(path) + ").id + '\"]')")

    def press(self, path):
        mid = self.b.eval(f"D.intake_review.meetings.find(m=>m.path==={json.dumps(path)}).id")
        self.b.click(f'#v-intake-review [data-irm="{mid}"] [data-ira=process]')

    @needs_diff
    def test_process_on_the_three_sample_files_ends_in_review_with_no_go_ahead(self):
        """The two sample transcripts, one after the other (since #232 someone else's minutes are read in ask creaite, E1, so the
        minutes sample is not one of them): each ends drafted, with no go-ahead and the panel shut."""
        self.open_intake()
        for p in SAMPLES:
            self.press(p)
            self.b.wait("irBusy.value.length===0", 90)
        self.b.wait(" && ".join(f"!D.intake_review.meetings.some(m=>m.src==='upload'&&m.path==={json.dumps(p)}&&m.stage==='arrived')"
                                for p in SAMPLES), 30)
        self.assertFalse(self.b.eval("document.getElementById('chat').classList.contains('on')"))   # the panel stayed shut
        self.assertEqual(self.b.eval("document.querySelectorAll('#chLog .confirm').length"), 0)                  # no go-ahead card
        self.assertIsNone(self.b.eval("RUN"))
        self.assertTrue(self.b.eval("REV.some(r=>/Pilot readiness review/.test(JSON.stringify(r)))"))           # in Review

    @needs_diff
    def test_a_question_is_on_its_row_and_ask_creaite_opens_only_when_asked(self):
        self.open_intake()
        self.press(UNCLEAR)
        self.b.wait(f"!!{self.row(UNCLEAR)}.querySelector('[data-ira=askabout]')", 90)
        self.assertIn("Which project is this meeting for?", self.b.eval(f"{self.row(UNCLEAR)}.querySelector('.irnote').innerText"))
        self.assertFalse(self.b.eval("(document.getElementById('chIn')||{}).value||''"))       # nothing typed for Alan yet
        said = self.b.eval("document.querySelectorAll('#chLog .msg.u').length")
        self.b.eval(f"{self.row(UNCLEAR)}.querySelector('[data-ira=askabout]').click()")
        self.b.wait("(document.getElementById('chIn')||{}).value.includes('Which project is this meeting for?')")
        self.assertEqual(self.b.eval("document.querySelectorAll('#chLog .msg.u').length"), said)   # filled in, never sent


if __name__ == "__main__":
    unittest.main(verbosity=2)
