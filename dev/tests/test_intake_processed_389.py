"""#389 (Alan, 27-10-2026): a meeting that has been processed still showed in Intake's Arrived list.

A calendar meeting left Arrived only when it was processed under its own key (calendar:<event id>). A meeting processed from a file
(a transcript or minutes dropped or uploaded, no event ID in it) is recorded as fp:<day>|<title>|<hash>, so its calendar row stayed
Arrived beside a second row for the same meeting. The link is the meeting's day and title (minutes.norm_title), as
minutes.processed_meeting already matches them; when two calendar meetings share the day and title nothing is linked (no guess).

Run: python3 dev/tests/test_intake_processed_389.py
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import build_dashboard  # noqa: E402
import minutes  # noqa: E402
import paths  # noqa: E402
from test_intake_review_model import TODAY, cal, q  # noqa: E402

FP = "fp:2026-10-05|weekly sync|9f2c1a"
META = {"proposed-sync.json": {"mkey": FP, "title": "Weekly sync", "day": "2026-10-05", "transcript": "inbox/sync.docx",
                               "run": "cx-minutes"}}
FILE = {"name": "sync.docx", "path": "inbox/sync.docx", "state": "draft", "event": None, "p": "ABC", "date": "2026-10-06",
        "ext": "docx", "ft": "transcript"}


def model(rows, files=(), queue=(), meta=None, done=None):
    return build_dashboard.intake_review_model({"rows": rows}, list(files), list(queue), meta or {}, TODAY, 14, done=done)


def rows_of(m, title):
    return [r for r in m["meetings"] if r["title"] == title or r.get("path") == "inbox/sync.docx"]


class ProcessedFromAFile(unittest.TestCase):
    def test_a_meeting_drafted_from_a_file_is_not_in_arrived(self):
        m = model([cal(2, "2026-10-05", "15:00", "Weekly sync", transcript="available")], files=[FILE],
                  queue=[q(1, "proposed-sync.json", "minutes", kind="draft"), q(2, "proposed-sync.json")], meta=META)
        mine = rows_of(m, "Weekly sync")
        self.assertEqual([r["stage"] for r in mine if r["stage"] == "arrived"], [], mine)
        self.assertEqual(len(mine), 1, "one row for the one meeting")
        self.assertEqual((mine[0]["src"], mine[0]["stage"]), ("calendar", "drafted"))
        self.assertEqual(mine[0]["files"], ["proposed-sync.json"])
        self.assertEqual(m["counts"]["arrived"], 0)
        self.assertEqual(m["counts"]["drafted"], 1)

    def test_a_meeting_filed_this_week_from_a_file_is_one_done_row(self):
        done = [{"key": FP, "day": "2026-10-05", "title": "Weekly sync", "path": "projects/ABC Alpha/minutes/x.docx", "p": "ABC"}]
        m = model([cal(2, "2026-10-05", "15:00", "Weekly sync", transcript="available")], done=done)
        mine = rows_of(m, "Weekly sync")
        self.assertEqual(len(mine), 1, mine)
        self.assertEqual((mine[0]["src"], mine[0]["stage"], mine[0]["state"]), ("calendar", "approved", "done"))
        self.assertEqual(m["counts"]["arrived"], 0)

    def test_the_title_is_matched_as_minutes_matches_it(self):
        meta = {"proposed-sync.json": dict(META["proposed-sync.json"], mkey="fp:2026-10-05|abc weekly sync|9f2c1a")}
        m = model([cal(2, "2026-10-05", "15:00", "[ABC] Weekly  Sync!", transcript="available")], files=[FILE],
                  queue=[q(1, "proposed-sync.json")], meta=meta)
        self.assertEqual(m["counts"]["arrived"], 1, "a different title is a different meeting")
        m = model([cal(2, "2026-10-05", "15:00", "[ABC] Weekly  Sync!", transcript="available")], files=[FILE],
                  queue=[q(1, "proposed-sync.json")], meta=META)
        self.assertEqual(m["counts"]["arrived"], 0, "[CODE] tags, case and punctuation are not part of the title")

    def test_two_meetings_with_the_day_and_title_are_never_guessed(self):
        rows = [cal(2, "2026-10-05", "09:00", "Weekly sync", transcript="available"),
                cal(3, "2026-10-05", "15:00", "Weekly sync", transcript="available")]
        m = model(rows, files=[FILE], queue=[q(1, "proposed-sync.json")], meta=META)
        self.assertEqual(m["counts"]["arrived"], 2)
        self.assertEqual([r["src"] for r in m["meetings"] if r["files"]], ["upload"], "the proposals stay with the file")

    def test_a_meeting_on_another_day_is_not_linked(self):
        m = model([cal(2, "2026-10-06", "15:00", "Weekly sync", transcript="available")], files=[FILE],
                  queue=[q(1, "proposed-sync.json")], meta=META)
        self.assertEqual(m["counts"]["arrived"], 1)

    def test_a_calendar_meeting_processed_under_its_own_key_is_unchanged(self):
        m = model([cal(2, "2026-10-05", "15:00", "Weekly sync", processed="2026-10-06")])
        self.assertEqual([(r["stage"], r["state"]) for r in m["meetings"]], [("approved", "done")])


class ProcessedInAnEarlierWeek(unittest.TestCase):
    """The #307 Done rows are this week's only; a meeting processed from a file before that must still leave Arrived."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.processed = Path(self.tmp.name) / "processed.txt"
        self.processed.write_text("# processed\n2026-09-29 | fp:2026-09-28|weekly sync|9f2c1a | projects/ABC Alpha/minutes/x.docx\n",
                                  encoding="utf-8")
        p = mock.patch.object(paths, "PROCESSED", self.processed)
        p.start()
        self.addCleanup(p.stop)

    def test_minutes_says_when_a_meeting_of_that_day_and_title_was_processed(self):
        self.assertEqual(minutes.processed_on_meeting("2026-09-28", "[ABC] Weekly sync"), "2026-09-29")
        self.assertIsNone(minutes.processed_on_meeting("2026-09-28", "Supplier call"))
        self.assertIsNone(minutes.processed_on_meeting("2026-09-29", "Weekly sync"))

    def test_the_calendar_row_is_processed(self):
        ev = {"id": "ev-7", "title": "Weekly sync", "start": "15:00", "end": "16:00"}
        with mock.patch.object(build_dashboard, "_inbox_match", return_value=("ABC", "matched", {})):
            row = build_dashboard._inbox_row("2026-09-28", ev, [], {}, set(), {}, {})
        self.assertEqual(row["processed"], "2026-09-29")

    def test_two_calendar_meetings_of_that_day_and_title_are_not_marked(self):
        evs = [{"id": "ev-7", "title": "Weekly sync", "start": "09:00"}, {"id": "ev-8", "title": "Weekly sync", "start": "15:00"}]
        with mock.patch.object(build_dashboard, "_inbox_match", return_value=("ABC", "matched", {})):
            rows = [build_dashboard._inbox_row("2026-09-28", ev, [], {}, set(), {}, {}, same_title=2) for ev in evs]
        self.assertEqual([r["processed"] for r in rows], [None, None])


if __name__ == "__main__":
    unittest.main()
