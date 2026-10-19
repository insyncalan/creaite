"""#232-0 (v2.5.0): Intake and Review on one page. The merged row model (build_dashboard.intake_review_model, pure), the
routine rule it shares with `review.py bulk` (review.hold_reason), and the Later and Not needed store (intake-cleared.json).
No browser. The folding rules (core/irFold.js) are tested in test_intake_review_fold.py; the page in test_intake_review_page.py."""
import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import build_dashboard  # noqa: E402
import review  # noqa: E402
from clear_day_support import ClearData, MONDAY  # noqa: E402
from test_meetings import page_data  # noqa: E402

TODAY = date(2026, 10, 8)


def cal(i, day, start, title, **k):
    return {"id": f"ev-{i}", "key": f"ev-{i}", "day": day, "start": start, "end": "", "title": title, "p": "ABC",
            "private": False, "teams": True, "processed": None, "draft": False, "transcript": None, "loaded": None, **k}


def q(n, file, hold="", p="ABC", age=0, kind="actions"):
    return {"n": n, "file": file, "p": p, "hold": hold, "indiv": bool(hold), "kind": kind, "age": age}


META = {"proposed-steer.json": {"mkey": "calendar:ev-1", "title": "ABC Steering", "day": "2026-10-05", "transcript": None, "run": "cx-minutes"},
        "proposed-up.json": {"mkey": "fp:2026-10-06|notes|abc", "title": "Upload notes", "day": "2026-10-06",
                             "transcript": "inbox/notes.vtt", "run": "cx-minutes"},
        "proposed-old.json": {"mkey": "calendar:ev-9", "title": "Old review", "day": "2026-09-20", "transcript": None, "run": "cx-minutes"},
        "proposed-sweep.json": {"mkey": None, "title": "", "day": "", "transcript": None, "run": "cx-sweep"},
        "proposed-edit.json": {"mkey": None, "title": "", "day": "", "transcript": None, "run": "cx-edit"}}


def model(**over):
    meetings = {"rows": [cal(1, "2026-10-05", "09:00", "ABC Steering", processed=None, draft=True),
                         cal(2, "2026-10-05", "15:00", "Weekly sync", transcript="available"),
                         cal(3, "2026-10-07", "10:00", "Supplier call"),
                         cal(4, "2026-10-06", "11:00", "Done meeting", processed="2026-10-06")],
                "cleared": [cal(5, "2026-10-06", "12:00", "Chat", reason="Informal chat", note="just a catch-up")],
                "later": [cal(6, "2026-10-07", "16:00", "Snoozed", later_since="2026-10-07")]}
    files = [{"name": "notes.vtt", "path": "inbox/notes.vtt", "state": "draft", "event": None, "p": "ABC", "date": "2026-10-06", "ext": "vtt"},
             {"name": "fresh.docx", "path": "inbox/fresh.docx", "state": "new", "event": None, "p": None, "date": "2026-10-08", "ext": "docx"},
             {"name": "gone.vtt", "path": "inbox/gone.vtt", "state": "processed", "event": None, "p": None, "date": "2026-10-01", "ext": "vtt"}]
    queue = [q(1, "proposed-steer.json", "minutes", kind="draft", age=3), q(2, "proposed-steer.json", "new decision"),
             q(3, "proposed-steer.json"), q(4, "proposed-steer.json"), q(5, "proposed-steer.json", "need a project", p=None),
             q(6, "proposed-up.json"), q(7, "proposed-old.json", "new risk", age=19),
             q(8, "proposed-sweep.json"), q(9, "proposed-sweep.json", "closing update"), q(10, "proposed-edit.json", "health change")]
    args = dict(meetings=meetings, files=files, queue=queue, meta=META, today=TODAY, stale_after=14)
    args.update(over)
    return build_dashboard.intake_review_model(**args)


class RowModelTests(unittest.TestCase):
    def setUp(self):
        self.m = model()
        self.by = {r["title"]: r for r in self.m["meetings"]}

    def test_one_list_of_calendar_rows_uploads_and_drafts(self):
        self.assertEqual(self.m["v"], 1)
        self.assertEqual({r["title"]: r["src"] for r in self.m["meetings"]},
                         {"ABC Steering": "calendar", "Weekly sync": "calendar", "Supplier call": "calendar", "Done meeting": "calendar",
                          "notes.vtt": "upload", "fresh.docx": "upload", "Old review": "draft"})
        days = [r["day"] for r in self.m["meetings"]]
        self.assertEqual(days, sorted(days, reverse=True))                      # newest day first
        self.assertEqual(len({r["id"] for r in self.m["meetings"]}), len(self.m["meetings"]))   # stable unique ids

    def test_proposals_nest_under_their_meeting_split_by_the_bulk_rule(self):
        steer = self.by["ABC Steering"]
        self.assertEqual((steer["stage"], steer["state"]), ("drafted", "proposals"))
        self.assertEqual(steer["groups"], {"needs": [1, 2, 5], "routine": [3, 4]})
        self.assertEqual(steer["files"], ["proposed-steer.json"])
        self.assertEqual(self.by["notes.vtt"]["groups"], {"needs": [], "routine": [6]})     # joined by its transcript path
        self.assertEqual(self.by["Old review"]["groups"], {"needs": [7], "routine": []})
        self.assertTrue(self.by["Old review"]["stale"])                                     # 19 days, past 14
        self.assertFalse(steer["stale"])

    def test_stages_and_states(self):
        st = {t: (r["stage"], r["state"]) for t, r in self.by.items()}
        self.assertEqual(st["Weekly sync"], ("arrived", "ready"))
        self.assertEqual(st["Supplier call"], ("arrived", "waiting"))
        self.assertEqual(st["Done meeting"], ("approved", "done"))
        self.assertEqual(st["fresh.docx"], ("arrived", "ready"))
        self.assertNotIn("gone.vtt", self.by)                                               # processed files are not rows

    def test_mail_and_other_proposals_sit_apart(self):
        self.assertEqual(self.m["mail"], {"needs": [9], "routine": [8]})
        self.assertEqual(self.m["other"], {"needs": [10], "routine": []})

    def test_later_and_not_needed_lists(self):
        self.assertEqual([x["title"] for x in self.m["later"]], ["Snoozed"])
        self.assertEqual(self.m["later"][0]["since"], "2026-10-07")
        self.assertEqual([(x["title"], x["reason"], x["note"]) for x in self.m["not_needed"]], [("Chat", "Informal chat", "just a catch-up")])

    def test_counts_and_badge(self):
        c = self.m["counts"]
        self.assertEqual((c["arrived"], c["ready"], c["drafted"], c["approved"]), (3, 2, 3, 1))
        self.assertEqual(c["to_approve"], 10)
        self.assertEqual(c["badge"], 12)                                                    # ready meetings and files + proposals

    def test_empty(self):
        m = build_dashboard.intake_review_model({}, [], [], {}, TODAY, 14)
        self.assertEqual(m["meetings"], [])
        self.assertEqual(m["counts"], {"arrived": 0, "ready": 0, "drafted": 0, "approved": 0, "to_approve": 0, "badge": 0})

    def test_a_loaded_transcript_is_its_calendar_row_not_a_second_row(self):
        meetings = {"rows": [cal(2, "2026-10-05", "15:00", "Weekly sync", loaded="inbox/Weekly sync.vtt")]}
        files = [{"name": "Weekly sync.vtt", "path": "inbox/Weekly sync.vtt", "state": "new", "event": "ev-2", "p": None, "date": "2026-10-05"}]
        m = build_dashboard.intake_review_model(meetings, files, [], {}, TODAY, 14)
        self.assertEqual([(r["src"], r["state"]) for r in m["meetings"]], [("calendar", "ready")])


class HoldReasonTests(unittest.TestCase):
    """The one routine rule: what `review.py bulk` approves is exactly what the page calls routine."""

    def item(self, **k):
        return {"op": "new", "table": "actions", "id": "ABC-A-900", "values": {"description": "x", "project": "ABC"},
                "match": "strong", "decision": "pending", **k}

    def test_rule(self):
        self.assertIsNone(review.hold_reason(self.item()))                                       # owner and date never tested
        self.assertEqual(review.hold_reason(self.item(table="decisions")), "new decision")
        self.assertEqual(review.hold_reason(self.item(table="raid", values={"type": "Risk", "project": "ABC"})), "new risk")
        self.assertIsNone(review.hold_reason(self.item(table="raid", values={"type": "Issue", "project": "ABC"})))
        self.assertEqual(review.hold_reason(self.item(match="possible")), "need a project")
        self.assertEqual(review.hold_reason(self.item(flags=["conflict"])), "conflict")
        self.assertEqual(review.hold_reason(self.item(flags=["invalid"])), "invalid")            # Alan, 18-10-2026
        self.assertIsNone(review.hold_reason(self.item(inferred=["owner"])))                     # a guessed field stays routine
        self.assertEqual(review.hold_reason({"op": "update", "table": "actions", "id": "ABC-A-001",
                                             "changes": {"status": "Closed"}}), "closing update")


class LaterAndNotNeededStoreTests(ClearData, unittest.TestCase):
    """intake-cleared.json carries kind, reason and note; Later comes back when the transcript arrives."""
    NOW = MONDAY

    def test_not_needed_keeps_its_reason_and_note(self):
        self.py(f"b.clear_meetings([{{'key':'ev-1','day':'{self.mon}','start':'09:00','title':'ABC Steering','reason':'No decisions','note':'two\\nlines'}}])")
        e = self.cleared_file()["cleared"][0]
        self.assertEqual((e["reason"], e["note"]), ("No decisions", "two lines"))
        self.v.run(script="build_dashboard.py")
        d = page_data(self.v)
        self.assertEqual([(x["key"], x["reason"]) for x in d["intake_review"]["not_needed"]], [("ev-1", "No decisions")])

    def test_a_bad_reason_or_kind_is_refused(self):
        for bad in ("'reason':'Because'", "'kind':'forever'", "'kind':'later','reason':'Other'"):
            with self.subTest(bad=bad), self.assertRaises(AssertionError):
                self.py(f"b.clear_meetings([{{'key':'ev-1','day':'{self.mon}','start':'09:00','title':'a',{bad}}}])")
        self.assertIsNone(self.cleared_file())

    def test_later_waits_then_returns_with_the_transcript_and_restore_undoes(self):
        self.py(f"b.clear_meetings([{{'key':'ev-2','day':'{self.mon}','start':'15:00','title':'Weekly sync 12','kind':'later'}}])")
        self.v.run(script="build_dashboard.py")
        d = page_data(self.v)
        self.assertNotIn("ev-2", [r["id"] for r in d["meetings"]["rows"]])
        self.assertEqual([r["id"] for r in d["meetings"]["later"]], ["ev-2"])
        self.assertEqual([r["id"] for r in d["meetings"]["cleared"]], [])                  # Later is not Not needed
        (self.v.root / "system/staging/transcripts.json").write_text(json.dumps({"checked": {"ev-2": {"status": "available", "checked": "x"}}}))
        self.v.run(script="build_dashboard.py")
        d = page_data(self.v)
        row = next(r for r in d["meetings"]["rows"] if r["id"] == "ev-2")
        self.assertTrue(row["later_back"])
        self.assertEqual(d["meetings"]["later"], [])
        self.assertEqual(self.py("print(b.restore_meetings(keys=['ev-2']))").strip(), "1")

    def test_later_then_not_needed_changes_the_entry(self):
        base = f"'key':'ev-2','day':'{self.mon}','start':'15:00','title':'Weekly sync 12'"
        self.py(f"b.clear_meetings([{{{base},'kind':'later'}}])")
        self.assertEqual(self.py(f"print(b.clear_meetings([{{{base},'reason':'Other'}}]))").strip(), "1")
        e = self.cleared_file()["cleared"]
        self.assertEqual(len(e), 1)
        self.assertEqual((e[0].get("kind"), e[0]["reason"]), (None, "Other"))


if __name__ == "__main__":
    unittest.main()
