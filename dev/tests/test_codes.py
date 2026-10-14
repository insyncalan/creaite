"""Tests for project codes of 3 to 7 letters or digits (BL-08) and for tracker.py migrate.

Run: python3 dev/tests/test_codes.py
"""
import json
import re
import sqlite3
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault, action  # noqa: E402

# The three-letter rules of schema v1, as databases created before BL-08 store them
V1_CHECKS = {
    "projects": ("code", "CHECK (length(code) = 3 AND code = upper(code))"),
    "actions": ("id", "CHECK (id GLOB '[A-Z][A-Z][A-Z]-A-[0-9][0-9][0-9]')"),
    "raid": ("id", "CHECK (id GLOB '[A-Z][A-Z][A-Z]-[0-9][0-9][0-9]')"),
    "decisions": ("id", "CHECK (id GLOB '[A-Z][A-Z][A-Z]-D-[0-9][0-9][0-9]')"),
}


def v1_schema(schema_text):
    """schema.sql as it was before BL-08: same tables and columns, three-letter checks."""
    out, table = [], None
    for line in schema_text.splitlines():
        m = re.match(r"CREATE TABLE IF NOT EXISTS (\w+)", line)
        if m:
            table = m.group(1)
        if table in V1_CHECKS:
            field, check = V1_CHECKS[table]
            if re.match(rf"\s+{field}\s+TEXT PRIMARY KEY CHECK", line):
                line = f"  {field} TEXT PRIMARY KEY {check},"
        out.append(line)
    return "\n".join(out)


def new_project(n, code, name="Test project"):
    return {"n": n, "op": "new", "table": "projects", "values": {"code": code, "name": name},
            "match": "strong", "flags": [], "decision": "approved"}


class CodeTests(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        reg = self.v.root / "projects/_portfolio/project-register.md"
        reg.write_text(reg.read_text().replace(
            "|  |  |  |  |  |  |  |  |",
            "| ORX2C | Larkspur CM | ORX2C Larkspur CM | CM | Sam Sample (sponsor) | example.ae | CM – Core | CM |"))
        self.v.run("init")

    def tearDown(self):
        self.v.cleanup()

    def test_register_reads_long_codes(self):
        self.assertEqual([p["code"] for p in self.v.rows("projects")], ["ABC", "ORX2C"])

    def test_ids_per_project_side_by_side(self):
        raid = {"op": "new", "table": "raid", "match": "strong", "flags": [], "decision": "approved",
                "values": {"type": "Issue", "description": "Licences not ordered", "raised": "2026-10-01",
                           "source": "s"}}
        decision = {"op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
                    "values": {"decision": "Hypercare ends 16 Oct", "date": "2026-10-01", "source": "s"}}
        self.v.propose("a", [
            action(1), action(2, project="ORX2C", description="Agree KT scope"),
            action(3, project="ORX2C", description="Close PO query"),
            {**raid, "n": 4, "values": {**raid["values"], "project": "ORX2C"}},
            {**raid, "n": 5, "values": {**raid["values"], "project": "ABC"}},
            {**decision, "n": 6, "values": {**decision["values"], "project": "ORX2C"}},
        ])
        self.v.run("apply")
        self.assertEqual([a["id"] for a in self.v.rows("actions")], ["ABC-A-001", "ORX2C-A-001", "ORX2C-A-002"])
        # One number sequence per project across actions, RAID items and decisions; each project counts on its own
        self.assertEqual([r["id"] for r in self.v.rows("raid")], ["ABC-002", "ORX2C-003"])
        self.assertEqual([d["id"] for d in self.v.rows("decisions")], ["ORX2C-D-004"])
        # Reads, search filters and the Excel export work with the longer code
        rows = json.loads(self.v.run("read", "actions", "--project", "ORX2C").stdout)
        self.assertEqual(len(rows), 2)
        self.assertEqual(self.v.run("export", script="excel_sync.py").returncode, 0)

    def test_valid_and_invalid_codes(self):
        for code in ("DEF", "FALCN", "ORX2", "ABCDEFG"):
            p = self.v.propose(f"ok-{code}", [new_project(1, code)])
            self.assertEqual(self.v.run("validate", str(p)).returncode, 0, code)
        for code in ("2AB", "AB", "ABCDEFGH", "AB-C", "abc", "AB C"):
            p = self.v.propose(f"bad-{len(code)}", [new_project(1, code)])
            r = self.v.run("validate", str(p), ok=False)
            self.assertEqual(r.returncode, 1, code)
            self.assertIn("3 to 7 capital letters or digits, starting with a letter", r.stdout, code)

    def test_schema_itself_enforces_codes_and_ids(self):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            def ok(sql, *a):
                try:
                    con.execute("SAVEPOINT s")
                    con.execute(sql, a)
                    con.execute("ROLLBACK TO s")
                    return True
                except sqlite3.IntegrityError:
                    con.execute("ROLLBACK TO s")
                    return False
            for code, good in (("ABCDEFG", True), ("2AB", False), ("ABCDEFGH", False), ("AB-C", False)):
                self.assertEqual(ok("INSERT INTO projects (code, name) VALUES (?, 'x')", code), good, code)
            ins = "INSERT INTO actions (id, project, description, raised, source) VALUES (?, 'ORX2C', 'd', '2026-10-01', 's')"
            for i, good in (("ORX2C-A-001", True), ("ABC-A-001", True), ("ORX2C-001", False),
                            ("ORX2C-A-01", False), ("AB-C-A-001", False)):
                self.assertEqual(ok(ins, i), good, i)
            ins = "INSERT INTO raid (id, project, type, description, raised, source) VALUES (?, 'ORX2C', 'Risk', 'd', '2026-10-01', 's')"
            for i, good in (("ORX2C-001", True), ("ORX2C-A-001", False), ("ORX-2C-001", False)):
                self.assertEqual(ok(ins, i), good, i)


class MigrateTests(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        schema = self.v.root / "system/scripts/schema.sql"
        self.new_schema = schema.read_text()
        schema.write_text(v1_schema(self.new_schema))   # a vault created before BL-08
        self.v.run("init")
        self.v.propose("seed", [action(1), action(2, description="Book UAT environment"),
                                {"n": 3, "op": "new", "table": "raid", "match": "strong", "flags": [],
                                 "decision": "approved",
                                 "values": {"project": "ABC", "type": "Risk", "description": "Data late → MVP slips",
                                            "impact": "High", "likelihood": "Low", "raised": "2026-10-01",
                                            "source": "s"}}])
        self.v.run("apply")
        schema.write_text(self.new_schema)              # the BL-08 schema arrives

    def tearDown(self):
        self.v.cleanup()

    def test_old_database_migrates_without_losing_rows(self):
        before = {t: self.v.rows(t) for t in ("projects", "actions", "raid", "change_log", "applies")}
        self.assertEqual(self.v.run("init").stdout.count("run tracker.py migrate"), 1)
        r = self.v.run(script="doctor.py", ok=False)
        self.assertIn("run tracker.py migrate", r.stdout)
        out = self.v.run("migrate").stdout
        self.assertIn("Migrated", out)
        after = {t: self.v.rows(t) for t in before}
        for t, rows in before.items():                                  # every row kept, unchanged;
            self.assertEqual([{k: r[k] for k in rows[0]} for r in after[t]] if rows else after[t], rows, t)
        self.assertTrue(all(a["milestone"] is None for a in after["actions"]))   # new optional column, empty
        self.assertIn("Schema is up to date", self.v.run("migrate").stdout)
        self.assertIn("0 failed", self.v.run(script="doctor.py").stdout)
        # Longer codes now work, and the earlier apply can still be undone
        self.v.propose("long", [new_project(1, "ORX2C"), action(2, project="ORX2C")])
        self.v.run("apply")
        self.assertIn("ORX2C-A-001", [a["id"] for a in self.v.rows("actions")])
        self.v.run("undo")
        self.v.run("undo")
        self.assertEqual(self.v.rows("actions"), [])
        self.assertTrue(any(p.name.endswith("-migrate.db") for p in (self.v.root / "system/backups").iterdir()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
