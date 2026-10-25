"""#343 (Cap's H2): the record panel's header never says "Saved for Review" while a change only waits for the Save button.

Run: python3 dev/tests/test_header_waiting_343.py
"""
import unittest
from pathlib import Path

PANEL = (Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/panel.js").read_text(encoding="utf-8")


class Header(unittest.TestCase):
    def test_nothing_says_saved_for_review(self):
        self.assertNotIn("Saved for Review", PANEL)

    def test_a_staged_change_says_it_waits(self):
        self.assertGreaterEqual(PANEL.count("Waiting to be saved"), 3)   # the default, the record's header and a new item's header

    def test_saved_after_the_save_button_is_kept(self):
        self.assertRegex(PANEL, r'd\.length\?"Saved"')


if __name__ == "__main__":
    unittest.main()
