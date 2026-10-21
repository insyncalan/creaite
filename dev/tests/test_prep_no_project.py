"""#279: a prep page always opens, even for a meeting with no project.

Run: python3 dev/tests/test_prep_no_project.py   (no browser, no model)
A meeting nobody matched to a project opens its page in the all-projects view with chosen False (the page's Project chip is then
a picker). "No project (general meeting)" is the saved value "_portfolio" in settings prep.series: chosen True, the same
all-projects view, and the page is filed in the portfolio's Agendas folder. A real project chosen files in its own folder.
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

TITLE = "Quarterly catch-up"


class NoProject(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        prep_world(self.v)
        cal = self.v.root / "system/staging/calendar.json"
        data = json.loads(cal.read_text())
        for evs in data["days"].values():
            evs[0]["title"] = TITLE
        cal.write_text(json.dumps(data))
        self.key = f"09:00|{TITLE}"

    def tearDown(self):
        self.v.cleanup()

    def remember(self, code):
        py(self.v, f"import paths; p = paths.SETTINGS if hasattr(paths, 'SETTINGS') else paths.ROOT / 'system/config/settings.json'; "
                   f"s = json.loads(p.read_text()); s.setdefault('prep', {{}}).setdefault('series', {{}})['quarterly catch up'] = {code!r}; "
                   f"p.write_text(json.dumps(s)); print(json.dumps(1))")

    def ctx(self):
        return py(self.v, f"import prep_page; c = prep_page.context({self.key!r}); print(json.dumps({{k: c.get(k) for k in "
                          f"('error', 'project', 'chosen', 'series')}}))")

    def test_no_project_still_opens_and_is_not_chosen(self):
        c = self.ctx()
        self.assertIsNone(c["error"])
        self.assertEqual((c["project"], c["chosen"]), ("_portfolio", False))
        self.assertTrue(c["series"])

    def test_no_project_chosen_is_a_saved_value_apart_from_not_chosen(self):
        self.remember("_portfolio")
        c = self.ctx()
        self.assertEqual((c["error"], c["project"], c["chosen"]), (None, "_portfolio", True))

    def test_a_project_chosen_is_remembered_and_filed_in_its_own_folder(self):
        self.remember("ABC")
        c = self.ctx()
        self.assertEqual((c["project"], c["chosen"]), ("ABC", True))

    def test_the_page_is_filed_in_the_portfolio_agendas_folder(self):
        self.remember("_portfolio")
        rel = py(self.v, f"import prep_page; rel, _ = prep_page.build({self.key!r}, {{'about': 'x'}}); print(json.dumps(rel))")
        self.assertTrue(rel.startswith("projects/_portfolio/"), rel)
        self.assertTrue((self.v.root / rel).exists())
        view = py(self.v, f"import prep_view; v = prep_view.view({self.key!r}); m = v['model']['meeting']; "
                          f"print(json.dumps([v['ok'], m['chosen'], m['project'], m['series']]))")
        self.assertEqual(view[:3], [True, True, "_portfolio"])


if __name__ == "__main__":
    unittest.main()
