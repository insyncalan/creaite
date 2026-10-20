"""#268 Minutes view v2: the Track column's states map onto the record's existing changes, with no server change.

Run: python3 dev/tests/test_minutes_track_ops.py      (quick tier: no Chrome)
What the view does on Approve minutes (components/minutes/track.js reconcileOps), done here through the real
minutes_record.change and review.approve_minutes on test_minutes_approve's staged meeting:
- neither = `remove` with keep_line (the line stays in the filed minutes, no item); cross = `remove` (the line goes); a tick
  on a kept line = `restore`; a cross on a kept line = `restore` then `remove`;
- nothing ticked (#261, "take no items"): every item rejected, and the minutes are still filed with no work items;
- a mix: only the ticked items are written, in one apply;
- Approve, Undo, Approve again (#268's bug): Undo leaves the minutes exactly as they were before Approve (the rows the approve
  took out or kept as lines come back as item rows, with their items pending and no "Removed in the minutes"), so the second
  Approve gives the same result as the first: nothing leaks to Review.
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


    def view(self):
        return self.js("import minutes_record\n"
                       f"r = minutes_record.view(file={self.name!r})\nprint(json.dumps({{'settle': r.get('settle'), 'doc': r['doc']}}))")

    def approve_as_the_view_does(self):
        """Neither on the decision (4) and the risk (5), a cross on the issue (2), the rest ticked; the own ticks 6 and 7."""
        for op in ({"op": "remove", "n": 2}, {"op": "remove", "n": 4, "keep_line": True}, {"op": "remove", "n": 5, "keep_line": True}):
            self.assertTrue(self.change(op)["ok"], op)
        return self.approve(group=True, own=[6, 7])

    def test_approve_undo_approve_again_gives_the_same_result(self):
        before = self.doc()
        first = self.approve_as_the_view_does()
        self.assertTrue(first["ok"], first)
        self.assertIn("Undid apply", self.v.run("undo").stdout)
        seen = self.view()
        self.assertEqual(seen["settle"], [5, 4, 2], "the view says which rows to put back, newest first")
        r = self.change({"op": "settle"})
        self.assertTrue(r["ok"], r)
        self.assertIn("Put back 3 lines", r["message"])
        after = self.doc()
        for sid in ("decisions", "raid", "actions"):
            self.assertEqual(self.rows(after, sid), self.rows(before, sid), f"{sid}: every row as it was before Approve")
        self.assertFalse(after["meta"].get("removed"), "nothing left taken out")
        for i in self.data()["items"]:
            self.assertEqual(i["decision"], "pending", i["n"])
            self.assertNotIn("reject_reason", i, i["n"])
        self.assertEqual(self.view()["settle"], [], "settled")
        again = self.change({"op": "settle"})
        self.assertEqual((again["ok"], again["message"]), (False, "Nothing to put back."), "nothing to settle: no new version")
        second = self.approve_as_the_view_does()
        self.assertTrue(second["ok"], second)
        self.assertEqual((second["approved"], second["waiting"]), (first["approved"], first["waiting"]), "the same result both times")
        self.assertEqual(second["waiting"], [], "nothing waits in Review")
        text = (self.v.root / FILED).read_text(encoding="utf-8")
        self.assertIn("Go-live stays on 20 November", text, "neither: the line stays")
        self.assertNotIn("Test data isn't anonymised", text, "crossed: the line goes")
        self.assertNotIn("Test data isn't anonymised", [x["description"] for x in self.v.rows("raid")], "crossed: never registered (review H1)")
        self.assertNotIn("Go-live stays on 20 November", [d["decision"] for d in self.v.rows("decisions")], "neither: no item")

    def test_any_change_after_an_undo_settles_the_record_first(self):
        self.assertTrue(self.approve_as_the_view_does()["ok"])
        self.v.run("undo")
        self.assertTrue(self.change({"op": "edit", "n": 1, "values": {"owner": "Jane Doe"}})["ok"])
        self.assertEqual(self.view()["settle"], [])
        self.assertTrue(any(x.get("ref") == "@4" for x in self.rows(self.doc(), "decisions")), "the decision is an item row again")



class RaidWorkstream(Base):
    """dev/proposals/minutes-view-v2/raid-workstream.diff, applied: a risk's or issue's workstream is set from the minutes, and
    every workstream from the minutes (an action's too) must be one of the project's Active workstreams, or empty."""
    def setUp(self):
        super().setUp()
        self.v.propose("2026-10-14-0800", [{"n": 1, "op": "new", "table": "workstreams", "decision": "approved",
                                            "values": {"project": "ABC", "name": "Testing", "lead": "Jane Doe", "status": "Active",
                                                       "source": "t"}}])
        self.v.run("apply")

    def item(self, n):
        return next(i for i in self.data()["items"] if i["n"] == n)

    def test_a_risk_takes_one_of_the_projects_workstreams_in_its_own_spelling(self):
        r = self.change({"op": "edit", "n": 5, "values": {"workstream": "testing"}})
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.item(5)["values"]["workstream"], "Testing")
        self.assertTrue(self.change({"op": "edit", "n": 2, "values": {"workstream": "Testing"}})["ok"], "an issue too")
        self.assertTrue(self.change({"op": "edit", "n": 5, "values": {"workstream": ""}})["ok"])
        self.assertNotIn("workstream", self.item(5)["values"], "empty clears it")

    def test_anything_else_is_refused_and_nothing_changes(self):
        for bad in ("Unknown", "<img src=x onerror=alert(1)>", "Testing\n", "Test\x00ing", "   ", 7, ["Testing"], {"a": 1}, "x" * 200):
            for n in (5, 1):
                r = self.change({"op": "edit", "n": n, "values": {"workstream": bad}})
                self.assertFalse(r["ok"], (n, bad))
                self.assertNotIn("workstream", self.item(n)["values"], (n, bad))


if __name__ == "__main__":
    unittest.main()
