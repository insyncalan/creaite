"""#232-B (v2.5.0): the Review side's keys on Intake. Up and down move between the proposals of the open meeting (and the
mail section), Enter opens the peek, A approves, R opens the reasons menu; Esc closes the peek first and then the meeting. The old
Review's keys (J, K, Space, X, E) are not bound on this page.

Run: python3 dev/tests/test_intake_review_keys_review.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intake_review_support as S  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

ROW = "#v-intake-review tr.irprop"


class KeysReview(LiveBrowserCase):
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        S.load(v)

    def focus_first(self):
        b = self.b
        S.open_meeting(b)
        b.eval(f"document.querySelector('{ROW}').focus()")
        b.wait(f"document.activeElement===document.querySelector('{ROW}')")

    def test_arrows_move_between_proposals(self):
        b = self.b
        self.focus_first()
        first = b.eval("document.activeElement.dataset.irn")
        b.key("ArrowDown")
        b.wait(f"document.activeElement.matches('{ROW}') && document.activeElement.dataset.irn!=={first!r}")
        second = b.eval("document.activeElement.dataset.irn")
        b.key("ArrowUp")
        b.wait(f"document.activeElement.dataset.irn==={first!r}")
        self.assertNotEqual(first, second)
        self.assertEqual(b.eval("irOpen.value!==null"), True)                  # the meeting did not lose its place to the meeting-level arrows

    def test_enter_opens_the_peek_and_esc_closes_it_before_the_meeting(self):
        b = self.b
        self.focus_first()
        b.eval(f"document.querySelectorAll('{ROW}')[1].focus()")
        b.key("Enter")
        b.wait("document.getElementById('panel').classList.contains('on')")
        b.key("Escape")
        b.wait("!document.getElementById('panel').classList.contains('on')")
        self.assertIsNotNone(b.eval("irOpen.value"))
        b.key("Escape")
        b.wait("irOpen.value===null")

    def test_a_approves_the_focused_proposal_and_r_opens_the_reasons_menu(self):
        b = self.b
        S.open_page(b)
        b.eval(f"[...document.querySelectorAll('{ROW}')].find(t=>t.querySelector('.icttl').textContent.includes('Supplier may miss')).focus()")
        b.key("r")
        b.wait("!!document.getElementById('rvReason')")
        b.key("Escape")
        b.wait("!document.getElementById('rvReason')")
        b.eval(f"[...document.querySelectorAll('{ROW}')].find(t=>t.querySelector('.icttl').textContent.includes('Confirm data residency')).focus()")
        b.key("a")
        end = time.time() + 25
        while time.time() < end and not any(r["description"] == "Confirm data residency with legal" for r in self.v.rows("actions")):
            time.sleep(0.3)
        self.assertIn("Confirm data residency with legal", [r["description"] for r in self.v.rows("actions")])

    def test_the_old_review_keys_do_nothing_here(self):
        b = self.b
        self.focus_first()
        before = b.eval("[RHL.size, REV.filter(r=>r.done).length]")
        for k in ("j", "k", "x", " "):
            b.key(k)
        self.assertEqual(b.eval("[RHL.size, REV.filter(r=>r.done).length]"), before)


if __name__ == "__main__":
    unittest.main()
