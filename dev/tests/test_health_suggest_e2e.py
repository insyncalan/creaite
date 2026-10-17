"""#203, both halves together: the project page's sparkle against the real draft route (drafts.py suggest mode) with the stand-in Claude.

Run: python3 dev/tests/test_health_suggest_e2e.py   (needs Google Chrome; needs the plain half, drafts_fake.py's suggest reply)
"""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_drafts_update import DraftCase  # noqa: E402


class Together(DraftCase):
    def test_the_sparkle_shows_the_real_suggestion_and_use_saves_nothing(self):
        b = self.b
        con = sqlite3.connect(self.v.root / "system/tracker.db")
        before = con.execute("SELECT health, health_reason FROM projects WHERE code='ABC'").fetchone()
        con.close()
        b.eval("go('cockpit','ABC'); openProject('ABC','health')")
        b.wait("document.querySelector('#pFields [data-hsuggest]')")
        b.click("#pFields [data-hsuggest]")
        b.wait("document.querySelector('#hSug .drcard')", 30)
        self.assertEqual(b.eval("document.getElementById('hsgReason').value.startsWith('Two actions are overdue')"), True)
        self.assertTrue(b.eval("document.querySelectorAll('#hSug .hsg-why li').length>0"))
        self.assertTrue(b.eval("!!document.querySelector('#hSug .hsg-chip')"))
        b.click("#hSug [data-hsdo=use]")
        b.wait("document.getElementById('f_reason').value.startsWith('Two actions are overdue')")
        con = sqlite3.connect(self.v.root / "system/tracker.db")
        self.assertEqual(con.execute("SELECT health, health_reason FROM projects WHERE code='ABC'").fetchone(), before)
        con.close()
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
