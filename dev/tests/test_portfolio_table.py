"""BL-285 (v1.9.0): Today's Portfolio table. The project's description is no longer a line under its name but the name's
tooltip, on hover and on keyboard focus, and screen readers get it too (aria-describedby); an empty description has no
tooltip. The columns resize like Work's (pointer drag, the keyboard separator, 60 to 900 px), remembered in this browser
under creaite-colwidths `portfolio|<column>`; double-click resets one; a resize never opens the project; at 320 px nothing
scrolls sideways. And BL-308's source checks: the wordmark has no dashed draft copy, and BL-291's rule for it is gone.

The page tests run in a real browser on the snapshot sample vault (test_snapshots: fixed day, UTC, en-GB): ABC, Example
Programme, has a description (its client, "Example Client Ltd"); DEF, Digital Enablement, has none.

Run: python3 dev/tests/test_portfolio_table.py   (the page tests need Google Chrome; skipped otherwise)
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_snapshots as ts  # noqa: E402
from live_browser import TEST_PALETTES  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DASH = ROOT / "system" / "templates" / "dashboard"
PF = "#pfTbl"
ABC = f'{PF} tr[data-cock="ABC"]'
DEF = f'{PF} tr[data-cock="DEF"]'


class Source(unittest.TestCase):
    """Without a browser: the template's own files."""

    def test_wordmark_has_no_dashed_copy(self):
        shell = (DASH / "shell.html").read_text(encoding="utf-8")
        logo = re.search(r'<div class="logo">.*?</div>', shell, re.S).group(0)
        self.assertNotIn("wmd", logo)
        self.assertNotIn("stroke-dasharray", logo)
        self.assertEqual(logo.count("<use "), 1, "the word once")
        self.assertIn('aria-label="creaite"', logo)
        self.assertIn('class="wmb"', logo, "the saffron bar")

    def test_bl291_rule_is_gone(self):
        css = (DASH / "style.css").read_text(encoding="utf-8")
        self.assertNotIn(".wmd", css)
        for block in re.findall(r"@media \(prefers-contrast: more\)\{(.*?)\n?\}", css, re.S):
            self.assertNotIn(".logo", block)

    def test_description_is_not_a_line_under_the_name(self):
        src = (DASH / "src" / "today.js").read_text(encoding="utf-8")
        fn = src[src.index("export function portfolioTable("):src.index("export function pfResize(")]
        self.assertNotIn("p.client)}</div>", fn)
        self.assertIn('class="pfname"', fn)
        self.assertNotIn(" title=", fn, "never a title attribute")


class Portfolio(ts.Snapshots):
    test_every_screen_matches_its_golden = None

    def setUp(self):
        super().setUp()
        b = self.b
        b.eval("try{ localStorage.removeItem('creaite-colwidths'); }catch(e){} shared.RZ={}; go('today')")
        b.wait(f"!document.getElementById('v-today').hidden && document.querySelector({json.dumps(ABC)})", 15)
        b.pump(0.3)

    def tip(self):
        return self.b.eval("(()=>{ const t=document.getElementById('tip'); return t&&t.classList.contains('on')?t.textContent:null; })()")

    def colw(self, col):
        return self.b.eval(f"Math.round(document.querySelector('{PF} th[data-col=\"{col}\"]').getBoundingClientRect().width)")

    # 1. Description on hover and focus
    def test_one_line_per_project_and_the_description_is_the_names_tooltip(self):
        b = self.b
        r = b.eval(f"""(()=>{{ const td=document.querySelector({json.dumps(ABC)}+' td'), n=td.querySelector('button.pfname'), d=document.getElementById(n.getAttribute('aria-describedby'));
          return {{name:n.textContent, tip:n.dataset.tip, title:n.hasAttribute('title'), subs:td.querySelectorAll('.sub').length, desc:d&&d.textContent, hidden:d&&d.classList.contains('vh')}}; }})()""")
        self.assertEqual(r, {"name": "Example Programme", "tip": "Example Client Ltd", "title": False, "subs": 0,
                             "desc": "Example Client Ltd", "hidden": True})
        # the pointer resting on the name shows it
        pos = b.box(f"{ABC} button.pfname")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=pos["x"], y=pos["y"])
        b.wait("document.getElementById('tip')&&document.getElementById('tip').classList.contains('on')", 5)
        self.assertEqual(self.tip(), "Example Client Ltd")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=990)
        b.pump(0.4)

    def test_keyboard_focus_shows_the_description_and_enter_opens_the_project(self):
        b = self.b
        b.eval("document.body.focus()")
        b.key("Tab")             # a keyboard user: focus becomes :focus-visible
        for _ in range(80):
            if b.eval("document.activeElement&&document.activeElement.matches('#pfTbl tr[data-cock=\"ABC\"] .pfname')"):
                break
            b.key("Tab")
        self.assertTrue(b.eval("document.activeElement.matches('#pfTbl .pfname')"), "Tab reaches the project's name")
        b.wait("document.getElementById('tip')&&document.getElementById('tip').classList.contains('on')", 5)
        self.assertEqual(self.tip(), "Example Client Ltd")
        self.assertEqual(b.eval("document.activeElement.getAttribute('aria-describedby')"), "pfd-ABC", "screen readers keep the description")
        b.key("Enter")
        b.wait("VIEW==='cockpit' && COCK==='ABC'", 5)

    def test_an_empty_description_has_no_tooltip(self):
        r = self.b.eval(f"""(()=>{{ const n=document.querySelector({json.dumps(DEF)}+' button.pfname');
          return {{name:n.textContent, tip:n.hasAttribute('data-tip'), desc:n.hasAttribute('aria-describedby')}}; }})()""")
        self.assertEqual(r, {"name": "Digital Enablement", "tip": False, "desc": False})

    # 2. Resizable columns
    def test_every_column_has_a_resize_handle(self):
        r = self.b.eval(f"""[...document.querySelectorAll('{PF} thead th')].map(th=>{{ const h=th.querySelector('.colrz');
          return [th.dataset.col, !!h&&h.getAttribute('role'), !!h&&h.tabIndex, !!h&&h.getAttribute('aria-label')]; }})""")
        self.assertEqual(r, [["project", "separator", 0, "Resize Project column"], ["health", "separator", 0, "Resize Health column"],
                             ["evidence", "separator", 0, "Resize Evidence column"], ["trend", "separator", 0, "Resize 6 weeks column"],
                             ["next", "separator", 0, "Resize Next milestone column"]])

    def test_drag_resizes_is_remembered_and_double_click_resets(self):
        b = self.b
        w0 = self.colw("project")
        h = b.box(f'{PF} th[data-col="project"] .colrz')
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=h["x"], y=h["y"])
        b.call("Input.dispatchMouseEvent", type="mousePressed", x=h["x"], y=h["y"], button="left", buttons=1, clickCount=1)
        for i in range(1, 9):
            b.call("Input.dispatchMouseEvent", type="mouseMoved", x=h["x"] + 10 * i, y=h["y"], button="left", buttons=1)
        b.call("Input.dispatchMouseEvent", type="mouseReleased", x=h["x"] + 80, y=h["y"], button="left", buttons=0, clickCount=1)
        b.pump(0.2)
        self.assertEqual(b.eval("VIEW"), "today", "a resize never opens the project")
        w1 = self.colw("project")
        self.assertAlmostEqual(w1, w0 + 80, delta=3)
        saved = b.eval("JSON.parse(localStorage.getItem('creaite-colwidths'))['portfolio|project']")
        self.assertAlmostEqual(saved, w1, delta=1)
        # survives a reload
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('today')")
        b.wait(f"document.querySelector({json.dumps(ABC)})", 15)
        b.pump(0.3)
        self.assertAlmostEqual(self.colw("project"), w1, delta=1)
        # a click on the handle doesn't open the project; a double-click puts the column back
        b.click(f'{PF} th[data-col="project"] .colrz')
        self.assertEqual(b.eval("VIEW"), "today")
        b.click(f'{PF} th[data-col="project"] .colrz', count=2)
        b.pump(0.2)
        self.assertIsNone(b.eval("JSON.parse(localStorage.getItem('creaite-colwidths')||'{}')['portfolio|project']??null"))
        self.assertAlmostEqual(self.colw("project"), w0, delta=3)

    def test_keyboard_resizes_within_60_to_900(self):
        b = self.b
        b.eval(f"document.querySelector('{PF} th[data-col=\"health\"] .colrz').focus()")
        w0 = self.colw("health")
        b.key("ArrowRight")
        self.assertAlmostEqual(self.colw("health"), w0 + 16, delta=2)
        self.assertEqual(b.eval("VIEW"), "today")
        for _ in range(80):
            b.key("ArrowLeft")
        small = b.eval("JSON.parse(localStorage.getItem('creaite-colwidths'))['portfolio|health']")
        self.assertGreaterEqual(small, 60)          # never under 60 (the column's own content may stop it sooner)
        self.assertLess(small, w0)
        for _ in range(70):
            b.key("ArrowRight")
        self.assertEqual(b.eval("JSON.parse(localStorage.getItem('creaite-colwidths'))['portfolio|health']"), 900)

    def test_nothing_scrolls_sideways_at_320(self):
        b = self.b
        b.eval("shared.RZ['portfolio|project']=900; shared.RZ['portfolio|evidence']=900; renderToday()")
        try:
            b.resize(320, 800)
            b.pump(0.4)
            r = b.eval("""(()=>{ const s=document.scrollingElement, v=document.getElementById('v-today');
              return {page:s.scrollWidth-s.clientWidth, view:v.scrollWidth-v.clientWidth, frame:getComputedStyle(document.getElementById('pfTbl')).overflowX}; })()""")
            self.assertLessEqual(r["page"], 0)
            self.assertLessEqual(r["view"], 0)
            self.assertEqual(r["frame"], "auto", "the table scrolls inside its frame")
        finally:
            b.resize(self.width, self.height)


    # 4. #162: the six-week health trend (option B, height is health), its tooltip and its key
    BARS = "(()=>{ const hs={}; document.querySelectorAll('#pfTbl .spark:not(.mini) > i').forEach(i=>{ hs[i.className]=Math.max(hs[i.className]||0, i.getBoundingClientRect().height); }); return hs; })()"

    def test_the_bars_are_six_and_height_is_health(self):
        b = self.b
        b.eval("""(()=>{ const p=P.find(x=>x.code==='ABC'); p.trail=['ok','warn','bad','','ok','warn']; p.trailend=['2026-09-04','2026-09-11','2026-09-18','2026-09-25','2026-10-02','2026-10-09'];
          p.trailwhy=['','Late build','Vendor gone','','','Recovering']; renderToday(); })()""")
        b.pump(0.3)
        self.assertEqual(b.eval(f"document.querySelectorAll({json.dumps(ABC)}+' .spark > i').length"), 6)
        h = b.eval(f"""[...document.querySelectorAll({json.dumps(ABC)}+' .spark > i')].map(i=>[i.className, Math.round(i.getBoundingClientRect().height)])""")
        by = {c: v for c, v in h}
        self.assertGreater(by["s-ok"], by["s-warn"], "On track is the tallest bar")
        self.assertGreater(by["s-warn"], by["s-bad"])
        self.assertLess(by["s-bad"], by["s-warn"], "Off track is the shortest bar")
        self.assertLess(by["s-"], by["s-bad"], "a week with no update is the thin line")
        self.assertLessEqual(by["s-"], 3)
        self.assertEqual(b.eval("document.querySelector('#pfTbl th[data-col=trend]').firstChild.textContent"), "6 weeks")

    def test_the_tooltip_lists_six_weeks_with_the_reason_and_the_keyboard_moves_between_them(self):
        b = self.b
        b.eval("""(()=>{ const p=P.find(x=>x.code==='ABC'); p.trail=['ok','warn','bad','','ok','warn']; p.trailend=['2026-09-04','2026-09-11','2026-09-18','2026-09-25','2026-10-02','2026-10-09'];
          p.trailwhy=['','Late build','Vendor gone','','','Recovering']; renderToday(); })()""")
        b.eval("document.body.focus()")
        for _ in range(120):
            b.key("Tab")
            if b.eval("document.activeElement.matches('#pfTbl tr[data-cock=\"ABC\"] .spark')"):
                break
        b.wait("document.getElementById('sparkTip')&&!document.getElementById('sparkTip').hidden", 5)
        o = b.eval("(()=>{ const t=document.getElementById('sparkTip'); return {rows:t.querySelectorAll('.spk-list li').length, text:t.textContent}; })()")
        self.assertEqual(o["rows"], 6, "the week list has six rows")
        self.assertIn("Week ending 09-10-2026 · this week", o["text"])
        self.assertIn("Recovering", o["text"])
        self.assertIn("At risk", o["text"])
        b.key("Home")
        b.pump(0.2)
        self.assertIn("Week ending 04-09-2026", b.eval("document.getElementById('sparkTip').textContent"))
        b.key("ArrowRight")
        b.pump(0.2)
        t = b.eval("document.getElementById('sparkTip').textContent")
        self.assertIn("Week ending 11-09-2026", t)
        self.assertIn("Changed from On track", t)
        self.assertIn("Late build", t)
        b.key("Escape")
        b.pump(0.2)
        self.assertTrue(b.eval("document.getElementById('sparkTip').hidden"))

    def test_the_question_mark_opens_the_key_and_escape_closes_it(self):
        b = self.b
        b.click(f"{PF} th[data-col=trend] .legbtn")
        b.wait("document.getElementById('sparkLeg')", 5)
        self.assertEqual(b.eval("document.querySelectorAll('#sparkLeg .spark.mini > i').length"), 4, "the four bars of the key")
        self.assertEqual(b.eval("document.querySelector('.legbtn').getAttribute('aria-expanded')"), "true")
        b.key("Escape")
        b.pump(0.2)
        self.assertFalse(b.eval("!!document.getElementById('sparkLeg')"))
        self.assertEqual(b.eval("document.activeElement.classList.contains('legbtn')"), True)

    def test_the_project_page_strip_has_the_key_and_it_says_the_reason_is_shortened(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("VIEW==='cockpit' && COCK==='ABC'", 5)
        b.click(".cock .legbtn")
        b.wait("document.getElementById('sparkLeg')", 5)
        self.assertIn("shortened to 160 characters", b.eval("document.getElementById('sparkLeg').textContent"))
        b.key("Escape")
        b.pump(0.2)
        self.assertFalse(b.eval("!!document.getElementById('sparkLeg')"))
        self.assertEqual(b.eval("document.activeElement.classList.contains('legbtn') && !!document.activeElement.closest('.cock')"), True,
                         "Esc returns focus to the button that was opened")

    def test_the_bars_read_in_both_palettes_and_modes(self):
        b = self.b
        for palette in TEST_PALETTES:
            for mode in ("light", "dark"):
                b.eval(f"document.documentElement.dataset.palette='{palette}'; document.documentElement.dataset.theme='{mode}'")
                b.pump(0.1)
                r = b.eval("""(()=>{ const c=k=>getComputedStyle(document.querySelector('#pfTbl .spark:not(.mini) > i.s-'+k)).backgroundColor, bg=getComputedStyle(document.body).backgroundColor;
                  return {ok:c('ok'), warn:c('warn'), bad:c('bad'), bg}; })()""") if b.eval("!!document.querySelector('#pfTbl .spark:not(.mini) > i.s-ok')") else None
                if r:
                    self.assertEqual(len({r["ok"], r["warn"], r["bad"]}), 3, f"{palette} {mode}: three colours")
                    self.assertNotIn(r["bg"], (r["ok"], r["warn"], r["bad"]))


if __name__ == "__main__":
    unittest.main()
