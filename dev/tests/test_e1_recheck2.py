"""E1 D, Cap re-check 2 (issue #375): a bare label in its own piece (HIGH 1), HTML with a break inside a label (HIGH 2), the Meet-link
rule on ordinary slugs (MEDIUM), dotted letters (LOW). Every value is made up.

Run: python3 dev/tests/test_e1_recheck2.py      (quick tier, plain code)
"""
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "system" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import invite_filter as F  # noqa: E402
import invite_clean as C  # noqa: E402

D = F.filter_text_with_scrub
BREAKS = ["\x0b", "\x0c", "\x85", "\u2028", "\u2029"]


class BareLabelPiece(unittest.TestCase):
    def test_sibling_value_goes(self):
        for a in BREAKS:
            for b in BREAKS:
                t = "Agenda\nPasscode:%sReview%swagakelov\nRisks" % (a, b)
                self.assertNotIn("wagakelov", D(t), repr(t))
                self.assertEqual(D(t), "Agenda\nRisks", repr(t))

    def test_label_without_colon(self):
        t = "Agenda\nMeeting ID\x85Review\x85771\nRisks"
        self.assertEqual(D(t), "Agenda\nRisks")

    def test_piece_with_own_value_keeps_the_rest(self):
        self.assertEqual(D("Agenda\nPasscode: 8825\x85Review the budget\nRisks"), "Agenda\nReview the budget\nRisks")

    def test_stated_gap(self):
        # documented: a word-only value after a break keeps the word
        self.assertEqual(D("Passcode: 8825\x85zejumud"), "zejumud")


class HtmlBreaks(unittest.TestCase):
    def test_html_breaks(self):
        for nl in BREAKS:
            for t in ("<p>Zoom passcode:</p><p>Decisions %slog</p><p>mupiwoc</p>" % nl,
                      "<p>Host %skey (organiser only):</p><p>770</p>" % nl,
                      "<ul><li>Mot de %spasse:  gusos58#</li></ul>" % nl):
                out = D(t)
                for v in ("mupiwoc", "770", "gusos58", "log"):
                    self.assertNotIn(v, out, repr(t))
                self.assertEqual(out, C.invite_text(t), repr(t))      # as bare22 (the scrub on the body as written)

    def test_br_forms(self):
        for t in ("<p>Zoom passcode:<br>Decisions<br>mupiwoc</p>", "<p>Zoom passcode:</p><br><p>mupiwoc</p>"):
            self.assertEqual(D(t).count("mupiwoc"), C.invite_text(t).count("mupiwoc"), t)      # never worse than the scrub

    def test_html_agenda_kept(self):
        out = D("<ol><li>Budget</li><li>Risks</li></ol>")
        self.assertIn("Budget", out)
        self.assertIn("Risks", out)

    def test_idempotent(self):
        for t in ("<p>Zoom passcode:</p><p>Decisions \x85log</p><p>mupiwoc</p>", "<p>Agenda</p><p>Budget\x85review</p><p>Risks<br>log</p>"):
            o = D(t)
            self.assertEqual(D(o), o)


class MeetSlug(unittest.TestCase):
    AG = "Agenda\n1. Budget\n2. Risks\n"

    def test_ordinary_slugs_keep_the_agenda(self):
        for u in ("wiki.example.org/bid-plan-two", "wiki.example.org/sop-hand-off", "wiki.example.org/new-team-day"):
            self.assertEqual(D(self.AG + "https://" + u), "Agenda\n1. Budget\n2. Risks", u)

    def test_meet_code_is_a_join_link(self):
        self.assertTrue(F._meet_link("https://meet.google.com/abc-defg-hij"))
        self.assertTrue(F._meet_link("meet.example.org/abc-defg-hij"))
        self.assertFalse(F._meet_link("https://wiki.example.org/bid-plan-two"))
        self.assertFalse(F._plain_link("https://meet.example.org/abc-defg-hij"))

    def test_join_paths(self):
        for u in ("https://wiki.example.org/meet/bid", "https://wiki.example.org/my/room"):
            self.assertFalse(F._plain_link(u), u)
        self.assertTrue(F._plain_link("https://wiki.example.org/plan"))


class Dotted(unittest.TestCase):
    def test_dotted_label(self):
        self.assertEqual(D("Agenda\nP.A.S.S.C.O.D.E: 4330\nRisks"), "Agenda\nRisks")

    def test_abbreviations_stay(self):
        self.assertEqual(D("Agenda\nU.S.A. and U.K. plans\nRisks"), "Agenda\nU.S.A. and U.K. plans\nRisks")


class Mutants(unittest.TestCase):
    def _mutant(self, old, new, probe, expect_leak):
        src = (SCRIPTS / "invite_filter.py").read_text(encoding="utf-8")
        self.assertIn(old, src)
        ns = {"__name__": "invite_filter_mutant", "__file__": str(SCRIPTS / "invite_filter.py")}
        exec(compile(src.replace(old, new, 1), "mutant", "exec"), ns)
        self.assertIn(expect_leak, ns["filter_text_with_scrub"](probe))

    def test_bare_label_exemption_is_needed(self):
        self._mutant(" and not _ends_with_label(_skeleton(piece)) and not _label_only(piece)", "",
                     "Agenda\nPasscode:\x0cReview\x85wagakelov\nRisks", "wagakelov")

    def test_html_raw_is_needed(self):
        self._mutant("raw = asked if html else _line_breaks(asked)", "raw = _line_breaks(asked)",
                     "<p>Zoom passcode:</p><p>Decisions \x85log</p><p>mupiwoc</p>", "mupiwoc")

    def test_meet_host_is_needed(self):
        src = (SCRIPTS / "invite_filter.py").read_text(encoding="utf-8")
        self.assertIn("if not _LINK_MEET.search(tok):", src)

    def test_dotted_is_needed(self):
        self._mutant('    if "." in s:\n        s = _DOTTED_LETTERS', '    if False:\n        s = _DOTTED_LETTERS',
                     "Agenda\nP.A.S.S.C.O.D.E: 4330\nRisks", "4330")


if __name__ == "__main__":
    unittest.main()
