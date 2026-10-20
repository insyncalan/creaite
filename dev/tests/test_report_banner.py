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
                if self.VIEW != "#v-minutes":                                   # the hub's bar is icons: the controls are there, the words are tooltips
                    self.assertTrue(self.b.eval(f"!!document.querySelector('{self.VIEW} .sheet-bar #hubExp') && !!document.querySelector('{self.VIEW} .sheet-bar #zVal')"))
                else:                                                           # #268: the minutes' bar is icons too (Show as exported is an .ib with its tip)
                    self.assertTrue(self.b.eval(f"!!document.querySelector('{self.VIEW} .sheet-bar .ib.sheet-exp[aria-label=\"Show as exported\"]')"))
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
        """Clicks that do not scroll on their own (the zoom label, Show as exported, a menu item), so a header that stays hidden
        is the rule, not a re-hide after a re-layout. Any click in the bar bringing the header back fails this."""
        for w, h in WIDTHS:
            with self.subTest(width=w):
                self.start(w, h)
                self.hide()
                before = (self.scroll_top(), self.b.eval(f"document.querySelector('{self.VIEW} .sheet-zv').textContent"))
                self.press(f"{self.VIEW} .sheet-bar .sheet-zv")
                self.b.pump(0.4)
                self.assertTrue(self.b.eval("!!" + SLIM.format(v=self.VIEW)), "the zoom label")
                self.assertEqual((self.scroll_top(), self.b.eval(f"document.querySelector('{self.VIEW} .sheet-zv').textContent")), before,
                                 "and nothing changed")
                self.press(f"{self.VIEW} .sheet-bar .sheet-exp")
                self.b.pump(0.5)
                self.assertTrue(self.b.eval("!!" + SLIM.format(v=self.VIEW)), "Show as exported")
                self.assertAlmostEqual(self.header_height(), 48, delta=1.5)
                self.menu_click()
                self.assertTrue(self.b.eval("!!" + SLIM.format(v=self.VIEW)), "a menu item")
                self.assertAlmostEqual(self.header_height(), 48, delta=1.5)

    def menu_click(self):
        """Open the toolbar's Export menu (when the view has one) and pick its HTML item with real clicks."""
        sel = "#hubExport" if self.VIEW == "#v-reporting" else f"{self.VIEW} .sheet-barr [aria-haspopup]"
        if not self.b.eval(f"!!document.querySelector({json.dumps(sel)})"):
            return
        self.press(sel)
        self.b.pump(0.4)
        item = self.b.eval("(()=>{const i=[...document.querySelectorAll('[role^=menuitem]')].find(e=>/HTML/.test(e.textContent)); "
                           "if(!i) return null; i.setAttribute('data-pick','1'); return 1})()")
        if item:
            self.press("[data-pick='1']")
        self.b.pump(0.6)

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
    """The hub's Internal view (#221 H1: the weekly page is retired; #v-reporting)."""
    VIEW, HEAD = "#v-reporting", ".wrhead"

    @classmethod
    def load(cls, v):
        populate(v)

    def open_view(self):
        self.b.eval("go('reporting','ABC')")
        self.b.wait("document.querySelector('#v-reporting section[data-id=current_state]')", 20)

    def test_a_save_that_fails_shows_in_the_slim_bar(self):
        """A real failed save (the save route stubbed to refuse) while the bar is slim: 'Not saved.' is visible, and it is a status."""
        self.start(1400, 1000)
        self.hide()
        self.b.eval("""(()=>{ const real=window.fetch.bind(window);
          window.fetch=(u,o)=>String(u).endsWith('/api/report/save')?Promise.resolve(new Response(JSON.stringify({ok:false,message:'Not saved.'}),
            {headers:{'Content-Type':'application/json'}})):real(u,o); })()""")
        self.b.eval("document.querySelector('#v-reporting [data-id=risks] tbody tr .wr-eye').click()")
        self.b.eval("document.querySelector('#v-reporting .sheet-root').dispatchEvent(new KeyboardEvent('keydown',{key:'s',metaKey:true,bubbles:true,cancelable:true}))")
        self.b.wait("/Not saved/.test(document.querySelector('#v-reporting .sheet-status').textContent)", 10)
        self.assertTrue(self.b.eval("!!" + SLIM.format(v=self.VIEW)), "still the slim bar")
        self.assertGreater(self.b.eval("document.querySelector('#v-reporting .sheet-status').getBoundingClientRect().width"), 20)
        self.assertEqual(self.b.eval("document.querySelector('#v-reporting .sheet-status').getAttribute('role')"), "status")

    def test_the_slim_bar_has_the_weekly_buttons(self):
        self.start(1400, 1000)
        self.hide()
        self.assertIn("Weekly reporting", self.b.eval("document.querySelector('#v-reporting .sheet-bar').innerText"))
        for sel in ("#hubExport", "#hubApprove", "#hubExp", "#zVal", "#hubCfg"):
            self.assertTrue(self.b.eval(f"document.querySelector('#v-reporting .sheet-bar {sel}').getBoundingClientRect().width>0"), sel)


class WeeklyMotion(WeeklyBanner):
    """The same with motion allowed: still nothing slides."""
    reduced_motion = False


class ClientBanner(Banner, LiveBrowserCase):
    """The hub's Client view."""
    VIEW, HEAD = "#v-reporting", ".wrhead"

    @classmethod
    def load(cls, v):
        R.populate(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": R.NOW, "CREAITE_NO_LAUNCH": "1"}

    def open_view(self):
        self.b.eval("go('reporting','ABC'); hubView.value='client'")
        self.b.wait("document.querySelector('#v-reporting .wr-health')", 20)


class ClientNote(ClientBanner):
    """A failed Approve client report from the slim bar leaves its message on screen, with Approve anyway."""

    def test_a_failed_approve_from_the_slim_bar_is_visible(self):
        doc = self.b.eval("""fetch('/api/report/draft',{method:'POST',headers:{'Content-Type':'application/json','X-Creaite-Token':D.token},
          body:JSON.stringify({kind:'weekly',code:'ABC',week_ending:'2026-10-09'})}).then(r=>r.json())""")["doc"]
        next(x for x in doc["sections"] if x["id"] == "health")["text"] = "UAT start slipped two weeks."        # a health that is not On track needs its reason
        self.b.eval(f"""fetch('/api/report/save',{{method:'POST',headers:{{'Content-Type':'application/json','X-Creaite-Token':D.token}},
          body:JSON.stringify({{doc:{json.dumps(doc)},base_version:0}})}}).then(r=>r.json())""")
        self.b.eval("""fetch('/api/report/approve',{method:'POST',headers:{'Content-Type':'application/json','X-Creaite-Token':D.token},
          body:JSON.stringify({kind:'weekly',code:'ABC',week_ending:'2026-10-09',force:true})}).then(r=>r.json())""")
        self.start(1400, 1000)
        self.hide()
        self.b.eval("""(()=>{ const real=window.fetch.bind(window);
          window.fetch=(u,o)=>String(u).endsWith('/api/report/approve')&&/"kind":"client"/.test(String(o&&o.body))
            ?Promise.resolve(new Response(JSON.stringify({ok:false,message:'The check is awaiting review'}),{headers:{'Content-Type':'application/json'}})):real(u,o); })()""")
        self.press("#hubApprove")
        self.b.wait("[...document.querySelectorAll('.ddmenu.on [role^=menuitem]')].some(e=>/client report/.test(e.textContent)&&e.getAttribute('aria-disabled')!=='true')", 10)
        self.b.eval("[...document.querySelectorAll('.ddmenu.on [role^=menuitem]')].find(e=>/client report/.test(e.textContent)).setAttribute('data-pick','1')")
        self.press("[data-pick='1']")
        self.b.wait("document.querySelector('.crnote')", 10)
        self.b.pump(0.3)
        self.assertTrue(self.b.eval("!!" + SLIM.format(v=self.VIEW)), "still the slim bar")
        r = self.b.eval("(()=>{const n=document.querySelector('.crnote').getBoundingClientRect(), f=document.querySelector('[data-crforce]').getBoundingClientRect();"
                        "return [n.width,n.height,n.top,f.width,f.height]})()")
        self.assertGreater(r[0], 100)
        self.assertGreater(r[1], 10)
        self.assertGreater(r[3], 20, "Approve anyway can be pressed")


class MinutesBanner(Banner, LiveBrowserCase):
    VIEW, HEAD = "#v-minutes", ".mnhead"

    @classmethod
    def load(cls, v):
        populate(v)
        cls.proposal = stage_meeting(v)

    def open_view(self):
        self.b.eval(f"go('minutes',{{file:{json.dumps(self.proposal)}}})")
        self.b.wait("document.querySelector('#v-minutes tr.mi')", 15)     # #268: the item rows are the Track tables' rows


if __name__ == "__main__":
    unittest.main()
