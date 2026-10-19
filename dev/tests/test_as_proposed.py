"""BL-232 (fix-as-proposed): capture edits. The first edit of a pending item keeps a write-once `as_proposed` copy of its
values (`values` for a new item, `changes` for an update).

Run: python3 dev/tests/test_as_proposed.py

Python edits reach `tracker.stamp_as_proposed` (review.py's save: edit, assign; minutes.py's refresh); the page's edits
reach it in `editProposal`. A second edit leaves it; the page's Undo puts it back; apply ignores it and keeps it on the
applied proposal; an old proposal without it stays without it ("edited, before-value unknown").
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault, action  # noqa: E402
import test_minutes_review as tmr  # noqa: E402


def pending(n, **v):
    return {**action(n, **v), "decision": "pending"}


class ReviewEditTests(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        populate(self.v)
        self.p = self.v.propose("bl232", [pending(1, owner="Alan Carter", due_date="2026-11-02"),
                                          {**pending(2, description="An old edit"), "edited_in": "dashboard"},
                                          pending(3, description="Left alone")])

    def tearDown(self):
        self.v.cleanup()

    def items(self, p=None):
        return {i["n"]: i for i in json.loads((p or self.p).read_text())["items"]}

    def num(self, ref):
        rows = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        return next(r["n"] for r in rows if r["file"] == self.p.name and r["ref"] == ref)

    def test_first_edit_records_and_second_keeps(self):
        first = dict(self.items()[1]["values"])
        self.v.run("edit", str(self.num(1)), "owner=Sara Example", script="review.py")
        it = self.items()[1]
        self.assertEqual(it["as_proposed"], first)
        self.assertEqual(it["values"]["owner"], "Sara Example")
        data = json.loads(self.p.read_text())                                       # back to pending, to edit again
        data["items"][0]["decision"] = "pending"
        self.p.write_text(json.dumps(data))
        self.v.run("edit", str(self.num(1)), "due_date=06-11-2026", script="review.py")
        it = self.items()[1]
        self.assertEqual(it["as_proposed"], first)                                 # write-once
        self.assertEqual(it["values"]["due_date"], "2026-11-06")

    def test_a_decision_alone_is_not_an_edit_and_old_items_stay_unknown(self):
        self.v.run("approve", str(self.num(3)), script="review.py")
        self.v.run("approve", str(self.num(2)), script="review.py")
        items = self.items()
        self.assertNotIn("as_proposed", items[3])                                   # a filled Raised or a decision isn't an edit
        self.assertNotIn("as_proposed", items[2])                                   # edited before BL-232: never guessed
        self.assertEqual(items[2]["edited_in"], "dashboard")

    def test_an_update_item_keeps_its_changes(self):
        populate_ids = [a["id"] for a in self.v.rows("actions") if a["project"] == "ABC"]
        p = self.v.propose("upd", [{"n": 1, "op": "update", "table": "actions", "id": populate_ids[0],
                                    "changes": {"status": "Closed"}, "why": "Done", "match": "strong", "flags": [],
                                    "decision": "pending"}])
        rows = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        n = next(r["n"] for r in rows if r["file"] == p.name)
        self.v.run("edit", str(n), "status=Delayed", script="review.py")
        self.assertEqual(self.items(p)[1]["as_proposed"], {"status": "Closed"})

    def test_bl200_assign_records_once(self):
        first = dict(self.items()[1]["values"])
        self.v.run("assign", str(self.num(1)), "DEF", script="review.py")
        self.assertEqual(self.items()[1]["as_proposed"], first)
        self.v.run("assign", str(self.num(1)), "ABC", script="review.py")              # moved back: still the first
        self.assertEqual(self.items()[1]["as_proposed"], first)

    def test_apply_ignores_it_and_keeps_it(self):
        first = dict(self.items()[1]["values"])
        self.v.run("edit", str(self.num(1)), "owner=Sara Example", script="review.py")
        self.v.run("apply")
        made = next(a for a in self.v.rows("actions") if a["description"] == "Send revised SOW to client"
                    and a["owner"] == "Sara Example")
        self.assertEqual(made["owner"], "Sara Example")                             # the edited value, not as_proposed
        applied = next(f for f in (self.v.root / "system/staging/applied" / self.p.name, self.p) if f.exists())
        self.assertTrue(self.items(applied)[1].get("applied"))
        self.assertEqual(self.items(applied)[1]["as_proposed"], first)              # kept for BL-233


class RefreshTests(unittest.TestCase):
    """minutes.py refresh: an item the draft changed keeps what was proposed; an unchanged one gets nothing."""
    setUp, tearDown, fill, items = tmr.RefreshTests.setUp, tmr.RefreshTests.tearDown, tmr.RefreshTests.fill, tmr.RefreshTests.items

    def test_refresh_records_once(self):
        sow = next(i for i in self.items() if i["table"] == "actions" and i["values"]["description"].startswith("Send revised SOW"))
        first = dict(sow["values"])
        edited = tmr.fill_values()
        edited["ACTIONS"] = [{"A_OWNER": "Sara Example", "A_TEXT": "Send revised SOW to the client", "A_DUE": "09-10-2026"}]
        self.fill(edited)
        self.v.run("refresh", self.prop.name, script="minutes.py")
        now = next(i for i in self.items() if i["n"] == sow["n"])
        self.assertEqual(now["as_proposed"], first)
        self.assertEqual(now["edited_in"], "refresh")
        untouched = [i for i in self.items() if i["table"] == "decisions" and i.get("edited_in") != "refresh"]
        self.assertTrue(untouched and all("as_proposed" not in i for i in untouched))
        edited["ACTIONS"][0]["A_OWNER"] = "Jane Doe"
        self.fill(edited)
        self.v.run("refresh", self.prop.name, script="minutes.py")
        now = next(i for i in self.items() if i["n"] == sow["n"])
        self.assertEqual((now["as_proposed"], now["values"]["owner"]), (first, "Jane Doe"))


# ── the dashboard, against the real live server ───────────────────────────────────────────────────────────────────────
from live_browser import LiveBrowserCase  # noqa: E402


class PageEditTests(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        cls.prop = v.propose("bl232", [pending(1, owner="Alan Carter", due_date="2026-11-02"),
                                       pending(2, description="Second row", due_date="2026-11-03"),
                                       {**pending(3, description="Old edit"), "edited_in": "dashboard"}])
        v.run(script="build_dashboard.py")

    def items(self):
        return {i["n"]: i for i in json.loads(self.prop.read_text())["items"]}

    def edit(self, js):
        self.b.eval(f'editProposal("{self.prop.name}",data=>{{ const it=n=>data.items.find(i=>i.n===n); {js} }})')

    def test_each_page_path_records_once(self):
        first = {n: dict(i["values"]) for n, i in self.items().items()}
        self.edit('it(1).values.owner="Sara Example"; it(1).edited_in="dashboard";')            # the panel / cell editor
        self.assertEqual(self.items()[1]["as_proposed"], first[1])
        self.edit('it(1).values.due_date="2026-11-09"; it(1).edited_in="dashboard";')          # a second edit
        self.assertEqual(self.items()[1]["as_proposed"], first[1])
        self.edit('it(2).values.project="DEF"; it(2).match="strong"; it(2).moved_from="ABC"; it(2).edited_in="review";')   # BL-200
        self.assertEqual(self.items()[2]["as_proposed"], first[2])
        self.edit('it(1).decision="approved"; it(1).decided_in="dashboard";')                  # a decision is not an edit
        self.edit('it(3).decision="approved";')
        self.assertNotIn("as_proposed", self.items()[3])                                         # old: stays unknown

    def test_peek_staging_records_its_first_values(self):
        self.edit('it(1).values={...it(1).values,description:"Send the revised SOW"};')          # the peek replaces values
        self.assertEqual(self.items()[1]["as_proposed"]["description"], "Send revised SOW to client")
        self.edit('it(1).values={...it(1).values,description:"Send the SOW"};')
        self.assertEqual(self.items()[1]["as_proposed"]["description"], "Send revised SOW to client")

    def test_review_row_edit_and_undo(self):
        b = self.b
        b.eval("go('review',null,{legacy:true})")
        b.wait("document.querySelector('#reviewBody tr[data-n]')")
        n = b.eval("REV.find(r=>r.rec&&r.rec.t==='Second row').n")
        b.eval(f"RHL.clear(); RHL.add({n}); rvSyncChk(); renderReview()")
        first = dict(self.items()[2]["values"])
        b.eval("rvSet('o','Sara Example')")
        b.wait(f"REV.find(r=>r.n==={n}).edited", 10)
        it = self.items()[2]
        self.assertEqual((it["values"]["owner"], it["as_proposed"]), ("Sara Example", first))
        b.click("#snackU")                                                                       # Undo
        b.wait(f"!REV.find(r=>r.n==={n}).edited", 10)
        it = self.items()[2]
        self.assertEqual(it["values"], first)
        self.assertNotIn("as_proposed", it)                                                      # restored with the values
        self.assertNotIn("edited_in", it)


if __name__ == "__main__":
    unittest.main()
