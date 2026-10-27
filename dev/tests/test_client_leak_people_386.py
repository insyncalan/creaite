"""#386 slice 4: the client names check reads the people table too (G-c, client_leak-386s4.diff), and so does the client-wording
check (drafts.people_names, ordinary, on the branch).

The guarded diff in dev/proposals/386/ (client_leak-386s4.diff) makes the ClientLeak tests pass. Without it they fail (never
skip). TableFromSchema also needs slice 3's schema-386.diff (the people table made by tracker.py init), so slice 4 applied
without slice 3, or slice 3 without slice 4, leaves a failure. Each test builds a throwaway vault (test_tracker.Vault) and runs
the real scripts there.

Run: python3 dev/tests/test_client_leak_people_386.py
"""
import json
import os
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault, action  # noqa: E402
from test_reports import CLIENT_MSG  # noqa: E402  (a complete client message, so the action really is client-visible)

REGISTER = "projects/_portfolio/people-register.md"
REG = ("# People register\n\n## People\n\n| Full name | Email | Aliases | Organisation | Role | Hidden | Labels |\n"
       "|---|---|---|---|---|---|---|\n"
       "| Jane Doe | jane@example.com | Jane | Example Client Ltd | Sponsor | | |\n"
       "| Omar Ali | omar@example.com | Omar | Example Client Ltd | Tester | | |\n")
# The columns slice 3's schema gives the table (schema-386.diff); made here only when tracker.py init didn't make it.
TABLE = ("CREATE TABLE people (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL COLLATE NOCASE UNIQUE, email TEXT, "
         "aliases TEXT NOT NULL DEFAULT '[]', organisation TEXT, role TEXT, is_group INTEGER NOT NULL DEFAULT 0, "
         "hidden INTEGER NOT NULL DEFAULT 0, labels TEXT NOT NULL DEFAULT '[]', projects_add TEXT NOT NULL DEFAULT '[]', "
         "projects_remove TEXT NOT NULL DEFAULT '[]', needs_details INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, "
         "updated_at TEXT NOT NULL DEFAULT (datetime('now')))")
HEAD = "import sys, json; sys.path.insert(0, 'system/scripts')\nimport tracker, client_leak, drafts\ncon = tracker.connect()\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        (self.v.root / REGISTER).write_text(REG, encoding="utf-8")

    def tearDown(self):
        self.v.cleanup()

    def db(self):
        return closing(sqlite3.connect(self.v.root / "system" / "tracker.db", isolation_level=None))

    def has_table(self):
        with self.db() as con:
            return con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'people'").fetchone() is not None

    def people(self, *rows):
        """Rows straight into the people table (the test's own throwaway vault): (name, aliases as a list or raw text)."""
        with self.db() as con:
            if not self.has_table():
                con.execute(TABLE)
            for name, aliases in rows:
                con.execute("INSERT INTO people (name, aliases, created) VALUES (?, ?, '2026-10-27')",
                            (name, aliases if isinstance(aliases, str) else json.dumps(aliases)))

    def py(self, code, ok=True):
        r = subprocess.run([sys.executable, "-c", HEAD + code], cwd=self.v.root, capture_output=True, text=True,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        if ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            return json.loads(r.stdout.strip().splitlines()[-1])
        return r

    def owners(self):
        """Jane Doe owns a client-visible open action; Omar Ali owns only an open one a client report can't show."""
        p = self.v.root / "system" / "staging" / "proposed-c386.json"
        p.write_text(json.dumps({"created": "2026-10-04T09:00:00", "source_run": "cx-edit", "files": [], "items": [
            action(1, owner="Jane Doe", description="Confirm the UAT window", client_visible=1, client_message=CLIENT_MSG),
            action(2, owner="Omar Ali", description="Chase the vendor")]}), encoding="utf-8")
        self.v.run("apply")


class ClientLeak(Base):
    """G-c: client_leak.register_aliases reads the people table on the caller's connection, and still fails closed."""

    def test_table_alias_joins_the_register_aliases(self):
        self.people(("Omar Ali", ["Oz", "O. Ali"]), ("Ravi Singh", ["Rav"]))
        got = self.py("print(json.dumps(client_leak.register_aliases(con)))")
        self.assertEqual(sorted(got["omar ali"]), ["O. Ali", "Omar", "Oz"])      # the register's alias kept, the table's added
        self.assertEqual(got["ravi singh"], ["Rav"])                              # in the table only (register not written yet)
        self.assertEqual(got["jane doe"], ["Jane"])

    def test_internal_owner_named_by_a_table_alias_is_a_finding(self):
        self.owners()
        self.people(("Omar Ali", ["Ozzy"]))
        client, internal = self.py("c, i = client_leak.people(con, 'ABC'); print(json.dumps([sorted(c), sorted(i)]))")
        self.assertEqual(client, ["Jane", "Jane Doe"], "the client side is really there (Cap's LOW 2 on 9dab8c88)")
        self.assertIn("Ozzy", internal)
        self.assertNotIn("Ozzy", client)
        found = self.py("print(json.dumps(client_leak.name_findings(con, 'ABC', 'Ozzy will chase the vendor.')))")
        self.assertEqual(found, ["Ozzy is named but owns only items a client report can't show"])

    def test_an_unreadable_people_table_fails_closed(self):
        self.owners()
        self.people(("Omar Ali", "[oops]"))
        found = self.py("print(json.dumps(client_leak.name_findings(con, 'ABC', 'Nothing to see.')))")
        self.assertEqual(found, [self.py("print(json.dumps(client_leak.REGISTER_UNREAD))")])

    def test_a_broken_people_table_fails_closed(self):
        self.people(("Omar Ali", "[oops]"))
        r = self.py("client_leak.register_aliases(con)", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("RegisterUnreadable", r.stderr)


class FailsClosedOnTheConnection(Base):
    """Cap's LOW 1 on 9dab8c88: a connection that can't be read must raise, never fall back to the register alone (a
    has_table()-style 'error means no table' read would fail open here)."""

    def test_a_closed_connection_fails_closed(self):
        r = self.py("con.close()\nclient_leak.register_aliases(con)", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("RegisterUnreadable", r.stderr)


class Unchanged(Base):
    """What G-c leaves as it was (true with or without the diff)."""

    def test_a_missing_register_still_fails_closed_with_a_table(self):
        self.people(("Omar Ali", ["Oz"]))
        (self.v.root / REGISTER).unlink()
        r = self.py("try:\n    client_leak.register_aliases(con)\nexcept TypeError:\n    client_leak.register_aliases()",
                    ok=False)
        self.assertIn("RegisterUnreadable", r.stderr)

    def test_no_people_table_reads_the_register_alone(self):
        with self.db() as con:
            con.execute("DROP TABLE IF EXISTS people")
        got = self.py("print(json.dumps(client_leak.register_aliases()))")
        self.assertEqual(got, {"jane doe": ["Jane"], "omar ali": ["Omar"]})


class TableFromSchema(Base):
    """Slice 3 and slice 4 together: the table tracker.py init makes (schema-386.diff) is the one the check reads."""

    def test_init_makes_the_table_the_check_reads(self):
        self.assertTrue(self.has_table(), "tracker.py init made no people table: schema-386.diff isn't applied")
        self.people(("Omar Ali", ["Oz"]))
        got = self.py("print(json.dumps(client_leak.register_aliases(con)))")
        self.assertIn("Oz", got["omar ali"])


class DraftsNames(Base):
    """Ordinary half: drafts.people_names (the client-wording check) reads the table too, and stays tolerant."""

    def test_table_names_and_aliases_are_added(self):
        self.people(("Omar Ali", ["Oz"]), ("Ravi Singh", ["Rav"]))
        got = self.py("print(json.dumps(drafts.people_names()))")
        for n in ("Jane Doe", "Jane", "Omar Ali", "Omar", "Oz", "Ravi Singh", "Rav"):
            self.assertIn(n, got)

    def test_a_broken_table_or_none_changes_nothing(self):
        want = ["Jane", "Jane Doe", "Omar", "Omar Ali"]
        with self.db() as con:
            con.execute("DROP TABLE IF EXISTS people")
        self.assertEqual([n for n in self.py("print(json.dumps(drafts.people_names()))") if n in want or n in ("Oz",)], want)
        self.people(("Omar Ali", "[oops]"))
        self.assertEqual([n for n in self.py("print(json.dumps(drafts.people_names()))") if n in want or n in ("Oz",)], want)


if __name__ == "__main__":
    unittest.main()
