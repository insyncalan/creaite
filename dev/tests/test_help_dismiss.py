"""Defect #249 (v2.5.1): the Help sidebar (the ? panel, helpscreen.js) is easily dismissed.

Alan, 19-10-2026: "when the help sidebar is up it should be easily dismissed with an esc or clicking outside the sidebar itself."
- Esc closes it when it is the top layer, and focus goes back to the opener (or what had focus before).
- A click outside it closes it; a click inside it does not; the ? key toggles it.
  (#284, v2.5.4: Today's header ? button is gone; the ? key is the opener everywhere.)
- A layer above it (a modal dialog) takes Esc first; a layer under it (the peek) stays when Esc closes Help.
- The click that closes it passes through: the panel is a side sheet, not a modal, and the page beside it stays usable.
- The same after moving between pages, and at 900 px wide.

Run: python3 dev/tests/test_help_dismiss.py   (Chrome tier; skipped without Chrome)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ON = "document.getElementById('helpPanel').classList.contains('on')"


class HelpDismiss(LiveBrowserCase):
    shared_server = True        # it only reads

    def setUp(self):
        super().setUp()
        self.b.call("Emulation.setFocusEmulationEnabled", enabled=True)

    def on(self):
        return self.b.eval(ON)

    def today(self):
        self.b.eval("go('today'); renderToday()")
        self.b.wait("document.getElementById('dayClose')")

    def press_help(self):
        self.b.eval("document.activeElement&&document.activeElement.blur&&document.activeElement.blur()")
        self.b.call("Input.dispatchKeyEvent", type="keyDown", key="?", code="Slash", text="?", windowsVirtualKeyCode=191, modifiers=8)
        self.b.call("Input.dispatchKeyEvent", type="keyUp", key="?", code="Slash", windowsVirtualKeyCode=191, modifiers=8)
        self.b.wait(ON)

    def click_at(self, x, y):
        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
            self.b.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", clickCount=1)
        self.b.pump(0.1)

    def click_outside(self):
        """A real click on plain page text left of the panel: the page's title (Today: the day band's date), which acts on no click."""
        x, y = self.b.eval("""(()=>{ const p=document.getElementById('helpPanel').getBoundingClientRect();
          const t=[...document.querySelectorAll('.view h1, #v-today .dayband h1, #v-today .dayband .dtitle, #v-today .dayband')]
            .find(e=>{ const r=e.getBoundingClientRect(); return r.width&&r.height&&r.left<p.left-20; });
          const r=t.getBoundingClientRect(); return [r.left+Math.min(20,r.width/2), r.top+r.height/2]; })()""")
        self.assertFalse(self.b.eval(f"!!document.elementFromPoint({x},{y}).closest('#helpPanel')"))
        self.click_at(x, y)

    def focus_close_the_day(self):
        """What had focus before Help opened: the Close the day door (the ? key leaves focus where it was)."""
        self.b.eval("document.getElementById('dayClose').focus()")

    def press_help_from_door(self):
        self.focus_close_the_day()
        self.b.call("Input.dispatchKeyEvent", type="keyDown", key="?", code="Slash", text="?", windowsVirtualKeyCode=191, modifiers=8)
        self.b.call("Input.dispatchKeyEvent", type="keyUp", key="?", code="Slash", windowsVirtualKeyCode=191, modifiers=8)
        self.b.wait(ON)

    def test_esc_closes_it_and_focus_goes_back(self):
        self.today()
        self.press_help_from_door()
        self.b.key("Escape")
        self.assertFalse(self.on())
        self.assertTrue(self.b.eval("document.activeElement===document.getElementById('dayClose')"))

    def test_a_click_outside_closes_it_and_focus_goes_back(self):
        self.today()
        self.press_help_from_door()
        self.click_outside()
        self.assertFalse(self.on())
        self.assertTrue(self.b.eval("document.activeElement===document.getElementById('dayClose')"))

    def test_a_click_inside_keeps_it_open(self):
        self.today()
        self.press_help()
        self.b.click("#helpPanel .sub")
        self.assertTrue(self.on())
        self.b.click("#helpPanel #hpnT")
        self.assertTrue(self.on())

    def press_key(self):
        self.b.call("Input.dispatchKeyEvent", type="keyDown", key="?", code="Slash", text="?", windowsVirtualKeyCode=191, modifiers=8)
        self.b.call("Input.dispatchKeyEvent", type="keyUp", key="?", code="Slash", windowsVirtualKeyCode=191, modifiers=8)
        self.b.frames(2)

    def test_the_key_toggles_it(self):
        self.today()
        self.press_help()
        self.press_key()
        self.assertFalse(self.on())
        self.press_key()
        self.assertTrue(self.on())

    def test_a_dialog_over_it_takes_esc_first(self):
        self.today()
        self.press_help()
        self.b.eval("openCk()")
        self.b.wait("document.getElementById('cmdk').open")
        self.b.key("Escape")
        self.assertEqual(self.b.eval(f"[document.getElementById('cmdk').open, {ON}]"), [False, True])
        self.b.key("Escape")
        self.assertFalse(self.on())

    def test_esc_closes_help_and_leaves_the_peek_under_it(self):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        b.eval("openRecord('actions', document.querySelector('#workTbl tbody tr[data-row]').dataset.row)")
        b.wait("document.getElementById('panel').classList.contains('on')")
        self.press_help()
        b.key("Escape")
        self.assertEqual(b.eval(f"[{ON}, document.getElementById('panel').classList.contains('on')]"), [False, True])

    def test_after_moving_between_pages_and_at_900_px(self):
        for width in (1400, 900):
            self.b.resize(width, 900)
            for view in ("work", "review", "people"):
                self.b.eval(f"go({view!r})")
                self.b.frames(2)
                self.press_help()
                self.b.key("Escape")
                self.assertFalse(self.on(), (width, view, "Esc"))
                self.press_help()
                self.click_outside()
                self.assertFalse(self.on(), (width, view, "click outside"))
            self.today()
            self.press_help()
            self.press_key()
            self.assertFalse(self.on(), (width, "the ? key toggles"))


if __name__ == "__main__":
    unittest.main()
