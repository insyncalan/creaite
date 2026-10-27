"""#386 slice 3: the people table (schema.sql) and its one writer (tracker.py).

The two guarded diffs in dev/proposals/386/ (schema-386.diff, tracker-386.diff) make these pass together. Applied alone, either
one leaves tests failing (never skipped): the schema alone has a table nothing writes, tracker alone writes a table that isn't
there. Each test builds a throwaway vault (test_tracker.Vault) and runs the real tracker.py there.

Run: python3 dev/tests/test_people_table_386.py
"""
import json
import sqlite3
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, REPO, Vault, action  # noqa: E402

REGISTER = "projects/_portfolio/people-register.md"
COLUMNS = ["id", "name", "email", "aliases", "organisation", "role", "is_group", "hidden", "labels", "projects_add",
           "projects_remove", "needs_details", "created", "updated_at"]
SEVEN = (("actions", "owner"), ("raid", "owner"), ("decisions", "made_by"), ("promises", "promised_by"),
         ("promises", "promised_to"), ("milestones", "owner"), ("workstreams", "lead"))
REG = """# People register

## People

| Full name | Email | Aliases | Organisation | Role | Hidden | Follow | Labels | Projects | Left projects | Phone |
|---|---|---|---|---|---|---|---|---|---|---|
| Jane Doe | jane.doe@client.com | Jane, JD | Example Client Ltd | Sponsor |  | yes | Executive sponsor | ABC |  | 0100 |
| Omar Ali | omar@def.example, o.ali@def.example | Omar | Enable | Project manager | yes |  |  |  | ABC |  |
| Sara Example | sara.example@client.com | Sara, Sara E | Example Client Ltd |  |  |  |  |  |  |  |

Notes: kept only in the copy.
"""


def item(n, table, values, op="new"):
    return {"n": n, "op": op, "table": table, "values": values, "match": "strong", "flags": [], "decision": "approved"}


def change(n, table, key, changes, op="update", **more):
    return {"n": n, "op": op, "table": table, "id": key, "changes": changes, "match": "strong", "flags": [],
            "decision": "approved", **more}


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.n = 0

    def tearDown(self):
        self.v.cleanup()

    def path(self, rel):
        return self.v.root / rel

    def write_register(self, text=REG):
        self.path(REGISTER).write_text(text, encoding="utf-8")

    def private_moved(self):
        p = self.path("system/staging/people-private.json")
        p.write_text(json.dumps({"follow": ["Jane Doe"], "kinds": {}, "hidden": [], "moved": "2026-10-27"}), encoding="utf-8")

    def apply(self, *items, ok=True):
        self.n += 1
        self.v.propose(f"p386-{self.n}", list(items))
        return self.v.run("apply", ok=ok)

    def people(self):
        return {p["name"]: p for p in self.v.rows("people")}

    def db(self):
        con = sqlite3.connect(self.path("system/tracker.db"))
        con.row_factory = sqlite3.Row
        return closing(con)

    def migrate(self, *args, ok=True):
        return self.v.run("migrate-people", *args, ok=ok)

    def staged(self):
        return [json.loads(p.read_text()) for p in sorted((self.v.root / "system" / "staging").glob("proposed-*.json"))]


class Schema(Base):
    def test_the_table_and_its_columns(self):
        with self.db() as con:
            cols = [r[1] for r in con.execute("PRAGMA table_info(people)")]
        self.assertEqual(cols, COLUMNS)

    def test_the_schema_refuses_bad_rows(self):
        with self.db() as con:
            con.execute("INSERT INTO people (name, created) VALUES ('Ann Lee', '2026-10-27')")
            for name, aliases in (("ann lee", "[]"), (" Bo", "[]"), ("A|B", "[]"), ("", "[]"), ("Cy", "Cy, C")):
                with self.assertRaises(sqlite3.IntegrityError, msg=(name, aliases)):
                    con.execute("INSERT INTO people (name, aliases, created) VALUES (?, ?, '2026-10-27')", (name, aliases))
            row = con.execute("SELECT needs_details, hidden, is_group, aliases FROM people").fetchone()
            self.assertEqual(tuple(row), (1, 0, 0, "[]"))

    def test_no_follow_column(self):                       # BL-288: who is followed never goes in the tracker
        self.assertFalse({c for c in COLUMNS if "follow" in c or "vip" in c})


class Classified(unittest.TestCase):
    def test_migrate_people_is_a_record_command(self):     # BL-267: ask creaite runs it only in a run Alan confirmed
        sys.path.insert(0, str(REPO / "system" / "scripts"))
        import reach
        self.assertEqual(reach.SCRIPT_COMMANDS["tracker.py"].get("migrate-people"), ("record", "--dry-run"))


class Writer(Base):
    def test_add_update_and_undo(self):
        self.apply(item(1, "people", {"name": "  Priya Nair ", "aliases": ["PN", "pn", " "], "projects_add": ["ABC"]}))
        p = self.people()["Priya Nair"]
        self.assertEqual((p["aliases"], p["projects_add"], p["needs_details"]), ('["PN"]', '["ABC"]', 1))
        self.apply(change(1, "people", str(p["id"]), {"email": "priya@northgate.example", "organisation": "Northgate",
                                                      "role": "Sponsor"}))
        self.assertEqual(self.people()["Priya Nair"]["needs_details"], 0)    # all three details filled
        self.v.run("undo")
        self.assertEqual(self.people()["Priya Nair"]["needs_details"], 1)
        self.v.run("undo")
        self.assertEqual(self.v.rows("people"), [])

    def test_validation_holds_the_item(self):
        self.apply(item(1, "people", {"name": "Ann Lee", "aliases": ["Ann"]}))
        bad = ({"name": "ANN LEE"}, {"name": "Bo Ray", "aliases": ["ann"]}, {"name": "Cy", "email": "not an address"},
               {"name": "Di", "projects_add": ["abc"]}, {"name": "Ed", "aliases": ["E, D"]}, {"name": "Fay", "aliases": ["Fay"]},
               {"name": "Gil", "follow": 1}, {"name": "Hal\nX"})
        out = self.apply(*[item(i, "people", v) for i, v in enumerate(bad, 1)]).stdout
        self.assertEqual(out.count("Held in Review"), len(bad), out)
        self.assertEqual(list(self.people()), ["Ann Lee"])

    def test_people_rows_cannot_be_cancelled(self):
        self.apply(item(1, "people", {"name": "Ann Lee"}))
        out = self.apply(change(1, "people", "1", {}, op="cancel")).stdout
        self.assertIn("Held in Review", out)


class Migration(Base):
    def test_dry_run_writes_nothing(self):
        self.write_register()
        self.private_moved()
        self.apply(action(1, owner="Wren Lead"))
        before = self.path(REGISTER).read_text(encoding="utf-8")
        out = self.migrate("--dry-run").stdout
        self.assertIn("3 from the register, 2 from items", out)          # Wren Lead and Alan Carter (identity)
        self.assertEqual(self.v.rows("people"), [])
        self.assertEqual(self.path(REGISTER).read_text(encoding="utf-8"), before)

    def test_every_column_kept_then_undone(self):
        self.write_register()
        self.private_moved()
        self.apply(action(1, owner="Wren Lead"), action(2, owner="Jane"), action(3, owner="TBC"))
        self.migrate()
        by = self.people()
        self.assertEqual(set(by), {"Jane Doe", "Omar Ali", "Sara Example", "Wren Lead", "Alan Carter"})
        j, o = by["Jane Doe"], by["Omar Ali"]
        self.assertEqual((j["email"], json.loads(j["aliases"]), j["organisation"], j["role"], json.loads(j["labels"]),
                          json.loads(j["projects_add"]), j["hidden"], j["needs_details"]),
                         ("jane.doe@client.com", ["Jane", "JD"], "Example Client Ltd", "Sponsor", ["Executive sponsor"],
                          ["ABC"], 0, 0))
        self.assertEqual((o["email"], o["hidden"], json.loads(o["projects_remove"])), ("omar@def.example, o.ali@def.example", 1, ["ABC"]))
        self.assertEqual((by["Sara Example"]["needs_details"], by["Wren Lead"]["needs_details"]), (1, 1))
        text = self.path(REGISTER).read_text(encoding="utf-8")
        self.assertIn("Made by creaite from your project record", text)
        self.assertNotIn("Follow", text)                                  # BL-288
        self.assertIn("| Alan Carter |", text)                             # Alan is in the export
        kept = self.path("system/backups/people-register.before-386.md")
        self.assertEqual(kept.read_text(encoding="utf-8"), REG)
        self.assertIn("Nothing to do", self.migrate().stdout)              # idempotent
        self.v.run("undo")
        self.assertEqual(self.v.rows("people"), [])
        self.assertEqual(self.path(REGISTER).read_text(encoding="utf-8"), REG)

    def test_the_export_reads_back_the_same(self):
        sys.path.insert(0, str(self.v.root / "system" / "scripts"))
        import propose
        self.write_register()
        self.private_moved()
        self.migrate()
        old = {p["name"]: p for p in propose.people_parse(REG)}
        new = {p["name"]: p for p in propose.people_parse(self.path(REGISTER).read_text(encoding="utf-8"))}
        for name, p in old.items():
            for f in ("email", "aliases", "org", "role", "hidden", "labels"):
                self.assertEqual(new[name][f], p[f], (name, f))
            for c in ("Projects", "Left projects"):
                self.assertEqual(new[name]["extra"].get(c, ""), p["extra"].get(c, ""), (name, c))

    def test_follow_still_in_the_register_stops_it(self):
        self.write_register()
        r = self.migrate(ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("who you follow", r.stdout)
        self.assertEqual(self.v.rows("people"), [])
        self.assertEqual(self.path(REGISTER).read_text(encoding="utf-8"), REG)

    def test_ambiguity_stops_it(self):
        for twin in ("| Jane | j2@client.com |  |  |  |  |  |  |  |  |  |", "| Bo Ray |  | JD |  |  |  |  |  |  |  |  |",
                     "| jane doe |  |  |  |  |  |  |  |  |  |  |"):
            self.write_register(REG.replace("\n\nNotes", "\n" + twin + "\n\nNotes"))
            self.private_moved()
            r = self.migrate(ok=False)
            self.assertEqual(r.returncode, 1, twin)
            self.assertIn("never guesses", r.stdout)
            self.assertEqual(self.v.rows("people"), [])


class Live(Base):
    def setUp(self):
        super().setUp()
        self.write_register()
        self.private_moved()
        self.migrate()

    def pid(self, name):
        return str(self.people()[name]["id"])

    def test_a_new_name_on_an_item_is_added(self):
        self.apply(action(1, owner="Kim New"), action(2, owner="Sara"), action(3, owner="TBC"), action(4, owner="kim new"))
        by = self.people()
        self.assertEqual(by["Kim New"]["needs_details"], 1)
        self.assertNotIn("Sara", by)                                       # an alias is a known person
        self.assertNotIn("TBC", by)
        self.assertEqual(len(by), 5)                                 # the register, Alan and Kim once
        self.assertIn("| Kim New |", self.path(REGISTER).read_text(encoding="utf-8"))
        self.v.run("undo")
        self.assertNotIn("Kim New", self.people())
        self.assertNotIn("Kim New", self.path(REGISTER).read_text(encoding="utf-8"))

    def test_nothing_is_added_before_the_move(self):
        v = Vault()
        try:
            v.run("init")
            v.propose("x", [action(1, owner="Kim New")])
            v.run("apply")
            with closing(sqlite3.connect(v.root / "system" / "tracker.db")) as con:
                self.assertEqual(con.execute("SELECT count(*) FROM people").fetchone()[0], 0)
            self.assertNotIn("Made by creaite", (v.root / REGISTER).read_text(encoding="utf-8"))
        finally:
            v.cleanup()

    def all_seven(self, name):
        self.apply(item(1, "milestones", {"project": "ABC", "name": "Go-live", "baseline_date": "2026-12-01", "owner": name,
                                          "source": f"{ABC}/minutes/x.docx"}),
                   item(2, "workstreams", {"project": "ABC", "name": "Testing", "lead": name, "source": f"{ABC}/minutes/x.docx"}),
                   action(3, owner=name),
                   item(4, "raid", {"project": "ABC", "type": "Risk", "description": "Late data", "owner": name,
                                    "raised": "2026-10-01", "source": f"{ABC}/minutes/x.docx"}),
                   item(5, "decisions", {"project": "ABC", "decision": "Go with plan B", "made_by": name, "date": "2026-10-02",
                                         "source": f"{ABC}/minutes/x.docx"}),
                   item(6, "promises", {"project": "ABC", "promised_by": name, "promised_to": name, "description": "Send notes",
                                        "raised": "2026-10-01", "source": f"{ABC}/minutes/x.docx"}))

    def names_on_items(self):
        with self.db() as con:
            return sorted((t, c, v) for t, c in SEVEN for (v,) in con.execute(f"SELECT {c} FROM {t}"))

    def test_rename_carries_all_seven_columns_and_undoes(self):
        self.all_seven("Omar Ali")
        before = self.names_on_items()
        self.apply(change(1, "people", self.pid("Omar Ali"), {"name": "Omar Ali-Khan"}, op="rename"))
        after = self.names_on_items()
        self.assertEqual(len(after), 7)
        self.assertTrue(all(v == "Omar Ali-Khan" for _, _, v in after), after)
        self.assertIn("Omar Ali-Khan", self.people())
        self.assertNotIn("Omar Ali", self.people())                         # no stray person from the carried names
        self.v.run("undo")
        self.assertEqual(self.names_on_items(), before)
        self.assertIn("Omar Ali", self.people())

    def test_merge_joins_and_undoes(self):
        self.all_seven("Sara Example")
        rows_before = self.v.rows("people")
        self.apply(change(1, "people", self.pid("Sara Example"), {}, op="merge", into=self.pid("Jane Doe")))
        by = self.people()
        self.assertNotIn("Sara Example", by)
        self.assertEqual(json.loads(by["Jane Doe"]["aliases"]), ["Jane", "JD", "Sara Example", "Sara", "Sara E"])
        self.assertTrue(all(v == "Jane Doe" for _, _, v in self.names_on_items()))
        self.v.run("undo")
        self.assertEqual(self.v.rows("people"), rows_before)
        self.assertTrue(all(v == "Sara Example" for _, _, v in self.names_on_items()))

    def test_rename_onto_someone_else_is_refused(self):
        out = self.apply(change(1, "people", self.pid("Omar Ali"), {"name": "jane doe"}, op="rename")).stdout
        self.assertIn("Held in Review", out)
        self.assertIn("merge", out)

    def test_a_proposal_cannot_write_the_register_once_it_is_made(self):
        before = self.path(REGISTER).read_bytes()
        self.v.propose("old-style", [], file_changes={"title": "People", "project": None, "file_changes_decision": "approved",
                                                      "file_ops": [{"op": "write", "path": REGISTER, "content": "# People\n",
                                                                    "previous": before.decode()}]})
        r = self.v.run("apply", ok=False)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("made from your project record", r.stdout)
        self.assertEqual(self.path(REGISTER).read_bytes(), before)

    def test_hide(self):
        self.apply(change(1, "people", self.pid("Sara Example"), {}, op="hide"))
        self.assertEqual(self.people()["Sara Example"]["hidden"], 1)

    def test_export_is_stable_and_a_hand_edit_is_kept(self):
        reg = self.path(REGISTER)
        first = reg.read_bytes()
        self.apply(action(1, owner="Jane Doe"))
        self.assertEqual(reg.read_bytes(), first)                           # nothing about people changed
        reg.write_text(first.decode() + "| Hand Made | | | | | | | | | |\n", encoding="utf-8")
        out = self.apply(action(2, owner="Omar Ali")).stdout
        self.assertIn("edited by hand", out)
        self.assertEqual(reg.read_bytes(), first)                           # made from the tracker again
        state = json.loads(self.path("system/staging/people-export.json").read_text())
        kept = self.path(state["hand_edit"]["kept"])
        self.assertIn("Hand Made", kept.read_text(encoding="utf-8"))
        self.assertTrue(state["hand_edit"]["kept"].startswith("system/backups/files/"))

    def test_recode_carries_a_persons_projects(self):
        self.apply({"n": 1, "op": "recode", "table": "projects", "id": "ABC", "changes": {"code": "ABX"}, "match": "strong",
                    "flags": [], "decision": "approved"})
        self.assertEqual(json.loads(self.people()["Jane Doe"]["projects_add"]), ["ABX"])
        self.assertEqual(json.loads(self.people()["Omar Ali"]["projects_remove"]), ["ABX"])
        self.v.run("undo")
        self.assertEqual(json.loads(self.people()["Jane Doe"]["projects_add"]), ["ABC"])


if __name__ == "__main__":
    unittest.main()
