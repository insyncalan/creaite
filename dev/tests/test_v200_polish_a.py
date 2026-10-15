"""v2.0.0 polish A (check 44's sheet, #61): two defects.

- (5) in forced colours the capture drawer's Confidential switch keeps a visible track and thumb, on and off, 24 px or more,
  and the two states differ;
- (1) the AI bar's menu (10 items) stays inside a short window: it flips upward or scrolls, and every item can be reached
  by keyboard and mouse.

Shots go to $CREAITE_SHOTS (default ~/dev.env/team-stark-shots/v200-polish/a), named <tag>-<screen>-<width>-<mode>.png, tag
from $CREAITE_SHOT_TAG (default "after").
Run: python3 dev/tests/test_v200_polish_a.py   (needs Google Chrome)
"""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import notes_find_fixture as fx  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

SHOTS = Path(os.environ.get("CREAITE_SHOTS", "~/dev.env/team-stark-shots/v200-polish/a")).expanduser()
TAG = os.environ.get("CREAITE_SHOT_TAG", "after")
META, SHIFT = 4, 8


def media(b, dark=False, forced=False):
    f = [{"name": "prefers-reduced-motion", "value": "reduce"}, {"name": "prefers-color-scheme", "value": "dark" if dark else "light"},
         {"name": "forced-colors", "value": "active" if forced else "none"}]
    b.call("Emulation.setEmulatedMedia", features=f)
    b.pump(0.15)


class Polish(LiveBrowserCase):
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        fx.load(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": fx.NOW}

    FILE = fx.NOTE.rsplit("/", 1)[1]

    def shot(self, name):
        SHOTS.mkdir(parents=True, exist_ok=True)
        self.b.screenshot(str(SHOTS / f"{TAG}-{name}.png"))

    def size(self, w, h):
        self.b.resize(w, h)
        self.b.pump(0.3)

    # ---- (5) ----
    def open_drawer(self):
        b = self.b
        b.eval("document.body.focus()")
        b.key("N", META | SHIFT)
        b.wait("document.getElementById('capDrawer')&&!document.getElementById('capDrawer').hidden&&!!document.getElementById('capBody').cxed")

    def switch_look(self):
        """The switch's box, its track (background or border) and its thumb, as drawn."""
        return self.b.eval("""(()=>{ const s=document.getElementById('capConf'), c=getComputedStyle(s), t=getComputedStyle(s,'::after'), r=s.getBoundingClientRect();
          return {w:r.width, h:r.height, bg:c.backgroundColor, bw:c.borderTopWidth, bs:c.borderTopStyle, bc:c.borderTopColor,
                  tbg:t.backgroundColor, tx:t.transform, on:s.checked}; })()""")

    def test_confidential_switch_is_visible_and_differs_on_and_off_in_forced_colours(self):
        b = self.b
        self.open_drawer()
        for w, h in ((1400, 900), (900, 800)):
            self.size(w, h)
            for dark in (False, True):
                mode = "dark" if dark else "light"
                media(b, dark=dark, forced=True)
                self.assertTrue(b.eval("matchMedia('(forced-colors: active)').matches"))
                if b.eval("document.getElementById('capConf').checked"):
                    b.click("#capConf")
                off = self.switch_look()
                self.shot(f"switch-{w}-{mode}-off")
                b.click("#capConf")
                b.wait("document.getElementById('capConf').checked")
                b.pump(0.3)
                on = self.switch_look()
                self.shot(f"switch-{w}-{mode}-on")
                for st, look in (("off", off), ("on", on)):
                    self.assertGreaterEqual(look["w"], 24, f"{st} {w} {mode}")
                    self.assertGreaterEqual(look["h"], 24, f"{st} {w} {mode}")
                    visible = look["bs"] != "none" and look["bw"] != "0px"
                    self.assertTrue(visible, f"{st} {w} {mode}: no border {look}")
                    self.assertNotEqual(look["tbg"], "rgba(0, 0, 0, 0)", f"{st} {w} {mode}: no thumb")
                self.assertNotEqual((on["bg"], on["tx"], on["bc"]), (off["bg"], off["tx"], off["bc"]), f"{w} {mode}: on looks like off")
                b.click("#capConf")                                                  # back to off
                b.wait("!document.getElementById('capConf').checked")
        media(b)
        self.assertEqual(b.errors, [])

    def test_the_switch_is_unchanged_outside_forced_colours(self):
        b = self.b
        self.open_drawer()
        media(b)
        look = self.switch_look()
        self.assertEqual((look["w"], look["h"]), (40, 24))
        self.assertNotEqual(look["bg"], "rgba(0, 0, 0, 0)")
        self.shot("switch-1400-light-plain")


if __name__ == "__main__":
    unittest.main()
