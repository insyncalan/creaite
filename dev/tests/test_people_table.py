"""F3 (2.6.4): the people table's logic: stable IDs, the importer, the generated Markdown copy, the private VIP and Hidden file.

Run: python3 dev/tests/test_people_table.py
Pure functions and throwaway folders only; nothing here touches a vault or a database.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import people_table as pt  # noqa: E402
import person_id  # noqa: E402

FIXTURE = REPO / "dev" / "proposals" / "f3" / "fixture" / "people-register.md"
TEXT = FIXTURE.read_text(encoding="utf-8")


def big_register(n):
    """A register of n fictional people."""
    rows = ["| Full name | Email | Aliases | Organisation | Role | Hidden | VIP | Labels | Desk |", "|---|---|---|---|---|---|---|---|---|"]
    rows += [f"| Person {i} Example | person{i}@brightwater.example | P{i} | Org {i % 20} | Role {i % 7} | "
             f"{'yes' if i % 50 == 0 else ''} | {'client' if i % 97 == 0 else ''} | | D{i} |" for i in range(n)]
    return "# People register\n\n## People\n\n" + "\n".join(rows) + "\n\nNotes:\n- demo\n"


class StableId(unittest.TestCase):
    def test_known_value(self):
        import hashlib
        self.assertEqual(person_id.person_id("a@b.example"), hashlib.sha256(b"a@b.example").hexdigest()[:16])
        self.assertEqual(len(person_id.person_id("a@b.example")), 16)

    def test_case_and_space_insensitive(self):
        self.assertEqual(person_id.person_id("  Alex.Example@Brightwater.EXAMPLE "), person_id.person_id("alex.example@brightwater.example"))

    def test_first_address_sets_the_id(self):
        self.assertEqual(person_id.person_id("a@b.example, c@d.example"), person_id.person_id("a@b.example"))

    def test_no_email_gives_no_email_id(self):
        self.assertEqual(person_id.person_id(""), "")
        self.assertEqual(person_id.person_id(None), "")

    def test_fallback_is_deterministic_and_never_an_email_id(self):
        a = person_id.fallback_id("Dev  Placeholder (Enable)")
        self.assertEqual(a, person_id.fallback_id("dev placeholder"))
        self.assertEqual((len(a), a[0], person_id.is_fallback(a)), (16, "n", True))
        self.assertFalse(person_id.is_fallback(person_id.person_id("x@y.example")))
        self.assertEqual(person_id.fallback_id(" "), "")

    def test_javascript_twin_agrees(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        js = REPO / "dev" / "proposals" / "f3" / "person_id.js"
        cases = ["a@b.example", "  Alex.Example@Brightwater.EXAMPLE ", "a@b.example; c@d.example", "é@ü.example", "", "x" * 200 + "@y.example"]
        names = ["Dev  Placeholder (Enable)", "Ana-María O'Example", "", "A. B., C"]
        code = (f"const m=require({json.dumps(str(js))});console.log(JSON.stringify([{json.dumps(cases)}.map(m.personId),"
                f"{json.dumps(names)}.map(m.fallbackId)]))")
        got = json.loads(subprocess.run([node, "-e", code], capture_output=True, text=True, check=True).stdout)
        self.assertEqual(got, [[person_id.person_id(c) for c in cases], [person_id.fallback_id(n) for n in names]])


class Importer(unittest.TestCase):
    def setUp(self):
        self.people, self.private, self.flags = pt.parse_register(TEXT)
        self.by = {p["name"]: p for p in self.people}

    def test_people_and_ids(self):
        self.assertEqual(len(self.people), 6)
        alex = self.by["Alex Example"]
        self.assertEqual(alex["id"], person_id.person_id("alex.example@brightwater.example"))
        self.assertEqual(alex["aliases"], ["Alex", "AE"])
        self.assertEqual(self.by["Bea Sample"]["emails"], ["bea.sample@northgate.example", "b.sample@northgate-old.example"])
        self.assertEqual(self.by["Bea Sample"]["id"], person_id.person_id("bea.sample@northgate.example"))

    def test_case_and_spaces_in_the_email(self):
        self.assertEqual(self.by["Eli Fictional"]["id"], person_id.person_id("eli.fictional@brightwater.example"))

    def test_no_email_gets_a_fallback_id_and_a_flag(self):
        dev = self.by["Dev Placeholder"]
        self.assertEqual((dev["id"], dev["id_source"]), (person_id.fallback_id("Dev Placeholder"), "name"))
        self.assertEqual([f["name"] for f in self.flags], ["Dev Placeholder"])
        self.assertIn("no email", self.flags[0]["reason"])

    def test_unknown_columns_are_kept(self):
        self.assertEqual(self.by["Alex Example"]["extra"], {"Slack": "Slack handle", "Desk": "@alex"})
        self.assertNotIn("Hidden", self.by["Alex Example"]["extra"])
        self.assertNotIn("VIP", self.by["Alex Example"]["extra"])

    def test_vip_and_hidden_go_to_the_private_values(self):
        self.assertEqual(self.private, {self.by["Bea Sample"]["id"]: {"vip": "management"},
                                        self.by["Casey Demo"]["id"]: {"hidden": True},
                                        self.by["Eli Fictional"]["id"]: {"vip": "client"}})
        for p in self.people:
            self.assertFalse({"hidden", "vip"} & set(p))

    def test_two_rows_with_one_address_get_distinct_ids(self):
        lines = TEXT.splitlines()
        i = max(n for n, ln in enumerate(lines) if ln.startswith("| Fran Test"))
        lines.insert(i + 1, "| Alex Twin | ALEX.example@brightwater.example |  |  |  |  |  |  |  |  |")
        people, _, flags = pt.parse_register("\n".join(lines))
        ids = [p["id"] for p in people]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(any("same email" in f["reason"] for f in flags))

    def test_a_register_with_no_table(self):
        self.assertEqual(pt.parse_register("# nothing here\n"), ([], {}, []))


class Generator(unittest.TestCase):
    def test_round_trip(self):
        people, _, _ = pt.parse_register(TEXT)
        md = pt.render_register(people)
        again, _, _ = pt.parse_register(md)
        self.assertTrue(pt.same_people(people, again))
        self.assertEqual(pt.render_register(again), md)                  # and the text is stable too

    def test_round_trip_with_the_existing_file_kept(self):
        people, _, _ = pt.parse_register(TEXT)
        md = pt.render_register(people, TEXT)
        self.assertIn("Demo register.", md)
        self.assertTrue(pt.same_people(people, pt.parse_register(md)[0]))

    def test_vip_and_hidden_are_not_in_the_shared_copy(self):
        people, private, _ = pt.parse_register(TEXT)
        for md in (pt.render_register(people), pt.render_register(pt.overlay(people, private), TEXT)):
            head = [ln for ln in md.splitlines() if ln.startswith("| Full name")][0]
            self.assertNotIn("VIP", head)
            self.assertNotIn("Hidden", head)
            for word in ("management", "yes"):
                self.assertNotIn("| " + word + " |", md)
        self.assertNotIn("Casey Demo | casey.demo@enable.example | CD | Enable Example | Project manager | yes", md)

    def test_extras_survive_and_pipes_are_made_safe(self):
        people, _, _ = pt.parse_register(TEXT)
        people[0]["role"] = "Lead | sponsor"
        people[0]["extra"]["New col"] = "x"
        again, _, _ = pt.parse_register(pt.render_register(people))
        self.assertEqual(again[0]["role"], "Lead / sponsor")
        self.assertEqual(again[0]["extra"]["New col"], "x")
        self.assertEqual(again[1]["extra"].get("New col", ""), "")

    def test_a_row_with_a_second_address_keeps_both(self):
        people, _, _ = pt.parse_register(TEXT)
        again, _, _ = pt.parse_register(pt.render_register(people))
        self.assertEqual([p["emails"] for p in again], [p["emails"] for p in people])


class Plan(unittest.TestCase):
    def test_first_import_inserts_everyone_and_a_second_changes_nothing(self):
        people, _, _ = pt.parse_register(TEXT)
        first = pt.plan_import([], people)
        self.assertEqual((len(first["insert"]), first["update"], first["remove"]), (6, [], []))
        second = pt.plan_import(people, people)
        self.assertEqual((second["insert"], second["update"], second["remove"], second["same"]), ([], [], [], 6))

    def test_edit_and_removal(self):
        people, _, _ = pt.parse_register(TEXT)
        new = [dict(p) for p in people[1:]]
        new[0] = {**new[0], "role": "Changed"}
        plan = pt.plan_import(people, new)
        self.assertEqual(([p["name"] for p in plan["update"]], plan["remove"]), (["Bea Sample"], [people[0]["id"]]))

    def test_adding_an_email_rekeys_the_person(self):
        people, _, _ = pt.parse_register(TEXT)
        new = [dict(p) for p in people]
        dev = [p for p in new if p["name"] == "Dev Placeholder"][0]
        dev.update(emails=["dev.placeholder@enable.example"], id=person_id.person_id("dev.placeholder@enable.example"), id_source="email")
        plan = pt.plan_import(people, new)
        old = person_id.fallback_id("Dev Placeholder")
        self.assertEqual(plan["rekeyed"], [(old, dev["id"], "Dev Placeholder")])
        self.assertEqual(plan["remove"], [old])
        self.assertEqual(len(plan["insert"]), 1)


class PrivateFile(unittest.TestCase):
    def test_save_load_and_overlay(self):
        with tempfile.TemporaryDirectory() as d:
            path = pt.private_path(d)
            people, private, _ = pt.parse_register(TEXT)
            self.assertEqual(pt.load_private(path), {})
            pt.save_private(path, private)
            self.assertEqual(pt.load_private(path), private)
            self.assertEqual(path.relative_to(d).as_posix(), "system/staging/people-private.json")
            ov = {p["name"]: p for p in pt.overlay(people, pt.load_private(path))}
            self.assertEqual((ov["Bea Sample"]["vip"], ov["Casey Demo"]["hidden"], ov["Alex Example"]["vip"]), ("management", True, ""))

    def test_bad_file_is_empty_and_the_laptops_own_choice_wins(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "p.json"
            path.write_text("not json", encoding="utf-8")
            self.assertEqual(pt.load_private(path), {})
        self.assertEqual(pt.merge_private({"a": {"vip": "client"}}, {"a": {"vip": "x"}, "b": {"hidden": True}}),
                         {"a": {"vip": "client"}, "b": {"hidden": True}})

    def test_the_private_file_is_in_the_backup_exclusion_proposal(self):
        diff = (REPO / "dev" / "proposals" / "f3" / "backup.diff").read_text(encoding="utf-8")
        self.assertIn("system/staging/people-private.json", diff)


class Scale(unittest.TestCase):
    def test_a_thousand_people_round_trip_is_quick(self):
        text = big_register(1000)
        t0 = time.perf_counter()
        people, private, flags = pt.parse_register(text)
        md = pt.render_register(people, text)
        again, _, _ = pt.parse_register(md)
        plan = pt.plan_import(people, again)
        took = time.perf_counter() - t0
        self.assertEqual((len(people), len(flags), plan["same"]), (1000, 0, 1000))
        self.assertEqual(len(private), 20 + 11 - 1)                     # hidden every 50th, vip every 97th, person 0 is both
        self.assertLess(took, 2.0, f"took {took:.2f}s")


if __name__ == "__main__":
    unittest.main()
