"""#264 in real Chrome: Intake's Process stages the ticked files and they reach Review, with no go-ahead and without opening ask
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

    def open_intake(self):
        self.b.eval("go('inbox')")
        self.b.wait("document.querySelectorAll('#inboxTbl tr[data-inf]').length>=4")

    def state(self, name):
        return self.b.eval(f"(()=>{{ const tr=[...document.querySelectorAll('#inboxTbl tr[data-inf]')].find(t=>t.dataset.inf.endsWith({name!r})); "
                           f"return tr?tr.cells[6].innerText.trim():''; }})()")

    @needs_diff
    def test_process_on_the_three_sample_files_ends_in_review_with_no_go_ahead(self):
        self.open_intake()
        self.b.eval("INSEL.clear(); D.inbox.filter(f=>/Pilot readiness|Supplier checkpoint|Budget review minutes/.test(f.name))"
                    ".forEach(f=>INSEL.add(f.path)); renderInbox()")
        self.assertEqual(self.b.eval("document.getElementById('inboxGo').textContent"), "Process 3 selected")
        self.b.click("#inboxGo")
        self.b.wait("[...document.querySelectorAll('#inboxTbl tr[data-inf]')].filter(t=>/Pilot readiness|Supplier checkpoint|Budget review "
                    "minutes/.test(t.dataset.inf)&&/Draft ready/.test(t.cells[6].innerText)).length===3",
                    timeout=90)
        self.assertFalse(self.b.eval("document.getElementById('chat').classList.contains('on')"))   # the panel stayed shut
        self.assertEqual(self.b.eval("document.querySelectorAll('#chLog .confirm').length"), 0)                  # no go-ahead card
        self.assertIsNone(self.b.eval("RUN"))
        self.b.eval("go('review')")
        self.b.wait("document.body.innerText.includes('Pilot readiness review')", timeout=20)

    @needs_diff
    def test_a_question_is_on_its_row_and_ask_creaite_opens_only_when_asked(self):
        self.open_intake()
        self.b.eval("INSEL.clear(); D.inbox.filter(f=>/Unclear/.test(f.name)).forEach(f=>INSEL.add(f.path)); renderInbox()")
        self.b.click("#inboxGo")
        self.b.wait("[...document.querySelectorAll('#inboxTbl tr[data-inf]')].some(t=>/Needs you/.test(t.cells[6].innerText))", timeout=90)
        self.assertIn("Which project is this meeting for?", self.state("Unclear call.vtt"))
        self.assertFalse(self.b.eval("(document.getElementById('chIn')||{}).value||''"))       # nothing typed for Alan yet
        self.b.eval("[...document.querySelectorAll('#inboxTbl tr[data-inf]')].find(t=>/Unclear/.test(t.dataset.inf)).querySelector('[data-inask]').click()")
        self.b.wait("(document.getElementById('chIn')||{}).value.includes('Which project is this meeting for?')")
        self.assertEqual(self.b.eval("document.querySelectorAll('#chLog .msg.u').length"), 0)   # filled in, never sent


if __name__ == "__main__":
    unittest.main(verbosity=2)
