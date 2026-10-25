"""#362: a project code in a meeting title always beats the remembered series (a client-leak guard).

Run: python3 dev/tests/test_title_code_wins.py   (no browser, no model)
The rule (build_dashboard.prep_match): one code in the title wins over the series Alan chose before, in any case ("[def]");
two different codes win nothing (Not sure, whatever was remembered); "_portfolio" (his no-project choice) still stands. A
confidential meeting's row never carries a project, a name, a code or a reason.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
import build_dashboard as bd  # noqa: E402
from test_dashboard import today  # noqa: E402

PROJECTS = [{"code": "ABC", "name": "Harbour Upgrade"}, {"code": "DEF", "name": "Orchard Rollout"},
            {"code": "ORX", "name": "Quay Works"}, {"code": "ORX2C", "name": "Quay Works Two"}]
MEM = {"weekly sync": "ABC"}


class TitleCodeWins(unittest.TestCase):
    def test_other_code_beats_memory(self):
        self.assertEqual(bd.prep_match("[DEF] Weekly sync", PROJECTS, MEM), ("DEF", "matched"))

    def test_lower_case_tag(self):
        self.assertEqual(bd.prep_match("[def] Weekly sync", PROJECTS, MEM), ("DEF", "matched"))
        self.assertEqual(bd.prep_match("[ def ] Weekly sync", PROJECTS, MEM), ("DEF", "matched"))

    def test_leading_code_wins(self):
        self.assertEqual(bd.prep_match("DEF Weekly sync", PROJECTS, {"def weekly sync": "ABC"}), ("DEF", "matched"))
        self.assertEqual(bd.prep_match("DEF: Weekly sync", PROJECTS, {"def weekly sync": "ABC"}), ("DEF", "matched"))

    def test_mid_title_code_does_not_beat_memory(self):         # #362 review LOW 5: only a [TAG] or a leading code has authority
        for t in ("Budget review (follow-up from DEF)", "Re: DEF weekly sync", "Weekly sync with DEF"):
            self.assertEqual(bd.title_codes(t, PROJECTS), set(), t)
            self.assertEqual(bd.prep_match(t, PROJECTS, {bd.series_of(t): "ABC"}), ("ABC", "remembered"), t)

    def test_a_longer_word_is_no_leading_code(self):
        one = PROJECTS + [{"code": "ONE", "name": "One Thing"}]
        self.assertEqual(bd.title_codes("Re: ONE-to-one", one), set())
        self.assertEqual(bd.title_codes("ONE-to-one", one), set())
        self.assertEqual(bd.title_codes("ONE to one", one), {"ONE"})

    def test_long_and_odd_titles_are_bounded(self):
        t = "[" * 5000 + "DEF" + "]" * 5000
        self.assertEqual(bd.title_codes(t, PROJECTS), set())
        self.assertTrue(len(bd.series_of("[a" * 50000)) <= 300)
        self.assertEqual(bd.title_codes("[ﬀ] x", PROJECTS + [{"code": "FF", "name": "Ff"}]), set())             # non-ASCII is never upper-cased into a code

    def test_same_code_as_memory_is_still_remembered(self):
        self.assertEqual(bd.prep_match("[ABC] Weekly sync", PROJECTS, MEM), ("ABC", "remembered"))
        self.assertEqual(bd.prep_match("Weekly sync", PROJECTS, MEM), ("ABC", "remembered"))

    def test_two_codes_win_nothing(self):
        for t in ("[ABC] [DEF] Weekly sync", "[abc][def] Weekly sync", "ABC [DEF] Weekly sync"):
            self.assertEqual(bd.prep_match(t, PROJECTS, MEM), (None, "unsure"), t)
            self.assertEqual(bd.prep_match(t, PROJECTS, {}), (None, "unsure"), t)

    def test_codes_match_whole(self):
        self.assertEqual(bd.prep_match("[ORX2C] Weekly sync", PROJECTS, {"weekly sync": "ORX"}), ("ORX2C", "matched"))
        self.assertEqual(bd.prep_match("[ORX] Weekly sync", PROJECTS, {"weekly sync": "ORX2C"}), ("ORX", "matched"))

    def test_unknown_tag_is_no_code(self):
        self.assertEqual(bd.prep_match("[ZZZ] Weekly sync", PROJECTS, MEM), ("ABC", "remembered"))

    def test_portfolio_choice_stands(self):
        self.assertEqual(bd.prep_match("[ABC] Weekly sync", PROJECTS, {"weekly sync": "_portfolio"}), ("_portfolio", "remembered"))

    def test_series_ignores_tags_in_any_case(self):
        self.assertEqual(bd.series_of("[def] Weekly sync 3"), bd.series_of("[ABC] Weekly sync"))

    def test_minutes_and_capture_share_the_rule(self):
        import minutes
        self.assertIn("prep_match", open(minutes.__file__).read())


class ConfidentialRow(unittest.TestCase):
    """A confidential meeting's row never carries a project, name, code, domain or reason."""

    def row(self, **kw):
        m = {"id": "e1", "title": "Catch-up", "day": "2026-10-20", "start": "10:00", "end": "11:00", "confidential": True,
             "p": "DEF", "how": "matched", "level": "likely", "reason": "Orchard Rollout fits orchard.example",
             "cands": ["DEF"], "offer": {"kind": "domain", "value": "orchard.example"}, "series": "catch up", **kw}
        return bd._ir_calendar(m, {}, today(), 7)

    def test_no_project_or_reason_leaks(self):
        r = self.row()
        self.assertIsNone(r["p"])
        text = json.dumps(r)
        for leak in ("DEF", "Orchard", "orchard.example", "likely", "fits"):
            self.assertNotIn(leak, text)

    def test_not_confidential_keeps_its_project(self):
        self.assertEqual(self.row(confidential=False)["p"], "DEF")


if __name__ == "__main__":
    unittest.main()
