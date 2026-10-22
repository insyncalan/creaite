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

    # ── Cap's review of #279 ──────────────────────────────────────────────────
    def built_for(self, code, note):
        self.remember(code)
        return py(self.v, f"import prep_page; rel, _ = prep_page.build({self.key!r}, {{'about': {code + ' research'!r}, "
                          f"'notes': [{{'text': {note!r}}}]}}); print(json.dumps(rel))")

    def test_research_done_for_another_project_is_not_shown_under_the_new_one(self):
        """A reply researched for ABC never shows under DEF once the series is switched: it is flagged, never mixed in."""
        rel = self.built_for("ABC", "ABC only note")
        self.remember("DEF")
        v = py(self.v, f"import prep_view; v = prep_view.view({self.key!r}); mo = v['model']; "
                       f"print(json.dumps([mo['meeting']['project'], mo['about'], [n.get('text') for n in mo['notes']], v['saved'], "
                       f"v.get('stale'), v['stored']]))")
        project, about, notes, saved, stale, stored = v
        self.assertEqual(project, "DEF")
        self.assertEqual((about, notes, saved, stored), ("", [], None, False))
        self.assertEqual((stale or {}).get("project"), "ABC")
        self.assertTrue((stale or {}).get("project_name"))
        self.assertTrue((self.v.root / rel).exists(), "the earlier page is kept")

    def test_regenerate_never_refiles_another_projects_research(self):
        rel = self.built_for("ABC", "ABC only note")
        before = (self.v.root / rel).read_bytes()
        self.remember("DEF")
        day = py(self.v, f"import prep_page; print(json.dumps(prep_page.context({self.key!r})['day']))")
        out = py(self.v, f"import prep_view; print(json.dumps(prep_view.regenerate({self.key!r}, {day!r})))")
        self.assertIsNone(out)
        self.assertEqual((self.v.root / rel).read_bytes(), before)
        self.assertFalse(list((self.v.root / "projects").glob("DEF*/agendas/*Prep*")))

    def test_a_remembered_code_that_is_no_project_any_more_is_not_chosen_and_builds(self):
        """An unknown, removed or archived code opens as not chosen (the picker asks again) and the page still builds."""
        self.remember("ZZZ")
        c = self.ctx()
        self.assertEqual((c["error"], c["project"], c["chosen"]), (None, "_portfolio", False))
        rel = py(self.v, f"import prep_page; rel, _ = prep_page.build({self.key!r}, {{'about': 'x'}}); print(json.dumps(rel))")
        self.assertTrue(rel.startswith("projects/_portfolio/"), rel)

    def test_place_gives_a_readable_error_for_a_project_with_no_folder(self):
        out = py(self.v, "import prep_page\ntry:\n    prep_page.place({'project': 'ZZZ', 'day': '2026-10-22', 'key': 'k', "
                         "'meeting': {'title': 'T'}})\n    print(json.dumps('placed'))\nexcept ValueError as e:\n    print(json.dumps('ValueError'))")
        self.assertEqual(out, "ValueError")

    def test_two_meetings_with_one_title_on_one_day_keep_their_own_pages(self):
        """Same title, same day, no project: the second never replaces the first's page."""
        self.remember("_portfolio")
        cal = self.v.root / "system/staging/calendar.json"
        data = json.loads(cal.read_text())
        for evs in data["days"].values():
            evs.append({**evs[0], "id": "t2", "start": "11:00", "end": "12:00"})
        cal.write_text(json.dumps(data))
        one = py(self.v, f"import prep_page; rel, _ = prep_page.build({self.key!r}, {{'about': 'first'}}); print(json.dumps(rel))")
        two = py(self.v, f"import prep_page; rel, _ = prep_page.build({('11:00|' + TITLE)!r}, {{'about': 'second'}}); print(json.dumps(rel))")
        self.assertNotEqual(one, two)
        self.assertIn("first", (self.v.root / one).read_text())
        again = py(self.v, f"import prep_page; rel, _ = prep_page.build({('11:00|' + TITLE)!r}, {{'about': 'again'}}); print(json.dumps(rel))")
        self.assertEqual(again, two, "a meeting's own page is still replaced")

    def test_no_project_is_called_no_project(self):
        self.remember("_portfolio")
        c = py(self.v, f"import prep_page; print(json.dumps(prep_page.context({self.key!r})['project_name']))")
        self.assertEqual(c, "No project")


if __name__ == "__main__":
    unittest.main()
