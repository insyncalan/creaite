"""BL-250 parts B and C (fix-history-feed): a work item's feed holds its whole history, and link and label changes reach it.

B: with more than 2000 change log rows, an item made first still shows its "created" line and its early changes in the peek's
feed (build_dashboard.activity's `flags["older"]`, D.activity_older on the page), while the Activity page keeps its cap and note.
C: a link (`from|to|kind`) shows in both linked items' feeds, worded from each side, and a label change in its item's feed; the
old and the new parts of the log both count.

Run: python3 dev/tests/test_history_feed.py   (the browser part needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

BULK = 2100              # one logged field each (updated_at is not counted), so the newest 2000 rows don't reach the start


def upd(n, id_, **changes):
    return {"n": n, "op": "update", "table": "actions", "id": id_, "changes": changes, "match": "strong", "flags": [], "decision": "approved"}


def load(v):
    """The sample data; an early change, a link and a label on the first two actions; then BULK changes to a third; then the
    link and the label removed (so the old part of the log and the newest part both hold link and label lines)."""
    populate(v)
    first, second, third = [a["id"] for a in v.rows("actions")][:3]
    v.propose("early", [upd(1, first, latest_update="Early change marker")])
    v.run("apply")
    v.propose("link", [{"n": 1, "op": "new", "table": "links", "values": {"from_item": first, "to_item": second, "source": "Alan (cx-edit)"},
                        "match": "strong", "flags": [], "decision": "approved"}, upd(2, first, labels=["Sensitive"])])
    v.run("apply")
    v.propose("bulk", [upd(i + 1, third, latest_update=f"Bulk {i:04d}") for i in range(BULK)])
    v.run("apply")
    v.propose("unlink", [{"n": 1, "op": "cancel", "table": "links", "id": f"{first}|{second}|blocks", "confirm": "not needed",
                          "match": "strong", "flags": [], "decision": "approved"}, upd(2, first, labels=[])])
    v.run("apply")
    return first, second


class HistoryFeed(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        cls.first, cls.second = load(v)

    def feed(self, id_):
        b = self.b
        b.eval("WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        b.eval(f"PK.tab='all'; openRecord('actions',{id_!r})")
        b.wait(f"CUR&&CUR.id==={id_!r}&&document.getElementById('panel').classList.contains('peek')")
        b.pump(0.3)
        return b.eval("document.getElementById('pkFeed').textContent")

    def test_the_data_is_capped_and_the_older_part_keeps_each_items_history(self):
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        import tracker
        import build_dashboard
        with closing(tracker.connect(self.v.root / "system/tracker.db")) as con:
            flags = {}
            lines = build_dashboard.activity(con, flags)
        self.assertTrue(flags["capped"])
        self.assertFalse([a for a in lines if a["id"] == self.first and a["change"].startswith("created")])   # past the cap
        older = flags["older"]
        mine = [x[1] for x in older["items"][self.first]]
        self.assertTrue(any(w.startswith("created") for w in mine))
        self.assertIn("latest update: — → Early change marker", mine)
        self.assertIn(f"Linked to {self.second} (blocks)", mine)
        self.assertIn("Label added: Sensitive", mine)
        self.assertIn(f"Linked from {self.first} (blocks)", [x[1] for x in older["items"][self.second]])
        self.assertTrue(all(0 <= x[2] < len(older["by"]) for x in older["items"][self.first]))
        newest = {a["change"] for a in lines if a.get("sides")}                         # the newest part words the removals too
        self.assertIn(f"Link to {self.second} removed (blocks)", newest)
        self.assertIn("Label removed: Sensitive", newest)

    def test_an_old_item_shows_its_created_line_early_changes_links_and_labels(self):
        text = self.feed(self.first)
        for words in ("created", "Early change marker", f"Linked to {self.second} (blocks)", "Label added: Sensitive",
                      f"Link to {self.second} removed (blocks)", "Label removed: Sensitive"):
            self.assertIn(words, text)
        self.assertLess(text.index("Label removed: Sensitive"), text.index("Early change marker"))     # newest first
        self.assertLess(text.index("Early change marker"), text.index("created"))

    def test_the_other_linked_item_shows_the_link_from_its_side(self):
        text = self.feed(self.second)
        self.assertIn(f"Linked from {self.first} (blocks)", text)
        self.assertIn(f"Link from {self.first} removed (blocks)", text)
        self.assertNotIn("Label added", text)

    def test_the_activity_page_keeps_its_cap_and_note(self):
        b = self.b
        b.eval("go('activity')")
        b.wait("document.querySelector('#actTbl tr[data-row]')")
        self.assertTrue(b.eval("D.activity_capped"))
        self.assertFalse(b.eval("document.getElementById('actCap').hidden"))
        self.assertIn("newest 2,000", b.eval("document.getElementById('actCap').textContent"))
        self.assertEqual(b.eval(f"ACT.filter(a=>a.id==={self.first!r}&&/^created/.test(a.change)).length"), 0)


if __name__ == "__main__":
    unittest.main()
