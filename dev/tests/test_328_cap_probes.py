"""#328 against the 2.6.7 release: Cap's findings, probed as behaviour (fictional data).

Run: python3 dev/tests/test_328_cap_probes.py   (no browser, no model; Node runs the page's own Process-all-ready rule)
Each test names the probe: H-A (one series pick vs two clients), H1 (lower-case tag), PORTFOLIO (a remembered no-project choice in
Process all ready), LIKELY (a Likely guess is never a chosen project), TWO_CODES (two codes keep a remembered no-project choice).
Tests named test_accepted_* document behaviour that stays by design.
"""
import json
import subprocess
import sys
import types
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dashboard as bd  # noqa: E402
import capture  # noqa: E402
import prep_page  # noqa: E402
from test_dashboard import today  # noqa: E402

ROWS = [{"code": "ABC", "name": "Harbour Upgrade", "aliases": [], "people": [], "domains": ["harbourco.example"], "channels": [],
         "keywords": [], "senders": [], "exclude": []},
        {"code": "DEF", "name": "Orchard Rollout", "aliases": [], "people": [], "domains": ["orchard.example"], "channels": [],
         "keywords": [], "senders": [], "exclude": []}]
P = [{"code": "ABC", "name": "Harbour Upgrade"}, {"code": "DEF", "name": "Orchard Rollout"}]
ACT = (REPO / "system/templates/dashboard/src/components/intakeReview/actions.js").read_text()


def needs_project(row):
    """The page's own Process-all-ready rule (irNeedsProject), run in Node on a row."""
    line = [ln for ln in ACT.splitlines() if ln.startswith("export const irNeedsProject")][0].replace("export const", "const", 1)
    js = f"{line}\nconsole.log(JSON.stringify(irNeedsProject({json.dumps(row)})));"
    return json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)


def mutate_bd(old, new):
    """build_dashboard with `old` replaced by `new` (it must be there), as a separate module."""
    src = Path(bd.__file__).read_text()
    assert old in src, old
    m = types.ModuleType("bd_mutant")
    m.__file__ = bd.__file__
    exec(compile(src.replace(old, new, 1), bd.__file__, "exec"), m.__dict__)
    return m


def row_for(title, attendees, remembered):
    """The Calendar import row's matcher fields for a meeting, and whether Process all ready would skip it."""
    code, how, match = bd._inbox_match(title, {"title": title, "attendees": attendees}, False, False, P, remembered)
    r = {"src": "calendar", "private": False, "confidential": False, "p": code, "how": how, **{k: match[k] for k in ("level",) if match}}
    return code, how, needs_project(r)


class Base(unittest.TestCase):
    def setUp(self):
        self.orig = capture.register
        capture.register = lambda: {"projects": ROWS, "shared": set()}

    def tearDown(self):
        capture.register = self.orig


class SeriesAcrossClients(Base):
    MEM = {"weekly sync": "ABC"}

    def test_H_A_the_other_clients_meeting_is_not_filed_under_the_remembered_project(self):
        mine = row_for("Weekly sync", [{"email": "a@harbourco.example"}], self.MEM)
        other = row_for("Weekly sync", [{"email": "a@orchard.example"}], self.MEM)
        self.assertEqual(mine, ("ABC", "remembered", False))                  # the picked client's own meeting runs
        self.assertEqual(other, (None, "unsure", True))                       # the other known client's is skipped and listed

    def test_accepted_a_generic_title_with_no_known_attendee_follows_the_series_pick(self):
        """By design: with no attendee on any project's list there is nothing to contradict the pick. The button says the pick is
        kept for every meeting with this title."""
        self.assertEqual(row_for("Weekly sync", [], self.MEM), ("ABC", "remembered", False))
        self.assertEqual(row_for("Weekly sync", [{"email": "a@unlisted.example"}], self.MEM), ("ABC", "remembered", False))
        self.assertIn("Your pick is kept for every meeting with this title.",
                      (REPO / "system/templates/dashboard/src/components/intakeReview/rows.jsx").read_text())


class LowerCaseTag(Base):
    def test_H1_a_lower_case_tag_does_not_file_under_the_remembered_project(self):
        mem = {"weekly sync": "ABC"}
        self.assertEqual(bd.prep_match_ev("[def] Weekly sync", {"title": "x"}, P, mem), ("DEF", "matched"))
        code, how, skipped = row_for("[def] Weekly sync", [], mem)
        self.assertNotEqual(code, "ABC")
        self.assertTrue(skipped)                                              # unsure, so Process all ready skips it
        self.assertEqual(bd.prep_match_ev("[ def ] Weekly sync", {"title": "x"}, P, mem)[0], "DEF")

    def test_H1_mutant(self):
        import meeting_match as mm
        src = Path(mm.__file__).read_text()
        old = 'if p["code"] not in strong and re.search('
        self.assertIn(old, src)
        m = types.ModuleType("mm_mutant")
        m.__file__ = mm.__file__
        exec(compile(src.replace(old, "if False and re.search(", 1), mm.__file__, "exec"), m.__dict__)
        self.assertEqual(m.match_meeting("[def] Weekly sync", [], ROWS, "ABC")["p"], "ABC")   # the leak without the fix
        self.assertNotEqual(mm.match_meeting("[def] Weekly sync", [], ROWS, "ABC")["p"], "ABC")


class PortfolioRows(Base):
    def test_PORTFOLIO_a_remembered_no_project_row_is_processed_as_portfolio(self):
        code, how, skipped = row_for("Weekly sync", [{"email": "a@orchard.example"}], {"weekly sync": "_portfolio"})
        self.assertEqual((code, how, skipped), ("_portfolio", "remembered", False))

    def test_PORTFOLIO_the_filter_fails_closed_on_everything_else(self):
        base = {"src": "calendar", "private": False, "confidential": False, "p": "ABC"}
        self.assertTrue(needs_project(base))                                  # no level at all
        self.assertTrue(needs_project({**base, "level": "likely"}))
        self.assertTrue(needs_project({**base, "level": "unsure"}))
        self.assertTrue(needs_project({**base, "level": "weird"}))
        self.assertFalse(needs_project({**base, "level": "matched"}))
        self.assertFalse(needs_project({**base, "p": "_portfolio"}))
        self.assertFalse(needs_project({**base, "src": "upload"}))            # a file has no project guess

    def test_PORTFOLIO_mutant(self):
        m = mutate_bd('match = {} if private or code == "_portfolio" else', 'match = {} if private or how == "portfolio" else')
        self.assertEqual(m._inbox_match("Weekly sync", {"attendees": []}, False, False, P, {"weekly sync": "_portfolio"})[:2],
                         (None, "unsure"))                                    # the gap without the fix


class LikelyIsNotChosen(Base):
    EV = {"title": "Catch-up", "start": "10:00", "end": "11:00", "attendees": [{"name": "Sam Lee", "email": "a@orchard.example"}]}

    def ctx(self):
        return {"projects": P, "remembered": {}, "history": [], "items": None, "ms_names": {}, "vips": {}, "today": today()}

    def test_LIKELY_prep_entry_and_prep_page_do_not_count_it_as_chosen(self):
        _, rec = bd.prep_entry(self.EV, today(), self.ctx())
        self.assertEqual((rec["p"], rec["how"]), (None, "likely"))
        self.assertEqual(prep_page._project_of({"projects": P}, {"p": "DEF", "how": "likely", "invite": {}}), ("_portfolio", False))
        self.assertEqual(prep_page._project_of({"projects": P}, {"p": "DEF", "how": "matched", "invite": {}}), ("DEF", True))

    def test_LIKELY_the_hub_records_do_not_count_it(self):
        self.assertIsNone(bd.ev_project(self.EV, "Catch-up", P, {}))
        self.assertEqual(bd.ev_project({**self.EV, "title": "[DEF] x"}, "[DEF] x", P, {}), "DEF")
        day = today().isoformat()
        hub = bd.meeting_hub({}, P, today(), {"days": {day: [self.EV]}}, [], [], [], {})
        rec = next(r for r in hub.values() if r.get("title") == "Catch-up")
        self.assertEqual(rec["p"], [])

    def test_LIKELY_capture_uses_the_title_only(self):
        orig = bd.saved_calendar_days
        bd.saved_calendar_days = lambda: {today().isoformat(): [self.EV]}
        try:
            self.assertIsNone(capture.meeting(today().isoformat(), "10:00", "Catch-up", P)["code"])
        finally:
            bd.saved_calendar_days = orig

    def test_accepted_the_day_line_still_names_the_likely_project(self):
        """The Today/day line shows the likely project by name (a display, not a choice): meeting_project is unchanged."""
        src = Path(bd.__file__).read_text()
        self.assertIn('def meeting_project(e, title, look):', src)


class TwoCodes(Base):
    def test_TWO_CODES_a_remembered_no_project_choice_stands(self):
        mem = {"weekly sync": "_portfolio"}
        self.assertEqual(bd.prep_match("[ABC][DEF] Weekly sync", P, mem), ("_portfolio", "remembered"))
        self.assertEqual(bd._inbox_match("[ABC][DEF] Weekly sync", {}, False, False, P, mem)[:2], ("_portfolio", "remembered"))

    def test_TWO_CODES_otherwise_nothing_wins(self):
        for mem in ({}, {"weekly sync": "ABC"}, {"weekly sync": "DEF"}):
            self.assertEqual(bd.prep_match("[ABC][DEF] Weekly sync", P, mem), (None, "unsure"), mem)

    def test_TWO_CODES_mutant(self):
        m = mutate_bd('return ("_portfolio", "remembered") if mem == "_portfolio" else (None, "unsure")', 'return None, "unsure"')
        self.assertEqual(m.prep_match("[ABC][DEF] x", P, {"x": "_portfolio"}), (None, "unsure"))

    def test_LIKELY_mutants(self):
        m = mutate_bd('return None if how == "likely" else code', 'return code')
        self.assertEqual(m.ev_project(LikelyIsNotChosen.EV, "Catch-up", P, {}), "DEF")           # the hub gap without the fix
        m = mutate_bd('elif how == "likely":', 'elif False:')
        _, rec = m.prep_entry(LikelyIsNotChosen.EV, today(), LikelyIsNotChosen().ctx())
        self.assertEqual(rec["p"], "DEF")


if __name__ == "__main__":
    unittest.main()
