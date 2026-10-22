"""#307 path 12, in Chrome: Intake's Discard offers Undo on its toast, and Undo puts the row back on Intake.

Needs Google Chrome. The shared engine and the live-server route are dev/proposals/discard-undo/*.diff; until this tree has them the
throwaway vault gets them (never this tree). Run: python3 dev/tests/test_discard_undo_browser.py
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_held_missing_source as hm  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_discard_undo import PROPOSALS, COMMAND_IN_TREE  # noqa: E402
from test_discard_undo_routes import ROUTE_IN_TREE  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import make_draft  # noqa: E402


class DiscardThenUndo(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        root = v.root
        (root / ".creaite-dev").unlink(missing_ok=True)
        if not (COMMAND_IN_TREE and ROUTE_IN_TREE):
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            if not COMMAND_IN_TREE:
                subprocess.run(["git", "apply", str(PROPOSALS / "review.py.diff")], cwd=root, check=True)
            if not ROUTE_IN_TREE:
                subprocess.run(["git", "apply", str(PROPOSALS / "live_server.py.diff")], cwd=root, check=True)
        (root / hm.TRANSCRIPT).write_text(hm.VTT, encoding="utf-8")
        make_draft(root / hm.DRAFT)
        f = root / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps({"title": hm.TITLE, "date": hm.DAY, "projects": ["ABC"], "transcript": hm.TRANSCRIPT,
                                 "draft": hm.DRAFT, "items": [hm.ITEM]}), encoding="utf-8")
        v.run("stage", str(f), script="minutes.py", cwd=root)
        (root / hm.TRANSCRIPT).unlink()

    def test_discard_then_undo_puts_the_row_back(self):
        b = self.b
        b.wait("REV.some(x=>x.ref==='meeting'&&x.held)", timeout=15)
        n = b.eval("REV.find(x=>x.ref==='meeting').n")
        row = f'#v-intake-review tr.irprop[data-irn="{n}"]'
        b.eval(f"go('intake-review', {n})")
        b.wait(f"!!document.querySelector('{row} [data-ira=held-discard]')", timeout=10)
        b.eval(f"document.querySelector('{row} [data-ira=held-discard]').click()")
        b.wait("!REV.some(x=>x.ref==='meeting'&&x.held)", timeout=15)
        self.assertFalse(b.eval(f"!!document.querySelector('{row}')"), "the row has left Intake")
        b.wait("/Undo/.test((document.getElementById('snackU')||{}).textContent||'')", timeout=5)
        b.eval("document.getElementById('snackU').click()")
        b.wait("REV.some(x=>x.ref==='meeting'&&x.held)", timeout=15)
        b.wait(f"(document.getElementById('snackT')||{{}}).textContent.includes('Put back: {hm.TITLE} is waiting in Intake again.')", timeout=5)
        n2 = b.eval("REV.find(x=>x.ref==='meeting').n")
        b.eval(f"go('intake-review', {n2})")
        b.wait(f'!!document.querySelector(\'#v-intake-review tr.irprop[data-irn="{n2}"] [data-ira=held-discard]\')', timeout=10)
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
