"""Leak fix (Cap's M4): a confidential meeting whose title names a project, with nothing remembered, builds a Prep page and an
agenda end to end without the project: the page and the agenda file in the portfolio's Agendas folder, and the context, the stored
content and prep-pages.json hold no project. Once Alan remembers the project, the same meeting files in its folder.

Run: python3 dev/tests/test_confidential_end_to_end.py   (no browser, no model; the clock is test_dashboard.today())
Kills Cap's mutant M4c: context() taking back a matched project after _project_of.
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_decisions_prep import prep_world  # noqa: E402
from test_prep_reimagined import py  # noqa: E402
from test_tracker import Vault  # noqa: E402

TITLE = "ABC weekly"
KEY = f"09:00|{TITLE}"
REPLY = "{'about': 'x', 'notes': [{'text': 'a note'}]}"


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        prep_world(self.v)
        cal = self.v.root / "system/staging/calendar.json"
        data = json.loads(cal.read_text())
        for evs in data["days"].values():
            evs[0]["sensitivity"] = "confidential"
        cal.write_text(json.dumps(data))

    def tearDown(self):
        self.v.cleanup()

    def remember(self, code):
        py(self.v, f"import paths; p = paths.ROOT / 'system/config/settings.json'; s = json.loads(p.read_text()); "
                   f"s.setdefault('prep', {{}}).setdefault('series', {{}})['abc weekly'] = {code!r}; "
                   f"p.write_text(json.dumps(s)); print(json.dumps(1))")

    def run_all(self):
        return py(self.v, f"import prep_page; c = prep_page.context({KEY!r}); rel, html = prep_page.build({KEY!r}, {REPLY}); "
                          f"ag = prep_page.save_agenda({KEY!r}, {{'agenda': [{{'point': 'p', 'minutes': 5}}]}}); "
                          f"print(json.dumps({{'project': c['project'], 'chosen': c['chosen'], 'name': c['project_name'], "
                          f"'ctx': json.dumps(c), 'rel': rel, 'agenda': ag}}))")

    def test_a_guessed_project_files_in_the_portfolio_and_is_kept_out_of_every_record(self):
        r = self.run_all()
        self.assertEqual((r["project"], r["chosen"], r["name"]), ("_portfolio", False, "No project"))
        self.assertTrue(r["rel"].startswith("projects/_portfolio/"), r["rel"])
        self.assertTrue(r["agenda"].startswith("projects/_portfolio/"), r["agenda"])
        root = self.v.root
        self.assertFalse(list((root / "projects").glob("ABC*/agendas/*")), "nothing in the guessed project's Agendas folder")
        self.assertEqual(json.loads(r["ctx"])["project"], "_portfolio")      # the all-projects view lists every project's items
        registry = (root / "system/staging/prep-pages.json").read_text()
        self.assertNotIn("ABC/", registry.replace("ABC weekly", ""))
        stored = [json.loads(f.read_text()) for f in (root / "system/staging/prep").glob("*.json")]
        self.assertTrue(stored)
        for rec in stored:
            self.assertEqual(rec["project"], "_portfolio")

    def test_a_remembered_project_files_in_its_folder(self):
        self.remember("ABC")
        r = self.run_all()
        self.assertEqual((r["project"], r["chosen"]), ("ABC", True))
        self.assertIn("/agendas/", r["rel"])
        self.assertFalse(r["rel"].startswith("projects/_portfolio/"), r["rel"])
        self.assertFalse(r["agenda"].startswith("projects/_portfolio/"), r["agenda"])


if __name__ == "__main__":
    unittest.main()
