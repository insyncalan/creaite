"""#386 slice 3: the people table (schema.sql) and its one writer (tracker.py, reach.py).

The three guarded diffs in dev/proposals/386/ (schema-386.diff, tracker-386.diff, reach-386.diff) make these pass together.

Gating (the same shape as slice 2's guarded test): each diff leaves a fixed marker in its file (schema.sql's "-- People (#386)",
tracker.py's slice 3 banner, reach.py's migrate-people comment). None present: the diffs are not applied (the branch as committed),
every test of the change SKIPS and only the always-on checks run. Some but not all present: `AllOrNone` FAILS (the three are one
change) and every other test runs and fails too. All three present: everything runs.

Who Alan follows and who is hidden are never in the table, the change log or the exported register (Jarvis, 27-10-2026): both live
only in slice 2's system/staging/people-private.json.

Each test builds a throwaway vault (test_tracker.Vault) and runs the real tracker.py there. Fictional names only.
Run: python3 dev/tests/test_people_table_386.py
"""
import hashlib
import json
import os
import sqlite3
import sys
import unicodedata
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, REPO, Vault, action  # noqa: E402

SCRIPTS = REPO / "system" / "scripts"
SCHEMA_ON = "-- People (#386)" in (SCRIPTS / "schema.sql").read_text(encoding="utf-8")
TRACKER_ON = "# ===== #386 slice 3: the people table and its one writer =====" in (SCRIPTS / "tracker.py").read_text(encoding="utf-8")
REACH_ON = "#386: the register moves into the people table" in (SCRIPTS / "reach.py").read_text(encoding="utf-8")
ANY_APPLIED = SCHEMA_ON or TRACKER_ON or REACH_ON
APPLIED_ONLY = unittest.skipUnless(ANY_APPLIED, "none of the three slice 3 guarded diffs is applied (dev/proposals/386/)")

REGISTER = "projects/_portfolio/people-register.md"
PRIVATE = "system/staging/people-private.json"
COLUMNS = ["id", "name", "email", "aliases", "organisation", "role", "is_group", "labels", "projects_add",
           "projects_remove", "needs_details", "created", "updated_at"]
SEVEN = (("actions", "owner"), ("raid", "owner"), ("decisions", "made_by"), ("promises", "promised_by"),
         ("promises", "promised_to"), ("milestones", "owner"), ("workstreams", "lead"))
# A register the move carries whole: the template's own guidance lines, the Follow and Hidden columns (their values are slice 2's,
# read from the private file once it is moved), a Group column and the project columns.
REG = """# People register

Keep this file at `projects/_portfolio/people-register.md`, beside `project-register.md`. Claude reads it every run.

## People

| Full name | Email | Aliases | Organisation | Role | Hidden | Follow | Labels | Group | Projects | Left projects |
|---|---|---|---|---|---|---|---|---|---|---|
| Jane Doe | jane.doe@client.com | Jane, JD | Example Client Ltd | Sponsor |  | yes | Sensitive |  | ABC |  |
| Omar Ali | omar@def.example, o.ali@def.example | Omar | Enable | Project manager | yes |  |  |  |  | ABC |
| Sara Example | sara.example@client.com | Sara, Sara E | Example Client Ltd |  |  |  |  |  |  |  |
| Delivery Team |  |  | Brightwater | Group |  |  |  | yes |  |  |

Notes:
- **Full name:** the one name used on every item. Required; everything else can be added later.
- **Hidden:** `yes` keeps someone out of the owner picker. Their items keep their name.
- Use no `|` characters inside a cell.
"""
LAST_ROW = "| Delivery Team |  |  | Brightwater | Group |  |  |  | yes |  |  |\n"
SMALL = "# People register\n\n## People\n\n| Full name | Email |\n|---|---|\n| Jane Doe | jane.doe@client.com |\n"


def row(*cells):
    """One register row of REG's eleven columns."""
    cells = list(cells) + [""] * (11 - len(cells))
    return "| " + " | ".join(cells) + " |"


def with_row(line, text=REG):
    """`text` (REG) with one more People row at the end of the table."""
    assert LAST_ROW in text
    return text.replace(LAST_ROW, LAST_ROW + line + "\n", 1)


def item(n, table, values, op="new"):
    return {"n": n, "op": op, "table": table, "values": values, "match": "strong", "flags": [], "decision": "approved"}


def change(n, table, key, changes, op="update", **more):
    return {"n": n, "op": op, "table": table, "id": key, "changes": changes, "match": "strong", "flags": [],
            "decision": "approved", **more}


def fold(s):
    return unicodedata.normalize("NFC", s).casefold()


class AllOrNone(unittest.TestCase):
    """Runs whether or not the diffs are applied."""

    def test_all_three_diffs_or_none(self):
        self.assertEqual((SCHEMA_ON, TRACKER_ON, REACH_ON), (ANY_APPLIED,) * 3,
                         "only some of the three slice 3 guarded diffs are applied: they land together, as one commit "
                         "(dev/proposals/386/README-slice3.md)")

    def test_the_chain_and_the_readme_name_each_diff_and_its_sha256(self):
        d = REPO / "dev" / "proposals" / "386"
        chain = (d / "GUARDED-386-s3.chain").read_text(encoding="utf-8").splitlines()
        listed = [x.strip() for x in chain if x.strip() and not x.lstrip().startswith("#")]
        self.assertEqual(listed, [f"dev/proposals/386/{n}-386.diff" for n in ("schema", "tracker", "reach")])
        readme = (d / "README-slice3.md").read_text(encoding="utf-8")
        for rel in listed:
            sha = hashlib.sha256((REPO / rel).read_bytes()).hexdigest()
            self.assertIn(sha, "\n".join(chain), rel + " in the chain file")
            self.assertIn(f"`{sha}`", readme, rel + " in the README")


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
        """Slice 2's private file after its move (people_private.migrate): who is followed and hidden are there."""
        self.path(PRIVATE).write_text(json.dumps({"follow": ["Jane Doe"], "kinds": {}, "hidden": ["Omar Ali"],
                                                  "moved": "2026-10-27"}), encoding="utf-8")

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

    def applies(self):
        with self.db() as con:
            return con.execute("SELECT count(*) FROM applies").fetchone()[0]

    def files(self):
        """Every file in the vault but the scripts' caches and the debug log, with its bytes' sha256."""
        out = {}
        for f in sorted(self.v.root.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts and "logs" not in f.parts:       # the debug log notes every run
                out[f.relative_to(self.v.root).as_posix()] = hashlib.sha256(f.read_bytes()).hexdigest()
        return out

    def assert_refused(self, r, words, text=REG):
        """The move stopped, wrote nothing and said why."""
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        self.assertIn(words, r.stdout)
        self.assertEqual(self.v.rows("people"), [])
        self.assertEqual(self.path(REGISTER).read_text(encoding="utf-8"), text)


@APPLIED_ONLY
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
            r = con.execute("SELECT needs_details, is_group, aliases FROM people").fetchone()
            self.assertEqual(tuple(r), (1, 0, "[]"))

    def test_no_private_column(self):                      # BL-288, Jarvis 27-10: follow and hidden are slice 2's private file's
        self.assertFalse({c for c in COLUMNS if "follow" in c or "vip" in c or "hidden" in c})
        schema = (SCRIPTS / "schema.sql").read_text(encoding="utf-8")
        block = schema[schema.index("CREATE TABLE IF NOT EXISTS people"):]
        self.assertNotIn("hidden", block[:block.index(");")])


@APPLIED_ONLY
class Classified(unittest.TestCase):
    def test_migrate_people_is_a_record_command(self):     # BL-267: ask creaite runs it only in a run Alan confirmed
        sys.path.insert(0, str(SCRIPTS))
        import reach
        self.assertEqual(reach.SCRIPT_COMMANDS["tracker.py"].get("migrate-people"), ("record", "--dry-run"))


@APPLIED_ONLY
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
               {"name": "Gil", "follow": 1}, {"name": "Hal\nX"}, {"name": "Hy", "hidden": 1},
               {"name": unicodedata.normalize("NFD", "ÁNN LEE")},
               # explicit "new" is as strict as auto-add: no placeholder names, known project codes and labels only
               {"name": "TBC"}, {"name": "n/a"}, {"name": "Iz", "projects_add": ["ZZZ"]}, {"name": "Jo", "labels": ["Nonesuch"]},
               # organisation and role keep the register's cells whole: no bar, no line break
               {"name": "Ko", "organisation": "Example | Client"}, {"name": "Lu", "role": "Lead\nSponsor"},
               {"name": "Mo", "role": "Lead\rSponsor"})
        self.apply(item(1, "people", {"name": "Ánn Lee"}))
        out = self.apply(*[item(i, "people", v) for i, v in enumerate(bad, 1)]).stdout
        self.assertEqual(out.count("Held in Review"), len(bad), out)
        self.assertEqual(sorted(self.people()), ["Ann Lee", "Ánn Lee"])

    def test_a_known_label_and_project_are_taken(self):
        self.apply(item(1, "people", {"name": "Ann Lee", "labels": ["sensitive"], "projects_remove": ["ABC"]}))
        self.assertEqual(json.loads(self.people()["Ann Lee"]["projects_remove"]), ["ABC"])

    def test_people_rows_cannot_be_cancelled(self):
        self.apply(item(1, "people", {"name": "Ann Lee"}))
        out = self.apply(change(1, "people", "1", {}, op="cancel")).stdout
        self.assertIn("Held in Review", out)

    def test_there_is_no_hide_op(self):                    # hidden is slice 2's route's, never the record's
        self.apply(item(1, "people", {"name": "Ann Lee"}))
        out = self.apply(change(1, "people", "1", {}, op="hide")).stdout
        self.assertIn("Held in Review", out)
        out = self.apply(change(1, "people", "1", {"hidden": 1})).stdout
        self.assertIn("Held in Review", out)


@APPLIED_ONLY
class Migration(Base):
    def test_dry_run_writes_no_file_and_takes_no_backup(self):
        self.write_register()
        self.private_moved()
        self.apply(action(1, owner="Wren Lead"))
        before, applies = self.files(), self.applies()
        out = self.migrate("--dry-run").stdout
        self.assertIn("4 from the register, 2 from items", out)          # Wren Lead and Alan Carter (identity)
        self.assertEqual(self.v.rows("people"), [])
        self.assertEqual(self.files(), before)                            # no backup, no state file, the register as it was
        self.assertEqual(self.applies(), applies)

    def test_every_column_kept_then_undone(self):
        self.write_register()
        self.private_moved()
        self.apply(action(1, owner="Wren Lead"), action(2, owner="Jane"), action(3, owner="TBC"))
        self.migrate()
        by = self.people()
        self.assertEqual(set(by), {"Jane Doe", "Omar Ali", "Sara Example", "Delivery Team", "Wren Lead", "Alan Carter"})
        j, o = by["Jane Doe"], by["Omar Ali"]
        self.assertEqual((j["email"], json.loads(j["aliases"]), j["organisation"], j["role"], json.loads(j["labels"]),
                          json.loads(j["projects_add"]), j["is_group"], j["needs_details"]),
                         ("jane.doe@client.com", ["Jane", "JD"], "Example Client Ltd", "Sponsor", ["Sensitive"], ["ABC"], 0, 0))
        self.assertEqual((o["email"], json.loads(o["projects_remove"])), ("omar@def.example, o.ali@def.example", ["ABC"]))
        self.assertNotIn("hidden", o)                                     # hidden stays in the private file only
        self.assertEqual(by["Delivery Team"]["is_group"], 1)
        self.assertEqual((by["Sara Example"]["needs_details"], by["Wren Lead"]["needs_details"]), (1, 1))
        text = self.path(REGISTER).read_text(encoding="utf-8")
        self.assertIn("Made by creaite from your project record", text)
        for word in ("Follow", "Hidden", "VIP"):                          # BL-288: neither flag reaches the OneDrive register
            self.assertNotIn(word, text)
        self.assertIn("| Alan Carter |", text)                             # Alan is in the export
        kept = self.path("system/backups/people-register.before-386.md")
        self.assertEqual(kept.read_text(encoding="utf-8"), REG)
        self.assertIn("Nothing to do", self.migrate().stdout)              # idempotent
        self.v.run("undo")
        self.assertEqual(self.v.rows("people"), [])
        self.assertEqual(self.path(REGISTER).read_text(encoding="utf-8"), REG)

    def test_hidden_is_nowhere_in_the_record(self):
        self.write_register()
        self.private_moved()
        self.migrate()
        with self.db() as con:
            fields = {r[0] for r in con.execute("SELECT DISTINCT field FROM change_log WHERE tbl = 'people'")}
        self.assertTrue(fields)
        self.assertFalse({f for f in fields if f in ("hidden", "follow", "vip")}, fields)
        self.assertEqual(json.loads(self.path(PRIVATE).read_text())["hidden"], ["Omar Ali"])    # slice 2's file untouched

    def test_the_export_reads_back_the_same(self):
        sys.path.insert(0, str(self.v.root / "system" / "scripts"))
        import propose
        self.write_register()
        self.private_moved()
        self.migrate()
        old = {p["name"]: p for p in propose.people_parse(REG)}
        new = {p["name"]: p for p in propose.people_parse(self.path(REGISTER).read_text(encoding="utf-8"))}
        for name, p in old.items():
            for f in ("email", "aliases", "org", "role", "labels"):
                self.assertEqual(new[name][f], p[f], (name, f))
            for c in ("Projects", "Left projects", "Group"):
                self.assertEqual(new[name]["extra"].get(c, ""), p["extra"].get(c, ""), (name, c))
        self.assertEqual(new["Delivery Team"]["extra"]["Group"], "yes")

    def test_aliases_are_the_third_column_of_the_export(self):     # client_leak reads the file's Aliases cell by position
        self.write_register()
        self.private_moved()
        self.migrate()
        head = next(x for x in self.path(REGISTER).read_text(encoding="utf-8").splitlines() if x.startswith("| Full name"))
        self.assertEqual([c.strip() for c in head.strip("|").split("|")][:3], ["Full name", "Email", "Aliases"])

    def test_follow_still_in_the_register_stops_it(self):
        self.write_register()
        self.assert_refused(self.migrate(ok=False), "who you follow")

    def test_hidden_still_in_the_register_stops_it(self):
        text = REG.replace("| yes | Sensitive |", "|  | Sensitive |")         # nobody followed, Omar still hidden
        self.write_register(text)
        self.assert_refused(self.migrate(ok=False), "hide", text)
        self.assert_refused(self.migrate("--dry-run", ok=False), "hide", text)

    def test_empty_follow_and_hidden_columns_do_not_stop_it(self):
        text = REG.replace("| yes | Sensitive |", "|  | Sensitive |").replace("| Project manager | yes |", "| Project manager |  |")
        self.write_register(text)
        self.migrate()
        self.assertIn("Omar Ali", self.people())

    def test_slice_2s_tombstone_alone_counts_as_moved(self):
        self.write_register()
        self.path(PRIVATE + ".moved").write_text('{"moved": "2026-10-27"}\n', encoding="utf-8")
        self.migrate()
        self.assertIn("Jane Doe", self.people())

    def test_ambiguity_stops_it(self):
        for twin in (row("Jane", "j2@client.com"), row("Bo Ray", "", "JD"), row("jane doe")):
            text = with_row(twin)
            self.write_register(text)
            self.private_moved()
            self.assert_refused(self.migrate(ok=False), "never guesses", text)
        nfd = unicodedata.normalize("NFD", "Élodie Durand")
        text = with_row(row("Élodie Durand") + "\n" + row(nfd))
        self.write_register(text)
        self.assert_refused(self.migrate(ok=False), "never guesses", text)     # NFC and NFD twins are one name

    def test_an_nfd_owner_on_an_item_is_the_registers_person(self):
        self.write_register(with_row(row("Élodie Durand", "elodie@client.com", "", "Example Client Ltd", "Analyst")))
        self.private_moved()
        self.apply(action(1, owner=unicodedata.normalize("NFD", "ÉLODIE DURAND")))
        self.migrate()
        self.assertEqual([n for n in self.people() if fold(n) == fold("élodie durand")], ["Élodie Durand"])

    def test_what_the_move_cannot_carry_stops_it(self):
        cases = {
            "a column with values": "# People register\n\n## People\n\n| Full name | Email | Phone |\n|---|---|---|\n"
                                    "| Jane Doe | jane.doe@client.com | 0100 |\n",
            "another section": SMALL + "\n## Groups\n\n- Delivery Team: Jane Doe\n",
            "a free note": SMALL + "\nKeep me: Jane is back on 02-11-2026.\n",
            "a note before the table": SMALL.replace("## People", "Call Omar first.\n\n## People"),
            "a second table": SMALL + "\n| Name | Phone |\n|---|---|\n| Jane Doe | 0100 |\n",
            "no Full name column": SMALL.replace("| Full name |", "| Name |"),
            "a row without a name": SMALL + "|  | lost@client.com |\n",
            "a row longer than the header": SMALL + "| Kim Long | kim@client.com | extra |\n",
            "an unreadable Group value": "# People register\n\n## People\n\n| Full name | Group |\n|---|---|\n| Jane Doe | maybe |\n",
            "no separator line": SMALL.replace("|---|---|\n", "") + "| Omar Ali | omar@def.example |\n",
        }
        for why, text in cases.items():
            with self.subTest(why):
                self.write_register(text)
                before = self.files()
                self.assert_refused(self.migrate(ok=False), "People not moved", text)
                self.assertEqual(self.files(), before, why)                  # not even a backup
                self.assert_refused(self.migrate("--dry-run", ok=False), "People not moved", text)

    def test_an_empty_extra_column_is_dropped(self):                          # nothing in it, nothing lost
        self.write_register("# People register\n\n## People\n\n| Full name | Email | Phone |\n|---|---|---|\n"
                            "| Jane Doe | jane.doe@client.com |  |\n")
        self.migrate()
        self.assertEqual(sorted(self.people()), ["Alan Carter", "Jane Doe"])
        self.assertNotIn("Phone", self.path(REGISTER).read_text(encoding="utf-8"))

    def test_a_failure_mid_way_writes_nothing(self):
        text = with_row(row("Kim Bad", "not an address"))                     # the last row the writer refuses
        self.write_register(text)
        self.private_moved()
        applies = self.applies()
        self.assert_refused(self.migrate(ok=False), "nothing was written", text)
        self.assertEqual(self.applies(), applies)
        with self.db() as con:
            self.assertEqual(con.execute("SELECT count(*) FROM change_log WHERE tbl = 'people'").fetchone()[0], 0)

    def test_a_pending_register_write_stops_it(self):
        self.write_register()
        self.private_moved()
        for decision, rel in (("pending", REGISTER), ("approved", REGISTER.replace("people-register", "People-Register"))):
            with self.subTest(decision):
                self.v.propose("old-style", [], file_changes={
                    "title": "People", "project": None, "file_changes_decision": decision,
                    "file_ops": [{"op": "write", "path": rel, "content": REG + "\n", "previous": REG}]})
                self.assert_refused(self.migrate(ok=False), "waiting in Review")
                self.assert_refused(self.migrate("--dry-run", ok=False), "waiting in Review")
        self.path("system/staging/proposed-old-style.json").unlink()
        self.migrate()
        self.apply(action(1, owner="Jane Doe"))                               # and the next full apply isn't blocked

    def test_a_dry_run_under_a_held_lock_says_so_plainly(self):
        self.write_register()
        self.private_moved()
        con = sqlite3.connect(self.path("system/tracker.db"), isolation_level=None)
        try:
            con.execute("BEGIN EXCLUSIVE")
            r = self.migrate("--dry-run", ok=False)
        finally:
            con.execute("ROLLBACK")
            con.close()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        self.assertIn("busy", r.stdout)

    def test_running_again_after_an_undo_records_no_hand_edit(self):
        self.write_register()
        self.private_moved()
        self.migrate()
        self.v.run("undo")
        out = self.migrate().stdout
        self.assertNotIn("edited by hand", out)
        self.assertNotIn("hand_edit", json.loads(self.path("system/staging/people-export.json").read_text()))
        self.assertEqual(list(self.path("system/backups").glob("files/people-register-hand-edit-*")), [])
        self.v.run("undo")
        self.assertEqual(self.path(REGISTER).read_text(encoding="utf-8"), REG)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "a read-only folder doesn't stop root")
    def test_a_failed_first_export_can_still_be_undone(self):
        self.write_register()
        self.private_moved()
        folder = self.path(REGISTER).parent
        mode = folder.stat().st_mode
        folder.chmod(0o555)                                               # the register can't be replaced
        try:
            out = self.migrate().stdout
        finally:
            folder.chmod(mode)
        self.assertIn("People moved", out)
        self.assertEqual(self.path(REGISTER).read_text(encoding="utf-8"), REG)
        with self.db() as con:
            ops = json.loads(con.execute("SELECT file_ops FROM applies ORDER BY apply_id DESC LIMIT 1").fetchone()[0])
        self.assertEqual([o["op"] for o in ops], ["people-register"])       # recorded before the write, never "[]"
        self.apply(action(1, owner="Jane Doe"))                           # the next save writes the register
        self.assertIn("Made by creaite", self.path(REGISTER).read_text(encoding="utf-8"))
        self.v.run("undo")
        self.v.run("undo")
        self.assertEqual(self.v.rows("people"), [])
        self.assertEqual(self.path(REGISTER).read_text(encoding="utf-8"), REG)


@APPLIED_ONLY
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
        self.assertEqual(len(by), 6)                                 # the register, Alan and Kim once
        self.assertIn("| Kim New |", self.path(REGISTER).read_text(encoding="utf-8"))
        self.v.run("undo")
        self.assertNotIn("Kim New", self.people())
        self.assertNotIn("Kim New", self.path(REGISTER).read_text(encoding="utf-8"))

    def test_an_nfd_or_upper_case_twin_is_no_new_person(self):
        self.apply(item(1, "people", {"name": "Élodie Durand"}))
        n = len(self.people())
        self.apply(action(1, owner=unicodedata.normalize("NFD", "Élodie Durand")), action(2, owner="ÉLODIE DURAND"))
        self.assertEqual(len(self.people()), n)

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

    def test_rename_carries_any_case_beyond_ascii(self):
        self.apply(item(1, "people", {"name": "Élodie Durand"}))
        self.apply(action(1, owner="ÉLODIE DURAND"), action(2, owner="élodie durand"),
                   action(3, owner=unicodedata.normalize("NFD", "Élodie Durand")))
        self.apply(change(1, "people", self.pid("Élodie Durand"), {"name": "Élodie Martin"}, op="rename"))
        self.assertEqual([a["owner"] for a in self.v.rows("actions")], ["Élodie Martin"] * 3)

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

    def test_merge_joins_labels_and_projects(self):
        self.apply(change(1, "people", self.pid("Jane Doe"), {}, op="merge", into=self.pid("Omar Ali")))
        o = self.people()["Omar Ali"]
        self.assertEqual((json.loads(o["labels"]), json.loads(o["projects_add"]), json.loads(o["projects_remove"])),
                         (["Sensitive"], ["ABC"], ["ABC"]))

    def test_rename_onto_someone_else_is_refused(self):
        out = self.apply(change(1, "people", self.pid("Omar Ali"), {"name": "jane doe"}, op="rename")).stdout
        self.assertIn("Held in Review", out)
        self.assertIn("merge", out)

    def test_a_proposal_cannot_write_the_register_once_it_is_made(self):
        before = self.path(REGISTER).read_bytes()
        for rel in (REGISTER, REGISTER.replace("people-register", "People-Register")):     # a case-insensitive disk: one file
            with self.subTest(rel):
                self.v.propose("old-style", [], file_changes={
                    "title": "People", "project": None, "file_changes_decision": "approved",
                    "file_ops": [{"op": "write", "path": rel, "content": "# People\n", "previous": before.decode()}]})
                r = self.v.run("apply", ok=False)
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("made from your project record", r.stdout)
                self.assertEqual(self.path(REGISTER).read_bytes(), before)

    def test_export_is_stable_and_a_hand_edit_is_kept(self):
        reg = self.path(REGISTER)
        first = reg.read_bytes()
        self.apply(action(1, owner="Jane Doe"))
        self.assertEqual(reg.read_bytes(), first)                           # nothing about people changed
        reg.write_text(first.decode() + "| Hand Made | | | | | | | | |\n", encoding="utf-8")
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
