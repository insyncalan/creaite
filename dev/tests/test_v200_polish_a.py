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

    # ---- (1) ----
    def open_note(self):
        b = self.b
        b.eval(f"location.hash='#notes=FAL&n='+encodeURIComponent({json.dumps(self.FILE)})")
        b.wait(f"noteCur.value&&noteCur.value.path==={json.dumps(fx.NOTE)}&&!!document.querySelector('#v-notes .nbody [data-p]')", 20)

    def select_low(self, words):
        """Select `words`, and scroll so that its line is low in the window (near the bottom), where the menu has no room."""
        b = self.b
        b.click("#v-notes .nbody")
        b.eval("""(()=>{ const h=document.querySelector('#v-notes .nbody').cxed, doc=h.editor.state.doc; let at=-1;
          doc.descendants((n,pos)=>{ if(at<0&&n.isText){ const i=n.text.indexOf(%s); if(i>=0) at=pos+i; } });
          h.focus(); h.editor.commands.setTextSelection({from:at,to:at+%d}); })()""" % (json.dumps(words), len(words)))
        b.wait("document.querySelector('#aiLayer .aibar')")
        b.pump(0.2)

    def pin_bar_low(self):
        """Put the bar near the bottom of the window whatever the note's length is (as a selection low on the page would)."""
        self.b.eval("(()=>{ const a=document.querySelector('#aiLayer .aibar'); a.style.top=(innerHeight-60)+'px'; })()")
        self.b.pump(0.1)

    def menu_state(self):
        return self.b.eval("""(()=>{ const m=document.querySelector('#aiLayer [role=menu]'); if(!m) return null;
          const r=m.getBoundingClientRect(), its=[...m.querySelectorAll('[data-ai]')];
          return {top:r.top, bottom:r.bottom, ih:innerHeight, n:its.length, scroll:m.scrollHeight>m.clientHeight+1,
            inside:its.every(e=>{const q=e.getBoundingClientRect(); return q.top>=r.top-1&&q.bottom<=r.bottom+1&&q.top>=0&&q.bottom<=innerHeight}),
            first:its[0].dataset.ai, last:its[its.length-1].dataset.ai}; })()""")

    def test_the_menu_stays_in_a_short_window_and_every_item_is_reachable(self):
        b = self.b
        self.open_note()
        for w, h in ((1400, 700), (900, 700), (900, 900)):
            self.size(w, h)
            self.select_low("Sandbox access granted")
            self.pin_bar_low()
            b.click("#aiLayer .aibar button[aria-haspopup]")
            b.wait("document.querySelector('#aiLayer [role=menu]')")
            b.pump(0.3)
            self.shot(f"ai-menu-{w}x{h}")
            st = self.menu_state()
            self.assertEqual(st["n"], 10)
            self.assertGreaterEqual(st["top"], 0, f"{w}x{h}: above the window {st}")
            self.assertLessEqual(st["bottom"], st["ih"], f"{w}x{h}: below the window {st}")
            # mouse: the last item scrolls into view and is clickable
            b.eval("document.querySelector('#aiLayer [role=menu] [data-ai=custom]').scrollIntoView({block:'nearest'})")
            self.assertTrue(b.eval("""(()=>{ const q=document.querySelector('#aiLayer [role=menu] [data-ai=custom]').getBoundingClientRect();
              return q.top>=0&&q.bottom<=innerHeight })()"""), f"{w}x{h}: last item not reachable")
            # keyboard: End reaches the last, Home the first, arrows between
            b.key("End")
            self.assertEqual(b.eval("document.activeElement.dataset.ai"), "custom")
            self.assertTrue(b.eval("""(()=>{ const q=document.activeElement.getBoundingClientRect(); return q.top>=0&&q.bottom<=innerHeight })()"""))
            b.key("Home")
            self.assertEqual(b.eval("document.activeElement.dataset.ai"), "rewrite")
            b.key("ArrowDown")
            self.assertEqual(b.eval("document.activeElement.dataset.ai"), "shorter")
            b.key("ArrowUp")
            self.assertEqual(b.eval("document.activeElement.dataset.ai"), "rewrite")
            b.key("Escape")
            b.wait("!document.querySelector('#aiLayer [role=menu]')")
            self.assertTrue(b.eval("!!document.querySelector('#aiLayer .aibar button[aria-haspopup]') && document.activeElement===document.querySelector('#aiLayer .aibar button[aria-haspopup]')"))
            b.eval("document.querySelector('#v-notes .nbody').cxed.focus()")
        self.assertEqual(b.errors, [])

    def test_the_menu_under_a_bar_with_room_still_opens_downward(self):
        b = self.b
        self.size(1400, 900)
        self.open_note()
        self.select_low("Sandbox access granted")
        b.eval("document.querySelector('#aiLayer .aibar').style.top='80px'")
        b.click("#aiLayer .aibar button[aria-haspopup]")
        b.wait("document.querySelector('#aiLayer [role=menu]')")
        b.pump(0.2)
        self.assertTrue(b.eval("""(()=>{ const m=document.querySelector('#aiLayer [role=menu]').getBoundingClientRect(),
          a=document.querySelector('#aiLayer .aibar button[aria-haspopup]').getBoundingClientRect(); return m.top>=a.bottom })()"""))
        self.shot("ai-menu-room-1400x900")


if __name__ == "__main__":
    unittest.main()
