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


class ReviewFindings(unittest.TestCase):
    """Stark's review of 1174b7b1 (27-10-2026): two MEDIUMs and the surviving mutants, with Jarvis's ruling on #232 E1."""

    def test_a_set_aside_twin_is_never_guessed(self):
        """MEDIUM 1: the day's count includes a meeting set aside (Not needed, Later): the row says how many share its title."""
        m = model([cal(2, "2026-10-05", "15:00", "Weekly sync", transcript="available", same_title=2)], files=[FILE],
                  queue=[q(1, "proposed-sync.json")], meta=META)
        self.assertEqual(m["counts"]["arrived"], 1)
        self.assertEqual([r["src"] for r in m["meetings"] if r["files"]], ["upload"])

    def test_someone_elses_minutes_never_link(self):
        """MEDIUM 2, Jarvis's ruling: #232 E1 holds; someone else's minutes never mark the meeting processed, drafted or done."""
        meta = {"proposed-sync.json": dict(META["proposed-sync.json"], transcript=None, kind="minutes by others")}
        m = model([cal(2, "2026-10-05", "15:00", "Weekly sync", transcript="available")], queue=[q(1, "proposed-sync.json")], meta=meta)
        self.assertEqual(m["counts"]["arrived"], 1)
        done = [{"key": FP, "day": "2026-10-05", "title": "Weekly sync", "path": "projects/ABC Alpha/minutes/x.docx", "p": "ABC"}]
        m = build_dashboard.intake_review_model({"rows": [cal(2, "2026-10-05", "15:00", "Weekly sync", transcript="available")]}, [], [],
                                                {}, TODAY, 14, done=done, others={FP})
        self.assertEqual(m["counts"]["arrived"], 1, "their filing stays its own Done row")
        self.assertEqual(m["counts"]["approved"], 1)

    def test_an_empty_title_never_links(self):
        meta = {"proposed-sync.json": dict(META["proposed-sync.json"], mkey="fp:2026-10-05||9f2c1a")}
        m = model([cal(2, "2026-10-05", "15:00", "[ABC]", transcript="available")], files=[FILE], queue=[q(1, "proposed-sync.json")],
                  meta=meta)
        self.assertEqual(m["counts"]["arrived"], 1)


class ProcessedLines(unittest.TestCase):
    """What processed.txt says: comment lines, rejected minutes and someone else's minutes are never a processing of the meeting."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.processed = Path(self.tmp.name) / "processed.txt"
        for p in (mock.patch.object(paths, "PROCESSED", self.processed),):
            p.start()
            self.addCleanup(p.stop)

    def lines(self, *rows):
        self.processed.write_text("".join(r + "\n" for r in rows), encoding="utf-8")

    def test_a_comment_line_is_not_a_record(self):
        self.lines("# 2026-09-29 | fp:2026-09-28|weekly sync|9f2c1a | projects/ABC Alpha/minutes/x.docx | 3")
        self.assertIsNone(minutes.processed_on_meeting("2026-09-28", "Weekly sync"))

    def test_rejected_minutes_are_not_a_processing(self):
        self.lines("2026-09-29 | fp:2026-09-28|weekly sync|9f2c1a | not filed | 0")
        self.assertIsNone(minutes.processed_on_meeting("2026-09-28", "Weekly sync"))
        self.lines("2026-09-29 | fp:2026-09-28|weekly sync|9f2c1a | not filed | 0",
                   "2026-09-30 | fp:2026-09-28|weekly sync|77aa01 | projects/ABC Alpha/minutes/x.docx | 2")
        self.assertEqual(minutes.processed_on_meeting("2026-09-28", "Weekly sync"), "2026-09-30")

    def test_an_empty_title_is_never_matched(self):
        """A title that normalises to nothing ('[ABC]') never takes a processing recorded as fp:<day>||…"""
        self.lines("2026-09-29 | fp:2026-09-28||9f2c1a | projects/ABC Alpha/minutes/x.docx | 3")
        self.assertIsNone(minutes.processed_on_meeting("2026-09-28", "[ABC]"))

    def test_someone_elses_minutes_are_skipped(self):
        self.lines("2026-09-29 | fp:2026-09-28|weekly sync|9f2c1a | projects/ABC Alpha/minutes/theirs.docx | 2")
        self.assertIsNone(minutes.processed_on_meeting("2026-09-28", "Weekly sync", skip={"fp:2026-09-28|weekly sync|9f2c1a"}))

    def test_the_meetings_own_processing_keeps_its_date(self):
        """M9: a meeting processed under its own key keeps that date; a file's processing never replaces it."""
        self.lines("2026-09-29 | calendar:ev-7 | projects/ABC Alpha/minutes/x.docx | 3",
                   "2026-09-30 | fp:2026-09-28|weekly sync|9f2c1a | projects/ABC Alpha/minutes/y.docx | 1")
        self.assertEqual(build_dashboard._inbox_done("2026-09-28", "Weekly sync", "ev-7", 1, set()), "2026-09-29")

    def test_a_meeting_without_an_event_id_is_never_marked(self):
        """M10: without an event ID the meeting can't be picked, so nothing marks it."""
        self.lines("2026-09-29 | fp:2026-09-28|weekly sync|9f2c1a | projects/ABC Alpha/minutes/x.docx | 3")
        self.assertIsNone(build_dashboard._inbox_done("2026-09-28", "Weekly sync", None, 1, set()))
        self.assertEqual(build_dashboard._inbox_done("2026-09-28", "Weekly sync", "ev-7", 1, set()), "2026-09-29")

    def test_the_days_titles_are_counted_as_minutes_matches_them(self):
        """M14: '[ABC] Weekly sync' and 'Weekly sync' on one day are the same title, so neither is alone."""
        evs = [{"title": "[ABC] Weekly sync"}, {"title": "Weekly  sync"}, {"title": "Supplier call"}, {}]
        counts = build_dashboard._title_counts(evs)
        self.assertEqual((counts["weekly sync"], counts["supplier call"], counts["meeting"]), (2, 1, 1))


class InboxMeetingsRows(unittest.TestCase):
    """inbox_meetings itself, in a temp vault: the count covers the day's set-aside meetings, and someone else's minutes in an
    applied proposal never mark the calendar meeting processed."""
    DAY = "2026-10-21"

    def rows(self, events, processed, cleared=(), applied=None):
        import json
        import subprocess
        from test_dashboard import populate
        from test_tracker import Vault
        v = Vault()
        self.addCleanup(v.cleanup)
        populate(v)
        st = v.root / "system/staging"
        (st / "calendar.json").write_text(json.dumps({"fetched": self.DAY + " 07:00", "days": {self.DAY: events}}), encoding="utf-8")
        (v.root / "system/processed.txt").write_text("".join(r + "\n" for r in processed), encoding="utf-8")
        if cleared:
            (st / "intake-cleared.json").write_text(json.dumps({"cleared": list(cleared)}), encoding="utf-8")
        if applied:
            (st / "applied").mkdir(parents=True, exist_ok=True)
            (st / "applied" / "proposed-theirs.json").write_text(json.dumps(applied), encoding="utf-8")
        code = ("import json\nfrom datetime import date\nimport build_dashboard as bd\n"
                f"print(json.dumps(bd.inbox_meetings(bd.paths.load_settings(), [], date.fromisoformat({self.DAY!r}))))")
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'system/scripts')\n" + code], cwd=v.root,
                           capture_output=True, text=True, check=True)
        return {m["id"]: m for m in json.loads(r.stdout)["rows"]}

    @staticmethod
    def ev(eid, start, title="Weekly sync"):
        return {"id": eid, "start": start, "end": start[:2] + ":45", "title": title, "teams": True, "all_day": False,
                "private": False, "organiser": False, "sensitivity": "normal"}

    def test_a_twin_set_aside_still_counts(self):
        fp = f"2026-10-22 | fp:{self.DAY}|weekly sync|9f2c1a | projects/ABC Alpha/minutes/x.docx | 3"
        rows = self.rows([self.ev("w1", "09:00"), self.ev("w2", "15:00")], [fp],
                         cleared=[{"key": "w1", "day": self.DAY, "kind": "not", "reason": "Informal chat"}])
        self.assertEqual(sorted(rows), ["w2"])
        self.assertEqual(rows["w2"]["same_title"], 2)
        self.assertIsNone(rows["w2"]["processed"])

    def test_alone_it_is_processed(self):
        fp = f"2026-10-22 | fp:{self.DAY}|weekly sync|9f2c1a | projects/ABC Alpha/minutes/x.docx | 3"
        rows = self.rows([self.ev("w2", "15:00")], [fp])
        self.assertEqual((rows["w2"]["same_title"], rows["w2"]["processed"]), (1, "2026-10-22"))

    def test_someone_elses_minutes_never_mark_it(self):
        key = f"fp:{self.DAY}|weekly sync|9f2c1a"
        applied = {"meeting": {"key": key, "kind": "minutes by others", "title": "Weekly sync", "date": self.DAY,
                               "minutes_decision": "approved", "applied": "a1"}, "items": []}
        rows = self.rows([self.ev("w2", "15:00")], [f"2026-10-22 | {key} | projects/ABC Alpha/minutes/theirs.docx | 2"],
                         applied=applied)
        self.assertIsNone(rows["w2"]["processed"])


if __name__ == "__main__":
    unittest.main()
