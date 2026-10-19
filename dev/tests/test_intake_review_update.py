"""#232-B (release 2.6): the update proposal in the peek, the data and the pure rules; no browser.

B1  The row model: an update row carries the table of its target and, per change, the database column and the item's own text.
B2  core/irUpdate.js (run under Node): the one list of changes, as against the live row, that feeds the chips, the note and the
    "If approved" line; the line's words (B4); what a save writes (B3).
B3  The apply path: what a proposal edited in the peek carries, applied by tracker.py.

Run: python3 dev/tests/test_intake_review_update.py"""
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_dashboard  # noqa: E402
from test_tracker import ABC, Vault, action  # noqa: E402

IRU = Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/core/irUpdate.js"
SRC = f"{ABC}/minutes/2026-10-05 Steering.docx — Actions"

HARNESS = r'''
import json, sys
sys.path.insert(0, "system/scripts")
import build_dashboard as B
data = B.collect(B.clock())
print(json.dumps([r for r in data["review"] if r["kind"] == "update"], sort_keys=True))
'''


def update(n, table, item_id, changes, **k):
    return {"n": n, "op": "update", "table": table, "id": item_id, "changes": changes, "decision": "pending", "match": "strong",
            "flags": [], "source": SRC, **k}


class RowModel(unittest.TestCase):
    """B1: update_record adds `table`, the item's text and each change's database column."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        test_dashboard.populate(cls.v)
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(cls.v.root / "system/tracker.db")) as con:
            cls.aid = con.execute("SELECT id FROM actions WHERE description = 'Book UAT environment'").fetchone()[0]
            cls.rid = con.execute("SELECT id FROM raid LIMIT 1").fetchone()[0]
        cls.v.propose("ups", [
            update(1, "actions", cls.aid, {"due_date": "2026-12-01", "latest_update": "Supplier confirmed"}, why="the supplier confirmed"),
            update(2, "raid", cls.rid, {"status": "Closed"}),
            update(3, "projects", "ABC", {"health": "At risk", "health_reason": "UAT"})])
        r = subprocess.run([sys.executable, "-c", HARNESS], cwd=cls.v.root, capture_output=True, text=True, timeout=300,
                           env={**os.environ, "CREAITE_NOW": "2026-10-09 11:30", "TZ": "UTC"})
        assert r.returncode == 0, r.stderr[-2000:]
        cls.rows = {x["rec"]["target"]: x["rec"] for x in json.loads(r.stdout.strip().splitlines()[-1])}

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_the_table_of_the_target_comes_from_the_server(self):
        self.assertEqual(self.rows[self.aid]["table"], "actions")
        self.assertEqual(self.rows[self.rid]["table"], "raid")
        self.assertEqual(self.rows["ABC"]["table"], "projects")

    def test_each_change_names_its_database_column(self):
        ch = self.rows[self.aid]["changes"]
        self.assertEqual([c["col"] for c in ch], ["due_date", "latest_update"])
        self.assertEqual([c["field"] for c in ch], ["due date", "latest update"])       # the words are unchanged
        self.assertEqual(self.rows[self.rid]["changes"][0]["col"], "status")
        self.assertEqual(self.rows["ABC"]["changes"][1]["col"], "health_reason")

    def test_the_items_own_text_is_there_for_the_line(self):
        self.assertEqual(self.rows[self.aid]["title"], "Book UAT environment")
        self.assertEqual(self.rows["ABC"]["title"], "Example Programme")


if __name__ == "__main__":
    unittest.main()
