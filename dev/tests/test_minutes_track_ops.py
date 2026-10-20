"""#268 Minutes view v2: the Track column's states map onto the record's existing changes, with no server change.

Run: python3 dev/tests/test_minutes_track_ops.py      (quick tier: no Chrome)
What the view does on Approve minutes (components/minutes/track.js reconcileOps), done here through the real
minutes_record.change and review.approve_minutes on test_minutes_approve's staged meeting:
- neither = `remove` with keep_line (the line stays in the filed minutes, no item); cross = `remove` (the line goes); a tick
  on a kept line = `restore`; a cross on a kept line = `restore` then `remove`;
- nothing ticked (#261, "take no items"): every item rejected, and the minutes are still filed with no work items;
- a mix: only the ticked items are written, in one apply.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_minutes_approve import ABC, FILED, Base  # noqa: E402


class TrackOps(Base):
    def test_nothing_ticked_files_the_minutes_with_no_items(self):
        for n in range(1, 8):
            self.assertTrue(self.change({"op": "remove", "n": n, "keep_line": n % 2 == 0})["ok"])
        r = self.approve(group=True, own=[])
        self.assertTrue(r["ok"], r)
        self.assertEqual((r["approved"], r["waiting"]), (0, []))
        self.assertIn("filed 1", r["message"])
        self.assertIn("rejected 7", r["message"])
        self.assertTrue((self.v.root / FILED).exists())
        filed = self.doc(FILED)
        self.assertEqual(filed["state"], "approved")
        kept = [x for s in filed["sections"] for x in s.get("rows") or [] if x.get("kept_line")]
        self.assertEqual(len(kept), 3, "neither: three lines stay in the minutes, with no item")
        self.assertNotIn("Book the UAT environment", [a["description"] for a in self.v.rows("actions")])

    def test_a_mix_writes_only_the_ticked_items_and_kept_lines_come_back_by_restore(self):
        self.assertTrue(self.change({"op": "remove", "n": 2, "keep_line": True})["ok"])     # neither
        self.assertTrue(self.change({"op": "remove", "n": 5, "keep_line": True})["ok"])     # neither, then ticked again
        self.assertTrue(self.change({"op": "restore", "n": 5})["ok"])                       # tick on a kept line
        self.assertTrue(self.change({"op": "remove", "n": 4, "keep_line": True})["ok"])     # neither, then crossed
        self.assertTrue(self.change({"op": "restore", "n": 4})["ok"])
        self.assertTrue(self.change({"op": "remove", "n": 4})["ok"])                        # cross on a kept line
        r = self.approve(group=True, own=[5, 6, 7])
        self.assertTrue(r["ok"], r)
        raid = [x["description"] for x in self.v.rows("raid")]
        self.assertIn("Vendor capacity is short → the cutover slips", raid, "the restored risk is written")
        self.assertNotIn("Test data isn't anonymised", raid, "neither: no item")
        self.assertNotIn("Go-live stays on 20 November", [d["decision"] for d in self.v.rows("decisions")], "crossed: no item")
        text = (self.v.root / FILED).read_text(encoding="utf-8")
        self.assertIn("Test data isn't anonymised", text, "neither: the line stays")
        self.assertNotIn("Go-live stays on 20 November", text, "crossed: the line goes")
        self.assertTrue(str(FILED).startswith(ABC))


if __name__ == "__main__":
    unittest.main()
