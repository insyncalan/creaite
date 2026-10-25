"""#362: nothing persisted or sent takes a confidential meeting's project from a guess (dev/proposals/362/PERSISTED-PATHS.md).

Run: python3 dev/tests/test_confidential_persisted.py   (no browser, no model)
Every writer and sender goes through prep_page.context, whose project comes from prep_page._project_of: a confidential meeting's
counts only when Alan chose it (how "remembered"). One test per persisted path: the Agendas folder, prep-pages.json, the stored
content; and the sent paths through the context.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
import paths  # noqa: E402,F401
import prep_page  # noqa: E402
import prep_view  # noqa: E402

D = {"projects": [{"code": "ABC", "name": "Harbour Upgrade"}, {"code": "DEF", "name": "Orchard Rollout"}]}


def entry(how, conf=True, p="DEF"):
    return {"p": p, "how": how, "invite": {"confidential": conf}}


class Chosen(unittest.TestCase):
    def test_a_guess_is_not_a_project_for_a_confidential_meeting(self):
        for how in ("matched", "likely", "unsure"):
            self.assertEqual(prep_page._project_of(D, entry(how)), ("_portfolio", False), how)

    def test_a_remembered_choice_counts(self):
        self.assertEqual(prep_page._project_of(D, entry("remembered")), ("DEF", True))
        self.assertEqual(prep_page._project_of(D, entry("remembered", p="_portfolio")), ("_portfolio", True))

    def test_an_ordinary_meeting_is_unchanged(self):
        self.assertEqual(prep_page._project_of(D, entry("matched", conf=False)), ("DEF", True))

    def test_context_takes_its_project_from_it(self):
        src = Path(prep_page.__file__).read_text()
        self.assertIn("code, chosen = _project_of(d, m)", src)


class Persisted(unittest.TestCase):
    ctx = None

    def setUp(self):
        code, chosen = prep_page._project_of(D, entry("matched"))
        self.ctx = {"key": "10:00|x", "day": "2026-10-26", "project": code, "chosen": chosen, "series": "x",
                    "meeting": {"title": "[DEF] x"}, "project_name": prep_page.NO_PROJECT}

    def test_agendas_folder_is_the_portfolios(self):
        asked = []
        orig = paths.folder
        paths.folder = lambda code, kind: (asked.append((code, kind)), Path(tempfile.mkdtemp()))[1]
        try:
            prep_page.place(self.ctx)
        finally:
            paths.folder = orig
        self.assertEqual(asked, [("_portfolio", "agendas")])

    def test_registry_record_names_no_project(self):
        orig = (prep_page.REGISTRY, paths.rel)
        tmp = Path(tempfile.mkdtemp())
        prep_page.REGISTRY = tmp / "prep-pages.json"
        paths.rel = lambda p: str(p)
        try:
            prep_page.record(self.ctx, tmp / "Portfolio" / "page.html", b"x")
            text = prep_page.REGISTRY.read_text()
        finally:
            prep_page.REGISTRY, paths.rel = orig
        self.assertNotIn("DEF", text)
        self.assertNotIn("Orchard", text)

    def test_stored_content_names_no_project(self):
        orig = prep_view.CONTENT
        prep_view.CONTENT = Path(tempfile.mkdtemp())
        try:
            rec = prep_view.store(self.ctx, {}, "page.html")
            text = prep_view.content_path(rec["id"]).read_text()
        finally:
            prep_view.CONTENT = orig
        self.assertEqual(json.loads(text)["project"], "_portfolio")
        self.assertNotIn("Orchard", text)
        self.assertNotIn('"DEF"', text)


if __name__ == "__main__":
    unittest.main()
