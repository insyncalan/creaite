"""#347 (v2.6.5): chat words in plain language: check my mail, save, undo last save.

Run: python3 dev/tests/test_v265_plain_words.py      (quick tier)
Help shows the plain words first and keeps the old ones as "also works". The skill and rules checks marked GUARDED need the diffs in
dev/proposals/347/ applied (skills.diff, creaite-rules.md.diff, live_server.py.diff); they skip until then.
"""
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def read(rel):
    return (REPO / rel).read_text(encoding="utf-8")


def frontmatter_description(rel):
    m = re.search(r"^description:(.*)$", read(rel), re.M)
    return m.group(1) if m else ""


class Help(unittest.TestCase):
    def test_help_shows_plain_words_and_keeps_the_old_ones(self):
        h = read("system/templates/help.md")
        for w in ("`check my mail`", "`save`", "`undo last save`"):
            self.assertIn(w, h)
        for w in ("`sweep` also works", "`apply` also works", "`undo last apply` also works"):
            self.assertIn(w, h)

    def test_the_table_leads_with_the_plain_words(self):
        h = read("system/templates/help.md")
        self.assertLess(h.index("| `check my mail` |"), h.index("`sweep` also works"))
        self.assertIn("| `review` · `save` |", h)


class Guarded(unittest.TestCase):
    """GUARDED: pass only once dev/proposals/347 is applied."""

    def test_cx_sweep_accepts_the_new_words_and_the_old(self):
        d = frontmatter_description(".claude/skills/cx-sweep/SKILL.md")
        if '"check my mail"' not in d:
            self.skipTest("GUARDED: needs dev/proposals/347/skills.diff")
        for w in ('"check my mail for <CODE>"', '"sweep"', '"sweep mail for ABC"', '"refresh calendar"'):
            self.assertIn(w, d)

    def test_cx_review_accepts_save_and_undo_last_save_and_the_old(self):
        d = frontmatter_description(".claude/skills/cx-review/SKILL.md")
        if '"undo last save"' not in d:
            self.skipTest("GUARDED: needs dev/proposals/347/skills.diff")
        for w in ('"save"', '"apply"', '"undo last apply"'):
            self.assertIn(w, d)
        body = read(".claude/skills/cx-review/SKILL.md")
        self.assertIn("Saving n approved items", body)
        self.assertIn("only as the whole message", body)

    def test_rules_table_lists_the_new_words(self):
        r = read("system/creaite-rules.md")
        if '"check my mail"' not in r:
            self.skipTest("GUARDED: needs dev/proposals/347/creaite-rules.md.diff")
        self.assertIn('"undo last save"', r)
        self.assertIn('"undo last apply"', r)


class Regression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(REPO / "system" / "scripts"))
        import live_server
        cls.ls = live_server

    def test_the_not_list_still_refuses_apply_and_undo(self):
        for w in ("apply", "undo"):
            self.assertTrue(self.ls.PANEL_SWEEP_NOT.search(f"the {w} thread"))
        self.assertFalse(self.ls.panel_sweep("sweep the budget and apply thread"))
        self.assertFalse(self.ls.panel_sweep("sweep the x thread then undo"))

    def test_chat_apply_is_not_recognised_by_the_server(self):
        """The server never matches "apply"/"save" as a command: the model reads cx-review. Only panel_sweep and the
        confirmed flow exist, and neither treats a bare apply or save as a sweep."""
        for m in ("apply", "save", "undo last apply", "undo last save"):
            self.assertFalse(self.ls.panel_sweep(m), m)


if __name__ == "__main__":
    unittest.main()
