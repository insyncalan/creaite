"""#306: minutes (a record, edited in the minutes view) whose transcript has gone: Approve minutes says so in plain words, and
approving them without the transcript copy (review.py approve --without-transcript, as the page's button does) then Approve minutes
files them with their ticked items."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_minutes_approve as tm  # noqa: E402
from test_tracker import REPO  # noqa: E402


class Held(tm.Base):
    def test_plain_refusal_then_file_without_the_transcript(self):
        (self.v.root / "inbox/2026-10-14 Steering committee.vtt").unlink()
        r = self.approve()
        self.assertFalse(r["ok"])
        for jargon in ("staged", "proposal", "inbox/", ".vtt"):
            self.assertNotIn(jargon, r["message"])
        self.assertIn("transcript", r["message"])
        o = self.v.run("approve", "1", "--without-transcript", "--as-staged", script="review.py", ok=False, cwd=self.v.root)
        self.assertEqual(o.returncode, 0, o.stdout + o.stderr)
        r = self.approve()
        self.assertTrue(r["ok"], r)
        self.assertGreaterEqual(r["approved"], 1)
        self.assertTrue(list(self.v.root.glob("projects/*/minutes/2026-10-14 *")), "the minutes are filed")

    def test_review_path_really_drops_the_copy_for_a_record(self):
        """Root cause of #306: decide_record re-read the file and lost the dropped copy, so Apply held the minutes again."""
        (self.v.root / "inbox/2026-10-14 Steering committee.vtt").unlink()
        o = self.v.run("approve", "1", "--without-transcript", script="review.py", ok=False, cwd=self.v.root)
        self.assertEqual(o.returncode, 0, o.stdout + o.stderr)
        r = self.v.run("apply", ok=False, cwd=self.v.root)
        self.assertNotIn("Held in Review", r.stdout)
        self.assertIn("written", r.stdout)
        self.assertTrue(list(self.v.root.glob("projects/*/minutes/2026-10-14 *")))

    def test_the_minutes_view_offers_the_button(self):
        src = (REPO / "system/templates/dashboard/src/components/minutes/MinutesView.jsx").read_text(encoding="utf-8")
        self.assertIn("File without the transcript copy", src)
        self.assertIn("Filed without the transcript copy: ${r.n} item", src)
        self.assertIn("Not saved because", src)


if __name__ == "__main__":
    unittest.main(argv=["x", "Held"])
