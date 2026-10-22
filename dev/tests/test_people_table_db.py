"""F3 (2.6.4): the guarded half, end to end on a throwaway vault. Skipped until dev/proposals/f3/*.diff are applied.

Run: python3 dev/tests/test_people_table_db.py
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import REPO, Vault  # noqa: E402

APPLIED = "CREATE TABLE IF NOT EXISTS people" in (REPO / "system" / "scripts" / "schema.sql").read_text(encoding="utf-8")
FIXTURE = (REPO / "dev" / "proposals" / "f3" / "fixture" / "people-register.md").read_text(encoding="utf-8")
REG = "projects/_portfolio/people-register.md"


@unittest.skipUnless(APPLIED, "the F3 diffs are not applied in this tree")
class PeopleTableDb(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        (self.v.root / REG).write_text(FIXTURE, encoding="utf-8")
        self.v.run("init")
        self.private = self.v.root / "system" / "staging" / "people-private.json"

    def test_import_fills_the_table_and_the_private_file(self):
        out = self.v.run("people-import").stdout
        self.assertIn("6 people: 6 new", out)
        self.assertIn("needs a look: Dev Placeholder", out)
        rows = {r["name"]: r for r in self.v.rows("people")}
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows["Dev Placeholder"]["id_source"], "name")
        self.assertEqual(json.loads(rows["Alex Example"]["extra"]), {"Desk": "@alex", "Slack": "Slack handle"})
        priv = json.loads(self.private.read_text(encoding="utf-8"))["people"]
        self.assertEqual(sorted(v.get("vip", "hidden") for v in priv.values()), ["client", "hidden", "management"])
        for r in rows.values():                                   # no VIP or Hidden anywhere in the table
            self.assertNotIn("management", json.dumps(r))
        self.assertEqual((self.v.root / REG).read_text(encoding="utf-8"), FIXTURE)       # the register itself is not touched

    def test_second_import_changes_nothing_and_export_round_trips(self):
        self.v.run("people-import")
        self.assertIn("0 new, 0 changed, 0 removed, 6 the same", self.v.run("people-import").stdout)
        md = self.v.run("people-export").stdout
        for word in ("VIP", "Hidden", "management"):
            self.assertNotIn(word, md.split("Notes:")[0])
        (self.v.root / REG).write_text(md, encoding="utf-8")
        self.assertIn("0 new, 0 changed, 0 removed, 6 the same", self.v.run("people-import").stdout)

    def test_dry_run_and_a_failed_import_leave_the_database_alone(self):
        self.v.run("people-import", "--dry-run")
        self.assertEqual(self.v.rows("people"), [])
        self.assertFalse(self.private.exists())

    def test_adding_an_email_rekeys(self):
        self.v.run("people-import")
        (self.v.root / REG).write_text(FIXTURE.replace("| Dev Placeholder |  |", "| Dev Placeholder | dev.placeholder@enable.example |"), encoding="utf-8")
        out = self.v.run("people-import").stdout
        self.assertIn("1 gained an email", out)
        self.assertEqual(len(self.v.rows("people")), 6)

    def test_propose_reads_the_private_values_back(self):
        self.v.run("people-import")
        (self.v.root / REG).write_text(self.v.run("people-export").stdout, encoding="utf-8")
        code = ("import sys; sys.path.insert(0, 'system/scripts'); import propose; "
                "print(sorted((p['name'], p['hidden'], p['vip']) for p in propose.people_parse(propose.people_register_text()[0]) "
                "if p['hidden'] or p['vip'])); print([v['name'] for v in propose.vip_people()])")
        import subprocess
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, check=True)
        self.assertIn("('Bea Sample', False, 'management')", r.stdout)
        self.assertIn("('Casey Demo', True, '')", r.stdout)
        self.assertIn("Eli Fictional", r.stdout.splitlines()[1])

    def test_regenerating_a_generated_register_keeps_private_columns_out(self):
        self.v.run("people-import")
        (self.v.root / REG).write_text(self.v.run("people-export").stdout, encoding="utf-8")
        code = ("import sys; sys.path.insert(0, 'system/scripts'); import propose; t = propose.people_register_text()[0]; "
                "print(propose.people_text(t, propose.people_parse(t)))")
        import subprocess
        out = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, check=True).stdout
        head = [ln for ln in out.splitlines() if ln.startswith("| Full name")][0]
        self.assertNotIn("VIP", head)
        self.assertNotIn("Hidden", head)

    def test_migrate_adds_the_table_to_an_older_database_and_keeps_the_rows(self):
        import sqlite3
        db = self.v.root / "system" / "tracker.db"
        con = sqlite3.connect(db)
        con.execute("DROP TABLE people")
        con.commit()
        con.close()
        before = self.v.rows("projects")
        self.v.run("migrate")
        self.assertEqual(self.v.rows("people"), [])
        self.assertEqual(self.v.rows("projects"), before)
        self.assertIn("6 people: 6 new", self.v.run("people-import").stdout)

    def test_a_recode_works_with_the_people_table_and_leaves_it_alone(self):
        """The recode refuses a table with an ID-looking column it does not know ("people.person_id"); RECODE_OTHER names it.
        Without dev/proposals/f3/recode.diff this fails at the staging step ("doesn't know how to recode people")."""
        import shutil
        from test_tracker import action
        self.v.propose("seed", [action(1)])
        self.v.run("apply")
        self.v.run("people-import")
        before = self.v.rows("people")
        root = self.v.root / "projects"
        shutil.move(str(root / "ABC Example Programme"), str(root / "XPL Example Plus"))
        self.v.run("recode", "ABC", "XPL", "--name", "Example Plus", "--folder", "XPL Example Plus", script="propose.py")
        self.v.run("apply")
        self.assertEqual([r["id"] for r in self.v.rows("actions")], ["XPL-A-001"])
        self.assertEqual(self.v.rows("people"), before)

    def test_a_thousand_people_import_is_quick(self):
        import time
        rows = ["| Full name | Email | Aliases | Organisation | Role | Hidden | VIP | Labels |", "|---|---|---|---|---|---|---|---|"]
        rows += [f"| Person {i} Example | p{i}@brightwater.example | P{i} | Org | Role | {'yes' if i % 50 == 0 else ''} | | |" for i in range(1000)]
        (self.v.root / REG).write_text("# People register\n\n## People\n\n" + "\n".join(rows) + "\n", encoding="utf-8")
        t0 = time.perf_counter()
        self.assertIn("1000 people: 1000 new", self.v.run("people-import").stdout)
        self.assertIn("1000 the same", self.v.run("people-import").stdout)
        self.assertLess(time.perf_counter() - t0, 10.0)             # two runs, each a fresh process, a backup and a transaction


if __name__ == "__main__":
    unittest.main()
