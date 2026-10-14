"""Tests for the people register (BL-55): parse and write, matching, mapping, edits as proposals and undo, migration.

Run: python3 dev/tests/test_people.py
Each test builds a throwaway vault (test_tracker.Vault) and runs the real propose.py there.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, REPO, Vault, action  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import propose  # noqa: E402  (pure functions only; nothing here touches the repository's own vault)

REGISTER = "projects/_portfolio/people-register.md"
TEXT = (REPO / REGISTER).read_text(encoding="utf-8")


def people():
    return propose.people_parse(TEXT)


class RegisterFormat(unittest.TestCase):
    def test_parse_the_sample(self):
        by = {p["name"]: p for p in people()}
        self.assertEqual(set(by), {"Jane Doe", "Omar Ali", "Sara Example"})
        sara = by["Sara Example"]
        self.assertEqual((sara["email"], sara["aliases"], sara["org"], sara["role"], sara["hidden"]),
                         ("sara.example@client.com", ["Sara", "Sara E"], "Example Client Ltd", "Delivery lead", False))

    def test_write_round_trip_keeps_everything_else(self):
        self.assertEqual(propose.people_text(TEXT, people()), TEXT)                 # nothing changed, nothing moved
        rows = people()
        rows[0]["role"] = "Executive sponsor"
        rows.append({"name": "Priya Nair", "email": "", "aliases": ["PN"], "org": "Northgate", "role": "", "hidden": True,
                     "extra": {}})
        out = propose.people_text(TEXT, rows)
        again = propose.people_parse(out)
        self.assertEqual([(p["name"], p["role"], p["aliases"], p["hidden"]) for p in again],
                         [(p["name"], p["role"], p["aliases"], p["hidden"]) for p in rows])
        self.assertIn("Notes:", out)                                                  # the text around the table survives
        self.assertTrue(out.startswith("# People register"))

    def test_extra_columns_and_pipes(self):
        text = "# R\n\n## People\n\n| Full name | Email | Phone |\n|---|---|---|\n| Ann Lee | a@x.com | 123 |\n"
        rows = propose.people_parse(text)
        self.assertEqual(rows[0]["extra"], {"Phone": "123"})
        rows[0]["role"] = "A|B"
        out = propose.people_text(text, rows)
        self.assertIn("| Phone |", out)
        self.assertIn("123", out)
        self.assertEqual(propose.people_parse(out)[0]["role"], "A/B")                # a pipe would break the table

    def test_no_table_yet(self):
        out = propose.people_text("# People register\n", [{"name": "Ann Lee", "email": "", "aliases": [], "org": "",
                                                           "role": "", "hidden": False, "extra": {}}])
        self.assertEqual([p["name"] for p in propose.people_parse(out)], ["Ann Lee"])


class Matching(unittest.TestCase):
    def setUp(self):
        self.people = people() + [{"name": "Alan Carter", "email": "", "aliases": ["Alan", "AC"], "org": "", "role": "",
                                   "hidden": False, "extra": {}}]

    def r(self, text, others=()):
        return propose.resolve_person(text, self.people, others)

    def test_full_name_alias_and_email_map(self):
        self.assertEqual((self.r("sara example")["status"], self.r("sara example")["name"]), ("known", "Sara Example"))
        self.assertEqual((self.r("Sara")["status"], self.r("Sara")["name"]), ("alias", "Sara Example"))
        self.assertEqual(self.r("sara e")["name"], "Sara Example")
        self.assertEqual((self.r("Sara.Example@Client.com")["status"], self.r("Sara.Example@Client.com")["name"]),
                         ("email", "Sara Example"))
        self.assertEqual(self.r("AC")["name"], "Alan Carter")                           # Alan's short forms
        self.assertEqual(self.r("Omar Ali (Enable)")["name"], "Omar Ali")              # a bracketed company is ignored

    def test_likely_matches_are_offered_never_mapped(self):
        for text in ("Example", "S Example", "SE", "Sara Exampl"):
            r = self.r(text)
            self.assertEqual((r["status"], r["name"], r["candidates"]), ("likely", None, ["Sara Example"]), text)
        r = self.r("sara.example@other.com")                                           # same person, another address
        self.assertEqual((r["status"], r["candidates"]), ("likely", ["Sara Example"]))
        self.assertEqual(self.r("Jan Doe")["candidates"], ["Jane Doe"])                # a one-letter slip

    def test_unknown_is_unknown(self):
        for text in ("Bob", "Priya Nair", "", "TBC x"):
            self.assertEqual(self.r(text)["status"], "unknown", text)

    def test_names_on_items_count_as_known(self):
        self.assertEqual(self.r("Noah Price (FAL)", others=["Noah Price (FAL)"])["status"], "known")
        self.assertEqual(self.r("Noah", others=["Noah Price"])["candidates"], ["Noah Price"])


class RegisterCommands(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.v.propose("seed", [
            action(1, owner="Sara"), action(2, owner="Sara Example", description="Book UAT"),
            action(3, owner="Omar Ali", description="Agree scope"),
            {"n": 4, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
             "values": {"project": "ABC", "decision": "Go-live moves", "made_by": "Sara", "date": "2026-10-01",
                        "source": f"{ABC}/minutes/x.docx — Decisions"}}])
        self.v.run("apply")

    def tearDown(self):
        self.v.cleanup()

    def p(self, *args, ok=True):
        return self.v.run("people", *args, script="propose.py", ok=ok)

    def register(self):
        return propose.people_parse((self.v.root / REGISTER).read_text(encoding="utf-8"))

    def staged(self):
        return sorted((self.v.root / "system/staging").glob("proposed-*-edit.json")) + \
            sorted((self.v.root / "system/staging").glob("proposed-*-cx-setup.json"))

    def apply(self):
        self.v.run("apply")

    def test_add_is_a_file_change_proposal_and_undoable(self):
        before = self.v.snapshot()
        out = self.p("add", "Priya Nair", "--email", "priya@northgate.example", "--aliases", "Priya, PN", "--org",
                     "Northgate", "--role", "Architect").stdout
        self.assertIn("Staged and approved", out)
        self.assertIn(f"Change {REGISTER}:", out)
        self.assertEqual(len(self.register()), 3)                                       # nothing is written until apply
        self.apply()
        row = next(p for p in self.register() if p["name"] == "Priya Nair")
        self.assertEqual((row["email"], row["aliases"], row["org"], row["role"]),
                         ("priya@northgate.example", ["Priya", "PN"], "Northgate", "Architect"))
        self.v.run("undo")
        self.assertEqual(self.v.snapshot(), before)                                     # the file is restored exactly

    def test_add_refuses_someone_already_there(self):
        r = self.p("add", "Sara", ok=False)                                             # an alias of Sara Example
        self.assertIn("already in the register", r.stderr + r.stdout)
        self.assertEqual(self.staged(), [])

    def test_edit_fields_aliases_and_hidden(self):
        self.p("edit", "Omar Ali", "--role", "Programme manager", "--add-alias", "OA", "--hidden", "yes")
        self.apply()
        omar = next(p for p in self.register() if p["name"] == "Omar Ali")
        self.assertEqual((omar["role"], omar["aliases"], omar["hidden"]), ("Programme manager", ["Omar", "OA"], True))
        self.assertEqual(next(p for p in self.register() if p["name"] == "Jane Doe")["role"], "Sponsor")

    def test_rename_updates_the_register_and_every_item_then_undoes(self):
        before = self.v.snapshot()
        out = self.p("rename", "Sara Example", "Sara Khan").stdout
        self.assertIn("ABC-A-002 · Owner: Sara Example → Sara Khan", out)
        self.apply()
        self.assertIn("Sara Khan", [p["name"] for p in self.register()])
        self.assertNotIn("Sara Example", [p["name"] for p in self.register()])
        owners = {a["id"]: a["owner"] for a in self.v.rows("actions")}
        self.assertEqual(owners["ABC-A-002"], "Sara Khan")
        self.assertEqual(owners["ABC-A-001"], "Sara")                                   # "Sara" is another spelling: a merge
        self.v.run("undo")
        self.assertEqual(self.v.snapshot(), before)

    def test_merge_adds_the_old_name_as_an_alias_and_moves_decisions_too(self):
        self.p("merge", "Sara", "Sara Example")                                         # "Sara" is only on items
        self.apply()
        self.assertEqual({a["id"]: a["owner"] for a in self.v.rows("actions")}["ABC-A-001"], "Sara Example")
        self.assertEqual(self.v.rows("decisions")[0]["made_by"], "Sara Example")
        sara = next(p for p in self.register() if p["name"] == "Sara Example")
        self.assertEqual(sara["aliases"], ["Sara", "Sara E"])                           # already there: not doubled
        # a merge of two registered people keeps the details of both
        self.p("add", "S. Example", "--email", "se@x.example", "--org", "Elsewhere")
        self.apply()
        self.p("merge", "S. Example", "Sara Example")
        self.apply()
        names = [p["name"] for p in self.register()]
        self.assertNotIn("S. Example", names)
        sara = next(p for p in self.register() if p["name"] == "Sara Example")
        self.assertIn("S. Example", sara["aliases"])
        self.assertEqual(sara["email"], "sara.example@client.com")                      # the keeper's email wins

    def test_map_a_proposal_maps_aliases_and_flags_unknown_owners(self):
        f = self.v.root / "system/staging/drafts/sweep.json"
        f.write_text(json.dumps({"items": [
            {"n": 1, "op": "new", "table": "actions", "flags": [], "values": {"owner": "sara.example@client.com"}},
            {"n": 2, "op": "new", "table": "actions", "flags": ["no-due-date"], "values": {"owner": "Omar"}},
            {"n": 3, "op": "new", "table": "actions", "flags": [], "values": {"owner": "Priya"}},
            {"n": 4, "op": "new", "table": "raid", "flags": [], "values": {"owner": "TBC"}},
            {"n": 5, "op": "new", "table": "decisions", "flags": [], "values": {"made_by": "Jane"}},
            {"n": 6, "op": "new", "table": "actions", "flags": [], "values": {"owner": "Example"}}]}))
        out = self.p("map", str(f)).stdout
        items = json.loads(f.read_text())["items"]
        self.assertEqual([i["values"].get("owner") or i["values"].get("made_by") for i in items],
                         ["Sara Example", "Omar Ali", "Priya", "TBC", "Jane Doe", "Example"])
        self.assertEqual([i["flags"] for i in items], [[], ["no-due-date"], ["unknown-owner"], [], [],
                                                       ["unknown-owner"]])
        self.assertIn("Is “Example” Sara Example?", out)                                # offered, not guessed
        self.assertIn("“Priya” isn't in the people register", out)

    def test_cx_edit_stage_maps_an_alias_and_notes_an_unknown_name(self):
        spec = self.v.root / "system/staging/drafts/spec.json"
        spec.write_text(json.dumps({"items": [{"op": "update", "table": "actions", "id": "ABC-A-003",
                                               "changes": {"owner": "Sara E"}},
                                              {"op": "update", "table": "actions", "id": "ABC-A-002",
                                               "changes": {"owner": "Pria"}}]}))
        out = self.v.run("stage", str(spec), script="propose.py").stdout
        self.assertIn("ABC-A-003 · Owner: Omar Ali → Sara Example", out)
        self.assertIn("Person: “Pria” isn't in the people register", out)
        staged = json.loads(self.staged()[0].read_text())
        self.assertEqual([i["changes"]["owner"] for i in staged["items"]], ["Sara Example", "Pria"])
        self.assertNotIn("_notes", staged)

    def test_without_a_register_nothing_changes(self):
        (self.v.root / REGISTER).unlink()
        spec = self.v.root / "system/staging/drafts/spec.json"
        spec.write_text(json.dumps({"items": [{"op": "update", "table": "actions", "id": "ABC-A-003",
                                               "changes": {"owner": "Whoever"}}]}))
        out = self.v.run("stage", str(spec), script="propose.py").stdout
        self.assertNotIn("Person:", out)

    def test_list_includes_names_that_are_only_on_items(self):
        out = self.p("list").stdout
        self.assertIn("Sara Example · sara.example@client.com", out)
        self.assertIn("Alan Carter", out)
        rows = json.loads(self.p("list", "--json").stdout)
        self.assertIn(("Sara", False), [(r["name"], r.get("registered", True)) for r in rows])

    def test_migrate_moves_the_settings_names_once(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["people"] = {"added": ["Noah Price (FAL)", "Sara Example"], "hidden": ["Noah Price (FAL)"], "note": "x"}
        cfg.write_text(json.dumps(data, indent=2))
        out = self.p("migrate").stdout
        self.assertIn("| Noah Price |  | Noah Price (FAL) | FAL |  | yes |", out)
        self.assertEqual(json.loads(cfg.read_text())["people"]["added"], ["Noah Price (FAL)", "Sara Example"])  # not yet
        self.apply()
        noah = next(p for p in self.register() if p["name"] == "Noah Price")
        self.assertEqual((noah["org"], noah["aliases"], noah["hidden"]), ("FAL", ["Noah Price (FAL)"], True))
        self.assertEqual(len(self.register()), 4)                                       # Sara Example was already there
        self.assertIn("cleared", self.p("migrate").stdout)                             # the second run clears the lists
        self.assertEqual(json.loads(cfg.read_text())["people"]["added"], [])
        self.assertIn("Nothing to move", self.p("migrate").stdout)

    def test_migrate_creates_the_register_when_there_is_none(self):
        (self.v.root / REGISTER).unlink()
        self.p("migrate")                                                               # the dev settings hold Noah
        self.apply()
        self.assertEqual([p["name"] for p in self.register()], ["Noah Price"])
        self.assertIn("## People", (self.v.root / REGISTER).read_text())


class HandOffs(unittest.TestCase):
    """The checks other areas own: the live server may read the register; doctor reports on it."""
    def test_live_server_may_read_but_not_write_the_register(self):
        import live_server
        self.assertTrue(live_server.allowed("read", REGISTER))
        self.assertTrue(live_server.allowed("exists", REGISTER))
        self.assertFalse(live_server.allowed("write", REGISTER))                      # written only by apply

    def test_doctor(self):
        v = Vault()
        try:
            v.run("init")
            line = lambda: next(l for l in v.run(script="doctor.py", ok=False).stdout.splitlines() if "People register" in l)
            self.assertTrue(line().startswith("PASS"))
            self.assertIn("settings.json still lists", line())                         # the dev settings hold Noah
            (v.root / REGISTER).write_text("# People register\n\nNo table.\n", encoding="utf-8")
            self.assertTrue(line().startswith("FAIL"))
            (v.root / REGISTER).unlink()
            self.assertIn("not created yet", line())
            self.assertTrue(line().startswith("PASS"))
        finally:
            v.cleanup()


if __name__ == "__main__":
    unittest.main()
