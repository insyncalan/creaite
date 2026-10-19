"""#232-A (v2.5.0): the Intake keys on Intake and Review, in a real browser: Enter processes the meeting with focus when its
transcript is ready (and opens or closes one with proposals), N asks why it is Not needed (a number picks the reason), H sets it
aside for Later. They are bound by the page (IntakeReviewPage.jsx), not core/keys.js, and stay out of a text field, a menu, a
modified key and a meeting with nothing to set aside. The Review side's keys (arrows, Esc) are test_intake_review_keys_review.py.

Run: python3 dev/tests/test_intake_review_keys_intake.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ir_intake_support import IntakeBase  # noqa: E402


class IntakeKeys(IntakeBase):
    shared_server = True

    def press(self, title, k, **mods):
        opts = json.dumps({"key": k, "bubbles": True, **mods})
        self.b.eval(f"(()=>{{ const r={self.row(title)}; r.focus(); r.dispatchEvent(new KeyboardEvent('keydown',{opts})); }})()")

    def test_enter_processes_a_ready_meeting_then_opens_it(self):
        b = self.b
        self.stage_stub()
        self.press("ABC Steering", "Enter")
        b.wait(f"{self.row('ABC Steering')}.dataset.stage==='drafted'", 30)
        self.assertEqual([q for q, _ in b.eval("ASKED")], ["process inbox/2026-10-05 ABC Steering.vtt"])
        self.press("ABC Steering", "Enter")                                   # now it has proposals: Enter opens it
        b.wait("irOpen.value===%s.dataset.irm" % self.row("ABC Steering"))
        self.press("ABC Steering", "Enter")
        b.wait("irOpen.value===null")
        self.assertEqual(len(b.eval("ASKED")), 1)                             # and never processed twice

    def test_n_asks_a_reason_and_a_number_picks_it(self):
        b = self.b
        self.press("Weekly sync 12", "n")
        b.wait("!!document.querySelector('#irAside')")
        self.assertEqual(b.eval("document.querySelectorAll('#irAside [data-reason]').length"), 4)
        b.eval("document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'2',bubbles:true}))")
        b.wait("D.intake_review.not_needed.some(x=>x.title==='Weekly sync 12' && x.reason==='No decisions')", 20)
        self.assertFalse(b.eval("!!document.querySelector('#irAside')"))

    def test_esc_closes_the_reasons_menu_and_nothing_is_set_aside(self):
        b = self.b
        self.press("Weekly sync 12", "N")
        b.wait("!!document.querySelector('#irAside')")
        b.eval("document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")
        b.wait("!document.querySelector('#irAside')")
        self.assertEqual(self.cleared(), [])

    def test_h_sets_a_meeting_aside_for_later(self):
        b = self.b
        self.press("Busy", "h")
        b.wait("D.intake_review.later.some(x=>x.title==='Busy')", 20)
        self.assertEqual([(e["key"], e.get("kind")) for e in self.cleared()], [("ev-3", "later")])

    def test_keys_wait_in_a_field_with_a_modifier_and_on_a_meeting_with_proposals(self):
        b = self.b
        self.stage_stub()
        self.press("Weekly sync 12", "h", metaKey=True)                       # ⌘H is the browser's
        self.press("Weekly sync 12", "n", ctrlKey=True)
        b.eval(f"(()=>{{ const i=document.createElement('input'); i.id='irTmp'; {self.row('Weekly sync 12')}.querySelector('td.title').appendChild(i); i.focus(); "
               "i.dispatchEvent(new KeyboardEvent('keydown',{key:'h',bubbles:true})); i.remove(); })()")
        b.pump(1)
        self.assertEqual(self.cleared(), [])
        self.assertFalse(b.eval("!!document.querySelector('#irAside')"))
        mid = b.eval("D.intake_review.meetings.find(m=>m.src==='draft' && m.stage==='drafted').id")      # the sample's draft: proposals to check
        b.eval(f"(()=>{{ const r=document.querySelector('[data-irm=\"{mid}\"]'); r.focus(); "
               "r.dispatchEvent(new KeyboardEvent('keydown',{key:'h',bubbles:true})); r.dispatchEvent(new KeyboardEvent('keydown',{key:'n',bubbles:true})); })()")
        b.pump(1)
        self.assertEqual(self.cleared(), [])
        self.assertFalse(b.eval("!!document.querySelector('#irAside')"))


if __name__ == "__main__":
    unittest.main()
