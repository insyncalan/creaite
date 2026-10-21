"""#232-A hardening against p250-a, the data side (pure; no browser): an uploaded file set aside, the Later "seen" rule, the store's
checks, and the confidential flag the brief's standing rule needs. A failure is a finding for the review.
Run: python3 dev/tests/test_intake_review_harden_model.py"""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import build_dashboard as bd  # noqa: E402
from test_intake_review_model import cal, model  # noqa: E402

TODAY = date(2026, 10, 8)


def aside(key, **k):
    return {"key": key, "day": "2026-10-08", "start": "", "title": "x", "cleared": "2026-10-08", **k}


class Uploads(unittest.TestCase):
    def test_not_needed_file_keeps_reason_and_leaves_the_ready_count(self):
        base, m = model(), model(aside=[aside("inbox/fresh.docx", reason="Informal chat", note="n")])
        self.assertNotIn("fresh.docx", [r["title"] for r in m["meetings"]])
        self.assertEqual([(x["title"], x["reason"], x["note"]) for x in m["not_needed"] if x["key"] == "inbox/fresh.docx"],
                         [("fresh.docx", "Informal chat", "n")])
        self.assertEqual(m["counts"]["badge"], base["counts"]["badge"] - 1)

    def test_a_later_file_is_listed_in_later_not_not_needed(self):
        m = model(aside=[aside("inbox/fresh.docx", kind="later")])
        self.assertEqual([x["title"] for x in m["later"] if x["key"] == "inbox/fresh.docx"], ["fresh.docx"])
        self.assertEqual([x for x in m["not_needed"] if x["key"] == "inbox/fresh.docx"], [])

    def test_an_entry_for_a_file_that_is_gone_or_already_processed_is_ignored(self):
        m = model(aside=[aside("inbox/gone.vtt", reason="Other"), aside("inbox/nothing.docx", reason="Other")])
        self.assertEqual([x for x in m["not_needed"] if x["key"].startswith("inbox/")], [])

    def test_a_meeting_key_never_hides_a_file(self):
        m = model(aside=[aside("ev-2", reason="Other")])
        self.assertIn("fresh.docx", [r["title"] for r in m["meetings"]])


class LaterSeen(unittest.TestCase):
    def rows(self, seen, tx):
        ordered = [{"key": "k", "transcript": tx, "loaded": None, "title": "t", "day": "2026-10-07", "start": "10:00"}]
        return bd.split_set_aside(ordered, {}, {"k": {"key": "k", "seen": seen, "cleared": "2026-10-07"}})

    def test_waiting_later_returns_when_the_transcript_arrives(self):
        self.assertEqual([r["later_back"] for r in self.rows(False, "available")["rows"]], [True])
        self.assertEqual(self.rows(False, "none")["rows"], [])
        self.assertEqual(len(self.rows(False, "none")["later"]), 1)

    def test_a_seen_later_does_not_return_by_itself(self):
        r = self.rows(True, "available")
        self.assertEqual(r["rows"], [])
        self.assertEqual(len(r["later"]), 1, "a seen Later with its transcript here must stay listed under Later so Restore can reach it")


class Store(unittest.TestCase):
    def test_seen_is_kept_for_later_only(self):
        _, e = bd.set_aside_entry({"key": "k", "day": "2026-10-08", "kind": "later", "seen": True}, TODAY)
        self.assertTrue(e.get("seen"))
        _, e = bd.set_aside_entry({"key": "k", "day": "2026-10-08", "reason": "Other", "seen": True}, TODAY)
        self.assertNotIn("seen", e)

    def test_bad_input_is_refused(self):
        for bad in ({"key": "k", "day": "nonsense"}, {"key": "k", "day": "2026-10-08", "reason": "Because"},
                    {"key": "k", "day": "2026-10-08", "kind": "later", "reason": "Other"}, {"key": "k", "day": "2026-10-08", "kind": "forever"}):
            with self.assertRaises(ValueError, msg=str(bad)):
                bd.set_aside_entry(bad, TODAY)

    def test_note_title_and_key_are_cut(self):
        k, e = bd.set_aside_entry({"key": "k" * 900, "day": "2026-10-08", "title": "t" * 900, "note": "n\n" * 400, "reason": "Other"}, TODAY)
        self.assertEqual((len(k), len(e["title"]), "\n" in e["note"], len(e["note"]) <= 200), (300, 200, False, True))

    def test_a_non_string_value_does_not_crash_the_store(self):
        k, e = bd.set_aside_entry({"key": 5, "day": "2026-10-08", "title": None, "note": ["x"], "reason": ""}, TODAY)
        self.assertEqual(k, "5")


class Confidential(unittest.TestCase):
    def test_the_row_model_marks_a_confidential_meeting(self):
        m = model(meetings={"rows": [cal(1, "2026-10-05", "09:00", "Board", confidential=True)], "cleared": [], "later": []}, queue=[], files=[])
        self.assertTrue(m["meetings"][0].get("confidential"), "the model has no confidential flag, so the page cannot hide the project")

    def test_inbox_meetings_reads_the_calendars_sensitivity(self):
        import inspect
        self.assertIn("sensitivity", inspect.getsource(bd.inbox_meetings))


if __name__ == "__main__":
    unittest.main()
