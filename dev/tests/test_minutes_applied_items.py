"""Approve minutes never fails on an item that was already approved earlier (2.6.0 defect, fixed in 2.6.1).

Run: python3 dev/tests/test_minutes_applied_items.py      (quick tier; the track.js part needs Node)
State: the minutes were approved in part earlier (items 1 to 4 and 6 applied, 5 and 7 pending); the record still has a row for
every item. Approve minutes used to send a remove for each applied row and stopped on "Item 6 isn't a pending item".
Now the view sends nothing for an applied row, the counts leave it out, and the server says in words which line was already
approved and never names an item by number.
"""
import json
import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_minutes_approve import DRAFT  # noqa: E402
from test_minutes_track_ops import RunsTrackJs, Base  # noqa: E402


class AppliedItems(RunsTrackJs, Base):
    def partly_approved(self):
        """Items 1 to 4 and 6 approved and applied on their own in Review; the minutes themselves still a draft."""
        f = self.proposal_path()
        data = json.loads(f.read_text(encoding="utf-8"))
        for i in data["items"]:
            if i["n"] in (1, 2, 3, 4, 6):
                i["decision"] = "approved"
        f.write_text(json.dumps(data), encoding="utf-8")
        self.v.run("apply", f.name, script="tracker.py")
        data = json.loads(f.read_text(encoding="utf-8"))
        self.assertEqual(sorted(i["n"] for i in data["items"] if i.get("applied")), [1, 2, 3, 4, 6])
        self.assertEqual(self.doc()["state"], "draft")

    @unittest.skipUnless(shutil.which("node"), "needs Node")
    def test_the_view_sends_nothing_for_an_applied_row(self):
        self.partly_approved()
        ops = self.track("T.reconcileOps(doc, plan)")
        self.assertFalse([o for o in ops if o["n"] in (1, 2, 3, 4, 6)], ops)
        counts = self.track("T.trackCounts(doc, plan)")
        self.assertEqual(counts, {"y": 0, "k": 1, "n": 0, "w": 1}, counts)   # only the two pending items: 5 kept, 7 left in Review

    def test_the_server_names_an_applied_line_in_words(self):
        self.partly_approved()
        for op in ({"op": "remove", "n": 4, "keep_line": True}, {"op": "restore", "n": 6}):
            r = self.change(op)
            self.assertFalse(r["ok"], r)
            self.assertIn("was already approved earlier", r["message"])
            self.assertNotRegex(r["message"], r"[Ii]tem \d")
        self.assertIn("Vendor capacity is short", self.change({"op": "remove", "n": 5})["message"])

    def test_the_pending_items_still_go_through(self):
        self.partly_approved()
        r = self.approve(group=True, own=[5, 7])
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["approved"], 2)


if __name__ == "__main__":
    unittest.main()
