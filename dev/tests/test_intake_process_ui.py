"""#264 in real Chrome (on #232's Intake page): a row's Process stages the file and they reach Review, with no go-ahead and without opening ask
creaite; a question the run couldn't answer is on its row ("Needs you"), and "ask creaite about this" opens the panel with the
question filled in, not sent.

Run: python3 dev/tests/test_intake_process_ui.py     (needs Google Chrome; skipped otherwise)
The real live server with test_intake_process's stand-in Claude (it stages through the real minutes.py stage). The tests are
expected failures until the guarded diffs in dev/proposals/intake-process/ are applied.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_intake_process import DAY, FAKE, VTT, needs_diff, put_samples  # noqa: E402


class IntakeProcessPage(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        put_samples(v)
        (v.root / f"inbox/{DAY} Unclear call.vtt").write_text(VTT.format(title="Unclear call"), encoding="utf-8")
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}

    ROW = "[...document.querySelectorAll('#v-intake-review [data-irv=list] tr[data-irm]')].find(t=>{pat}.test(t.querySelector('.icmeethd').textContent))"

    def row(self, pat):
        return self.ROW.format(pat=pat)

    def open_intake(self):
        """#232: Intake is one page (Intake and Review); each file is a row with its own Process."""
        self.b.eval("go('inbox')")
        self.b.wait(f"!!{self.row('/Pilot readiness/')}&&!!{self.row('/Supplier checkpoint/')}&&!!{self.row('/Unclear call/')}", timeout=30)

    def process(self, pat):
        self.b.wait(f"!!({self.row(pat)}||{{}}).querySelector&&!!{self.row(pat)}.querySelector('[data-ira=process]:not([disabled])')", timeout=30)
        self.b.eval(f"{self.row(pat)}.querySelector('[data-ira=process]').click()")

    @needs_diff
    def test_process_on_the_three_sample_files_ends_in_review_with_no_go_ahead(self):
        """The two sample transcripts, one after the other (since #232 someone else's minutes are read in ask creaite, E1, so the
        minutes sample is not one of them): each ends drafted, with no go-ahead and the panel shut."""
        self.open_intake()
        for pat in ("/Pilot readiness/", "/Supplier checkpoint/"):
            self.process(pat)
            self.b.wait(f"({self.row(pat)}||{{dataset:{{}}}}).dataset.stage==='drafted'", timeout=90)
        self.assertFalse(self.b.eval("document.getElementById('chat').classList.contains('on')"))   # the panel stayed shut
        self.assertEqual(self.b.eval("document.querySelectorAll('#chLog .confirm').length"), 0)                  # no go-ahead card
        self.assertIsNone(self.b.eval("RUN"))
        self.b.wait("document.body.innerText.includes('Pilot readiness review')", timeout=20)

    @needs_diff
    def test_a_question_is_on_its_row_and_ask_creaite_opens_only_when_asked(self):
        self.open_intake()
        self.process("/Unclear call/")
        self.b.wait(f"!!({self.row('/Unclear call/')}||{{querySelector:()=>null}}).querySelector('[data-ira=askabout]')", timeout=90)
        self.assertIn("Which project is this meeting for?", self.b.eval(f"{self.row('/Unclear call/')}.querySelector('.irnote').innerText"))
        self.assertFalse(self.b.eval("(document.getElementById('chIn')||{}).value||''"))       # nothing typed for Alan yet
        self.b.eval(f"{self.row('/Unclear call/')}.querySelector('[data-ira=askabout]').click()")
        self.b.wait("(document.getElementById('chIn')||{}).value.includes('Which project is this meeting for?')")
        self.assertEqual(self.b.eval("document.querySelectorAll('#chLog .msg.u').length"), 0)   # filled in, never sent


if __name__ == "__main__":
    unittest.main(verbosity=2)
