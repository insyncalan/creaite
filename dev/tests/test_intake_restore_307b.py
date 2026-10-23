"""#307 path 29 (real Chrome): Restore of a file that has left the inbox says so and does not claim success.

Run: python3 dev/tests/test_intake_restore_307b.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ir_harden_support import IrHardenCase  # noqa: E402


class RestoreGone(IrHardenCase):
    def test_restoring_a_file_that_left_the_inbox_says_nothing_was_restored(self):
        b = self.b
        name = "2026-10-05 Gone soon.txt"
        self.upload(name)
        b.click(self.sel(name, " [data-ira=later]"))
        b.wait("D.intake_review.later.some(x=>x.title.includes('Gone soon'))", 20)
        (self.v.root / "inbox" / name).unlink()
        b.wait("(()=>{ const e=document.getElementById('snackU'), r=e&&e.getBoundingClientRect(); return !!(r&&r.width&&r.height); })()", 20)   # shown, not just present
        b.click("#snackU", exact=True)
        b.wait("/no longer in your inbox/.test(document.getElementById('snackT').textContent)", 20)
        t = b.eval("document.getElementById('snackT').textContent")
        self.assertEqual(t, "That file is no longer in your inbox, so nothing was restored.")


if __name__ == "__main__":
    unittest.main()
