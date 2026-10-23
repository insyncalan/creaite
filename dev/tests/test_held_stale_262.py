"""2.6.2 (A): the minutes view was opened while the transcript was there, then the transcript went without a reload.

Approve minutes re-reads the held state before it saves anything: it says the plain held words with the
"File without the transcript copy" button, and the version, the draft and the proposal are not written.
Run: python3 dev/tests/test_held_stale_262.py      (needs Google Chrome)
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
import test_minutes_editor as me  # noqa: E402


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.md5(p.read_bytes()).hexdigest()
            for p in sorted(root.glob("system/staging/**/*")) + sorted(root.glob("projects/**/*")) if p.is_file() and p.name != "review-index.json"}   # review-index.json is the list's derived cache, made by any read of the list


def version(b):
    return b.eval("(document.querySelector('.sheet-status')||{innerText:''}).innerText")


class Base(LiveBrowserCase):
    TRACK = False

    @classmethod
    def load(cls, v):
        populate(v)
        cls.proposal = me.stage_meeting(v)

    def run_case(self):
        b, root = self.b, self.v.root
        b.eval(f"go('minutes',{{file:{json.dumps(self.proposal)}}})")
        b.wait("document.querySelector('#v-minutes tr.mi')", 15)
        b.pump(0.5)
        self.assertFalse(b.eval(f"REV.some(r=>r.file==={json.dumps(self.proposal)}&&r.held)"), "not held at load")
        if self.TRACK:
            b.click("#v-minutes tr.mi[data-n='1'] .mntrk button.n")
            b.wait("/^Saved/.test((document.querySelector('.sheet-status')||{innerText:''}).innerText)", timeout=15)
            b.pump(0.8)
        before, snap = version(b), snapshot(root)
        (root / "inbox" / f"{me.DAY} Steering committee.vtt").unlink()
        b.eval("document.getElementById('mnApproveBtn').click()")
        b.pump(0.5)
        if b.eval("!!document.getElementById('mnApproveGo')"):
            b.eval("document.getElementById('mnApproveGo').click()")
        b.wait("(document.getElementById('toastHost')||{innerText:''}).innerText.includes('File without the transcript copy')", timeout=20)
        b.pump(0.8)
        self.assertEqual(version(b), before, "the version did not move")
        after = snapshot(root)
        self.assertEqual([k for k in after if k in snap and snap[k] != after[k]], [], "nothing was rewritten")
        self.assertEqual(sorted(set(after) ^ set(snap)), [], "nothing was added or removed")


class NotTracked(Base):
    def test_stale_held(self):
        self.run_case()


class Tracked(Base):
    TRACK = True

    def test_stale_held(self):
        self.run_case()


if __name__ == "__main__":
    unittest.main(verbosity=1)
