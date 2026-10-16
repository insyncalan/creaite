"""#98 (v2.1.0): the item peek's Client-visible switch (.pk-sw) and a milestone's Visible to client switch (.mv-sw) keep a visible
track and thumb in forced colours, on and off, 24 px or more, and on differs from off in fill and in the thumb's position.
Outside forced colours both are drawn as before.

Shots go to $CREAITE_SHOTS (default ~/dev.env/team-stark-shots/ux-98), named <tag>-<switch>-<width>-<mode>-<state>.png, tag from
$CREAITE_SHOT_TAG (default "after"). Run: python3 dev/tests/test_forced_colours_toggles.py   (needs Google Chrome)
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import milestone_data  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

SHOTS = Path(os.environ.get("CREAITE_SHOTS", "~/dev.env/team-stark-shots/ux-98")).expanduser()
TAG = os.environ.get("CREAITE_SHOT_TAG", "after")
KEY = "creaite.cockpit.milestones.view"
CLEAR = "rgba(0, 0, 0, 0)"


def media(b, dark=False, forced=False):
    b.call("Emulation.setEmulatedMedia", features=[
        {"name": "prefers-reduced-motion", "value": "reduce"}, {"name": "prefers-color-scheme", "value": "dark" if dark else "light"},
        {"name": "forced-colors", "value": "active" if forced else "none"}])
    b.pump(0.15)


class Toggles(LiveBrowserCase):
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        milestone_data.load(v)

    def shot(self, name):
        SHOTS.mkdir(parents=True, exist_ok=True)
        self.b.screenshot(str(SHOTS / f"{TAG}-{name}.png"))

    def size(self, w, h):
        self.b.resize(w, h)
        self.b.pump(0.3)

    def look(self, sel):
        """The switch's box, its track and its thumb as drawn; x is the thumb's left edge inside the switch."""
        return self.b.eval("""(()=>{ const s=document.querySelector(%r), c=getComputedStyle(s), t=getComputedStyle(s,'::after'), r=s.getBoundingClientRect();
          const m=new DOMMatrix(t.transform==='none'?undefined:t.transform);
          return {w:r.width, h:r.height, bg:c.backgroundColor, bw:c.borderTopWidth, bs:c.borderTopStyle, bc:c.borderTopColor,
                  blw:c.borderLeftWidth, tbg:t.backgroundColor, tw:t.width, x:(parseFloat(t.left)||0)+m.m41, on:s.getAttribute('aria-checked')==='true'}; })()""" % sel)

    def toggle(self, sel, want):
        b = self.b
        if self.look(sel)["on"] != want:
            b.click(sel)
            b.wait("document.querySelector(%r).getAttribute('aria-checked')===%r" % (sel, "true" if want else "false"))
            b.pump(0.3)

    def open_peek(self):
        b = self.b
        b.eval("go('work'); openRecord('actions',A[0].id)")
        b.pump(0.3)
        b.eval("if(document.getElementById('pkDetT').getAttribute('aria-expanded')==='false') document.getElementById('pkDetT').click()")
        b.wait("document.querySelector('.pk-sw')")
        b.eval("document.querySelector('.pk-sw').scrollIntoView({block:'center'})")

    def open_milestone(self):
        b = self.b
        b.eval(f"localStorage.setItem('{KEY}','int'); MVAUD='int'")
        b.eval("mvOpenPage('ABC','plan')")
        b.wait("VIEW==='milestones'&&document.querySelector('#v-milestones .mv-card')")
        b.click("#mvAdd")
        b.wait("MV.add&&!document.getElementById('mvPeek').hidden&&document.getElementById('mvCli')")
        b.eval("document.getElementById('mvCli').scrollIntoView({block:'center'})")

    SWITCHES = (("pk", "open_peek", ".pk-sw"), ("mv", "open_milestone", ".mv-sw"))

    def test_the_switches_are_visible_and_differ_on_and_off_in_forced_colours(self):
        b = self.b
        for name, opener, sel in self.SWITCHES:
            getattr(self, opener)()
            for w, h in ((1400, 900), (900, 800)):
                self.size(w, h)
                for dark in (False, True):
                    mode = "dark" if dark else "light"
                    media(b, dark=dark, forced=True)
                    self.assertTrue(b.eval("matchMedia('(forced-colors: active)').matches"))
                    self.toggle(sel, False)
                    off = self.look(sel)
                    self.shot(f"{name}-{w}-{mode}-off")
                    self.toggle(sel, True)
                    on = self.look(sel)
                    self.shot(f"{name}-{w}-{mode}-on")
                    for st, lk in (("off", off), ("on", on)):
                        tag = f"{name} {st} {w} {mode}"
                        self.assertGreaterEqual(lk["w"], 24, tag)
                        self.assertGreaterEqual(lk["h"], 24, tag)
                        self.assertTrue(lk["bs"] != "none" and lk["bw"] != "0px" and lk["blw"] != "0px", f"{tag}: no border {lk}")
                        self.assertNotEqual(lk["tbg"], CLEAR, f"{tag}: no thumb")
                        self.assertNotEqual(lk["tw"], "0px", tag)
                    self.assertNotEqual(on["bg"], off["bg"], f"{name} {w} {mode}: same fill")
                    self.assertNotEqual(on["tbg"], off["tbg"], f"{name} {w} {mode}: same thumb colour")
                    self.assertGreater(on["x"], off["x"] + 8, f"{name} {w} {mode}: the thumb did not move {on['x']} {off['x']}")
                    self.toggle(sel, False)
        media(self.b)
        self.assertEqual(b.errors, [])

    def test_the_switches_are_unchanged_outside_forced_colours(self):
        b = self.b
        for name, opener, sel in self.SWITCHES:
            getattr(self, opener)()
            for dark in (False, True):
                media(b, dark=dark)
                self.toggle(sel, False)
                off = self.look(sel)
                self.toggle(sel, True)
                on = self.look(sel)
                self.assertEqual((off["w"], off["h"]), (36, 24) if name == "pk" else (40, 24))
                self.assertEqual(off["blw"], "0px")                       # no border drawn: the track is the background
                self.assertNotEqual(off["bg"], CLEAR)
                self.assertNotEqual(on["bg"], off["bg"])
                self.assertEqual(off["tw"], "16px" if name == "pk" else "18px")
                self.assertGreater(on["x"], off["x"] + 12)
            self.shot(f"{name}-1400-light-plain")
            self.toggle(sel, False)


if __name__ == "__main__":
    unittest.main()
