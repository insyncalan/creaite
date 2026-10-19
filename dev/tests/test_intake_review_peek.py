"""#232-B (v2.5.0): a mail or Teams proposal opens in the peek (the app's right-hand panel) from Intake and Review: an editable title,
the key fields by kind (Status for an update; Impact and Likelihood for a risk), Reject, Cancel, Save and Save and approve, previous and
next over the proposals on the page. Esc closes the peek first, then the open meeting. Nothing reaches the tracker until it is approved.

Run: python3 dev/tests/test_intake_review_peek.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intake_review_support as S  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

ROW = "#v-intake-review tr.irprop"


def click_row(b, text):
    """Click a proposal row's title, as a person would."""
    b.eval(f"[...document.querySelectorAll('{ROW}')].find(t=>t.querySelector('.icttl').textContent.includes({text!r})).querySelector('.icttl').click()")


def click_kind(b, pill):
    b.eval(f"[...document.querySelectorAll('{ROW}')].find(t=>t.querySelector('.ickind').textContent==={pill!r}).querySelector('.icttl').click()")


class PeekReadOnly(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        S.load(v)

    def test_fields_by_kind(self):
        b = self.b
        S.open_page(b)
        click_row(b, "Supplier may miss")
        b.wait("document.getElementById('panel').classList.contains('on') && document.getElementById('panel').classList.contains('pkprop')")
        panel = b.eval("document.getElementById('panel').textContent")
        for label in ("Impact", "Likelihood"):
            self.assertIn(label, panel)
        self.assertTrue(b.eval("!!document.querySelector('#pkTitle[contenteditable]')"))
        self.assertEqual(b.eval("[...document.querySelectorAll('#pkFoot2 button')].map(x=>x.textContent.trim())"), ["Reject", "Cancel", "Save", "Save and approve"])
        b.eval("closePanel()")
        click_kind(b, "Update")
        b.wait("document.getElementById('panel').classList.contains('on') && /Status/.test(document.getElementById('panel').textContent)")
        self.assertNotIn("Proposed value", b.eval("document.getElementById('panel').textContent"))

    def test_prev_next_step_through_the_proposals(self):
        b = self.b
        S.open_page(b)
        first = b.eval(f"[...document.querySelectorAll('{ROW}')].find(t=>t.dataset.kind!=='update').querySelector('.icttl').textContent")
        click_row(b, first)
        b.wait("document.getElementById('panel').classList.contains('pkprop')")
        self.assertTrue(b.eval("document.getElementById('pkPrev').disabled"))                 # the first on the page
        self.assertFalse(b.eval("document.getElementById('pkNext').disabled"))
        b.click("#pkNext")
        b.wait(f"!document.getElementById('pkTitle').textContent.includes({first!r})")
        self.assertFalse(b.eval("document.getElementById('pkPrev').disabled"))
        b.click("#pkPrev")
        b.wait(f"document.getElementById('pkTitle').textContent.includes({first!r})")

    def test_esc_closes_the_peek_first_then_the_meeting(self):
        b = self.b
        S.open_meeting(b)
        click_row(b, "Steering action 0")
        b.wait("document.getElementById('panel').classList.contains('on')")
        b.key("Escape")
        b.wait("!document.getElementById('panel').classList.contains('on')")
        self.assertIsNotNone(b.eval("irOpen.value"))                           # the meeting is still open
        b.key("Escape")
        b.wait("irOpen.value===null")


class PeekApproves(LiveBrowserCase):
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        S.load(v)

    def test_save_and_approve(self):
        b = self.b
        S.open_page(b)
        click_row(b, "Confirm data residency")
        b.wait("document.getElementById('panel').classList.contains('pkprop')")
        self.assertFalse(any(r["description"] == "Confirm data residency with legal" for r in self.v.rows("actions")))   # nothing yet
        b.click("#pkPSaveA")
        b.wait("!document.querySelector('#v-intake-review tr.irprop .icttl') || ![...document.querySelectorAll('#v-intake-review tr.irprop .icttl')].some(x=>x.textContent.includes('Confirm data residency'))", 25)
        b.wait("document.querySelectorAll('#v-intake-review tr.irprop').length>=0", 5)
        end = time.time() + 20
        while time.time() < end and not any(r["description"] == "Confirm data residency with legal" for r in self.v.rows("actions")):
            time.sleep(0.3)                                                            # the apply follows the decision
        self.assertIn("Confirm data residency with legal", [r["description"] for r in self.v.rows("actions")])

    def test_reject_with_a_reason_from_the_row(self):
        b = self.b
        S.open_page(b)
        b.eval(f"[...document.querySelectorAll('{ROW}')].find(t=>t.querySelector('.icttl').textContent.includes('Supplier may miss')).querySelector('[data-ira=reject]').click()")
        b.wait("!!document.getElementById('rvReason')")
        b.key("0")
        b.wait(f"![...document.querySelectorAll('{ROW} .icttl')].some(x=>x.textContent.includes('Supplier may miss'))", 25)
        self.assertFalse(any(r["description"].startswith("Supplier may miss") for r in self.v.rows("raid")))


if __name__ == "__main__":
    unittest.main()
