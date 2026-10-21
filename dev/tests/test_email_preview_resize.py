"""#281: the Draft email preview is user-resizable, built once in the shared preview: the dialog's #dePrev (decision chase, action chase,
update request, person page and Review all open it) and the peek's chase pane (#chMail). Dragging the grip on the bottom edge makes
it taller or shorter and the text and table reflow. At desktop width and 900px.

Run: python3 dev/tests/test_email_preview_resize.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_draft_chase_pane import ChaseCase  # noqa: E402
from test_drafts_email import EmailCase  # noqa: E402


class Resizable:
    SEL = ""

    def h(self):
        return round(self.b.eval(f"document.querySelector({self.SEL!r}).getBoundingClientRect().height"))

    def grip_drag(self, dy):
        b = self.b
        b.eval(f"document.querySelector({self.SEL!r}).scrollIntoView({{block:'center'}})")
        b.pump(0.2)
        r = b.eval(f"(()=>{{const r=document.querySelector({self.SEL!r}).getBoundingClientRect(); return {{x:r.right-6,y:r.bottom-6}}}})()")
        for kind, y in (("mouseMoved", r["y"]), ("mousePressed", r["y"]), ("mouseMoved", r["y"] + dy / 2), ("mouseMoved", r["y"] + dy),
                        ("mouseReleased", r["y"] + dy)):
            b.call("Input.dispatchMouseEvent", type=kind, x=r["x"], y=y, button="left", clickCount=1)
        b.pump(0.2)

    def check(self):
        b = self.b
        for width in (1280, 900):
            b.resize(width, 1000)
            b.pump(0.2)
            self.assertEqual(b.eval(f"getComputedStyle(document.querySelector({self.SEL!r})).resize"), "vertical")
            start = self.h()
            self.assertGreaterEqual(start, 128)
            self.grip_drag(120)
            self.assertGreater(self.h(), start + 60, f"taller at {width}")
            taller = self.h()
            self.grip_drag(-200)
            self.assertLess(self.h(), taller - 100, f"shorter at {width}")
            self.assertGreaterEqual(self.h(), 128)
            b.eval(f"document.querySelector({self.SEL!r}).style.height=''")
        self.assertEqual(b.errors, [])


class DialogPreview(Resizable, EmailCase):
    SEL = "#dePrev"

    def test_dialog_preview_resizes(self):
        b = self.b
        b.eval("openDraftEmail('Sara Example','chase')")
        b.wait("document.querySelector('#dePrev')&&document.querySelector('#dePrev').textContent.length>40")
        self.check()


class PanePreview(Resizable, ChaseCase):
    SEL = "#chMail"

    def test_peek_pane_preview_resizes(self):
        self.chase(self.theirs)
        self.check()


if __name__ == "__main__":
    unittest.main()
