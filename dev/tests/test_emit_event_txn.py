"""Cap's HIGH (2.6.1): a failed item_events insert must not be swallowed inside the apply transaction.

With the swallow, the apply COMMITS change_log rows without their item_events (a history gap) and says success. The fix
(dev/proposals/emit-event-txn/tracker.diff): a note of the wrong shape is read by the via alone, before the insert;
any other failure of the insert propagates and rolls the whole apply back (rc 1, nothing written).

The fault is a TRIGGER in the throwaway vault's database that aborts every insert into item_events.
Run: python3 dev/tests/test_emit_event_txn.py     Without the diff in the tree, the test applies it to the throwaway vault's own tracker.py (green both ways).
"""
import json
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from test_tracker import Vault, action  # noqa: E402

SRC = (REPO / "system/scripts/tracker.py").read_text(encoding="utf-8")
CHAIN = "def emit_event" in SRC
FIXED = "emit-event-txn" in SRC          # the repo's own tracker.py carries the fix (in-process test only)
DIFF = REPO / "dev/proposals/emit-event-txn/tracker.diff"


def count(v, sql):
    with closing(sqlite3.connect(v.root / "system" / "tracker.db")) as con:
        return con.execute(sql).fetchone()[0]


class EmitEventTxn(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.fixed = FIXED
        if not FIXED and CHAIN:     # the diff is not in the tree: the throwaway vault's own copy of tracker.py gets it
            r = subprocess.run(["git", "apply", "-p1", str(DIFF)],
                               cwd=self.v.root.resolve(), capture_output=True, text=True)
            if r.returncode != 0:
                self.v.cleanup()
                self.skipTest("the diff does not apply to this tracker.py: " + r.stderr.strip()[:200])
            self.fixed = True
        self.v.run("init")

    def tearDown(self):
        self.v.cleanup()

    def break_events(self, only_real=True):
        """only_real: the insert fails in the real apply (once its applies row exists) but not in the dry run before it."""
        when = "WHEN (SELECT count(*) FROM applies WHERE undone_at IS NULL) > 0 OR NEW.undoes IS NOT NULL OR NEW.route = 'undo' " if only_real else ""
        with closing(sqlite3.connect(self.v.root / "system" / "tracker.db")) as con:
            con.execute(f"CREATE TRIGGER no_events BEFORE INSERT ON item_events {when}BEGIN SELECT RAISE(ABORT, 'disk I/O error'); END")
            con.commit()

    def state(self):
        return {"change_log": count(self.v, "SELECT count(*) FROM change_log"),
                "applies": count(self.v, "SELECT count(*) FROM applies"),
                "actions": count(self.v, "SELECT count(*) FROM actions"),
                "orphans": count(self.v, "SELECT count(*) FROM change_log c WHERE c.field != 'updated_at' "
                                         "AND NOT EXISTS (SELECT 1 FROM item_events e WHERE e.change = c.rowid)")}

    @unittest.skipUnless(CHAIN, "needs the history chain (emit_event in tracker.py)")
    def test_a_failed_event_insert_rolls_the_whole_apply_back(self):
        self.break_events()
        before = self.state()
        self.v.propose("t1", [action(1, description="Item one")])
        r = self.v.run("apply", ok=False)
        after = self.state()
        print(f"\n[repro] rc={r.returncode} before={before} after={after}\n{r.stdout.strip()[-300:]}")
        self.assertNotEqual(r.returncode, 0, "the apply must fail, not report success")
        self.assertEqual(after, before, "nothing is written: no change rows, no applies row, no item")
        self.assertEqual(after["orphans"], 0)

    def test_a_lasting_fault_refuses_the_apply_and_leaves_the_proposal_untouched(self):
        """Cap #275 MEDIUM: the fault is there from the start (the dry run too). The apply stops (rc 1, plain words); it must not
        hold every item as invalid and rewrite the proposal, which would lose Alan's approvals."""
        self.break_events(only_real=False)
        before = self.state()
        p = self.v.propose("t5", [action(1, description="Item one"), action(2, description="Item two")])
        for item in json.loads(p.read_text())["items"]:
            self.assertEqual(item.get("decision"), "approved")
        raw = p.read_bytes()
        r = self.v.run("apply", ok=False)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertNotIn("Held in Review", r.stdout, "a database fault is not a fault in each item")
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        self.assertEqual(self.state(), before)
        self.assertEqual(p.read_bytes(), raw, "the proposal is byte for byte as it was: every approval still stands")

    def test_validate_with_a_lasting_fault_does_not_flag_items_invalid(self):
        self.break_events(only_real=False)
        p = self.v.propose("t6", [action(1, description="Item one")])
        self.v.run("validate", p.name, ok=True)
        for item in json.loads(p.read_text())["items"]:
            self.assertNotIn("invalid", item.get("flags", []))
            self.assertEqual(item.get("decision"), "approved")

    def test_the_failure_is_plain_words(self):
        self.break_events()
        self.v.propose("t2", [action(1, description="Item one")])
        r = self.v.run("apply", ok=False)
        self.assertNotIn("Traceback", r.stdout + r.stderr)

    def test_a_working_apply_has_an_event_for_every_change(self):
        self.v.propose("t3", [action(1, description="Item one")])
        self.v.run("apply")
        self.assertGreater(count(self.v, "SELECT count(*) FROM change_log"), 0)
        self.assertEqual(self.state()["orphans"], 0)

    def test_undo_with_a_failing_event_insert_in_its_own_transaction_changes_nothing(self):
        """The fault appears only inside the real transaction of `tracker.py undo` (route 'undo'), not in the apply before it."""
        self.v.propose("t4", [action(1, description="Item one")])
        self.v.run("apply")
        with closing(sqlite3.connect(self.v.root / "system" / "tracker.db")) as con:
            con.execute("CREATE TRIGGER no_undo_events BEFORE INSERT ON item_events WHEN NEW.route = 'undo' "
                        "BEGIN SELECT RAISE(ABORT, 'disk I/O error'); END")
            con.commit()
        before = self.state()
        r = self.v.run("undo", ok=False)
        print(f"\n[undo repro] rc={r.returncode} before={before} after={self.state()}\n{r.stdout.strip()[-200:]}")
        self.assertNotEqual(r.returncode, 0, "the undo must fail, not report success")
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        self.assertEqual(self.state(), before, "no partial reversal: the item is still applied, no change rows added")
        self.assertEqual(len(self.v.rows("actions")), 1)
        self.assertIsNone(self.v.rows("applies")[0]["undone_at"], "the apply is not marked undone")

    @unittest.skipUnless(FIXED, "in process: needs the diff applied to the repo's tracker.py")
    def test_a_field_of_the_wrong_shape_is_skipped_before_the_insert(self):
        """In process: reading the route raises a shape error (TypeError); the event is still written from the via alone."""
        sys.path.insert(0, str(REPO / "system" / "scripts"))
        import item_history
        import tracker
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.executescript("CREATE TABLE applies (apply_id INTEGER PRIMARY KEY); CREATE TABLE change_log (x);")
        schema = (REPO / "system/scripts/schema.sql").read_text(encoding="utf-8")
        start = schema.index("CREATE TABLE IF NOT EXISTS item_events")
        con.executescript(schema[start:schema.index("CREATE INDEX IF NOT EXISTS item_events_item")])
        orig = item_history.source_of
        item_history.source_of = lambda *a: (_ for _ in ()).throw(TypeError("note"))
        try:
            tracker.EVENT_CTX.clear()
            tracker.emit_event(con, 1, None, "actions", "ABC-A-001", "status", "proposed-x.json")
        finally:
            item_history.source_of = orig
        self.assertEqual(con.execute("SELECT count(*) FROM item_events").fetchone()[0], 1)

    @unittest.skipUnless(FIXED, "in process: needs the diff applied to the repo's tracker.py")
    def test_only_a_shape_error_is_read_by_the_via_alone(self):
        """The fallback is for the shape of the data. A database error while reading the route is not swallowed (mutant: widened except)."""
        sys.path.insert(0, str(REPO / "system" / "scripts"))
        import item_history
        import tracker
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE item_events (x)")
        orig = item_history.source_of
        item_history.source_of = lambda *a: (_ for _ in ()).throw(sqlite3.OperationalError("disk I/O error"))
        try:
            tracker.EVENT_CTX.clear()
            with self.assertRaises(sqlite3.OperationalError):
                tracker.emit_event(con, 1, None, "actions", "ABC-A-001", "status", "proposed-x.json")
        finally:
            item_history.source_of = orig


if __name__ == "__main__":
    unittest.main()
