"""#262 (c51): every Intake row is keyed by its item, so a button the page is holding when a refresh renumbers the list stays its own
row's (Bravo's Approve never saves Charlie). Two checks:
  1. the source: the list of proposal-line rows carries a `key` made from the item's model key and content fingerprint (the mutant,
     the key removed, fails here, and in c51 below);
  2. the behaviour, by Team Cap's check c51 (dev/tests/handchecks/test_v261_intake307_identity.py, a real Chrome run on a release
     built from the committed tree): run it with  python3 dev/tests/handchecks/test_v261_intake307_identity.py Identity307.test_c51_bravo_row_after_the_quick_refresh_never_saves_charlie
Run: python3 dev/tests/test_intake_held_key_262.py
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINE, KEYF = "Proposal" + "Line", "model" + "KeyOf"
SRC = ROOT / "system/templates/dashboard/src/components/intakeReview/proposals.jsx"
BUILT = ROOT / "system/templates/dashboard.html"


class RowKey(unittest.TestCase):
    def test_every_proposal_line_has_a_key_from_its_item(self):
        lines = re.findall(r"<" + LINE + r"\b[^>]*/>", SRC.read_text(encoding="utf-8"))
        self.assertTrue(lines)
        for ln in lines:
            self.assertRegex(ln, r"\bkey=\{" + KEYF + r"\(n\)", ln)
            self.assertIn("cfp", ln)

    def test_the_built_page_has_it_too(self):
        self.assertRegex(BUILT.read_text(encoding="utf-8"), LINE + r",\s*\{[^}]*\},\s*" + KEYF + r"\(\w+\)\s*\+")


if __name__ == "__main__":
    unittest.main()
