"""#281: the Draft email preview is user-resizable, built once in the shared preview: the dialog's #dePrev (decision chase, action chase,
update request, person page and Review all open it) and the peek's chase pane (#chMail). Dragging the grip on the bottom edge makes
it taller or shorter and the text and table reflow. At desktop width and 900px.

Cap's review: a drag on the grip that is released below the popup (on the scrim) must not close it; the preview starts fitted to the
email (no blank space under a short one), at most 28vh so the grip shows without scrolling the popup; a dragged size survives a mode
switch; a real click on the scrim still closes it.

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

    def grip(self, center=True):
        b = self.b
        if center is not None:
            b.eval(f"document.querySelector({self.SEL!r}).scrollIntoView({{block:{'center' if center else 'nearest'!r}}})")
            b.pump(0.2)
        return b.eval(f"(()=>{{const r=document.querySelector({self.SEL!r}).getBoundingClientRect(); return {{x:r.right-6,y:r.bottom-6}}}})()")

    def grip_drag(self, dy, to=None, center=True):
        """Press the grip, move by dy (or to the y given) and release there: real mouse events, so the click lands where a mouse's would."""
        b = self.b
        r = self.grip(center)
        end = r["y"] + dy if to is None else to
        for kind, y in (("mouseMoved", r["y"]), ("mousePressed", r["y"]), ("mouseMoved", (r["y"] + end) / 2), ("mouseMoved", end),
                        ("mouseReleased", end)):
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

    def open_it(self):
        b = self.b
        b.eval("openDraftEmail('Sara Example','chase')")
        b.wait("document.querySelector('#deDlg').open&&document.querySelector('#dePrev')&&document.querySelector('#dePrev').textContent.length>40")
        b.pump(0.2)

    def tearDown(self):
        self.b.eval("document.querySelector('#dePrev')&&(document.querySelector('#dePrev').style.height=''); "
                    "document.querySelector('#deDlg')&&document.querySelector('#deDlg').open&&document.querySelector('#deDlg').close(); true")
        super().tearDown()

    def test_dialog_preview_resizes(self):
        self.open_it()
        self.check()

    def test_a_drag_released_below_the_popup_keeps_it_open(self):
        b = self.b
        for width, height in ((900, 700), (1440, 900), (1280, 900)):
            with self.subTest(width=width):
                b.resize(width, height)
                b.pump(0.3)
                self.open_it()
                start = self.h()
                bottom = b.eval("document.querySelector('#deDlg').getBoundingClientRect().bottom")
                below = min(bottom + 30, height - 3)
                self.assertGreater(below, bottom, "room under the popup to release on the scrim")
                self.grip_drag(0, to=below, center=False)
                self.assertTrue(b.eval("document.querySelector('#deDlg').open"), f"still open at {width}")
                self.assertGreater(self.h(), start, f"taller at {width}")
                b.eval("document.querySelector('#dePrev').style.height=''; document.querySelector('#deDlg').close(); true")
                b.pump(0.2)
        self.assertEqual(b.errors, [])

    def test_a_real_scrim_click_still_closes_it(self):
        b = self.b
        b.resize(1280, 900)
        self.open_it()
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=5, button="none")
        for kind in ("mousePressed", "mouseReleased"):
            b.call("Input.dispatchMouseEvent", type=kind, x=5, y=5, button="left", clickCount=1)
        b.wait("!document.querySelector('#deDlg').open")

    def test_it_starts_fitted_with_the_grip_in_view(self):
        """At 900 and 1440 wide, 900 high. (At 700 high the controls above the preview fill the popup, so a short scroll is needed.)"""
        b = self.b
        for width, height in ((900, 900), (1440, 900)):
            with self.subTest(width=width):
                b.resize(width, height)
                b.pump(0.3)
                self.open_it()
                b.eval("document.querySelector('#deDlg .prepbody').scrollTop=0; true")
                b.pump(0.1)
                g = self.grip(center=None)
                body = b.eval("document.querySelector('#deDlg .prepbody').getBoundingClientRect().bottom")
                self.assertLess(g["y"], body, f"the grip shows without scrolling the popup at {width}x{height}")
                fit = b.eval("(()=>{const e=document.querySelector('#dePrev'); return e.scrollHeight<=e.clientHeight+1 || "
                             "e.getBoundingClientRect().height>=innerHeight*0.28-2})()")
                self.assertTrue(fit, "fitted to the email, up to 28vh")
                b.eval("document.querySelector('#deDlg').close(); true")
                b.pump(0.2)

    def test_a_dragged_size_survives_a_mode_switch(self):
        b = self.b
        b.resize(1280, 1000)
        self.open_it()
        self.grip_drag(150)
        dragged = self.h()
        b.click("[data-demode='update']")
        b.wait("document.querySelector('[data-demode=update]').getAttribute('aria-pressed')==='true'")
        b.pump(0.2)
        self.assertLessEqual(abs(self.h() - dragged), 2)


class PanePreview(Resizable, ChaseCase):
    SEL = "#chMail"

    def test_peek_pane_preview_resizes(self):
        self.chase(self.theirs)
        self.check()

    def test_a_drag_released_past_the_pane_keeps_it_open(self):
        b = self.b
        for width, height in ((900, 700), (1440, 900)):
            with self.subTest(width=width):
                b.resize(width, height)
                b.pump(0.3)
                self.chase(self.theirs)
                self.grip_drag(0, to=height - 3)
                self.assertTrue(b.eval("!!document.querySelector('#chMail')&&document.getElementById('panel').classList.contains('peek')"),
                                f"the chase pane stays open at {width}")
                b.eval("document.querySelector('#chMail').style.height=''; true")
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
