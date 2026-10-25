"""#341 hardening (Wanda's LOW 9): a saved sort refuses __proto__ and constructor, folded groups nobody is in any more are pruned,
and the Display menu escapes a column key. Runs the rules under Node and reads the menu's source; no browser.
Run: python3 dev/tests/test_v265_341_hardening.py
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

CORE = Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/core"


def node(js):
    r = subprocess.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@unittest.skipUnless(shutil.which("node"), "needs Node")
class Hardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        js = """const f = await import(%s); const o = {};
        const P = (n, org, role, on) => ({ n, org, role, on, late: 0, missing: [] });
        const rows = [P("Ann", "Acme", "PM", ["ABC"]), P("Cy", "Acme", "Dev", ["ABC"])];
        const name = c => "Project " + c;
        o.sorts = ["__proto__", "constructor", "toString", "hasOwnProperty", "late"].map(c => f.pdSort({ col: c, dir: "asc" }).col);
        o.nonString = [f.pdSort({ col: ["late"], dir: "asc" }).col, f.pdSort({ col: 7, dir: "asc" }).col, f.pdSort(null).col];
        const st = f.pdNormalise({ group: "org", sub: "role", collapsed: { [f.pdKey("org", "Acme")]: true, [f.pdKey("org", "Gone Ltd")]: true,
          [f.pdKey("org", "Acme", "role", "PM")]: true, [f.pdKey("org", "Acme", "role", "Nobody")]: true, "proj|ABC": true } });
        o.before = Object.keys(st.collapsed).sort();
        o.dropped = f.pdPrune(st, rows, name); o.after = Object.keys(st.collapsed).sort();
        const none = f.pdNormalise({ group: "none", collapsed: { "org|Gone Ltd": true } }); o.noneDropped = f.pdPrune(none, rows, name); o.noneKept = Object.keys(none.collapsed);
        o.sameAgain = f.pdPrune(st, rows, name);
        const sw = f.pdNormalise({ group: "role", collapsed: { "org|Acme": true, "role|PM": true, "role|Gone": true } });
        o.otherDropped = f.pdPrune(sw, rows, name); o.otherKept = Object.keys(sw.collapsed).sort();
        console.log(JSON.stringify(o));""" % json.dumps((CORE / "peopleDisplay.js").as_uri())
        cls.o = node(js)

    def test_a_saved_sort_on_an_inherited_name_falls_back(self):
        self.assertEqual(self.o["sorts"], ["late", "late", "late", "late", "late"])   # the default sort column is late; only "late" is a real own key
        self.assertEqual(self.o["nonString"], ["late", "late", "late"])

    def test_folds_of_groups_nobody_is_in_are_dropped(self):
        self.assertEqual(len(self.o["before"]), 5)
        self.assertEqual(self.o["dropped"], 2)
        self.assertEqual(self.o["after"], ["org|Acme", "org|Acme|role|PM", "proj|ABC"])   # the project folds belong to another grouping: kept
        self.assertEqual(self.o["sameAgain"], 0)

    def test_switching_grouping_does_not_lose_the_other_groupings_folds(self):
        self.assertIn("proj|ABC", self.o["after"])
        self.assertEqual(self.o["otherKept"], ["org|Acme", "role|PM"])
        self.assertEqual(self.o["otherDropped"], 1)

    def test_no_grouping_keeps_the_folds_for_later(self):
        self.assertEqual((self.o["noneDropped"], self.o["noneKept"]), (0, ["org|Gone Ltd"]))

    def test_the_menu_escapes_a_column_key(self):
        src = (CORE / "displayMenu.js").read_text(encoding="utf-8")
        self.assertIn('id="${esc(prefix)}-${esc(c[0])}" value="${esc(c[0])}"', src)
        self.assertEqual(src.count('data-mv="${esc(c[0])}"'), 2)
        self.assertNotIn('data-mv="${c[0]}"', src)
        self.assertNotIn('value="${c[0]}"', src)


if __name__ == "__main__":
    unittest.main()
