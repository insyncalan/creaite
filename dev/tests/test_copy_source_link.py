"""#269 round 2 (L-B), the guarded half: `tracker.py apply` files a meeting's transcript or draft only when the source is a plain file,
checked when the proposal is validated and again just before the copy, so a transcript swapped for a link after `minutes.py stage`
checked it is never filed (the link's target, possibly outside the vault, would otherwise be copied into the project).

Run: python3 dev/tests/test_copy_source_link.py      (quick tier)
Skipped until dev/proposals/minutes-stage-spec/tracker-copy-link.diff is applied (tracker.py is a guarded file: Alan approves it).
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, REPO, Vault, make_draft  # noqa: E402

APPLIED = "#269 round 2 (L-B)" in (REPO / "system/scripts/tracker.py").read_text(encoding="utf-8")
DAY = "2026-10-14"
TRANSCRIPT = f"inbox/{DAY} Steering committee.vtt"
DRAFT = f"system/staging/drafts/{DAY} Steering committee.docx"
FILED = f"{ABC}/transcripts/{DAY} Steering committee.vtt"
VTT = "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v Alan Carter>Morning.</v>\n"


@unittest.skipUnless(APPLIED, "needs dev/proposals/minutes-stage-spec/tracker-copy-link.diff (a guarded change)")
class CopySourceIsAPlainFile(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.root = self.v.root
        self.v.run("init")
        self.outside = Path(tempfile.mkdtemp(prefix="creaite-outside-"))
        (self.outside / "Board pack.vtt").write_text("WEBVTT\n\nnot for the project\n")
        (self.root / "inbox").mkdir(exist_ok=True)
        make_draft(self.root / DRAFT)

    def tearDown(self):
        self.v.cleanup()
        shutil.rmtree(self.outside, ignore_errors=True)

    def meeting(self):
        return {"key": f"fp:{DAY}|steering committee|x", "title": "Steering committee", "date": DAY, "projects": ["ABC"],
                "draft": DRAFT, "transcript": TRANSCRIPT, "minutes_decision": "approved", "file_ops": [
                    {"op": "copy", "from": "draft", "to": f"{ABC}/minutes/{DAY} Steering committee.docx"},
                    {"op": "copy", "from": "transcript", "to": FILED}]}

    def test_a_transcript_that_is_a_link_is_not_filed(self):
        (self.root / TRANSCRIPT).symlink_to(self.outside / "Board pack.vtt")
        self.v.propose("meeting", [], source_run="cx-minutes", meeting=self.meeting())
        r = self.v.run("apply", ok=False)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("link", r.stdout + r.stderr)
        self.assertFalse((self.root / FILED).exists())

    def test_a_transcript_swapped_for_a_link_after_the_check_is_not_filed(self):
        (self.root / TRANSCRIPT).write_text(VTT)
        code = ("import json, os, sys; sys.path.insert(0, 'system/scripts'); import tracker\n"
                f"blk = json.loads({json.dumps(json.dumps(self.meeting()))})\n"
                "fop = blk['file_ops'][1]\n"
                "tracker.check_file_op(fop, blk)\n"
                f"os.unlink({TRANSCRIPT!r}); os.symlink({str(self.outside / 'Board pack.vtt')!r}, {TRANSCRIPT!r})\n"
                "try:\n"
                "    tracker._op_copy(1, fop, blk, [])\n"
                "    print('copied')\n"
                "except tracker.Invalid as e:\n"
                "    print('refused', e)\n")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.root, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("refused", r.stdout)
        self.assertFalse((self.root / FILED).exists())

    def test_a_plain_transcript_is_filed(self):
        (self.root / TRANSCRIPT).write_text(VTT)
        self.v.propose("meeting", [], source_run="cx-minutes", meeting=self.meeting())
        self.v.run("apply")
        self.assertEqual((self.root / FILED).read_text(), VTT)


if __name__ == "__main__":
    unittest.main()
