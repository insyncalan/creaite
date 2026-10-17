"""#109 (ux): editing a project's health from the cockpit opens the form over the page, like the other peeks, and does not
reflow the cockpit behind it (no content rect changes width at 1400 or 900px). Esc closes it and focus goes back to the pencil.

A real browser against the real live server. Set SHOTS=<folder> to also save before/after screenshots.

Run: python3 dev/tests/test_health_peek_overlay.py   (needs Google Chrome; skipped otherwise)
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

RECTS = """(()=>{ const out={}; for(const [i,e] of [...document.querySelectorAll('#v-cockpit, #v-cockpit .cock, #v-cockpit .cock > *, #v-cockpit .card')].entries()){
  const r=e.getBoundingClientRect(); out[i+':'+(e.id||e.className)]=[Math.round(r.left),Math.round(r.width)]; } return out; })()"""


class Overlay(LiveBrowserCase):
    shared_server = True

    def open_cockpit(self, width):
        b = self.b
        b.resize(width, 900)
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#v-cockpit [data-edproj]')")

    def shot(self, name, width):
        folder = os.environ.get("SHOTS")
        if folder:
            Path(folder).mkdir(parents=True, exist_ok=True)
            self.b.screenshot(str(Path(folder) / f"{name}-{width}.png"))

    def same(self, a, b, msg):
        """Equal to the pixel, but for the closed side panel's own 1px edge line, which leaves the flow when the form opens."""
        self.assertEqual(a.keys(), b.keys(), msg)
        for k in a:
            self.assertLessEqual(abs(a[k][0] - b[k][0]), 1, f"{msg}: {k}")
            self.assertLessEqual(abs(a[k][1] - b[k][1]), 1, f"{msg}: {k}")

    def check(self, width):
        b = self.b
        self.open_cockpit(width)
        before = b.eval(RECTS)
        self.shot("before-closed" if os.environ.get("PHASE") == "before" else "closed", width)
        b.click("#v-cockpit [data-edproj]")
        b.wait("document.querySelector('#panel.on #f_health')")
        self.shot("before-open" if os.environ.get("PHASE") == "before" else "open", width)
        after = b.eval(RECTS)
        self.same(before, after, f"the cockpit moved or narrowed behind the form at {width}px")
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('panel')).position"), "fixed")
        pw = b.eval("document.getElementById('panel').getBoundingClientRect().right")
        self.assertEqual(pw, width)                                        # at the window's right edge, over the page
        b.key("Escape")
        b.wait("!document.querySelector('#panel.on')")
        self.assertTrue(b.eval("!!document.activeElement.closest('[data-edproj]')"), "focus returns to the pencil")
        self.same(before, b.eval(RECTS), "the cockpit did not come back")

    def test_1400(self):
        self.check(1400)

    def test_900(self):
        self.check(900)

    def test_other_forms_keep_their_place(self):
        b = self.b
        self.open_cockpit(1400)
        b.eval("openProject('ABC','health')")
        b.wait("document.querySelector('#panel.on')")
        self.assertTrue(b.eval("document.getElementById('panel').classList.contains('pover')"))
        b.key("Escape")
        b.wait("!document.querySelector('#panel.on')")
        self.assertFalse(b.eval("document.getElementById('panel').classList.contains('pover')"))


if __name__ == "__main__":
    unittest.main()
