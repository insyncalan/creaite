"""Regression tests for the MEDIUM findings that shipped unfixed in creaite v2.6.7 (#328 M1 and M2; fictional data).

Run: python3 dev/tests/test_267_medium_regressions.py   (no browser, no model; Node runs the page's own Process-all-ready rule)
The four tests that were marked expectedFailure on 2.6.7 are plain tests now: the fixes landed (v268-328d). The #339 M1 pin lives in test_lighter_runs_339.py.
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dashboard as bd  # noqa: E402
import prep_page  # noqa: E402
from test_328_cap_probes import Base, P, row_for, needs_project  # noqa: E402
from test_dashboard import today  # noqa: E402


class RememberedSeriesVersusAttendee(Base):
    """#328 M1: prep_match_ev returns early on "remembered", so a remembered series beats an attendee who points at another project
    on the Prep, hub and Today paths. The Intake path already gives (None, "unsure")."""
    MEM = {"weekly sync": "ABC"}
    EV = {"title": "Weekly sync", "start": "10:00", "end": "11:00", "attendees": [{"email": "a@orchard.example"}]}

    def entry(self, mem):
        ctx = {"projects": P, "remembered": mem, "history": [], "items": None, "ms_names": {}, "vips": {}, "today": today()}
        return bd.prep_entry(self.EV, today(), ctx)[1]

    def test_M1_intake_already_leaves_it_unsure(self):
        self.assertEqual(bd._inbox_match("Weekly sync", self.EV, False, False, P, self.MEM)[:2], (None, "unsure"))

    def test_M1_prep_entry_does_not_file_it_under_the_remembered_series(self):
        m = self.entry(self.MEM)
        self.assertEqual((m["p"], m["how"]), (None, "unsure"))

    def test_M1_prep_page_does_not_treat_it_as_a_chosen_project(self):
        self.assertNotEqual(prep_page._project_of({"projects": P}, self.entry(self.MEM)), ("ABC", True))

    def test_M1_the_hub_does_not_show_the_remembered_project(self):
        self.assertNotEqual(bd.ev_project(self.EV, "Weekly sync", P, self.MEM), "ABC")

    def test_M1_control_a_remembered_portfolio_choice_still_stands(self):
        m = self.entry({"weekly sync": "_portfolio"})
        self.assertEqual((m["p"], m["how"]), ("_portfolio", "remembered"))
        self.assertEqual(bd.ev_project(self.EV, "Weekly sync", P, {"weekly sync": "_portfolio"}), "_portfolio")


class GuessedPortfolioInProcessAll(Base):
    """#328 M2: irNeedsProject lets any p === "_portfolio" row through, so Process all ready runs a guessed portfolio row (the
    word "portfolio" in the title, how "portfolio", no level). Only a remembered _portfolio choice may run."""

    def test_M2_control_a_remembered_portfolio_row_runs(self):
        self.assertEqual(row_for("Weekly sync", [], {"weekly sync": "_portfolio"}), ("_portfolio", "remembered", False))

    def test_M2_a_guessed_portfolio_row_is_skipped_and_listed(self):
        code, how, skipped = row_for("Harbour portfolio review", [{"email": "x@orchard.example"}], {})
        self.assertEqual((code, how), ("_portfolio", "portfolio"))            # the model row, as the Calendar import builds it
        self.assertTrue(skipped)
        self.assertTrue(needs_project({"src": "calendar", "private": False, "confidential": False, "p": "_portfolio",
                                       "how": "portfolio"}))


if __name__ == "__main__":
    unittest.main()
