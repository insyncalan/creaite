"""BL-164: Activity's type icons, search and filters, and undoing several past changes, part 1 of 3 (the undo-changes command; the fixture is in activity_undo_support.py).

Run: python3 dev/tests/test_activity_undo.py   (the browser tests need Google Chrome; skipped otherwise)
"""
import json
import sqlite3
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault  # noqa: E402
from activity_undo_support import (  # noqa: E402
    Db,
    seed,
    upd,
)


class UndoChangesCommand(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        seed(self.v)
        self.db = Db(self.v)

    def tearDown(self):
        self.v.cleanup()

    def undo(self, *rowids, dry=False, ok=True):
        r = self.v.run("undo-changes", "--json", *(["--dry-run"] if dry else []), *map(str, rowids), ok=ok)
        return json.loads([x for x in r.stdout.splitlines() if x.startswith("{")][-1])

    def three(self):
        return [self.db.rowid("ABC-A-001", "status"), self.db.rowid("ABC-A-002", "owner"), self.db.rowid("ABC-A-003", "due_date")]

    def test_three_past_changes_in_three_items_go_back_in_one_new_apply(self):
        applies = len(self.db.q("SELECT * FROM applies"))
        backups = set((self.v.root / "system/backups").glob("tracker-*-revert.db"))
        rows = self.three()
        out = self.undo(*rows)
        self.assertEqual(len(out["done"]), 3, out)
        self.assertEqual(out["skipped"], [])
        self.assertEqual(self.db.item("actions", "ABC-A-001")["status"], "Open")
        self.assertIsNone(self.db.item("actions", "ABC-A-001")["closed"])        # the derived field follows, as in any update
        self.assertEqual(self.db.item("actions", "ABC-A-002")["owner"], "Alan Carter")
        self.assertIsNone(self.db.item("actions", "ABC-A-003")["due_date"])
        self.assertEqual(self.db.item("actions", "ABC-A-003")["priority"], "High")   # not chosen: left as it is
        self.assertEqual(len(self.db.q("SELECT * FROM applies")), applies + 1)        # one new apply
        new = out["apply_id"]
        vias = {r["via"] for r in self.db.q("SELECT via FROM change_log WHERE apply_id = ?", new)}
        self.assertEqual(vias, {"revert:" + ",".join(map(str, sorted(rows)))})        # via carries the rowids
        self.assertEqual({r["op"] for r in self.db.q("SELECT op FROM change_log WHERE apply_id = ?", new)}, {"update"})   # ordinary rows
        self.assertTrue(set((self.v.root / "system/backups").glob("tracker-*-revert.db")) - backups)   # the database backup

    def test_a_later_edit_skips_that_item_and_the_others_still_go_back(self):
        rows = self.three()
        self.v.propose("a5", [upd(1, "actions", "ABC-A-002", owner="Omar Ali")])     # changed since
        self.v.run("apply")
        out = self.undo(*rows)
        self.assertEqual(sorted(d["id"] for d in out["done"]), ["ABC-A-001", "ABC-A-003"])
        self.assertEqual([(s["id"], s["why"]) for s in out["skipped"]], [("ABC-A-002", "has changed since: left as it is")])
        self.assertEqual(self.db.item("actions", "ABC-A-002")["owner"], "Omar Ali")
        self.assertIn("skipped 1", out["message"])

    def test_the_dry_run_matches_what_happens_and_writes_nothing(self):
        rows = self.three()
        self.v.propose("a5", [upd(1, "actions", "ABC-A-002", owner="Omar Ali")])
        self.v.run("apply")
        before = (self.db.q("SELECT count(*) n FROM change_log")[0]["n"], self.db.q("SELECT count(*) n FROM applies")[0]["n"])
        plan = self.undo(*rows, dry=True)
        self.assertEqual(before, (self.db.q("SELECT count(*) n FROM change_log")[0]["n"], self.db.q("SELECT count(*) n FROM applies")[0]["n"]))
        self.assertEqual(self.db.item("actions", "ABC-A-001")["status"], "Closed")
        self.assertIsNone(plan["apply_id"])
        real = self.undo(*rows)
        strip = lambda o: ([(d["rowid"], d["id"], d.get("from"), d.get("to")) for d in o["done"]], [(s["rowid"], s["why"]) for s in o["skipped"]])  # noqa: E731
        self.assertEqual(strip(plan), strip(real))
        self.assertEqual(plan["done"][0]["from"], "Closed" if plan["done"][0]["id"] == "ABC-A-001" else plan["done"][0]["from"])

    def test_the_revert_is_itself_undone_by_undo_last_apply(self):
        rows = self.three()
        out = self.undo(*rows)
        self.v.run("undo")
        self.assertEqual(self.db.item("actions", "ABC-A-001")["status"], "Closed")
        self.assertEqual(self.db.item("actions", "ABC-A-002")["owner"], "Sara Example")
        self.assertEqual(self.db.item("actions", "ABC-A-003")["due_date"], "2026-11-20")
        self.assertTrue(self.db.q("SELECT undone_at FROM applies WHERE apply_id = ?", out["apply_id"])[0]["undone_at"])
        # with the revert undone, the same changes can be put back again
        again = self.undo(*rows)
        self.assertEqual(len(again["done"]), 3)

    def test_a_created_item_is_removed_only_if_untouched(self):
        made = self.db.rowid("ABC-A-002", "id", op="insert")
        out = self.undo(made)                                                         # ABC-A-002's owner changed since: kept
        self.assertEqual(out["done"], [])
        self.assertIn("changed since", out["skipped"][0]["why"])
        self.assertIsNotNone(self.db.item("actions", "ABC-A-002"))
        made_r = self.db.rowid("ABC-004", "id", op="insert")                         # the risk: never changed
        out = self.undo(made_r)
        self.assertEqual([d["change"] for d in out["done"]], ["removed"])
        self.assertIsNone(self.db.item("raid", "ABC-004"))
        self.v.run("undo")                                                            # and back again, as it was
        self.assertEqual(self.db.item("raid", "ABC-004")["description"], "Data access late")

    def test_a_created_item_that_something_refers_to_stays(self):
        self.v.propose("ms", [{"n": 1, "op": "new", "table": "milestones", "decision": "approved",
                               "values": {"project": "ABC", "name": "UAT", "baseline_date": "2026-11-01", "forecast_date": "2026-11-01",
                                          "source": "Alan (cx-edit)"}}])
        self.v.run("apply")
        ms = self.db.q("SELECT id FROM milestones")[0]["id"]
        made = self.db.rowid(ms, "id", op="insert")
        self.v.propose("link", [upd(1, "actions", "ABC-A-003", milestone=ms)])
        self.v.run("apply")
        out = self.undo(made)
        self.assertEqual(out["done"], [])
        self.assertIn("refers to it", out["skipped"][0]["why"])

    def test_what_cannot_be_chosen(self):
        rows = self.three()
        out = self.undo(*rows)
        undo_row = self.db.q("SELECT rowid FROM change_log WHERE apply_id = ? LIMIT 1", out["apply_id"])[0]["rowid"]
        again = self.undo(undo_row, rows[0])
        whys = {s["rowid"]: s["why"] for s in again["skipped"]}
        self.assertEqual(whys[undo_row], "is itself an undo")
        self.assertEqual(whys[rows[0]], "already undone")
        self.assertIn("not in the change log", self.undo(999999)["skipped"][0]["why"])
        self.assertIn("Nothing to undo", self.undo(999999)["message"])
        self.assertEqual(self.v.run("undo-changes", "abc", ok=False).returncode, 2)

    def test_two_changes_to_one_field_go_back_in_turn(self):
        self.v.propose("a5", [upd(1, "actions", "ABC-A-002", owner="Omar Ali")])
        self.v.run("apply")
        first = self.db.q("SELECT rowid FROM change_log WHERE item_id='ABC-A-002' AND field='owner' AND op='update' ORDER BY rowid")
        out = self.undo(*[r["rowid"] for r in first])
        self.assertEqual(len(out["done"]), 2)
        self.assertEqual(self.db.item("actions", "ABC-A-002")["owner"], "Alan Carter")

    def test_validation_is_never_loosened(self):
        """A restore that breaks a rule is skipped with the rule's own words; nothing else changes for it."""
        self.v.propose("d", [{"n": 1, "op": "new", "table": "decisions", "decision": "approved",
                              "values": {"project": "ABC", "decision": "Pick a vendor", "status": "Pending", "source": "Alan (cx-edit)"}}])
        self.v.run("apply")
        dec = self.db.q("SELECT id FROM decisions")[0]["id"]
        self.v.propose("d2", [upd(1, "decisions", dec, status="Made", date="2026-10-05", made_by="Jane Doe")])
        self.v.run("apply")
        out = self.undo(self.db.rowid(dec, "status"))
        self.assertEqual(out["done"], [])
        self.assertIn("can't go back to Pending", out["skipped"][0]["why"])
        self.assertEqual(self.db.item("decisions", dec)["status"], "Made")

    def test_no_schema_change(self):
        schema = (self.v.root / "system/scripts/schema.sql").read_text()
        self.undo(*self.three())
        for _ in range(2):
            r = self.v.run("migrate")
        tables = self.db.q("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name")
        self.v.run("migrate")
        self.assertEqual(tables, self.db.q("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"))
        self.assertEqual(schema, (Path(__file__).resolve().parents[2] / "system/scripts/schema.sql").read_text())
        self.assertNotIn("revert", schema)
        del r

    def test_activity_marks_reverted_entries_and_shows_one_entry_for_the_revert(self):
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        import build_dashboard
        rows = self.three()
        out = self.undo(*rows)
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.row_factory = sqlite3.Row
            act = build_dashboard.activity(con)
        by_row = {a.get("rowid"): a for a in act if a.get("rowid")}
        for r in rows:
            self.assertTrue(by_row[r]["reverted"], r)
        rev = [a for a in act if a.get("revert")]
        self.assertEqual(len(rev), 1)
        self.assertEqual(rev[0]["change"], "Undid 3 changes")
        self.assertEqual(rev[0]["apply_id"], out["apply_id"])
        self.assertEqual(rev[0]["by"], "You, in Activity")
        kinds = {a["id"]: a["kind"] for a in act if a.get("id") and a.get("kind")}
        self.assertEqual(kinds["ABC-A-001"], "action")
        self.assertEqual(kinds["ABC-004"], "Risk")
        self.assertTrue(all("rowid" not in a or isinstance(a["rowid"], int) for a in act))
        # entries that can't be chosen carry no rowid: the revert itself
        self.assertNotIn("rowid", rev[0])


if __name__ == "__main__":
    unittest.main()
