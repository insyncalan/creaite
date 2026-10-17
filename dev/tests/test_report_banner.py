"""#202 (v2.2.0): the report banner, in real Chrome on the real live server (desktop only: 1400 and 900 px; no Claude runs).

On the weekly report, the client report and the minutes view, the FIRST downward wheel tick (a real mouseWheel event of 2 px, not a
scrollTop assignment) hides the search bar and the title block at once, with no threshold, and leaves the toolbar as one slim bar
(title, project and date, zoom, Show as exported, the view's buttons). The header is in the layout (mockup report-banner, option A).
- the first 2 px tick hides both bands and the header is 48 px high within 50 ms (a threshold of any size fails this);
- the slim bar holds the title and date line, zoom, Show as exported (the weekly one also Export and Approve and file);
- a click in the slim bar (zoom +) leaves the header hidden;
- Tab (a focus) into a control in a hidden band brings the header back;
- nothing slides: the bands have no transition, with reduced motion or without;
- at the top the first rows of the report are below the toolbar, never under it.
- scrolling up by 8, 50 or 500 px never brings the header back (the slim bar stays); only the top of the report does (scrollTop 0);
- the hide leaves the reader's place in the report alone (scrollTop is what the tick made it; nothing jumps to the top).
The rule (when the header hides and returns) is one function and three constants, headerPolicy in sheetLib.js; this file tests it
through the page. Alan has not yet confirmed Jarvis's reading of his note, so that is the one place to change.

Run: python3 dev/tests/test_report_banner.py      (Chrome tier; skipped without Chrome)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reports as R  # noqa: E402  (its fixture and fixed clock)
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_minutes_editor import stage_meeting  # noqa: E402

WIDTHS = ((1400, 1000), (900, 900))
SLIM = "document.querySelector('{v} .sheet-root.rpt-slim')"


class Banner:
    """The checks; a subclass says how its view opens (VIEW, HEAD, open_view)."""
    VIEW = HEAD = ""
    shared_server = True

    def start(self, w, h):
        self.b.resize(w, h)
        self.b.reload("typeof go==='function' && LIVE")
        self.open_view()
        self.b.pump(0.3)

    def scroller(self):
        """The element that scrolls the report: the sheet's own scroller, or (the minutes at 900 px, stacked) the whole body."""
        return (f"((v,s)=>s.scrollHeight>s.clientHeight+1?s:v.querySelector('.mnwrap')||s)"
                f"(document.querySelector('{self.VIEW}'),document.querySelector('{self.VIEW} .sheet-scroll'))")

    def scroll_top(self):
        return self.b.eval(self.scroller() + ".scrollTop")

    def set_scroll(self, y):
        self.b.eval(f"{self.scroller()}.scrollTop={y}")

    def tick(self, dy=2):
        """One real wheel tick over the sheet."""
        r = self.b.eval(f"(()=>{{const r=document.querySelector('{self.VIEW} .sheet-scroll').getBoundingClientRect();"
                        "const t=Math.max(r.top,60), b=Math.min(r.bottom,window.innerHeight);"
                        "return [r.left+r.width/2, t+(b-t)/2]})()")
        self.b.call("Input.dispatchMouseEvent", type="mouseWheel", x=r[0], y=r[1], deltaX=0, deltaY=dy)

    def header_height(self):
        """Everything above the report: from the top of the window to the foot of the toolbar."""
        return self.b.eval(f"document.querySelector('{self.VIEW} .sheet-bar').getBoundingClientRect().bottom")

    def press(self, selector):
        """A real mouse click at the element's centre, without scrolling it into view (the harness's click does, and moves the page)."""
        r = self.b.eval(f"(()=>{{const r=document.querySelector({json.dumps(selector)}).getBoundingClientRect();return [r.left+r.width/2, r.top+r.height/2]}})()")
        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
            self.b.call("Input.dispatchMouseEvent", type=kind, x=r[0], y=r[1], button="left", clickCount=1)

    def hide(self):
        self.tick(2)
        self.b.wait(SLIM.format(v=self.VIEW), 5)
        self.b.pump(0.3)

    def test_first_tick_hides_the_bands_and_leaves_the_slim_bar(self):
        for w, h in WIDTHS:
            with self.subTest(width=w):
                self.start(w, h)
                self.assertFalse(self.b.eval("!!" + SLIM.format(v=self.VIEW)))
                self.assertGreater(self.header_height(), 150, "the full header is there before")
                self.tick(2)
                self.b.pump(0.05)                      # within 50 ms
                self.assertTrue(self.b.eval("!!" + SLIM.format(v=self.VIEW)), "hidden by the first tick")
                self.assertAlmostEqual(self.header_height(), 48, delta=1.5, msg="the header is the 48 px slim bar")
                st = self.b.eval(f"""(()=>{{const q=s=>document.querySelector(s);
                  return {{bar:q('.main>.bar').getBoundingClientRect().height, head:q('{self.VIEW} {self.HEAD}').getBoundingClientRect().height,
                    mini:q('{self.VIEW} .sheet-mini').innerText, text:q('{self.VIEW} .sheet-bar').innerText}}}})()""")
                self.assertEqual((st["bar"], st["head"]), (0, 0), "search bar and title block gone")
                self.assertIn("·", st["mini"])
                self.assertIn("Show as exported", st["text"])
                self.assertIn("%", st["text"])

    def test_scrolling_up_never_brings_it_back_only_the_top_does(self):
        for w, h in WIDTHS:
            for up in (8, 50, 500):
                with self.subTest(width=w, up=up):
                    self.start(w, h)
                    self.hide()
                    self.set_scroll(900)
                    self.b.pump(0.2)
                    self.tick(-up)
                    self.b.pump(0.3)
                    self.assertGreater(self.scroll_top(), 0)
                    self.assertTrue(self.b.eval("!!" + SLIM.format(v=self.VIEW)), f"still the slim bar after {up} px up")
        for w, h in WIDTHS:
            with self.subTest(width=w, top=True):
                self.start(w, h)
                self.hide()
                self.set_scroll(0)
                self.b.pump(0.3)
                self.assertFalse(self.b.eval("!!" + SLIM.format(v=self.VIEW)), "the top brings the header back")
                self.assertGreater(self.header_height(), 150)

    def test_the_hide_leaves_the_place_alone(self):
        for w, h in WIDTHS:
            with self.subTest(width=w):
                self.start(w, h)
                self.hide()
                self.b.pump(0.2)
                self.assertEqual(self.scroll_top(), 2)

    def test_a_click_in_the_slim_bar_keeps_it_hidden(self):
        for w, h in WIDTHS:
            with self.subTest(width=w):
                self.start(w, h)
                self.hide()
                self.press(f"{self.VIEW} .sheet-bar [aria-label='Zoom in']")
                self.b.pump(0.6)
                self.assertTrue(self.b.eval("!!" + SLIM.format(v=self.VIEW)))
                self.assertAlmostEqual(self.header_height(), 48, delta=1.5)

    def test_tab_into_a_hidden_control_brings_the_header_back(self):
        for w, h in WIDTHS:
            with self.subTest(width=w):
                self.start(w, h)
                self.hide()
                self.b.eval("document.querySelector('#searchBtn').focus()")
                self.b.pump(0.2)
                self.assertFalse(self.b.eval("!!" + SLIM.format(v=self.VIEW)))
                self.assertGreater(self.header_height(), 150)

    def test_nothing_slides(self):
        self.start(1400, 1000)
        self.hide()
        for sel in (".main>.bar", f"{self.VIEW} {self.HEAD}"):
            self.assertEqual(self.b.eval(f"getComputedStyle(document.querySelector('{sel}')).transitionDuration"), "0s")

    def test_the_first_rows_are_never_under_the_toolbar(self):
        for w, h in WIDTHS:
            with self.subTest(width=w):
                self.start(w, h)
                gap = self.b.eval(f"document.querySelector('{self.VIEW} .page').getBoundingClientRect().top - "
                                  f"document.querySelector('{self.VIEW} .sheet-bar').getBoundingClientRect().bottom")
                self.assertGreaterEqual(gap, 20)


class WeeklyBanner(Banner, LiveBrowserCase):
    VIEW, HEAD = "#v-weekly", ".wrhead"

    @classmethod
    def load(cls, v):
        populate(v)

    def open_view(self):
        self.b.eval("go('weekly',{code:'ABC'})")
        self.b.wait("document.querySelector('#v-weekly section[data-id=current_state]')", 20)

    def test_the_slim_bar_has_the_weekly_buttons(self):
        self.start(1400, 1000)
        self.hide()
        text = self.b.eval("document.querySelector('#v-weekly .sheet-bar').innerText")
        for word in ("Weekly report", "Export", "Approve and file", "Show as exported"):
            self.assertIn(word, text)


class WeeklyMotion(WeeklyBanner):
    """The same with motion allowed: still nothing slides."""
    reduced_motion = False


class ClientBanner(Banner, LiveBrowserCase):
    VIEW, HEAD = "#v-clientreport", ".crhead"

    @classmethod
    def load(cls, v):
        R.populate(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": R.NOW, "CREAITE_NO_LAUNCH": "1"}

    def open_view(self):
        self.b.eval("go('clientreport',{code:'ABC',week:'2026-10-09'})")
        self.b.wait("document.querySelector('#v-clientreport .crhealth')", 20)


class MinutesBanner(Banner, LiveBrowserCase):
    VIEW, HEAD = "#v-minutes", ".mnhead"

    @classmethod
    def load(cls, v):
        populate(v)
        cls.proposal = stage_meeting(v)

    def open_view(self):
        self.b.eval(f"go('minutes',{{file:{json.dumps(self.proposal)}}})")
        self.b.wait("document.querySelector('#v-minutes .mnrow')", 15)


if __name__ == "__main__":
    unittest.main()
