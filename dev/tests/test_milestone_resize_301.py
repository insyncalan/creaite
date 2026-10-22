"""#301: the milestone plan line on the project page (and the Milestones page, which shares it) is as tall as you drag its corner grip
(the browser's own, as the Draft email preview's, #281). Taller spreads the label rows, shorter scrolls; there is a smallest and a
largest height; double-click on the grip goes back; the height is remembered per browser. Mouse only; desktop width and 900px.

Run: python3 dev/tests/test_milestone_resize_301.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

SEL = "#v-cockpit .mv-stripwrap"


class MilestoneResize(LiveBrowserCase):
    shared_server = True

    def open(self):
        b = self.b
        b.eval("try{localStorage.removeItem('creaite.mvStripH')}catch(e){}")
        b.eval("go('cockpit','ABC')")
        b.wait(f"!!document.querySelector({SEL!r})")
        b.pump(0.3)

    def h(self):
        return round(self.b.eval(f"document.querySelector({SEL!r}).getBoundingClientRect().height"))

    def grip(self, dy, clicks=1):
        b = self.b
        b.eval(f"document.querySelector({SEL!r}).scrollIntoView({{block:'center'}})")
        b.pump(0.2)
        r = b.eval(f"(()=>{{const r=document.querySelector({SEL!r}).getBoundingClientRect(); return {{x:r.right-6,y:r.bottom-6}}}})()")
        if clicks == 2:
            b.eval(f"document.querySelector({SEL!r}).dispatchEvent(new MouseEvent('dblclick',{{bubbles:true,clientX:{r['x']},clientY:{r['y']}}}))")
        else:
            for kind, y in (("mouseMoved", r["y"]), ("mousePressed", r["y"]), ("mouseMoved", r["y"] + dy / 2), ("mouseMoved", r["y"] + dy),
                            ("mouseReleased", r["y"] + dy)):
                b.call("Input.dispatchMouseEvent", type=kind, x=r["x"], y=y, button="left", clickCount=1)
        b.pump(0.3)

    def test_drag_limits_reset_and_remember(self):
        b = self.b
        for width in (1280, 900):
            b.resize(width, 1000)
            self.open()
            self.assertEqual(b.eval(f"getComputedStyle(document.querySelector({SEL!r})).resize"), "vertical")
            start = self.h()
            self.grip(150)
            taller = self.h()
            self.assertGreater(taller, start + 80, f"taller at {width}")
            self.assertEqual(b.eval(f"document.querySelector({SEL!r}).querySelector('.mv-strip').style.height") != "", True)
            self.grip(-600)
            self.assertEqual(self.h(), 120, f"smallest at {width}")
            self.grip(3000)
            self.assertLessEqual(self.h(), round(1000 * 0.85) + 1, f"largest at {width}")
            self.assertGreater(self.h(), 300)
            self.grip(-(self.h() - taller))                                  # back to a middle height
            mid = self.h()
            self.assertEqual(b.eval("localStorage.getItem('creaite.mvStripH')"), str(mid))
            b.eval("go('today')")
            b.wait("VIEW==='today'")
            b.eval("go('cockpit','ABC')")
            b.wait(f"!!document.querySelector({SEL!r})")
            b.pump(0.3)
            self.assertEqual(self.h(), mid, f"remembered at {width}")
            self.grip(0, clicks=2)
            self.assertEqual(self.h(), start, f"double-click resets at {width}")
            self.assertIsNone(b.eval("localStorage.getItem('creaite.mvStripH')"))
        self.assertEqual(b.errors, [])

    def test_a_click_away_from_the_grip_changes_nothing(self):
        b = self.b
        self.open()
        self.grip(100)
        before = self.h()
        b.eval(f"(()=>{{const w=document.querySelector({SEL!r}), r=w.getBoundingClientRect(); w.dispatchEvent(new MouseEvent('dblclick',{{bubbles:true,clientX:r.left+30,clientY:r.top+30}}))}})()")
        self.assertEqual(self.h(), before)


if __name__ == "__main__":
    unittest.main()
