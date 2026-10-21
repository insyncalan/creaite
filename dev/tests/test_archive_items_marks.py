"""BL-10 fixes (v1.9.5, hand checks 24 to 28; board #81): how an item archived for its age is named and marked.

Run: python3 dev/tests/test_archive_items_marks.py     (quick tier: no Chrome)

- Activity's "By" for the daily archiving is "Archived for age", not "Approved in review": the apply records its source as
  "archive" (an age-archive only; Alan's own edits, VIA_NAMES, are unchanged).
- With Show archived on, the page's records carry the flag (`ar`), for an age-archived item and an archived project's item.
- /api/records with aged=1 hands the page an age-archived item of a live project (so search can open it), never an archived
  project's item; without it both stay missing.
- Search says which archived items belong to an archived project (`project_archived` in `opens`).
- Ticking an age-archive's rows in Activity is refused with words that fit: undo the archive apply, or edit the item.
- The settings catalogue names the switch as built, where it is, and mentions items archived for their age.
Everything is fictional and temporary.
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
from test_archive_items import DAY, SEED  # noqa: E402
from test_tracker import Vault  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


class AgeArchiveMarks(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.v.propose("seed", SEED)
        self.v.run("apply")
        self.ids = {}
        for t in ("actions", "raid", "promises"):
            for r in self.v.rows(t):
                self.ids[r["description"]] = r["id"]
        self.sh(DAY, "daily", script="archive.py")

    def tearDown(self):
        self.v.cleanup()

    def sh(self, day, *args, script="tracker.py", ok=True):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts" / script), *args], capture_output=True,
                           text=True, cwd=self.v.root, env={**os.environ, "CREAITE_NOW": day})
        if ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def py(self, code):
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); " + code],
                           cwd=self.v.root, capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": DAY})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def show_archived(self, on=True):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data.setdefault("dashboard", {})["show_archived"] = on
        cfg.write_text(json.dumps(data, indent=2))

    def archive_project(self):
        spec = self.sh(DAY, "archive", "ABC", "--cancel-open", script="propose.py").stdout
        f = self.v.root / "system/staging/drafts/a.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(spec, encoding="utf-8")
        self.sh(DAY, "stage", str(f), script="propose.py")
        self.sh(DAY, "apply")

    # --- check 24 ---
    def test_activity_names_the_daily_archiving(self):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            vias = {r[0] for r in con.execute("SELECT via FROM change_log WHERE field = 'archived'")}
        self.assertEqual(vias, {"archive"})
        lines = self.py("import build_dashboard as b, sqlite3; con = b.ro_db(); con.row_factory = sqlite3.Row; "
                        "print(json.dumps([[a['id'], a['by']] for a in b.activity(con) if 'rchived' in a['change']]))")
        self.assertEqual(len(lines), 5, lines)
        self.assertEqual({by for _, by in lines}, {"Archived for age"})
        import importlib
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        tracker = importlib.import_module("tracker")
        self.assertNotIn("archive", tracker.VIA_NAMES)         # not one of Alan's own edits (promises' last touched)

    def test_a_report_archive_with_no_items_keeps_its_file_name(self):
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        import tracker
        self.assertEqual(tracker.via_for(Path("proposed-x-archive.json"),
                                         {"source_run": "archive", "items": [{"op": "archive_item"}]}), "archive")
        self.assertEqual(tracker.via_for(Path("proposed-y.json"), {"source_run": "archive", "items": []}), "proposed-y.json")

    # --- check 26 ---
    def test_shown_records_carry_the_archived_flag(self):
        self.show_archived()
        got = self.py("import build_dashboard as b; d = b.collect(); "
                      "print(json.dumps({x['id']: x.get('ar', False) for x in d['actions'] + d['raid']}))")
        self.assertIs(got[self.ids["Closed on the boundary"]], True)
        self.assertIs(got[self.ids["Risk closed long ago"]], True)
        self.assertIs(got[self.ids["Open for ages"]], False)
        self.show_archived(False)
        got = self.py("import build_dashboard as b; d = b.collect(); print(json.dumps([x['id'] for x in d['actions'] if 'ar' in x]))")
        self.assertEqual(got, [])                               # off: nothing archived is in the page at all

    def test_an_archived_projects_items_are_flagged_too(self):
        self.archive_project()
        self.show_archived()
        got = self.py("import build_dashboard as b; d = b.collect(); "
                      "print(json.dumps([x.get('ar', False) for x in d['actions'] + d['raid'] + d['decisions']]))")
        self.assertTrue(got and all(got), got)

    # --- check 27 ---
    def test_records_hand_over_an_age_archived_item_only_when_asked(self):
        aid = self.ids["Closed on the boundary"]
        got = self.py(f"import build_dashboard as b; r = b.records(['{aid}']); print(json.dumps([r['missing'], r['records']['actions']]))")
        self.assertEqual(got, [[aid], []])
        got = self.py(f"import build_dashboard as b; r = b.records(['{aid}'], aged=True); "
                      "print(json.dumps([r['missing'], r['records']['actions']]))")
        self.assertEqual(got[0], [])
        self.assertEqual([(x["id"], x["ar"]) for x in got[1]], [(aid, True)])

    def test_records_never_hand_over_an_archived_projects_item(self):
        self.archive_project()
        oid = self.ids["Open for ages"]
        got = self.py(f"import build_dashboard as b; r = b.records(['{oid}'], aged=True); print(json.dumps(r['missing']))")
        self.assertEqual(got, [oid])

    def test_the_records_route_takes_aged(self):
        text = (REPO / "system/scripts/live_server.py").read_text(encoding="utf-8")
        route = text[text.index("def records_route"):text.index("# ===== end BL-304")]
        self.assertIn('"aged"', route)
        self.assertIn("aged=", route)

    def test_search_says_whose_project_is_archived(self):
        out = json.loads(self.sh(DAY, "query", "boundary", script="search.py").stdout)
        r = next(r for rs in out["groups"].values() for r in rs if r.get("id") == self.ids["Closed on the boundary"])
        self.assertTrue(r["opens"]["archived"])
        self.assertNotIn("project_archived", r["opens"])
        self.archive_project()
        out = json.loads(self.sh(DAY, "query", "ages", script="search.py").stdout)
        r = next(r for rs in out["groups"].values() for r in rs if r.get("id") == self.ids["Open for ages"])
        self.assertTrue(r["opens"]["archived"])
        self.assertTrue(r["opens"]["project_archived"])

    # --- check 28 ---
    def test_ticking_an_age_archive_says_how_to_bring_it_back(self):
        aid = self.ids["Closed on the boundary"]
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            rid = con.execute("SELECT rowid FROM change_log WHERE item_id = ? AND field = 'archived'", (aid,)).fetchone()[0]
        r = self.v.run("undo-changes", "--json", str(rid), ok=False)
        got = json.loads([x for x in r.stdout.splitlines() if x.startswith("{")][-1])
        self.assertEqual(got["done"], [])
        why = got["skipped"][0]["why"]
        self.assertNotIn("archiving or restoring the project", why)
        self.assertIn("archived for its age", why)
        self.assertIn("Undo", why)
        self.assertIn("edit the item", why)

    # --- the switch, as built (BL-10's write-up names no place for it) ---
    def test_the_catalogue_names_the_built_switch(self):
        sys.path.insert(0, str(REPO / "system/scripts"))
        import settings_catalogue as sc
        group, label, line, reason = sc.CATALOGUE["dashboard.show_archived"]
        self.assertEqual(label, "Show archived projects")
        self.assertIn("in Work, Today and the Excel export", line)              # v2.6 (#246): it names what it shows, not a tab
        self.assertIn("archived for their age", line)
        src = (REPO / "system/templates/dashboard/src/settings.js").read_text(encoding="utf-8")
        help_ = src[src.index('row("Show archived projects"'):][:300]
        self.assertIn("archived for their age", help_)


if __name__ == "__main__":
    unittest.main()
