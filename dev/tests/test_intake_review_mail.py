"""#232-B (v2.5.0): the mail and Teams proposals on Intake say what changes, in the same rows as a meeting's:
an update in words ("Closes ABC-A-014: Draft the comms plan · status Open → Closed · Looks done"; a changed latest update as "and the latest update") with its evidence and source; a new action or risk with
owner, date or impact; the same two groups; and the source line shows no times.

Run: python3 dev/tests/test_intake_review_mail.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intake_review_support as S  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

ROW = "#v-intake-review tr.irprop"


class Mail(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        S.load(v)

    def line(self, text):
        return self.b.eval(f"(()=>{{ const r=[...document.querySelectorAll('{ROW}')].find(t=>t.querySelector('.icttl').textContent.includes({text!r})); "
                           "return r?{pill:r.querySelector('.ickind').textContent, chg:r.querySelector('.icchg').textContent, "
                           "q:(r.querySelector('.icq')||{}).textContent||'', src:r.querySelector('.icsrc').textContent, hold:r.dataset.hold}:null; })()")

    def test_update_line_in_words(self):
        S.open_page(self.b)
        row = self.b.eval(f"(()=>{{ const r=[...document.querySelectorAll('{ROW}')].find(t=>t.querySelector('.ickind').textContent==='Update'); "
                          "return {chg:r.querySelector('.icchg').textContent, q:(r.querySelector('.icq')||{}).textContent||''}; })()")
        self.assertIn("Closes ABC-A-001: Escalate data access to the client CIO", row["chg"])      # B4: the item's title after its ID
        self.assertIn("status Open → Closed", row["chg"])
        self.assertIn("Looks done", row["chg"])
        self.assertIn("attached the SOW", row["q"])
        self.assertNotIn("15:02", row["q"])                                    # the quote keeps its day, not its time

    def test_new_action_and_risk_lines(self):
        S.open_page(self.b)
        act = self.line("Confirm data residency")
        self.assertEqual(act["pill"], "Action")
        self.assertIn("Sara Example", act["chg"])
        self.assertIn("due 02-11-2026", act["chg"])
        self.assertIn("Routine", act["chg"])
        risk = self.line("Supplier may miss")
        self.assertEqual(risk["pill"], "Risk")
        self.assertIn("Impact High", risk["chg"])
        self.assertIn("Likelihood Medium", risk["chg"])
        self.assertIn("approve individually", risk["chg"])

    def test_same_two_groups_needs_first(self):
        S.open_page(self.b)
        heads = self.b.eval("[...document.querySelector('[data-irsec=mail]').parentElement.querySelectorAll('tr.icsubhead')].map(t=>t.dataset.irg)")
        self.assertEqual(heads, ["needs", "routine"])
        self.assertEqual(self.line("Supplier may miss")["hold"], "new risk")
        self.assertEqual(self.line("Confirm data residency")["hold"], "")

    def test_source_line_no_times_and_open_source(self):
        S.open_page(self.b)
        for text in ("Confirm data residency", "Supplier may miss"):
            src = self.line(text)["src"]
            self.assertNotRegex(src, r"\d{1,2}:\d{2}", src)
        self.assertIn("Data residency", self.line("Confirm data residency")["src"])
        self.assertIn("Open source", self.line("Confirm data residency")["src"])
        self.assertEqual(self.b.eval(f"[...document.querySelectorAll('{ROW}')].find(t=>t.querySelector('.icttl').textContent.includes('Confirm data')).querySelector('a.srclink').target"), "_blank")


if __name__ == "__main__":
    unittest.main()
