"""#207 (v2.3.0): the app's top bar hides on any scroll down, on every page, in real Chrome on the real live server (desktop only: 1400
and 900 px; fixed CREAITE_NOW; no Claude runs).

The bar (search or jump, ask creaite, theme) is 53 px. On every screen (Today, Work, Review, Projects, Files, People, Activity, Settings,
Help, the cockpit, Milestones, Notes) and on the three reports (weekly, client, minutes):
- the FIRST real 2 px wheel tick down hides it at once (no threshold; no slide);
- the page gains the 53 px and its text does not move (the area grows upward, the page's top padding grows by the same amount);
- scrolling up by 8, 50 or 500 px never brings it back; the pointer at the top edge does not; only scrollTop 0 does;
- Tab skips the hidden bar (it is not focusable); Cmd+K opens the palette and Cmd+J opens ask creaite while it is hidden;
- on a report #202's slim bar sits at the very top of the window once the top bar is gone.
The rule is #202's: headerPolicy and its three constants (core/scrollPolicy.js), not a second one.

Run: python3 dev/tests/test_topbar_hide.py      (Chrome tier; skipped without Chrome)
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
BAR = 53


class Common:
    shared_server = True

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": R.NOW, "CREAITE_NO_LAUNCH": "1"}

    def bar_h(self):
        return self.b.eval("document.querySelector('.main>.bar').getBoundingClientRect().height")

    def off(self):
        return self.b.eval("document.querySelector('.main>.bar').getBoundingClientRect().height===0")

    def press_wheel(self, x, y, dy):
        self.b.call("Input.dispatchMouseEvent", type="mouseWheel", x=x, y=y, deltaX=0, deltaY=dy)

    def tab_skips_the_bar(self):
        """Focus the last control before the bar, then Tab a few times: the focus never lands in the bar."""
        self.b.eval("(()=>{const f=[...document.querySelectorAll('#rail a,#rail button,#rail [tabindex]')].filter(e=>e.offsetParent&&e.tabIndex>=0);"
                    "(f[f.length-1]||document.body).focus()})()")
        for _ in range(4):
            self.b.key("Tab")
            self.assertFalse(self.b.eval("!!document.activeElement.closest('.main>.bar')"), "Tab landed in the hidden bar")
        self.b.eval("document.activeElement.blur()")       # a focus restored to a control at the page's top would scroll it there (which shows the bar)

    def keys_work(self):
        self.b.key("K", 4)
        self.b.wait("document.querySelector('#cmdk').open", 5)
        self.b.key("Escape")
        self.b.wait("!document.querySelector('#cmdk').open", 5)
        self.b.key("J", 4)
        self.b.wait("document.querySelector('#chat').classList.contains('on')", 5)
        self.b.key("J", 4)
        self.b.wait("!document.querySelector('#chat').classList.contains('on')", 5)


class Pages(Common, LiveBrowserCase):
    """Every ordinary page."""
    PAGES = (("today", "go('today')"), ("work", "go('work')"), ("review", "go('review')"), ("projects", "go('projects')"),
             ("files", "go('files')"), ("people", "go('people')"), ("activity", "go('activity')"), ("settings", "go('settings')"),
             ("help", "go('help')"), ("cockpit", "go('cockpit','ABC')"), ("milestones", "go('milestones','ABC')"),
             ("notes", "go('notes','ABC')"))

    @classmethod
    def load(cls, v):
        populate(v)

    def open(self, call, w, h):
        self.b.resize(w, h)
        self.b.reload("typeof go==='function' && LIVE")
        self.b.eval(call)
        self.b.pump(0.5)
        # the page's scroller (the biggest scrollable box in the view); a page too short to scroll gets a test-only spacer
        self.b.eval("""(()=>{const c=document.querySelector('.content'), v=c.querySelector('.view:not([hidden])');
          document.querySelectorAll('[data-tbs]').forEach(e=>e.removeAttribute('data-tbs'));
          const big=e=>/(auto|scroll)/.test(getComputedStyle(e).overflowY)&&e.clientHeight>=c.clientHeight*.5;
          let s=[v,...v.querySelectorAll('*')].find(e=>big(e)&&e.scrollHeight>e.clientHeight+60);
          if(!s){ s=[v,...v.querySelectorAll('*')].find(big)||v; const sp=document.createElement('div'); sp.style.cssText='height:3000px;flex:none'; sp.setAttribute('data-tbspacer','1'); s.appendChild(sp); }
          s.setAttribute('data-tbs','1');
          const t=[...s.querySelectorAll('h1,h2,h3,p,td,span,div')].find(e=>e.offsetParent&&e.children.length===0&&e.textContent.trim().length>2&&getComputedStyle(e).position!=='sticky'&&e.getBoundingClientRect().top>60);
          if(t) t.setAttribute('data-tbt','1'); })()""")
        self.b.pump(0.2)

    def centre(self):
        return self.b.eval("(()=>{const r=document.querySelector('[data-tbs]').getBoundingClientRect();"
                           "return [r.left+r.width/2, Math.max(r.top,60)+(Math.min(r.bottom,innerHeight)-Math.max(r.top,60))/2]})()")

    def st(self):
        return self.b.eval("document.querySelector('[data-tbs]').scrollTop")

    def test_every_page(self):
        for name, call in self.PAGES:
            for w, h in WIDTHS:
                with self.subTest(page=name, width=w):
                    self.open(call, w, h)
                    self.assertAlmostEqual(self.bar_h(), BAR, delta=1.5)
                    top0 = self.b.eval("(()=>{const t=document.querySelector('[data-tbt]');return t?t.getBoundingClientRect().top:null})()")
                    area0 = self.b.eval("document.querySelector('.content').getBoundingClientRect().height")
                    x, y = self.centre()
                    self.press_wheel(x, y, 2)
                    self.b.pump(0.05)
                    self.assertTrue(self.off(), "hidden by the first 2 px tick")
                    self.assertEqual(self.b.eval("getComputedStyle(document.querySelector('.main>.bar')).visibility"), "hidden")
                    self.assertEqual(self.b.eval("getComputedStyle(document.querySelector('.main>.bar')).transitionDuration"), "0s")
                    self.b.pump(0.2)
                    self.assertAlmostEqual(self.b.eval("document.querySelector('.content').getBoundingClientRect().height") - area0, BAR, delta=1.5,
                                           msg="the page area gains the bar's room")
                    if top0 is not None:
                        top1 = self.b.eval("document.querySelector('[data-tbt]').getBoundingClientRect().top")
                        self.assertAlmostEqual(top1, top0 - self.st(), delta=1.5, msg="the text did not move (apart from the 2 px scrolled)")
                    # scrolling up never brings it back
                    for up in (8, 50, 500):
                        self.b.eval("document.querySelector('[data-tbs]').scrollTop=900")
                        self.b.pump(0.15)
                        x, y = self.centre()
                        self.press_wheel(x, y, -min(up, self.st() - 3))      # a short page cannot go 500 px up and stay off the top
                        self.b.pump(0.25)
                        self.assertGreater(self.st(), 0)
                        self.assertTrue(self.off(), f"still hidden after {up} px up")
                    # nor the pointer at the top edge
                    for yy in (0, 1, 3):
                        self.b.call("Input.dispatchMouseEvent", type="mouseMoved", x=300, y=yy)
                    self.b.pump(0.3)
                    self.assertTrue(self.off(), "the pointer at the top edge does not bring it back")
                    self.tab_skips_the_bar()
                    self.b.eval("document.querySelector('[data-tbs]').scrollTop=900")     # Tab may have scrolled the page to its top (which shows the bar)
                    self.b.pump(0.25)
                    self.assertTrue(self.off())
                    self.keys_work()
                    self.assertTrue(self.off())
                    # the top of the page does
                    self.b.eval("document.querySelector('[data-tbs]').scrollTop=0")
                    self.b.pump(0.3)
                    self.assertFalse(self.off(), "back at scrollTop 0")
                    self.assertAlmostEqual(self.bar_h(), BAR, delta=1.5)
                    self.assertEqual(self.b.eval("document.querySelector('.main').classList.contains('tb-off')"), False)

    def test_the_padding_is_given_back(self):
        self.open("go('files')", 1400, 1000)
        before = self.b.eval("document.querySelector('.content>.view:not([hidden])').style.paddingTop")
        x, y = self.centre()
        self.press_wheel(x, y, 2)
        self.b.pump(0.2)
        self.b.eval("document.querySelector('[data-tbs]').scrollTop=0")
        self.b.pump(0.3)
        self.assertEqual(self.b.eval("document.querySelector('.content>.view:not([hidden])').style.paddingTop"), before)

    def test_focus_in_the_bar_moves_to_the_page(self):
        """A focused search or ask button hides with the bar: focus goes to the page's scroll container, never body."""
        for ctl in ("searchBtn", "askBtn"):
            with self.subTest(control=ctl):
                self.open("go('files')", 1400, 1000)
                self.b.eval(f"document.getElementById('{ctl}').focus()")
                self.assertEqual(self.b.eval("document.activeElement.id"), ctl)
                x, y = self.centre()
                self.press_wheel(x, y, 2)
                self.b.pump(0.3)
                self.assertTrue(self.off())
                self.assertTrue(self.b.eval("document.activeElement===document.querySelector('.content>.view:not([hidden])')"),
                                "focus moved to the scroll container, not body")

    def test_changing_page_brings_it_back(self):
        self.open("go('files')", 1400, 1000)
        x, y = self.centre()
        self.press_wheel(x, y, 2)
        self.b.pump(0.2)
        self.assertTrue(self.off())
        self.b.eval("go('today')")
        self.b.pump(0.3)
        self.assertFalse(self.off(), "a new page starts at its top")


class Report:
    VIEW = ""
    shared_server = True

    def start(self, w, h):
        self.b.resize(w, h)
        self.b.reload("typeof go==='function' && LIVE")
        self.open_view()
        self.b.pump(0.3)

    def scroller(self):
        return (f"((v,s)=>s.scrollHeight>s.clientHeight+1?s:v.querySelector('.mnwrap')||s)"
                f"(document.querySelector('{self.VIEW}'),document.querySelector('{self.VIEW} .sheet-scroll'))")

    def tick(self, dy=2):
        r = self.b.eval(f"(()=>{{const r=document.querySelector('{self.VIEW} .sheet-scroll').getBoundingClientRect();"
                        "const t=Math.max(r.top,60), b=Math.min(r.bottom,window.innerHeight);"
                        "return [r.left+r.width/2, t+(b-t)/2]})()")
        self.b.call("Input.dispatchMouseEvent", type="mouseWheel", x=r[0], y=r[1], deltaX=0, deltaY=dy)

    def off(self):
        return self.b.eval("document.querySelector('.main>.bar').getBoundingClientRect().height===0")

    def test_the_report_with_the_top_bar(self):
        for w, h in WIDTHS:
            with self.subTest(width=w):
                self.start(w, h)
                self.assertAlmostEqual(self.b.eval("document.querySelector('.main>.bar').getBoundingClientRect().height"), BAR, delta=1.5)
                self.tick(2)
                self.b.wait("!!document.querySelector('%s .sheet-root.rpt-slim')" % self.VIEW, 5)
                self.b.pump(0.3)
                self.assertTrue(self.off())
                self.assertAlmostEqual(self.b.eval(f"document.querySelector('{self.VIEW} .sheet-bar').getBoundingClientRect().top"), 0, delta=1.5,
                                       msg="#202's slim bar is at the very top of the window")
                for up in (8, 50, 500):
                    self.b.eval(f"{self.scroller()}.scrollTop=900")
                    self.b.pump(0.2)
                    self.tick(-up)
                    self.b.pump(0.25)
                    self.assertTrue(self.off(), f"hidden after {up} px up")
                for yy in (0, 1, 3):
                    self.b.call("Input.dispatchMouseEvent", type="mouseMoved", x=300, y=yy)
                self.b.pump(0.3)
                self.assertTrue(self.off())
                self.b.eval("(()=>{const f=[...document.querySelectorAll('#rail a,#rail button,#rail [tabindex]')].filter(e=>e.offsetParent&&e.tabIndex>=0);"
                            "(f[f.length-1]||document.body).focus()})()")
                for _ in range(4):
                    self.b.key("Tab")
                    self.assertFalse(self.b.eval("!!document.activeElement.closest('.main>.bar')"), "Tab landed in the hidden bar")
                self.b.eval("document.activeElement.blur()")
                self.b.eval(f"{self.scroller()}.scrollTop=900")
                self.b.pump(0.25)
                self.assertTrue(self.off())
                self.b.key("K", 4)
                self.b.wait("document.querySelector('#cmdk').open", 5)
                self.b.key("Escape")
                self.b.wait("!document.querySelector('#cmdk').open", 5)
                self.b.key("J", 4)
                self.b.wait("document.querySelector('#chat').classList.contains('on')", 5)
                self.b.key("J", 4)
                self.b.wait("!document.querySelector('#chat').classList.contains('on')", 5)
                self.assertTrue(self.off())
                self.b.eval(f"{self.scroller()}.scrollTop=0")
                self.b.pump(0.3)
                self.assertFalse(self.off(), "back at scrollTop 0")


class WeeklyTop(Report, Common, LiveBrowserCase):
    VIEW = "#v-reporting"

    @classmethod
    def load(cls, v):
        populate(v)

    def open_view(self):
        self.b.eval("go('weekly',{code:'ABC'})")
        self.b.wait("document.querySelector('#v-reporting section[data-id=current_state]')", 20)


class ClientTop(Report, Common, LiveBrowserCase):
    VIEW = "#v-reporting"

    @classmethod
    def load(cls, v):
        R.populate(v)

    def open_view(self):
        self.b.eval("go('clientreport',{code:'ABC',week:'2026-10-09'})")
        self.b.wait("document.querySelector('#v-reporting .wr-health')", 20)


class MinutesTop(Report, Common, LiveBrowserCase):
    VIEW = "#v-minutes"

    @classmethod
    def load(cls, v):
        populate(v)
        cls.proposal = stage_meeting(v)

    def open_view(self):
        self.b.eval(f"go('minutes',{{file:{json.dumps(self.proposal)}}})")
        self.b.wait("document.querySelector('#v-minutes tr.mi')", 15)     # #268: the item rows are the Track tables' rows


if __name__ == "__main__":
    unittest.main()
