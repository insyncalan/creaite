"""#232-A (v2.5.0): creaite's rules on the Intake side of Intake and Review (the meetings part; 232-B adds the proposals part). In a real
browser, in all three views: a confidential meeting shows its title and times only (no project, organiser, place or Teams mark);
nobody is labelled a VIP; a project is named, never shown by its code; the Not needed and Later lists show a reason, not a code.

Run: python3 dev/tests/test_intake_review_rules.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ir_intake_support import IntakeBase  # noqa: E402

VIEWS = (("list", "[data-irv=list]"), ("board", "[data-irv=board]"), ("two", "[data-irv=two]"))


class MeetingRules(IntakeBase):
    shared_server = True

    def show(self, view):
        self.b.eval(f"document.querySelector('[data-irview={view}]').click()")
        self.b.wait(f"!!document.querySelector('[data-irv={view}]')")

    def test_a_confidential_meeting_shows_only_its_title_and_times(self):
        b = self.b
        self.patch("Busy", teams=True, organiser="Jane Doe", where="Room 4", p="ABC")        # even if the data carried more, the row would not show it
        self.show("list")
        text = b.eval(f"{self.row('Busy')}.innerText")
        self.assertIn("Busy", text)
        self.assertIn("08:30–09:00", text)
        for hidden in ("Jane Doe", "Room 4", "Teams", "Example Programme", "ABC"):
            self.assertNotIn(hidden, text, hidden)
        self.show("board")
        card = b.eval(f"{self.row('Busy')}.innerText")
        for hidden in ("Jane Doe", "Room 4", "Example Programme", "ABC"):
            self.assertNotIn(hidden, card, hidden)
        self.show("two")
        b.eval(f"{self.row('Busy')}.click()")
        b.wait("document.querySelector('[data-irdet]').textContent.includes('Busy')")
        det = b.eval("document.querySelector('[data-irdet]').innerText")
        for hidden in ("Jane Doe", "Room 4", "Example Programme", "ABC"):
            self.assertNotIn(hidden, det, hidden)

    def test_a_confidential_meeting_set_aside_keeps_no_project_in_the_lists(self):
        b = self.b
        self.press_aside("Busy")
        b.wait("D.intake_review.not_needed.some(x=>x.title==='Busy')", 20)
        self.unfold("not_needed")
        text = b.eval("document.querySelector('[data-irsec=not_needed]').innerText")
        self.assertIn("Busy", text)
        self.assertIn("Informal chat", text)
        self.assertNotIn("Example Programme", text)

    def press_aside(self, title):
        self.b.click(self.sel(title, ' [data-ira="notneeded"]'))
        self.b.click('#irAside [data-reason="Informal chat"]')

    def test_nobody_is_labelled_a_vip_in_any_view(self):
        b = self.b
        b.eval("(()=>{ D.vip = D.vip || {}; })()")
        for view, _ in VIEWS:
            self.show(view)
            self.assertNotRegex(b.eval("document.getElementById('v-intake-review').innerText"), r"(?i)\bvip\b", view)

    def test_a_project_is_named_never_its_code(self):
        b = self.b
        for view, _ in VIEWS:
            self.show(view)
            if view == "two":
                b.eval(f"{self.row('ABC Steering')}.click()")
                b.wait("document.querySelector('[data-irdet]').textContent.includes('ABC Steering')")
                lines = b.eval("[...document.querySelectorAll('[data-irdet] .why')].map(x=>x.innerText).join(' | ')")
            else:
                lines = b.eval(f"[...{self.row('ABC Steering')}.querySelectorAll('.why')].map(x=>x.innerText).join(' | ')")
            self.assertIn("Example Programme", lines, view)
            self.assertNotRegex(lines, r"\bABC\b", view)


if __name__ == "__main__":
    unittest.main()
