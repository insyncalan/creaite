"""#362 (Team Cap, test only): a remembered meeting series must not beat the project code in the meeting's title.

Defect in build_dashboard.prep_match (and series_of, which strips [CODE] tags to form the series key): remember "[ABC] Weekly sync"
as project ABC, then "[DEF] Weekly sync" returns ("ABC", "remembered"), and minutes would be processed under ABC. prep_match is the
one matcher behind Intake (meetings_rows), Today, the Prep entry, the week line, capture.py and minutes.py (intake_process).

The cases that show the defect are marked expected failures: the fix is Stark's. When it lands they turn into "unexpected success";
remove the marker then. The cases that already hold are plain tests and must stay green. Engine only: no browser, no vault.

Run: python3 dev/tests/test_series_vs_code_362.py
"""
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import build_dashboard as bd  # noqa: E402

WHY = "Team Cap #362: a remembered series beats a project code in the title; fix is Stark's"
FIXME = unittest.expectedFailure       # reason: WHY

PROJECTS = [{"code": "ABC", "name": "Alpha Programme"}, {"code": "DEF", "name": "Delta Programme"}]
SERIES = bd.series_of("Weekly sync")           # the key every title below forms: "weekly sync"
REMEMBERED_ABC = {SERIES: "ABC"}               # Alan set ABC once on the "Weekly sync" series


def match(title, remembered=None):
    # The register supplies aliases and keywords; none here, so only a [CODE] tag or a project name can match.
    with mock.patch.object(bd, "register_signals", return_value=[]):
        return bd.prep_match(title, PROJECTS, REMEMBERED_ABC if remembered is None else remembered)


class SeriesVersusTitleCode(unittest.TestCase):
    def test_the_series_key_ignores_the_code_tag(self):
        """The premise: both titles form one series, so the memory applies to both."""
        self.assertEqual(bd.series_of("[ABC] Weekly sync"), SERIES)
        self.assertEqual(bd.series_of("[DEF] Weekly sync"), SERIES)

    # ---- the defect
    @FIXME
    def test_a_different_project_code_in_the_title_is_not_overruled_by_the_memory(self):
        """Remembered "[ABC] Weekly sync" as ABC; "[DEF] Weekly sync" must not come back as ABC, remembered. Today it returns
        ("ABC", "remembered") (a bare (code, how) pair: the function has no shape for "not sure, with both candidates" yet). The
        fix must give "Not sure" with ABC and DEF both offered; this asserts only what the pair can show: not chosen as ABC, and
        DEF not lost (it is either the choice or the result is unsure)."""
        code, how = match("[DEF] Weekly sync")
        self.assertNotEqual((code, how), ("ABC", "remembered"), WHY)
        self.assertTrue(code == "DEF" or (code is None and how == "unsure"), f"DEF was lost: {(code, how)}")

    @FIXME
    def test_the_code_in_a_different_case_counts_too(self):
        code, how = match("[def] Weekly sync")
        self.assertNotEqual((code, how), ("ABC", "remembered"), WHY)

    @FIXME
    def test_two_codes_in_one_title_are_not_settled_silently_by_the_memory(self):
        code, how = match("[ABC][DEF] Weekly sync")
        self.assertNotEqual((code, how), ("ABC", "remembered"), WHY)
        self.assertNotEqual(how, "remembered", "two codes disagree with each other: the memory cannot decide between them")

    # ---- behaviour that must stay
    def test_a_bracket_that_is_not_a_project_code_falls_back_to_the_remembered_series(self):
        self.assertEqual(match("[TBD] Weekly sync"), ("ABC", "remembered"))

    def test_a_series_remembered_with_no_code_in_the_title_is_still_remembered(self):
        self.assertEqual(match("Weekly sync"), ("ABC", "remembered"))
        self.assertEqual(match("Weekly sync 12"), ("ABC", "remembered"), "numbers are not part of the series")

    def test_the_same_code_as_the_memory_is_abc(self):
        self.assertEqual(match("[ABC] Weekly sync"), ("ABC", "remembered"))

    def test_a_code_in_the_title_with_nothing_remembered_is_matched(self):
        self.assertEqual(match("[DEF] Weekly sync", remembered={}), ("DEF", "matched"))

    def test_no_code_and_nothing_remembered_is_unsure(self):
        self.assertEqual(match("Weekly sync", remembered={}), (None, "unsure"))

    # ---- confidential (#232-A): the Intake row names no project whatever the matcher said
    def test_a_confidential_meeting_row_still_shows_no_project(self):
        for title in ("Weekly sync", "[DEF] Weekly sync"):
            code, how = match(title)
            m = {"id": "ev-1", "key": "ev-1", "day": "2026-10-05", "start": "09:00", "end": "09:30", "title": title, "p": code,
                 "how": how, "private": False, "confidential": True, "teams": True, "processed": None, "draft": False,
                 "transcript": None, "loaded": None}
            row = bd._ir_calendar(m, {}, date(2026, 10, 5), 3)
            self.assertIsNone(row["p"], f"{title}: a confidential meeting names no project")
            self.assertIs(row["confidential"], True)


if __name__ == "__main__":
    unittest.main()
