"""F1 (semi-shared database foundation, plan #314/#315): five nullable columns on applies and change_log.

Run: python3 dev/tests/test_f1_columns.py     (quick tier: no Chrome)

The change is a guarded diff (dev/proposals/f1/), so on a tree without it this file skips. To run it, apply the diff in a throwaway
worktree first: the line2 variant f1-nullable-columns.diff on the frozen 2.6.1 line, or f1-nullable-columns-after-chain.diff on
the line with the 2.6.1 guarded chain (dev/proposals/f1/README.md). Covered: the columns exist and are nullable; an apply and an undo
stamp engine_version; rows made before keep NULL; recode and undo round-trip; migrate on an old database adds the columns, keeps
every row and is a no-op the second time; the old engine's queries still work on the migrated database; rollback is the dated copy.
Everything is fictional and temporary."""
import shutil
import sqlite3
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault, action  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
APPLIED = "engine_version" in (REPO / "system/scripts/schema.sql").read_text(encoding="utf-8")
APPLY_COLS = ("author", "origin", "sequence", "engine_version")
LOG_COLS = ("author", "origin", "sequence", "base_version", "engine_version")


def info(db, table):
    with closing(sqlite3.connect(db)) as con:
        return {r[1]: r for r in con.execute(f"PRAGMA table_info({table})")}


def old_database(v):
    """A database as the engine before F1 made it: the new one with the F1 columns dropped from both tables."""
    db = v.root / "system/tracker.db"
    with closing(sqlite3.connect(db)) as con:
        for t, cols in (("applies", APPLY_COLS), ("change_log", LOG_COLS)):
            for c in cols:
                con.execute(f"ALTER TABLE {t} DROP COLUMN {c}")
        con.commit()
    return db


@unittest.skipUnless(APPLIED, "F1 diff not applied (dev/proposals/f1/)")
class F1Columns(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        (self.v.root / "VERSION").write_text("9.9.9\n", encoding="utf-8")
        self.v.run("init")
        self.db = self.v.root / "system/tracker.db"

    def apply_one(self, n=1):
        self.v.propose(f"f1-{n}", [action(n)])
        self.v.run("apply")

    def test_columns_exist_and_are_nullable(self):
        for t, cols in (("applies", APPLY_COLS), ("change_log", LOG_COLS)):
            got = info(self.db, t)
            for c in cols:
                self.assertIn(c, got, f"{t}.{c}")
                self.assertEqual(got[c][3], 0, f"{t}.{c} must be nullable")       # notnull
                self.assertIsNone(got[c][4], f"{t}.{c} must have no default")
        self.assertEqual(info(self.db, "applies")["sequence"][2], "INTEGER")
        self.assertEqual(info(self.db, "change_log")["base_version"][2], "INTEGER")

    def test_an_apply_stamps_the_engine_version_and_nothing_else(self):
        self.apply_one()
        rows = self.v.rows("applies")
        self.assertEqual([r["engine_version"] for r in rows], ["9.9.9"])
        self.assertEqual([(r["author"], r["origin"], r["sequence"]) for r in rows], [(None, None, None)])
        for r in self.v.rows("change_log"):
            self.assertTrue(all(r[c] is None for c in LOG_COLS), r)

    def test_without_a_version_file_the_stamp_is_null_and_the_apply_works(self):
        (self.v.root / "VERSION").unlink()
        self.apply_one()
        self.assertEqual([r["engine_version"] for r in self.v.rows("applies")], [None])

    def test_undo_is_stamped_and_round_trips(self):
        before = {t: self.v.rows(t) for t in ("actions",)}
        self.apply_one()
        self.v.run("undo")
        self.assertEqual(self.v.rows("actions"), before["actions"])
        self.assertEqual([r["engine_version"] for r in self.v.rows("applies")], ["9.9.9"])   # the undo adds no apply row
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_recode_and_its_undo_round_trip(self):
        self.apply_one()
        start = [r["id"] for r in self.v.rows("actions")]
        old = self.v.root / "projects/ABC Example Programme"
        new = self.v.root / "projects/XPL Example Plus"
        if old.exists():
            shutil.move(str(old), str(new))
        self.v.run("recode", "ABC", "XPL", "--name", "Example Plus", "--folder", "XPL Example Plus", script="propose.py")
        self.v.run("apply")
        self.assertTrue(all(r["id"].startswith("XPL-") for r in self.v.rows("actions")))
        self.assertTrue(all(r["engine_version"] == "9.9.9" for r in self.v.rows("applies")))
        self.v.run("undo")
        self.assertEqual([r["id"] for r in self.v.rows("actions")], start)

    def test_migrate_adds_the_columns_keeps_every_row_and_is_a_no_op_the_second_time(self):
        self.apply_one()
        self.v.run("undo")
        self.apply_one(2)
        old = old_database(self.v)
        self.assertNotIn("engine_version", info(old, "applies"))
        before = {t: self.v.rows(t) for t in ("applies", "change_log", "actions")}
        out = self.v.run("migrate").stdout
        self.assertIn("Migrated", out)
        for t, cols in (("applies", APPLY_COLS), ("change_log", LOG_COLS)):
            self.assertTrue(set(cols) <= set(info(old, t)), t)
            after = self.v.rows(t)
            self.assertEqual(len(after), len(before[t]), t)
            self.assertEqual([{k: v for k, v in r.items() if k not in cols} for r in after], before[t], t)     # every value kept
            self.assertTrue(all(r[c] is None for r in after for c in cols), t)                               # old rows keep NULL
        self.assertEqual(self.v.rows("actions"), before["actions"])
        self.assertIn("up to date", self.v.run("migrate").stdout)                                           # second time: nothing
        with closing(sqlite3.connect(old)) as con:
            self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.apply_one(3)                                                                                   # and it stamps from then on
        self.assertEqual([r["engine_version"] for r in self.v.rows("applies")][-1], "9.9.9")

    def test_an_old_engine_still_reads_and_writes_the_migrated_database(self):
        """The previous engine names its columns everywhere: its queries (copied in shape) run on the migrated tables."""
        self.apply_one()
        with closing(sqlite3.connect(self.db)) as con:
            n = con.execute("SELECT count(*) FROM applies").fetchone()[0]
            con.execute("INSERT INTO applies (at, proposals, file_ops) VALUES (?, ?, ?)", ("2026-10-23 09:00:00", "[]", "[]"))
            aid = con.execute("SELECT max(apply_id) FROM applies").fetchone()[0]
            con.execute("INSERT INTO change_log (at, apply_id, tbl, item_id, field, old_value, new_value, op, via) VALUES (?,?,?,?,?,?,?,?,?)",
                        ("2026-10-23 09:00:00", aid, "actions", "ABC-A-001", "status", "Open", "Done", "update", "cx-edit"))
            con.execute("UPDATE applies SET undone_at = ? WHERE apply_id = ?", ("2026-10-23 10:00:00", aid))
            self.assertEqual(con.execute("SELECT apply_id, at, proposals, file_ops, undone_at FROM applies").fetchall()[-1][4], "2026-10-23 10:00:00")
            self.assertTrue(con.execute("SELECT at, apply_id, tbl, item_id, field, old_value, new_value, op, via FROM change_log").fetchall())
            self.assertEqual(con.execute("SELECT count(*) FROM applies").fetchone()[0], n + 1)
            con.commit()
        row = self.v.rows("applies")[-1]
        self.assertIsNone(row["engine_version"])                                                           # the old engine stamps nothing

    def test_rollback_is_the_dated_copy(self):
        self.apply_one()
        old = old_database(self.v)
        snapshot = {t: self.v.rows(t) for t in ("applies", "change_log", "actions")}
        self.v.run("migrate")
        backups = sorted((self.v.root / "system/backups").glob("tracker-*-migrate.db"))
        self.assertTrue(backups, "migrate must take a dated copy first")
        self.apply_one(2)                                  # something writes after the migration ...
        shutil.copy2(backups[-1], old)                     # ... and the rollback is the restore (before anything else writes, in practice)
        self.assertNotIn("engine_version", info(old, "applies"))
        for t in snapshot:
            self.assertEqual(self.v.rows(t), snapshot[t], t)


if __name__ == "__main__":
    unittest.main()
