"""Cap's HIGH (2.6.1): a failed item_events insert must not be swallowed inside the apply transaction.

With the swallow, the apply COMMITS change_log rows without their item_events (a history gap) and says success. The fix
(dev/proposals/emit-event-txn/tracker.diff): a note of the wrong shape is skipped BEFORE the insert (no exception arises for it);
any other failure of the insert propagates and rolls the whole apply back (rc 1, nothing written).

The fault is a TRIGGER in the throwaway vault's database that aborts every insert into item_events.
Run: python3 dev/tests/test_emit_event_txn.py     The fix tests skip until the diff is applied (marker in tracker.py).
"""
import sqlite3
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
FIXED = "emit-event-txn" in SRC


def count(v, sql):
    with closing(sqlite3.connect(v.root / "system" / "tracker.db")) as con:
        return con.execute(sql).fetchone()[0]


class EmitEventTxn(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
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

    @unittest.skipUnless(FIXED, "needs the emit-event-txn diff")
    def test_a_fault_the_dry_run_sees_holds_the_item_and_writes_nothing(self):
        self.break_events(only_real=False)
        before = self.state()
        self.v.propose("t5", [action(1, description="Item one")])
        self.v.run("apply", ok=False)
        self.assertEqual(self.state(), before)

    @unittest.skipUnless(FIXED, "needs the emit-event-txn diff")
    def test_the_failure_is_plain_words(self):
        self.break_events()
        self.v.propose("t2", [action(1, description="Item one")])
        r = self.v.run("apply", ok=False)
        self.assertNotIn("Traceback", r.stdout + r.stderr)

    @unittest.skipUnless(FIXED, "needs the emit-event-txn diff")
    def test_a_working_apply_has_an_event_for_every_change(self):
        self.v.propose("t3", [action(1, description="Item one")])
        self.v.run("apply")
        self.assertGreater(count(self.v, "SELECT count(*) FROM change_log"), 0)
        self.assertEqual(self.state()["orphans"], 0)

    @unittest.skipUnless(CHAIN, "needs the history chain (emit_event in tracker.py)")
    def test_undo_with_a_failing_event_insert_rolls_back_too(self):
        self.v.propose("t4", [action(1, description="Item one")])
        self.v.run("apply")
        self.break_events()
        before = self.state()
        r = self.v.run("undo", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.state(), before)

    @unittest.skipUnless(FIXED, "needs the emit-event-txn diff")
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


if __name__ == "__main__":
    unittest.main()
