"""BL-154 (replaced for work items by the peek's Details: BL-176 for existing ones, BL-179 for new ones): the edit panel shows the fields that matter first; the rest are under More fields, which opens by itself when one
of them has a value or a validation message, or is the field asked for. Saving still reads every field. A real browser against
the real live server.

Run: python3 dev/tests/test_edit_panel_fields.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402



DETAILS = "JSON.stringify([...document.querySelectorAll('#pkDet .pk-drow .lab span')].map(d=>d.textContent))"


class EditPanelFields(LiveBrowserCase):
    """BL-176 (sprint-peek): an existing action, RAID item or decision opens in the peek, where BL-154's More fields became
    Details. BL-179 (sprint-peek-new): a new one is the peek too, so no work item shows More fields any more."""
    def open_new(self, k):
        b = self.b
        b.eval("go('work')")
        b.pump(0.2)
        b.eval(f"openNew({k!r})")
        b.wait("CUR && CUR.mode==='new'")

    def test_a_new_item_has_the_key_row_and_details_not_more_fields(self):
        b = self.b
        for k in ("actions", "raid", "decisions"):
            self.open_new(k)
            self.assertEqual(b.eval("document.querySelectorAll('#pFields details.morefields,#pFields [name]').length"), 0, k)
            b.click("#pkDetT")
            details = json.loads(b.eval(DETAILS))
            self.assertIn("Project", details, k)
            self.assertIn("Client-visible", details, k)
            if k == "decisions":
                self.assertIn("Options considered", details)
            else:
                self.assertIn("Milestone", details)
            b.eval("closePanel()")

    def test_the_peek_details_hold_the_rest(self):
        """BL-176: Details, closed unless the item is client-visible, with the fields More fields had."""
        b = self.b
        b.eval("go('work'); openRecord('actions',A[0].id)")
        b.pump(0.3)
        self.assertEqual(b.eval("document.getElementById('pkDetT').getAttribute('aria-expanded')"), "false")
        b.click("#pkDetT")
        for f in ("Project", "Workstream", "Milestone", "Raised", "Client-visible"):
            self.assertIn(f, json.loads(b.eval(DETAILS)))
        b.eval("openRecord('decisions',DEC[0].id)")
        b.pump(0.3)
        b.click("#pkDetT")
        details = json.loads(b.eval(DETAILS))
        for f in ("Options considered", "Revisit", "Replaces", "Client-visible"):
            self.assertIn(f, details)

if __name__ == "__main__":
    unittest.main()
