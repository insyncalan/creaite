"""Tidy-up from 1.4.0 (sprint-milestones): Activity's search looks through every line read (the newest 2000 change-log rows), not
only the newest 300; the list shows the newest 300 until a search or filter is on, and the cap's note shows only when the 2000-row
limit is reached.

Run: python3 dev/tests/test_activity_search.py   (the browser part needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import action  # noqa: E402


N = 420


def many(v):
    """N changes (one field each), so the 2000 rows read hold more than 300 lines without reaching the limit."""
    populate(v)
    v.propose("one", [action(1, description="Bulk target")])
    v.run("apply")
    target = next(a["id"] for a in v.rows("actions") if a["description"] == "Bulk target")
    v.propose("many", [{"n": i + 1, "op": "update", "table": "actions", "id": target, "changes": {"latest_update": f"Bulk action {i:03d}"},
                        "match": "strong", "flags": [], "decision": "approved"} for i in range(N)])
    v.run("apply")


class ActivitySearch(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        many(v)

    def test_the_data_holds_every_line_and_is_not_capped(self):
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        import tracker
        import build_dashboard
        with closing(tracker.connect(self.v.root / "system/tracker.db")) as con:
            flags = {}
            lines = build_dashboard.activity(con, flags)
        self.assertGreater(len(lines), N)
        self.assertFalse(flags["capped"])

    def test_search_finds_an_old_line_and_the_list_says_it_shows_the_newest(self):
        b = self.b
        b.eval("go('activity')")
        b.wait("document.querySelector('#actTbl tr[data-row]')")
        self.assertEqual(b.eval("document.querySelectorAll('#actTbl tr[data-row]').length"), 300)
        self.assertIn("The newest 300 of", b.eval("document.getElementById('actMore').textContent"))
        self.assertTrue(b.eval("document.getElementById('actCap').hidden"))          # 2000 rows not reached: no cap note
        oldest = b.eval("ACT.filter(a=>/Bulk action 000/.test(a.what)).length")
        self.assertEqual(oldest, 2)                                                   # set to 000, then from 000 to 001
        pos = b.eval("ACT.findIndex(a=>/Bulk action 000/.test(a.what))")
        self.assertGreaterEqual(pos, 300)                                             # beyond the newest 300
        b.eval("ACTF.q='Bulk action 000'; renderActivity()")
        b.wait("document.querySelectorAll('#actTbl tr[data-row]').length===2")
        self.assertIsNone(b.eval("document.getElementById('actMore')"))
        b.eval("D.activity_capped=true; renderActivity()")
        self.assertIn("newest 2,000", b.eval("document.getElementById('actCap').textContent"))


if __name__ == "__main__":
    unittest.main()
