"""#307 path 13 / #306 part 2 (real headless Chrome): Approve minutes on minutes whose transcript has gone writes nothing.

The refusal is said at once with the "File without the transcript copy" button, and the minutes' version does not move.
Run: python3 dev/tests/test_held_editor_307b.py      (needs Google Chrome)
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
import test_minutes_editor as me  # noqa: E402


def version(b):
    return b.eval("(document.querySelector('.sheet-status')||{innerText:''}).innerText")


class FailedApproveWritesNothing(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        cls.proposal = me.stage_meeting(v)
        (v.root / "inbox" / f"{me.DAY} Steering committee.vtt").unlink()

    def test_a_failed_approve_leaves_the_version_alone(self):
        b = self.b
        b.eval(f"go('minutes',{{file:{json.dumps(self.proposal)}}})")
        b.wait("document.querySelector('#v-minutes tr.mi')", 15)
        b.pump(0.5)
        before = version(b)
        recs = sorted(self.v.root.glob("projects/**/*.json")) + sorted((self.v.root / "system/staging").glob("*.json"))
        snap = {p: p.read_bytes() for p in recs}
        b.eval("document.getElementById('mnApproveBtn').click()")
        b.pump(0.5)
        if b.eval("!!document.getElementById('mnApproveGo')"):
            b.eval("document.getElementById('mnApproveGo').click()")
        b.wait("(document.getElementById('toastHost')||{innerText:''}).innerText.includes('File without the transcript copy')", timeout=20)
        b.pump(0.8)
        self.assertEqual(version(b), before, "the page's version did not move")
        for p, data in snap.items():
            self.assertEqual(p.read_bytes(), data, f"{p.name} was not written by a failed approve")
        self.assertEqual(sorted(self.v.root.glob("projects/**/*.json")) + sorted((self.v.root / "system/staging").glob("*.json")), list(snap),
                         "no record was added")


class ApprovedThisWeek(LiveBrowserCase):
    """Path 8: minutes made from a dropped transcript, once approved, count under Approved this week and have a Done row."""

    @classmethod
    def load(cls, v):
        populate(v)
        cls.proposal = me.stage_meeting(v)

    def test_a_dropped_transcript_counts_when_approved(self):
        b = self.b
        before = b.eval("D.intake_review.counts.approved")
        b.eval(f"go('minutes',{{file:{json.dumps(self.proposal)}}})")
        b.wait("document.querySelector('#v-minutes tr.mi')", 15)
        b.pump(0.5)
        b.eval("document.getElementById('mnApproveBtn').click()")
        b.pump(0.5)
        if b.eval("!!document.getElementById('mnApproveGo')"):
            b.eval("document.getElementById('mnApproveGo').click()")
        b.wait("(document.getElementById('toastHost')||{innerText:''}).innerText.includes('Minutes approved')", timeout=25)
        b.pump(1.5)
        b.pump(1.0)
        self.assertEqual(b.eval("D.intake_review.counts.approved"), before + 1, "Approved this week moved")
        self.assertTrue(b.eval("D.intake_review.meetings.some(m=>m.stage==='approved'&&/Steering committee/i.test(m.title))"),
                        "a Done row")


if __name__ == "__main__":
    unittest.main()
