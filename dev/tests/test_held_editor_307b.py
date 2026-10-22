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


class StaleMinutesView(LiveBrowserCase):
    """Path 19: the minutes were approved elsewhere; Approve minutes in an old view says plainly what happened and refreshes."""

    @classmethod
    def load(cls, v):
        populate(v)
        cls.proposal = me.stage_meeting(v)

    def test_a_stale_view_says_the_minutes_moved_and_refreshes(self):
        b = self.b
        b.eval(f"go('minutes',{{file:{json.dumps(self.proposal)}}})")
        b.wait("document.querySelector('#v-minutes tr.mi')", 15)
        b.pump(0.5)
        # approved elsewhere (Claude Code, another tab): the record leaves the drafts
        b.eval(f"api('/api/minutes/approve',{{file:{json.dumps(self.proposal)},group:true,own:[]}}).then(r=>{{window.ELSEWHERE=r}})")
        b.wait("window.ELSEWHERE", 25)
        b.eval("document.getElementById('mnApproveBtn').click()")
        b.pump(0.5)
        if b.eval("!!document.getElementById('mnApproveGo')"):
            b.eval("document.getElementById('mnApproveGo').click()")
        b.wait("/moved or been filed/.test((document.getElementById('toastHost')||{innerText:''}).innerText)", timeout=20)
        t = toast(b)
        self.assertIn("These minutes have moved or been filed. The list has been refreshed.", t)
        self.assertNotIn("isn't there", t)
        b.pump(1.0)
        self.assertFalse(b.eval("!!document.getElementById('mnApproveBtn') && !document.getElementById('mnApproveBtn').disabled"),
                         "the view no longer offers Approve minutes")


def toast(b):
    return b.eval("(document.getElementById('toastHost')||{innerText:''}).innerText")


if __name__ == "__main__":
    unittest.main()
